from __future__ import annotations

from typing import Any


class AIServiceError(Exception):
    """Base class for expected AI service failures."""

    code = "ai_service_error"
    status_code = 500
    default_message = "AI service error"

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)

    def to_response(self) -> dict[str, Any]:
        return {
            "status": "failed",
            "data": None,
            "message": self.message,
            "error": {
                "code": self.code,
                "details": self.details,
            },
        }


class ConfigurationError(AIServiceError):
    code = "configuration_error"
    status_code = 500
    default_message = "AI service configuration error"


class STTProcessingError(AIServiceError):
    code = "stt_processing_failed"
    status_code = 500
    default_message = "STT processing failed"


class LLMProcessingError(AIServiceError):
    code = "llm_processing_failed"
    status_code = 502
    default_message = "LLM processing failed"


class SchemaValidationError(AIServiceError):
    code = "schema_validation_failed"
    status_code = 422
    default_message = "Schema validation failed"


class PipelineError(AIServiceError):
    code = "pipeline_failed"
    status_code = 500
    default_message = "AI pipeline failed"
