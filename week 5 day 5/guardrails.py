import re
from collections.abc import Iterable

from tools import MAX_GUESTS, Restaurant, get_restaurants


MAX_QUESTION_LENGTH = 1000

EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?91[\s.-]?)?[6-9]\d{9}(?!\d)")
GUEST_COUNT_PATTERN = re.compile(
    r"(?<!\w)(-?\d+)\s*(?:guests?|people|persons?|diners?)\b",
    re.IGNORECASE,
)
FOLLOW_UP_PATTERN = re.compile(
    r"^(?:yes|no|ok|okay|sure|please|that one|the first one|the second one|"
    r"\d+\s*(?:guests?|people|persons?|diners?)|"
    r"(?:what about|make that|make it|change it to|increase it to|"
    r"what if i increase it to)\s+\d+\s*(?:guests?|people|persons?|diners?))$",
    re.IGNORECASE,
)

RESTAURANT_TERMS = (
    "restaurant",
    "cuisine",
    "food",
    "dine",
    "dining",
    "meal",
    "seat",
    "seating",
    "price",
    "cost",
    "cheap",
    "cheapest",
    "expensive",
    "budget",
    "per person",
    "menu",
    "reservation",
    "booking",
    "book",
    "lunch",
    "dinner",
    "breakfast",
)


def contains_pii(text: str) -> bool:
    """Return whether text contains an email address or an Indian mobile number."""
    return bool(EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text))


def clean_output(answer: str) -> str:
    """Redact email addresses and Indian mobile numbers from displayed output."""
    answer = EMAIL_PATTERN.sub("[EMAIL REDACTED]", answer)
    return PHONE_PATTERN.sub("[PHONE REDACTED]", answer)


def validate_question(question: str) -> str | None:
    """Return a user-facing validation message, or None when input is valid."""
    if not question.strip():
        return "Please enter a question."
    if len(question) > MAX_QUESTION_LENGTH:
        return f"Questions must be {MAX_QUESTION_LENGTH} characters or fewer."
    if contains_pii(question):
        return "Please remove email addresses and phone numbers before continuing."

    guest_count = GUEST_COUNT_PATTERN.search(question)
    if guest_count:
        count = int(guest_count.group(1))
        if count < 1 or count > MAX_GUESTS:
            return f"Guest count must be between 1 and {MAX_GUESTS}."
    return None


def _contains_term(question: str, terms: Iterable[str]) -> bool:
    return any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", question, re.IGNORECASE)
        for term in terms
    )


def is_restaurant_related(
    question: str,
    *,
    has_context: bool = False,
    restaurants: list[Restaurant] | None = None,
) -> bool:
    """Allow restaurant topics and short contextual replies, blocking unrelated asks."""
    if _contains_term(question, RESTAURANT_TERMS):
        return True

    records = restaurants if restaurants is not None else get_restaurants()
    data_terms = (
        value
        for restaurant in records
        for value in (restaurant["name"], restaurant["cuisine"], restaurant["location"])
    )
    if _contains_term(question, data_terms):
        return True

    return has_context and bool(FOLLOW_UP_PATTERN.fullmatch(question.strip().rstrip(".!?")))
