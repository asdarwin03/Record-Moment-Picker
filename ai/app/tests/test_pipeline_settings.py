from __future__ import annotations

import json

import pytest

from app.core.pipeline_settings import (
    PipelineSettings,
    default_pipeline_settings,
    processing_options,
)
from app.main import _parse_pipeline_settings


def test_processing_options_uses_env_defaults_and_allowlists():
    payload = processing_options()

    assert payload["defaults"]["stt"]["model"]
    assert payload["defaults"]["refine"]["model"]
    assert payload["defaults"]["segmenting"]["model"]
    assert payload["defaults"]["reasoning"]["model"]
    assert payload["defaults"]["stt"]["model"] in payload["options"]["sttModels"]
    assert payload["defaults"]["refine"]["model"] in payload["options"]["llmModels"]


def test_pipeline_settings_accepts_camel_case_upload_payload():
    payload = default_pipeline_settings().model_dump(by_alias=True)
    payload["stt"]["chunkSeconds"] = 420
    payload["segmenting"]["chunkSeconds"] = 240

    parsed = PipelineSettings.model_validate(payload)

    assert parsed.stt.chunk_seconds == 420
    assert parsed.segmenting.chunk_seconds == 240


def test_parse_pipeline_settings_uses_defaults_when_omitted():
    assert _parse_pipeline_settings(None) == default_pipeline_settings()


def test_parse_pipeline_settings_rejects_unknown_model():
    payload = default_pipeline_settings().model_dump(by_alias=True)
    payload["reasoning"]["model"] = "not-supported"

    with pytest.raises(Exception, match="Pipeline settings validation failed"):
        _parse_pipeline_settings(json.dumps(payload))
