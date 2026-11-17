import pytest

from app.validation import (
    MAX_CITY_LENGTH,
    MAX_CONTACT_LENGTH,
    MAX_NAME_LENGTH,
    MAX_STORY_LENGTH,
    MIN_STORY_LENGTH,
    SubmissionValidationError,
    ValidatedSubmission,
    normalise_contact,
    validate_submission,
)

VALID_SUBMISSION_DATA = {
    "name": "Aarav Sharma",
    "city": "Jaipur",
    "contact": "aarav@example.com",
    "story": "Every evening at five, my grandmother brewed strong kadak masala chai for all of us.",
    "consent": True,
}


# ==============================================================================
# 1. Valid Submissions & Normalisation
# ==============================================================================


def test_validate_submission_with_email():
    result = validate_submission(
        name="Aarav Sharma",
        city="Jaipur",
        contact="Aarav.Sharma@Example.COM",
        story="Every evening at five, my grandmother brewed strong kadak masala chai.",
        consent=True,
    )
    assert isinstance(result, ValidatedSubmission)
    assert result.name == "Aarav Sharma"
    assert result.city == "Jaipur"
    assert result.contact == "aarav.sharma@example.com"
    assert result.contact_type == "email"
    assert result.story == "Every evening at five, my grandmother brewed strong kadak masala chai."
    assert result.consent is True


@pytest.mark.parametrize(
    "phone_input",
    [
        "9876543210",
        "+91 98765 43210",
        "+91-98765-43210",
        "+919876543210",
        "09876543210",
        "98765 43210",
        "98765-43210",
    ],
)
def test_validate_submission_with_phone_variants(phone_input: str):
    data = {**VALID_SUBMISSION_DATA, "contact": phone_input}
    result = validate_submission(**data)
    assert result.contact_type == "phone"
    assert "9876543210" in result.contact
    assert not any(char in result.contact for char in " -()")


def test_validate_submission_whitespace_trimming():
    result = validate_submission(
        name="   Priya   Patel   ",
        city="  Bengaluru  ",
        contact="   priya.patel@example.com   ",
        story="   \nChai at the corner stall after our final exams was unforgettable.\n   ",
        consent=True,
    )
    assert result.name == "Priya Patel"
    assert result.city == "Bengaluru"
    assert result.contact == "priya.patel@example.com"
    assert result.story == "Chai at the corner stall after our final exams was unforgettable."


@pytest.mark.parametrize("truthy_consent", [True, "true", "True", "on", "yes", "1"])
def test_validate_submission_truthy_consent(truthy_consent):
    data = {**VALID_SUBMISSION_DATA, "consent": truthy_consent}
    result = validate_submission(**data)
    assert result.consent is True


def test_validate_submission_boundary_lengths():
    exact_100_name = "N" * MAX_NAME_LENGTH
    exact_100_city = "C" * MAX_CITY_LENGTH
    exact_10_story = "S" * MIN_STORY_LENGTH
    exact_2000_story = "A" * MAX_STORY_LENGTH

    result = validate_submission(
        name=exact_100_name,
        city=exact_100_city,
        contact="boundary@example.com",
        story=exact_10_story,
        consent=True,
    )
    assert result.name == exact_100_name
    assert result.city == exact_100_city
    assert result.story == exact_10_story

    result_long_story = validate_submission(
        name="Valid Name",
        city="Valid City",
        contact="boundary@example.com",
        story=exact_2000_story,
        consent=True,
    )
    assert len(result_long_story.story) == MAX_STORY_LENGTH


# ==============================================================================
# 2. Contact Normalisation Unit Tests
# ==============================================================================


@pytest.mark.parametrize(
    ("raw_email", "expected_email"),
    [
        ("test@example.com", "test@example.com"),
        ("  User.Name+Tag@Example.CO.IN  ", "user.name+tag@example.co.in"),
        ("chai_break123@domain.org", "chai_break123@domain.org"),
    ],
)
def test_normalise_contact_email(raw_email: str, expected_email: str):
    contact, contact_type = normalise_contact(raw_email)
    assert contact_type == "email"
    assert contact == expected_email


@pytest.mark.parametrize(
    "raw_phone",
    [
        "9876543210",
        "+91 98765 43210",
        "+91-98765-43210",
        "09876543210",
        "+1 (415) 555-2671",
    ],
)
def test_normalise_contact_phone(raw_phone: str):
    contact, contact_type = normalise_contact(raw_phone)
    assert contact_type == "phone"
    assert not any(c in contact for c in " -()")


@pytest.mark.parametrize(
    "invalid_contact",
    [
        "",
        "   ",
        "not-an-email-or-phone",
        "user@",
        "@example.com",
        "user@.com",
        "user name@domain.com",
        "12345",
        "abcdefghij",
        "98765abcde",
        "+" * 20,
        "x" * (MAX_CONTACT_LENGTH + 1),
    ],
)
def test_normalise_contact_invalid_raises_value_error(invalid_contact: str):
    with pytest.raises(ValueError):
        normalise_contact(invalid_contact)


# ==============================================================================
# 3. Invalid / Missing Name and City
# ==============================================================================


@pytest.mark.parametrize("invalid_name", ["", "   ", "\t\n", "A" * (MAX_NAME_LENGTH + 1)])
def test_validate_submission_invalid_name(invalid_name: str):
    data = {**VALID_SUBMISSION_DATA, "name": invalid_name}
    with pytest.raises(SubmissionValidationError) as exc_info:
        validate_submission(**data)
    assert "name" in exc_info.value.errors


@pytest.mark.parametrize("invalid_city", ["", "   ", "\t\n", "C" * (MAX_CITY_LENGTH + 1)])
def test_validate_submission_invalid_city(invalid_city: str):
    data = {**VALID_SUBMISSION_DATA, "city": invalid_city}
    with pytest.raises(SubmissionValidationError) as exc_info:
        validate_submission(**data)
    assert "city" in exc_info.value.errors


# ==============================================================================
# 4. Invalid Contact
# ==============================================================================


@pytest.mark.parametrize(
    "invalid_contact",
    [
        "",
        "   ",
        "user@",
        "@domain.com",
        "user@.com",
        "plainaddress",
        "12345",
        "abcdefghij",
        "98765abcde",
        "a" * (MAX_CONTACT_LENGTH + 1),
    ],
)
def test_validate_submission_invalid_contact(invalid_contact: str):
    data = {**VALID_SUBMISSION_DATA, "contact": invalid_contact}
    with pytest.raises(SubmissionValidationError) as exc_info:
        validate_submission(**data)
    assert "contact" in exc_info.value.errors


# ==============================================================================
# 5. Invalid Story
# ==============================================================================


@pytest.mark.parametrize(
    "invalid_story",
    [
        "",
        "   ",
        "\t\n   \n",
        "Short",  # < 10 chars
        "123456789",  # 9 chars
        "S" * (MAX_STORY_LENGTH + 1),  # > 2000 chars
    ],
)
def test_validate_submission_invalid_story(invalid_story: str):
    data = {**VALID_SUBMISSION_DATA, "story": invalid_story}
    with pytest.raises(SubmissionValidationError) as exc_info:
        validate_submission(**data)
    assert "story" in exc_info.value.errors


# ==============================================================================
# 6. Missing / False Consent
# ==============================================================================


@pytest.mark.parametrize("falsy_consent", [False, None, "", "off", "false", "0", "no"])
def test_validate_submission_invalid_consent(falsy_consent):
    data = {**VALID_SUBMISSION_DATA, "consent": falsy_consent}
    with pytest.raises(SubmissionValidationError) as exc_info:
        validate_submission(**data)
    assert "consent" in exc_info.value.errors


# ==============================================================================
# 7. Multi-Field Error Collection
# ==============================================================================


def test_validate_submission_all_fields_invalid_reported_together():
    """All invalid fields should be collected and returned in exc.errors in a single pass."""
    with pytest.raises(SubmissionValidationError) as exc_info:
        validate_submission(
            name="",
            city="",
            contact="",
            story="",
            consent=False,
        )
    errors = exc_info.value.errors
    assert "name" in errors
    assert "city" in errors
    assert "contact" in errors
    assert "story" in errors
    assert "consent" in errors
    assert len(errors) == 5


def test_validate_submission_partial_fields_invalid():
    """Valid fields must not appear in errors; invalid fields must be captured."""
    with pytest.raises(SubmissionValidationError) as exc_info:
        validate_submission(
            name="Rohan Verma",  # valid
            city="Delhi",        # valid
            contact="notanemail",# invalid
            story="Too short",   # invalid (< 10 chars)
            consent="off",       # invalid
        )
    errors = exc_info.value.errors
    assert "name" not in errors
    assert "city" not in errors
    assert "contact" in errors
    assert "story" in errors
    assert "consent" in errors
