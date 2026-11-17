"""Validation and normalisation for story submissions (Phase 3).

Core rules:
- Name: 1-100 characters, whitespace-trimmed and collapsed.
- City: 1-100 characters, whitespace-trimmed and collapsed.
- Contact: Email or phone number, up to 255 characters.
  * Emails are normalised to lowercase.
  * Phone numbers are stripped of delimiters/formatting.
  * Contact type must be 'email' or 'phone'.
- Story: 10-2000 characters, whitespace-trimmed (newlines preserved).
- Consent: Must be explicitly granted (truthy boolean or checkbox values like 'on', 'true', '1').
- Error handling: Collects all field errors simultaneously so user forms can highlight
  every invalid field in a single round-trip.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Field limits matching app/models.py Entry schema
MAX_NAME_LENGTH = 100
MAX_CITY_LENGTH = 100
MAX_CONTACT_LENGTH = 255
MIN_STORY_LENGTH = 10
MAX_STORY_LENGTH = 2000

# Regex for email validation
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class SubmissionValidationError(Exception):
    """Raised when one or more form fields fail validation.

    Designed for clean FastAPI form handling:
        try:
            valid = validate_submission(name, city, contact, story, consent)
        except SubmissionValidationError as exc:
            return templates.TemplateResponse(
                "submit.html",
                {"request": request, "errors": exc.errors, ...},
                status_code=422,
            )

    Attributes:
        errors: Dictionary mapping field name ('name', 'city', 'contact',
                'story', 'consent') to a clear, user-facing error message.
    """

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed for fields: {list(errors.keys())}")


class ValidatedSubmission(BaseModel):
    """Clean, normalised, and validated submission data ready for database insertion."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str
    city: str
    contact: str
    contact_type: Literal["email", "phone"]
    story: str
    consent: bool
    errors: dict[str, str] = {}


# Alias to support both naming conventions
ValidationResult = ValidatedSubmission


def _collapse_spaces(value: str) -> str:
    """Collapse multiple consecutive whitespace characters into a single space and strip."""
    return " ".join(value.split())


def normalise_contact(raw_contact: str) -> tuple[str, str]:
    """Validate and normalise an email address or phone number.

    Args:
        raw_contact: Raw input string from the user.

    Returns:
        tuple[str, str]: (normalised_contact, contact_type) where contact_type is
                         'email' or 'phone'.

    Raises:
        ValueError: If raw_contact is neither a valid email nor a valid phone number.
    """
    if not isinstance(raw_contact, str):
        raise ValueError("Enter a valid email address or phone number.")

    cleaned = raw_contact.strip()
    if not cleaned or len(cleaned) > MAX_CONTACT_LENGTH:
        raise ValueError("Enter a valid email address or phone number.")

    # Email branch
    if "@" in cleaned:
        if any(ch.isspace() for ch in cleaned) or ".." in cleaned:
            raise ValueError("Enter a valid email address or phone number.")
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Enter a valid email address or phone number.")
        return cleaned.lower(), "email"

    # Phone branch
    has_plus = cleaned.startswith("+")
    # Reject if '+' appears anywhere other than index 0
    if "+" in cleaned[1:]:
        raise ValueError("Enter a valid email address or phone number.")

    # Strip common formatting characters
    chars_to_strip = {" ", "-", "(", ")", "."}
    target = cleaned[1:] if has_plus else cleaned
    stripped_digits = "".join(c for c in target if c not in chars_to_strip)

    if not stripped_digits.isdigit():
        raise ValueError("Enter a valid email address or phone number.")

    if not (10 <= len(stripped_digits) <= 15):
        raise ValueError("Enter a valid email address or phone number.")

    normalised_phone = f"+{stripped_digits}" if has_plus else stripped_digits
    return normalised_phone, "phone"


def validate_submission(
    name: str,
    city: str,
    contact: str,
    story: str,
    consent: bool | str | None,
) -> ValidatedSubmission:
    """Validate and normalise all submission fields at once.

    Collects all validation errors across all fields so the user form can display
    every invalid field in a single response rather than failing one by one.

    Args:
        name: Submitter's full name (1-100 chars).
        city: Submitter's city (1-100 chars).
        contact: Email address or phone number (up to 255 chars).
        story: Chai story text (10-2000 chars).
        consent: Explicit agreement to campaign terms (truthy value).

    Returns:
        ValidatedSubmission: Cleaned and typed submission data.

    Raises:
        SubmissionValidationError: If one or more fields are invalid, containing
                                   an `errors` dictionary mapping field names to error messages.
    """
    errors: dict[str, str] = {}

    # 1. Name validation
    clean_name = _collapse_spaces(name) if isinstance(name, str) else ""
    if not clean_name:
        errors["name"] = "Name is required."
    elif len(clean_name) > MAX_NAME_LENGTH:
        errors["name"] = f"Name must be {MAX_NAME_LENGTH} characters or fewer."

    # 2. City validation
    clean_city = _collapse_spaces(city) if isinstance(city, str) else ""
    if not clean_city:
        errors["city"] = "City is required."
    elif len(clean_city) > MAX_CITY_LENGTH:
        errors["city"] = f"City must be {MAX_CITY_LENGTH} characters or fewer."

    # 3. Contact validation
    norm_contact = ""
    contact_type: Literal["email", "phone"] = "email"
    try:
        raw_contact_str = contact if isinstance(contact, str) else ""
        norm_contact, ct = normalise_contact(raw_contact_str)
        contact_type = ct  # type: ignore[assignment]
    except ValueError as exc:
        errors["contact"] = str(exc)

    # 4. Story validation (preserve intentional internal newlines)
    clean_story = story.strip() if isinstance(story, str) else ""
    if not clean_story:
        errors["story"] = "Story is required."
    elif len(clean_story) < MIN_STORY_LENGTH:
        errors["story"] = f"Story must be at least {MIN_STORY_LENGTH} characters."
    elif len(clean_story) > MAX_STORY_LENGTH:
        errors["story"] = f"Story must be {MAX_STORY_LENGTH} characters or fewer."

    # 5. Consent validation
    is_consent_valid = consent is True or (
        isinstance(consent, str) and consent.strip().lower() in {"true", "on", "yes", "1"}
    )
    if not is_consent_valid:
        errors["consent"] = "You must agree to the campaign terms to submit."

    # Final decision: raise on any errors or return valid submission
    if errors:
        raise SubmissionValidationError(errors)

    return ValidatedSubmission(
        name=clean_name,
        city=clean_city,
        contact=norm_contact,
        contact_type=contact_type,
        story=clean_story,
        consent=True,
    )
