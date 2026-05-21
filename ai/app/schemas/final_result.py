from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, TypeAdapter, model_validator

from app.schemas.segment import (
    ImportantMoment,
    NonEmptyString,
    SegmentId,
    SummarySentence,
    TranscriptId,
    TranscriptItem,
)


class Clue(BaseModel):
    """Evidence mapping between a summary sentence and transcript item IDs."""

    model_config = ConfigDict(extra="forbid")

    summary_index: NonNegativeInt = Field(..., description="0-based index in summary.")
    clue: list[TranscriptId] = Field(..., min_length=1, description="Supporting transcript IDs.")


class FinalSegment(BaseModel):
    """Final segment returned to Backend and Frontend."""

    model_config = ConfigDict(extra="forbid")

    sid: SegmentId = Field(..., description="Segment ID, such as segment_01.")
    start_time: float = Field(..., ge=0, description="Segment start time in seconds.")
    end_time: float = Field(..., ge=0, description="Segment end time in seconds.")
    title: NonEmptyString = Field(..., description="Short segment title.")
    summary: list[SummarySentence] = Field(..., description="Summary sentences.")
    texts: list[TranscriptItem] = Field(..., description="Transcript items in this segment.")
    important: list[ImportantMoment] = Field(..., description="Important replay moments.")
    clues: list[Clue] = Field(..., description="Summary evidence mappings.")

    @model_validator(mode="after")
    def validate_final_segment_contract(self) -> "FinalSegment":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time.")

        for clue in self.clues:
            if clue.summary_index >= len(self.summary):
                raise ValueError("summary_index is out of range for summary.")

        return self


FinalResult = list[FinalSegment]
FinalResultAdapter = TypeAdapter(FinalResult)


def validate_final_result(data: Any) -> FinalResult:
    result = FinalResultAdapter.validate_python(data)

    sids = [segment.sid for segment in result]
    if len(sids) != len(set(sids)):
        raise ValueError("final result contains duplicate sid values.")

    t_ids = [text.t_id for segment in result for text in segment.texts]
    if len(t_ids) != len(set(t_ids)):
        raise ValueError("final result contains duplicate transcript t_id values.")

    for segment in result:
        valid_t_ids = {text.t_id for text in segment.texts}
        for clue in segment.clues:
            unknown_ids = set(clue.clue) - valid_t_ids
            if unknown_ids:
                raise ValueError(
                    f"final result clue references t_id values outside segment {segment.sid}: {sorted(unknown_ids)}."
                )

    return result
