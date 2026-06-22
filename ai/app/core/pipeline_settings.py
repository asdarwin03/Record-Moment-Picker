from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class RuntimeModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class STTPipelineSettings(RuntimeModel):
    provider: str = settings.stt_provider
    model: str = settings.whisper_model
    device: str = settings.whisper_device
    compute_type: str = settings.whisper_compute_type
    preprocessing_enabled: bool = True
    chunking_enabled: bool = settings.stt_chunking_enabled
    chunk_seconds: float = Field(default=settings.stt_chunk_seconds, ge=30, le=3600)
    overlap_seconds: float = Field(
        default=settings.stt_chunk_overlap_seconds,
        ge=0,
        le=120,
    )
    min_duration_seconds: float = Field(
        default=settings.stt_chunk_min_duration_seconds,
        ge=30,
        le=14400,
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in settings.stt_provider_options:
            raise ValueError("unsupported STT provider")
        return normalized

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if value not in settings.stt_model_options:
            raise ValueError("unsupported STT model")
        return value

    @field_validator("device")
    @classmethod
    def validate_device(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in settings.stt_device_options:
            raise ValueError("device must be cpu or cuda")
        return normalized

    @field_validator("compute_type")
    @classmethod
    def validate_compute_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"int8", "float16", "float32"}:
            raise ValueError("unsupported compute type")
        return normalized


class LLMPipelineSettings(RuntimeModel):
    model: str = settings.openai_model
    temperature: float = Field(default=settings.llm_temperature, ge=0, le=2)
    max_output_tokens: int = Field(default=4096, ge=256, le=65536)

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if value not in settings.llm_model_options:
            raise ValueError("unsupported LLM model")
        return value


class SegmentingPipelineSettings(LLMPipelineSettings):
    chunk_seconds: int = Field(default=settings.llm_segment_chunk_seconds, ge=60, le=3600)
    merge_max_output_tokens: int = Field(
        default=settings.llm_merge_max_output_tokens,
        ge=256,
        le=65536,
    )


class PipelineSettings(RuntimeModel):
    stt: STTPipelineSettings
    refine: LLMPipelineSettings
    segmenting: SegmentingPipelineSettings
    reasoning: LLMPipelineSettings


def default_pipeline_settings() -> PipelineSettings:
    return PipelineSettings(
        stt=STTPipelineSettings(
            provider=settings.stt_provider,
            model=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        ),
        refine=LLMPipelineSettings(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_refine_max_output_tokens,
        ),
        segmenting=SegmentingPipelineSettings(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_segment_max_output_tokens,
            chunk_seconds=settings.llm_segment_chunk_seconds,
            merge_max_output_tokens=settings.llm_merge_max_output_tokens,
        ),
        reasoning=LLMPipelineSettings(
            model=settings.openai_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_reasoning_max_output_tokens,
        ),
    )


def processing_options() -> dict:
    return {
        "defaults": default_pipeline_settings().model_dump(by_alias=True),
        "options": {
            "sttProviders": list(settings.stt_provider_options),
            "sttModels": list(settings.stt_model_options),
            "sttDevices": list(settings.stt_device_options),
            "sttComputeTypes": ["int8", "float16", "float32"],
            "llmModels": list(settings.llm_model_options),
        },
    }
