from __future__ import annotations

import json
from pathlib import Path

from app.modules.reasoning.service import add_reasoning
from app.modules.reasoning.service import _normalize_clues
from app.modules.reasoning.service import _normalize_segment_clues
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


def test_normalize_segment_clues_falls_back_when_clue_list_is_empty():
    segment = {
        "sid": "segment_01",
        "summary": ["Opening remarks"],
        "texts": [
            {
                "t_id": "001",
                "start_time": 0,
                "end_time": 3,
                "text": "Hello.",
            }
        ],
    }

    result = _normalize_segment_clues(
        segment,
        [{"summary_index": 0, "clue": []}],
    )

    assert result == [{"summary_index": 0, "clue": ["001"]}]


def test_normalize_segment_clues_fills_missing_summary_indices():
    segment = {
        "sid": "segment_01",
        "summary": ["Opening remarks", "Next topic"],
        "texts": [
            {
                "t_id": "001",
                "start_time": 0,
                "end_time": 3,
                "text": "Hello.",
            },
            {
                "t_id": "002",
                "start_time": 3,
                "end_time": 6,
                "text": "Next.",
            },
        ],
    }

    result = _normalize_segment_clues(
        segment,
        [{"summary_index": 0, "clue": [{"t_id": "001", "score": 1.0}]}],
    )

    assert result == [
        {"summary_index": 0, "clue": ["001"]},
        {"summary_index": 1, "clue": ["002"]},
    ]


def test_normalize_clues_falls_back_for_missing_segments():
    segments = [
        {
            "sid": "segment_01",
            "summary": ["Opening remarks"],
            "texts": [
                {
                    "t_id": "001",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
        }
    ]

    result = _normalize_clues({"segments": []}, segments)

    assert result == {"segment_01": [{"summary_index": 0, "clue": ["001"]}]}


def test_normalize_clues_accepts_segment_id_map():
    segments = [
        {
            "sid": "segment_01",
            "summary": ["Opening remarks"],
            "texts": [
                {
                    "t_id": "001",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
        }
    ]

    result = _normalize_clues(
        {
            "segment_01": {
                "clues": [
                    {
                        "summary_index": 0,
                        "clue": [{"t_id": "001", "score": 1.0}],
                    }
                ]
            }
        },
        segments,
    )

    assert result == {"segment_01": [{"summary_index": 0, "clue": ["001"]}]}
