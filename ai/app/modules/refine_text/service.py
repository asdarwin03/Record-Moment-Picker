from __future__ import annotations

from collections.abc import Mapping
import inspect
import re
from typing import Any, Protocol

from app.core.exceptions import PipelineError
from app.schemas.refined_text import validate_refined_text_output
from app.schemas.stt import validate_stt_output


class LLMClient(Protocol):
    def refine_text(
        self,
        transcript_items: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Return refined transcript items from an LLM provider."""


class ContextClient(Protocol):
    def identify_topic(self, preview_items: list[dict[str, Any]]) -> Any:
        """Return a topic or search query from preview STT items."""

    def search_web(self, query: str) -> Any:
        """Return web search results for the topic query."""


def refine_text(
    stt_result: list[dict[str, Any]],
    llm_client: LLMClient | None = None,
    context: dict[str, Any] | str | None = None,
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
    Optional context can include a topic, preview transcript, and web results.
    """

    try:
        validated_stt_items = validate_stt_output(stt_result)
        stt_items = [item.model_dump() for item in validated_stt_items]
        refine_context = _normalize_refine_context(context)

        if llm_client is None:
            refined_result = [_refine_item_without_llm(item) for item in stt_items]
        else:
            refined_result = _call_llm_refine(llm_client, stt_items, refine_context)

        refined_result = _restore_metadata_and_clean_text(stt_items, refined_result)
        validated_refined_items = validate_refined_text_output(refined_result)
        refined_items = [item.model_dump() for item in validated_refined_items]

        _validate_metadata_preserved(stt_items, refined_items)
        return refined_items
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"refine_text failed: {exc}") from exc


def build_refine_context_from_preview(
    preview_stt_result: list[dict[str, Any]],
    context_client: ContextClient | None = None,
    *,
    max_web_results: int = 5,
) -> dict[str, Any]:
    """
    Build refinement context from the beginning of a recording.

    `context_client` is expected to perform topic detection and web-search
    tool-use. Without it, this returns preview transcript context only.
    """

    try:
        validated_preview_items = validate_stt_output(preview_stt_result)
        preview_items = [item.model_dump() for item in validated_preview_items]
        preview_text = _join_transcript_text(preview_items)
        topic = _infer_topic_from_preview(preview_text)
        search_query = topic
        web_results: list[dict[str, str]] = []

        if context_client is not None:
            topic_response = _call_topic_identifier(context_client, preview_items)
            topic, search_query = _coerce_topic_response(
                topic_response,
                fallback_topic=topic,
                fallback_query=search_query,
            )

            if search_query:
                web_response = _call_web_search(
                    context_client,
                    search_query,
                    max_web_results=max(0, max_web_results),
                )
                web_results = _normalize_web_results(web_response, max_web_results)

        return {
            "topic": topic,
            "search_query": search_query,
            "preview_transcript": preview_text,
            "web_results": web_results,
        }
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(f"build_refine_context_from_preview failed: {exc}") from exc


def _call_llm_refine(
    llm_client: LLMClient,
    stt_items: list[dict[str, Any]],
    context: dict[str, Any] | None,
) -> Any:
    refine_method = llm_client.refine_text
    if context is None:
        return refine_method(stt_items)

    try:
        signature = inspect.signature(refine_method)
    except (TypeError, ValueError):
        try:
            return refine_method(stt_items, context=context)
        except TypeError as error:
            if "context" in str(error):
                return refine_method(stt_items)
            raise

    parameters = signature.parameters
    if _accepts_keyword(parameters, "context"):
        return refine_method(stt_items, context=context)
    if _accepts_second_positional(parameters):
        return refine_method(stt_items, context)

    return refine_method(stt_items)


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


def _normalize_refine_context(context: dict[str, Any] | str | None) -> dict[str, Any] | None:
    if context is None:
        return None

    if isinstance(context, str):
        text = _clip_context_text(context)
        return {"notes": text} if text else None

    if not isinstance(context, dict):
        text = _clip_context_text(str(context))
        return {"notes": text} if text else None

    normalized = dict(context)
    if "topic" in normalized:
        normalized["topic"] = _clip_context_text(str(normalized["topic"]), limit=160)
    if "search_query" in normalized:
        normalized["search_query"] = _clip_context_text(
            str(normalized["search_query"]),
            limit=180,
        )
    if "preview_transcript" in normalized:
        normalized["preview_transcript"] = _clip_context_text(
            str(normalized["preview_transcript"]),
            limit=2500,
        )
    if "web_results" in normalized:
        normalized["web_results"] = _normalize_web_results(normalized["web_results"])

    return normalized or None


def _restore_metadata_and_clean_text(
    stt_items: list[dict[str, Any]],
    refined_result: Any,
) -> list[dict[str, Any]]:
    if not isinstance(refined_result, list):
        raise PipelineError("refined text output must be a JSON array.")

    if len(refined_result) != len(stt_items):
        raise PipelineError("refined text output length must match STT input length.")

    restored_items: list[dict[str, Any]] = []
    for index, (original, refined) in enumerate(zip(stt_items, refined_result)):
        if not isinstance(refined, dict):
            raise PipelineError(f"refined_result[{index}] must be an object.")

        text = _basic_korean_cleanup(str(refined.get("text", "")))
        if not text:
            text = _basic_korean_cleanup(str(original["text"]))

        restored_item = dict(original)
        restored_item["text"] = text
        restored_items.append(restored_item)

    return restored_items


def _basic_korean_cleanup(text: str) -> str:
    replacements = {
        "안냥하세요": "안녕하세요",
        "생강보다": "생각보다",
        "복잣합니다": "복잡합니다",
        "에스티티": "STT",
        "에스티티를": "STT를",
        "에스티티가": "STT가",
        "에스티티는": "STT는",
        "에이아이": "AI",
        "제이슨": "JSON",
        "엘엘엠": "LLM",
        "레코드 모먼트 피커": "Record Moment Picker",
    }

    refined_text = " ".join(text.strip().split())
    for source, target in replacements.items():
        refined_text = refined_text.replace(source, target)

    refined_text = _deduplicate_repeated_sentences(refined_text)
    refined_text = re.sub(r"\s+([,.?!:;])", r"\1", refined_text)
    refined_text = re.sub(r"([,.?!]){3,}", r"\1\1", refined_text)
    return refined_text.strip()


def _deduplicate_repeated_sentences(text: str) -> str:
    parts = [part for part in re.split(r"([.!?。！？]+)", text) if part]
    sentences: list[str] = []
    current = ""

    for part in parts:
        current += part
        if re.fullmatch(r"[.!?。！？]+", part):
            sentences.append(current.strip())
            current = ""

    if current.strip():
        sentences.append(current.strip())

    if len(sentences) <= 1:
        return text

    deduplicated: list[str] = []
    previous_key = ""
    for sentence in sentences:
        key = _normalize_sentence_key(sentence)
        if key and key == previous_key:
            continue
        deduplicated.append(sentence)
        previous_key = key

    return " ".join(deduplicated)


def _normalize_sentence_key(sentence: str) -> str:
    return "".join(character.lower() for character in sentence if character.isalnum())


def _call_topic_identifier(
    context_client: ContextClient,
    preview_items: list[dict[str, Any]],
) -> Any:
    identify_topic = getattr(context_client, "identify_topic", None)
    if not callable(identify_topic):
        return None
    return identify_topic(preview_items)


def _call_web_search(
    context_client: ContextClient,
    search_query: str,
    max_web_results: int,
) -> Any:
    search_web = getattr(context_client, "search_web", None)
    if not callable(search_web):
        search_web = getattr(context_client, "web_search", None)
    if not callable(search_web):
        return None

    try:
        signature = inspect.signature(search_web)
    except (TypeError, ValueError):
        return search_web(search_query)

    parameters = signature.parameters
    if _accepts_keyword(parameters, "max_results"):
        return search_web(search_query, max_results=max_web_results)
    if _accepts_keyword(parameters, "limit"):
        return search_web(search_query, limit=max_web_results)
    return search_web(search_query)


def _coerce_topic_response(
    topic_response: Any,
    *,
    fallback_topic: str,
    fallback_query: str,
) -> tuple[str, str]:
    if isinstance(topic_response, dict):
        topic = _first_text_value(
            topic_response,
            ("topic", "title", "subject"),
            fallback=fallback_topic,
        )
        query = _first_text_value(
            topic_response,
            ("search_query", "query", "web_query"),
            fallback=topic or fallback_query,
        )
        return topic, query

    if isinstance(topic_response, str):
        topic = _clip_context_text(topic_response, limit=160)
        return topic or fallback_topic, topic or fallback_query

    return fallback_topic, fallback_query


def _first_text_value(
    values: dict[str, Any],
    keys: tuple[str, ...],
    *,
    fallback: str,
) -> str:
    for key in keys:
        value = values.get(key)
        if value is None:
            continue
        text = _clip_context_text(str(value), limit=180)
        if text:
            return text
    return fallback


def _normalize_web_results(
    web_response: Any,
    max_results: int = 5,
) -> list[dict[str, str]]:
    if web_response is None or max_results <= 0:
        return []

    raw_results = web_response
    if isinstance(web_response, dict):
        raw_results = (
            web_response.get("results")
            or web_response.get("items")
            or web_response.get("data")
            or []
        )

    if not isinstance(raw_results, list):
        raw_results = [raw_results]

    normalized_results: list[dict[str, str]] = []
    for raw_result in raw_results:
        if len(normalized_results) >= max_results:
            break

        if isinstance(raw_result, dict):
            result = {
                "title": _first_text_value(raw_result, ("title", "name"), fallback=""),
                "url": _first_text_value(raw_result, ("url", "link"), fallback=""),
                "snippet": _first_text_value(
                    raw_result,
                    ("snippet", "summary", "content", "text"),
                    fallback="",
                ),
            }
        else:
            result = {
                "title": "",
                "url": "",
                "snippet": _clip_context_text(str(raw_result), limit=500),
            }

        if any(result.values()):
            normalized_results.append(result)

    return normalized_results


def _join_transcript_text(items: list[dict[str, Any]]) -> str:
    return _clip_context_text(
        " ".join(str(item.get("text", "")).strip() for item in items)
    )


def _infer_topic_from_preview(preview_text: str) -> str:
    text = _clip_context_text(preview_text, limit=160)
    if not text:
        return ""

    first_sentence = re.split(r"[.!?。！？\n]", text, maxsplit=1)[0].strip()
    return _clip_context_text(first_sentence or text, limit=120)


def _clip_context_text(text: str, limit: int = 1000) -> str:
    clipped = " ".join(text.strip().split())
    if len(clipped) <= limit:
        return clipped
    return clipped[:limit].rstrip()


def _accepts_keyword(
    parameters: Mapping[str, inspect.Parameter],
    keyword: str,
) -> bool:
    return any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        or (name == keyword and parameter.kind != inspect.Parameter.POSITIONAL_ONLY)
        for name, parameter in parameters.items()
    )


def _accepts_second_positional(
    parameters: Mapping[str, inspect.Parameter],
) -> bool:
    positional_count = 0
    for parameter in parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }:
            positional_count += 1

    return positional_count >= 2
