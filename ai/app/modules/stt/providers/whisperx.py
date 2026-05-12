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
    compute_type: str | None = None,
    language: str | None = "ko",
    batch_size: int = 16,
) -> list[dict[str, Any]]:
    """Transcribe audio with WhisperX.

    This returns segment-level timestamps. Word alignment can be added later if
    the UI needs word-level evidence.
    """

    path = _validate_audio_path(audio_path)
    model_name = model_name or settings.whisper_model
    device = device or settings.whisper_device
    compute_type = compute_type or settings.whisper_compute_type

    try:
        import whisperx
    except ImportError as error:
        raise STTProcessingError(
            "whisperx is not installed. Install `whisperx` to use STT_PROVIDER=whisperx."
        ) from error

    try:
        model = whisperx.load_model(
            model_name,
            device,
            compute_type=compute_type,
            language=language,
        )
        result = model.transcribe(str(path), batch_size=batch_size)
    except Exception as error:
        raise STTProcessingError(f"WhisperX transcription failed: {error}") from error

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
