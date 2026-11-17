import json

from pydantic import ValidationError

from app.ai.schema import AIResult


class AIParseError(Exception):
    """Raised when raw AI output is empty, broken JSON, not an object, or fails schema validation."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def parse_ai_response(raw: str | None) -> AIResult:
    """Turn raw LLM text into a validated AIResult, or raise AIParseError with a safe code."""
    if not isinstance(raw, str) or not raw.strip():
        raise AIParseError("empty_response")

    text = raw.strip()

    # Strip optional markdown code fences (```json ... ``` or ``` ... ```)
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
        else:
            raise AIParseError("invalid_json")

    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        raise AIParseError("invalid_json") from None

    if not isinstance(data, dict):
        raise AIParseError("not_an_object")

    try:
        return AIResult.model_validate(data)
    except ValidationError:
        raise AIParseError("invalid_values") from None