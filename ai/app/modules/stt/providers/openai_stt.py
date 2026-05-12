from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.exceptions import STTProcessingError


def transcribe(audio_path: str | Path, **_: Any) -> list[dict[str, Any]]:
    """Deprecated provider kept only to avoid accidental import surprises.

    Record Moment Picker currently uses Whisper-based local STT. Use one of:
    `whisper`, `whisperx`, or `faster_whisper`.
    """

    raise STTProcessingError(
        "OpenAI STT is not used in this project. Set STT_PROVIDER to whisper, whisperx, or faster_whisper."
    )
