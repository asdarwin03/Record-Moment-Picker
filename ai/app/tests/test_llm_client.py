from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from email.message import Message

import pytest

from app.clients.llm_client import LLMClient, LLMClientConfig
from app.clients.llm_client import LLMClientError
from app.clients.llm_client import LLMRateLimitError


SEGMENT = {
    "sid": "segment_01",
    "start_time": 0,
    "end_time": 3,
    "title": "Intro",
    "summary": ["Opening remarks"],
    "texts": [
        {
            "t_id": "001",
            "start_time": 0,
            "end_time": 3,
            "text": "Hello.",
        }
    ],
    "important": [],
}


ARRAY_SCHEMA = {
    "type": "array",
    "items": {"type": "object"},
}


class StubLLMClient(LLMClient):
    def __init__(self, response: Any) -> None:
        super().__init__(LLMClientConfig(api_key="test-key"))
        self.response = response
        self.payload: dict[str, Any] | None = None

    def _create_response(self, payload: dict[str, Any]) -> str:
        self.payload = payload
        return json.dumps(self.response)


def test_generate_json_unwraps_schema_name_data_envelope_for_array_schema():
    client = StubLLMClient({"structured_segments": {"data": [SEGMENT]}})

    result = client.generate_json(
        system_prompt="Return structured segments.",
        user_payload={"items": []},
        schema=ARRAY_SCHEMA,
        schema_name="structured_segments",
    )

    assert result == [SEGMENT]


def test_extract_output_text_includes_incomplete_reason():
    client = LLMClient(LLMClientConfig(api_key="test-key"))

    with pytest.raises(LLMClientError, match="max_output_tokens"):
        client._extract_output_text(
            {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
            }
        )


def test_generate_json_uses_strict_schema_format():
    client = StubLLMClient({"data": [SEGMENT]})

    client.generate_json(
        system_prompt="Return structured segments.",
        user_payload={"items": []},
        schema=ARRAY_SCHEMA,
        schema_name="structured_segments",
    )

    assert client.payload is not None
    assert client.payload["text"]["format"]["strict"] is True


def test_retry_delay_uses_retry_after_header_for_rate_limit():
    client = LLMClient(LLMClientConfig(api_key="test-key"))
    headers = Message()
    headers["Retry-After"] = "17"
    error = HTTPError(
        url="https://api.openai.test/responses",
        code=429,
        msg="Too Many Requests",
        hdrs=headers,
        fp=None,
    )

    assert client._retry_delay_seconds(error, attempt=0) == 17


def test_http_error_returns_friendly_rate_limit_error():
    client = LLMClient(LLMClientConfig(api_key="test-key"))
    headers = Message()
    headers["Retry-After"] = "30"
    error = HTTPError(
        url="https://api.openai.test/responses",
        code=429,
        msg="Too Many Requests",
        hdrs=headers,
        fp=None,
    )

    result = client._http_error(error)

    assert isinstance(result, LLMRateLimitError)
    assert "rate limit" in str(result)
    assert "30 seconds" in str(result)
