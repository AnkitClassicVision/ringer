from __future__ import annotations

import json
import inspect
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sms_recall_batch as sender


# The ledger helpers are client-scoped now, so a direct call has to name whose ledger
# it is reading or writing. These tests exercise CVC's profile.
CVC = sender.resolve_client("cvc-outbound-recall-manifest.v1")

NOW = datetime(2026, 7, 24, 15, 0, tzinfo=timezone.utc)
PHONE_HEADER = ["phone_e164", "consent_source", "consent_date"]
TOKEN_HEADER = PHONE_HEADER + ["recall_token"]
LEGACY_PATIENT_HEADER = TOKEN_HEADER + ["patient_id"]
PATIENT_HEADER = ["patient_id", "consent_source", "consent_date"]
PATIENT_TOKEN_HEADER = PATIENT_HEADER + ["recall_token"]


@pytest.fixture
def configured_cvc(monkeypatch):
    """Let tests unrelated to sender-line resolution exercise their original path."""
    monkeypatch.setattr(
        sender,
        "CLIENTS",
        tuple(
            replace(profile, agent_number="+12025550199")
            if profile.key == "cvc"
            else profile
            for profile in sender.CLIENTS
        ),
    )


def write_feed(tmp_path: Path, header: list[str], rows: list[list[str]]) -> Path:
    path = tmp_path / "feed.csv"
    path.write_text(",".join(header) + "\n" + "\n".join(",".join(row) for row in rows) + "\n")
    os.utime(path, (NOW.timestamp(), NOW.timestamp()))
    return path


def write_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "schema_version": sender.MANIFEST_SCHEMA,
        "pathway_name": "mott-v20",
        "pathway_id": "approved-mott-pathway",
        "version": 20,
        "voice_source_pathway_id": sender.EXPECTED_VOICE_SOURCE_PATHWAY_ID,
        "voice_source_version": sender.EXPECTED_VOICE_SOURCE_VERSION,
        "start_node_id": "n_contact_lookup",
        "time_out_hours": 72,
        "restart_after_end_call": False,
        "structural_sha256": "a" * 64,
        "created_utc": "2026-07-24T12:00:00Z",
    }))
    return path


class FakeHttp:
    def __init__(
        self,
        patient_responses: dict[str, tuple[int, Any]] | None = None,
        *,
        suppressed: set[str] | None = None,
        suppression_status: int = 200,
        suppression_body: Any = None,
        recheck: bool = False,
        recheck_status: int = 200,
        recheck_body: Any = None,
        send_status: int = 200,
        send_body: Any = None,
        outage: BaseException | None = None,
    ):
        self.patient_responses = patient_responses or {}
        self.suppressed = suppressed or set()
        self.suppression_status = suppression_status
        self.suppression_body = suppression_body
        self.recheck = recheck
        self.recheck_status = recheck_status
        self.recheck_body = recheck_body
        self.send_status = send_status
        self.send_body = {"ok": True} if send_body is None else send_body
        self.outage = outage
        self.calls: list[tuple[str, str, dict[str, Any] | None, bool | str]] = []

    def __call__(self, method: str, url: str, payload: dict[str, Any] | None, auth: bool | str):
        self.calls.append((method, url, payload, auth))
        if url.endswith("/patient-search"):
            assert auth == "gateway"
            if self.outage:
                raise sender.Refusal(f"endpoint unavailable: {type(self.outage).__name__}")
            assert payload is not None
            return self.patient_responses[payload["patient_id"]]
        if "/sms-suppression?" in url:
            assert auth == "gateway"
            body = {"suppressed": self.recheck} if self.recheck_body is None else self.recheck_body
            return self.recheck_status, body
        if url.endswith("/sms-suppression") and method == "GET":
            assert auth == "gateway"
            body = (
                {"data": [{"phone_e164": phone} for phone in sorted(self.suppressed)]}
                if self.suppression_body is None
                else self.suppression_body
            )
            return self.suppression_status, body
        if url.endswith("/v1/sms/send"):
            assert auth is True
            return self.send_status, self.send_body
        if url.endswith("/sms-suppression") and method == "POST":
            assert auth == "gateway"
            return 200, {"ok": True}
        raise AssertionError(f"unexpected HTTP call: {method} {url}")


def match(patient_id: str, mobile: Any = "+12025550123", *, count: int = 1, returned_id: str | None = None) -> tuple[int, Any]:
    patients = [] if count == 0 else [{"patient_id": returned_id or patient_id, "phone_mobile": mobile}]
    if count > 1:
        patients.append({"patient_id": patient_id, "phone_mobile": "+12025550124"})
    return 200, {"ok": True, "result": {"count": count, "patients": patients}}


def invoke(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    http: FakeHttp,
    header: list[str],
    rows: list[list[str]],
    *,
    approve: bool = False,
) -> tuple[int, str]:
    args = [
        "--feed", str(write_feed(tmp_path, header, rows)),
        "--manifest", str(write_manifest(tmp_path)),
        "--send-ledger", str(tmp_path / "ledger.json"),
    ]
    if approve:
        args.extend(["--approve", "--max-sends", "10"])
    code = sender.run(args, http=http, clock=lambda: NOW)
    return code, capsys.readouterr().out


def ledger_entry(
    phone: str,
    timestamp: str,
    *,
    status: str = "sent",
    recall_token: str | None = None,
) -> dict[str, Any]:
    return {
        "recall_token": recall_token,
        "phone_sha256": sender._phone_sha256(phone),
        "phone_last4": phone[-4:],
        "status": status,
        "timestamp": timestamp,
    }


@pytest.mark.parametrize("header,rows", [
    (PHONE_HEADER, [["+12025550123", "web_sms", "2026-07-23"]]),
    (TOKEN_HEADER, [["+12025550123", "web_sms", "2026-07-23", "ValidToken12"]]),
    (LEGACY_PATIENT_HEADER, [["+12025550123", "web_sms", "2026-07-23", "ValidToken12", "P123"]]),
    (PATIENT_HEADER, [["P123", "web_sms", "2026-07-23"]]),
    (PATIENT_TOKEN_HEADER, [["P123", "web_sms", "2026-07-23", "ValidToken12"]]),
])
def test_all_legacy_and_patient_feed_shapes_load(tmp_path, header, rows):
    loaded = sender.load_feed(write_feed(tmp_path, header, rows), 24, NOW)
    assert len(loaded) == 1


def test_unique_patient_match_enriches_and_constructs_request_data(
    tmp_path, capsys, configured_cvc
):
    http = FakeHttp({"P123": match("P123")})
    code, output = invoke(
        tmp_path, capsys, http, PATIENT_TOKEN_HEADER,
        [["P123", "web_sms", "2026-07-23", "ValidToken12"]],
        approve=True,
    )
    assert code == 0
    lookups = [call for call in http.calls if call[1].endswith("/patient-search")]
    assert lookups == [("POST", sender.PATIENT_SEARCH_URL, {"profile": "contact", "patient_id": "P123"}, "gateway")]
    sends = [call for call in http.calls if call[1].endswith("/v1/sms/send")]
    assert len(sends) == 1
    assert sends[0][2]["user_number"] == "+12025550123"
    assert sends[0][2]["request_data"] == {
        "campaign": "cvc_recall_outbound",
        "recall_token": "ValidToken12",
        "recall_patient_id": "P123",
        "recall_cell": "+12025550123",
    }
    assert output.rstrip().endswith("external_actions_taken=1")


def test_legacy_phone_plus_patient_id_does_not_claim_enrichment(
    tmp_path, capsys, configured_cvc
):
    http = FakeHttp()
    code, _ = invoke(
        tmp_path, capsys, http, LEGACY_PATIENT_HEADER,
        [["+12025550123", "web_sms", "2026-07-23", "ValidToken12", "P123"]],
        approve=True,
    )
    assert code == 0
    send = next(call for call in http.calls if call[1].endswith("/v1/sms/send"))
    assert send[2]["request_data"] == {
        "campaign": "cvc_recall_outbound",
        "recall_token": "ValidToken12",
        "recall_patient_id": "P123",
    }


@pytest.mark.parametrize("response,reason", [
    (match("P123", count=0), "patient-match-zero=1"),
    (match("P123", count=2), "patient-match-ambiguous=1"),
    (match("P123", None), "mobile-missing=1"),
    (match("P123", "2025550123"), "mobile-invalid=1"),
    (match("P123", returned_id="OTHER"), "patient-id-mismatch=1"),
])
def test_safe_enrichment_skips_are_counted_without_send(tmp_path, capsys, response, reason):
    http = FakeHttp({"P123": response})
    code, output = invoke(tmp_path, capsys, http, PATIENT_HEADER, [["P123", "web_sms", "2026-07-23"]], approve=True)
    assert code == 0
    assert reason in output and "sendable=0" in output
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


@pytest.mark.parametrize("response", [
    (200, {}),
    (200, {"ok": False, "result": {"count": 1, "patients": []}}),
    (200, {"ok": True, "result": []}),
    (200, {"ok": True, "result": {"count": "1", "patients": []}}),
    (200, {"ok": True, "result": {"count": 1, "patients": []}}),
    (503, {"ok": False}),
])
def test_malformed_or_non_200_enrichment_fails_batch_before_sms(tmp_path, capsys, response):
    http = FakeHttp({"P123": response})
    code, output = invoke(tmp_path, capsys, http, PATIENT_HEADER, [["P123", "web_sms", "2026-07-23"]], approve=True)
    assert code == 2
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)
    assert not any(call[0] == "GET" and "/sms-suppression" in call[1] for call in http.calls)
    assert output.rstrip().endswith("external_actions_taken=0")


def test_gateway_outage_fails_batch_before_sms(tmp_path, capsys):
    http = FakeHttp({"P123": match("P123")}, outage=TimeoutError())
    code, output = invoke(tmp_path, capsys, http, PATIENT_HEADER, [["P123", "web_sms", "2026-07-23"]], approve=True)
    assert code == 2
    assert len(http.calls) == 1
    assert output.rstrip().endswith("external_actions_taken=0")


def test_consent_rejection_happens_without_patient_lookup(tmp_path, capsys):
    http = FakeHttp()
    code, output = invoke(tmp_path, capsys, http, PATIENT_HEADER, [["P123", "voice_only", "2026-07-23"]], approve=True)
    assert code == 0 and "consent-refused=1" in output
    assert not any(call[1].endswith("/patient-search") for call in http.calls)
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


def test_enriched_phone_is_suppressed_before_send(tmp_path, capsys):
    http = FakeHttp({"P123": match("P123")}, suppressed={"+12025550123"})
    code, output = invoke(tmp_path, capsys, http, PATIENT_HEADER, [["P123", "web_sms", "2026-07-23"]], approve=True)
    assert code == 0 and "suppressed=1" in output
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


def test_patient_ids_dedupe_before_lookup(tmp_path, capsys):
    http = FakeHttp({"P123": match("P123")})
    code, _ = invoke(
        tmp_path, capsys, http, PATIENT_HEADER,
        [["P123", "web_sms", "2026-07-23"], ["P123", "web_sms", "2026-07-23"]],
    )
    assert code == 0
    assert len([call for call in http.calls if call[1].endswith("/patient-search")]) == 1


def test_enriched_rows_dedupe_by_phone_after_lookup(
    tmp_path, capsys, configured_cvc
):
    http = FakeHttp({"P123": match("P123"), "P456": match("P456")})
    code, output = invoke(
        tmp_path, capsys, http, PATIENT_HEADER,
        [["P123", "web_sms", "2026-07-23"], ["P456", "web_sms", "2026-07-23"]],
        approve=True,
    )
    assert code == 0 and "phone-deduplicated=1" in output
    assert len([call for call in http.calls if call[1].endswith("/v1/sms/send")]) == 1


def test_legacy_phone_suppression_frequency_quiet_hours_and_recheck_remain(tmp_path, capsys):
    http = FakeHttp(recheck=True)
    code, _ = invoke(tmp_path, capsys, http, PHONE_HEADER, [["+12025550123", "web_sms", "2026-07-23"]], approve=True)
    assert code == 0
    assert any("/sms-suppression?" in call[1] for call in http.calls)
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)
    local = datetime(2026, 7, 24, 9, 59, tzinfo=sender.ZoneInfo(sender.TIMEZONE))
    assert sender.within_quiet_hours(local) is False


def test_sender_logs_phone_only_as_hash_and_last_four(caplog):
    http = FakeHttp()
    with caplog.at_level("INFO"):
        sender.record_opt_out("+12025550123", "stop", http)
    assert "+12025550123" not in caplog.text
    assert "0123" in caplog.text
    assert sender._phone_sha256("+12025550123") in caplog.text


@pytest.mark.parametrize("header", [
    PHONE_HEADER + ["foo"],
    PHONE_HEADER + ["patient_name"],
    PHONE_HEADER + ["patient_id"],
])
def test_legacy_feed_schema_refuses_unapproved_columns(tmp_path, header):
    row = ["+12025550123", "web_sms", "2026-07-23", "x"]
    with pytest.raises(sender.Refusal):
        sender.load_feed(write_feed(tmp_path, header, [row]), 24, NOW)


def test_legacy_bad_e164_and_stale_feed_refuse(tmp_path):
    with pytest.raises(sender.Refusal, match="E.164"):
        sender.load_feed(
            write_feed(tmp_path, PHONE_HEADER, [["2025550123", "web_sms", "2026-07-23"]]),
            24,
            NOW,
        )
    stale = write_feed(
        tmp_path,
        PHONE_HEADER,
        [["+12025550123", "web_sms", "2026-07-23"]],
    )
    os.utime(stale, (NOW.timestamp() - 25 * 3600, NOW.timestamp() - 25 * 3600))
    with pytest.raises(sender.Refusal, match="freshness"):
        sender.load_feed(stale, 24, NOW)


def test_manifest_schema_and_voice_pins_remain_fail_closed(tmp_path):
    path = write_manifest(tmp_path)
    expected = json.loads(path.read_text())
    assert sender.load_manifest(path) == expected
    for field, bad in (
        ("schema_version", "old-schema"),
        ("voice_source_pathway_id", "wrong-source"),
        ("voice_source_version", 52),
    ):
        value = dict(expected)
        value[field] = bad
        path.write_text(json.dumps(value))
        with pytest.raises(sender.Refusal):
            sender.load_manifest(path)


@pytest.mark.parametrize("status", [404, 503])
def test_legacy_bulk_suppression_error_blocks_send(tmp_path, capsys, status):
    http = FakeHttp(suppression_status=status)
    code, output = invoke(
        tmp_path,
        capsys,
        http,
        PHONE_HEADER,
        [["+12025550123", "web_sms", "2026-07-23"]],
        approve=True,
    )
    assert code == 2
    assert output.rstrip().endswith("external_actions_taken=0")
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


@pytest.mark.parametrize("body", [{}, {"ok": True}, {"error": "x"}])
def test_legacy_malformed_bulk_suppression_blocks_send(tmp_path, capsys, body):
    http = FakeHttp(suppression_body=body)
    code, output = invoke(
        tmp_path,
        capsys,
        http,
        PHONE_HEADER,
        [["+12025550123", "web_sms", "2026-07-23"]],
        approve=True,
    )
    assert code == 2
    assert output.rstrip().endswith("external_actions_taken=0")
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


@pytest.mark.parametrize("status,body", [
    (404, {"suppressed": False}),
    (200, {}),
    (200, {"ok": True}),
])
def test_legacy_immediate_suppression_recheck_blocks_on_error(
    tmp_path, capsys, status, body
):
    http = FakeHttp(recheck_status=status, recheck_body=body)
    code, output = invoke(
        tmp_path,
        capsys,
        http,
        PHONE_HEADER,
        [["+12025550123", "web_sms", "2026-07-23"]],
        approve=True,
    )
    assert code == 2
    assert output.rstrip().endswith("external_actions_taken=0")
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


def test_legacy_frequency_cap_and_old_send_behavior(
    tmp_path, capsys, configured_cvc
):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({
        "schema_version": sender.SEND_LEDGER_SCHEMA,
        "sends": [ledger_entry("+12025550123", "2026-07-20T15:00:00+00:00")],
    }))
    http = FakeHttp()
    args = [
        "--feed", str(write_feed(
            tmp_path,
            PHONE_HEADER,
            [["+12025550123", "web_sms", "2026-07-23"]],
        )),
        "--manifest", str(write_manifest(tmp_path)),
        "--send-ledger", str(ledger),
        "--approve",
        "--max-sends", "1",
    ]
    assert sender.run(args, http=http, clock=lambda: NOW) == 0
    output = capsys.readouterr().out
    assert "frequency-refused=1" in output
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)

    ledger.write_text(json.dumps({
        "schema_version": sender.SEND_LEDGER_SCHEMA,
        "sends": [ledger_entry("+12025550123", "2026-06-01T15:00:00+00:00")],
    }))
    http = FakeHttp()
    assert sender.run(args, http=http, clock=lambda: NOW) == 0
    capsys.readouterr()
    assert len([call for call in http.calls if call[1].endswith("/v1/sms/send")]) == 1
    assert len(sender.load_send_ledger(ledger, CVC)) == 2


def test_frequency_cap_keys_by_recall_token():
    sends = [
        ledger_entry(
            "+12025550123",
            "2026-07-20T15:00:00+00:00",
            recall_token="SameToken_123",
        )
    ]
    assert sender.frequency_capped(
        "+12025550999",
        sends,
        NOW,
        30,
        recall_token="SameToken_123",
    )


def test_concurrent_pending_reservations_preserve_both_entries(tmp_path):
    ledger = tmp_path / "ledger.json"
    barrier = Barrier(2)

    def reserve(item):
        phone, token = item
        local: list[dict[str, Any]] = []
        barrier.wait()
        return sender.reserve_pending_send(ledger, local, phone, token, NOW, 30, CVC)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, [
            ("+12025550123", "TokenOne_123"),
            ("+12025550124", "TokenTwo_123"),
        ]))
    assert results == [True, True]
    assert len(sender.load_send_ledger(ledger, CVC)) == 2


def test_approval_and_max_send_gates_remain(tmp_path, capsys):
    feed = write_feed(
        tmp_path,
        PHONE_HEADER,
        [
            ["+12025550123", "web_sms", "2026-07-23"],
            ["+12025550124", "web_sms", "2026-07-23"],
        ],
    )
    common = [
        "--feed", str(feed),
        "--manifest", str(write_manifest(tmp_path)),
        "--send-ledger", str(tmp_path / "ledger.json"),
    ]
    http = FakeHttp()
    assert sender.run(common + ["--approve"], http=http, clock=lambda: NOW) == 2
    output = capsys.readouterr().out
    assert "sendable=2" in output
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)

    http = FakeHttp()
    assert sender.run(
        common + ["--approve", "--max-sends", "1"],
        http=http,
        clock=lambda: NOW,
    ) == 2
    capsys.readouterr()
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


def invoke_approved_at(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    http: FakeHttp,
    now: datetime,
) -> tuple[int, str]:
    feed = write_feed(
        tmp_path,
        PHONE_HEADER,
        [["+12025550123", "web_sms", "2026-07-23"]],
    )
    os.utime(feed, (now.timestamp(), now.timestamp()))
    args = [
        "--feed", str(feed),
        "--manifest", str(write_manifest(tmp_path)),
        "--send-ledger", str(tmp_path / "ledger.json"),
        "--approve",
        "--max-sends", "1",
    ]
    code = sender.run(args, http=http, clock=lambda: now)
    return code, capsys.readouterr().out


def test_sunday_approve_refuses_before_sms_send(
    tmp_path, capsys, caplog, configured_cvc
):
    sunday = datetime(2026, 7, 26, 15, 0, tzinfo=timezone.utc)
    http = FakeHttp()
    with caplog.at_level("ERROR", logger="sms_recall_batch"):
        code, output = invoke_approved_at(tmp_path, capsys, http, sunday)
    assert code == 2
    assert "weekend outbound sends are blocked by policy" in caplog.text
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)
    assert output.rstrip().endswith("external_actions_taken=0")


def test_saturday_approve_refuses_before_sms_send(
    tmp_path, capsys, caplog, configured_cvc
):
    saturday = datetime(2026, 7, 25, 15, 0, tzinfo=timezone.utc)
    http = FakeHttp()
    with caplog.at_level("ERROR", logger="sms_recall_batch"):
        code, output = invoke_approved_at(tmp_path, capsys, http, saturday)
    assert code == 2
    assert "weekend outbound sends are blocked by policy" in caplog.text
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)
    assert output.rstrip().endswith("external_actions_taken=0")


def test_weekend_gate_allows_monday_approve_to_send_once(
    tmp_path, capsys, configured_cvc
):
    monday = datetime(2026, 7, 27, 15, 0, tzinfo=timezone.utc)
    http = FakeHttp()
    code, output = invoke_approved_at(tmp_path, capsys, http, monday)
    assert code == 0
    assert len([call for call in http.calls if call[1].endswith("/v1/sms/send")]) == 1
    assert output.rstrip().endswith("external_actions_taken=1")


def test_legacy_phone_send_payload_remains_non_phi(
    tmp_path, capsys, configured_cvc
):
    http = FakeHttp()
    code, output = invoke(
        tmp_path,
        capsys,
        http,
        PHONE_HEADER,
        [["+12025550123", "web_sms", "2026-07-23"]],
        approve=True,
    )
    assert code == 0
    send = next(call for call in http.calls if call[1].endswith("/v1/sms/send"))
    assert send[2]["request_data"] == {"campaign": "cvc_recall_outbound"}
    assert send[2]["start_node_id"] == "n_contact_lookup"
    assert output.rstrip().endswith("external_actions_taken=1")


@pytest.mark.parametrize("reason", sorted(sender.ALLOWED_OPT_OUT_REASONS))
def test_legacy_opt_out_contract(reason):
    http = FakeHttp()
    sender.record_opt_out("+12025550123", reason, http)
    assert http.calls[-1] == (
        "POST",
        f"{sender.GATEWAY}/sms-suppression",
        {
            "phone_e164": "+12025550123",
            "reason": reason,
            "source": "sms_recall_batch",
        },
        "gateway",
    )


@pytest.mark.parametrize("hour,minute,allowed", [
    (9, 59, False),
    (10, 0, True),
    (17, 59, True),
    (18, 0, False),
])
def test_legacy_quiet_hour_boundaries(hour, minute, allowed):
    local = datetime(
        2026,
        7,
        24,
        hour,
        minute,
        tzinfo=sender.ZoneInfo(sender.TIMEZONE),
    )
    assert sender.within_quiet_hours(local) is allowed


@pytest.mark.parametrize("bad", ["short", "has space", "bad!char", "x" * 129])
def test_malformed_tokens_are_counted_and_never_logged(
    tmp_path, capsys, caplog, bad
):
    http = FakeHttp()
    with caplog.at_level("DEBUG", logger="sms_recall_batch"):
        code, output = invoke(
            tmp_path,
            capsys,
            http,
            TOKEN_HEADER,
            [["+12025550123", "web_sms", "2026-07-23", bad]],
            approve=True,
        )
    assert code == 0
    assert "token-refused=1" in output
    assert bad not in caplog.text
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


@pytest.mark.parametrize("body", [
    {},
    {"status": "error"},
    {"error": "x"},
    {"ok": True, "status": "error"},
])
def test_ambiguous_sms_send_retains_pending_reconciliation(
    tmp_path, capsys, body, configured_cvc
):
    http = FakeHttp(send_body=body)
    code, output = invoke(
        tmp_path,
        capsys,
        http,
        TOKEN_HEADER,
        [["+12025550123", "web_sms", "2026-07-23", "OpaqueToken_777"]],
        approve=True,
    )
    assert code == 2
    sends = sender.load_send_ledger(tmp_path / "ledger.json", CVC)
    assert sends[0]["status"] == "pending"
    assert "phone_e164" not in sends[0]
    assert output.rstrip().endswith("external_actions_taken=0")


def test_crash_reconciliation_prevents_duplicate_send(
    tmp_path, capsys, monkeypatch, configured_cvc
):
    http = FakeHttp()
    original = sender.mark_send_sent

    def crash(*args, **kwargs):
        raise sender.Refusal("simulated ledger flip failure")

    monkeypatch.setattr(sender, "mark_send_sent", crash)
    code, _ = invoke(
        tmp_path,
        capsys,
        http,
        TOKEN_HEADER,
        [["+12025550123", "web_sms", "2026-07-23", "CrashToken_123"]],
        approve=True,
    )
    assert code == 2
    assert len([call for call in http.calls if call[1].endswith("/v1/sms/send")]) == 1

    monkeypatch.setattr(sender, "mark_send_sent", original)
    http = FakeHttp()
    code, output = invoke(
        tmp_path,
        capsys,
        http,
        TOKEN_HEADER,
        [["+12025550123", "web_sms", "2026-07-23", "CrashToken_123"]],
        approve=True,
    )
    assert code == 0
    assert "pending-reconciliation=1" in output
    assert not any(call[1].endswith("/v1/sms/send") for call in http.calls)


@pytest.mark.parametrize("body,reason", [
    ({"ok": True, "result": {"count": 0}}, "patient_match_zero"),
    ({"ok": True, "result": {"count": 2}}, "patient_match_ambiguous"),
])
def test_zero_and_ambiguous_count_skip_without_array(body, reason):
    mobile, actual = sender._parse_enrichment(body, "P123")
    assert mobile is None
    assert actual == reason


def test_post_enrichment_dedupe_prefers_identity_context():
    legacy = sender.FeedRow(
        "+12025550123",
        "web_sms",
        "2026-07-23",
        "LegacyToken_12",
    )
    patient = sender.FeedRow(
        None,
        "web_sms",
        "2026-07-23",
        "PatientToken_12",
        "P123",
    )
    http = FakeHttp({"P123": match("P123")})
    rows, reasons = sender.enrich_patient_rows([legacy, patient], http)
    assert len(rows) == 1
    assert rows[0].enriched is True
    assert rows[0].patient_id == "P123"
    assert reasons == {"phone_deduplicated": 1}


# --- multi-practice manifests -------------------------------------------------
# The sender used to be pinned to one practice in five places, so a second practice's
# job was refused outright rather than merely mislabelled. These lock in that each
# practice keeps its own pins and that the two cannot be crossed.

def _mott() -> dict[str, Any]:
    return mott_manifest()


def _write(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_both_practices_load_and_keep_their_own_start_nodes(tmp_path: Path) -> None:
    mott = sender.load_manifest(_write(tmp_path, mott_manifest()))
    cvc = sender.load_manifest(_write(tmp_path, cvc_manifest()))
    assert mott["start_node_id"] == "n_identity"
    assert cvc["start_node_id"] != mott["start_node_id"]


def test_each_practice_gets_its_own_campaign_tag() -> None:
    mott = sender.resolve_client("mott-outbound-recall-manifest.v1").campaign
    cvc = sender.resolve_client("cvc-outbound-recall-manifest.v1").campaign
    assert mott == "mott_recall_outbound"
    assert cvc == "cvc_recall_outbound"
    assert mott != cvc


def test_a_practice_cannot_borrow_another_practices_start_node(tmp_path: Path) -> None:
    data = _mott()
    data["start_node_id"] = "n_recall_lookup"  # the other practice's entry point
    with pytest.raises(sender.Refusal):
        sender.load_manifest(_write(tmp_path, data))


def test_unpinned_practice_cannot_smuggle_in_a_voice_source(tmp_path: Path) -> None:
    data = _mott()
    data["voice_source_pathway_id"] = "128fe6af-1843-4924-b071-6e19f729b056"
    with pytest.raises(sender.Refusal):
        sender.load_manifest(_write(tmp_path, data))


def test_unknown_schema_is_refused_rather_than_defaulted(tmp_path: Path) -> None:
    data = _mott()
    data["schema_version"] = "someone-elses-recall-manifest.v1"
    with pytest.raises(sender.Refusal):
        sender.load_manifest(_write(tmp_path, data))


def test_pinned_practice_still_enforces_its_voice_source(tmp_path: Path) -> None:
    data = cvc_manifest()
    data["voice_source_version"] = data["voice_source_version"] + 1
    with pytest.raises(sender.Refusal):
        sender.load_manifest(_write(tmp_path, data))


MOTT = sender.resolve_client("mott-outbound-recall-manifest.v1")


def test_each_practice_has_its_own_ledger_identity():
    """The two practices must not be able to share a send ledger.

    The ledger is the frequency cap and the duplicate-send guard, keyed by phone hash.
    One shared file means a send to a patient of one clinic silently suppresses the
    other clinic's send to the same person, and puts both practices' phone hashes in
    one artifact. Distinct schema and distinct default path are what prevent that.
    """
    assert CVC.send_ledger_schema != MOTT.send_ledger_schema
    assert CVC.send_ledger_path != MOTT.send_ledger_path
    assert CVC.campaign != MOTT.campaign


def test_ledger_written_for_one_practice_is_refused_for_the_other(tmp_path: Path):
    """Cross-practice ledger use fails closed instead of merging send histories."""
    ledger = tmp_path / "ledger.json"

    ledger.write_text(json.dumps({
        "schema_version": CVC.send_ledger_schema,
        "sends": [ledger_entry("+12025550123", "2026-07-24T12:00:00+00:00")],
    }))
    assert len(sender.load_send_ledger(ledger, CVC)) == 1
    with pytest.raises(sender.Refusal, match="invalid send ledger schema"):
        sender.load_send_ledger(ledger, MOTT)

    ledger.write_text(json.dumps({
        "schema_version": MOTT.send_ledger_schema,
        "sends": [ledger_entry("+12025550123", "2026-07-24T12:00:00+00:00")],
    }))
    assert len(sender.load_send_ledger(ledger, MOTT)) == 1
    with pytest.raises(sender.Refusal, match="invalid send ledger schema"):
        sender.load_send_ledger(ledger, CVC)


def test_ledger_writes_carry_the_running_practice_schema(tmp_path: Path):
    """A Mott send must not stamp CVC's schema onto the file it creates."""
    ledger = tmp_path / "mott_ledger.json"
    assert sender.reserve_pending_send(
        ledger, [], "+12025550123", None, NOW, 30, MOTT) is True
    written = json.loads(ledger.read_text())
    assert written["schema_version"] == MOTT.send_ledger_schema
    assert written["schema_version"] != sender.SEND_LEDGER_SCHEMA

    sender.mark_send_sent(ledger, sender.load_send_ledger(ledger, MOTT),
                          "+12025550123", None, NOW, MOTT)
    assert json.loads(ledger.read_text())["schema_version"] == MOTT.send_ledger_schema


def mott_manifest() -> dict[str, Any]:
    return {
        "schema_version": MOTT.schema,
        "pathway_name": "Mott Optical recall (SMS)",
        "pathway_id": "approved-mott-pathway",
        "version": 55,
        "voice_source_pathway_id": "",
        "voice_source_version": 0,
        "start_node_id": "n_identity",
        "time_out_hours": 72,
        "restart_after_end_call": False,
        "structural_sha256": "b" * 64,
        "created_utc": "2026-07-26T12:00:00Z",
    }


def cvc_manifest() -> dict[str, Any]:
    return {
        "schema_version": sender.MANIFEST_SCHEMA,
        "pathway_name": "cvc-recall",
        "pathway_id": "approved-cvc-pathway",
        "version": 53,
        "voice_source_pathway_id": sender.EXPECTED_VOICE_SOURCE_PATHWAY_ID,
        "voice_source_version": sender.EXPECTED_VOICE_SOURCE_VERSION,
        "start_node_id": "n_contact_lookup",
        "time_out_hours": 72,
        "restart_after_end_call": False,
        "structural_sha256": "a" * 64,
        "created_utc": "2026-07-24T12:00:00Z",
    }


def sms_payload(http: FakeHttp) -> dict[str, Any]:
    return next(call for call in http.calls if call[1].endswith("/v1/sms/send"))[2]


def test_mott_send_uses_exact_measured_contract_and_required_request_data():
    """Mott's n_identity refuses on store == "" and its availability body interpolates
    the store variable directly, so a send without it dead-ends or posts a null and the
    gateway rejects it. The scenario harness supplies store from its own environment,
    which is exactly why this gap stayed invisible to every chat-endpoint run."""
    http = FakeHttp()
    sender.send_one("+12025550123", mott_manifest(), http, "ValidToken12", "P123", "+12025550123")
    payload = sms_payload(http)
    assert http.calls[-1][0:2] == ("POST", f"{sender.API_BASE}/v1/sms/send")
    assert set(payload) == {
        "user_number",
        "agent_number",
        "new_conversation",
        "start_node_id",
        "request_data",
    }
    assert "agent_message" not in payload
    assert payload["user_number"] == "+12025550123"
    assert payload["agent_number"] == "+15095611012"
    assert payload["new_conversation"] is True
    assert payload["start_node_id"] == "n_identity"
    assert payload["request_data"] == {
        "campaign": "mott_recall_outbound",
        "store": "711",
        "recall_token": "ValidToken12",
        "recall_patient_id": "P123",
        "recall_cell": "+12025550123",
    }


def test_mott_agent_number_comes_from_profile_not_send_function_literal():
    assert MOTT.agent_number == "+15095611012"
    assert "+15095611012" not in inspect.getsource(sender.send_one)


def test_profile_without_agent_number_refuses_without_transport_call():
    assert CVC.agent_number is None
    http = FakeHttp()
    with pytest.raises(sender.Refusal, match="has no SMS agent_number; refusing send"):
        sender.send_one("+12025550123", cvc_manifest(), http)
    assert http.calls == []


def test_cvc_store_shape_remains_unchanged_when_sender_line_is_configured(
    configured_cvc,
):
    """A configured CVC profile still must not grow a store variable."""
    assert CVC.store is None
    http = FakeHttp()
    sender.send_one("+12025550123", cvc_manifest(), http, "ValidToken12", "P123", None)
    payload = sms_payload(http)
    assert "store" not in payload["request_data"]
    assert set(payload["request_data"]) == {"campaign", "recall_token", "recall_patient_id"}


def test_bulk_suppression_404_names_missing_read_endpoint():
    http = FakeHttp(suppression_status=404)
    with pytest.raises(
        sender.Refusal, match="gateway serves no suppression read endpoint"
    ):
        sender.bulk_suppressions(http)


def test_suppression_recheck_404_names_missing_read_endpoint():
    http = FakeHttp(recheck_status=404)
    with pytest.raises(
        sender.Refusal, match="gateway serves no suppression read endpoint"
    ):
        sender.is_suppressed("+12025550123", http)
