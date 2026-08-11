#!/usr/bin/env python3
"""Gated live probe for booked-then-alive behavior. Do not run during build."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

BLAND_BASE = "https://api.bland.ai/v1"
GW_BASE = "https://mott-booking-gw.mail.mybcat.com"
PATHWAY_ID = "94abad8b-fbe2-4e67-9c64-d9b586dd2653"
MESSAGES = ["hi", "thursday please", "1", "yes", "wait can I change it?", "are you still there?"]
OFFICE_DIGITS = "2122192219"
REBOOKING_CLAIM = re.compile(
    r"(?:\b(?:i|we)\s+(?:can|will|could|am able to|'ll)\s+(?:help\s+)?(?:rebook|reschedule|change|move|cancel|modify|find|check)\b|"
    r"\b(?:choose|pick|tell me)\s+(?:another|a new|a different)\s+(?:day|date|time|opening)\b|"
    r"\b(?:available|other|new)\s+(?:slot|opening|time)s?\b)",
    re.I,
)


def unwrap_secret(raw: str) -> str:
    """Accept a plain secret or the JSON envelopes emitted by secret_exec."""
    value = raw.strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    while isinstance(parsed, dict):
        for key in ("value", "secret", "api_key", "token", "password"):
            if key in parsed:
                parsed = parsed[key]
                break
        else:
            if len(parsed) == 1:
                parsed = next(iter(parsed.values()))
            else:
                raise ValueError("BLAND_API_KEY JSON envelope has no recognized secret field")
    if not isinstance(parsed, str) or not parsed.strip():
        raise ValueError("BLAND_API_KEY resolved to an empty or non-string value")
    return parsed.strip()


def request_json(url: str, payload: dict, headers: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "mybcat-cli", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:300]}") from exc
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"non-object JSON from {url}")
    return parsed


def first_string(value, keys: tuple[str, ...]) -> str:
    if isinstance(value, dict):
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for candidate in value.values():
            found = first_string(candidate, keys)
            if found:
                return found
    elif isinstance(value, list):
        for candidate in value:
            found = first_string(candidate, keys)
            if found:
                return found
    return ""


def appointment_rows(payload: dict) -> list[dict]:
    result = payload.get("result", payload)
    if isinstance(result, list):
        return [row for row in result if isinstance(row, dict)]
    if isinstance(result, dict):
        for key in ("appointments", "items", "rows", "data"):
            rows = result.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def appointment_id(row: dict) -> str:
    for key in ("appointment_id", "appt_id", "id", "AppointmentID", "ApptID"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise RuntimeError("appointment row has no recognized appointment id")


def mask(text: str) -> str:
    return re.sub(r"\d{7,}", lambda match: "*" * (len(match.group()) - 4) + match.group()[-4:], text)


def cleanup(gw_headers: dict, patient_id: str, store: str) -> int:
    listed = request_json(f"{GW_BASE}/appt-list", {"patient_id": patient_id, "store": store}, gw_headers)
    for row in appointment_rows(listed):
        request_json(
            f"{GW_BASE}/sign",
            {
                "verb": "appt.cancel",
                "target": appointment_id(row),
                "store": store,
                "reason": "patient-request",
                "params": {"appt_id": appointment_id(row), "day": str(row.get("start") or "")[:10]},
            },
            gw_headers,
        )
    remaining = request_json(f"{GW_BASE}/appt-list", {"patient_id": patient_id, "store": store}, gw_headers)
    rows = appointment_rows(remaining)
    reported = remaining.get("result", {}).get("count") if isinstance(remaining.get("result"), dict) else None
    return int(reported) if isinstance(reported, (int, float)) else len(rows)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: post_booking_probe.py <pathway_version>", file=sys.stderr)
        return 2
    required = ("BLAND_API_KEY", "GW_TOKEN", "HARNESS_PATIENT_ID", "HARNESS_CELL", "HARNESS_STORE")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print("missing environment: " + ", ".join(missing), file=sys.stderr)
        return 2

    bland_headers = {"authorization": unwrap_secret(os.environ["BLAND_API_KEY"])}
    gw_headers = {"Authorization": f"Bearer {os.environ['GW_TOKEN'].strip()}"}
    patient_id = os.environ["HARNESS_PATIENT_ID"].strip()
    store = os.environ["HARNESS_STORE"].strip()
    all_ok = True
    cleanup_count = -1
    responses: list[str] = []
    try:
        created = request_json(
            f"{BLAND_BASE}/pathway/chat/create",
            {
                "pathway_id": PATHWAY_ID,
                "pathway_version": int(sys.argv[1]),
                "request_data": {
                    "recall_patient_id": patient_id,
                    "recall_cell": os.environ["HARNESS_CELL"].strip(),
                    "store": store,
                    "campaign": "harness",
                },
            },
            bland_headers,
        )
        chat_id = first_string(created, ("chat_id", "id"))
        if not chat_id:
            raise RuntimeError("chat creation returned no chat id")
        for number, message in enumerate(MESSAGES, 1):
            reply = request_json(f"{BLAND_BASE}/pathway/chat/{chat_id}", {"message": message}, bland_headers)
            reply_data = reply.get("data") or {}
            said = " | ".join(str(item) for item in (reply_data.get("assistant_responses") or []) if str(item).strip())
            ok = bool(said.strip())
            if number == len(MESSAGES) - 1:
                ok = ok and OFFICE_DIGITS in re.sub(r"\D", "", said) and REBOOKING_CLAIM.search(said) is None
            elif number == len(MESSAGES):
                ok = ok and REBOOKING_CLAIM.search(said) is None
            all_ok = all_ok and ok
            responses.append(said)
            print(mask(f"TURN={number} OK={str(ok).lower()} SAID={said[:120]}"))
    except Exception as exc:
        all_ok = False
        print(mask(f"PROBE_ERROR={exc}"), file=sys.stderr)
    finally:
        try:
            cleanup_count = cleanup(gw_headers, patient_id, store)
        except Exception as exc:
            all_ok = False
            print(mask(f"CLEANUP_ERROR={exc}"), file=sys.stderr)

    all_ok = all_ok and cleanup_count == 0 and len(responses) == len(MESSAGES)
    print(f"PROBE_RESULT booked_then_alive={str(all_ok).lower()} cleanup_count={cleanup_count}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
