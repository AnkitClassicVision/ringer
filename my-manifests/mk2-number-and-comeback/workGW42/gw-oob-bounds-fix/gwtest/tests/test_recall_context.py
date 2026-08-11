"""Offline coverage for Phase A recall context handling."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "container" / "bland_gateway.py"


def load_gateway():
    spec = importlib.util.spec_from_file_location("recall_context_gateway", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load gateway")
    gateway = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gateway)
    gateway.CLI = "eyecloud-pro-pp-cli"
    gateway.AWS_ENV_WRAPPER = "/not-present/eyecloud-pro-aws-env"
    gateway.API_KEY = "recall-token"
    gateway.TEST_MODE = False
    return gateway


class Completed:
    def __init__(self, payload, returncode=0, stderr=""):
        self.returncode = returncode
        self.stdout = json.dumps(payload)
        self.stderr = stderr


def post(gateway, payload):
    encoded = json.dumps(payload).encode()
    handler = gateway.Handler.__new__(gateway.Handler)
    handler.path = "/patient-search"
    handler.command = "POST"
    handler.headers = {"Authorization": "Bearer recall-token", "Content-Length": str(len(encoded))}
    handler.rfile = io.BytesIO(encoded)
    response = {}
    handler._send = lambda status, body=None: response.update(status=status, body=body)
    handler.do_POST()
    return response["status"], response["body"]


def test_recall_token_is_not_forwarded_to_cli(monkeypatch):
    gateway = load_gateway()
    calls = []
    monkeypatch.setattr(gateway.subprocess, "run", lambda argv, **_kwargs: (
        calls.append(argv) or Completed({"count": 0, "capped": False, "patients": []})
    ))
    status, _ = post(gateway, {"phone": "6785551234", "recall_token": "rc-abc"})
    assert status == 200
    assert len(calls) == 1
    assert not any("recall" in value for value in calls[0])


def test_token_only_short_circuit_has_recall_fields(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setattr(gateway.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("CLI must not run")
    ))
    status, body = post(gateway, {"recall_token": "rc-abc"})
    assert status == 200
    assert body["result"]["count"] == 0
    assert body["result"]["exam_category"] == ""
    assert body["result"]["exam_type_id"]


def test_pinned_patient_envelope_has_recall_fields(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setattr(gateway.subprocess, "run", lambda *_args, **_kwargs: Completed(
        {"patient_id": "222", "name_first": "Target"}
    ))
    status, body = post(gateway, {
        "phone": "6785551234", "patient_id": "222", "recall_token": "rc-abc",
    })
    assert status == 200
    assert body["result"]["count"] == 1
    assert body["result"]["exam_category"] == ""
    assert body["result"]["exam_type_id"]


def test_augment_search_envelope_uses_legacy_fallback(monkeypatch):
    gateway = load_gateway()
    monkeypatch.delenv("ECP_DEFAULT_APPT_TYPE", raising=False)
    monkeypatch.delenv("ECP_APPT_TYPE_MAP", raising=False)
    assert gateway.augment_search_envelope({}, "")["exam_type_id"] == "1006896092"


def test_augment_search_envelope_uses_default_override(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_DEFAULT_APPT_TYPE", "default-type")
    assert gateway.augment_search_envelope({}, "")["exam_type_id"] == "default-type"


def test_augment_search_envelope_uses_category_map(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_APPT_TYPE_MAP", json.dumps({"contact_lens:existing": "contact-type"}))
    result = gateway.augment_search_envelope({}, "contact_lens")
    assert result == {"exam_category": "contact_lens", "exam_type_id": "contact-type"}


def test_augment_search_envelope_invalid_map_falls_back(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_DEFAULT_APPT_TYPE", "default-type")
    monkeypatch.setenv("ECP_APPT_TYPE_MAP", "not-json")
    assert gateway.augment_search_envelope({}, "contact_lens")["exam_type_id"] == "default-type"


class DynamoStub:
    def __init__(self, response=None, error=None):
        self.response = response or {}
        self.error = error
        self.calls = []

    def get_item(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def install_dynamo_stub(monkeypatch, gateway, client):
    client_calls = []

    def make_client(service):
        client_calls.append(service)
        return client

    monkeypatch.setattr(gateway, "boto3", SimpleNamespace(client=make_client))
    return client_calls


def test_resolve_recall_context_hit_maps_envelope(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_RECALL_ROWS_TABLE", "recall-rows")
    monkeypatch.setenv("ECP_APPT_TYPE_MAP", json.dumps({"medical:existing": "medical-type"}))
    client = DynamoStub({"Item": {"exam_category": {"S": "medical"}}})
    client_calls = install_dynamo_stub(monkeypatch, gateway, client)

    category = gateway.resolve_recall_context("token-value", "batch-value")

    assert category == "medical"
    assert gateway.augment_search_envelope({}, category)["exam_type_id"] == "medical-type"
    assert client_calls == ["dynamodb"]
    assert client.calls == [{
        "TableName": "recall-rows",
        "Key": {
            "batch_id": {"S": "batch-value"},
            "recall_token": {"S": "token-value"},
        },
    }]


def test_resolve_recall_context_missing_item(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_RECALL_ROWS_TABLE", "recall-rows")
    client = DynamoStub({})
    install_dynamo_stub(monkeypatch, gateway, client)
    assert gateway.resolve_recall_context("token-value", "batch-value") == ""


def test_resolve_recall_context_disabled_without_client(monkeypatch):
    gateway = load_gateway()
    monkeypatch.delenv("ECP_RECALL_ROWS_TABLE", raising=False)
    client = DynamoStub({"Item": {"exam_category": {"S": "medical"}}})
    client_calls = install_dynamo_stub(monkeypatch, gateway, client)
    assert gateway.resolve_recall_context("token-value", "batch-value") == ""
    assert client_calls == []
    assert client.calls == []


def test_resolve_recall_context_invalid_stored_value(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_RECALL_ROWS_TABLE", "recall-rows")
    client = DynamoStub({"Item": {"exam_category": {"S": "not-allowed"}}})
    install_dynamo_stub(monkeypatch, gateway, client)
    assert gateway.resolve_recall_context("token-value", "batch-value") == ""


def test_resolve_recall_context_client_exception(monkeypatch):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_RECALL_ROWS_TABLE", "recall-rows")
    client = DynamoStub(error=RuntimeError("throttled"))
    install_dynamo_stub(monkeypatch, gateway, client)
    assert gateway.resolve_recall_context("token-value", "batch-value") == ""


def test_template_recall_token_is_absent():
    gateway = load_gateway()
    body = {"phone": "6785551234", "recall_token": "{{recall_token}}"}
    short, patient_id, token, batch_id = gateway.prepare_patient_search(
        body, include_recall_context=True
    )
    assert short is None
    assert patient_id == token == batch_id == ""
    assert "recall_token" not in body


def test_prepare_patient_search_still_pops_patient_id():
    gateway = load_gateway()
    body = {"phone": "6785551234", "patient_id": "222"}
    short, patient_id = gateway.prepare_patient_search(body)
    assert short is None
    assert patient_id == "222"
    assert "patient_id" not in body
