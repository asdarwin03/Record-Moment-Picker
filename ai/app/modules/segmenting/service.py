from app.core.exceptions import PipelineError
from app.clients.llm_client import default_llm_client


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
    _validate_input(refined_text)

    try:
        segments = default_llm_client.segment_text(refined_text)
    except Exception as e:
        raise PipelineError(f"LLM 호출 실패: {e}")

    _validate_output(segments, refined_text)

    return segments


# ── 입력 검증 ──

def _validate_input(refined_text: list[dict]) -> None:
    if not refined_text:
        raise PipelineError("refined_text가 비어 있습니다.")

    for i, item in enumerate(refined_text):
        for field in ("start_time", "end_time", "text"):
            if field not in item:
                raise PipelineError(
                    f"refined_text[{i}]에 '{field}' 필드가 없습니다: {item}"
                )
        if not isinstance(item["start_time"], int):
            raise PipelineError(
                f"refined_text[{i}]['start_time']이 정수가 아닙니다: {item['start_time']}"
            )
        if not isinstance(item["end_time"], int):
            raise PipelineError(
                f"refined_text[{i}]['end_time']이 정수가 아닙니다: {item['end_time']}"
            )
        if item["start_time"] >= item["end_time"]:
            raise PipelineError(
                f"refined_text[{i}]의 start_time({item['start_time']}) >= "
                f"end_time({item['end_time']})"
            )


# ── 출력 검증 ──────────────────────────────────────────

def _validate_output(segments: list[dict], refined_text: list[dict]) -> None:
    required_keys = {"sid", "start_time", "end_time", "title", "summary", "texts", "important"}
    seen_t_ids = set()
    covered_start_times = set()

    for i, seg in enumerate(segments):
        # 필수 필드 누락 검사
        missing = required_keys - seg.keys()
        if missing:
            raise PipelineError(
                f"{seg.get('sid', f'segment[{i}]')}에 필드 누락: {missing}"
            )

        # end_time 겹침 검사
        if i < len(segments) - 1:
            next_start = segments[i + 1]["start_time"]
            if seg["end_time"] >= next_start:
                raise PipelineError(
                    f"{seg['sid']}.end_time({seg['end_time']}) >= "
                    f"{segments[i + 1]['sid']}.start_time({next_start})"
                )

        for text_item in seg["texts"]:
            # t_id 존재 검사
            t_id = text_item.get("t_id")
            if not t_id:
                raise PipelineError(
                    f"{seg['sid']}의 text 항목에 t_id 없음: {text_item}"
                )
            # t_id 전역 고유 검사
            if t_id in seen_t_ids:
                raise PipelineError(
                    f"t_id 중복 발견: {t_id} (segment: {seg['sid']})"
                )
            seen_t_ids.add(t_id)

            # texts 내 필수 필드 검사
            for field in ("start_time", "end_time", "text"):
                if field not in text_item:
                    raise PipelineError(
                        f"{seg['sid']}의 text 항목에 '{field}' 필드 없음: {text_item}"
                    )

            covered_start_times.add(text_item["start_time"])

    # 발화 누락 검사
    input_start_times = {item["start_time"] for item in refined_text}
    missing_times = input_start_times - covered_start_times
    if missing_times:
        raise PipelineError(
            f"세그먼트에 포함되지 않은 발화가 있습니다 (start_time): {sorted(missing_times)}"
        )
        
# TODO(segmenting 담당): refined text 입력을 검증하고, segmenting.prompt로 llm_client를 호출한 뒤, structured segments를 검증해서 list[dict]로 반환하기.
