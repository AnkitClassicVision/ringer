#!/usr/bin/env python3
"""CVC Bland-facing shim for the five locked EyeCloud appointment endpoints."""

from __future__ import annotations

import errno
import fcntl
import hmac
import json
import logging
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capability_registry import QueryError, load_manifest, prepare_query, render_query_result

try:  # boto3 is optional so the gateway and offline tests import without it.
    import boto3
except ImportError:  # pragma: no cover - exercised only where boto3 is absent
    boto3 = None

CLI = os.environ.get("ECP_CLI", "/usr/local/bin/eyecloud-pro-pp-cli")
AWS_ENV_WRAPPER = os.environ.get("ECP_AWS_ENV_WRAPPER", str(Path.home() / ".local/bin/eyecloud-pro-aws-env"))
HOST = os.environ.get("ECP_SHIM_HOST", "127.0.0.1")
PORT = int(os.environ.get("ECP_SHIM_PORT", "8431"))
TIMEOUT_S = int(os.environ.get("ECP_CLI_TIMEOUT_S", "90"))
MAX_BODY = 16 * 1024
MAX_VALUE_LEN = 200

TEST_MODE = os.environ.get("ECP_SHIM_TEST_MODE", "0") == "1"
ECP_QUERY_RELEASE_GATE = os.environ.get("ECP_QUERY_RELEASE_GATE", "BLOCK")
TEST_LAST_PREFIX = os.environ.get("ECP_SHIM_TEST_LAST_PREFIX", "ZZTEST")
TEST_PATIENT_IDS = {
    p.strip()
    for p in os.environ.get("ECP_SHIM_TEST_PATIENTS", "4274030798").split(",")
    if p.strip()
}

API_KEY = os.environ.get("ECP_SHIM_BEARER", "")
READ_PRINCIPAL = os.environ.get("ECP_READ_PRINCIPAL", "bland-read")
TENANT_ID = os.environ.get("ECP_TENANT_ID", "cvc")


def load_query_credential_record(raw: str) -> dict:
    """Parse the deployment-bound /query credential without logging its value."""
    try:
        record = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(record, dict) or set(record) != {"token", "tenant", "principal"}:
        return {}
    if not all(isinstance(record[key], str) and record[key].strip() for key in record):
        return {}
    return {key: record[key].strip() for key in record}


CONSUMER_CREDENTIAL_FIELDS = {
    "consumer_id",
    "token",
    "tenant",
    "principal",
    "enabled",
    "routes",
    "rate_per_minute",
}


def load_consumer_credential_set(raw: str) -> tuple[list[dict], bool]:
    """Parse all consumer credentials atomically without logging their values."""
    if not isinstance(raw, str) or not raw.strip():
        return [], False
    try:
        document = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return [], True
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "consumers"}
        or not isinstance(document["version"], int)
        or isinstance(document["version"], bool)
        or not isinstance(document["consumers"], list)
    ):
        return [], True

    consumers = []
    consumer_ids = set()
    tokens = []
    for record in document["consumers"]:
        if not isinstance(record, dict) or set(record) != CONSUMER_CREDENTIAL_FIELDS:
            return [], True
        if not all(
            isinstance(record[key], str) and record[key].strip()
            for key in ("consumer_id", "token", "tenant", "principal")
        ):
            return [], True
        if not isinstance(record["enabled"], bool):
            return [], True
        if (
            not isinstance(record["routes"], list)
            or not all(isinstance(route, str) and route.strip() for route in record["routes"])
        ):
            return [], True
        if (
            not isinstance(record["rate_per_minute"], int)
            or isinstance(record["rate_per_minute"], bool)
        ):
            return [], True

        consumer_id = record["consumer_id"].strip()
        token = record["token"].strip()
        if consumer_id in consumer_ids or any(
            hmac.compare_digest(token, existing_token) for existing_token in tokens
        ):
            return [], True
        consumer_ids.add(consumer_id)
        tokens.append(token)
        consumers.append(
            {
                **record,
                "consumer_id": consumer_id,
                "token": token,
                "tenant": record["tenant"].strip(),
                "principal": record["principal"].strip(),
                "routes": [route.strip() for route in record["routes"]],
            }
        )
    return consumers, False


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


QUERY_CREDENTIAL = load_query_credential_record(
    os.environ.get("ECP_QUERY_CREDENTIAL_RECORD", "")
)
if QUERY_CREDENTIAL:
    API_KEY = API_KEY or QUERY_CREDENTIAL["token"]
_CONSUMER_CREDENTIALS_RAW = os.environ.get("ECP_CONSUMER_CREDENTIALS", "")
CONSUMER_CREDENTIALS_CONFIGURED = bool(_CONSUMER_CREDENTIALS_RAW.strip())
CONSUMER_CREDENTIALS, CONSUMER_CREDENTIALS_LOAD_FAILED = load_consumer_credential_set(
    _CONSUMER_CREDENTIALS_RAW
)
CONSUMER_ACCEPT_LEGACY = _env_bool("ECP_CONSUMER_ACCEPT_LEGACY", True)
_DATE_ORDINAL_FALLBACK = _env_bool("ECP_DATE_ORDINAL_FALLBACK", False)
_RAW_TEXT_DATES = _env_bool("ECP_RAW_TEXT_DATES", False)
CAPABILITY_MANIFEST = load_manifest()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cvc-booking-gateway")

ENDPOINTS = {
    "/availability": (
        "availability",
        {
            "store": "--store",
            "from": "--from",
            "to": "--to",
            "doctor": "--doctor",
            "min_minutes": "--min-minutes",
            "slot_minutes": "--slot-minutes",
            "after": "--after",
            "before": "--before",
        },
        False,
    ),
    "/conflict-check": (
        "conflict-check",
        {"store": "--store", "doctor": "--doctor", "start": "--start", "end": "--end"},
        False,
    ),
    "/patient-search": (
        "patient-search",
        {"last": "--last", "first": "--first", "phone": "--phone", "dob": "--dob"},
        False,
    ),
    "/book": (
        "book",
        {
            "patient_id": "--patient",
            "store": "--store",
            "doctor": "--doctor",
            "start": "--start",
            "end": "--end",
            "type": "--type",
            "notes": "--notes",
        },
        True,
    ),
    "/book-new-patient": (
        "book-new-patient",
        {
            "first": "--first",
            "last": "--last",
            "dob": "--dob",
            "phone": "--phone",
            "email": "--email",
            "gender": "--gender",
            "addr": "--addr",
            "city": "--city",
            "state": "--state",
            "zip": "--zip",
            "ssn_last4": "--ssn-last4",
            "store": "--store",
            "doctor": "--doctor",
            "start": "--start",
            "end": "--end",
            "type": "--type",
            "notes": "--notes",
        },
        True,
    ),
    "/cancel": (
        "cancel",
        {
            "store": "--store",
            "appt_id": "--appt-id",
            "day": "--day",
        },
        True,
    ),
    "/reschedule": (
        "reschedule",
        {
            "store": "--store",
            "appt_id": "--appt-id",
            "day": "--day",
            "start": "--new-start",
            "end": "--new-end",
        },
        True,
    ),
    # Read-only: a caller's upcoming appointments, for the reschedule/cancel lane.
    # patient_id is required (the caller is already resolved in the identity lane);
    # never allow an unfiltered list.
    "/appt-list": (
        "list",
        {
            "patient_id": "--patient",
            "last": "--last",
            "dob": "--dob",
            "store": "--store",
            "from": "--from",
            "to": "--to",
            "include_past": "--include-past",
        },
        False,
    ),
}

_DEFAULT_STORE_REGISTRY = {
    # Mott rotates providers by weekday, so the safe default does not force one.
    "711": {"name": "MS", "doctor": "", "alt": ""},
    "956": {"name": "Kennesaw", "doctor": "3281237823", "alt": "East Cobb"},
    "958": {"name": "East Cobb", "doctor": "1006898359", "alt": "Kennesaw"},
}


def _store_registry() -> dict:
    try:
        configured = json.loads(os.environ.get("ECP_STORE_REGISTRY", "{}") or "{}")
    except (TypeError, json.JSONDecodeError):
        return dict(_DEFAULT_STORE_REGISTRY)
    if not isinstance(configured, dict):
        return dict(_DEFAULT_STORE_REGISTRY)
    return {**_DEFAULT_STORE_REGISTRY, **configured}


STORE_ID_NAMES = {}
STORE_DOCTORS = {}
ALT_STORES = {}
for _store_id, _store in _store_registry().items():
    if not isinstance(_store, dict):
        continue
    _store_id = str(_store_id).strip()
    _store_name = str(_store.get("name", "")).strip()
    _store_doctor = str(_store.get("doctor", "")).strip()
    _store_alt = str(_store.get("alt", "")).strip()
    if not _store_id or not _store_name:
        continue
    STORE_ID_NAMES[_store_id] = _store_name
    STORE_DOCTORS[_store_id] = _store_doctor
    STORE_DOCTORS[_store_name.lower()] = _store_doctor
    if _store_alt:
        ALT_STORES[_store_id] = _store_alt
        ALT_STORES[_store_name.lower()] = _store_alt

TIME_PREFS = {
    "morning": [("--before", "12:00 pm")],
    "afternoon": [("--after", "12:00 pm")],
    "evening": [("--after", "04:00 pm")],
}
DAYKEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Availability and booking are FORCED to the store's registered provider so
# phantom scheduler columns (e.g. 2895935197) are never offered or booked. Any
# caller-supplied doctor is ignored. (owner-confirmed 2026-07-01)
def normalize_phone(val) -> str:
    # EyeCloud phone_search matches 10-digit / (xxx) xxx-xxxx forms but NOT
    # E.164 (+1XXXXXXXXXX), which is what Bland's {{from}} sends — that mismatch
    # made real callers hit the "no match" lane (live probe 2026-07-01). Reduce
    # to the bare 10 digits; pass anything else through unchanged.
    digits = re.sub(r"\D", "", str(val))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else str(val).strip()


def _eastern_today():
    from datetime import datetime, timedelta, timezone
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=-5)))


def _hours_cfg() -> dict:
    return json.loads(os.environ.get("CVC_HOURS_JSON", "{}") or "{}")


def _day_window(cfg, store_cfg, d):
    if d.strftime("%Y-%m-%d") in set(cfg.get("holidays", [])):
        return None
    win = store_cfg.get(DAYKEYS[d.weekday()])
    if not win:
        return None
    o_h, o_m = map(int, win[0].split(":"))
    c_h, c_m = map(int, win[1].split(":"))
    return (
        d.replace(hour=o_h, minute=o_m, second=0, microsecond=0),
        d.replace(hour=c_h, minute=c_m, second=0, microsecond=0),
    )


def _fmt(dt):
    # Zero-padded hour (%I, not %-I): the EyeCloud scheduler CLI rejects
    # unpadded times ('bad --start: unrecognized scheduler time "07/14/2026
    # 4:00 pm"', proven live 2026-07-14 on the urgent double-book lane), and
    # the CLI's own availability output is padded, so padded is canonical.
    return dt.strftime("%m/%d/%Y %I:%M %p").lower()


def normalize_sched_time(sval: str) -> str:
    """Re-emit a scheduler timestamp with a zero-padded hour.

    Callers (including older pathway versions and cached variables) may send
    '07/14/2026 4:00 pm'; the EyeCloud CLI only accepts '07/14/2026 04:00 pm'.
    Unparseable values pass through unchanged so the CLI still reports them.
    """
    try:
        dt = datetime.strptime(str(sval).strip().lower(), "%m/%d/%Y %I:%M %p")
    except ValueError:
        return sval
    return dt.strftime("%m/%d/%Y %I:%M %p").lower()


def hours_state(store: str, now) -> dict:
    cfg = _hours_cfg()
    store_cfg = (cfg.get("stores") or {}).get(str(store).strip().lower())
    if not store_cfg:
        raise ValueError("unknown store")
    buf = int(cfg.get("about_to_close_minutes", 30))
    win = _day_window(cfg, store_cfg, now)
    state, closes_at = "after_hours", ""
    if win and win[0] <= now < win[1]:
        closes_at = _fmt(win[1])
        state = "about_to_close" if (win[1] - now).total_seconds() <= buf * 60 else "open"
    probe = now
    if not (win and now < win[0]):
        probe = probe + timedelta(days=1)
    for _ in range(14):
        w = _day_window(cfg, store_cfg, probe.replace(hour=0, minute=0))
        if w:
            first_am = w[0]
            break
        probe = probe + timedelta(days=1)
    else:
        raise ValueError("no open day within 14 days")
    return {"state": state, "closes_at": closes_at, "first_am_start": _fmt(first_am)}


def _next_open_dt(cfg, store_cfg, now):
    probe = now
    if not (_day_window(cfg, store_cfg, now) and now < _day_window(cfg, store_cfg, now)[0]):
        probe = probe + timedelta(days=1)
    for _ in range(14):
        w = _day_window(cfg, store_cfg, probe.replace(hour=0, minute=0))
        if w:
            return w[0]
        probe = probe + timedelta(days=1)
    raise ValueError("no open day within 14 days")


def _next_boundary(now):
    # Strictly-next :00 / :30 boundary at or after now+ (never now itself).
    add = (30 - now.minute % 30) % 30 or 30
    return now.replace(second=0, microsecond=0) + timedelta(minutes=add)


def urgent_window(store: str, slot_mode: str, now) -> dict:
    """Resolve the concrete availability window + double-book target for an urgent
    booking. same_day only holds while the office is open/about-to-close; anything
    else (or an after-hours same_day request) falls back to first_am. Pure function
    of (store, mode, now) so the pathway never does date math."""
    cfg = _hours_cfg()
    store_cfg = (cfg.get("stores") or {}).get(str(store).strip().lower())
    if not store_cfg:
        raise ValueError("unknown store")
    mode = str(slot_mode).strip().lower()
    win = _day_window(cfg, store_cfg, now)
    open_now = bool(win and win[0] <= now < win[1])
    if mode == "same_day" and open_now:
        book_start = _next_boundary(now)
        last = win[1] - timedelta(minutes=30)
        if book_start > last:
            book_start = last
        return {"mode": "same_day", "avail_from": _fmt(now), "avail_to": _fmt(win[1]),
                "book_start": _fmt(book_start), "book_end": _fmt(book_start + timedelta(minutes=30))}
    first_am = _next_open_dt(cfg, store_cfg, now)
    return {"mode": "first_am", "avail_from": _fmt(first_am),
            "avail_to": _fmt(first_am + timedelta(hours=4)),
            "book_start": _fmt(first_am), "book_end": _fmt(first_am + timedelta(minutes=30))}


def verify_booking(book_pid: str, new_id: str, run_list_fn) -> bool:
    """BOOK-PROOF read-after-write. Returns True only when the freshly-created
    appointment id is actually present in a re-read of the patient's appointment
    list. run_list_fn(patient_id) -> parsed CLI 'appt list' result (or None on
    failure). Any failure, missing id, or unparseable read -> False (never a
    false 'booked')."""
    new_id = str(new_id or "").strip()
    if len(new_id) < 4 or not book_pid:
        return False
    try:
        listing = run_list_fn(book_pid)
    except Exception:
        return False
    if listing is None:
        return False
    return new_id in json.dumps(listing)


def alert_sms_recipients(state: str) -> list:
    """Hours-conditional SMS ping recipients. Open/about-to-close -> front desk;
    after-hours -> on-call doctor. Falls back to the flat list when the split
    envs are unset."""
    flat = os.environ.get("CVC_ALERT_SMS_TO", "").strip()
    if state in ("open", "about_to_close"):
        picked = os.environ.get("CVC_ALERT_SMS_TO_OPEN", "").strip() or flat
    else:
        picked = os.environ.get("CVC_ALERT_SMS_TO_AFTERHOURS", "").strip() or flat
    return [n.strip() for n in picked.split(",") if n.strip()]


_WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}


_ORDINAL_MONTHS = (
    "january|february|march|april|may|june|july|august|september|"
    "october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
)


def _ordinal_suffix(day: int) -> str:
    if 11 <= day % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def resolve_relative_date(raw) -> str | None:
    # Dates reach us from LLM-extracted variables; the CLI only accepts
    # MM/DD/YYYY or YYYY-MM-DD, so anything else must be resolved here, not
    # left for the model to format (live failure 2026-07-21: "Friday" reached
    # the CLI verbatim -> 409). Bare/this/next weekday means the next future
    # occurrence (Eastern, never today). "Next week" means the next calendar
    # week's Monday. English and Chinese weekday-plus-week phrases use that
    # weekday in the next/second-next Monday-anchored calendar week.
    # Explicit-year dates pass through unmodified; rewriting a year the caller
    # stated would surprise them.
    from datetime import datetime, timedelta

    today = _eastern_today().date()
    t = re.sub(r"[.,!?]", "", str(raw or "").strip().lower())
    t = re.sub(r"\s+", " ", t)
    if not t:
        return None

    def emit(day):
        return day.strftime("%m/%d/%Y")

    def next_weekday(weekday):
        ahead = (weekday - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)

    def calendar_weekday(weekday, weeks_ahead):
        monday = today - timedelta(days=today.weekday())
        return monday + timedelta(weeks=weeks_ahead, days=weekday)

    simple_days = {
        "today": 0, "tomorrow": 1, "tmrw": 1, "tmr": 1,
        "day after tomorrow": 2,
        "今天": 0, "明天": 1, "后天": 2, "大后天": 3,
    }
    if t in simple_days:
        return emit(today + timedelta(days=simple_days[t]))

    if t in ("next week", "下周"):
        return emit(calendar_weekday(0, 1))

    # "Coming weekend" follows the existing bare-weekday rule: it is always
    # the next future Saturday, even when today is Saturday.
    if t in ("weekend", "this weekend", "周末", "这周末"):
        return emit(next_weekday(5))
    if t == "next weekend":
        return emit(next_weekday(5) + timedelta(days=7))
    if t == "下周末":
        return emit(calendar_weekday(5, 1))

    match = re.fullmatch(r"(?:in )?(\d+) days(?: from now)?", t)
    if not match:
        match = re.fullmatch(r"(\d+) days from now", t)
    if match:
        return emit(today + timedelta(days=int(match.group(1))))

    number_words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "couple": 2,
    }
    match = re.fullmatch(r"in (?:a|a (couple)|(\d+|one|two|three|four|five|six|seven|eight|nine|ten|couple)) weeks?", t)
    if match:
        count_text = match.group(1) or match.group(2)
        count = 1 if count_text is None else number_words.get(
            count_text, int(count_text) if count_text.isdigit() else None
        )
        return emit(today + timedelta(days=7 * count))
    match = re.fullmatch(r"(\d+) weeks (?:from now|out)", t)
    if match:
        return emit(today + timedelta(days=7 * int(match.group(1))))

    zh_numbers = {
        "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    }
    match = re.fullmatch(r"(\d+|[一二两三四五六七八九十])天后", t)
    if match:
        count = int(match.group(1)) if match.group(1).isdigit() else zh_numbers[match.group(1)]
        return emit(today + timedelta(days=count))
    match = re.fullmatch(r"(\d+|[一二两三四五六七八九十])(?:周|个星期)后", t)
    if match:
        count = int(match.group(1)) if match.group(1).isdigit() else zh_numbers[match.group(1)]
        return emit(today + timedelta(days=7 * count))

    zh_weekdays = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
    match = re.fullmatch(r"(下下|下|这|本)?(?:周|星期|礼拜)([一二三四五六日天])", t)
    if match:
        prefix, day_text = match.groups()
        weekday = zh_weekdays[day_text]
        if prefix == "下":
            return emit(calendar_weekday(weekday, 1))
        if prefix == "下下":
            return emit(calendar_weekday(weekday, 2))
        return emit(next_weekday(weekday))

    weekday_pattern = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))
    match = re.fullmatch(rf"(?:day after next|the day after) ({weekday_pattern})", t)
    if match:
        return emit(next_weekday(_WEEKDAYS[match.group(1)]) + timedelta(days=1))
    match = re.fullmatch(rf"({weekday_pattern}) after next", t)
    if match:
        return emit(calendar_weekday(_WEEKDAYS[match.group(1)], 2))
    match = re.fullmatch(rf"(?:a week from ({weekday_pattern})|({weekday_pattern}) next week)", t)
    if match:
        weekday_text = match.group(1) or match.group(2)
        return emit(calendar_weekday(_WEEKDAYS[weekday_text], 1))

    weekday_text = re.sub(r"^(this|next|on|coming)\s+", "", t)
    if weekday_text in _WEEKDAYS:
        return emit(next_weekday(_WEEKDAYS[weekday_text]))
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(t, fmt).date().strftime("%m/%d/%Y")
        except ValueError:
            continue
    # Yearless dates: the year is ours to pick, so a day that already passed
    # this year means the next occurrence.
    for fmt in ("%m/%d", "%B %d", "%b %d"):
        try:
            d = datetime.strptime(t, fmt).date().replace(year=today.year)
        except ValueError:
            continue
        if d < today:
            try:
                d = d.replace(year=d.year + 1)
            except ValueError:  # Feb 29
                d = d.replace(month=2, day=28, year=d.year + 1)
        return d.strftime("%m/%d/%Y")
    if _DATE_ORDINAL_FALLBACK and TENANT_ID != "cvc":
        m = re.fullmatch(r"(" + _ORDINAL_MONTHS + r") (\d{1,2})(st|nd|rd|th)( \d{4})?", t)
        if m and 1 <= int(m.group(2)) <= 31 and m.group(3) == _ordinal_suffix(int(m.group(2))):
            return resolve_relative_date(f"{m.group(1)} {m.group(2)}{m.group(4) or ''}")
    if _DATE_ORDINAL_FALLBACK and TENANT_ID != "cvc":
        _RELATIVE_PREFIX = {"today", "tomorrow", "tmrw", "tmr"}
        _compound_words = t.split()
        if len(_compound_words) >= 3 and (_compound_words[0] in _RELATIVE_PREFIX or _compound_words[0] in _WEEKDAYS):
            remainder = " ".join(_compound_words[1:])
            if any(m in remainder for m in _ORDINAL_MONTHS.split("|")):
                result = resolve_relative_date(remainder)
                if result is not None:
                    return result
    return None


def extract_date_from_text(text) -> str | None:
    normalized = re.sub(
        r"[^A-Za-z0-9\s/\-:,;.?!\u3400-\u4dbf\u4e00-\u9fff]",
        " ",
        str(text or ""),
    ).lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"\bcan\s+t\b", "can not", normalized)
    normalized = re.sub(r"\bwon\s+t\b", "will not", normalized)
    normalized = re.sub(r"\bdon\s+t\b", "do not", normalized)
    shorthand = {
        "nxt": "next", "wk": "week", "wks": "weeks",
        "tmrw": "tomorrow", "tmr": "tomorrow", "2day": "today",
        "2moro": "tomorrow", "2morrow": "tomorrow",
    }
    normalized = " ".join(shorthand.get(token, token) for token in normalized.split())
    if not normalized:
        return None

    explicit = re.compile(
        r"\b(" + _ORDINAL_MONTHS + r")\s+(\d{1,2})(st|nd|rd|th)?"
        r"(?:\s*,?\s*(\d{4}))?\b"
    )
    history_terms = (
        "ago", "last time", "renewed", "paid", "birthday", "born",
        "since", "back in", "history",
    )
    address_terms = (
        "avenue", "ave", "street", "road", "rd", "blvd", "boulevard",
        "drive", "apartment", "apt", "unit", "suite", "floor", "zip",
    )
    negators = (
        "cannot", "can not", "cant", "wont", "will not", "dont", "do not",
        "not", "no", "never", "except", "anything but", "rather than",
        "instead of",
    )
    candidates = []
    order = 0

    # "Anything but Friday" is a negation phrase, not a correction boundary.
    clause_texts = re.split(
        r"\s*[;.?!]\s*|(?<!anything)\s+\bbut\b\s+",
        normalized,
    )
    for clause_index, clause in enumerate(clause_texts):
        if not clause.strip():
            continue
        clause_killed = any(
            re.search(rf"\b{re.escape(term)}\b", clause)
            for term in history_terms + address_terms
        )
        offset = 0
        for segment_index, segment in enumerate(clause.split(",")):
            segment = segment.strip()
            if not segment:
                offset += 1
                continue

            def killed(start):
                if clause_killed:
                    return True
                before = segment[:start]
                return any(
                    re.search(rf"\b{re.escape(term)}\b", before)
                    for term in negators
                )

            occupied = []
            for match in explicit.finditer(segment):
                day = int(match.group(2))
                suffix = match.group(3)
                if not 1 <= day <= 31 or (
                    suffix is not None and suffix != _ordinal_suffix(day)
                ):
                    continue
                phrase = f"{match.group(1)} {day}"
                if match.group(4):
                    phrase += f" {match.group(4)}"
                result = resolve_relative_date(phrase)
                if result and not killed(match.start()):
                    candidates.append(("explicit", clause_index, segment_index,
                                       offset + match.start(), order, result))
                    order += 1
                occupied.append(match.span())

            for match in re.finditer(r"(\d{1,2})月(\d{1,2})[号日]", segment):
                result = resolve_relative_date(f"{match.group(1)}/{match.group(2)}")
                if result and not killed(match.start()):
                    candidates.append(("explicit", clause_index, segment_index,
                                       offset + match.start(), order, result))
                    order += 1
                occupied.append(match.span())

            for match in re.finditer(r"\b(?:the\s+)?(\d{1,2})(st|nd|rd|th)\b", segment):
                if any(a <= match.start() < b for a, b in occupied):
                    continue
                day = int(match.group(1))
                if not 1 <= day <= 31 or match.group(2) != _ordinal_suffix(day):
                    continue
                today = _eastern_today().date()
                year, month = today.year, today.month
                if day < today.day:
                    month += 1
                    if month == 13:
                        year, month = year + 1, 1
                while True:
                    try:
                        result = datetime(year, month, day).strftime("%m/%d/%Y")
                        break
                    except ValueError:
                        month += 1
                        if month == 13:
                            year, month = year + 1, 1
                if not killed(match.start()):
                    candidates.append(("bare", clause_index, segment_index,
                                       offset + match.start(), order, result))
                    order += 1
                occupied.append(match.span())

            token_matches = list(re.finditer(r"\S+", segment))
            for size in (4, 3, 2, 1):
                for start in range(len(token_matches) - size + 1):
                    first, last = token_matches[start], token_matches[start + size - 1]
                    if any(a < last.end() and first.start() < b for a, b in occupied):
                        continue
                    window = segment[first.start():last.end()]
                    if re.fullmatch(r"\d+", window):
                        continue
                    result = resolve_relative_date(window)
                    if result and not killed(first.start()):
                        candidates.append(("window", clause_index, segment_index,
                                           offset + first.start(), order, result))
                        order += 1
            offset += len(segment) + 1

    explicit_survivors = [item for item in candidates if item[0] == "explicit"]
    if explicit_survivors:
        return max(explicit_survivors, key=lambda item: item[1:5])[5]
    bare_survivors = [item for item in candidates if item[0] == "bare"]
    if bare_survivors:
        return max(bare_survivors, key=lambda item: item[1:5])[5]
    window_survivors = [item for item in candidates if item[0] == "window"]
    if window_survivors:
        return min(window_survivors, key=lambda item: item[4])[5]
    return None


def resolve_from_conversation(messages) -> tuple:
    user_messages = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = message.get("sender", message.get("role", ""))
        if str(role or "").upper() == "USER":
            user_messages.append(message)
    if not user_messages:
        return None, None
    if all(message.get("created_at") for message in user_messages):
        chosen = max(user_messages, key=lambda message: str(message["created_at"]))
    else:
        chosen = user_messages[-1]
    latest = str(chosen.get("message", chosen.get("content", "")) or "")[:2000]
    resolved = extract_date_from_text(latest)
    return (resolved, resolved) if resolved else (None, None)


def _fetch_conversation(call_id) -> list | None:
    started = time.monotonic()
    api_key = os.environ.get("ECP_BLAND_API_KEY", "")
    if not api_key:
        return None
    # Defense-in-depth: the id is spliced into a URL path with our API key
    # attached, so only a plain conversation-id shape may pass.
    call_id = str(call_id or "")
    if (
        not re.fullmatch(r"[A-Za-z0-9-]{8,64}", call_id)
        or len(re.findall(r"[A-Za-z0-9]", call_id)) < 8
    ):
        return None
    headers = {
        "Authorization": api_key,
        "User-Agent": "mott-gateway",
    }
    urls = (
        f"https://api.bland.ai/v1/sms/conversations/{call_id}",
        f"https://api.bland.ai/v1/pathway/chat/{call_id}",
    )
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect())
    for attempt, url in enumerate(urls):
        if attempt and time.monotonic() - started > 2.5:
            return None
        try:
            request = urllib.request.Request(url, headers=headers)
            with opener.open(request, timeout=2) as response:
                payload = json.loads(response.read(524288))
            data = payload.get("data", payload) if isinstance(payload, dict) else {}
            if not isinstance(data, dict):
                continue
            messages = data.get("messages") or data.get("chat_history")
            if isinstance(messages, list) and messages:
                return messages
        except Exception:
            continue
    return None


def clamp_availability_range(body: dict) -> None:
    call_id = str(body.pop("callID", "") or "").strip()
    first_requested = str(body.get("first_available", "")).strip().lower() in (
        "1", "true", "yes",
    )
    if (
        _RAW_TEXT_DATES
        and TENANT_ID.strip().lower() == "mott"
        and call_id
        and not first_requested
    ):
        try:
            msgs = _fetch_conversation(call_id)
            if msgs:
                raw_from, raw_to = resolve_from_conversation(msgs)
                if raw_from:
                    body["from"], body["to"] = raw_from, raw_to
                    log.info("date_source=raw")
                else:
                    log.info("date_source=fallback")
        except Exception:
            log.info("date_source=error_fallback")
    # first_available=1 replaces from/to with tomorrow..+6 days (Eastern) —
    # closed days simply return no slots, so no business-day logic is needed.
    # Otherwise from/to go through resolve_relative_date; bad/inverted "to"
    # collapses to same-day; spans are capped at 14 days.
    from datetime import datetime, timedelta

    first = str(body.pop("first_available", "")).strip().lower()
    if first in ("1", "true", "yes"):
        start = _eastern_today() + timedelta(days=1)
        body["from"] = start.strftime("%m/%d/%Y")
        body["to"] = (start + timedelta(days=6)).strftime("%m/%d/%Y")
        return

    def parse(v):
        try:
            return datetime.strptime(str(v).strip(), "%m/%d/%Y")
        except ValueError:
            return None

    resolved = resolve_relative_date(body.get("from"))
    if resolved is None:
        return
    body["from"] = resolved
    frm = parse(resolved)
    to_resolved = resolve_relative_date(body.get("to"))
    to = parse(to_resolved) if to_resolved else None
    if to is None or to < frm:
        to = frm
    if (to - frm).days > 13:
        to = frm + timedelta(days=13)
    body["to"] = to.strftime("%m/%d/%Y")


def sanitize_patient_search(body: dict):
    # Identity safety (live chat-test finding 2026-07-01): an unresolved Bland
    # variable like "{{from}}" reached EyeCloud as a phone filter, EyeCloud
    # ignored it, and the search returned an unfiltered patient list; a
    # DOB-only follow-up then matched the WRONG real patient. Rules:
    #   - a phone that doesn't normalize to 10 digits is dropped
    #   - dob without last/first/phone is never searched (wrong-person risk)
    #   - if nothing usable remains, short-circuit to a clean 0-match so the
    #     pathway falls into its ask-for-last-name-and-DOB lane
    phone = str(body.get("phone", "")).strip()
    if phone and not re.fullmatch(r"\d{10}", normalize_phone(phone)):
        body.pop("phone", None)
    has = {k: str(body.get(k, "")).strip() for k in ("last", "first", "phone", "dob")}
    if has["dob"] and not (has["last"] or has["phone"]):
        body.pop("dob", None)
        has["dob"] = ""
    if not (has["last"] or has["phone"]):
        return {"count": 0, "capped": False, "patients": []}
    return None


def prepare_patient_search(body: dict, include_recall_context: bool = False):
    """Remove gateway-only campaign fields before sanitizing the CLI request.

    ``include_recall_context`` preserves the historical two-value return for
    existing internal callers while letting the HTTP flow receive the recall
    token and batch id alongside ``(short, patient_id)``.
    """
    requested_patient_id = str(body.pop("patient_id", "") or "").strip()
    patient_id = requested_patient_id if requested_patient_id and "{{" not in requested_patient_id else ""
    requested_recall_token = str(body.pop("recall_token", "") or "").strip()
    recall_token = (requested_recall_token
                    if requested_recall_token and "{{" not in requested_recall_token else "")
    requested_recall_batch_id = str(body.pop("recall_batch_id", "") or "").strip()
    recall_batch_id = (requested_recall_batch_id
                       if requested_recall_batch_id and "{{" not in requested_recall_batch_id else "")
    short = sanitize_patient_search(body) if not patient_id else None
    if include_recall_context:
        return short, patient_id, recall_token, recall_batch_id
    return short, patient_id


def resolve_recall_context(recall_token, recall_batch_id) -> str:
    """Resolve an allowlisted exam category from one campaign row, fail-open."""
    global _recall_rows_client
    recall_token = str(recall_token or "").strip()
    recall_batch_id = str(recall_batch_id or "").strip()
    table_name = os.environ.get("ECP_RECALL_ROWS_TABLE", "").strip()
    if not recall_token or not recall_batch_id or not table_name or boto3 is None:
        return ""
    try:
        if _recall_rows_client is None:
            _recall_rows_client = boto3.client("dynamodb")
        response = _recall_rows_client.get_item(
            TableName=table_name,
            Key={
                "batch_id": {"S": recall_batch_id},
                "recall_token": {"S": recall_token},
            },
        )
        item = response.get("Item", {}) if isinstance(response, dict) else {}
        attribute = item.get("exam_category", {}) if isinstance(item, dict) else {}
        category = attribute.get("S", "") if isinstance(attribute, dict) else ""
        return category if category in {"comprehensive", "contact_lens", "medical"} else ""
    except Exception:
        # Resolution is optional context; booking retains today's default behavior.
        return ""


_recall_rows_client = None


SMS_SUPPRESSION_REASONS = frozenset({"stop", "unsubscribe", "complaint", "manual"})
SMS_SUPPRESSION_SOURCES = frozenset({"sms_reply", "voice", "manual", "import"})
_sms_suppression_client = None


class SuppressionStoreError(RuntimeError):
    """A user-safe suppression-store failure suitable for an HTTP response."""


def _is_conditional_check_failure(exc: Exception) -> bool:
    response = getattr(exc, "response", {})
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    return (
        isinstance(error, dict)
        and error.get("Code") == "ConditionalCheckFailedException"
    )


def record_sms_suppression(body: dict) -> None:
    """Validate and idempotently record one SMS suppression."""
    global _sms_suppression_client

    for field in ("phone_e164", "reason", "source"):
        if field not in body:
            raise ValueError(f"{field} is required")

    phone = body["phone_e164"]
    reason = body["reason"]
    source = body["source"]
    if not isinstance(phone, str) or not re.fullmatch(r"\+[0-9]{8,15}", phone):
        raise ValueError("invalid phone_e164")
    if not isinstance(reason, str) or reason not in SMS_SUPPRESSION_REASONS:
        raise ValueError("invalid reason")
    if not isinstance(source, str) or source not in SMS_SUPPRESSION_SOURCES:
        raise ValueError("invalid source")

    table_name = os.environ.get("ECP_SMS_SUPPRESSION_TABLE", "").strip()
    if not table_name:
        raise SuppressionStoreError("suppression_store_unconfigured")
    if boto3 is None:
        raise SuppressionStoreError("suppression_store_unavailable")

    created_at = datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    try:
        if _sms_suppression_client is None:
            _sms_suppression_client = boto3.client("dynamodb")
        _sms_suppression_client.put_item(
            TableName=table_name,
            Item={
                "pk": {"S": phone},
                "reason": {"S": reason},
                "source": {"S": source},
                "created_at": {"S": created_at},
            },
            ConditionExpression="attribute_not_exists(pk)",
        )
    except Exception as exc:
        if _is_conditional_check_failure(exc):
            return
        raise SuppressionStoreError("suppression_store_unavailable") from exc


def augment_search_envelope(result, category):
    """Attach recall booking context to a patient-search result envelope."""
    if not isinstance(result, dict):
        return result
    exam_type_id = ""
    if category:
        try:
            type_map = json.loads(os.environ.get("ECP_APPT_TYPE_MAP", ""))
            if isinstance(type_map, dict):
                exam_type_id = str(type_map.get(f"{category}:existing") or "").strip()
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    if not exam_type_id:
        exam_type_id = os.environ.get("ECP_DEFAULT_APPT_TYPE", "").strip()
    if not exam_type_id:
        # CVC legacy /sign type id: a deploy without new env config books as today.
        exam_type_id = "1006896092"
    result["exam_category"] = category
    result["exam_type_id"] = exam_type_id
    return result


def build_patient_get_argv(patient_id: str) -> list[str]:
    """Build the audited direct demographic read for a campaign-pinned patient."""
    return [CLI, "appt", "patient-get", "--agent", "--reason",
            "bland-patient-get", "--patient", patient_id]


PATIENT_PROFILES = {"identity", "contact", "full_demographics"}
PATIENT_IDENTITY_FIELDS = {
    "patient_id": ("patient_id",),
    "name_first": ("name_first", "first_name", "first"),
    "name_last": ("name_last", "last_name", "last"),
    "dob": ("dob", "date_of_birth"),
    "home_store": ("home_store",),
}
PATIENT_CONTACT_FIELDS = {
    "phone_mobile": ("phone_mobile", "mobile_phone", "cell_phone", "mobile"),
    "phone_home": ("phone_home", "home_phone"),
    "phone_work": ("phone_work", "work_phone"),
    "email": ("email", "email_address"),
}
PATIENT_DEMOGRAPHIC_FIELDS = {
    "name_preferred": ("name_pref", "name_preferred", "preferred_name"),
    "name_middle": ("name_middle", "middle_name"),
    "gender": ("gender",),
    "gender_identity": ("gender_identity",),
    "address": ("home_addr_1", "address", "address1", "street"),
    "address_2": ("home_addr_2", "address_2", "address2"),
    "city": ("home_city", "city"),
    "state": ("home_state", "state"),
    "zip": ("home_zip", "zip", "zipcode", "postal_code"),
    "country": ("country",),
}


def strip_unresolved_templates(body: dict, fields) -> None:
    for field in fields:
        value = body.get(field)
        if isinstance(value, str) and re.fullmatch(r"\s*\{\{.*\}\}\s*", value):
            body.pop(field, None)


def prepare_patient_profile(body: dict) -> str:
    strip_unresolved_templates(
        body,
        {
            "patient_id", "first", "last", "phone", "dob", "profile",
            "recall_token", "recall_batch_id",
        },
    )
    profile = str(body.pop("profile", "") or "identity").strip().lower()
    if profile not in PATIENT_PROFILES:
        raise ValueError("unknown patient profile")
    return profile


def _first_value(record: dict, aliases) -> str:
    for alias in aliases:
        value = record.get(alias)
        if value not in (None, ""):
            return str(value)
    return ""


def project_patient(result: dict, profile: str) -> dict:
    fields = result.get("fields") if isinstance(result.get("fields"), dict) else {}
    source = {**result, **fields}
    output = {}
    selected = dict(PATIENT_IDENTITY_FIELDS)
    if profile in {"contact", "full_demographics"}:
        selected.update(PATIENT_CONTACT_FIELDS)
    if profile == "full_demographics":
        selected.update(PATIENT_DEMOGRAPHIC_FIELDS)
    for target, aliases in selected.items():
        output[target] = _first_value(source, aliases)
    if not output["home_store"]:
        output["home_store"] = STORE_ID_NAMES.get(
            str(result.get("store_id") or fields.get("store_id") or ""),
            "",
        )
    return output


def patient_get_envelope(result, profile: str = "identity"):
    """Adapt a direct patient-get record to the stable patient-search envelope.

    The live CLI returns demographics nested under ``fields`` plus a top-level
    ``store_id``; search records are flat. Flatten to the search-record shape
    (PHI-minimal: only the fields a search record already exposes, plus
    home_store) so pathway variable extraction is uniform across both paths.
    """
    if not isinstance(result, dict) or not result:
        return {"count": 0, "capped": False, "patients": []}
    return {"count": 1, "capped": False, "patients": [project_patient(result, profile)]}


def finalize_patient_search_envelope(result: dict, query_mode: str, profile: str) -> dict:
    result["query_mode"] = query_mode
    result["profile"] = profile
    result["sensitive_withheld"] = ["ssn"]
    return result


def authed(headers) -> bool:
    auth = headers.get("Authorization", "")
    return bool(API_KEY) and auth.startswith("Bearer ") and hmac.compare_digest(auth[7:].strip(), API_KEY)


class ConsumerResolution(NamedTuple):
    consumer: dict | None
    outcome: str


def resolve_consumer(headers, method: str, path: str) -> ConsumerResolution:
    """Resolve a deployment-bound consumer solely from its bearer token."""
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return ConsumerResolution(None, "unknown_token")
    presented_token = auth[7:].strip()
    matched = None
    for record in CONSUMER_CREDENTIALS:
        if hmac.compare_digest(presented_token, record["token"]):
            matched = record
            break
    if matched is None:
        return ConsumerResolution(None, "unknown_token")
    if matched["tenant"] != TENANT_ID or matched["principal"] != READ_PRINCIPAL:
        return ConsumerResolution(matched, "unknown_token")
    if not matched["enabled"]:
        return ConsumerResolution(matched, "disabled")
    route = f"{method.upper()} {path}"
    wildcard_all = matched["routes"][-1:] == ["*"]
    if not wildcard_all and route not in matched["routes"]:
        return ConsumerResolution(matched, "forbidden_scope")
    return ConsumerResolution(matched, "ok")


def resolve_request_auth(headers, method: str, path: str) -> ConsumerResolution:
    """Resolve consumer auth, falling back to the legacy bearer only when safe."""
    resolution = resolve_consumer(headers, method, path)
    if resolution.outcome == "ok":
        return resolution
    if (
        resolution.consumer is None
        and resolution.outcome == "unknown_token"
        and not CONSUMER_CREDENTIALS_LOAD_FAILED
        and CONSUMER_ACCEPT_LEGACY
        and authed(headers)
    ):
        return ConsumerResolution(None, "ok")
    return resolution


def resolve_query_credential(headers) -> dict:
    """Return only identity cryptographically bound to the presented token."""
    record = QUERY_CREDENTIAL
    auth = headers.get("Authorization", "")
    if (
        not record
        or not auth.startswith("Bearer ")
        or not hmac.compare_digest(auth[7:].strip(), record["token"])
        or record["tenant"] != TENANT_ID
        or record["principal"] != READ_PRINCIPAL
    ):
        return {}
    return {"tenant": record["tenant"], "principal": record["principal"]}


def query_audit(
    request_id: str,
    tenant: str,
    principal: str,
    operation: str,
    status: int,
    duration_ms: int,
    count: int,
) -> None:
    """Emit exactly one payload-free metadata record for each /query request."""
    log.info(
        "query_audit %s",
        json.dumps(
            {
                "request_id": request_id,
                "tenant": tenant,
                "principal": principal,
                "operation": operation,
                "status": status,
                "duration_ms": duration_ms,
                "count": count,
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
    )


# --- Callback message delivery (voicemail-to-email) ------------------------------
# The pathway's "Leave a message" lane POSTs the captured message here; we email it
# to the practice inbox via SES (AWS BAA, no third party). The message may contain
# PHI, so it is NEVER written to logs — only a length + store + delivery status.
CALLBACK_INBOX = os.environ.get("CVC_CALLBACK_INBOX", "").strip()
CALLBACK_FROM = os.environ.get("CVC_CALLBACK_FROM", "noreply@mybcat.com").strip()
CALLBACK_REGION = os.environ.get("CVC_CALLBACK_SES_REGION", os.environ.get("AWS_REGION", "us-east-1")).strip()
# Optional Google Chat delivery (in ADDITION to email). Empty = skipped.
CALLBACK_GCHAT_WEBHOOK = os.environ.get("CVC_CALLBACK_GCHAT_WEBHOOK", "").strip()
_ses_client = None
_sns_client = None
# PHI-minimal SMS ping for urgent alerts. Constant only: never interpolate
# caller name, phone, or symptoms into this text (PHI stays on the secure channel).
SMS_PING = "Urgent eye emergency call - check the channel"
CVC_ALERT_SMS_TO = os.environ.get("CVC_ALERT_SMS_TO", "").strip()


def post_google_chat(text: str) -> bool:
    """Post a plain-text card to the configured Google Chat webhook. Returns True
    on success, False on any failure (delivery must never break email). The
    message text is NOT logged."""
    if not CALLBACK_GCHAT_WEBHOOK:
        return False
    import urllib.request
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(CALLBACK_GCHAT_WEBHOOK, data=payload, method="POST",
                                 headers={"Content-Type": "application/json; charset=UTF-8"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception:
        log.warning("google chat delivery failed (email path unaffected)")
        return False


def _ses():
    global _ses_client
    if _ses_client is None:
        import boto3  # lazy so the shim still imports where boto3 is absent
        _ses_client = boto3.client("sesv2", region_name=CALLBACK_REGION)
    return _ses_client


def _sns():
    global _sns_client
    if _sns_client is None:
        import boto3  # lazy; SNS only touched on urgent alerts when enabled
        _sns_client = boto3.client("sns", region_name=CALLBACK_REGION)
    return _sns_client


def deliver_message(body: dict) -> dict:
    """Email a captured callback message to the practice inbox. Raises on refusal
    (400/503-worthy) so do_POST maps it to a status. No PHI is logged here."""
    if not CALLBACK_INBOX:
        raise RuntimeError("callback delivery not configured")

    def clean(v, limit):
        # Drop unresolved Bland template placeholders ("{{store}}") so they never
        # appear literally in a staff email.
        s = str(v or "").strip()
        if re.fullmatch(r"\{\{.*\}\}", s):
            s = ""
        return s[:limit]

    msg = clean(body.get("message"), 4000)
    if not msg:
        raise ValueError("message is required")
    if len(str(body.get("message", "")).strip()) > 4000:
        msg = msg[:4000] + " [truncated]"
    store = clean(body.get("store"), 40) or "unspecified office"
    caller = clean(body.get("caller_name"), 120)
    callback = clean(body.get("callback_phone"), 40)
    intent = clean(body.get("intent"), 120)
    kind = clean(body.get("kind"), 32)
    issue = clean(body.get("issue"), 200)
    is_urgent = kind == "urgent_alert"
    about = issue or intent
    if is_urgent:
        header = "*** URGENT EYE EMERGENCY - caller triaged as needs-to-be-seen-fast ***"
        subject = f"URGENT EYE EMERGENCY - {store} - callback needed"
    else:
        header = "A caller left a message with the Classic Vision Care voice assistant."
        subject = f"CVC callback request - {store}"
    # Structured, plain-text body. SES 'to' is a CVC-owned inbox (BAA path).
    # PHI (name / phone / issue) rides ONLY this secure channel (SES + Google Chat).
    lines = [
        header,
        "",
        f"Office: {store}",
        f"Caller name (as given): {caller or '(not provided)'}",
        f"Callback number: {callback or '(not provided)'}",
        f"About: {about or '(not specified)'}",
        "",
        "Message:",
        msg,
        "",
        "-- Sent automatically by the CVC booking assistant. Reply is not monitored.",
    ]
    body_text = "\n".join(lines)
    resp = _ses().send_email(
        FromEmailAddress=CALLBACK_FROM,
        Destination={"ToAddresses": [CALLBACK_INBOX]},
        Content={"Simple": {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
        }},
    )
    gchat = post_google_chat(f"*{subject}*\n{body_text}")
    sms = "n/a"
    if is_urgent:
        sms = "skipped"
        # The alert fires before the pathway's hours check, so the gateway resolves
        # office state itself (deterministic) to route the ping: front desk when
        # open, on-call doctor after hours.
        state = "after_hours"
        try:
            state = hours_state(store, datetime.now(ZoneInfo("America/New_York")))["state"]
        except Exception:
            pass
        recipients = alert_sms_recipients(state)
        if os.environ.get("CVC_ALERT_SMS_ENABLED") == "1" and recipients:
            try:
                # PHI-free: only the constant SMS_PING is ever published.
                for num in recipients:
                    _sns().publish(PhoneNumber=num, Message=SMS_PING)
                sms = "sent"
            except Exception:
                log.warning("urgent SMS ping failed (secure-channel alert unaffected)")
                sms = "failed"
    return {"ok": True, "delivered": True, "email": True, "google_chat": gchat,
            "sms": sms, "message_id": resp.get("MessageId", "")}


def build_argv(path: str, body: dict) -> tuple[list[str], bool]:
    verb, flagmap, is_write = ENDPOINTS[path]
    if path == "/availability":
        clamp_availability_range(body)
    argv = [CLI, "appt", verb, "--agent", "--reason", f"bland-{verb}"]
    pref = str(body.pop("time_pref", "")).strip().lower()
    for flag, val in TIME_PREFS.get(pref, []):
        argv += [flag, val]
    # Force the store's real provider (ignore any caller-supplied doctor) so only
    # Bhumi@Kennesaw / Mital@East Cobb slots are ever offered or booked.
    forced_doctor = STORE_DOCTORS.get(str(body.get("store", "")).strip().lower()) if "doctor" in flagmap else None
    if forced_doctor:
        body.pop("doctor", None)
    allow_conflict = body.pop("allow_conflict", None) if path == "/book" else None
    status = body.pop("status", None) if path == "/book" else None
    category = body.pop("category", None) if path in ("/book", "/book-new-patient") else None
    # Reschedule resolves the target patient's id inside the CLI.  The gateway
    # accepts an optional already-resolved id solely to open the CLI's per-call
    # test-patient firebreak; it must never become a CLI flag.
    firebreak_patient_id = body.pop("patient_id", None) if path == "/reschedule" else None
    if firebreak_patient_id is not None and not re.fullmatch(r"\d+", str(firebreak_patient_id).strip()):
        raise ValueError("field 'patient_id' must be numeric")
    if status is not None:
        status = str(status).strip().lower()
        if not status or "{{" in status:
            status = None
        elif status not in {"existing", "new"}:
            raise ValueError("unknown status")
    if category is not None:
        category = str(category).strip().lower()
        if not category or "{{" in category:
            category = None
    if category is not None:
        if category not in {"comprehensive", "contact_lens", "medical"}:
            raise ValueError("unknown category")
        raw_type_map = os.environ.get("ECP_APPT_TYPE_MAP", "")
        if raw_type_map:
            type_map = json.loads(raw_type_map)
            if not isinstance(type_map, dict):
                raise ValueError("ECP_APPT_TYPE_MAP must be a JSON object")
            status_final = status or ("existing" if path == "/book" else "new")
            mapped_type = type_map.get(f"{category}:{status_final}")
            if mapped_type is not None:
                body["type"] = mapped_type
    if isinstance(allow_conflict, str):
        allow_conflict = allow_conflict.strip().lower() in ("true", "1", "yes")
    if allow_conflict:
        # Owner-gated double-book. Reachable only from the URGENT lane; the server
        # refuses it unless the operator has explicitly enabled it via env.
        if os.environ.get("ECP_ALLOW_CONFLICT_ENABLED") != "1":
            raise PermissionError("allow_conflict is not enabled")
        argv.append("--allow-conflict")
    for key, val in body.items():
        if key == "confirm":
            continue
        if key not in flagmap:
            raise ValueError(f"unknown field {key!r} for {path}")
        if key == "include_past":
            if not isinstance(val, bool):
                raise ValueError("field 'include_past' must be a boolean")
            if val:
                argv.append(flagmap[key])
            continue
        if not isinstance(val, (str, int)):
            raise ValueError(f"field {key!r} must be a string")
        sval = normalize_phone(val) if key == "phone" else str(val).strip()
        if key in ("start", "end"):
            sval = normalize_sched_time(sval)
        if not sval:
            continue
        if len(sval) > MAX_VALUE_LEN or sval.startswith("-"):
            raise ValueError(f"field {key!r} has an invalid value")
        argv += [flagmap[key], sval]
    if forced_doctor:
        argv += ["--doctor", forced_doctor]
    # Strict: only a JSON boolean true triggers a write. A string like "false"
    # is truthy in Python and would otherwise fire an unintended booking.
    confirm = (body.get("confirm") is True) and is_write
    if confirm:
        argv.append("--confirm")
        if Path(AWS_ENV_WRAPPER).exists():
            argv = [AWS_ENV_WRAPPER, "--"] + argv
    return argv, confirm


def check_test_mode(path: str, body: dict) -> None:
    if not TEST_MODE:
        return
    # Booking EXISTING patients is open to all patients (owner decision
    # 2026-07-01): the ZZTEST-only allowlist on /book is lifted here and the CLI
    # firebreak is opened per-call in do_POST. New-patient CREATION stays gated to
    # the ZZTEST last-name prefix below.
    if path == "/book-new-patient":
        last = str(body.get("last", "")).replace(" ", "").strip().upper()
        if not last.startswith(TEST_LAST_PREFIX):
            raise PermissionError(f"test mode: new-patient last name must start with {TEST_LAST_PREFIX}")


def availability_envelope(result):
    slots = result if isinstance(result, list) else []
    first = slots[0] if slots else {}
    return {
        "count": len(slots),
        "first_start": str(first.get("start", "")),
        "first_end": str(first.get("end", "")),
        "first_doctor": str(first.get("doctor_id", "")),
        "slots": slots,
    }


def filter_test_mode(path: str, result):
    if not TEST_MODE or path != "/patient-search" or not isinstance(result, dict):
        return result
    pts = [
        p
        for p in result.get("patients", [])
        if str(p.get("name_last", "")).upper().startswith(TEST_LAST_PREFIX)
    ]
    return {"count": len(pts), "capped": False, "patients": pts, "test_mode": True}


def cli_json_result(proc):
    out = proc.stdout.strip()
    try:
        return json.loads(out) if out else None
    except json.JSONDecodeError:
        return None


def patient_search_is_empty(result) -> bool:
    if not isinstance(result, dict):
        return False
    try:
        return int(result.get("count", len(result.get("patients", [])))) == 0
    except (TypeError, ValueError):
        return not result.get("patients")


class _SessionRWLock:
    """Allow concurrent CLI calls while making session logins exclusive."""

    def __init__(self):
        self._condition = threading.Condition()
        self._readers = 0
        self._writer = False
        self._waiting_writers = 0

    @contextmanager
    def cli_call(self, deadline: float | None = None):
        with self._condition:
            while self._writer or self._waiting_writers:
                if deadline is None:
                    self._condition.wait()
                else:
                    self._condition.wait(timeout=_remaining_timeout(deadline))
            self._readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._readers -= 1
                if not self._readers:
                    self._condition.notify_all()

    @contextmanager
    def login(self, deadline: float | None = None):
        with self._condition:
            self._waiting_writers += 1
            try:
                while self._writer or self._readers:
                    if deadline is None:
                        self._condition.wait()
                    else:
                        self._condition.wait(timeout=_remaining_timeout(deadline))
                self._writer = True
            finally:
                self._waiting_writers -= 1
        try:
            yield
        finally:
            with self._condition:
                self._writer = False
                self._condition.notify_all()


# Any in-process session warmer must use SESSION_LOCK.login() around auth login.
SESSION_LOCK = _SessionRWLock()
_RELOGIN_TS = 0.0
_RELOGIN_COOLDOWN_S = 30
_DEAD_SESSION_RE = re.compile(r"egweb\.\S* returned HTTP 404")
_SESSION_LOCK_FILE_DEFAULT = "/tmp/eyecloud-session.lock"
_SESSION_LOCK_TIMEOUT_S_DEFAULT = 60.0


@contextmanager
def _session_file_lock(exclusive: bool = False, deadline: float | None = None):
    """Take the cross-process session lock, degrading open on failure/timeout."""
    lock_path = os.environ.get("ECP_SESSION_LOCK_FILE", _SESSION_LOCK_FILE_DEFAULT)
    try:
        lock_file = open(lock_path, "a+")
    except OSError as exc:
        log.warning("session flock unavailable path=%s error=%s; proceeding unlocked",
                    lock_path, exc)
        yield
        return

    acquired = False
    operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    try:
        try:
            timeout_s = max(
                0.0,
                float(os.environ.get(
                    "ECP_SESSION_LOCK_TIMEOUT_S",
                    str(_SESSION_LOCK_TIMEOUT_S_DEFAULT),
                )),
            )
        except ValueError:
            timeout_s = _SESSION_LOCK_TIMEOUT_S_DEFAULT
        lock_deadline = (
            time.monotonic() + timeout_s if deadline is None else deadline
        )
        while True:
            try:
                fcntl.flock(lock_file.fileno(), operation | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    log.warning(
                        "session flock unavailable path=%s error=%s; proceeding unlocked",
                        lock_path, exc,
                    )
                    break
                if time.monotonic() >= lock_deadline:
                    if deadline is not None:
                        raise subprocess.TimeoutExpired("eyecloud-cli", timeout_s)
                    log.warning(
                        "session flock wait timed out after %.1fs path=%s mode=%s; "
                        "proceeding unlocked",
                        timeout_s, lock_path, "exclusive" if exclusive else "shared",
                    )
                    break
                remaining = lock_deadline - time.monotonic()
                if remaining <= 0:
                    if deadline is not None:
                        raise subprocess.TimeoutExpired("eyecloud-cli", timeout_s)
                    break
                time.sleep(min(0.05, remaining))
        yield
    finally:
        if acquired:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError as exc:
                log.warning("session flock release failed path=%s error=%s",
                            lock_path, exc)
        lock_file.close()


def _dead_session(proc) -> bool:
    return proc.returncode != 0 and bool(_DEAD_SESSION_RE.search(proc.stderr or ""))


def _remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired("eyecloud-cli", 0)
    return remaining


def _relogin(
    env: dict,
    force: bool = False,
    deadline: float | None = None,
) -> bool:
    # One login at a time with a cooldown: EyeCloud keeps a single session per
    # user, so stampeding logins from concurrent requests would kill each
    # other's sessions — the very failure this recovers from.
    global _RELOGIN_TS
    with SESSION_LOCK.login(deadline=deadline):
        with _session_file_lock(exclusive=True, deadline=deadline):
            if not force and time.monotonic() - _RELOGIN_TS < _RELOGIN_COOLDOWN_S:
                return True
            argv = [CLI, "auth", "login", "--headless",
                    "--store-id", os.environ.get("ECP_STORE_ID", "956"),
                    "--agent", "--no-input", "--yes", "--reason", "bland-gateway-relogin"]
            timeout = 120 if deadline is None else _remaining_timeout(deadline)
            try:
                proc = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                if deadline is not None:
                    raise
                log.warning("on-demand relogin timed out after 120s")
                return False
            _RELOGIN_TS = time.monotonic()
            if proc.returncode == 0:
                log.info("on-demand relogin ok")
                return True
            log.warning("on-demand relogin failed rc=%s", proc.returncode)
            return False


def run_cli(
    argv: list,
    env: dict,
    timeout_s: float | None = None,
    deadline: float | None = None,
):
    # subprocess.run plus two bounded self-heals: the fixed !egweb-404 stderr
    # signature marks a dead session. The final rung forces a fresh login rather
    # than accepting the relogin cooldown. Writes are safe to retry: a
    # dead-session refusal happens before anything is written, and /book keeps
    # its read-after-write proof regardless. Arbitrary nonzero exits never retry.
    explicitly_timed = deadline is not None or timeout_s is not None
    if deadline is None and timeout_s is not None:
        deadline = time.monotonic() + timeout_s
    for attempt in range(1, 4):
        with SESSION_LOCK.cli_call(deadline=deadline):
            with _session_file_lock(deadline=deadline):
                proc = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_S if deadline is None else _remaining_timeout(deadline),
                    env=env,
                )
        if not _dead_session(proc) or attempt == 3:
            return proc
        force = attempt == 2
        if explicitly_timed:
            relogged = _relogin(env, force=force, deadline=deadline)
        else:
            relogged = _relogin(env, force=force)
        if not relogged:
            return proc
        if force:
            log.info("retrying CLI call after forced relogin (attempt 3/3)")
        else:
            log.info("retrying CLI call after relogin (attempt 2/3)")
    return proc


def run_patient_search(search_body: dict, env: dict):
    """Run patient-search and retry once without internal last-name spaces."""
    argv, _ = build_argv("/patient-search", dict(search_body))
    proc = run_cli(argv, env)
    result = cli_json_result(proc)
    last = str(search_body.get("last", ""))
    retried = False
    if proc.returncode == 0 and patient_search_is_empty(result) and re.search(r"\s", last):
        retry_body = dict(search_body)
        retry_body["last"] = re.sub(r"\s+", "", last)
        retry_argv, _ = build_argv("/patient-search", retry_body)
        retry_proc = run_cli(retry_argv, env)
        retried = True
        if retry_proc.returncode == 0:
            proc, result = retry_proc, cli_json_result(retry_proc)
    return proc, result, retried


def appointment_items(result) -> list:
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and isinstance(result.get("appointments"), list):
        return result["appointments"]
    return []


APPOINTMENT_METADATA_FIELDS = {
    "capped",
    "has_more",
    "next_cursor",
    "total",
    "total_count",
    "from",
    "to",
    "store",
    "include_past",
}


def appointment_metadata(result) -> dict:
    if not isinstance(result, dict):
        return {}
    return {
        key: result[key]
        for key in APPOINTMENT_METADATA_FIELDS
        if key in result and isinstance(result[key], (str, int, bool, type(None)))
    }


def normalized_appointment_result(result) -> dict:
    appointments = appointment_items(result)
    appointments.sort(key=appointment_start_key)
    return {
        **appointment_metadata(result),
        "count": len(appointments),
        "appointments": appointments,
    }


def appointment_start_key(appointment):
    start = str(appointment.get("start", "")) if isinstance(appointment, dict) else ""
    for fmt in ("%m/%d/%Y %I:%M %p", "%Y-%m-%dT%H:%M:%S"):
        try:
            return (0, datetime.strptime(start.strip().lower(), fmt))
        except ValueError:
            pass
    return (1, start)


class Handler(BaseHTTPRequestHandler):
    server_version = "cvc-booking-gateway/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, status: int, payload: dict | None = None):
        data = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if data:
            self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._send(
                200,
                {
                    "ok": True,
                    "test_mode": TEST_MODE,
                    "consumer_set_loaded": bool(CONSUMER_CREDENTIALS),
                    "enabled_consumer_count": sum(
                        1 for consumer in CONSUMER_CREDENTIALS if consumer["enabled"]
                    ),
                    "consumer_accept_legacy": CONSUMER_ACCEPT_LEGACY,
                    "consumer_load_failed": CONSUMER_CREDENTIALS_LOAD_FAILED,
                },
            )
        if self.path == "/_auth":
            resolution = resolve_request_auth(self.headers, "GET", self.path)
            if resolution.outcome == "forbidden_scope":
                return self._send(403, {"error": "forbidden_scope"})
            return self._send(204 if resolution.outcome == "ok" else 401)
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        t0 = time.monotonic()
        status = 500
        query_request_id = secrets.token_hex(12) if self.path == "/query" else ""
        query_identity = {}
        query_operation = ""
        query_count = 0
        try:
            if self.path not in (
                "/message",
                "/hours-state",
                "/urgent-availability",
                "/sms-suppression",
                "/query",
            ) and self.path not in ENDPOINTS:
                status = 404
                return self._send(status, {"error": "not found"})
            if self.path == "/query":
                query_identity = resolve_query_credential(self.headers)
                if not query_identity:
                    status = 401
                    return self._send(status, {"ok": False, "error": "query_identity_unbound"})
                if ECP_QUERY_RELEASE_GATE != "SYNTHETIC_TEST_ONLY":
                    status = 403
                    return self._send(status, {"ok": False, "error": "query_release_blocked"})
            else:
                resolution = resolve_request_auth(self.headers, "POST", self.path)
                if resolution.outcome == "forbidden_scope":
                    status = 403
                    return self._send(status, {"error": "forbidden_scope"})
                if resolution.outcome != "ok":
                    status = 401
                    return self._send(status, {"error": "unauthorized"})
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY:
                status = 413
                return self._send(status, {"error": "body too large"})
            if self.path == "/hours-state":
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(body, dict):
                        raise ValueError("body must be a JSON object")
                    now = datetime.now(ZoneInfo("America/New_York"))
                    result = hours_state(str(body.get("store", "")), now)
                    status = 200
                    return self._send(status, {"ok": True, **result})
                except ValueError as exc:
                    status = 400
                    return self._send(status, {"ok": False, "error": str(exc)})
            if self.path == "/urgent-availability":
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(body, dict):
                        raise ValueError("body must be a JSON object")
                    store = str(body.get("store", ""))
                    now = datetime.now(ZoneInfo("America/New_York"))
                    uw = urgent_window(store, str(body.get("slot_mode", "")), now)
                    doctor = STORE_DOCTORS.get(store.strip().lower(), "")
                    argv = [CLI, "appt", "availability", "--agent", "--reason",
                            "bland-urgent-avail", "--store", store,
                            "--from", uw["avail_from"], "--to", uw["avail_to"],
                            "--slot-minutes", "30"]
                    if doctor:
                        argv += ["--doctor", doctor]
                    env = dict(os.environ)
                    proxy = os.environ.get("ECP_EYECLOUD_PROXY", "")
                    if proxy:
                        npx = os.environ.get(
                            "ECP_EYECLOUD_NO_PROXY",
                            "169.254.169.254,169.254.170.2,.amazonaws.com,localhost,127.0.0.1")
                        env.update({"HTTPS_PROXY": proxy, "HTTP_PROXY": proxy,
                                    "NO_PROXY": npx, "no_proxy": npx})
                    try:
                        proc = run_cli(argv, env)
                        raw = (json.loads(proc.stdout.strip())
                               if proc.returncode == 0 and proc.stdout.strip() else [])
                    except Exception:
                        raw = []
                    env_res = availability_envelope(raw)
                    if env_res["count"] >= 1:
                        res = {"count": env_res["count"], "slot_start": env_res["first_start"],
                               "slot_end": env_res["first_end"],
                               "slot_doctor": env_res["first_doctor"] or doctor,
                               "double_book": False, "slot_mode": uw["mode"]}
                    else:
                        # No open slot in the window -> emergency double-book target.
                        res = {"count": 0, "slot_start": uw["book_start"],
                               "slot_end": uw["book_end"], "slot_doctor": doctor,
                               "double_book": True, "slot_mode": uw["mode"]}
                    status = 200
                    return self._send(status, {"ok": True, "result": res})
                except ValueError as exc:
                    status = 400
                    return self._send(status, {"ok": False, "error": str(exc)})
            if self.path == "/message":
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(body, dict):
                        raise ValueError("body must be a JSON object")
                    result = deliver_message(body)
                    status = 200
                    log.info("message delivered store=%s len=%d",
                             str(body.get("store", ""))[:40], len(str(body.get("message", ""))))
                    return self._send(status, result)
                except ValueError as exc:
                    status = 400
                    return self._send(status, {"ok": False, "error": str(exc)})
                except Exception:  # SES failure / not configured: do not leak detail
                    status = 503
                    log.error("message delivery failed (see SES); body not logged")
                    return self._send(status, {"ok": False, "error": "delivery_failed"})
            if self.path == "/sms-suppression":
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(body, dict):
                        raise ValueError("body must be a JSON object")
                    record_sms_suppression(body)
                    status = 200
                    log.info("sms suppression accepted phone=***%s", body["phone_e164"][-4:])
                    return self._send(status, {"ok": True})
                except ValueError as exc:
                    status = 400
                    return self._send(status, {"ok": False, "error": str(exc)})
                except SuppressionStoreError as exc:
                    status = 503
                    log.error("sms suppression store failed; request body not logged")
                    return self._send(status, {"ok": False, "error": str(exc)})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("body must be a JSON object")
                if self.path == "/query":
                    requested_operation = body.get("operation")
                    query_operation = (
                        requested_operation
                        if isinstance(requested_operation, str)
                        and requested_operation in CAPABILITY_MANIFEST.get("operations", {})
                        else "unknown"
                    )
                check_test_mode(self.path, body)
                cli_body = dict(body)
                appt_list_identity_search = False
                pinned_patient_id = ""
                recall_category = ""
                patient_profile = "identity"
                patient_query_mode = "demographic"
                query_prepared = None
                if self.path == "/patient-search":
                    patient_profile = prepare_patient_profile(cli_body)
                    short, pinned_patient_id, recall_token, recall_batch_id = prepare_patient_search(
                        cli_body, include_recall_context=True
                    )
                    if pinned_patient_id and not re.fullmatch(r"\d+", pinned_patient_id):
                        raise ValueError("patient_id must be numeric")
                    if pinned_patient_id:
                        patient_query_mode = "patient_id"
                        if TEST_MODE and pinned_patient_id not in TEST_PATIENT_IDS:
                            raise PermissionError("test mode: patient_id is not allowlisted")
                    recall_category = resolve_recall_context(recall_token, recall_batch_id)
                    if short is not None:
                        log.info("patient-search short-circuit: no usable identity filters")
                        status = 200
                        result = augment_search_envelope(short, recall_category)
                        result = finalize_patient_search_envelope(
                            result, patient_query_mode, "identity"
                        )
                        return self._send(status, {"ok": True, "result": result})
                if self.path == "/appt-list":
                    patient_id = str(cli_body.get("patient_id", "")).strip()
                    if patient_id:
                        if not re.fullmatch(r"\d+", patient_id):
                            # Keep the resolved-patient path's identity safety unchanged.
                            status = 400
                            return self._send(status, {"error": "patient_id (numeric) is required"})
                    else:
                        if not (str(cli_body.get("last", "")).strip() and str(cli_body.get("dob", "")).strip()):
                            status = 400
                            return self._send(status, {"error": "patient_id (numeric) or last+dob are required"})
                        appt_list_identity_search = True
                if self.path == "/query":
                    query_prepared = prepare_query(
                        body,
                        cli=CLI,
                        principal=query_identity["principal"],
                        tenant=query_identity["tenant"],
                        release_gate=ECP_QUERY_RELEASE_GATE,
                        cursor_secret=API_KEY,
                        manifest=CAPABILITY_MANIFEST,
                    )
                    query_operation = query_prepared["operation_id"]
                    argv, confirm = query_prepared["argv"], False
                elif self.path == "/patient-search" and pinned_patient_id:
                    argv, confirm = build_patient_get_argv(pinned_patient_id), False
                elif not appt_list_identity_search:
                    argv, confirm = build_argv(self.path, cli_body)
                else:
                    confirm = False
            except QueryError as exc:
                log.info("query refused code=%s", exc.code)
                status = exc.status
                return self._send(status, {"ok": False, "error": exc.code})
            except PermissionError as exc:
                log.info("refused 403: %s", exc)
                status = 403
                return self._send(status, {"error": str(exc)})
            except (ValueError, json.JSONDecodeError) as exc:
                log.info("rejected 400: %s", exc)
                status = 400
                return self._send(status, {"error": str(exc)})

            env = dict(os.environ)
            # Route ONLY the EyeCloud CLI's EyeCloud HTTPS through the trusted office
            # exit node (PerimeterX blocks raw AWS IPs). Everything AWS must stay
            # DIRECT: the Fargate task-role creds served from the link-local metadata
            # endpoint (169.254.170.2) and all *.amazonaws.com calls (audit WORM ->
            # DynamoDB/Lambda/S3, KMS, STS/Secrets via the eyecloud-pro-aws-env
            # wrapper on writes). Without NO_PROXY those would tunnel through the exit
            # node and credential resolution / audit writes break.
            eyecloud_proxy = os.environ.get("ECP_EYECLOUD_PROXY", "")
            if eyecloud_proxy:
                no_proxy = os.environ.get(
                    "ECP_EYECLOUD_NO_PROXY",
                    "169.254.169.254,169.254.170.2,.amazonaws.com,localhost,127.0.0.1",
                )
                env["HTTPS_PROXY"] = eyecloud_proxy
                env["HTTP_PROXY"] = eyecloud_proxy
                env["NO_PROXY"] = no_proxy
                env["no_proxy"] = no_proxy
            if confirm and os.environ.get("ECP_CONFIRM_AWS_PROFILE"):
                env["AWS_PROFILE"] = os.environ["ECP_CONFIRM_AWS_PROFILE"]
            # Open the CLI test-patient firebreak only for the existing patient
            # resolved by this request.  /reschedule receives that optional id from
            # the preceding appointment-lookup lane and never sends it to the CLI.
            book_pid = ""
            if self.path in ("/book", "/reschedule"):
                firebreak_pid = str(body.get("patient_id", "")).strip()
                if firebreak_pid:
                    env["EYECLOUD_PRO_APPT_TEST_PATIENTS"] = firebreak_pid
                if self.path == "/book":
                    book_pid = firebreak_pid
            if appt_list_identity_search:
                try:
                    search_proc, search_result, retried = run_patient_search(
                        {"last": cli_body["last"], "dob": cli_body["dob"]}, env
                    )
                except subprocess.TimeoutExpired:
                    status = 504
                    return self._send(status, {"error": "cli timeout"})
                if search_proc.returncode != 0:
                    status = 409
                    return self._send(
                        status,
                        {"ok": False, "error": "upstream_refused"},
                    )
                search_result = filter_test_mode("/patient-search", search_result)
                patients = search_result.get("patients", []) if isinstance(search_result, dict) else []
                capped_records = len(patients) > 5
                appointments = []
                records_checked = 0
                source_metadata = []
                try:
                    for patient in patients[:5]:
                        patient_id = str(patient.get("patient_id", "")).strip() if isinstance(patient, dict) else ""
                        if not re.fullmatch(r"\d+", patient_id):
                            continue
                        list_body = {
                            key: cli_body[key]
                            for key in ("store", "from", "to", "include_past")
                            if key in cli_body
                        }
                        list_body["patient_id"] = patient_id
                        list_argv, _ = build_argv("/appt-list", list_body)
                        list_proc = run_cli(list_argv, env)
                        records_checked += 1
                        if list_proc.returncode != 0:
                            status = 409
                            return self._send(
                                status,
                                {"ok": False, "error": "upstream_refused"},
                            )
                        list_result = cli_json_result(list_proc)
                        appointments.extend(appointment_items(list_result))
                        metadata = appointment_metadata(list_result)
                        if metadata:
                            source_metadata.append(metadata)
                except subprocess.TimeoutExpired:
                    status = 504
                    return self._send(status, {"error": "cli timeout"})
                appointments.sort(key=appointment_start_key)
                result = {
                    "count": len(appointments),
                    "appointments": appointments,
                    "records_checked": records_checked,
                    "source_metadata": source_metadata,
                }
                if capped_records:
                    result["capped_records"] = True
                if retried:
                    result["retried_without_spaces"] = True
                status = 200
                return self._send(status, {"ok": True, "result": result})
            try:
                if self.path == "/patient-search" and pinned_patient_id:
                    proc = run_cli(
                        argv,
                        env,
                        timeout_s=(
                            query_prepared["timeout_s"]
                            if self.path == "/query"
                            else None
                        ),
                    )
                    result = cli_json_result(proc)
                    retried = False
                elif self.path == "/patient-search":
                    proc, result, retried = run_patient_search(cli_body, env)
                else:
                    proc = run_cli(
                        argv,
                        env,
                        timeout_s=(
                            query_prepared["timeout_s"]
                            if self.path == "/query"
                            else None
                        ),
                    )
                    result = cli_json_result(proc)
                    retried = False
            except subprocess.TimeoutExpired:
                if self.path == "/patient-search" and pinned_patient_id:
                    status = 200
                    empty = augment_search_envelope(
                        patient_get_envelope(None, patient_profile), recall_category
                    )
                    empty = finalize_patient_search_envelope(
                        empty, patient_query_mode, patient_profile
                    )
                    return self._send(status, {"ok": True, "result": empty})
                if self.path == "/query":
                    status = 504
                    return self._send(status, {"ok": False, "error": "upstream_timeout"})
                status = 504
                return self._send(status, {"error": "cli timeout"})

            if proc.returncode == 0:
                if self.path == "/query":
                    try:
                        response = render_query_result(query_prepared, result, API_KEY)
                    except QueryError as exc:
                        status = exc.status
                        return self._send(status, {"ok": False, "error": exc.code})
                    query_count = response["meta"]["count"]
                    status = 200
                    return self._send(status, response)
                if self.path == "/patient-search" and pinned_patient_id:
                    result = patient_get_envelope(result, patient_profile)
                else:
                    authoritative_count = (
                        int(result.get("count", len(result.get("patients", []))))
                        if self.path == "/patient-search" and isinstance(result, dict)
                        else 0
                    )
                    authoritative_capped = (
                        bool(result.get("capped"))
                        if self.path == "/patient-search" and isinstance(result, dict)
                        else False
                    )
                    result = filter_test_mode(self.path, result)
                if self.path == "/patient-search":
                    result = augment_search_envelope(result, recall_category)
                    patients = result.get("patients", []) if isinstance(result, dict) else []
                    if not pinned_patient_id:
                        result["patients"] = [
                            project_patient(patient, "identity")
                            for patient in patients
                            if isinstance(patient, dict)
                        ]
                    patients = result["patients"]
                    hydrated_exact = False
                    if (
                        not pinned_patient_id
                        and patient_profile != "identity"
                        and authoritative_count == 1
                        and not authoritative_capped
                        and len(patients) == 1
                    ):
                        exact_id = str(patients[0].get("patient_id", "")).strip()
                        if not re.fullmatch(r"\d+", exact_id):
                            status = 502
                            return self._send(
                                status,
                                {"ok": False, "error": "upstream_schema_error"},
                            )
                        hydrate_proc = run_cli(build_patient_get_argv(exact_id), env)
                        if hydrate_proc.returncode != 0:
                            status = 502
                            return self._send(
                                status,
                                {"ok": False, "error": "upstream_unavailable"},
                            )
                        hydrated = cli_json_result(hydrate_proc)
                        result["patients"] = patient_get_envelope(
                            hydrated, patient_profile
                        )["patients"]
                        hydrated_exact = True
                    effective_profile = (
                        patient_profile
                        if pinned_patient_id or hydrated_exact
                        else "identity"
                    )
                    result = finalize_patient_search_envelope(
                        result, patient_query_mode, effective_profile
                    )
                if retried and isinstance(result, dict):
                    result["retried_without_spaces"] = True
                if self.path == "/book" and confirm and isinstance(result, dict):
                    new_id = str(result.get("new_appt_id") or result.get("appointment_id") or "").strip()

                    def _run_list(pid):
                        largv = [CLI, "appt", "list", "--agent", "--reason",
                                 "bland-book-verify", "--patient", pid]
                        lp = run_cli(largv, env)
                        return (json.loads(lp.stdout.strip())
                                if lp.returncode == 0 and lp.stdout.strip() else None)

                    if verify_booking(book_pid, new_id, _run_list):
                        result["verified"] = True
                    else:
                        # BOOK-PROOF: never report success without a read-after-write
                        # confirmation that the appointment truly landed.
                        result["verified"] = False
                        result["success"] = False
                        result["verify_note"] = "read_after_write_unconfirmed"
                        log.warning("book read-after-write unconfirmed; success downgraded")
                if self.path == "/availability":
                    result = availability_envelope(result)
                    # Sticky-preference dead-end (live 2026-07-21): a morning
                    # pref carried over from an earlier turn filtered a
                    # Saturday with only afternoon slots down to zero and the
                    # caller was told "no openings". A day with slots must
                    # never read as empty: when a time filter zeroes out the
                    # result, retry unfiltered and flag the relaxation so the
                    # pathway can phrase it as "nothing that time of day, but".
                    pref = str(body.get("time_pref", "")).strip().lower()
                    if result["count"] == 0 and TIME_PREFS.get(pref):
                        try:
                            relax_body = {k: v for k, v in body.items() if k != "time_pref"}
                            argv_r, _ = build_argv(self.path, relax_body)
                            p_r = run_cli(argv_r, env)
                            relaxed = availability_envelope(cli_json_result(p_r)) if p_r.returncode == 0 else None
                            if relaxed and relaxed["count"]:
                                relaxed["time_pref_relaxed"] = pref
                                result = relaxed
                        except Exception as exc:
                            log.info("time-pref relax retry failed: %s", type(exc).__name__)
                    alt = ALT_STORES.get(str(body.get("store", "")).strip().lower())
                    result.update({"alt_store": "", "alt_count": 0, "alt_first_start": ""})
                    if result["count"] == 0 and alt:
                        try:
                            argv2, _ = build_argv(self.path, {**body, "store": alt})
                            p2 = run_cli(argv2, env)
                            alt_res = availability_envelope(
                                json.loads(p2.stdout.strip()) if p2.returncode == 0 and p2.stdout.strip() else []
                            )
                            result.update(
                                {
                                    "alt_store": alt,
                                    "alt_count": alt_res["count"],
                                    "alt_first_start": alt_res["first_start"],
                                }
                            )
                        except Exception as exc:
                            log.info("alt-store lookup failed: %s", type(exc).__name__)
                if self.path == "/appt-list":
                    result = normalized_appointment_result(result)
                status = 200
                return self._send(status, {"ok": True, "result": result})

            if self.path == "/patient-search" and pinned_patient_id:
                status = 200
                empty = augment_search_envelope(
                    patient_get_envelope(None, patient_profile), recall_category
                )
                empty = finalize_patient_search_envelope(
                    empty, patient_query_mode, patient_profile
                )
                return self._send(status, {"ok": True, "result": empty})

            if self.path == "/query":
                status = 502
                return self._send(status, {"ok": False, "error": "upstream_unavailable"})

            stderr_line = (proc.stderr.strip().splitlines() or [""])[-1]
            log.info("cli refusal 409: %s", stderr_line[:160])
            status = 409
            refusal = filter_test_mode(self.path, result)
            if isinstance(refusal, dict):
                for key in ("possible_duplicates", "patients", "matches", "ptData", "demographics", "result"):
                    if key in refusal:
                        value = refusal[key]
                        refusal[key] = {"redacted": True, "count": len(value) if isinstance(value, list) else 1}
            return self._send(status, {"ok": False, "exit_code": proc.returncode, "error": stderr_line, "result": refusal})
        finally:
            if self.path == "/query":
                query_audit(
                    query_request_id,
                    query_identity.get("tenant", ""),
                    query_identity.get("principal", ""),
                    query_operation,
                    status,
                    int((time.monotonic() - t0) * 1000),
                    query_count,
                )
            log.info("%s %s -> %d (%.0f ms)", self.command, self.path, status, (time.monotonic() - t0) * 1000)


def main():
    if (
        not API_KEY
        and not CONSUMER_CREDENTIALS
        and not CONSUMER_CREDENTIALS_CONFIGURED
        and CONSUMER_ACCEPT_LEGACY
    ):
        raise SystemExit("ECP_SHIM_BEARER is required")
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    log.info("listening on %s:%d", HOST, PORT)
    log.info("TEST_MODE=%s", TEST_MODE)
    srv.serve_forever()


if __name__ == "__main__":
    main()
