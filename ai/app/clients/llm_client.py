from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.exceptions import LLMProcessingError
from app.modules.reasoning.prompt import REASONING_SYSTEM_PROMPT
from app.modules.refine_text.prompt import REFINE_TEXT_SYSTEM_PROMPT
from app.modules.segmenting.prompt import SEGMENT_TEXT_SYSTEM_PROMPT


class LLMClientError(LLMProcessingError):
    """Raised when the LLM provider cannot return a usable response."""


@dataclass(frozen=True)
class LLMClientConfig:
    api_key: str | None = None
    model: str = "gpt-4.1-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 60
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "LLMClientConfig":
        return cls(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )


class LLMClient:
    """Small OpenAI Responses API client used after Whisper transcription.

    Whisper-based STT belongs in app.modules.stt. This client only handles
    post-STT text tasks: refinement, segmenting, and reasoning.
    """

    def __init__(self, config: LLMClientConfig | None = None) -> None:
        self.config = config or LLMClientConfig.from_env()

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: Any,
        schema: dict[str, Any] | None = None,
        schema_name: str = "rmp_response",
        max_output_tokens: int = 4096,
    ) -> Any:
        prompt = self._build_json_prompt(system_prompt, user_payload)
        response_schema = self._prepare_response_schema(schema)
        payload: dict[str, Any] = {
            "model": self.config.model,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
            "store": False,
        }

        if response_schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": response_schema,
                    "strict": False,
                }
            }
        else:
            payload["text"] = {"format": {"type": "json_object"}}

        text = self._create_response(payload)
        result = self._parse_json(text)
        return self._unwrap_array_schema_result(result, schema)

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int = 2048,
    ) -> str:
        payload = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
        return self._create_response(payload)

    def refine_text(self, transcript_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.generate_json(
            system_prompt=REFINE_TEXT_SYSTEM_PROMPT,
            user_payload={"items": transcript_items},
            schema=load_shared_schema("refined-text.schema.json"),
            schema_name="refined_text",
        )

    def segment_text(self, refined_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.generate_json(
            system_prompt=SEGMENT_TEXT_SYSTEM_PROMPT,
            user_payload={"items": refined_items},
            schema=load_shared_schema("structured-segments.schema.json"),
            schema_name="structured_segments",
            max_output_tokens=8192,
        )

    def add_reasoning(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.generate_json(
            system_prompt=REASONING_SYSTEM_PROMPT,
            user_payload={"segments": segments},
            schema=load_shared_schema("final-result.schema.json"),
            schema_name="final_result",
            max_output_tokens=8192,
        )

    def _create_response(self, payload: dict[str, Any]) -> str:
        if not self.config.api_key:
            raise LLMClientError("OPENAI_API_KEY is not set.")
        if self.config.api_key in {
            "your_openai_api_key_here",
            "replace_with_your_openai_api_key",
        }:
            raise LLMClientError(
                "OPENAI_API_KEY is still a placeholder. "
                "Set it to your real OpenAI API key in the root .env file."
            )
        if not self.config.api_key.isascii():
            raise LLMClientError(
                "OPENAI_API_KEY must be a real ASCII API key. "
                "Replace the placeholder value with your OpenAI API key."
            )

        url = f"{self.config.base_url.rstrip('/')}/responses"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return self._extract_output_text(data)
            except HTTPError as error:
                last_error = error
                if error.code not in {408, 409, 429, 500, 502, 503, 504}:
                    raise self._http_error(error) from error
            except (TimeoutError, URLError) as error:
                last_error = error

            if attempt < self.config.max_retries:
                time.sleep(2**attempt)

        raise LLMClientError(f"LLM request failed: {last_error}") from last_error

    def _extract_output_text(self, data: dict[str, Any]) -> str:
        if data.get("status") not in {None, "completed"}:
            raise LLMClientError(f"LLM response status is {data.get('status')!r}.")

        if isinstance(data.get("output_text"), str):
            return data["output_text"]

        chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)

        if not chunks:
            raise LLMClientError("LLM response did not include output text.")

        return "".join(chunks).strip()

    def _http_error(self, error: HTTPError) -> LLMClientError:
        try:
            detail = error.read().decode("utf-8")
        except Exception:
            detail = error.reason
        return LLMClientError(f"LLM request failed with HTTP {error.code}: {detail}")

    def _build_json_prompt(self, system_prompt: str, user_payload: Any) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Return only JSON that matches the requested contract.\n\n"
                    f"Input JSON:\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}"
                ),
            },
        ]

    def _parse_json(self, text: str) -> Any:
        normalized = text.strip()
        if normalized.startswith("```"):
            normalized = normalized.removeprefix("```json").removeprefix("```").strip()
            normalized = normalized.removesuffix("```").strip()

        try:
            return json.loads(normalized)
        except json.JSONDecodeError as error:
            raise LLMClientError(f"LLM returned invalid JSON: {text[:500]}") from error

    def _strip_schema_metadata(self, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in schema.items()
            if key not in {"$schema", "$id", "title", "description"}
        }

    def _prepare_response_schema(self, schema: dict[str, Any] | None) -> dict[str, Any] | None:
        if schema is None:
            return None

        stripped_schema = self._strip_schema_metadata(schema)
        if stripped_schema.get("type") != "array":
            return stripped_schema

        return {
            "type": "object",
            "required": ["data"],
            "additionalProperties": False,
            "properties": {
                "data": stripped_schema,
            },
        }

    def _unwrap_array_schema_result(self, result: Any, schema: dict[str, Any] | None) -> Any:
        if schema is None or self._strip_schema_metadata(schema).get("type") != "array":
            return result

        if isinstance(result, dict) and isinstance(result.get("data"), list):
            return result["data"]

        return result


def load_shared_schema(filename: str) -> dict[str, Any]:
    schema_path = settings.shared_schema_path(filename)
    with schema_path.open("r", encoding="utf-8") as file:
        return json.load(file)


default_llm_client = LLMClient()
