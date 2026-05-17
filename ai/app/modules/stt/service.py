from pathlib import Path
from typing import Callable

from app.core.config import settings
from app.core.exceptions import STTProcessingError
from app.schemas.stt import validate_stt_output
from app.modules.stt.providers import faster_whisper, openai_stt, whisper, whisperx


ProviderTranscribe = Callable[[str | Path], list[dict]]


_PROVIDER_MAP: dict[str, ProviderTranscribe] = {
    "whisper": whisper.transcribe,
    "whisperx": whisperx.transcribe,
    "faster_whisper": faster_whisper.transcribe,
    "faster-whisper": faster_whisper.transcribe,
    "openai_stt": openai_stt.transcribe,
    "openai-stt": openai_stt.transcribe,
}


def transcribe_audio(audio_path: str | Path) -> list[dict]:
    """
    Input:
    audio file path

    Output:
    [
      {
        "start_time": 41,
        "end_time": 56,
        "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
      }
    ]
    """
    provider_name = settings.stt_provider
    transcribe = _get_provider(provider_name)

    try:
        stt_output = transcribe(audio_path)
        validated_output = validate_stt_output(stt_output)
        return [item.model_dump() for item in validated_output]
    except STTProcessingError:
        raise
    except Exception as error:
        raise STTProcessingError(f"STT processing failed with provider '{provider_name}': {error}") from error


def _get_provider(provider_name: str) -> ProviderTranscribe:
    normalized_name = provider_name.strip().lower()

    if normalized_name not in _PROVIDER_MAP:
        available = ", ".join(sorted(_PROVIDER_MAP))
        raise STTProcessingError(
            f"Unsupported STT provider: {provider_name}. Available providers: {available}"
        )

    return _PROVIDER_MAP[normalized_name]
