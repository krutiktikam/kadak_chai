import json
import re

SPAM_PHRASES = ("http", "www.", "buy now", "click here", "crypto", "free money", "casino")
ABUSE_PHRASES = ("idiot", "stupid", "shut up")
ON_TOPIC_WORDS = {"chai", "tea", "kadak", "masala", "cutting"}

# Checked in this order; the first category with a matching word wins.
CATEGORY_WORDS = {
    "funny": {"funny", "laugh", "laughed", "lol", "joke", "haha"},
    "nostalgic": {"childhood", "grandma", "grandpa", "nani", "dadi", "school", "college", "remember"},
    "wholesome": {"family", "friend", "friends", "mom", "dad", "together", "love"},
}

CAPTIONS = {
    "funny": "Chai makes every day a little funnier",
    "nostalgic": "Some memories taste exactly like chai",
    "wholesome": "Chai is better when it is shared",
    "other": "Every chai break has a story",
}


def mock_response(story: str) -> str:
    """Pretend to be the LLM. Returns RAW TEXT, like the real provider does."""
    text = story.lower()
    words = set(re.findall(r"[a-z]+", text))

    # Failure triggers, so the pending_review path can be demoed.
    if "mock-error" in text:
        raise RuntimeError("mock provider failure")
    if "mock-broken" in text:
        return "Sure! Here is your JSON: {decision: approved"
    if "mock-wrong" in text:
        return json.dumps(
            {"decision": "maybe", "reason": None, "category": "sad", "caption": "x"}
        )

    # Rejections
    if any(p in text for p in SPAM_PHRASES):
        return _rejected("Looks like spam or an advertisement.")
    if any(p in text for p in ABUSE_PHRASES):
        return _rejected("Contains abusive language.")
    if not words & ON_TOPIC_WORDS:
        return _rejected("Not about a chai break.")

    # Approval: pick a category by keyword, caption comes from a fixed table.
    category = "other"
    for name, keywords in CATEGORY_WORDS.items():
        if words & keywords:
            category = name
            break
    return json.dumps(
        {"decision": "approved", "reason": None, "category": category, "caption": CAPTIONS[category]}
    )


def _rejected(reason: str) -> str:
    return json.dumps(
        {"decision": "rejected", "reason": reason, "category": "other",
         "caption": "Not a chai break story"}
    )