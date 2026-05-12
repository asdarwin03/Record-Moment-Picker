from __future__ import annotations

from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    StringConstraints,
    TypeAdapter,
    model_validator,
)


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
SegmentId = Annotated[str, StringConstraints(pattern=r"^segment_[0-9]{2,}$")]
TranscriptId = Annotated[str, StringConstraints(pattern=r"^[0-9]{3,}$")]
SummarySentence = Annotated[str, StringConstraints(min_length=1)]


class TranscriptItem(BaseModel):
    """Transcript item included in a structured segment."""

    model_config = ConfigDict(extra="forbid")

    t_id: TranscriptId = Field(..., description="Global transcript item ID.")
    time: NonNegativeFloat = Field(..., description="Utterance start time in seconds.")
    text: NonEmptyString = Field(..., description="Transcript text.")


class ImportantMoment(BaseModel):
    """A timestamp worth replaying in the frontend timeline."""

    model_config = ConfigDict(extra="forbid")

    time: NonNegativeFloat = Field(..., description="Important moment timestamp in seconds.")
    title: NonEmptyString = Field(..., description="Short title for the moment.")


class Segment(BaseModel):
    """Meaningful transcript section produced by the segmenting module."""

    model_config = ConfigDict(extra="forbid")

    sid: SegmentId = Field(..., description="Segment ID, such as segment_01.")
    start_time: NonNegativeFloat = Field(..., description="Segment start time in seconds.")
    end_time: NonNegativeFloat = Field(..., description="Segment end time in seconds.")
    title: NonEmptyString = Field(..., description="Short segment title.")
    summary: list[SummarySentence] = Field(..., description="Key summary sentences.")
    texts: list[TranscriptItem] = Field(..., description="Transcript items in this segment.")
    important: list[ImportantMoment] = Field(..., description="Important replay moments.")

    @model_validator(mode="after")
    def validate_time_range_and_ids(self) -> "Segment":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time.")

        t_ids = [item.t_id for item in self.texts]
        if len(t_ids) != len(set(t_ids)):
            raise ValueError("texts contains duplicate t_id values.")

        return self


StructuredSegments = list[Segment]
StructuredSegmentsAdapter = TypeAdapter(StructuredSegments)


def validate_structured_segments(data: Any) -> StructuredSegments:
    segments = StructuredSegmentsAdapter.validate_python(data)

    sids = [segment.sid for segment in segments]
    if len(sids) != len(set(sids)):
        raise ValueError("segments contains duplicate sid values.")

    t_ids = [text.t_id for segment in segments for text in segment.texts]
    if len(t_ids) != len(set(t_ids)):
        raise ValueError("segments contains duplicate transcript t_id values.")

    return segments
