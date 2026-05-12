from app.core.exceptions import PipelineError


def refine_text(stt_result: list[dict]) -> list[dict]:
    """
    Input:
    [
      {"time": 41, "text": "안냥하세요..."},
      {"time": 57, "text": "이 프로젝트는 생강보다..."}
    ]

    Output:
    [
      {"time": 41, "text": "안녕하세요..."},
      {"time": 57, "text": "이 프로젝트는 생각보다..."}
    ]
    """
    # TODO(refine_text 담당): STT 입력을 검증하고, refine_text.prompt로
    # llm_client를 호출한 뒤, refined-text 출력을 검증해서 list[dict]로 반환하기.
    raise PipelineError("refine_text service is not implemented yet.")
