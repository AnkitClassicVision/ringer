from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "container" / "bland_gateway.py"


def load_gateway():
    spec = importlib.util.spec_from_file_location("gw50_gateway", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_context_weekday_uses_context_dates_monday_anchored_week(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setattr(gateway, "_RAW_TEXT_DATES", False)
    monkeypatch.setattr(gateway, "_eastern_today", lambda: gateway.datetime(2026, 8, 5))
    body = {
        "from": "Monday that week",
        "to": "Monday that week",
        "context_date": "08/18/2026 10:30 am",
    }

    gateway.clamp_availability_range(body)

    assert body["from"] == "08/17/2026"
    assert body["to"] == "08/17/2026"
    assert "context_date" not in body


def test_bare_that_week_uses_monday_through_friday(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setattr(gateway, "_RAW_TEXT_DATES", False)
    monkeypatch.setattr(gateway, "_eastern_today", lambda: gateway.datetime(2026, 8, 5))
    body = {
        "from": "that week",
        "to": "that week",
        "context_date": "08/18/2026",
    }

    gateway.clamp_availability_range(body)

    assert body["from"] == "08/17/2026"
    assert body["to"] == "08/21/2026"


def test_self_resolving_week_of_ignores_context_date(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setattr(gateway, "_RAW_TEXT_DATES", False)
    monkeypatch.setattr(gateway, "_eastern_today", lambda: gateway.datetime(2026, 8, 5))
    body = {
        "from": "monday the week of 08/18/2026",
        "to": "monday the week of 08/18/2026",
        "context_date": "09/22/2026 3:00 pm",
    }

    gateway.clamp_availability_range(body)

    assert body["from"] == "08/17/2026"
    assert body["to"] == "08/17/2026"


def test_anchor_route_is_exclusive_across_all_four_outcomes():
    gateway = load_gateway()
    pref = "anchor=10:30 am"
    payloads = {
        "error": {"ok": False, "error": "upstream_refused"},
        "none": {"ok": True, "result": gateway.availability_envelope([], pref)},
        "exact": {
            "ok": True,
            "result": gateway.availability_envelope(
                [{"start": "08/17/2026 10:30 AM", "end": "08/17/2026 11:00 AM"}],
                pref,
            ),
        },
        "closest": {
            "ok": True,
            "result": gateway.availability_envelope(
                [{"start": "08/17/2026 11:00 AM", "end": "08/17/2026 11:30 AM"}],
                pref,
            ),
        },
    }

    routes = []
    for expected, payload in payloads.items():
        class ResponseSeam:
            path = "/availability"
            _availability_time_pref = pref
            wfile = io.BytesIO()

            def send_response(self, _status):
                pass

            def send_header(self, _key, _value):
                pass

            def end_headers(self):
                pass

        seam = ResponseSeam()
        gateway.Handler._send(seam, 200, payload)
        result = json.loads(seam.wfile.getvalue())["result"]
        assert result["anchor_route"] == expected
        routes.append(result["anchor_route"])

    assert sorted(routes) == ["closest", "error", "exact", "none"]


def test_non_anchor_response_omits_anchor_route():
    gateway = load_gateway()
    payload = {"ok": True, "result": gateway.availability_envelope([])}
    gateway.finalize_anchor_route(payload, "morning")
    assert "anchor_route" not in payload["result"]
