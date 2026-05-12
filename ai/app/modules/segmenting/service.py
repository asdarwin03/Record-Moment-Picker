from app.core.exceptions import PipelineError


def segment_text(refined_text: list[dict]) -> list[dict]:
    """
    Input:
    [
      {"time": 41, "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."}
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
            "time": 41,
            "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
          }
        ],
        "important": []
      }
    ]
    """
    # TODO(segmenting 담당): refined text 입력을 검증하고, segmenting.prompt로 llm_client를 호출한 뒤, structured segments를 검증해서 list[dict]로 반환하기.
    raise PipelineError("segmenting service is not implemented yet.")
