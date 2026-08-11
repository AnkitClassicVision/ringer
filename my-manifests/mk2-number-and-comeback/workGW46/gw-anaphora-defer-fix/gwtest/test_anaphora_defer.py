"""Handler-seam regressions for authoritative user_text date resolution."""

from datetime import datetime

import pytest

from conftest import load_gateway


@pytest.fixture(scope="module")
def gateway():
    return load_gateway()


def resolve(gateway, user_text: str, model_from: str) -> str:
    body = {"user_text": user_text, "from": model_from, "to": model_from}
    gateway.clamp_availability_range(body)
    return datetime.strptime(body["from"], "%m/%d/%Y").date().isoformat()


@pytest.mark.parametrize(
    ("user_text", "expected"),
    [
        ("What about Monday that week?", "2026-08-17"),
        ("What's the earliest I can do that day?", "2026-08-17"),
    ],
)
def test_unanchored_anaphora_preserves_pathway_date(gateway, user_text, expected):
    assert resolve(gateway, user_text, "monday the week of 08/18/2026") == expected


def test_away_sentence_keeps_authoritative_override(gateway):
    assert resolve(gateway, "I'm going away for two weeks", "in 2 weeks") == "2026-08-18"


def test_absolute_correction_keeps_authoritative_override(gateway):
    assert resolve(gateway, "No I said two weeks not today", "today") == "2026-08-18"


@pytest.mark.parametrize(
    "text",
    [
        "Monday that week",
        "Monday the same week",
        "earliest that day",
        "either of those days",
        "Monday the week we discussed",
        "Monday the week we talked about",
    ],
)
def test_supported_unanchored_anaphora_patterns_defer(gateway, text):
    assert gateway._defer_anaphoric_user_text(text)


@pytest.mark.parametrize(
    "text",
    [
        "Monday that week, 08/18/2026",
        "that day August 18",
        "that week next Monday",
        "that day in two weeks",
        "that day tomorrow",
    ],
)
def test_absolute_anchor_prevents_defer(gateway, text):
    assert not gateway._defer_anaphoric_user_text(text)

