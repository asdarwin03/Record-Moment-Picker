from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.clients.llm_client import default_llm_client
from app.core.exceptions import SchemaValidationError
from app.modules.reasoning.prompt import REASONING_SYSTEM_PROMPT
from app.schemas.final_result import validate_final_result
from app.schemas.segment import validate_structured_segments


# 하나의 summary에 대해 최종 노출할 clue(근거 t_id)의 최대 개수.
# LLM은 후보를 넓게 제시할 수 있고, service가 score 기준으로 top-k만 남긴다.
MAX_CLUES_PER_SUMMARY = 3

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
                                    "minItems": 1,
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


def add_reasoning(structured_segments: list[dict]) -> list[dict]:
    """
    Structured Segments에 clues 필드를 추가해 Final Result를 생성한다.

    기존 segment 필드는 그대로 보존하고, 각 summary 문장을 뒷받침하는
    t_id 목록만 새로 생성한다. score는 LLM이 ranking에만 사용하고
    Final Result에는 포함하지 않는다.
    """
    segments = _validate_input(structured_segments)
    if not segments:
        return []

    raw_clue_result = default_llm_client.generate_json(
        system_prompt=REASONING_SYSTEM_PROMPT,
        user_payload=_build_reasoning_input(segments),
        schema=REASONING_CLUES_SCHEMA,
        schema_name="reasoning_clues",
        max_output_tokens=4096,
    )

    clues_by_sid = _normalize_clues(raw_clue_result, segments)
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
        raise SchemaValidationError("Reasoning result must be a JSON object.")

    raw_segments = raw_result.get("segments")
    if not isinstance(raw_segments, list):
        raise SchemaValidationError("Reasoning result must contain a segments list.")

    clues_by_sid: dict[str, list[Any]] = {}
    for raw_segment in raw_segments:
        if (
            not isinstance(raw_segment, dict)
            or set(raw_segment.keys()) != {"sid", "clues"}
        ):
            raise SchemaValidationError(
                "Each reasoning segment must have exactly sid and clues."
            )

        sid = raw_segment["sid"]
        clues = raw_segment["clues"]

        if sid not in expected_sids:
            raise SchemaValidationError(f"Reasoning returned unknown sid: {sid}")
        if sid in clues_by_sid:
            raise SchemaValidationError(f"Reasoning returned duplicate sid: {sid}")
        if not isinstance(clues, list):
            raise SchemaValidationError("Reasoning clues must be a list.")

        clues_by_sid[sid] = clues

    missing = expected_sids - clues_by_sid.keys()
    if missing:
        raise SchemaValidationError(
            f"Reasoning did not return clues for sids: {sorted(missing)}."
        )

    return clues_by_sid


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
        summary_index, raw_clue = _parse_clue_object(clue_object, summary_count)

        if summary_index in seen_indices:
            raise SchemaValidationError(
                f"Duplicate summary_index in clues: {summary_index}."
            )
        seen_indices.add(summary_index)

        selected_t_ids = _rank_and_truncate_scored_clues(
            clue=raw_clue,
            valid_t_ids=valid_t_ids,
            t_id_order=t_id_order,
            top_k=MAX_CLUES_PER_SUMMARY,
        )
        normalized.append(
            {"summary_index": summary_index, "clue": selected_t_ids}
        )

    if seen_indices != set(range(summary_count)):
        raise SchemaValidationError(
            "clues must cover every summary item exactly once."
        )

    return sorted(normalized, key=lambda item: item["summary_index"])


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
    if not isinstance(clue, list) or not clue:
        raise SchemaValidationError("clue must be a non-empty list.")

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
        t_id, score = _parse_clue_item(item)
        if t_id not in valid_t_ids:
            raise SchemaValidationError(f"clue references unknown t_id: {t_id}")

        previous = best_score_by_t_id.get(t_id)
        if previous is None or score > previous:
            best_score_by_t_id[t_id] = score

    ranked = sorted(
        best_score_by_t_id.items(),
        key=lambda entry: (-entry[1], t_id_order[entry[0]]),
    )
    selected = [t_id for t_id, _ in ranked[:top_k]]
    return sorted(selected, key=lambda t_id: t_id_order[t_id])


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