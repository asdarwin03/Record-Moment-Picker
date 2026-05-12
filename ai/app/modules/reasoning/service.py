from app.core.exceptions import PipelineError


def add_reasoning(structured_segments: list[dict]) -> list[dict]:
    """
    Input:
    [
      {
        "sid": "segment_01",
        "summary": ["Record Moment Picker 발표가 시작됨"],
        "texts": [
          {
            "t_id": "001",
            "time": 41,
            "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
          }
        ]
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
            "time": 41,
            "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
          }
        ],
        "important": [],
        "clues": [
          {
            "summary_index": 0,
            "clue": ["001"]
          }
        ]
      }
    ]
    """
    # TODO(reasoning 담당): structured segments 입력을 검증하고, reasoning.prompt로
    # llm_client를 호출한 뒤, final result를 검증해서 list[dict]로 반환하기.
    raise PipelineError("reasoning service is not implemented yet.")
