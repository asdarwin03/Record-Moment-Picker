from __future__ import annotations

import json
from pathlib import Path

from app.modules.segmenting.service import segment_text
from app.modules.segmenting.service import _coerce_segment_list
from app.modules.segmenting.service import _dedupe_segment_texts
from app.modules.segmenting.service import _normalize_transcript_ids
from app.modules.segmenting.service import _post_process
from app.modules.segmenting.service import _restore_missing_utterances
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


def test_coerce_segment_list_finds_nested_segment_list():
    segment = {
        "sid": "segment_01",
        "start_time": 0,
        "end_time": 3,
        "title": "Intro",
        "summary": ["Opening remarks"],
        "texts": [
            {
                "t_id": "001",
                "start_time": 0,
                "end_time": 3,
                "text": "Hello.",
            }
        ],
        "important": [],
    }

    result = _coerce_segment_list(
        {
            "response": {
                "segments": [segment],
                "notes": "wrapped response",
            }
        },
        "test segmenting result",
    )

    assert result == [segment]


def test_coerce_segment_list_accepts_single_segment_without_sid():
    segment = {
        "start_time": 0,
        "end_time": 3,
        "title": "Intro",
        "summary": ["Opening remarks"],
        "texts": [
            {
                "t_id": "001",
                "start_time": 0,
                "end_time": 3,
                "text": "Hello.",
            }
        ],
        "important": [],
    }

    result = _coerce_segment_list(segment, "test segmenting result")

    assert result == [segment]


def test_coerce_segment_list_accepts_segment_id_map():
    segment = {
        "start_time": 0,
        "end_time": 3,
        "title": "Intro",
        "summary": ["Opening remarks"],
        "texts": [
            {
                "t_id": "001",
                "start_time": 0,
                "end_time": 3,
                "text": "Hello.",
            }
        ],
        "important": [],
    }

    result = _coerce_segment_list(
        {"segment_01": segment},
        "test merged boundary",
    )

    assert result == [segment]


def test_normalize_transcript_ids_pads_numeric_ids():
    segments = [
        {
            "sid": "segment_01",
            "start_time": 0,
            "end_time": 3,
            "title": "Intro",
            "summary": ["Opening remarks"],
            "texts": [
                {
                    "t_id": "76",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
            "important": [],
        }
    ]

    result = _normalize_transcript_ids(segments)

    assert result[0]["texts"][0]["t_id"] == "0076"


def test_post_process_drops_segments_without_texts():
    refined_items = [
        {
            "t_id": "0001",
            "start_time": 0,
            "end_time": 3,
            "text": "Hello.",
        }
    ]
    segments = [
        {
            "sid": "segment_01",
            "start_time": 0,
            "end_time": 3,
            "title": "Intro",
            "summary": ["Opening remarks"],
            "texts": [
                {
                    "t_id": "1",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
            "important": [],
        },
        {
            "sid": "segment_02",
            "start_time": 3,
            "end_time": 6,
            "title": "Empty",
            "summary": ["No evidence"],
            "texts": [],
            "important": [],
        },
    ]

    result = _post_process(segments, refined_items)

    assert len(result) == 1
    assert result[0]["title"] == "Intro"


def test_dedupe_segment_texts_removes_duplicate_t_ids_across_segments():
    segments = [
        {
            "sid": "segment_01",
            "start_time": 0,
            "end_time": 3,
            "title": "First",
            "summary": ["First summary"],
            "texts": [
                {
                    "t_id": "0001",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
            "important": [],
        },
        {
            "sid": "segment_02",
            "start_time": 3,
            "end_time": 6,
            "title": "Second",
            "summary": ["Second summary"],
            "texts": [
                {
                    "t_id": "0001",
                    "start_time": 3,
                    "end_time": 6,
                    "text": "Hello again.",
                }
            ],
            "important": [],
        },
    ]

    result = _dedupe_segment_texts(segments)

    assert [text["t_id"] for segment in result for text in segment["texts"]] == ["0001"]
    assert result[1]["texts"] == []


def test_post_process_removes_duplicate_t_ids_and_empty_segments():
    refined_items = [
        {
            "t_id": "0001",
            "start_time": 0,
            "end_time": 3,
            "text": "Hello.",
        }
    ]
    segments = [
        {
            "sid": "segment_01",
            "start_time": 0,
            "end_time": 3,
            "title": "First",
            "summary": ["First summary"],
            "texts": [
                {
                    "t_id": "1",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
            "important": [],
        },
        {
            "sid": "segment_02",
            "start_time": 3,
            "end_time": 6,
            "title": "Duplicate",
            "summary": ["Duplicate summary"],
            "texts": [
                {
                    "t_id": "1",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
            "important": [],
        },
    ]

    result = _post_process(segments, refined_items)

    assert len(result) == 1
    assert [text["t_id"] for segment in result for text in segment["texts"]] == ["0001"]


def test_restore_missing_utterances_preserves_source_t_id():
    segments = [
        {
            "sid": "segment_01",
            "start_time": 0,
            "end_time": 3,
            "title": "First",
            "summary": ["First summary"],
            "texts": [
                {
                    "t_id": "0001",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "Hello.",
                }
            ],
            "important": [],
        }
    ]
    refined_items = [
        {
            "t_id": "0001",
            "start_time": 0,
            "end_time": 3,
            "text": "Hello.",
        },
        {
            "t_id": "0002",
            "start_time": 3,
            "end_time": 6,
            "text": "Missing.",
        },
    ]

    result = _restore_missing_utterances(segments, refined_items)

    assert [text["t_id"] for segment in result for text in segment["texts"]] == [
        "0001",
        "0002",
    ]
