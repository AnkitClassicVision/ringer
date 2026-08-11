#!/usr/bin/env python3
"""Stage A: PHI-minimized recall-campaign feed extract.

Runs INSIDE the existing CVC booking-gateway container as an ECS scheduled
task. It calls the EyeCloud CLI through the same boundary that
``scripts/build_sms_recall_feed.py`` uses, normalizes phone numbers, and writes
a five-column feed CSV plus a counts-only sidecar to S3 under SSE-KMS.

Runtime contract (env driven, ECS-friendly):

- ``ECP_CLI_PATH``      EyeCloud CLI binary (REQUIRED; refuse if unset).
- ``FEED_WINDOW``       recall window passed to the CLI (default ``90d``).
- ``GATEWAY_HEALTH_URL``preflight URL (default the CVC booking gateway health).
- ``FEED_BUCKET``       destination bucket (REQUIRED; refuse if unset).
- ``KMS_KEY_ID``        SSE-KMS key for the feed objects (REQUIRED; refuse if unset).

Fail-closed posture: any refusal writes NOTHING to S3. A preflight failure
exits 3; every other refusal exits 2 (matching the reference extractor). The
only rows dropped from the feed are those whose phone fails E.164
normalization; they are counted, never written. No names, DOBs, or any field
beyond the five feed columns is ever emitted, and logs carry counts only.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

try:  # boto3 is import-guarded so the unit tests run without it installed.
    import boto3
except ImportError:  # pragma: no cover - exercised only where boto3 is absent
    boto3 = None

LOG = logging.getLogger("aws_campaign.feed_task")

DEFAULT_HEALTH_URL = "https://cvc-booking-gw.mail.mybcat.com/health"
DEFAULT_FEED_WINDOW = "90d"
FEED_REASON = "recall-campaign-feed"
CONSENT_SOURCE = "patient-provided-number"
# Order is load-bearing: it is the on-disk / in-S3 CSV column order.
FEED_COLUMNS = (
    "phone_e164",
    "consent_source",
    "consent_date",
    "recall_token",
    "patient_id",
)
E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

HttpGet = Callable[[str], "tuple[int, Any]"]


class Refusal(RuntimeError):
    """Fail-closed refusal to produce a campaign artifact (exit code 2)."""

    exit_code = 2


class PreflightRefusal(Refusal):
    """Gateway preflight did not pass three clean checks (exit code 3)."""

    exit_code = 3


def normalize_e164(value: Any, default_country_code: str = "1") -> str:
    """Return an E.164 string or raise ``ValueError`` (copied from the reference)."""
    raw = str(value or "").strip()
    if raw.startswith("+"):
        candidate = "+" + re.sub(r"\D", "", raw[1:])
    else:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 10:
            digits = default_country_code + digits
        candidate = "+" + digits
    if not E164_RE.fullmatch(candidate):
        raise ValueError("invalid E.164")
    return candidate


def http_get(url: str) -> tuple[int, Any]:
    """GET ``url`` and return ``(status, parsed_json_or_empty)``."""
    request = urllib.request.Request(url, headers={"User-Agent": "cvc-recall-feed/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", "replace")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PreflightRefusal(f"gateway health endpoint unavailable: {type(exc).__name__}") from exc
    except json.JSONDecodeError as exc:
        raise PreflightRefusal("gateway health endpoint returned malformed JSON") from exc


class EyeCloudAdapter(ABC):
    """The only boundary through which this task obtains EyeCloud rows."""

    @abstractmethod
    def recall_contacts(self) -> list[dict[str, Any]]:
        """Return the minimum fields needed to construct the feed."""


class RealEyeCloudAdapter(EyeCloudAdapter):
    """Invokes the EyeCloud CLI exactly like the reference extractor does."""

    ROW_FIELDS = {"patient_id", "recall_date", "mobile_phone", "phone_recorded_date"}

    def __init__(self, *, cli_path: str | None, window: str, reason: str = FEED_REASON):
        resolved_path = (cli_path or "").strip()
        if not resolved_path:
            raise Refusal(
                "real EyeCloud mode requires ECP_CLI_PATH; refusing to guess a binary path"
            )
        self.cli_path = resolved_path
        self.window = window
        self.reason = reason

    def recall_contacts(self) -> list[dict[str, Any]]:
        argv = [
            self.cli_path, "recall", "feed-source", "--window", self.window,
            "--json", "--reason", self.reason,
        ]
        try:
            completed = subprocess.run(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, check=False,
            )
        except OSError as exc:
            raise Refusal(f"EyeCloud feed-source invocation failed: {type(exc).__name__}") from exc
        if completed.returncode != 0:
            raise Refusal(
                f"EyeCloud feed-source refused or failed with exit code {completed.returncode}"
            )
        try:
            envelope = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            raise Refusal("EyeCloud feed-source returned malformed JSON; refusing feed") from exc
        if not isinstance(envelope, dict) or set(envelope) != {"rows", "count"}:
            raise Refusal("EyeCloud feed-source returned an unknown envelope; refusing feed")
        rows = envelope["rows"]
        count = envelope["count"]
        if not isinstance(rows, list) or isinstance(count, bool) or not isinstance(count, int):
            raise Refusal("EyeCloud feed-source returned an invalid envelope; refusing feed")
        if count != len(rows):
            raise Refusal("EyeCloud feed-source count does not match rows; refusing feed")
        for row in rows:
            if not isinstance(row, dict) or set(row) != self.ROW_FIELDS:
                raise Refusal("EyeCloud feed-source returned an unknown row shape; refusing feed")
            if not all(isinstance(row[f], str) for f in ("patient_id", "recall_date", "mobile_phone")):
                raise Refusal("EyeCloud feed-source returned invalid row field types; refusing feed")
            recorded = row["phone_recorded_date"]
            if recorded is not None and not isinstance(recorded, str):
                raise Refusal("EyeCloud feed-source returned invalid phone_recorded_date; refusing feed")
        return rows


def recall_token(patient_id: str, recall_date: str) -> str:
    """Opaque, deterministic per-(patient, recall) token: ``rc-`` + 16 hex chars."""
    digest = hashlib.sha256(f"{patient_id}{recall_date}".encode("utf-8")).hexdigest()
    return f"rc-{digest[:16]}"


def preflight_gateway(
    health_url: str,
    *,
    http: HttpGet = http_get,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = 3,
    interval_s: float = 20.0,
) -> None:
    """Require ``attempts`` clean 200/``ok:true`` health responses ``interval_s`` apart.

    Any non-200, missing/false ``ok``, or transport error raises
    ``PreflightRefusal`` immediately so the caller writes nothing.
    """
    for attempt in range(attempts):
        status, body = http(health_url)
        healthy = status == 200 and isinstance(body, dict) and body.get("ok") is True
        if not healthy:
            raise PreflightRefusal(
                f"gateway preflight check {attempt + 1}/{attempts} failed (status={status})"
            )
        LOG.info("gateway preflight check %d/%d passed", attempt + 1, attempts)
        if attempt < attempts - 1:
            sleep(interval_s)


def build_feed_artifacts(
    rows: list[dict[str, Any]],
    *,
    snapshot_utc: str,
) -> tuple[bytes, dict[str, Any]]:
    """Turn EyeCloud rows into ``(csv_bytes, meta_dict)``.

    The only drop reason is E.164 failure, so the accounting invariant
    ``extracted == written + dropped_invalid_phone`` always holds and is
    asserted before returning. ``consent_date`` is taken verbatim from
    ``phone_recorded_date`` (coerced to an empty string when the source left it
    null); no other field is derived or carried through.
    """
    written: list[dict[str, str]] = []
    extracted = 0
    dropped_invalid_phone = 0
    for raw in rows:
        extracted += 1
        try:
            phone = normalize_e164(raw.get("mobile_phone"))
        except ValueError:
            dropped_invalid_phone += 1
            continue
        patient_id = str(raw.get("patient_id") or "").strip()
        recall_date = str(raw.get("recall_date") or "").strip()
        consent_date = str(raw.get("phone_recorded_date") or "")
        written.append({
            "phone_e164": phone,
            "consent_source": CONSENT_SOURCE,
            "consent_date": consent_date,
            "recall_token": recall_token(patient_id, recall_date),
            "patient_id": patient_id,
        })

    if extracted != len(written) + dropped_invalid_phone:  # pragma: no cover - invariant guard
        raise Refusal("feed row accounting invariant violated; refusing feed")

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FEED_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(written)
    csv_bytes = buffer.getvalue().encode("utf-8")

    meta = {
        "schema_version": "cvc-recall-campaign-feed-meta.v1",
        "extracted": extracted,
        "written": len(written),
        "dropped_invalid_phone": dropped_invalid_phone,
        "snapshot_utc": snapshot_utc,
    }
    return csv_bytes, meta


def _default_s3_client() -> Any:
    if boto3 is None:
        raise Refusal("boto3 is unavailable; cannot create an S3 client")
    return boto3.client("s3")


def _require(env: Mapping[str, str], name: str) -> str:
    value = (env.get(name) or "").strip()
    if not value:
        raise Refusal(f"{name} is required; refusing to run without it")
    return value


def run(
    *,
    env: Mapping[str, str] | None = None,
    adapter: EyeCloudAdapter | None = None,
    s3_client_factory: Callable[[], Any] = _default_s3_client,
    http: HttpGet = http_get,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> int:
    """Execute the extract. Returns 0 on success, or a refusal exit code.

    Client construction, EyeCloud access, HTTP, sleep, and the clock are all
    injectable so the unit tests never touch AWS or the network.
    """
    env = os.environ if env is None else env
    try:
        health_url = (env.get("GATEWAY_HEALTH_URL") or DEFAULT_HEALTH_URL).strip()
        window = (env.get("FEED_WINDOW") or DEFAULT_FEED_WINDOW).strip()
        bucket = _require(env, "FEED_BUCKET")
        kms_key_id = _require(env, "KMS_KEY_ID")
        cli_path = (env.get("ECP_CLI_PATH") or "").strip()

        preflight_gateway(health_url, http=http, sleep=sleep)

        if adapter is None:
            adapter = RealEyeCloudAdapter(cli_path=cli_path, window=window)
        rows = adapter.recall_contacts()

        moment = now()
        if moment.tzinfo is None:
            raise Refusal("snapshot clock must be timezone-aware")
        moment = moment.astimezone(timezone.utc)
        snapshot_utc = moment.isoformat().replace("+00:00", "Z")
        date_str = moment.date().isoformat()

        csv_bytes, meta = build_feed_artifacts(rows, snapshot_utc=snapshot_utc)

        client = s3_client_factory()
        meta_key = f"feeds/{date_str}.meta.json"
        feed_key = f"feeds/{date_str}.csv"
        meta_bytes = json.dumps(meta, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        # Sidecar first, feed last: the Stage B trigger fires on the .csv, so its
        # supporting metadata must already exist when that object appears.
        client.put_object(
            Bucket=bucket, Key=meta_key, Body=meta_bytes,
            ServerSideEncryption="aws:kms", SSEKMSKeyId=kms_key_id,
            ContentType="application/json",
        )
        client.put_object(
            Bucket=bucket, Key=feed_key, Body=csv_bytes,
            ServerSideEncryption="aws:kms", SSEKMSKeyId=kms_key_id,
            ContentType="text/csv",
        )
    except Refusal as exc:
        LOG.error("feed extract refused: %s", exc)
        print(f"REFUSAL: {exc}", file=sys.stderr)
        return exc.exit_code

    LOG.info(
        "feed extract complete extracted=%d written=%d dropped_invalid_phone=%d",
        meta["extracted"], meta["written"], meta["dropped_invalid_phone"],
    )
    print(json.dumps({
        "written": meta["written"],
        "dropped_invalid_phone": meta["dropped_invalid_phone"],
        "feed_key": feed_key,
        "external_actions_taken": 0,
    }))
    return 0


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    raise SystemExit(run())
