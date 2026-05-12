from __future__ import annotations

import json
from pathlib import Path

from app.modules.segmenting.service import segment_text
from app.schemas.segment import validate_structured_segments


SAMPLES = Path(__file__).resolve().parents[3] / "ai" / "samples"


def load_json(filename: str):
    with (SAMPLES / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_segment_text_returns_structured_segments_contract():
    refined_items = load_json("refined_text.json")

    result = segment_text(refined_items)

    segments = validate_structured_segments(result)
    assert segments
    assert [segment.sid for segment in segments] == ["segment_01", "segment_02"]

    source_texts = [item["text"] for item in refined_items]
    segmented_texts = [text.text for segment in segments for text in segment.texts]
    assert segmented_texts == source_texts
