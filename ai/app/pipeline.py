from app.clients.llm_client import LLMClient, LLMClientConfig
from app.core.config import settings
from app.core.pipeline_settings import (
    LLMPipelineSettings,
    PipelineSettings,
    default_pipeline_settings,
)
from app.modules.stt.service import STTRuntimeOptions
from app.modules.stt.service import transcribe_audio
from app.modules.refine_text.service import refine_text
from app.modules.segmenting.service import segment_text
from app.modules.reasoning.service import add_reasoning
from app.core.tracing import log_event, track_stage

def run_pipeline(
    audio_path: str,
    pipeline_settings: PipelineSettings | None = None,
) -> list[dict]:
    runtime_settings = pipeline_settings or default_pipeline_settings()
    refine_client = _create_llm_client(runtime_settings.refine)
    segmenting_client = _create_llm_client(runtime_settings.segmenting)
    reasoning_client = _create_llm_client(runtime_settings.reasoning)

    with track_stage("stt", audio_path=audio_path):
        stt_result = transcribe_audio(
            audio_path,
            STTRuntimeOptions(
                provider=runtime_settings.stt.provider,
                model_name=runtime_settings.stt.model,
                device=runtime_settings.stt.device,
                compute_type=runtime_settings.stt.compute_type,
                chunking_enabled=runtime_settings.stt.chunking_enabled,
                chunk_seconds=runtime_settings.stt.chunk_seconds,
                overlap_seconds=runtime_settings.stt.overlap_seconds,
                min_duration_seconds=runtime_settings.stt.min_duration_seconds,
            ),
        )
        log_event("stage_result", stage="stt", items=len(stt_result))

    with track_stage("refine_text", input_items=len(stt_result)):
        refined_result = refine_text(stt_result, llm_client=refine_client)
        log_event("stage_result", stage="refine_text", items=len(refined_result))

    with track_stage("segmenting", input_items=len(refined_result)):
        structured_segments = segment_text(
            refined_result,
            llm_client=segmenting_client,
            chunk_seconds=runtime_settings.segmenting.chunk_seconds,
            max_output_tokens=runtime_settings.segmenting.max_output_tokens,
            merge_max_output_tokens=runtime_settings.segmenting.merge_max_output_tokens,
        )
        segment_text_count = sum(len(segment.get("texts", [])) for segment in structured_segments)
        log_event(
            "stage_result",
            stage="segmenting",
            segments=len(structured_segments),
            texts=segment_text_count,
        )

    with track_stage("reasoning", input_segments=len(structured_segments)):
        final_result = add_reasoning(
            structured_segments,
            llm_client=reasoning_client,
            max_output_tokens=runtime_settings.reasoning.max_output_tokens,
        )
        log_event("stage_result", stage="reasoning", segments=len(final_result))

    return final_result


def _create_llm_client(stage_settings: LLMPipelineSettings) -> LLMClient:
    return LLMClient(
        LLMClientConfig(
            api_key=settings.openai_api_key,
            model=stage_settings.model,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            temperature=stage_settings.temperature,
            refine_max_output_tokens=stage_settings.max_output_tokens,
        )
    )
