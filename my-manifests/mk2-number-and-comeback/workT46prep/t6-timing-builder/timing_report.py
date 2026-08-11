#!/usr/bin/env python3
"""Decompose Bland SMS reply latency using message and CloudWatch records."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


GATEWAY_PATH = Path(
    "/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/"
    "raw-text-authority-v2/bland_gateway_live.py"
)
LOG_GROUP = "/ecs/mott-booking-gateway"
REGION = "us-east-1"
TIMESTAMP_KEYS = (
    "created_at", "timestamp", "createdAt", "sent_at", "sentAt",
    "updated_at", "updatedAt", "delivered_at", "deliveredAt",
)


def fail(message: str) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(1)


def load_gateway():
    if not GATEWAY_PATH.is_file():
        fail(f"fetch failure: gateway source not found: {GATEWAY_PATH}")
    spec = importlib.util.spec_from_file_location("mott_bland_gateway_live", GATEWAY_PATH)
    if spec is None or spec.loader is None:
        fail("fetch failure: could not create gateway module spec")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        fail(f"fetch failure: gateway import failed: {type(exc).__name__}: {exc}")
    return module


def fetch_messages(conversation_id: str) -> list[dict]:
    if not os.environ.get("BLAND_API_KEY"):
        fail("fetch failure: BLAND_API_KEY is not set")
    gateway = load_gateway()
    try:
        messages = gateway._fetch_conversation(conversation_id)
    except Exception as exc:
        fail(f"fetch failure: Bland request failed: {type(exc).__name__}: {exc}")
    if not messages:
        fail("fetch failure: gateway fetch returned no conversation messages")
    if not all(isinstance(item, dict) for item in messages):
        fail("fetch failure: conversation messages contain a non-object record")
    # Copy whole records. In particular, do not project away timestamps returned by Bland.
    return [dict(item) for item in messages]


def parse_iso(value: object) -> tuple[datetime | None, str | None]:
    if value is None or value == "":
        return None, "timestamp field is absent"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if abs(number) > 100_000_000_000:
            number /= 1000.0
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc), None
        except (ValueError, OSError, OverflowError):
            return None, f"invalid numeric timestamp {value!r}"
    raw = str(value).strip()
    # Date + hour/minute, with no seconds, cannot support sub-minute decomposition.
    if re.search(r"[T ]\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?$", raw):
        limitation = f"timestamp lacks sub-minute precision: {raw}"
    else:
        limitation = None
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, f"unparseable timestamp {raw!r}"
    if parsed.tzinfo is None:
        return None, f"timestamp lacks UTC offset: {raw}"
    return parsed.astimezone(timezone.utc), limitation


def primary_timestamp(message: dict) -> tuple[object | None, datetime | None, str | None]:
    for key in TIMESTAMP_KEYS:
        if key in message and message[key] not in (None, ""):
            parsed, limitation = parse_iso(message[key])
            return message[key], parsed, limitation
    return None, None, "needed message timestamp field is absent"


def role_of(message: dict) -> str:
    raw = str(
        message.get("role") or message.get("sender") or message.get("author")
        or message.get("from") or message.get("type") or ""
    ).strip().lower()
    if raw in {"user", "patient", "human", "customer", "inbound"}:
        return "patient"
    if raw in {"assistant", "agent", "ai", "bot", "bland", "outbound"}:
        return "agent"
    direction = str(message.get("direction") or "").lower()
    if direction in {"inbound", "incoming"}:
        return "patient"
    if direction in {"outbound", "outgoing"}:
        return "agent"
    return "unknown"


def mask_text(text: object) -> str:
    return re.sub(
        r"\d{5,}",
        lambda match: "*" * (len(match.group(0)) - 4) + match.group(0)[-4:],
        str(text),
    )


def fetch_logs(start: datetime, end: datetime, conversation_id: str) -> list[dict]:
    command = [
        "aws", "logs", "filter-log-events", "--log-group-name", LOG_GROUP,
        "--region", REGION, "--start-time", str(int(start.timestamp() * 1000)),
        "--end-time", str(int(end.timestamp() * 1000)), "--output", "json",
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    except FileNotFoundError:
        fail("fetch failure: aws CLI is not installed")
    except subprocess.TimeoutExpired:
        fail("fetch failure: CloudWatch aws CLI call timed out after 120s")
    if proc.returncode != 0:
        reason = (proc.stderr or proc.stdout or "unknown aws CLI error").strip().splitlines()[-1]
        fail(f"fetch failure: CloudWatch request failed: {mask_text(reason)}")
    try:
        events = json.loads(proc.stdout).get("events", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        fail(f"fetch failure: invalid CloudWatch response: {type(exc).__name__}")
    # Only logs carrying the ID can truthfully be assigned to this conversation.
    return [e for e in events if conversation_id in str(e.get("message", ""))]


def fmt_dt(value: datetime | None) -> str:
    return value.isoformat().replace("+00:00", "Z") if value else ""


def seconds(start: datetime | None, end: datetime | None) -> float | None:
    return round((end - start).total_seconds(), 3) if start and end else None


def shown(value: float | None) -> str:
    return "NA" if value is None else f"{value:.3f}"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <conversation_id>", file=sys.stderr)
        return 2
    conversation_id = sys.argv[1]
    start_raw, end_raw = os.environ.get("WINDOW_START"), os.environ.get("WINDOW_END")
    start, start_err = parse_iso(start_raw)
    end, end_err = parse_iso(end_raw)
    if start_err or end_err or not start or not end or end <= start:
        fail(f"fetch failure: invalid WINDOW_START/WINDOW_END: {start_err or end_err or 'end must follow start'}")

    messages = fetch_messages(conversation_id)
    limitations: set[str] = set()
    ordered = []
    for position, message in enumerate(messages):
        raw_ts, parsed_ts, limitation = primary_timestamp(message)
        if limitation:
            limitations.add(limitation)
        ordered.append({"position": position, "record": message, "raw_ts": raw_ts,
                        "ts": parsed_ts, "role": role_of(message)})
    # Sort only timestamped records; stable API order breaks ties and retains untimestamped placement.
    if all(item["ts"] for item in ordered):
        ordered.sort(key=lambda item: (item["ts"], item["position"]))
    unknown_roles = sum(item["role"] == "unknown" for item in ordered)
    if unknown_roles:
        limitations.add(f"{unknown_roles} message record(s) have no recognized sender/role field")

    logs = fetch_logs(start, end, conversation_id)
    log_times = sorted(
        datetime.fromtimestamp(float(event["timestamp"]) / 1000, tz=timezone.utc)
        for event in logs if isinstance(event.get("timestamp"), (int, float))
    )
    patients = [item for item in ordered if item["role"] == "patient"]
    rows = []
    reply_totals = []
    for index, patient in enumerate(patients):
        next_patient_pos = patients[index + 1]["position"] if index + 1 < len(patients) else math.inf
        agents = [item for item in ordered if item["role"] == "agent"
                  and patient["position"] < item["position"] < next_patient_pos]
        msg1 = agents[0] if agents else None
        msg2 = agents[1] if len(agents) > 1 else None
        klass = "filler+answer" if msg2 else ("single-answer" if msg1 else "no-reply")
        gap1 = seconds(patient["ts"], msg1["ts"] if msg1 else None)
        gap2 = seconds(msg1["ts"] if msg1 else None, msg2["ts"] if msg2 else None)
        final_agent = msg2 or msg1
        total = seconds(patient["ts"], final_agent["ts"] if final_agent else None)
        if total is not None:
            reply_totals.append(total)
        boundary = patients[index + 1]["ts"] if index + 1 < len(patients) else end
        attributable = [ts for ts in log_times if patient["ts"] and patient["ts"] <= ts < boundary]
        rows.append({
            "turn": index + 1, "patient_ts": fmt_dt(patient["ts"]),
            "gw_first_log_ts": fmt_dt(attributable[0]) if attributable else "",
            "gw_last_log_ts": fmt_dt(attributable[-1]) if attributable else "",
            "agent_msg1_ts": fmt_dt(msg1["ts"] if msg1 else None),
            "agent_msg2_ts": fmt_dt(msg2["ts"] if msg2 else None),
            "gap_patient_to_msg1_s": "" if gap1 is None else gap1,
            "gap_msg1_to_msg2_s": "" if gap2 is None else gap2,
            "msg_class": klass,
        })

    fields = ["turn", "patient_ts", "gw_first_log_ts", "gw_last_log_ts", "agent_msg1_ts",
              "agent_msg2_ts", "gap_patient_to_msg1_s", "gap_msg1_to_msg2_s", "msg_class"]
    with open("waterfall.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        first = None if row["gap_patient_to_msg1_s"] == "" else float(row["gap_patient_to_msg1_s"])
        between = None if row["gap_msg1_to_msg2_s"] == "" else float(row["gap_msg1_to_msg2_s"])
        print(f"WATERFALL turn={row['turn']} gap_to_first={shown(first)} "
              f"gap_between={shown(between)} class={row['msg_class']}")
    two_count = sum(row["msg_class"] == "filler+answer" for row in rows)
    print(f"TWO_MSG_TURNS={two_count}/{len(rows)}")
    if reply_totals:
        sorted_totals = sorted(reply_totals)
        p95 = sorted_totals[max(0, math.ceil(0.95 * len(sorted_totals)) - 1)]
        print(f"SUMMARY median_reply_s={statistics.median(sorted_totals):.3f} p95_reply_s={p95:.3f}")
    else:
        print("SUMMARY median_reply_s=NA p95_reply_s=NA")
    if not log_times:
        print("UNMEASURED: gateway processing per turn - conversation ID not present in CloudWatch records")
    print("UNMEASURED: carrier delivery to handset - not present in any record")
    for limitation in sorted(limitations):
        print(f"UNMEASURED: message timing - {limitation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
