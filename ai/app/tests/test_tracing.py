from __future__ import annotations

import logging
import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.core.tracing import LOGGER_NAME, request_context
from app.modules.stt import service as stt_service


def test_process_audio_logs_upload_and_completion(monkeypatch, caplog):
    from app import main

    final_result = [
        {
            "sid": "segment_01",
            "start_time": 0,
            "end_time": 3,
            "title": "Intro",
            "summary": ["Opening remarks"],
            "texts": [
                {
                    "t_id": "001",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
            "important": [],
            "clues": [{"summary_index": 0, "clue": ["001"]}],
        }
    ]

    def fake_run_pipeline(audio_path: str, _pipeline_settings):
        assert Path(audio_path).exists()
        return final_result

    monkeypatch.setattr(main, "run_pipeline", fake_run_pipeline)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    response = asyncio.run(
        main.process_audio(
            UploadFile(
                file=BytesIO(b"fake audio"),
                filename="sample.wav",
            ),
            pipeline_settings=None,
        )
    )

    assert response["status"] == "success"
    assert "event=process_audio_received" in caplog.text
    assert "filename=sample.wav" in caplog.text
    assert "event=process_audio_saved_temp" in caplog.text
    assert "event=stage_started stage=final_validation" in caplog.text
    assert "event=process_audio_completed" in caplog.text


def test_pipeline_logs_stages(monkeypatch, caplog):
    from app import pipeline

    monkeypatch.setattr(
        pipeline,
        "transcribe_audio",
        lambda _path, _options: [{"start_time": 0, "end_time": 3, "text": "Hello."}],
    )
    monkeypatch.setattr(
        pipeline,
        "refine_text",
        lambda _items, **_options: [
            {"t_id": "0001", "start_time": 0, "end_time": 3, "text": "Hello."}
        ],
    )
    monkeypatch.setattr(
        pipeline,
        "segment_text",
        lambda _items, **_options: [
            {
                "sid": "segment_01",
                "start_time": 0,
                "end_time": 3,
                "title": "Intro",
                "summary": ["Opening remarks"],
                "texts": [
                    {
                        "t_id": "0001",
                        "start_time": 0,
                        "end_time": 3,
                        "text": "Hello.",
                    }
                ],
                "important": [],
            }
        ],
    )
    monkeypatch.setattr(pipeline, "add_reasoning", lambda items, **_options: items)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    with request_context("req-test"):
        pipeline.run_pipeline("sample.wav")

    assert "[AI][req-test] event=stage_started stage=stt" in caplog.text
    assert "event=stage_result stage=stt items=1" in caplog.text
    assert "event=stage_started stage=segmenting" in caplog.text
    assert "event=stage_result stage=reasoning segments=1" in caplog.text


def test_stt_chunking_logs_chunk_progress(monkeypatch, tmp_path, caplog):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio")

    def fake_write_audio_chunk(*_args, **_kwargs):
        return None

    def fake_transcribe(_chunk_path):
        return [{"start_time": 0, "end_time": 2, "text": "Hello."}]

    monkeypatch.setattr(stt_service, "_write_audio_chunk", fake_write_audio_chunk)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    with request_context("chunk-test"):
        result = stt_service._transcribe_audio_chunks(
            audio_path,
            duration_seconds=65,
            transcribe=fake_transcribe,
            options=stt_service.ChunkingOptions(
                enabled=True,
                chunk_seconds=30,
                overlap_seconds=5,
                min_duration_seconds=30,
                command_timeout_seconds=10,
            ),
        )

    assert result
    assert "[AI][chunk-test] event=stt_chunking_started" in caplog.text
    assert "chunks=3" in caplog.text
    assert "event=stt_chunk_started chunk_index=0" in caplog.text
    assert "event=stt_chunk_completed chunk_index=2" in caplog.text
    assert "event=stt_chunking_completed" in caplog.text
