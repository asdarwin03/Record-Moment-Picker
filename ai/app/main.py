import os
import json
import tempfile
import time
import traceback
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import AIServiceError, PipelineError, SchemaValidationError
from app.core.tracing import configure_logging, log_event, new_request_id, request_context, track_stage
from app.modules.reasoning.service import add_reasoning
from app.modules.refine_text.service import refine_text
from app.modules.segmenting.service import segment_text
from app.modules.stt.service import transcribe_audio
from app.pipeline import run_pipeline
from app.schemas.final_result import validate_final_result
from app.schemas.stt import STTItem, validate_stt_output

app = FastAPI()
configure_logging()


class ProcessTextRequest(BaseModel):
    items: list[STTItem] = Field(..., description="Timestamped transcript items.")


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(_request, exc: AIServiceError):
    print(f"[AIServiceError] {exc.code}: {exc.message}", flush=True)
    if exc.details:
        print(f"[AIServiceError details] {exc.details}", flush=True)
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


@app.exception_handler(Exception)
async def unexpected_error_handler(_request, exc: Exception):
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    return JSONResponse(
        status_code=500,
        content={
            "status": "failed",
            "data": None,
            "message": str(exc) or exc.__class__.__name__,
        },
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    request_id = new_request_id()
    started_at = time.perf_counter()
    audio_content = await file.read()

    with request_context(request_id):
        log_event(
            "process_audio_received",
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=len(audio_content),
            size_mb=len(audio_content) / 1024 / 1024,
            pipeline_mode=settings.ai_pipeline_mode,
        )

        if len(audio_content) > settings.max_audio_upload_bytes:
            max_mb = settings.max_audio_upload_bytes / 1024 / 1024
            log_event(
                "process_audio_rejected",
                reason="file_too_large",
                max_mb=max_mb,
            )
            raise PipelineError(
                f"Audio file is too large for local processing. "
                f"Current limit is {max_mb:.0f} MB. "
                "Shorten the audio or increase AI_MAX_AUDIO_UPLOAD_BYTES in .env."
            )

        if settings.ai_pipeline_mode == "demo":
            with track_stage("demo_result"):
                final_json = _load_demo_result()
                final_json = _ensure_final_result(final_json)
            log_event(
                "process_audio_completed",
                segments=len(final_json),
                elapsed_seconds=time.perf_counter() - started_at,
            )
            return {
                "status": "success",
                "data": final_json,
                "message": "AI_PIPELINE_MODE=demo: returned bundled sample result.",
            }

        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp:
            temp.write(audio_content)
            temp_path = temp.name

        log_event("process_audio_saved_temp", temp_path=temp_path)

        try:
            final_json = await run_in_threadpool(run_pipeline, temp_path)
            with track_stage("final_validation", input_segments=len(final_json)):
                final_json = _ensure_final_result(final_json)
        except Exception as error:
            log_event(
                "process_audio_failed",
                elapsed_seconds=time.perf_counter() - started_at,
                error_type=error.__class__.__name__,
                error=str(error),
            )
            raise
        finally:
            try:
                os.unlink(temp_path)
                log_event("process_audio_temp_deleted", temp_path=temp_path)
            except OSError as error:
                log_event(
                    "process_audio_temp_delete_failed",
                    temp_path=temp_path,
                    error=str(error),
                )

        log_event(
            "process_audio_completed",
            segments=len(final_json),
            elapsed_seconds=time.perf_counter() - started_at,
        )
        return {
            "status": "success",
            "data": final_json,
            "message": None,
        }


@app.post("/process-stt")
async def process_stt(file: UploadFile = File(...)):
    temp_path = await _save_upload_to_temp_file(file)

    try:
        stt_items = await run_in_threadpool(transcribe_audio, temp_path)
        stt_items = [item.model_dump() for item in validate_stt_output(stt_items)]
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    return {
        "status": "success",
        "data": stt_items,
        "message": None,
    }


@app.post("/process-text")
async def process_text(payload: ProcessTextRequest):
    request_id = new_request_id()

    with request_context(request_id):
        stt_items = [item.model_dump() for item in validate_stt_output(payload.items)]
        log_event("process_text_received", items=len(stt_items))

        with track_stage("refine_text", input_items=len(stt_items)):
            refined_result = _ensure_stage_result(refine_text(stt_items), "refine_text")
            log_event("stage_result", stage="refine_text", items=len(refined_result))

        with track_stage("segmenting", input_items=len(refined_result)):
            structured_segments = _ensure_stage_result(segment_text(refined_result), "segmenting")
            log_event("stage_result", stage="segmenting", segments=len(structured_segments))

        with track_stage("reasoning", input_segments=len(structured_segments)):
            final_json = _ensure_final_result(add_reasoning(structured_segments))
            log_event("stage_result", stage="reasoning", segments=len(final_json))

        log_event("process_text_completed", segments=len(final_json))

    return {
        "status": "success",
        "data": final_json,
        "message": None,
    }


def _ensure_stage_result(result: Any, stage: str) -> list[dict[str, Any]]:
    if not isinstance(result, list):
        raise PipelineError(f"{stage} stage is not implemented yet.")
    return result


def _ensure_final_result(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, list):
        raise PipelineError("Final result pipeline is not implemented yet.")

    try:
        return [segment.model_dump() for segment in validate_final_result(result)]
    except Exception as error:
        raise SchemaValidationError("Final result schema validation failed.") from error


def _load_demo_result() -> list[dict[str, Any]]:
    demo_path = settings.repo_root / "shared" / "examples" / "final-result.cross-topic-evidence.example.json"
    fallback_path = settings.repo_root / "shared" / "examples" / "final-result.example.json"
    source_path = demo_path if demo_path.exists() else fallback_path

    with source_path.open("r", encoding="utf-8") as file:
        return _normalize_legacy_transcript_times(json.load(file))


def _normalize_legacy_transcript_times(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_segments = []
    for segment_index, segment in enumerate(segments):
        normalized_segment = dict(segment)
        next_segment_start = segments[segment_index + 1].get("start_time") if segment_index + 1 < len(segments) else None
        texts = []
        for text_index, text in enumerate(segment.get("texts", [])):
            normalized_text = dict(text)
            if "time" in normalized_text and "start_time" not in normalized_text:
                normalized_text["start_time"] = normalized_text.pop("time")

            if "end_time" not in normalized_text:
                next_text = segment["texts"][text_index + 1] if text_index + 1 < len(segment.get("texts", [])) else None
                if next_text is not None:
                    normalized_text["end_time"] = next_text.get("start_time", next_text.get("time", normalized_text["start_time"]))
                elif isinstance(next_segment_start, (int, float)):
                    normalized_text["end_time"] = next_segment_start
                else:
                    normalized_text["end_time"] = normalized_segment.get("end_time", normalized_text["start_time"])

            texts.append(normalized_text)

        normalized_segment["texts"] = texts
        if texts:
            normalized_segment["start_time"] = min(text["start_time"] for text in texts)
            normalized_segment["end_time"] = max(text["end_time"] for text in texts)
        normalized_segments.append(normalized_segment)

    return normalized_segments


async def _save_upload_to_temp_file(file: UploadFile) -> str:
    audio_content = await file.read()

    if len(audio_content) > settings.max_audio_upload_bytes:
        max_mb = settings.max_audio_upload_bytes / 1024 / 1024
        raise PipelineError(
            f"Audio file is too large for local processing. "
            f"Current limit is {max_mb:.0f} MB. "
            "Shorten the audio or increase AI_MAX_AUDIO_UPLOAD_BYTES in .env."
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp:
        temp.write(audio_content)
        return temp.name
