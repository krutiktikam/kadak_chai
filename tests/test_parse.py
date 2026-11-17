import json
import traceback

import pytest

from app.ai.mock import mock_response
from app.ai.parse import AIParseError, parse_ai_response

VALID_PAYLOAD = {
    "decision": "approved",
    "reason": None,
    "category": "funny",
    "caption": "Chai fixes everything",
}


@pytest.mark.parametrize(
    ("raw_input", "expected_decision", "expected_reason", "expected_category", "expected_caption"),
    [
        (json.dumps(VALID_PAYLOAD), "approved", None, "funny", "Chai fixes everything"),
        (
            json.dumps({**VALID_PAYLOAD, "decision": "rejected", "reason": "spam"}),
            "rejected",
            "spam",
            "funny",
            "Chai fixes everything",
        ),
        (
            "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```",
            "approved",
            None,
            "funny",
            "Chai fixes everything",
        ),
        (
            "```\n" + json.dumps(VALID_PAYLOAD) + "\n```",
            "approved",
            None,
            "funny",
            "Chai fixes everything",
        ),
        (
            "  \n " + json.dumps(VALID_PAYLOAD) + " \n  ",
            "approved",
            None,
            "funny",
            "Chai fixes everything",
        ),
        (
            json.dumps({**VALID_PAYLOAD, "mood": "happy"}),
            "approved",
            None,
            "funny",
            "Chai fixes everything",
        ),
        (
            json.dumps({**VALID_PAYLOAD, "caption": " ".join(["chai"] * 12)}),
            "approved",
            None,
            "funny",
            " ".join(["chai"] * 12),
        ),
    ],
    ids=[
        "approved",
        "rejected",
        "json_fence",
        "plain_fence",
        "whitespace",
        "extra_key",
        "12_words",
    ],
)
def test_valid_responses(
    raw_input, expected_decision, expected_reason, expected_category, expected_caption
):
    res = parse_ai_response(raw_input)
    assert res.decision == expected_decision
    assert res.reason == expected_reason
    assert res.category == expected_category
    assert res.caption == expected_caption


@pytest.mark.parametrize("bad_input", ["", "   \n", None], ids=["empty", "whitespace_only", "none"])
def test_empty_response(bad_input):
    with pytest.raises(AIParseError) as exc_info:
        parse_ai_response(bad_input)
    assert exc_info.value.code == "empty_response"
    assert str(exc_info.value) == "empty_response"


@pytest.mark.parametrize(
    "broken_text",
    [
        "Sure! Here is your JSON: {decision: approved",
        '{"decision": "approved", "cat',
        "[" * 100000,
        "1" * 5000,
    ],
    ids=["prose_prefix", "truncated_json", "deep_nesting", "huge_integer"],
)
def test_broken_response_raises_invalid_json(broken_text):
    with pytest.raises(AIParseError) as exc_info:
        parse_ai_response(broken_text)
    assert exc_info.value.code == "invalid_json"
    assert str(exc_info.value) == "invalid_json"


@pytest.mark.parametrize(
    "non_obj",
    ["[]", '"approved"', "42", "null"],
    ids=["list", "string", "number", "null"],
)
def test_non_object_raises_not_an_object(non_obj):
    with pytest.raises(AIParseError) as exc_info:
        parse_ai_response(non_obj)
    assert exc_info.value.code == "not_an_object"
    assert str(exc_info.value) == "not_an_object"


@pytest.mark.parametrize(
    "bad_dict",
    [
        {**VALID_PAYLOAD, "decision": "maybe"},
        {**VALID_PAYLOAD, "decision": "Approved"},
        {**VALID_PAYLOAD, "category": "sad"},
        {**VALID_PAYLOAD, "caption": " ".join(["chai"] * 13)},
        {**VALID_PAYLOAD, "caption": "   "},
        {**VALID_PAYLOAD, "decision": "rejected"},
        {**VALID_PAYLOAD, "decision": "rejected", "reason": None},
        {"decision": "approved", "category": "funny"},
        {**VALID_PAYLOAD, "caption": 123},
        {},
    ],
    ids=[
        "maybe_decision",
        "capital_A_decision",
        "unknown_category",
        "13_words",
        "blank_caption",
        "rejected_no_reason",
        "rejected_null_reason",
        "missing_caption",
        "caption_is_int",
        "empty_object",
    ],
)
def test_valid_json_wrong_values_raises_invalid_values(bad_dict):
    with pytest.raises(AIParseError) as exc_info:
        parse_ai_response(json.dumps(bad_dict))
    assert exc_info.value.code == "invalid_values"
    assert str(exc_info.value) == "invalid_values"


def test_error_does_not_leak_story_text():
    payload = json.dumps(
        {**VALID_PAYLOAD, "category": "sad", "caption": "SECRET-STORY-TEXT"}
    )
    with pytest.raises(AIParseError) as exc_info:
        parse_ai_response(payload)
    assert exc_info.value.code == "invalid_values"
    assert "SECRET-STORY-TEXT" not in str(exc_info.value)
    rendered = "".join(traceback.format_exception(exc_info.value))
    assert "SECRET-STORY-TEXT" not in rendered


def test_mock_failure_triggers():
    with pytest.raises(AIParseError) as broken_exc:
        parse_ai_response(mock_response("chai mock-broken"))
    assert broken_exc.value.code == "invalid_json"

    with pytest.raises(AIParseError) as wrong_exc:
        parse_ai_response(mock_response("chai mock-wrong"))
    assert wrong_exc.value.code == "invalid_values"