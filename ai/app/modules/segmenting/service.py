from app.core.exceptions import PipelineError
from app.clients.llm_client import default_llm_client, load_shared_schema
from app.schemas.refined_text import validate_refined_text_output
from app.schemas.segment import validate_structured_segments
from app.modules.segmenting.prompt import SEGMENT_TEXT_SYSTEM_PROMPT, MERGE_SEGMENTS_SYSTEM_PROMPT


OVERLAP_SIZE = 15
CHUNK_DURATION = 1800  # 30분 (초 단위)


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
            "t_id": "1",
            "start_time": 41,
            "end_time": 56,
            "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
          }
        ],
        "important": []
      }
    ]
    """
    # 1. 입력 검증
    refined_items = _validate_input(refined_text)

    # 2. t_id 부여
    refined_items = _assign_t_ids(refined_items)

    # 3. 청크 분할
    chunks = _split_into_chunks(refined_items)
    total_chunks = len(chunks)

    # 4. 청크가 1개면 바로 LLM 호출 후 반환
    if total_chunks == 1:
        segments = _call_segment_llm(
            chunk=chunks[0],
            previous_summary=None,
            chunk_index=0,
            total_chunks=1
        )
        segments = _post_process(segments, refined_items)
        segments = _assign_sids(segments)
        return _validate_output(segments, refined_items)

    # 5. 청크별 순차 처리
    chunk_results = []
    previous_summary = None

    for i, chunk in enumerate(chunks):
        result = _call_segment_llm(
            chunk=chunk,
            previous_summary=previous_summary,
            chunk_index=i,
            total_chunks=total_chunks
        )

        # 오버랩 발화 제거 (첫 번째 청크 제외)
        result = _remove_overlap_texts(result, chunk, is_first=(i == 0))

        chunk_results.append(result)

        # 마지막 청크는 previous_summary 추출 불필요
        if i < total_chunks - 1:
            previous_summary = {
                "last_segment_summary": result[-2]["summary"] if len(result) > 1 else None,
                "current_segment_summary": result[-1]["summary"]
            }

    # 6. 경계 세그먼트 병합
    merged_boundaries = _merge_boundaries(chunk_results)

    # 7. 전체 세그먼트 조립
    segments = _assemble_segments(chunk_results, merged_boundaries)

    # 8. 후처리
    segments = _post_process(segments, refined_items)

    # 9. sid 부여
    segments = _assign_sids(segments)

    # 10. 출력 검증
    return _validate_output(segments, refined_items)


# ── LLM 호출 ──────────────────────────────────────────

def _call_segment_llm(
    chunk: list[dict],
    previous_summary: dict | None,
    chunk_index: int,
    total_chunks: int
) -> list[dict]:
    system_prompt = SEGMENT_TEXT_SYSTEM_PROMPT

    # 청크 정보 추가
    system_prompt += (
        f"\n\n## Chunk Info"
        f"\n- chunk_index: {chunk_index}"
        f"\n- total_chunks: {total_chunks}"
    )

    if previous_summary:
        system_prompt += "\n\n## Previous Chunk Context"
        if previous_summary["last_segment_summary"] is not None:
            system_prompt += (
                f"\n[Previous segment summary: {previous_summary['last_segment_summary']}]"
            )
        system_prompt += (
            f"\n[Current segment in progress: {previous_summary['current_segment_summary']}]"
        )

    try:
        return default_llm_client.generate_json(
            system_prompt=system_prompt,
            user_payload={"items": chunk},
            schema=load_shared_schema("structured-segments.schema.json"),
            schema_name="structured_segments",
            max_output_tokens=8192,
        )
    except Exception as e:
        raise PipelineError(f"LLM 호출 실패: {e}")


# ── 오버랩 발화 제거 ────────────────────────────────────

def _remove_overlap_texts(
    chunk_result: list[dict],
    chunk: list[dict],
    is_first: bool
) -> list[dict]:
    if is_first:
        return chunk_result

    # 앞 오버랩 발화 t_id 추출 (청크의 첫 15개)
    overlap_t_ids = {
        item["t_id"]
        for item in chunk[:OVERLAP_SIZE]
    }

    cleaned_result = []
    for segment in chunk_result:
        cleaned_texts = [
            text_item for text_item in segment.get("texts", [])
            if text_item.get("t_id") not in overlap_t_ids
        ]
        # texts가 비어있는 세그먼트는 제거
        if not cleaned_texts:
            continue
        cleaned_result.append({**segment, "texts": cleaned_texts})

    return cleaned_result


# ── t_id 부여 ──────────────────────────────────────────

def _assign_t_ids(refined_items: list[dict]) -> list[dict]:
    for i, item in enumerate(refined_items):
        item["t_id"] = str(i + 1).zfill(4)
    return refined_items


# ── 청크 분할 ──────────────────────────────────────────

def _split_into_chunks(refined_items: list[dict]) -> list[list[dict]]:
    chunks = []
    start = 0

    while start < len(refined_items):
        end = start
        while end < len(refined_items):
            duration = refined_items[end]["start_time"] - refined_items[start]["start_time"]
            if duration >= CHUNK_DURATION:
                break
            end += 1

        # 단일 발화가 30분 초과하는 경우 무한루프 방지
        if end == start:
            end = start + 1

        overlap_start = max(0, start - OVERLAP_SIZE)
        overlap_end = min(len(refined_items), end + OVERLAP_SIZE)

        chunks.append(refined_items[overlap_start:overlap_end])
        start = end

    return chunks


# ── 경계 세그먼트 병합 ──────────────────────────────────

def _merge_boundaries(chunk_results: list[list[dict]]) -> list[list[dict]]:
    merged_boundaries = []

    for i in range(len(chunk_results) - 1):
        if not chunk_results[i]:
            raise PipelineError(f"chunk {i} 세그멘팅 결과가 비어 있습니다.")
        if not chunk_results[i + 1]:
            raise PipelineError(f"chunk {i + 1} 세그멘팅 결과가 비어 있습니다.")

        segment_a = chunk_results[i][-1]
        segment_b = chunk_results[i + 1][0]

        try:
            merged = default_llm_client.generate_json(
                system_prompt=MERGE_SEGMENTS_SYSTEM_PROMPT,
                user_payload={
                    "segment_a": segment_a,
                    "segment_b": segment_b,
                },
                schema=load_shared_schema("structured-segments.schema.json"),
                schema_name="merged_segments",
                max_output_tokens=4096,
            )
        except Exception as e:
            raise PipelineError(f"경계 세그먼트 병합 실패 (chunk {i} / {i + 1}): {e}")

        merged_boundaries.append(merged)

    return merged_boundaries


# ── 전체 세그먼트 조립 ──────────────────────────────────

def _assemble_segments(
    chunk_results: list[list[dict]],
    merged_boundaries: list[list[dict]]
) -> list[dict]:
    all_segments = []

    for i, chunk_result in enumerate(chunk_results):
        is_first = i == 0
        is_last = i == len(chunk_results) - 1

        if is_first:
            all_segments.extend(chunk_result[:-1])
        elif is_last:
            all_segments.extend(chunk_result[1:])
        else:
            all_segments.extend(chunk_result[1:-1])

    for merged in merged_boundaries:
        if isinstance(merged, list):
            all_segments.extend(merged)
        else:
            all_segments.append(merged)

    all_segments.sort(key=lambda x: float(x.get("start_time", 0)))

    return all_segments


# ── 후처리 ─────────────────────────────────────────────

def _post_process(segments: list[dict], refined_items: list[dict]) -> list[dict]:
    segments = _normalize_segment_boundaries(segments)
    segments = _restore_missing_utterances(segments, refined_items)
    return segments


# ── sid 재번호 부여 ──────────────────────────────────────

def _assign_sids(segments: list[dict]) -> list[dict]:
    for i, seg in enumerate(segments):
        seg["sid"] = f"segment_{str(i + 1).zfill(2)}"
    return segments


# ── 입력 검증 ──────────────────────────────────────────

def _validate_input(refined_text: list[dict]) -> list[dict]:
    if not refined_text:
        raise PipelineError("refined_text가 비어 있습니다.")

    try:
        validated_items = validate_refined_text_output(refined_text)
    except Exception as error:
        raise PipelineError(f"refined_text schema validation failed: {error}") from error

    return [item.model_dump() for item in validated_items]


# ── 출력 검증 ──────────────────────────────────────────

def _validate_output(segments: list[dict], refined_items: list[dict]) -> list[dict]:
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
    input_keys = {_utterance_key(item) for item in refined_items}
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
                "t_id": str(next_t_id),
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
            t_id = str(text_item.get("t_id", "")).zfill(4)
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