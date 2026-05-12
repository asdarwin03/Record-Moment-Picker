from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import STTProcessingError
from app.modules.stt.providers import openai_stt
from app.schemas.stt import validate_stt_output


def test_stt_sample_contract():
    sample_path = Path(__file__).resolve().parents[3] / "ai" / "samples" / "stt_output.json"
    import json

    with sample_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    result = validate_stt_output(data)
    assert result
    assert all(item.time >= 0 for item in result)
    assert all(item.text for item in result)


def test_openai_stt_provider_is_disabled_for_this_project(tmp_path):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio")

    with pytest.raises(STTProcessingError, match="OpenAI STT is not used"):
        openai_stt.transcribe(audio_path)
