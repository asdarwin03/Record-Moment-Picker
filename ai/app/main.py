import tempfile
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.exceptions import AIServiceError, PipelineError, SchemaValidationError
from app.modules.reasoning.service import add_reasoning
from app.modules.refine_text.service import refine_text
from app.modules.segmenting.service import segment_text
from app.pipeline import run_pipeline
from app.schemas.final_result import validate_final_result
from app.schemas.stt import STTItem, validate_stt_output

app = FastAPI()


class ProcessTextRequest(BaseModel):
    items: list[STTItem] = Field(..., description="Timestamped transcript items.")


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(_request, exc: AIServiceError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp:
        temp.write(await file.read())
        temp_path = temp.name

    final_json = run_pipeline(temp_path)
    final_json = _ensure_final_result(final_json)

    return {
        "status": "success",
        "data": final_json,
        "message": None,
    }


@app.post("/process-text")
async def process_text(payload: ProcessTextRequest):
    stt_items = [item.model_dump() for item in validate_stt_output(payload.items)]

    refined_result = _ensure_stage_result(refine_text(stt_items), "refine_text")
    structured_segments = _ensure_stage_result(segment_text(refined_result), "segmenting")
    final_json = _ensure_final_result(add_reasoning(structured_segments))

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
