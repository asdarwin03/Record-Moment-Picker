from __future__ import annotations

from typing import Any, Protocol

from app.core.exceptions import PipelineError
from app.schemas.refined_text import validate_refined_text_output
from app.schemas.stt import validate_stt_output


class LLMClient(Protocol):
    def refine_text(self, transcript_items: list[dict[str, Any]]) -> Any:
        """Return refined transcript items from an LLM provider."""


def refine_text(
    stt_result: list[dict[str, Any]],
    llm_client: LLMClient | None = None,
) -> list[dict[str, Any]]:
    """
    Input:
    [
      {"start_time": 41, "end_time": 56, "text": "안냥하세요..."},
      {"start_time": 57, "end_time": 81, "text": "이 프로젝트는 생강보다..."}
    ]

    Output:
    [
      {"start_time": 41, "end_time": 56, "text": "안녕하세요..."},
      {"start_time": 57, "end_time": 81, "text": "이 프로젝트는 생각보다..."}
    ]

    If llm_client is None, this function uses a local fallback cleanup.
    If llm_client is provided, it uses the LLM client to refine text.
    """

    try:
        validated_stt_items = validate_stt_output(stt_result)
        stt_items = [item.model_dump() for item in validated_stt_items]

        if llm_client is None:
            refined_result = [_refine_item_without_llm(item) for item in stt_items]
        else:
            refined_result = llm_client.refine_text(stt_items)

        validated_refined_items = validate_refined_text_output(refined_result)
        refined_items = [item.model_dump() for item in validated_refined_items]

        _validate_metadata_preserved(stt_items, refined_items)
        return refined_items
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"refine_text failed: {exc}") from exc


def _validate_metadata_preserved(
    stt_items: list[dict[str, Any]],
    refined_items: list[dict[str, Any]],
) -> None:
    if len(refined_items) != len(stt_items):
        raise PipelineError("refined text output length must match STT input length.")

    for index, (original, refined) in enumerate(zip(stt_items, refined_items)):
        original_metadata = {key: value for key, value in original.items() if key != "text"}
        refined_metadata = {key: value for key, value in refined.items() if key != "text"}

        if original_metadata != refined_metadata:
            raise PipelineError(
                f"refined_result[{index}] must preserve all metadata fields exactly."
            )


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
