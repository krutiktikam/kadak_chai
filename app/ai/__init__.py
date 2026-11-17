from collections.abc import Callable
from dataclasses import dataclass

from app import config
from app.ai.client import AIProviderError, call_llm
from app.ai.mock import mock_response
from app.ai.parse import AIParseError, parse_ai_response


@dataclass(frozen=True)
class AnalysisOutcome:
    """Result of running AI moderation, ready to map straight onto an Entry row."""

    status: str
    ai_decision: str | None = None
    ai_reason: str | None = None
    ai_category: str | None = None
    ai_caption: str | None = None
    ai_error: str | None = None


def analyze_story(
    story: str,
    *,
    provider: Callable[[str], str] | None = None,
) -> AnalysisOutcome:
    """Moderate a story via mock or real LLM. Never raises; failures become pending_review."""
    if provider is not None:
        fetch = provider
    elif config.AI_PROVIDER == "mock":
        fetch = mock_response
    else:
        fetch = call_llm

    try:
        raw = fetch(story)
        result = parse_ai_response(raw)
    except (AIProviderError, AIParseError) as exc:
        return AnalysisOutcome(status="pending_review", ai_error=exc.code)
    except Exception:
        return AnalysisOutcome(status="pending_review", ai_error="unexpected_error")

    return AnalysisOutcome(
        status=result.decision,
        ai_decision=result.decision,
        ai_reason=result.reason,
        ai_category=result.category,
        ai_caption=result.caption,
        ai_error=None,
    )


__all__ = ["AnalysisOutcome", "analyze_story"]