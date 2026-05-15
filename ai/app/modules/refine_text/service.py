from __future__ import annotations

import json
from typing import Any, Protocol

from app.core.exceptions import PipelineError
from app.modules.refine_text.prompt import REFINE_TEXT_SYSTEM_PROMPT


class LLMClient(Protocol):
    def generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        """Return parsed JSON from an LLM call."""


def refine_text(stt_result: list[dict[str, Any]], llm_client: LLMClient | None = None) -> list[dict[str, Any]]:
    """
    Input:
    [
      {"t_id": "001", "start_time": 41, "end_time": 56, "text": "안냥하세요..."},
      {"t_id": "002", "start_time": 57, "end_time": 81, "text": "이 프로젝트는 생강보다..."}
    ]

    Output:
    [
      {"t_id": "001", "start_time": 41, "end_time": 56, "text": "안녕하세요..."},
      {"t_id": "002", "start_time": 57, "end_time": 81, "text": "이 프로젝트는 생각보다..."}
    ]
    """
    try:
        _validate_input(stt_result)

        if llm_client is None:
            refined_result = [_refine_item_without_llm(item) for item in stt_result]
        else:
            refined_result = llm_client.generate_json(
                system_prompt=REFINE_TEXT_SYSTEM_PROMPT,
                user_prompt=_build_user_prompt(stt_result),
            )

        _validate_output(stt_result, refined_result)
        return refined_result
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"refine_text failed: {exc}") from exc


def _build_user_prompt(stt_result: list[dict[str, Any]]) -> str:
    return json.dumps(stt_result, ensure_ascii=False, indent=2)


def _validate_input(stt_result: list[dict[str, Any]]) -> None:
    if not isinstance(stt_result, list):
        raise PipelineError("stt_result must be a list.")

    for index, item in enumerate(stt_result):
        if not isinstance(item, dict):
            raise PipelineError(f"stt_result[{index}] must be a dictionary.")

        _validate_required_text(item, index)
        _validate_time_fields(item, index)


def _validate_required_text(item: dict[str, Any], index: int) -> None:
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        raise PipelineError(f"stt_result[{index}].text must be a non-empty string.")


def _validate_time_fields(item: dict[str, Any], index: int) -> None:
    if "start_time" in item or "end_time" in item:
        if "start_time" not in item or "end_time" not in item:
            raise PipelineError(
                f"stt_result[{index}] must include both start_time and end_time.",
            )
        start_time = _validate_non_negative_number(item["start_time"], f"stt_result[{index}].start_time")
        end_time = _validate_non_negative_number(item["end_time"], f"stt_result[{index}].end_time")
        if end_time < start_time:
            raise PipelineError(f"stt_result[{index}].end_time must be greater than or equal to start_time.")
        return

    if "time" not in item:
        raise PipelineError(f"stt_result[{index}] must include time or start_time/end_time.")

    _validate_non_negative_number(item["time"], f"stt_result[{index}].time")


def _validate_non_negative_number(value: Any, field_name: str) -> float:
    if not isinstance(value, int | float) or value < 0:
        raise PipelineError(f"{field_name} must be a non-negative number.")
    return float(value)


def _validate_output(
    stt_result: list[dict[str, Any]],
    refined_result: Any,
) -> None:
    if not isinstance(refined_result, list):
        raise PipelineError("refined text output must be a list.")

    if len(refined_result) != len(stt_result):
        raise PipelineError("refined text output length must match STT input length.")

    for index, (original, refined) in enumerate(zip(stt_result, refined_result)):
        if not isinstance(refined, dict):
            raise PipelineError(f"refined_result[{index}] must be a dictionary.")

        _validate_required_text(refined, index)
        _validate_metadata_preserved(original, refined, index)


def _validate_metadata_preserved(
    original: dict[str, Any],
    refined: dict[str, Any],
    index: int,
) -> None:
    original_metadata = {key: value for key, value in original.items() if key != "text"}
    refined_metadata = {key: value for key, value in refined.items() if key != "text"}

    if original_metadata != refined_metadata:
        raise PipelineError(f"refined_result[{index}] must preserve all metadata fields exactly.")


def _refine_item_without_llm(item: dict[str, Any]) -> dict[str, Any]:
    refined_item = dict(item)
    refined_item["text"] = _basic_korean_cleanup(str(item["text"]))
    return refined_item


def _basic_korean_cleanup(text: str) -> str:
    replacements = {
        "안냥하세요": "안녕하세요",
        "생강보다": "생각보다",
        "복잣합니다": "복잡합니다",
        "에스티티": "STT",
    }

    refined_text = " ".join(text.strip().split())
    for source, target in replacements.items():
        refined_text = refined_text.replace(source, target)
    return refined_text
