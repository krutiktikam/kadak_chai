import pytest

from app import config
from app.ai import AnalysisOutcome, analyze_story
from app.ai.client import AIProviderError


def test_analyze_story_mock_approved(monkeypatch):
    monkeypatch.setattr(config, "AI_PROVIDER", "mock")
    outcome = analyze_story("Chai with my grandma after school.")

    assert isinstance(outcome, AnalysisOutcome)
    assert outcome.status == "approved"
    assert outcome.ai_decision == "approved"
    assert outcome.ai_reason is None
    assert outcome.ai_category in {"funny", "nostalgic", "wholesome", "other"}
    assert outcome.ai_caption
    assert outcome.ai_error is None


def test_analyze_story_mock_rejected(monkeypatch):
    monkeypatch.setattr(config, "AI_PROVIDER", "mock")
    outcome = analyze_story("Buy cheap watches at www.spam.example")

    assert outcome.status == "rejected"
    assert outcome.ai_decision == "rejected"
    assert outcome.ai_reason
    assert outcome.ai_caption
    assert outcome.ai_error is None


@pytest.mark.parametrize(
    ("trigger_story", "expected_code"),
    [
        ("chai mock-broken", "invalid_json"),
        ("chai mock-wrong", "invalid_values"),
    ],
    ids=["mock_broken", "mock_wrong"],
)
def test_analyze_story_mock_failure_triggers(monkeypatch, trigger_story, expected_code):
    monkeypatch.setattr(config, "AI_PROVIDER", "mock")
    outcome = analyze_story(trigger_story)

    assert outcome.status == "pending_review"
    assert outcome.ai_decision is None
    assert outcome.ai_reason is None
    assert outcome.ai_category is None
    assert outcome.ai_caption is None
    assert outcome.ai_error == expected_code


def test_analyze_story_uses_real_client_when_not_mock(monkeypatch):
    monkeypatch.setattr(config, "AI_PROVIDER", "groq")

    def fake_call_llm(story: str) -> str:
        assert story == "Monsoon evening cutting chai"
        return '{"decision": "approved", "reason": null, "category": "wholesome", "caption": "Rainy evening cutting chai"}'

    monkeypatch.setattr("app.ai.call_llm", fake_call_llm)
    outcome = analyze_story("Monsoon evening cutting chai")

    assert outcome.status == "approved"
    assert outcome.ai_category == "wholesome"
    assert outcome.ai_error is None


@pytest.mark.parametrize(
    ("fake_provider", "expected_error"),
    [
        (lambda _s: (_ for _ in ()).throw(AIProviderError("timeout")), "timeout"),
        (lambda _s: (_ for _ in ()).throw(AIProviderError("http_429")), "http_429"),
        (lambda _s: "", "empty_response"),
        (lambda _s: "not json at all", "invalid_json"),
        (lambda _s: "[]", "not_an_object"),
        (lambda _s: '{"decision": "maybe"}', "invalid_values"),
        (lambda _s: (_ for _ in ()).throw(RuntimeError("boom")), "unexpected_error"),
    ],
    ids=[
        "provider_timeout",
        "provider_429",
        "empty_response",
        "invalid_json",
        "not_an_object",
        "invalid_values",
        "unexpected_crash",
    ],
)
def test_analyze_story_failures_become_pending_review(fake_provider, expected_error):
    outcome = analyze_story("SECRET-STORY-TEXT about chai", provider=fake_provider)

    assert outcome.status == "pending_review"
    assert outcome.ai_decision is None
    assert outcome.ai_reason is None
    assert outcome.ai_category is None
    assert outcome.ai_caption is None
    assert outcome.ai_error == expected_error
    assert "SECRET-STORY-TEXT" not in outcome.ai_error