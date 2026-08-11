#!/usr/bin/env python3
"""Approval-gated Mott outbound SMS recall batch sender."""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

API_BASE = "https://api.bland.ai"
GATEWAY = "https://mott-booking-gw.mail.mybcat.com"
PATIENT_SEARCH_URL = f"{GATEWAY}/patient-search"
TIMEZONE = "America/New_York"
START_NODE_ID = "n_recall_lookup"
PHONE_COLUMNS = ("phone_e164", "consent_source", "consent_date")
PATIENT_COLUMNS = ("patient_id", "consent_source", "consent_date")
TOKEN_COLUMN = "recall_token"
PATIENT_ID_COLUMN = "patient_id"
MANIFEST_SCHEMA = "cvc-outbound-recall-manifest.v1"
EXPECTED_VOICE_SOURCE_PATHWAY_ID = "128fe6af-1843-4924-b071-6e19f729b056"
EXPECTED_VOICE_SOURCE_VERSION = 53
DEFAULT_MANIFEST = Path("config/cvc_outbound_recall_manifest.v1.json")


@dataclass(frozen=True)
class ClientProfile:
    """Everything that differs between practices, in one place.

    A practice is identified by its manifest's own schema_version, so a manifest cannot
    be run against the wrong practice's pins by accident. voice_source is optional: CVC's
    text pathway was derived from a specific voice pathway and must stay pinned to it,
    while a practice whose pathway was authored directly has nothing to pin.
    """

    key: str
    schema: str
    campaign: str
    start_nodes: frozenset[str]
    # The send ledger is the frequency cap and the duplicate-send guard, keyed by phone
    # hash and recall token. It MUST be per practice. Sharing one file across practices
    # means a send to a patient of one clinic silently suppresses the other clinic's send
    # to the same person, and puts both practices' phone hashes in one artifact.
    send_ledger_schema: str
    send_ledger_path: Path
    # The booking store id the pathway needs in request_data. Mott's start node refuses
    # on `store == ""` and its availability body interpolates {{store}} directly, so a
    # send without it either safe-exits immediately or posts "store":null and the gateway
    # rejects it as a type error. The scenario harness supplies store from its own env,
    # which is why chat-endpoint runs reached offers while no real send ever could.
    # None means "this practice's pathway does not take a store", which preserves the
    # existing request_data shape exactly for any client that never had one.
    store: str | None = None
    voice_source_pathway_id: str | None = None
    voice_source_version: int | None = None


CLIENTS: tuple[ClientProfile, ...] = (
    ClientProfile(
        key="cvc",
        schema=MANIFEST_SCHEMA,
        campaign="cvc_recall_outbound",
        start_nodes=frozenset({START_NODE_ID, "n_contact_lookup"}),
        send_ledger_schema="cvc-outbound-recall-send-ledger.v1",
        send_ledger_path=Path("config/cvc_outbound_recall_send_ledger.v1.json"),
        voice_source_pathway_id=EXPECTED_VOICE_SOURCE_PATHWAY_ID,
        voice_source_version=EXPECTED_VOICE_SOURCE_VERSION,
    ),
    ClientProfile(
        key="mott",
        schema="mott-outbound-recall-manifest.v1",
        campaign="mott_recall_outbound",
        start_nodes=frozenset({"n_identity"}),
        send_ledger_schema="mott-outbound-recall-send-ledger.v1",
        send_ledger_path=Path("config/mott_outbound_recall_send_ledger.v1.json"),
        store="711",
    ),
)


def resolve_client(schema_version: Any) -> ClientProfile:
    for profile in CLIENTS:
        if schema_version == profile.schema:
            return profile
    raise Refusal("unknown manifest schema; no client profile matches")
# Retained only for importers; the running code resolves both from the ClientProfile.
DEFAULT_SEND_LEDGER = CLIENTS[0].send_ledger_path
SEND_LEDGER_SCHEMA = CLIENTS[0].send_ledger_schema
PHI_COLUMN_RE = re.compile(
    r"(?:^|_)(?:name|dob|birth|patient|address|email|diagnosis|mrn)(?:_|$)", re.I
)
E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")
PATIENT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
RECALL_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]{8,128}$")
ALLOWED_OPT_OUT_REASONS = {"stop", "prose_revocation", "wrong_number", "help"}
LOG = logging.getLogger("sms_recall_batch")


class Refusal(RuntimeError):
    """A fail-closed refusal to continue the batch."""


@dataclass(frozen=True)
class FeedRow:
    phone_e164: str | None
    consent_source: str
    consent_date: str
    recall_token: str | None = None
    patient_id: str | None = None
    enriched: bool = False


HttpRequest = Callable[[str, str, dict[str, Any] | None, bool | str], tuple[int, Any]]
Clock = Callable[[], datetime]


def _last4(phone: str) -> str:
    return phone[-4:] if len(phone) >= 4 else "****"


def _phone_sha256(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def http_request(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    auth: bool | str = False,
) -> tuple[int, Any]:
    """HTTP seam. `True` is Bland auth and `"gateway"` is Mott gateway auth."""
    headers = {"User-Agent": "mott-sms-recall-batch/2.0"}
    if auth is True:
        value = os.environ.get("BLAND_API_KEY")
        if not value:
            raise Refusal("Bland authorization is unavailable")
        headers["Authorization"] = value
    elif auth == "gateway":
        value = os.environ.get("MOTT_GATEWAY_TOKEN")
        if not value:
            raise Refusal("gateway authorization is unavailable")
        headers["Authorization"] = value
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", "replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        status = exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Refusal(f"endpoint unavailable: {type(exc).__name__}") from exc
    try:
        return status, json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return status, raw[:500]


def _allowed_feed_columns(columns: tuple[str, ...]) -> bool:
    return columns in {
        PHONE_COLUMNS,
        PHONE_COLUMNS + (TOKEN_COLUMN,),
        PHONE_COLUMNS + (TOKEN_COLUMN, PATIENT_ID_COLUMN),
        PATIENT_COLUMNS,
        PATIENT_COLUMNS + (TOKEN_COLUMN,),
    }


def load_feed(path: Path, max_age_hours: float, now: datetime) -> list[FeedRow]:
    if max_age_hours <= 0:
        raise Refusal("--max-feed-age-hours must be positive")
    age_seconds = now.timestamp() - path.stat().st_mtime
    if age_seconds < -300 or age_seconds > max_age_hours * 3600:
        raise Refusal("feed freshness check failed")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        if any(
            PHI_COLUMN_RE.search(column.strip())
            and column.strip() != PATIENT_ID_COLUMN
            for column in columns
        ):
            raise Refusal("feed contains a PHI-looking column name")
        if not _allowed_feed_columns(columns):
            raise Refusal("feed columns do not match an approved phone or patient-ID shape")
        patient_only = columns[0] == PATIENT_ID_COLUMN
        unique: dict[str, FeedRow] = {}
        for line_number, raw in enumerate(reader, start=2):
            source = raw["consent_source"].strip()
            date_text = raw["consent_date"].strip()
            if not source or not date_text or "voice" in source.casefold():
                continue
            try:
                datetime.fromisoformat(date_text.replace("Z", "+00:00"))
            except ValueError as exc:
                raise Refusal(f"invalid consent_date on row {line_number}") from exc
            token = (raw.get(TOKEN_COLUMN) or "").strip()
            if token and not RECALL_TOKEN_RE.fullmatch(token):
                continue
            patient_id = (raw.get(PATIENT_ID_COLUMN) or "").strip() or None
            phone = (raw.get("phone_e164") or "").strip() or None
            if patient_only:
                if not patient_id or not PATIENT_ID_RE.fullmatch(patient_id):
                    raise Refusal(f"invalid patient_id on row {line_number}")
                key = f"patient:{patient_id}"
            else:
                if not phone or not E164_RE.fullmatch(phone):
                    raise Refusal(f"invalid E.164 phone on row {line_number}")
                if patient_id and not PATIENT_ID_RE.fullmatch(patient_id):
                    raise Refusal(f"invalid patient_id on row {line_number}")
                key = f"phone:{phone}"
            unique.setdefault(
                key,
                FeedRow(phone, source, date_text, token or None, patient_id),
            )
        return list(unique.values())


def _parse_enrichment(body: Any, trusted_id: str) -> tuple[str | None, str | None]:
    """Return (mobile, skip_reason); raise when the gateway contract is unsafe."""
    if not isinstance(body, dict) or body.get("ok") is not True:
        raise Refusal("patient enrichment response was not successful")
    result = body.get("result")
    if not isinstance(result, dict):
        raise Refusal("patient enrichment result was malformed")
    count = result.get("count")
    if isinstance(count, bool) or not isinstance(count, int):
        raise Refusal("patient enrichment envelope was malformed")
    if count == 0:
        return None, "patient_match_zero"
    if count > 1:
        return None, "patient_match_ambiguous"
    patients = result.get("patients")
    if not isinstance(patients, list):
        raise Refusal("patient enrichment envelope was malformed")
    if count != 1 or len(patients) != 1 or not isinstance(patients[0], dict):
        raise Refusal("patient enrichment count did not match its records")
    patient = patients[0]
    returned_id = patient.get("patient_id")
    if not isinstance(returned_id, str) or returned_id != trusted_id:
        return None, "patient_id_mismatch"
    mobile = patient.get("phone_mobile")
    if mobile in (None, ""):
        return None, "mobile_missing"
    if not isinstance(mobile, str) or not E164_RE.fullmatch(mobile):
        return None, "mobile_invalid"
    return mobile, None


def enrich_patient_rows(
    rows: list[FeedRow], http: HttpRequest
) -> tuple[list[FeedRow], dict[str, int]]:
    """Resolve patient-only rows, then deduplicate all rows by final phone."""
    reasons: dict[str, int] = {}
    enriched: list[FeedRow] = []
    for row in rows:
        if row.phone_e164 is not None:
            enriched.append(row)
            continue
        assert row.patient_id is not None
        status, body = http(
            "POST",
            PATIENT_SEARCH_URL,
            {"profile": "contact", "patient_id": row.patient_id},
            "gateway",
        )
        if status != 200:
            raise Refusal(f"patient enrichment failed with HTTP {status}")
        mobile, reason = _parse_enrichment(body, row.patient_id)
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        assert mobile is not None
        enriched.append(replace(row, phone_e164=mobile, enriched=True))
    unique: dict[str, FeedRow] = {}
    for row in enriched:
        assert row.phone_e164 is not None
        if row.phone_e164 in unique:
            reasons["phone_deduplicated"] = reasons.get("phone_deduplicated", 0) + 1
            # When a legacy phone row and a patient-ID-only row resolve to the
            # same mobile, retain the enriched row so v20 identity context is
            # not discarded merely because of feed ordering.
            if row.enriched and not unique[row.phone_e164].enriched:
                unique[row.phone_e164] = row
        else:
            unique[row.phone_e164] = row
    return list(unique.values()), reasons


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version", "pathway_name", "pathway_id", "version",
        "voice_source_pathway_id", "voice_source_version", "start_node_id",
        "time_out_hours", "restart_after_end_call", "structural_sha256", "created_utc",
    }
    if not isinstance(data, dict) or set(data) != required:
        raise Refusal("invalid release manifest schema")
    client = resolve_client(data.get("schema_version"))
    if not all(isinstance(data[key], str) and data[key] for key in ("pathway_name", "pathway_id")):
        raise Refusal("manifest identity is invalid")
    if isinstance(data["version"], bool) or not isinstance(data["version"], int):
        raise Refusal("manifest version is invalid")
    if client.voice_source_pathway_id is not None:
        if data["voice_source_pathway_id"] != client.voice_source_pathway_id:
            raise Refusal("manifest voice source pathway mismatch")
        if data["voice_source_version"] != client.voice_source_version:
            raise Refusal("manifest voice source version mismatch")
    elif data["voice_source_pathway_id"] != "" or data["voice_source_version"] != 0:
        raise Refusal("manifest declares a voice source this client does not have")
    if data["start_node_id"] not in client.start_nodes:
        raise Refusal("manifest start node mismatch")
    if not isinstance(data["time_out_hours"], (int, float)) or isinstance(data["time_out_hours"], bool) or data["time_out_hours"] <= 0:
        raise Refusal("manifest time_out_hours is invalid")
    if not isinstance(data["restart_after_end_call"], bool):
        raise Refusal("manifest restart_after_end_call is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(data["structural_sha256"])):
        raise Refusal("manifest structural_sha256 is invalid")
    created = datetime.fromisoformat(str(data["created_utc"]).replace("Z", "+00:00"))
    if created.tzinfo is None:
        raise Refusal("manifest created_utc must include timezone")
    return data


def _validate_ledger_entry(entry: Any) -> None:
    required = {"recall_token", "phone_sha256", "phone_last4", "status", "timestamp"}
    if not isinstance(entry, dict) or set(entry) != required:
        raise Refusal("invalid send ledger entry")
    if entry["recall_token"] is not None and not RECALL_TOKEN_RE.fullmatch(str(entry["recall_token"])):
        raise Refusal("invalid send ledger recall token")
    if not re.fullmatch(r"[0-9a-f]{64}", str(entry["phone_sha256"])):
        raise Refusal("invalid send ledger phone key")
    if not re.fullmatch(r"\d{4}", str(entry["phone_last4"])):
        raise Refusal("invalid send ledger phone suffix")
    if entry["status"] not in {"pending", "sent"}:
        raise Refusal("invalid send ledger status")
    if datetime.fromisoformat(str(entry["timestamp"]).replace("Z", "+00:00")).tzinfo is None:
        raise Refusal("send ledger timestamp must include timezone")


def load_send_ledger(path: Path, profile: ClientProfile) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal("send ledger is unreadable") from exc
    # Checked against THIS practice's schema, so pointing a run at another practice's
    # ledger is refused rather than silently merging two clinics' send histories.
    if not isinstance(data, dict) or set(data) != {"schema_version", "sends"} or data["schema_version"] != profile.send_ledger_schema:
        raise Refusal("invalid send ledger schema")
    if not isinstance(data["sends"], list):
        raise Refusal("invalid send ledger entries")
    for entry in data["sends"]:
        _validate_ledger_entry(entry)
    return data["sends"]


def frequency_capped(phone: str, sends: list[dict[str, Any]], now: datetime, min_days_between: float, recall_token: str | None = None) -> bool:
    if min_days_between <= 0:
        raise Refusal("--min-days-between must be positive")
    cutoff = now - timedelta(days=min_days_between)
    phone_key = _phone_sha256(phone)
    return any(
        (entry["phone_sha256"] == phone_key or (recall_token is not None and entry["recall_token"] == recall_token))
        and datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")) > cutoff
        for entry in sends
    )


@contextmanager
def _exclusive_ledger_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    try:
        with lock_path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise Refusal("send ledger lock failed") from exc


def _write_send_ledger(path: Path, sends: list[dict[str, Any]], profile: ClientProfile) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"schema_version": profile.send_ledger_schema, "sends": sends}, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise Refusal("send ledger write failed") from exc


def reserve_pending_send(path: Path, sends: list[dict[str, Any]], phone: str, recall_token: str | None, timestamp: datetime, min_days_between: float, profile: ClientProfile) -> bool:
    with _exclusive_ledger_lock(path):
        current = load_send_ledger(path, profile)
        if frequency_capped(phone, current, timestamp, min_days_between, recall_token):
            sends[:] = current
            return False
        current.append({
            "recall_token": recall_token,
            "phone_sha256": _phone_sha256(phone),
            "phone_last4": _last4(phone),
            "status": "pending",
            "timestamp": timestamp.astimezone(timezone.utc).isoformat(),
        })
        _write_send_ledger(path, current, profile)
        sends[:] = current
        return True


def mark_send_sent(path: Path, sends: list[dict[str, Any]], phone: str, recall_token: str | None, timestamp: datetime, profile: ClientProfile) -> None:
    with _exclusive_ledger_lock(path):
        current = load_send_ledger(path, profile)
        key = _phone_sha256(phone)
        matches = [i for i, entry in enumerate(current) if entry["status"] == "pending" and entry["phone_sha256"] == key and entry["recall_token"] == recall_token]
        if not matches:
            raise Refusal("pending send ledger record is missing")
        index = matches[-1]
        current[index] = {**current[index], "status": "sent", "timestamp": timestamp.astimezone(timezone.utc).isoformat()}
        _write_send_ledger(path, current, profile)
        sends[:] = current


def _suppressed_from_body(body: Any, phone: str | None = None) -> bool | set[str]:
    if phone is not None:
        if not isinstance(body, dict) or not isinstance(body.get("suppressed"), bool):
            raise Refusal("invalid suppression response")
        return body["suppressed"]
    if not isinstance(body, dict):
        raise Refusal("invalid bulk suppression response")
    rows = body.get("data", body.get("suppressions"))
    if not isinstance(rows, list):
        raise Refusal("invalid bulk suppression response")
    return {row["phone_e164"] for row in rows if isinstance(row, dict) and E164_RE.fullmatch(str(row.get("phone_e164", "")))}


def bulk_suppressions(http: HttpRequest) -> set[str]:
    status, body = http("GET", f"{GATEWAY}/sms-suppression", None, False)
    if status != 200:
        raise Refusal(f"suppression bulk GET failed with HTTP {status}")
    result = _suppressed_from_body(body)
    assert isinstance(result, set)
    return result


def is_suppressed(phone: str, http: HttpRequest) -> bool:
    url = f"{GATEWAY}/sms-suppression?{urllib.parse.urlencode({'phone': phone})}"
    status, body = http("GET", url, None, False)
    if status != 200:
        raise Refusal(f"suppression recheck failed with HTTP {status}")
    result = _suppressed_from_body(body, phone)
    assert isinstance(result, bool)
    return result


def record_opt_out(phone: str, reason: str, http: HttpRequest = http_request) -> None:
    if not E164_RE.fullmatch(phone) or reason not in ALLOWED_OPT_OUT_REASONS:
        raise Refusal("invalid opt-out suppression write")
    status, _ = http("POST", f"{GATEWAY}/sms-suppression", {"phone_e164": phone, "reason": reason, "source": "sms_recall_batch"}, "gateway")
    if not 200 <= status < 300:
        raise Refusal(f"suppression POST failed with HTTP {status}")
    LOG.info("suppression recorded for phone hash %s ending %s", _phone_sha256(phone), _last4(phone))


def within_quiet_hours(now: datetime, timezone_name: str = TIMEZONE) -> bool:
    try:
        local = now.astimezone(ZoneInfo(timezone_name))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise Refusal("clinic timezone is invalid") from exc
    return time(10, 0) <= local.time().replace(tzinfo=None) < time(18, 0)


def send_one(
    phone: str,
    manifest: dict[str, Any],
    http: HttpRequest,
    recall_token: str | None = None,
    recall_patient_id: str | None = None,
    recall_cell: str | None = None,
) -> None:
    profile = resolve_client(manifest.get("schema_version"))
    request_data: dict[str, Any] = {"campaign": profile.campaign}
    if profile.store:
        request_data["store"] = profile.store
    if recall_token:
        request_data["recall_token"] = recall_token
    if recall_patient_id:
        request_data["recall_patient_id"] = recall_patient_id
    if recall_cell:
        request_data["recall_cell"] = recall_cell
    payload = {
        "phone_number": phone,
        "pathway_id": manifest["pathway_id"],
        "pathway_version": manifest["version"],
        "start_node_id": manifest["start_node_id"],
        "request_data": request_data,
    }
    status, body = http("POST", f"{API_BASE}/v1/sms/create", payload, True)
    if not 200 <= status < 300:
        raise Refusal(f"SMS create failed with HTTP {status}")
    success_statuses = {"success", "created", "queued"}
    if not isinstance(body, dict) or body.get("error") not in (None, False, "") or ("status" in body and body["status"] not in success_statuses) or not (body.get("success") is True or body.get("ok") is True or body.get("status") in success_statuses):
        raise Refusal("SMS create response did not confirm success")
    LOG.info("SMS created for phone hash %s ending %s", _phone_sha256(phone), _last4(phone))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--send-ledger", type=Path, default=None,
                        help="defaults to the resolved practice's own ledger")
    parser.add_argument("--min-days-between", type=float, default=30.0)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--approve", action="store_true")
    parser.add_argument("--max-sends", type=int)
    parser.add_argument("--max-feed-age-hours", type=float, default=24.0)
    return parser


def run(argv: list[str] | None = None, *, http: HttpRequest = http_request, clock: Clock = lambda: datetime.now(timezone.utc)) -> int:
    actions = 0
    try:
        args = build_parser().parse_args(argv)
        now = clock()
        if now.tzinfo is None:
            raise Refusal("clock must return a timezone-aware datetime")
        manifest = load_manifest(args.manifest)
        # Resolved ONCE here and threaded, so the ledger, the campaign label and the
        # pathway pins can never come from different practices within a single run.
        profile = resolve_client(manifest.get("schema_version"))
        ledger_path = args.send_ledger or profile.send_ledger_path
        ledger = load_send_ledger(ledger_path, profile)
        rows = load_feed(args.feed, args.max_feed_age_hours, now)
        with args.feed.open(newline="", encoding="utf-8-sig") as handle:
            raw_rows = list(csv.DictReader(handle))
        consent_refused = sum(not row["consent_source"].strip() or not row["consent_date"].strip() or "voice" in row["consent_source"].casefold() for row in raw_rows)
        token_refused = sum(bool((row.get(TOKEN_COLUMN) or "").strip()) and not bool(RECALL_TOKEN_RE.fullmatch((row.get(TOKEN_COLUMN) or "").strip())) for row in raw_rows)
        rows, enrichment_reasons = enrich_patient_rows(rows, http)
        suppressed_set = bulk_suppressions(http)
        eligible = [row for row in rows if row.phone_e164 not in suppressed_set]
        frequency_refused = sum(frequency_capped(row.phone_e164 or "", ledger, now, args.min_days_between, row.recall_token) for row in eligible)
        sendable = [row for row in eligible if not frequency_capped(row.phone_e164 or "", ledger, now, args.min_days_between, row.recall_token)]
        print(f"total={len(raw_rows)}")
        print(f"consent-refused={consent_refused}")
        print(f"token-refused={token_refused}")
        for reason in sorted(enrichment_reasons):
            print(f"{reason.replace('_', '-')}={enrichment_reasons[reason]}")
        print(f"suppressed={len(rows) - len(eligible)}")
        print(f"frequency-refused={frequency_refused}")
        print(f"pending-reconciliation={sum(entry['status'] == 'pending' for entry in ledger)}")
        print(f"sendable={len(sendable)}")
        print(f"timezone={TIMEZONE}")
        print("message-template-preview=pathway-owned personalized first message")
        print("message-one-summary=pathway-owned personalized first message")
        if args.approve:
            if args.max_sends is None:
                raise Refusal("--max-sends N is required for --approve")
            if args.max_sends <= 0 or len(sendable) > args.max_sends:
                raise Refusal("sendable count exceeds approved maximum")
            for row in sendable:
                assert row.phone_e164 is not None
                if not within_quiet_hours(clock(), TIMEZONE):
                    raise Refusal("outside permitted sending window 10:00-18:00 America/New_York")
                if is_suppressed(row.phone_e164, http):
                    continue
                send_time = clock()
                if not reserve_pending_send(ledger_path, ledger, row.phone_e164, row.recall_token, send_time, args.min_days_between, profile):
                    continue
                send_one(
                    row.phone_e164,
                    manifest,
                    http,
                    row.recall_token,
                    row.patient_id,
                    row.phone_e164 if row.enriched else None,
                )
                actions += 1
                mark_send_sent(ledger_path, ledger, row.phone_e164, row.recall_token, clock(), profile)
        return 0
    except (Refusal, OSError, json.JSONDecodeError, ValueError) as exc:
        LOG.error("refused: %s", exc)
        return 2
    finally:
        print(f"external_actions_taken={actions}")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return run()


if __name__ == "__main__":
    sys.exit(main())
