from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

MAX_CAPTION_WORDS = 12


class AIResult(BaseModel):
    # Trim whitespace on every string; silently ignore any extra keys the model adds.
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    decision: Literal["approved", "rejected"]
    reason: str | None = None
    category: Literal["funny", "nostalgic", "wholesome", "other"]
    caption: str

    @field_validator("caption")
    @classmethod
    def caption_length(cls, value: str) -> str:
        words = value.split()
        if not words:
            raise ValueError("caption must not be empty")
        if len(words) > MAX_CAPTION_WORDS:
            raise ValueError(f"caption must be {MAX_CAPTION_WORDS} words or fewer")
        return value

    @model_validator(mode="after")
    def reason_required_when_rejected(self):
        if self.decision == "rejected" and not self.reason:
            raise ValueError("reason is required when decision is rejected")
        return self