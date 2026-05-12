from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, StringConstraints, TypeAdapter


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class RefinedTextItem(BaseModel):
    """One timestamped transcript item after text correction."""

    model_config = ConfigDict(extra="forbid")

    time: NonNegativeFloat = Field(..., description="Utterance start time in seconds.")
    text: NonEmptyString = Field(..., description="Corrected transcript text.")


RefinedTextOutput = list[RefinedTextItem]
RefinedTextOutputAdapter = TypeAdapter(RefinedTextOutput)


def validate_refined_text_output(data: Any) -> RefinedTextOutput:
    return RefinedTextOutputAdapter.validate_python(data)
