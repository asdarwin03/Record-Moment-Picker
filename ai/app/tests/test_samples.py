from __future__ import annotations

import json
from pathlib import Path

from app.schemas.final_result import validate_final_result
from app.schemas.refined_text import validate_refined_text_output
from app.schemas.segment import validate_structured_segments
from app.schemas.stt import validate_stt_output


REPO_ROOT = Path(__file__).resolve().parents[3]
AI_SAMPLES = REPO_ROOT / "ai" / "samples"
SHARED_EXAMPLES = REPO_ROOT / "shared" / "examples"
SHARED_SCHEMAS = REPO_ROOT / "shared" / "schemas"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_shared_schema_files_are_valid_json():
    for path in SHARED_SCHEMAS.glob("*.json"):
        assert load_json(path)


def test_ai_samples_validate_against_pydantic_contracts():
    validate_stt_output(load_json(AI_SAMPLES / "stt_output.json"))
    validate_refined_text_output(load_json(AI_SAMPLES / "refined_text.json"))
    validate_structured_segments(load_json(AI_SAMPLES / "structured_segments.json"))
    validate_final_result(load_json(AI_SAMPLES / "final_result.json"))


def test_shared_examples_validate_against_pydantic_contracts():
    validate_stt_output(load_json(SHARED_EXAMPLES / "stt-output.example.json"))
    validate_refined_text_output(load_json(SHARED_EXAMPLES / "refined-text.example.json"))
    validate_structured_segments(load_json(SHARED_EXAMPLES / "structured-segments.example.json"))
    validate_final_result(load_json(SHARED_EXAMPLES / "final-result.example.json"))


def test_ai_samples_match_shared_examples_for_current_mvp_fixture():
    pairs = [
        ("stt_output.json", "stt-output.example.json"),
        ("refined_text.json", "refined-text.example.json"),
        ("structured_segments.json", "structured-segments.example.json"),
        ("final_result.json", "final-result.example.json"),
    ]

    for ai_filename, shared_filename in pairs:
        assert load_json(AI_SAMPLES / ai_filename) == load_json(SHARED_EXAMPLES / shared_filename)
