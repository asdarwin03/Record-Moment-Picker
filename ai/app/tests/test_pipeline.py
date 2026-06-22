from __future__ import annotations

import json
import importlib
from pathlib import Path

from app.schemas.final_result import validate_final_result
from app.core.pipeline_settings import default_pipeline_settings


SAMPLES = Path(__file__).resolve().parents[3] / "ai" / "samples"


def load_json(filename: str):
    with (SAMPLES / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_run_pipeline_calls_steps_in_order_and_returns_final_result(monkeypatch, tmp_path):
    calls: list[str] = []
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio")

    stt_output = load_json("stt_output.json")
    refined_text = load_json("refined_text.json")
    structured_segments = load_json("structured_segments.json")
    final_result = load_json("final_result.json")

    runtime_settings = default_pipeline_settings()
    runtime_settings.refine.model = "gpt-4.1"
    runtime_settings.segmenting.model = "gpt-4o-mini"

    def fake_transcribe_audio(path: str, runtime_options):
        calls.append(f"stt:{Path(path).name}")
        assert runtime_options.model_name == runtime_settings.stt.model
        return stt_output

    def fake_refine_text(items: list[dict], *, llm_client):
        calls.append("refine")
        assert items == stt_output
        assert llm_client.config.model == "gpt-4.1"
        return refined_text

    def fake_segment_text(items: list[dict], **options):
        calls.append("segment")
        assert items == refined_text
        assert options["llm_client"].config.model == "gpt-4o-mini"
        assert options["chunk_seconds"] > 0
        return structured_segments

    def fake_add_reasoning(items: list[dict], **options):
        calls.append("reasoning")
        assert items == structured_segments
        assert options["max_output_tokens"] > 0
        return final_result

    import app.modules.stt.service as stt_service

    monkeypatch.setattr(stt_service, "transcribe_audio", fake_transcribe_audio, raising=False)
    pipeline = importlib.import_module("app.pipeline")
    monkeypatch.setattr(pipeline, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(pipeline, "refine_text", fake_refine_text)
    monkeypatch.setattr(pipeline, "segment_text", fake_segment_text)
    monkeypatch.setattr(pipeline, "add_reasoning", fake_add_reasoning)

    result = pipeline.run_pipeline(str(audio_path), runtime_settings)

    assert calls == ["stt:sample.wav", "refine", "segment", "reasoning"]
    assert result == final_result
    validate_final_result(result)
