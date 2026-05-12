from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.exceptions import STTProcessingError
from app.schemas.stt import validate_stt_output


def transcribe(
    audio_path: str | Path,
    *,
    model_name: str | None = None,
    device: str | None = None,
    language: str | None = "ko",
) -> list[dict[str, Any]]:
    """Transcribe audio with the open-source OpenAI Whisper package.

    Requires the `openai-whisper` package and ffmpeg to be installed.
    """

    path = _validate_audio_path(audio_path)
    model_name = model_name or settings.whisper_model
    device = device or settings.whisper_device

    try:
        import whisper
    except ImportError as error:
        raise STTProcessingError(
            "openai-whisper is not installed. Install `openai-whisper` to use STT_PROVIDER=whisper."
        ) from error

    try:
        model = whisper.load_model(model_name, device=device)
        result = model.transcribe(str(path), language=language)
    except Exception as error:
        raise STTProcessingError(f"Whisper transcription failed: {error}") from error

    items = [
        {
            "time": float(segment.get("start", 0.0)),
            "text": str(segment.get("text", "")).strip(),
        }
        for segment in result.get("segments", [])
        if str(segment.get("text", "")).strip()
    ]

    return [item.model_dump() for item in validate_stt_output(items)]


def _validate_audio_path(audio_path: str | Path) -> Path:
    path = Path(audio_path)
    if not path.exists():
        raise STTProcessingError(f"Audio file not found: {path}")
    if not path.is_file():
        raise STTProcessingError(f"Audio path is not a file: {path}")
    return path
