from __future__ import annotations

import json
from pathlib import Path

from app.modules.refine_text.service import refine_text
from app.schemas.refined_text import validate_refined_text_output


SAMPLES = Path(__file__).resolve().parents[3] / "ai" / "samples"


def load_json(filename: str):
    with (SAMPLES / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_refine_text_returns_refined_text_contract():
    stt_items = load_json("stt_output.json")

    result = refine_text(stt_items)

    validated = validate_refined_text_output(result)
    assert len(validated) == len(stt_items)
    assert [item.start_time for item in validated] == [item["start_time"] for item in stt_items]
    assert [item.end_time for item in validated] == [item["end_time"] for item in stt_items]
    assert all(item.text for item in validated)
