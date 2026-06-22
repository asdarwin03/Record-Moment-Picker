from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.clients.llm_client import default_llm_client
from app.core.config import settings
from app.core.exceptions import SchemaValidationError
from app.modules.reasoning.prompt import (
    DECOMPOSE_SUMMARIES_SYSTEM_PROMPT,
    MAP_UNITS_SYSTEM_PROMPT,
    REASONING_SYSTEM_PROMPT,
)
from app.schemas.final_result import validate_final_result
from app.schemas.segment import validate_structured_segments


# 하나의 summary에 대해 최종 노출할 clue(근거 t_id)의 최대 개수.
# LLM은 후보를 넓게 제시할 수 있고, service가 score 기준으로 top-k만 남긴다.
MAX_CLUES_PER_SUMMARY = 3

# units 모드에서 하나의 summary 문장을 분해할 수 있는 의미 단위의 최대 개수.
MAX_UNITS_PER_SUMMARY = 3

# Reasoning 모듈 내부 모드. 전역 config를 건드리지 않고 2-pass units 경로를 기본으로 사용한다.
REASONING_MODE = "units"

# LLM이 사용할 수 있는 evidence score. Final Result에는 포함되지 않으며
# top-k 선별에만 사용한다.
ALLOWED_CLUE_SCORES = {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}


# LLM은 sid + clues만 반환한다. 기존 segment 필드는 service가 보존한다.
# clue item은 새 형식 {"t_id": "001", "score": 1.0}을 사용하지만,
# 하위 호환을 위해 _rank_and_truncate_scored_clues에서 ["001", "002"]
# 형식도 허용한다.
REASONING_CLUES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["segments"],
    "additionalProperties": False,
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["sid", "clues"],
                "additionalProperties": False,
                "properties": {
                    "sid": {"type": "string"},
                    "clues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["summary_index", "clue"],
                            "additionalProperties": False,
                            "properties": {
                                "summary_index": {"type": "integer"},
                                "clue": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["t_id", "score"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "t_id": {"type": "string"},
                                            "score": {
                                                "type": "number",
                                                "enum": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
    },
}


# Phase 1(분해) LLM 응답 스키마. 각 summary를 의미 단위(unit_text)로 나눈다.
DECOMPOSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["segments"],
    "additionalProperties": False,
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["sid", "summaries"],
                "additionalProperties": False,
                "properties": {
                    "sid": {"type": "string"},
                    "summaries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["summary_index", "summary_units"],
                            "additionalProperties": False,
                            "properties": {
                                "summary_index": {"type": "integer"},
                                "summary_units": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["unit_text"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "unit_text": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
    },
}


# Phase 2(매핑) LLM 응답 스키마. 각 unit에 근거 t_id 1개(clue)를 붙인다.
MAP_UNITS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["segments"],
    "additionalProperties": False,
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["sid", "summaries"],
                "additionalProperties": False,
                "properties": {
                    "sid": {"type": "string"},
                    "summaries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["summary_index", "summary_units"],
                            "additionalProperties": False,
                            "properties": {
                                "summary_index": {"type": "integer"},
                                "summary_units": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["unit_text", "clue"],
                                        "additionalProperties": False,
                                        "properties": {
                                            "unit_text": {"type": "string"},
                                            "clue": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
    },
}


def add_reasoning(
    structured_segments: list[dict],
    *,
    llm_client=default_llm_client,
    max_output_tokens: int | None = None,
) -> list[dict]:
    """
    Structured Segments에 clues 필드를 추가해 Final Result를 생성한다.

    summary를 의미 단위로 분해(LLM #1)하고 각 단위에 근거 t_id를 매핑(LLM #2)한 뒤
    기존 clues 형식으로 재조합한다. 외부 Final Result schema는 변경하지 않는다.
    """
    segments = _validate_input(structured_segments)
    if not segments:
        return []

    token_limit = (
        max_output_tokens or settings.llm_reasoning_max_output_tokens
    )

    if REASONING_MODE == "single":
        return _add_reasoning_single(
            segments,
            llm_client=llm_client,
            max_output_tokens=token_limit,
        )

    return _add_reasoning_units(
        segments,
        llm_client=llm_client,
        max_output_tokens=token_limit,
    )


def _add_reasoning_single(
    segments: list[dict],
    *,
    llm_client=default_llm_client,
    max_output_tokens: int | None = None,
) -> list[dict]:
    """구방식: 단일 LLM 호출로 summary별 clue를 생성한다."""
    raw_clue_result = llm_client.generate_json(
        system_prompt=REASONING_SYSTEM_PROMPT,
        user_payload=_build_reasoning_input(segments),
        schema=REASONING_CLUES_SCHEMA,
        schema_name="reasoning_clues",
        max_output_tokens=(
            max_output_tokens or settings.llm_reasoning_max_output_tokens
        ),
    )

    clues_by_sid = _normalize_clues(raw_clue_result, segments)
    final_result = _attach_clues(segments, clues_by_sid)
    return _validate_output(final_result)


def _add_reasoning_units(segments: list[dict]) -> list[dict]:
    """units 모드: 분해 → 매핑 → 재조합으로 clue를 생성한다."""
    units = _decompose_summaries(segments)
    unit_t_ids = _map_units_to_clues(segments, units)
    clues_by_sid = {
        segment["sid"]: _recombine_units(segment, unit_t_ids[segment["sid"]])
        for segment in segments
    }
    final_result = _attach_clues(segments, clues_by_sid)
    return _validate_output(final_result)


def _validate_input(structured_segments: list[dict]) -> list[dict]:
    try:
        validated = validate_structured_segments(structured_segments)
    except Exception as error:
        raise SchemaValidationError(
            "Structured segments schema validation failed."
        ) from error
    return [segment.model_dump() for segment in validated]


def _build_reasoning_input(segments: list[dict]) -> dict[str, Any]:
    """Reasoning 판단에 필요한 필드만 LLM에 넘긴다."""
    return {
        "segments": [
            {"sid": s["sid"], "summary": s["summary"], "texts": s["texts"]}
            for s in segments
        ]
    }


def _attach_clues(
    segments: list[dict],
    clues_by_sid: dict[str, list[dict]],
) -> list[dict]:
    result = deepcopy(segments)
    for segment in result:
        segment["clues"] = clues_by_sid[segment["sid"]]
    return result


def _validate_output(final_result: list[dict]) -> list[dict]:
    try:
        validated = validate_final_result(final_result)
    except Exception as error:
        raise SchemaValidationError(
            "Final result schema validation failed."
        ) from error
    return [segment.model_dump() for segment in validated]


def _normalize_clues(
    raw_result: Any,
    original_segments: list[dict],
) -> dict[str, list[dict]]:
    """
    LLM 응답을 검증해 segment별 clue로 정규화한다.

    score 기반 top-k 선별과 결정적 정렬은 _normalize_segment_clues에서
    수행한다.
    """
    expected_sids = {segment["sid"] for segment in original_segments}
    raw_clues_by_sid = _extract_clues_by_sid(raw_result, expected_sids)

    return {
        segment["sid"]: _normalize_segment_clues(
            segment,
            raw_clues_by_sid[segment["sid"]],
        )
        for segment in original_segments
    }


def _extract_clues_by_sid(
    raw_result: Any,
    expected_sids: set[str],
) -> dict[str, list[Any]]:
    """LLM 응답 최상위 구조를 검증하고 sid → raw clue 리스트로 그룹핑한다."""
    if not isinstance(raw_result, dict):
        return {}

    raw_segments = _find_reasoning_segments(raw_result, expected_sids)
    if raw_segments is None:
        return {}

    clues_by_sid: dict[str, list[Any]] = {}
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            continue

        sid = raw_segment.get("sid")
        clues = raw_segment.get("clues")

        if sid not in expected_sids:
            continue
        if not isinstance(clues, list):
            continue

        clues_by_sid.setdefault(sid, []).extend(clues)

    for sid in expected_sids:
        clues_by_sid.setdefault(sid, [])

    return clues_by_sid


def _find_reasoning_segments(
    value: Any,
    expected_sids: set[str],
) -> list[dict] | None:
    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return value
        return None

    if not isinstance(value, dict):
        return None

    raw_segments = value.get("segments")
    if isinstance(raw_segments, list):
        return raw_segments

    mapped_segments = []
    for key, nested_value in value.items():
        if key not in expected_sids or not isinstance(nested_value, dict):
            continue

        mapped_segment = dict(nested_value)
        mapped_segment.setdefault("sid", key)
        mapped_segments.append(mapped_segment)

    if mapped_segments:
        return mapped_segments

    for nested_value in value.values():
        nested_segments = _find_reasoning_segments(nested_value, expected_sids)
        if nested_segments is not None:
            return nested_segments

    return None


def _normalize_segment_clues(
    segment: dict,
    raw_clues: list[Any],
) -> list[dict]:
    """
    한 segment의 clue를 검증·정규화하고 summary_index 순으로 정렬한다.

    - 각 summary 문장마다 정확히 하나의 clue 객체가 있어야 한다.
    - clue 안의 t_id는 같은 segment의 texts에 존재해야 한다.
    - score 기반으로 t_id를 top-k 선별한다.
    """
    summary_count = len(segment["summary"])
    valid_t_ids = {text["t_id"] for text in segment["texts"]}
    t_id_order = {text["t_id"]: index for index, text in enumerate(segment["texts"])}

    normalized: list[dict] = []
    seen_indices: set[int] = set()

    for clue_object in raw_clues:
        parsed_clue = _try_parse_clue_object(clue_object, summary_count)
        if parsed_clue is None:
            continue

        summary_index, raw_clue = parsed_clue

        if summary_index in seen_indices:
            continue
        seen_indices.add(summary_index)

        selected_t_ids = _rank_and_truncate_scored_clues(
            clue=raw_clue,
            valid_t_ids=valid_t_ids,
            t_id_order=t_id_order,
            top_k=MAX_CLUES_PER_SUMMARY,
        )
        if not selected_t_ids:
            selected_t_ids = _fallback_clue_t_ids(segment, summary_index)
        normalized.append(
            {"summary_index": summary_index, "clue": selected_t_ids}
        )

    for summary_index in range(summary_count):
        if summary_index in seen_indices:
            continue

        normalized.append(
            {
                "summary_index": summary_index,
                "clue": _fallback_clue_t_ids(segment, summary_index),
            }
        )

    return sorted(normalized, key=lambda item: item["summary_index"])


def _try_parse_clue_object(
    clue_object: Any,
    summary_count: int,
) -> tuple[int, list[Any]] | None:
    try:
        return _parse_clue_object(clue_object, summary_count)
    except SchemaValidationError:
        return None


def _parse_clue_object(
    clue_object: Any,
    summary_count: int,
) -> tuple[int, list[Any]]:
    """clue 객체 하나를 (summary_index, raw_clue_list)로 분해하며 검증한다."""
    if (
        not isinstance(clue_object, dict)
        or set(clue_object.keys()) != {"summary_index", "clue"}
    ):
        raise SchemaValidationError(
            "Each clue must have exactly summary_index and clue."
        )

    summary_index = clue_object["summary_index"]
    clue = clue_object["clue"]

    if isinstance(summary_index, bool) or not isinstance(summary_index, int):
        raise SchemaValidationError("summary_index must be an integer.")
    if not 0 <= summary_index < summary_count:
        raise SchemaValidationError(
            f"summary_index {summary_index} is out of range."
        )
    if not isinstance(clue, list):
        raise SchemaValidationError("clue must be a list.")

    return summary_index, clue


def _rank_and_truncate_scored_clues(
    *,
    clue: list[Any],
    valid_t_ids: set[str],
    t_id_order: dict[str, int],
    top_k: int,
) -> list[str]:
    """
    후보 clue를 score 기준으로 top-k 선별한 뒤 발화 순서로 정렬한다.

    입력은 두 형태를 허용한다.
        새 형식: [{"t_id": "001", "score": 1.0}, ...]
        기존 형식: ["001", "002"]  (score 1.0으로 간주, 하위 호환용)

    같은 t_id가 여러 번 나오면 가장 높은 score만 유지한다.
    score 동점이면 발화 순서 오름차순으로 정렬한다.
    최종 출력은 relevance 순서보다 발화 순서가 자연스럽다.
    """
    if top_k <= 0:
        return []

    best_score_by_t_id: dict[str, float] = {}
    for item in clue:
        try:
            t_id, score = _parse_clue_item(item)
        except SchemaValidationError:
            continue

        if t_id not in valid_t_ids:
            continue

        previous = best_score_by_t_id.get(t_id)
        if previous is None or score > previous:
            best_score_by_t_id[t_id] = score

    ranked = sorted(
        best_score_by_t_id.items(),
        key=lambda entry: (-entry[1], t_id_order[entry[0]]),
    )
    selected = [t_id for t_id, _ in ranked[:top_k]]
    return sorted(selected, key=lambda t_id: t_id_order[t_id])


def _fallback_clue_t_ids(segment: dict, summary_index: int) -> list[str]:
    """Return a deterministic in-segment clue when LLM evidence is unusable."""
    texts = segment["texts"]
    if not texts:
        raise SchemaValidationError(
            f"segment {segment['sid']} has summary but no transcript texts."
        )

    fallback_index = min(summary_index, len(texts) - 1)
    return [texts[fallback_index]["t_id"]]


def _parse_clue_item(item: Any) -> tuple[str, float]:
    """clue 항목 하나를 (t_id, score)로 분해한다. 기존 string 형식도 허용한다."""
    if isinstance(item, str):
        return item, 1.0

    if not isinstance(item, dict) or set(item.keys()) != {"t_id", "score"}:
        raise SchemaValidationError(
            "Each scored clue item must have exactly t_id and score."
        )

    t_id = item["t_id"]
    if not isinstance(t_id, str):
        raise SchemaValidationError("clue t_id must be a string.")

    return t_id, _normalize_score(item["score"])


def _normalize_score(score: Any) -> float:
    """LLM이 반환한 score를 검증하고 float로 정규화한다."""
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise SchemaValidationError("clue score must be a number.")

    rounded = round(float(score), 1)
    if rounded not in ALLOWED_CLUE_SCORES:
        raise SchemaValidationError(
            "clue score must be one of: 0.0, 0.2, 0.4, 0.6, 0.8, 1.0."
        )
    return rounded


def _build_decompose_input(segments: list[dict]) -> dict[str, Any]:
    """Phase 1: 분해에는 summary 문장만 필요하다(텍스트 미포함, 비용 절감)."""
    return {
        "segments": [{"sid": s["sid"], "summary": s["summary"]} for s in segments]
    }


def _clean_units(unit_texts: list[Any]) -> list[str]:
    """unit_text 후보에서 빈 문자열/비문자열을 제거하고 공백을 정리한다."""
    cleaned: list[str] = []
    for text in unit_texts:
        if isinstance(text, str) and text.strip():
            cleaned.append(text.strip())
    return cleaned


def _extract_summary_units_by_sid(
    raw_result: Any,
    field_name: str,
) -> dict[str, dict[int, list[Any]]]:
    """LLM 응답을 sid → {summary_index → unit별 field_name 값 리스트}로 그룹핑한다.

    분해(unit_text) 응답과 매핑(clue) 응답 모두 동일한 중첩 구조를 가지므로
    이 helper가 구조 탐색을 공유하고, 어떤 leaf 필드를 꺼낼지만 다르게 한다.
    """
    result: dict[str, dict[int, list[Any]]] = {}
    if not isinstance(raw_result, dict):
        return result

    segments = raw_result.get("segments")
    if not isinstance(segments, list):
        return result

    for raw_segment in segments:
        if not isinstance(raw_segment, dict):
            continue
        sid = raw_segment.get("sid")
        if not isinstance(sid, str):
            continue
        summaries = raw_segment.get("summaries")
        if not isinstance(summaries, list):
            continue

        per_summary: dict[int, list[Any]] = {}
        for raw_summary in summaries:
            if not isinstance(raw_summary, dict):
                continue
            summary_index = raw_summary.get("summary_index")
            if isinstance(summary_index, bool) or not isinstance(summary_index, int):
                continue
            units = raw_summary.get("summary_units")
            if not isinstance(units, list):
                continue
            per_summary[summary_index] = [
                unit.get(field_name) if isinstance(unit, dict) else None
                for unit in units
            ]
        result[sid] = per_summary

    return result


def _extract_decomposition_by_sid(
    raw_result: Any,
) -> dict[str, dict[int, list[Any]]]:
    """LLM 분해 응답을 sid → {summary_index → raw unit_text 리스트}로 그룹핑한다."""
    return _extract_summary_units_by_sid(raw_result, "unit_text")


def _normalize_decomposition(
    raw_result: Any,
    segments: list[dict],
) -> dict[str, dict[int, list[str]]]:
    """분해 응답을 정규화한다. 모든 summary는 항상 1~3개 unit을 갖는다."""
    raw_by_sid = _extract_decomposition_by_sid(raw_result)

    normalized: dict[str, dict[int, list[str]]] = {}
    for segment in segments:
        sid = segment["sid"]
        summary = segment["summary"]
        raw_summaries = raw_by_sid.get(sid, {})

        per_summary: dict[int, list[str]] = {}
        for summary_index in range(len(summary)):
            units = _clean_units(raw_summaries.get(summary_index, []))
            if not units:
                units = [summary[summary_index]]
            per_summary[summary_index] = units[:MAX_UNITS_PER_SUMMARY]
        normalized[sid] = per_summary

    return normalized


def _decompose_summaries(
    segments: list[dict],
) -> dict[str, dict[int, list[str]]]:
    """Phase 1: LLM으로 summary를 의미 단위로 분해하고 정규화한다."""
    raw_result = default_llm_client.generate_json(
        system_prompt=DECOMPOSE_SUMMARIES_SYSTEM_PROMPT,
        user_payload=_build_decompose_input(segments),
        schema=DECOMPOSE_SCHEMA,
        schema_name="decompose_summaries",
        max_output_tokens=settings.llm_reasoning_max_output_tokens,
    )
    return _normalize_decomposition(raw_result, segments)


def _build_map_input(
    segments: list[dict],
    units: dict[str, dict[int, list[str]]],
) -> dict[str, Any]:
    """Phase 2: 매핑에는 texts와 분해된 unit이 필요하다."""
    return {
        "segments": [
            {
                "sid": s["sid"],
                "texts": s["texts"],
                "summaries": [
                    {
                        "summary_index": summary_index,
                        "summary_units": [
                            {"unit_text": unit_text}
                            for unit_text in units[s["sid"]][summary_index]
                        ],
                    }
                    for summary_index in sorted(units[s["sid"]])
                ],
            }
            for s in segments
        ]
    }


def _extract_unit_clues_by_sid(
    raw_result: Any,
) -> dict[str, dict[int, list[Any]]]:
    """LLM 매핑 응답을 sid → {summary_index → unit 순서의 raw clue 리스트}로 그룹핑한다."""
    return _extract_summary_units_by_sid(raw_result, "clue")


def _normalize_unit_mappings(
    raw_result: Any,
    segments: list[dict],
    units: dict[str, dict[int, list[str]]],
) -> dict[str, dict[int, list[str]]]:
    """매핑 응답을 정규화한다. unit 순서로 유효한 t_id만 모은다(빈 리스트 가능)."""
    raw_by_sid = _extract_unit_clues_by_sid(raw_result)

    normalized: dict[str, dict[int, list[str]]] = {}
    for segment in segments:
        sid = segment["sid"]
        valid_t_ids = {text["t_id"] for text in segment["texts"]}
        raw_summaries = raw_by_sid.get(sid, {})

        per_summary: dict[int, list[str]] = {}
        for summary_index, unit_texts in units[sid].items():
            raw_clues = raw_summaries.get(summary_index, [])
            t_ids: list[str] = []
            for unit_position in range(len(unit_texts)):
                if unit_position >= len(raw_clues):
                    continue
                clue = raw_clues[unit_position]
                if isinstance(clue, str) and clue in valid_t_ids:
                    t_ids.append(clue)
            per_summary[summary_index] = t_ids
        normalized[sid] = per_summary

    return normalized


def _map_units_to_clues(
    segments: list[dict],
    units: dict[str, dict[int, list[str]]],
) -> dict[str, dict[int, list[str]]]:
    """Phase 2: LLM으로 각 unit에 근거 t_id를 매핑하고 정규화한다."""
    raw_result = default_llm_client.generate_json(
        system_prompt=MAP_UNITS_SYSTEM_PROMPT,
        user_payload=_build_map_input(segments, units),
        schema=MAP_UNITS_SCHEMA,
        schema_name="map_units",
        max_output_tokens=settings.llm_reasoning_max_output_tokens,
    )
    return _normalize_unit_mappings(raw_result, segments, units)


def _recombine_units(
    segment: dict,
    summary_unit_t_ids: dict[int, list[str]],
) -> list[dict]:
    """unit별 t_id를 summary별 clue로 합친다.

    union(등장순 우선 dedup) → 발화 순서 정렬 → top-k 절단 → 비면 결정적 fallback.
    summary당 최소 1개 clue를 보장한다.
    """
    t_id_order = {text["t_id"]: index for index, text in enumerate(segment["texts"])}
    summary_count = len(segment["summary"])

    clues: list[dict] = []
    for summary_index in range(summary_count):
        t_ids = summary_unit_t_ids.get(summary_index, [])
        deduped = list(dict.fromkeys(t_ids))
        ordered = sorted(deduped, key=lambda t_id: t_id_order[t_id])
        ordered = ordered[:MAX_CLUES_PER_SUMMARY]
        if not ordered:
            ordered = _fallback_clue_t_ids(segment, summary_index)
        clues.append({"summary_index": summary_index, "clue": ordered})

    return clues
