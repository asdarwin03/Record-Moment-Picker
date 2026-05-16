from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, StringConstraints, TypeAdapter


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class RefinedTextItem(BaseModel):
    """One timestamped transcript item after text correction."""

    model_config = ConfigDict(extra="forbid")

    t_id: NonEmptyString = Field(..., description="Original STT text id.")
    start_time: NonNegativeFloat = Field(..., description="Utterance start time in seconds.")
    end_time: NonNegativeFloat = Field(..., description="Utterance end time in seconds.")
    text: NonEmptyString = Field(..., description="Corrected transcript text.")


class RefinedTextOutput(BaseModel):
    """Refined transcript output with preserved timing metadata."""

    model_config = ConfigDict(extra="forbid")

    audio_duration: NonNegativeFloat = Field(..., description="Total audio duration in seconds.")
    texts: list[RefinedTextItem] = Field(default_factory=list)


RefinedTextOutputAdapter = TypeAdapter(RefinedTextOutput)


def validate_refined_text_output(data: Any) -> RefinedTextOutput:
    return RefinedTextOutputAdapter.validate_python(data)
