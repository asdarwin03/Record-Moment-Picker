from __future__ import annotations

import json
from pathlib import Path

from app.modules.reasoning.service import add_reasoning
from app.schemas.final_result import validate_final_result


SAMPLES = Path(__file__).resolve().parents[3] / "ai" / "samples"


def load_json(filename: str):
    with (SAMPLES / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def test_add_reasoning_returns_final_result_contract():
    structured_segments = load_json("structured_segments.json")

    result = add_reasoning(structured_segments)

    final_result = validate_final_result(result)
    assert len(final_result) == len(structured_segments)

    for segment in final_result:
        assert len(segment.clues) == len(segment.summary)
        valid_ids = {text.t_id for text in segment.texts}
        for clue in segment.clues:
            assert set(clue.clue) <= valid_ids
