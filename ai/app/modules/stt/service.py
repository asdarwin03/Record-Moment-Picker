from pathlib import Path

from app.core.exceptions import STTProcessingError


def transcribe_audio(audio_path: str | Path) -> list[dict]:
    """
    Input:
    audio file path

    Output:
    [
      {"time": 41, "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."}
    ]
    """
    # TODO(stt 담당): settings.stt_provider 값에 따라 whisper, whisperx, faster_whisper provider 중 하나를 선택해서 호출하기.
    # TODO(stt 담당): provider 결과를 shared/schemas/stt-output.schema.json에 맞게 검증하고 list[dict]로 반환하기.
    raise STTProcessingError("STT service is not implemented yet.")
