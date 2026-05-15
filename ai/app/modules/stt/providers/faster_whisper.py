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
    vad_filter: bool = True,
) -> list[dict[str, Any]]:
    """Transcribe audio with faster-whisper.

    Requires the `faster-whisper` package.
    """

    path = _validate_audio_path(audio_path)
    model_name = model_name or settings.whisper_model
    device = device or settings.whisper_device
    compute_type = compute_type or settings.whisper_compute_type

    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise STTProcessingError(
            "faster-whisper is not installed. Install `faster-whisper` to use STT_PROVIDER=faster_whisper."
        ) from error

    try:
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        segments, _info = model.transcribe(
            str(path),
            language=language,
            vad_filter=vad_filter,
        )
        items = [
            {
                "t_id": f"stt_{index + 1:03d}",
                "start_time": float(segment.start),
                "end_time": float(segment.end),
                "text": segment.text.strip(),
            }
            for segment in segments
            if segment.text.strip()
        ]
    except Exception as error:
        raise STTProcessingError(f"faster-whisper transcription failed: {error}") from error

    return [item.model_dump() for item in validate_stt_output(items)]


def _validate_audio_path(audio_path: str | Path) -> Path:
    path = Path(audio_path)
    if not path.exists():
        raise STTProcessingError(f"Audio file not found: {path}")
    if not path.is_file():
        raise STTProcessingError(f"Audio path is not a file: {path}")
    return path
