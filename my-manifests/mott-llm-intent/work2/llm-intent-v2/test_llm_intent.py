import importlib.util
import os
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest


def _stub_capability_registry():
    stub = types.ModuleType("capability_registry")

    class QueryError(Exception):
        pass

    stub.QueryError = QueryError
    stub.load_manifest = lambda *args, **kwargs: {}
    stub.prepare_query = lambda *args, **kwargs: {}
    stub.render_query_result = lambda *args, **kwargs: {}
    sys.modules["capability_registry"] = stub


def _load_gateway(name, llm_mode="authoritative"):
    _stub_capability_registry()
    os.environ["ECP_DATE_ORDINAL_FALLBACK"] = "1"
    os.environ["ECP_RAW_TEXT_DATES"] = "1"
    os.environ["ECP_TENANT_ID"] = "mott"
    os.environ["ECP_LLM_INTENT"] = llm_mode
    path = Path(__file__).with_name("bland_gateway.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module._eastern_today = lambda: datetime(2026, 7, 29, 12, 0, 0)
    return module


@pytest.fixture
def gateway():
    return _load_gateway("test_gateway_authoritative")


class FakeClient:
    def __init__(self, text):
        self.text = text

    def converse(self, **kwargs):
        return {
            "output": {
                "message": {
                    "content": [{"text": self.text}],
                }
            }
        }


def test_fenced_json_parse(gateway, monkeypatch):
    text = '```json\n{"phrase":"wednesday next week"}\n```'
    monkeypatch.setattr(gateway, "_bedrock", lambda: FakeClient(text))
    result = gateway.llm_interpret_intent(
        "hoping for something soonish", gateway._eastern_today()
    )
    assert result["intent"] == "date"
    assert result["date"] == "08/05/2026"


def test_next_weekday_derives_ambiguity(gateway, monkeypatch):
    monkeypatch.setattr(
        gateway, "_bedrock", lambda: FakeClient('{"phrase":"next friday"}')
    )
    result = gateway.llm_interpret_intent("anything", gateway._eastern_today())
    assert result["intent"] == "ambiguous"
    assert result["date"] == "07/31/2026"
    assert result["date2"] == "08/07/2026"


def test_asap_derives_range(gateway, monkeypatch):
    monkeypatch.setattr(
        gateway,
        "_bedrock",
        lambda: FakeClient('{"phrase":"as soon as possible"}'),
    )
    result = gateway.llm_interpret_intent("anything", gateway._eastern_today())
    assert result == {
        "intent": "range",
        "date": "07/30/2026",
        "date2": "08/05/2026",
    }


def test_empty_phrase_is_none(gateway, monkeypatch):
    monkeypatch.setattr(gateway, "_bedrock", lambda: FakeClient('{"phrase":""}'))
    assert gateway.llm_interpret_intent(
        "anything", gateway._eastern_today()
    ) == {"intent": "none"}


def test_garbage_reply_fails_open(gateway, monkeypatch):
    monkeypatch.setattr(gateway, "_bedrock", lambda: FakeClient("not json"))
    assert gateway.llm_interpret_intent("anything", gateway._eastern_today()) is None


def test_client_exception_fails_open(gateway, monkeypatch):
    class BrokenClient:
        def converse(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(gateway, "_bedrock", lambda: BrokenClient())
    assert gateway.llm_interpret_intent("anything", gateway._eastern_today()) is None


def _messages(text):
    return [
        {"sender": "AGENT", "message": "Which date?", "created_at": "1"},
        {"sender": "USER", "message": text, "created_at": "2"},
    ]


def _run_clamp(gateway, monkeypatch, text, verdict, body=None):
    monkeypatch.setattr(gateway, "_fetch_conversation", lambda call_id: _messages(text))
    monkeypatch.setattr(gateway, "llm_interpret_intent", lambda user_text, today: verdict)
    monkeypatch.setattr(gateway.time, "sleep", lambda seconds: None)
    body = body or {"callID": "abcdefgh", "from": "08/01/2026", "to": "08/01/2026"}
    gateway.clamp_availability_range(body)
    return body


def test_llm_fills_when_deterministic_is_none(gateway, monkeypatch, caplog):
    caplog.set_level("INFO", logger="cvc-booking-gateway")
    verdict = {
        "intent": "date", "date": "08/07/2026", "date2": "",
        "optionA": "", "optionB": "",
    }
    body = _run_clamp(gateway, monkeypatch, "hoping for something soonish", verdict)
    assert body["from"] == body["to"] == "08/07/2026"
    assert "date_source=llm" in caplog.text


def test_deterministic_wins(gateway, monkeypatch):
    verdict = {
        "intent": "date", "date": "08/07/2026", "date2": "",
        "optionA": "", "optionB": "",
    }
    body = _run_clamp(gateway, monkeypatch, "july 31st", verdict)
    assert body["from"] == body["to"] == "07/31/2026"


def test_ambiguous_fill(gateway, monkeypatch):
    verdict = {
        "intent": "ambiguous",
        "date": "07/31/2026",
        "date2": "08/07/2026",
        "optionA": "this coming Friday the 31st",
        "optionB": "next week Friday the 7th",
    }
    body = _run_clamp(gateway, monkeypatch, "hoping for something soonish", verdict)
    assert body["date_conflict"] == (
        "conflict",
        "07/31/2026",
        "08/07/2026",
        "this coming Friday the 31st",
        "next week Friday the 7th",
    )


def test_llm_exception_fails_open(gateway, monkeypatch):
    monkeypatch.setattr(
        gateway, "_fetch_conversation",
        lambda call_id: _messages("hoping for something soonish"),
    )
    monkeypatch.setattr(
        gateway, "llm_interpret_intent",
        lambda user_text, today: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(gateway.time, "sleep", lambda seconds: None)
    body = {"callID": "abcdefgh", "from": "08/01/2026", "to": "08/01/2026"}
    gateway.clamp_availability_range(body)
    assert body == {"from": "08/01/2026", "to": "08/01/2026"}


def test_off_mode_never_calls_llm(monkeypatch):
    gateway = _load_gateway("test_gateway_off", llm_mode="off")
    monkeypatch.setattr(
        gateway, "_fetch_conversation",
        lambda call_id: _messages("hoping for something soonish"),
    )
    monkeypatch.setattr(gateway.time, "sleep", lambda seconds: None)
    calls = {"count": 0}

    def counted(user_text, today):
        calls["count"] += 1
        return None

    monkeypatch.setattr(gateway, "llm_interpret_intent", counted)
    body = {"callID": "abcdefgh", "from": "08/01/2026", "to": "08/01/2026"}
    gateway.clamp_availability_range(body)
    assert calls["count"] == 0
