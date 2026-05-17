from app.core.exceptions import PipelineError
from app.clients.llm_client import default_llm_client
from app.schemas.refined_text import validate_refined_text_output
from app.schemas.segment import validate_structured_segments


def segment_text(refined_text: list[dict]) -> list[dict]:
    """
    Input:
    [
      {
        "start_time": 41,
        "end_time": 56,
        "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
      }
    ]

    Output:
    [
      {
        "sid": "segment_01",
        "start_time": 41,
        "end_time": 81,
        "title": "프로젝트 설명 시작",
        "summary": ["Record Moment Picker 발표가 시작됨"],
        "texts": [
          {
            "t_id": "001",
            "start_time": 41,
            "end_time": 56,
            "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
          }
        ],
        "important": []
      }
    ]
    """
    refined_items = _validate_input(refined_text)

    try:
        segments = default_llm_client.segment_text(refined_items)
    except Exception as e:
        raise PipelineError(f"LLM 호출 실패: {e}")

    normalized_segments = _normalize_segment_boundaries(segments)
    normalized_segments = _restore_missing_utterances(normalized_segments, refined_items)
    return _validate_output(normalized_segments, refined_items)


# ── 입력 검증 ──

def _validate_input(refined_text: list[dict]) -> list[dict]:
    if not refined_text:
        raise PipelineError("refined_text가 비어 있습니다.")

    try:
        validated_items = validate_refined_text_output(refined_text)
    except Exception as error:
        raise PipelineError(f"refined_text schema validation failed: {error}") from error

    return [item.model_dump() for item in validated_items]


# ── 출력 검증 ──────────────────────────────────────────

def _validate_output(segments: list[dict], refined_text: list[dict]) -> list[dict]:
    try:
        validated_segments = validate_structured_segments(segments)
    except Exception as error:
        raise PipelineError(f"structured segments schema validation failed: {error}") from error

    segment_dicts = [segment.model_dump() for segment in validated_segments]
    covered_keys = {
        _utterance_key(text_item)
        for segment in segment_dicts
        for text_item in segment["texts"]
    }
    input_keys = {_utterance_key(item) for item in refined_text}
    missing_keys = input_keys - covered_keys

    if missing_keys:
        raise PipelineError(
            f"세그먼트에 포함되지 않은 발화가 있습니다: {sorted(missing_keys)}"
        )

    return segment_dicts


def _normalize_segment_boundaries(segments: list[dict]) -> list[dict]:
    normalized_segments = [dict(segment) for segment in segments]

    for segment in normalized_segments:
        texts = segment.get("texts", [])
        text_start_times = [
            float(text_item["start_time"])
            for text_item in texts
            if "start_time" in text_item
        ]
        text_end_times = [
            float(text_item["end_time"])
            for text_item in texts
            if "end_time" in text_item
        ]

        if not text_start_times or not text_end_times:
            continue

        segment["start_time"] = min(text_start_times)
        segment["end_time"] = max(text_end_times)

    return normalized_segments


def _restore_missing_utterances(segments: list[dict], refined_text: list[dict]) -> list[dict]:
    """Add back transcript utterances the LLM omitted while segmenting.

    LLMs are good at finding topic boundaries but can drop short utterances when
    asked to copy every transcript row. The service keeps the LLM's topic
    choices, then deterministically restores missing rows into the segment whose
    time range best fits the utterance.
    """
    restored_segments = [dict(segment) for segment in segments]
    covered_keys = {
        _utterance_key(text_item)
        for segment in restored_segments
        for text_item in segment.get("texts", [])
    }
    next_t_id = _next_transcript_id(restored_segments)

    for item in refined_text:
        item_key = _utterance_key(item)
        if item_key in covered_keys:
            continue

        target_segment = _find_best_segment_for_utterance(restored_segments, item)
        target_segment.setdefault("texts", []).append(
            {
                "t_id": f"{next_t_id:03d}",
                "start_time": item["start_time"],
                "end_time": item["end_time"],
                "text": item["text"],
            }
        )
        next_t_id += 1
        covered_keys.add(item_key)

    for segment in restored_segments:
        segment["texts"] = sorted(
            segment.get("texts", []),
            key=lambda text_item: (text_item["start_time"], text_item["end_time"]),
        )

    return _dedupe_segment_texts(_normalize_segment_boundaries(restored_segments))


def _dedupe_segment_texts(segments: list[dict]) -> list[dict]:
    seen_keys = set()
    deduped_segments = []

    for segment in segments:
        deduped_texts = []
        for text_item in segment.get("texts", []):
            key = _utterance_key(text_item)
            if key in seen_keys:
                continue

            seen_keys.add(key)
            deduped_texts.append(text_item)

        deduped_segments.append({**segment, "texts": deduped_texts})

    return _normalize_segment_boundaries(deduped_segments)


def _utterance_key(item: dict) -> tuple[float, str]:
    return (
        round(float(item.get("start_time", 0)), 2),
        _normalize_text(str(item.get("text", ""))),
    )


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _next_transcript_id(segments: list[dict]) -> int:
    max_id = 0
    for segment in segments:
        for text_item in segment.get("texts", []):
            t_id = str(text_item.get("t_id", ""))
            if t_id.isdigit():
                max_id = max(max_id, int(t_id))

    return max_id + 1


def _find_best_segment_for_utterance(segments: list[dict], utterance: dict) -> dict:
    if not segments:
        raise PipelineError("segmenting result is empty.")

    utterance_midpoint = (utterance["start_time"] + utterance["end_time"]) / 2

    def score(segment: dict) -> tuple[float, float]:
        start_time = float(segment.get("start_time", 0))
        end_time = float(segment.get("end_time", start_time))

        if start_time <= utterance_midpoint <= end_time:
            return (0, end_time - start_time)

        distance = min(
            abs(utterance_midpoint - start_time),
            abs(utterance_midpoint - end_time),
        )
        return (distance, end_time - start_time)

    return min(segments, key=score)
        
# TODO(segmenting 담당): refined text 입력을 검증하고, segmenting.prompt로 llm_client를 호출한 뒤, structured segments를 검증해서 list[dict]로 반환하기.
