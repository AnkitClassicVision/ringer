"""Handler-level contracts for reviewed EyeCloud webhook capabilities."""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import multiprocessing
from pathlib import Path
import subprocess
import threading
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_gateway():
    spec = importlib.util.spec_from_file_location(
        f"webhook_gateway_{id(object())}",
        ROOT / "container/bland_gateway.py",
    )
    gateway = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(gateway)
    gateway.CLI = "eyecloud-pro-pp-cli"
    gateway.AWS_ENV_WRAPPER = "/not-present"
    gateway.API_KEY = "synthetic-token"
    gateway.READ_PRINCIPAL = "bland-read"
    gateway.TENANT_ID = "synthetic-tenant"
    gateway.QUERY_CREDENTIAL = {
        "token": "synthetic-token",
        "tenant": "synthetic-tenant",
        "principal": "bland-read",
    }
    return gateway


class Completed:
    def __init__(self, payload, returncode=0):
        self.returncode = returncode
        self.stdout = json.dumps(payload)
        self.stderr = ""


def _hold_exclusive_file_lock(lock_path, ready, release):
    import fcntl

    with open(lock_path, "a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        ready.set()
        release.wait(timeout=5)


def _start_exclusive_file_lock_holder(lock_path):
    ctx = multiprocessing.get_context("fork")
    ready = ctx.Event()
    release = ctx.Event()
    holder = ctx.Process(
        target=_hold_exclusive_file_lock,
        args=(str(lock_path), ready, release),
    )
    holder.start()
    assert ready.wait(timeout=1)
    return holder, release


def _release_file_lock_holder(holder, release):
    release.set()
    holder.join(timeout=2)
    if holder.is_alive():
        holder.terminate()
        holder.join(timeout=1)
    assert holder.exitcode == 0


def post(gateway, path, payload, token="synthetic-token"):
    encoded = json.dumps(payload).encode()
    handler = gateway.Handler.__new__(gateway.Handler)
    handler.path = path
    handler.command = "POST"
    handler.headers = {
        "Authorization": f"Bearer {token}",
        "Content-Length": str(len(encoded)),
    }
    handler.rfile = io.BytesIO(encoded)
    response = {}
    handler._send = lambda status, body=None: response.update(status=status, body=body)
    handler.do_POST()
    return response["status"], response["body"]


def test_patient_direct_id_profiles_and_sensitive_withholding(monkeypatch):
    gateway = load_gateway()
    gateway.TEST_MODE = True
    gateway.TEST_PATIENT_IDS = {"1001"}
    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        return Completed({
            "patient_id": "1001",
            "store_id": "958",
            "fields": {
                "name_first": "Test",
                "name_last": "Patient",
                "phone_mobile": "5550000000",
                "email": "synthetic@example.invalid",
                "city": "Testville",
                "ssn": "withhold-me",
                "chart": "withhold-me",
                "insurance": {"member_id": "withhold-me"},
            },
        })

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    status, body = post(gateway, "/patient-search", {
        "patient_id": "1001",
        "profile": "full_demographics",
        "phone": "{{phone_number}}",
    })

    assert status == 200
    assert calls[0][-1] == "1001"
    result = body["result"]
    assert result["query_mode"] == "patient_id"
    assert result["profile"] == "full_demographics"
    assert result["sensitive_withheld"] == ["ssn"]
    assert result["patients"][0]["city"] == "Testville"
    serialized = json.dumps(result)
    assert "withhold-me" not in serialized
    assert "ssn" in serialized


@pytest.mark.parametrize("patient_id", ["abc", "-1", "1.2"])
def test_patient_malformed_id_fails_closed(patient_id):
    gateway = load_gateway()
    status, _ = post(gateway, "/patient-search", {"patient_id": patient_id})
    assert status == 400


def test_patient_synthetic_id_denial_and_unknown_direct_id(monkeypatch):
    gateway = load_gateway()
    gateway.TEST_MODE = True
    gateway.TEST_PATIENT_IDS = {"1001"}
    assert post(gateway, "/patient-search", {"patient_id": "9999"})[0] == 403

    gateway.TEST_MODE = False
    monkeypatch.setattr(gateway.subprocess, "run", lambda *_a, **_k: Completed({}, 1))
    status, body = post(gateway, "/patient-search", {"patient_id": "9999"})
    assert status == 200
    assert body["result"]["count"] == 0


def test_patient_template_stripping_and_insufficient_search_avoid_cli(monkeypatch):
    gateway = load_gateway()
    called = False

    def fake_run(*_args, **_kwargs):
        nonlocal called
        called = True
        return Completed({})

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    status, body = post(gateway, "/patient-search", {
        "first": "Only",
        "dob": "{{date_of_birth}}",
        "profile": "{{patient_profile}}",
    })
    assert status == 200
    assert body["result"]["count"] == 0
    assert called is False


def test_exact_single_hydrates_but_filtered_multi_match_never_does(monkeypatch):
    gateway = load_gateway()
    gateway.TEST_MODE = True
    calls = []
    search_payload = {
        "count": 1,
        "capped": False,
        "patients": [{"patient_id": "1001", "name_last": "ZZTEST"}],
    }

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if argv[2] == "patient-search":
            return Completed(search_payload)
        return Completed({"patient_id": "1001", "fields": {"name_last": "ZZTEST", "email": "x@y.invalid"}})

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    status, body = post(gateway, "/patient-search", {
        "last": "ZZTEST",
        "dob": "01/01/1990",
        "profile": "contact",
    })
    assert status == 200
    assert body["result"]["profile"] == "contact"
    assert len(calls) == 2

    calls.clear()
    search_payload.update({
        "count": 2,
        "patients": [
            {"patient_id": "1001", "name_last": "ZZTEST"},
            {"patient_id": "2002", "name_last": "OTHER"},
        ],
    })
    status, body = post(gateway, "/patient-search", {
        "last": "ZZTEST",
        "dob": "01/01/1990",
        "profile": "contact",
    })
    assert status == 200
    assert body["result"]["count"] == 1
    assert body["result"]["profile"] == "identity"
    assert len(calls) == 1
    assert "email" not in body["result"]["patients"][0]


def test_appointment_read_regressions_preserve_complete_data_and_metadata(monkeypatch):
    gateway = load_gateway()

    def fake_run(argv, **_kwargs):
        command = argv[2]
        if command == "availability":
            return Completed([
                {"start": "07/25/2026 09:00 am", "end": "07/25/2026 09:30 am", "doctor_id": "D1"},
                {"start": "07/25/2026 10:00 am", "end": "07/25/2026 10:30 am", "doctor_id": "D2"},
            ])
        if command == "list":
            return Completed({
                "appointments": [{"id": "A1", "start": "07/25/2026 09:00 am", "store": "958"}],
                "capped": False,
                "next_cursor": "",
                "store": "958",
                "unapproved": "drop",
            })
        return Completed({"conflict": True, "overlap_ids": ["A1"], "appointments": [{"id": "A1"}]})

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    status, availability = post(gateway, "/availability", {
        "store": "958", "from": "07/25/2026", "to": "07/25/2026",
    })
    assert status == 200
    assert availability["result"]["count"] == 2
    assert len(availability["result"]["slots"]) == 2
    assert availability["result"]["first_start"] == availability["result"]["slots"][0]["start"]

    status, listed = post(gateway, "/appt-list", {"patient_id": "1001", "store": "958"})
    assert status == 200
    assert listed["result"]["count"] == 1
    assert listed["result"]["store"] == "958"
    assert listed["result"]["capped"] is False
    assert "unapproved" not in listed["result"]

    status, conflict = post(gateway, "/conflict-check", {
        "store": "958",
        "start": "07/25/2026 09:00 am",
        "end": "07/25/2026 09:30 am",
    })
    assert status == 200
    assert conflict["result"]["overlap_ids"] == ["A1"]


def test_appt_list_propagates_all_filters(monkeypatch):
    gateway = load_gateway()
    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if argv[2] == "patient-search":
            return Completed({
                "count": 1,
                "capped": False,
                "patients": [{"patient_id": "2002", "name_last": "SYNTHETIC"}],
            })
        return Completed({
            "appointments": [
                {
                    "id": "APPT-SYNTHETIC",
                    "start": "07/25/2026 09:00 am",
                    "store": "958",
                    "status": "scheduled",
                }
            ],
            "capped": False,
            "has_more": False,
            "next_cursor": "cursor-synthetic",
            "total": 1,
            "total_count": 1,
            "from": "07/01/2026",
            "to": "07/31/2026",
            "store": "958",
            "include_past": True,
        })

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    filters = {
        "store": "958",
        "from": "07/01/2026",
        "to": "07/31/2026",
        "include_past": True,
    }

    status, direct = post(
        gateway, "/appt-list", {"patient_id": "1001", **filters}
    )
    assert status == 200
    direct_argv = calls[-1]
    assert ["--store", "958"] == direct_argv[
        direct_argv.index("--store"):direct_argv.index("--store") + 2
    ]
    assert ["--from", "07/01/2026"] == direct_argv[
        direct_argv.index("--from"):direct_argv.index("--from") + 2
    ]
    assert ["--to", "07/31/2026"] == direct_argv[
        direct_argv.index("--to"):direct_argv.index("--to") + 2
    ]
    assert "--include-past" in direct_argv
    assert direct["result"] == {
        "capped": False,
        "has_more": False,
        "next_cursor": "cursor-synthetic",
        "total": 1,
        "total_count": 1,
        "from": "07/01/2026",
        "to": "07/31/2026",
        "store": "958",
        "include_past": True,
        "count": 1,
        "appointments": [{
            "id": "APPT-SYNTHETIC",
            "start": "07/25/2026 09:00 am",
            "store": "958",
            "status": "scheduled",
        }],
    }

    calls.clear()
    status, demographic = post(
        gateway,
        "/appt-list",
        {"last": "SYNTHETIC", "dob": "01/01/1990", **filters},
    )
    assert status == 200
    list_argv = next(argv for argv in calls if argv[2] == "list")
    assert ["--store", "958"] == list_argv[
        list_argv.index("--store"):list_argv.index("--store") + 2
    ]
    assert ["--from", "07/01/2026"] == list_argv[
        list_argv.index("--from"):list_argv.index("--from") + 2
    ]
    assert ["--to", "07/31/2026"] == list_argv[
        list_argv.index("--to"):list_argv.index("--to") + 2
    ]
    assert "--include-past" in list_argv
    assert demographic["result"]["count"] == 1
    assert demographic["result"]["appointments"][0]["status"] == "scheduled"
    assert demographic["result"]["source_metadata"] == [{
        "capped": False,
        "has_more": False,
        "next_cursor": "cursor-synthetic",
        "total": 1,
        "total_count": 1,
        "from": "07/01/2026",
        "to": "07/31/2026",
        "store": "958",
        "include_past": True,
    }]


def test_availability_preserves_convenience_fields(monkeypatch):
    gateway = load_gateway()
    primary_slots = [
        {
            "start": "07/25/2026 09:00 am",
            "end": "07/25/2026 09:30 am",
            "doctor_id": "DOCTOR-SYNTHETIC-1",
            "extra": "preserved",
        },
        {
            "start": "07/25/2026 10:00 am",
            "end": "07/25/2026 10:30 am",
            "doctor_id": "DOCTOR-SYNTHETIC-2",
        },
    ]
    monkeypatch.setattr(
        gateway.subprocess, "run", lambda *_a, **_k: Completed(primary_slots)
    )

    status, primary = post(gateway, "/availability", {
        "store": "958", "from": "07/25/2026", "to": "07/25/2026",
    })
    assert status == 200
    assert primary["result"]["slots"] == [
        {**slot, "day_name": "Saturday"} for slot in primary_slots
    ]
    assert primary["result"]["first_start"] == "07/25/2026 09:00 am"
    assert primary["result"]["first_end"] == "07/25/2026 09:30 am"
    assert primary["result"]["first_doctor"] == "DOCTOR-SYNTHETIC-1"
    assert primary["result"]["alt_store"] == ""
    assert primary["result"]["alt_count"] == 0
    assert primary["result"]["alt_first_start"] == ""

    results = iter([
        Completed([]),
        Completed([{
            "start": "07/26/2026 11:00 am",
            "end": "07/26/2026 11:30 am",
            "doctor_id": "DOCTOR-SYNTHETIC-ALT",
        }]),
    ])
    monkeypatch.setattr(
        gateway.subprocess, "run", lambda *_a, **_k: next(results)
    )
    status, alternate = post(gateway, "/availability", {
        "store": "958", "from": "07/26/2026", "to": "07/26/2026",
    })
    assert status == 200
    assert alternate["result"]["slots"] == [
        {"start": "", "end": "", "doctor_id": "", "day_name": "",
         "store_id": "", "store_name": ""},
        {"start": "", "end": "", "doctor_id": "", "day_name": "",
         "store_id": "", "store_name": ""},
    ]
    assert alternate["result"]["alt_store"] == "Kennesaw"
    assert alternate["result"]["alt_count"] == 1
    assert alternate["result"]["alt_first_start"] == "07/26/2026 11:00 am"


def test_query_timeout_includes_session_lock_wait(monkeypatch):
    gateway = load_gateway()
    holder_entered = threading.Event()
    release_holder = threading.Event()

    def hold_login_lock():
        with gateway.SESSION_LOCK.login():
            holder_entered.set()
            release_holder.wait(timeout=2)

    holder = threading.Thread(target=hold_login_lock)
    holder.start()
    assert holder_entered.wait(timeout=1)

    subprocess_reached = False

    def fail_if_run(*_args, **_kwargs):
        nonlocal subprocess_reached
        subprocess_reached = True
        raise AssertionError("subprocess.run must not be reached")

    monkeypatch.setattr(gateway.subprocess, "run", fail_if_run)
    started = time.monotonic()
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            gateway.run_cli(
                ["eyecloud-pro-pp-cli", "insurance", "get"],
                {},
                timeout_s=0.05,
            )
        assert time.monotonic() - started < 0.5
        assert subprocess_reached is False
    finally:
        release_holder.set()
        holder.join(timeout=1)
    assert not holder.is_alive()


def test_explicit_timeout_includes_file_lock_wait(monkeypatch, tmp_path):
    gateway = load_gateway()
    lock_path = tmp_path / "session.lock"
    monkeypatch.setenv("ECP_SESSION_LOCK_FILE", str(lock_path))
    holder, release_holder = _start_exclusive_file_lock_holder(lock_path)
    subprocess_reached = False

    def fail_if_run(*_args, **_kwargs):
        nonlocal subprocess_reached
        subprocess_reached = True
        raise AssertionError("subprocess.run must not be reached")

    monkeypatch.setattr(gateway.subprocess, "run", fail_if_run)
    started = time.monotonic()
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            gateway.run_cli(
                ["eyecloud-pro-pp-cli", "availability"],
                {},
                timeout_s=0.05,
            )
        elapsed = time.monotonic() - started
        assert 0.04 <= elapsed < 0.5
        assert subprocess_reached is False
    finally:
        _release_file_lock_holder(holder, release_holder)


def test_explicit_deadline_covers_relogin_and_retries(monkeypatch, tmp_path):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_SESSION_LOCK_FILE", str(tmp_path / "session.lock"))
    gateway._RELOGIN_TS = 0.0
    ticks = iter(float(value) for value in range(100, 120))
    monkeypatch.setattr(gateway.time, "monotonic", lambda: next(ticks))
    observed = []

    def dead_session_then_auth_then_retry(argv, **kwargs):
        observed.append(("auth" if "auth" in argv else "cli", kwargs["timeout"]))
        if len(observed) == 1:
            proc = Completed({}, returncode=1)
            proc.stderr = "GET /pos/!egweb.synthetic returned HTTP 404"
            return proc
        return Completed({})

    monkeypatch.setattr(gateway.subprocess, "run", dead_session_then_auth_then_retry)
    result = gateway.run_cli(
        ["eyecloud-pro-pp-cli", "availability"],
        {},
        timeout_s=10,
    )

    assert result.returncode == 0
    assert [kind for kind, _timeout in observed] == ["cli", "auth", "cli"]
    timeouts = [timeout for _kind, timeout in observed]
    assert all(0 < timeout <= 10 for timeout in timeouts)
    assert timeouts == sorted(timeouts, reverse=True)
    assert timeouts[1] < timeouts[0]
    assert timeouts[2] < timeouts[0]


def test_explicit_relogin_timeout_propagates(monkeypatch, tmp_path):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_SESSION_LOCK_FILE", str(tmp_path / "session.lock"))
    gateway._RELOGIN_TS = 0.0
    observed = []

    def dead_session_then_timeout(argv, **kwargs):
        observed.append((argv, kwargs["timeout"]))
        if "auth" in argv:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        proc = Completed({}, returncode=1)
        proc.stderr = "GET /pos/!egweb.synthetic returned HTTP 404"
        return proc

    monkeypatch.setattr(gateway.subprocess, "run", dead_session_then_timeout)
    with pytest.raises(subprocess.TimeoutExpired) as raised:
        gateway.run_cli(
            ["eyecloud-pro-pp-cli", "availability"],
            {},
            timeout_s=0.5,
        )

    assert len(observed) == 2
    assert "auth" in observed[1][0]
    assert 0 < observed[1][1] <= 0.5
    assert raised.value.timeout == observed[1][1]


def test_legacy_run_cli_waits_without_operation_deadline(monkeypatch, tmp_path):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_SESSION_LOCK_FILE", str(tmp_path / "session.lock"))
    holder_entered = threading.Event()
    release_holder = threading.Event()
    subprocess_started = threading.Event()
    worker_done = threading.Event()
    observed_timeouts = []
    outcome = {}

    def hold_login_lock():
        with gateway.SESSION_LOCK.login():
            holder_entered.set()
            release_holder.wait(timeout=2)

    def fake_run(_argv, **kwargs):
        observed_timeouts.append(kwargs["timeout"])
        subprocess_started.set()
        return Completed({})

    def run_untimed():
        try:
            outcome["result"] = gateway.run_cli(
                ["eyecloud-pro-pp-cli", "availability"],
                {},
            )
        except BaseException as exc:
            outcome["error"] = exc
        finally:
            worker_done.set()

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    holder = threading.Thread(target=hold_login_lock)
    worker = threading.Thread(target=run_untimed)
    holder.start()
    assert holder_entered.wait(timeout=1)
    worker.start()
    try:
        assert worker_done.wait(timeout=0.05) is False
        assert subprocess_started.is_set() is False
        release_holder.set()
        assert worker_done.wait(timeout=1)
    finally:
        release_holder.set()
        holder.join(timeout=1)
        worker.join(timeout=1)

    assert not holder.is_alive()
    assert not worker.is_alive()
    assert "error" not in outcome
    assert outcome["result"].returncode == 0
    assert observed_timeouts == [gateway.TIMEOUT_S]


def test_legacy_file_lock_timeout_degrades_open(
    monkeypatch, caplog, tmp_path
):
    gateway = load_gateway()
    lock_path = tmp_path / "session.lock"
    monkeypatch.setenv("ECP_SESSION_LOCK_FILE", str(lock_path))
    monkeypatch.setenv("ECP_SESSION_LOCK_TIMEOUT_S", "0.05")
    holder, release_holder = _start_exclusive_file_lock_holder(lock_path)
    observed_timeouts = []

    def fake_run(_argv, **kwargs):
        observed_timeouts.append(kwargs["timeout"])
        return Completed({})

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    started = time.monotonic()
    try:
        with caplog.at_level(logging.WARNING):
            result = gateway.run_cli(
                ["eyecloud-pro-pp-cli", "availability"],
                {},
            )
        elapsed = time.monotonic() - started
        assert result.returncode == 0
        assert 0.04 <= elapsed < 0.5
        assert observed_timeouts == [gateway.TIMEOUT_S]
        assert "session flock wait timed out" in caplog.text
        assert "proceeding unlocked" in caplog.text
    finally:
        _release_file_lock_holder(holder, release_holder)


def test_legacy_run_cli_preserves_per_attempt_timeouts(
    monkeypatch, caplog, tmp_path
):
    gateway = load_gateway()
    monkeypatch.setenv("ECP_SESSION_LOCK_FILE", str(tmp_path / "session.lock"))
    calls = []

    def dead_session_or_login(argv, **kwargs):
        calls.append((argv, kwargs["timeout"]))
        if "auth" in argv:
            return Completed({})
        proc = Completed({}, returncode=1)
        proc.stderr = "GET /pos/!egweb.synthetic returned HTTP 404"
        return proc

    monkeypatch.setattr(gateway.subprocess, "run", dead_session_or_login)
    result = gateway.run_cli(["eyecloud-pro-pp-cli", "availability"], {})

    cli_timeouts = [timeout for argv, timeout in calls if "auth" not in argv]
    login_timeouts = [timeout for argv, timeout in calls if "auth" in argv]
    assert result.returncode == 1
    assert cli_timeouts == [gateway.TIMEOUT_S] * 3
    assert login_timeouts == [120, 120]

    gateway._RELOGIN_TS = 0.0

    def timeout_login(argv, **kwargs):
        assert "auth" in argv
        assert kwargs["timeout"] == 120
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(gateway.subprocess, "run", timeout_login)
    with caplog.at_level(logging.WARNING):
        assert gateway._relogin({}, force=True) is False
    assert "on-demand relogin timed out after 120s" in caplog.text


def test_query_identity_release_audit_timeout_and_stable_response(monkeypatch, caplog, tmp_path):
    import capability_registry as registry

    gateway = load_gateway()
    gateway.ECP_QUERY_RELEASE_GATE = "BLOCK"
    caplog.set_level(logging.INFO)
    status, body = post(gateway, "/query", {})
    assert (status, body["error"]) == (403, "query_release_blocked")
    assert sum("query_audit " in record.message for record in caplog.records) == 1

    caplog.clear()
    gateway.ECP_QUERY_RELEASE_GATE = "SYNTHETIC_TEST_ONLY"
    gateway.CAPABILITY_MANIFEST["operations"]["insurance.get"]["limits"]["rate_per_minute"] = 100
    registry.RATE_LIMITER = registry.OperationRateLimiter(str(tmp_path / "rate.sqlite3"))
    seen = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        seen["timeout"] = kwargs["timeout"]
        return Completed({"insurance": [{"carrier": "Synthetic", "member_id": "hidden"}]})

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    status, body = post(gateway, "/query", {
        "operation": "insurance.get",
        "reason": "coverage-question",
        "params": {"patient_id": "1001"},
        "projection": "summary",
        "limit": 10,
    })
    assert status == 200
    assert seen["argv"][:3] == ["eyecloud-pro-pp-cli", "insurance", "get"]
    assert seen["timeout"] <= 30
    assert body["meta"]["sensitive_withheld"] == [
        "member_id", "subscriber_id", "policy_number", "group_number"
    ]
    assert "hidden" not in json.dumps(body)
    assert sum("query_audit " in record.message for record in caplog.records) == 1
    assert "1001" not in "\n".join(record.message for record in caplog.records)

    assert post(gateway, "/query", {
        "operation": "insurance.get",
        "reason": "coverage-question",
        "params": {"patient_id": "1001"},
    }, token="wrong")[1]["error"] == "query_identity_unbound"


def test_cursor_replay_context_is_rejected(tmp_path):
    import sys

    sys.path.insert(0, str(ROOT / "container"))
    import capability_registry as registry

    registry.RATE_LIMITER = registry.OperationRateLimiter(str(tmp_path / "rate.sqlite3"))
    manifest = registry.load_manifest(str(ROOT / "container/eyecloud_capabilities.v1.json"))
    base = {
        "operation": "insurance.get",
        "reason": "coverage-question",
        "params": {"patient_id": "1001"},
        "limit": 1,
    }
    prepared = registry.prepare_query(
        base,
        cli="cli",
        principal="bland-read",
        tenant="tenant-a",
        release_gate="SYNTHETIC_TEST_ONLY",
        cursor_secret="secret",
        manifest=manifest,
    )
    response = registry.render_query_result(
        prepared,
        {"insurance": [{"carrier": "A"}, {"carrier": "B"}]},
        "secret",
    )
    cursor = response["meta"]["next_cursor"]
    with pytest.raises(registry.QueryError, match="invalid_cursor"):
        registry.prepare_query(
            {**base, "params": {"patient_id": "2002"}, "cursor": cursor},
            cli="cli",
            principal="bland-read",
            tenant="tenant-a",
            release_gate="SYNTHETIC_TEST_ONLY",
            cursor_secret="secret",
            manifest=manifest,
        )


def _rate_worker(path, start, output):
    import sys

    sys.path.insert(0, str(ROOT / "container"))
    from capability_registry import OperationRateLimiter, QueryError

    start.wait()
    try:
        OperationRateLimiter(path).check(("tenant", "principal", "operation"), 1)
        output.put("allowed")
    except QueryError as exc:
        output.put(exc.code)


def test_rate_limiter_is_atomic_across_processes(tmp_path):
    ctx = multiprocessing.get_context("fork")
    start = ctx.Event()
    output = ctx.Queue()
    processes = [
        ctx.Process(target=_rate_worker, args=(str(tmp_path / "rate.sqlite3"), start, output))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start.set()
    results = sorted(output.get(timeout=5) for _ in processes)
    for process in processes:
        process.join(timeout=5)
    assert results == ["allowed", "rate_limited"]
