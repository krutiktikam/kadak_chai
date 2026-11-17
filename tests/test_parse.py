import json

import pytest

from app.ai.mock import mock_response
from app.ai.parse import AIParseError, parse_ai_response
from app.ai.schema import AIResult

VALID_PAYLOAD = {
    "decision": "approved",
    "reason": None,
    "category": "funny",
    "caption": "Chai fixes everything",
}


def test_valid_responses():
    # 1. Valid approved JSON
    res = parse_ai_response(json.dumps(VALID_PAYLOAD))
    assert res == AIResult.model_validate(VALID_PAYLOAD)

    # 2. Valid rejected JSON with a reason
    rejected = {**VALID_PAYLOAD, "decision": "rejected", "reason": "spam"}
    assert parse_ai_response(json.dumps(rejected)) == AIResult.model_validate(rejected)

    # 3. Valid JSON inside a ```json fence
    fenced = "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```"
    assert parse_ai_response(fenced) == AIResult.model_validate(VALID_PAYLOAD)

    # 4. Valid JSON with surrounding whitespace and newlines
    padded = "  \n " + json.dumps(VALID_PAYLOAD) + " \n  "
    assert parse_ai_response(padded) == AIResult.model_validate(VALID_PAYLOAD)

    # 5. Valid JSON plus an extra unknown key (ignored by AIResult)
    extra = {**VALID_PAYLOAD, "mood": "happy"}
    assert parse_ai_response(json.dumps(extra)) == AIResult.model_validate(VALID_PAYLOAD)

    # 6. Exact 12-word caption
    twelve = {**VALID_PAYLOAD, "caption": " ".join(["chai"] * 12)}
    assert parse_ai_response(json.dumps(twelve)) == AIResult.model_validate(twelve)


@pytest.mark.parametrize("bad_input", ["", "   \n", None])
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
    ],
)
def test_broken_response_raises_invalid_json(broken_text):
    with pytest.raises(AIParseError) as exc_info:
        parse_ai_response(broken_text)
    assert exc_info.value.code == "invalid_json"
    assert str(exc_info.value) == "invalid_json"


@pytest.mark.parametrize("non_obj", ["[]", '"approved"', "42", "null"])
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


def test_mock_failure_triggers():
    with pytest.raises(AIParseError) as broken_exc:
        parse_ai_response(mock_response("chai mock-broken"))
    assert broken_exc.value.code == "invalid_json"

    with pytest.raises(AIParseError) as wrong_exc:
        parse_ai_response(mock_response("chai mock-wrong"))
    assert wrong_exc.value.code == "invalid_values"