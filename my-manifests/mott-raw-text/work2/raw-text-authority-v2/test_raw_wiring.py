#!/usr/bin/env python3
import importlib.util
import os
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest


def load_gateway(name, raw="1", tenant="mott"):
    os.environ["ECP_DATE_ORDINAL_FALLBACK"] = "1"
    os.environ["ECP_RAW_TEXT_DATES"] = raw
    os.environ["ECP_TENANT_ID"] = tenant
    stub = types.ModuleType("capability_registry")
    stub.QueryError = type("QE", (Exception,), {})
    stub.load_manifest = lambda *a, **k: {}
    stub.prepare_query = lambda *a, **k: {}
    stub.render_query_result = lambda *a, **k: {}
    sys.modules["capability_registry"] = stub
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("bland_gateway.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._eastern_today = lambda: datetime(2026, 7, 27, 12, 0, 0)
    return mod


@pytest.fixture
def mod():
    return load_gateway("bland_gateway_raw")


def availability_body():
    return {"store": "711", "from": "thursday", "to": "thursday", "callID": "x"}


def test_raw_override(mod):
    mod._fetch_conversation = lambda call_id: [
        {"sender": "AGENT", "message": "What date?"},
        {"sender": "USER", "message": "Tomorrow july 28th"},
    ]
    body = availability_body()
    mod.clamp_availability_range(body)
    assert body["from"] == body["to"] == "07/28/2026"
    assert "callID" not in body


def test_fail_open(mod):
    def fail(call_id):
        raise RuntimeError("fetch failed")
    mod._fetch_conversation = fail
    body = availability_body()
    mod.clamp_availability_range(body)
    assert body["from"] == body["to"] == "07/30/2026"
    assert "callID" not in body


def test_flag_off():
    mod = load_gateway("bland_gateway_off", raw="0")
    called = []
    mod._fetch_conversation = lambda call_id: called.append(call_id)
    body = availability_body()
    mod.clamp_availability_range(body)
    assert not called
    assert "callID" not in body


def test_cvc_tenant():
    mod = load_gateway("bland_gateway_cvc", tenant="cvc")
    called = []
    mod._fetch_conversation = lambda call_id: called.append(call_id)
    body = availability_body()
    mod.clamp_availability_range(body)
    assert not called
    assert "callID" not in body


def test_no_date_latest_message(mod):
    mod._fetch_conversation = lambda call_id: [
        {"role": "USER", "content": "tomorrow"},
        {"role": "USER", "content": "1"},
    ]
    body = availability_body()
    mod.clamp_availability_range(body)
    assert body["from"] == body["to"] == "07/30/2026"
    assert "callID" not in body


def test_missing_api_key_never_opens_network(mod, monkeypatch):
    monkeypatch.delenv("ECP_BLAND_API_KEY", raising=False)

    def fail(*args, **kwargs):
        raise AssertionError("network opener must not be built")

    monkeypatch.setattr(mod.urllib.request, "build_opener", fail)
    monkeypatch.setattr(mod.urllib.request, "urlopen", fail)
    assert mod._fetch_conversation("a" * 12) is None


def test_first_available_skips_raw_fetch(mod):
    called = []
    mod._fetch_conversation = lambda call_id: called.append(call_id)
    body = {**availability_body(), "first_available": "1"}
    mod.clamp_availability_range(body)
    assert not called
    assert "callID" not in body


@pytest.mark.parametrize(
    ("tenant", "active"),
    [(" MOTT ", True), ("CVC", False), ("unknownclinic", False)],
)
def test_positive_tenant_gate(tenant, active):
    mod = load_gateway(f"bland_gateway_tenant_{tenant.strip()}", tenant=tenant)
    called = []
    mod._fetch_conversation = lambda call_id: called.append(call_id)
    body = availability_body()
    mod.clamp_availability_range(body)
    assert bool(called) is active
    assert "callID" not in body


def test_created_at_selects_newest_user_message(mod):
    messages = [
        {
            "sender": "USER",
            "message": "Wednesday",
            "created_at": "2026-07-27T15:00:00Z",
        },
        {
            "sender": "USER",
            "message": "Friday",
            "created_at": "2026-07-27T14:00:00Z",
        },
    ]
    assert mod.resolve_from_conversation(messages) == (
        "07/29/2026",
        "07/29/2026",
    )


def test_oversize_message_is_truncated_before_parsing(mod):
    message = "july 28th " + ("x" * 11990)
    started = mod.time.monotonic()
    assert mod.resolve_from_conversation(
        [{"sender": "USER", "message": message}]
    ) == ("07/28/2026", "07/28/2026")
    assert mod.time.monotonic() - started < 1
