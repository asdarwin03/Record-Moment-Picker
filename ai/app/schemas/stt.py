from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, StringConstraints, TypeAdapter


NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class STTItem(BaseModel):
    """One timestamped transcript item produced by Whisper STT."""

    model_config = ConfigDict(extra="forbid")

    start_time: NonNegativeFloat = Field(..., description="Utterance start time in seconds.")
    end_time: NonNegativeFloat = Field(..., description="Utterance end time in seconds.")
    text: NonEmptyString = Field(..., description="Raw transcript text from STT.")


STTOutput = list[STTItem]
STTOutputAdapter = TypeAdapter(STTOutput)


def validate_stt_output(data: Any) -> STTOutput:
    return STTOutputAdapter.validate_python(data)
