"""GW47 handler-seam regressions, frozen at 2026-08-04 by conftest."""

from datetime import datetime

import pytest

from conftest import load_gateway


@pytest.fixture(scope="module")
def gateway():
    return load_gateway()


def resolve(gateway, user_text, model_from):
    body = {"user_text": user_text, "from": model_from, "to": model_from}
    gateway.clamp_availability_range(body)
    return datetime.strptime(body["from"], "%m/%d/%Y").date().isoformat()


def test_explicit_full_date_beats_sentence_ordinal(gateway):
    assert resolve(gateway, "No Thursday the 27", "08/27/2026") == "2026-08-27"


def test_sentence_reader_parses_day_of_month(gateway):
    assert gateway.extract_date_from_text("No Thursday the 27") == "08/27/2026"
    assert resolve(gateway, "No Thursday the 27", "thursday the 27") == "2026-08-27"


def test_departure_availability_exception_wins_at_equal_rank(gateway):
    assert resolve(
        gateway, "leaving town today, back in 2 weeks", "in 2 weeks"
    ) == "2026-08-18"


def test_anaphora_still_defers(gateway):
    assert resolve(
        gateway,
        "What about Monday that week?",
        "monday the week of 08/18/2026",
    ) == "2026-08-17"


def test_equal_bare_weekday_still_uses_pathway_value(gateway):
    assert resolve(gateway, "thursday please", "thursday") == "2026-08-06"
