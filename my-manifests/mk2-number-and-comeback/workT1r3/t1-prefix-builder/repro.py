#!/usr/bin/env python3
"""Reproduce the deployed Mott raw-text date-authority pipeline."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


SOURCE = Path(
    "/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/"
    "raw-text-authority-v2/bland_gateway_live.py"
)
DEFAULT_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
ISOLATION_INPUTS = (
    "thursday",
    "the following thursday",
    "following thursday",
    "thursday next week",
    "next thursday",
    "thursday after next",
)
EXTRACT_INPUTS = (
    "No the following Thursday",
    "the following thursday",
    "no thursday the following week",
)
TIMESTAMP_FIELDS = (
    "created_at", "createdAt", "timestamp", "sent_at", "sentAt",
    "updated_at", "date_created", "time",
)


def mask_long_digits(value):
    """Mask digit runs of five or more, retaining only their last four digits."""
    if isinstance(value, str):
        return re.sub(r"\d{5,}", lambda match: "*" * (len(match.group()) - 4) + match.group()[-4:], value)
    if isinstance(value, list):
        return [mask_long_digits(item) for item in value]
    if isinstance(value, dict):
        return {key: mask_long_digits(item) for key, item in value.items()}
    return value


def safe_text(value) -> str:
    return mask_long_digits(str(value)).replace("\r", " ").replace("\n", " ")


def display_result(value) -> str:
    if value is None:
        return "NONE"
    if isinstance(value, str):
        return safe_text(value)
    return safe_text(repr(value))


def load_live_module():
    os.environ["ECP_TENANT_ID"] = "mott"
    os.environ.setdefault("ECP_LLM_MODEL_ID", DEFAULT_MODEL)

    class QueryError(Exception):
        pass

    def no_op(*_args, **_kwargs):
        return None

    capability_registry = types.ModuleType("capability_registry")
    capability_registry.QueryError = QueryError
    capability_registry.load_manifest = no_op
    capability_registry.prepare_query = no_op
    capability_registry.render_query_result = no_op
    sys.modules.setdefault("capability_registry", capability_registry)

    stubbed = {"capability_registry"}
    while True:
        spec = importlib.util.spec_from_file_location("mott_raw_text_authority_repro", SOURCE)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load source module: {SOURCE}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            return module
        except ModuleNotFoundError as exc:
            sys.modules.pop(spec.name, None)
            missing = exc.name
            if not missing or missing in stubbed or len(stubbed) >= 5:
                raise
            sibling = SOURCE.parent / (missing.replace(".", "/") + ".py")
            if sibling.exists():
                raise
            stub = types.ModuleType(missing)
            stub.__getattr__ = lambda _name: no_op
            sys.modules[missing] = stub
            stubbed.add(missing)


def frozen_datetime() -> datetime:
    raw = os.environ.get("FROZEN_NOW", "").strip()
    if not raw:
        raise ValueError("FROZEN_NOW is required (ISO8601 with offset)")
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("FROZEN_NOW must include a UTC offset")
    return value


def utc_datetime(raw: str, label: str) -> datetime:
    value = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be ISO8601 UTC")
    if value.utcoffset().total_seconds() != 0:
        raise ValueError(f"{label} must be ISO8601 UTC")
    return value.astimezone(timezone.utc)


def message_timestamp(message):
    if not isinstance(message, dict):
        return None
    for field in TIMESTAMP_FIELDS:
        if message.get(field) not in (None, ""):
            try:
                return datetime.fromisoformat(str(message[field]).strip().replace("Z", "+00:00")).astimezone(timezone.utc)
            except (ValueError, TypeError):
                continue
    return None


def latest_user_text(messages) -> str:
    users = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("sender", message.get("role", ""))
        if str(role or "").upper() == "USER":
            users.append(message)
    if not users:
        return ""
    if all(message.get("created_at") for message in users):
        chosen = max(users, key=lambda message: str(message["created_at"]))
    else:
        chosen = users[-1]
    return str(chosen.get("message", chosen.get("content", "")) or "")[:2000]


def fetch_with_120_second_timeout(module, conversation_id):
    original_build_opener = module.urllib.request.build_opener

    class TimeoutOpener:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def open(self, request, timeout=None):
            return self.wrapped.open(request, timeout=120)

    def build_opener(*handlers):
        return TimeoutOpener(original_build_opener(*handlers))

    module.urllib.request.build_opener = build_opener
    try:
        return module._fetch_conversation(conversation_id)
    finally:
        module.urllib.request.build_opener = original_build_opener


def main(argv) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} <conversation_id>")
        return 2

    try:
        now = frozen_datetime()
        gateway = load_live_module()
        gateway._eastern_today = lambda: now
        messages = fetch_with_120_second_timeout(gateway, argv[1])
    except Exception as exc:
        print(f"FETCH_FAILURE={safe_text(type(exc).__name__ + ': ' + str(exc))}")
        return 1

    if not messages:
        print("FETCH_FAILURE=no messages returned by module fetch path")
        return 1

    with Path("messages.json").open("w", encoding="utf-8") as handle:
        json.dump(mask_long_digits(messages), handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"MSGS={len(messages)}")
    raw_from, _raw_to = gateway.resolve_from_conversation(messages)
    print("PIPELINE_PICKED=NOT-APPLICABLE")
    resolved = raw_from if isinstance(raw_from, str) else None
    print(f"PIPELINE_RESOLVED={resolved or 'NONE'}")

    max_ts_raw = os.environ.get("MAX_TS", "").strip()
    if not max_ts_raw:
        print("PREFIX_MSGS=SKIPPED")
    else:
        try:
            max_ts = utc_datetime(max_ts_raw, "MAX_TS")
            timestamps = [message_timestamp(message) for message in messages]
            if not any(timestamp is not None for timestamp in timestamps):
                print("PREFIX_MSGS=NO-TIMESTAMPS")
                print("PREFIX_FALLBACK=first 11 messages")
                prefix = list(messages[:11])
            else:
                prefix = [
                    message for message, timestamp in zip(messages, timestamps)
                    if timestamp is not None and timestamp <= max_ts
                ]
                print(f"PREFIX_MSGS={len(prefix)}")
            with Path("messages_prefix.json").open("w", encoding="utf-8") as handle:
                json.dump(mask_long_digits(prefix), handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            prefix_from, _prefix_to = gateway.resolve_from_conversation(prefix)
            print(f"PREFIX_RESOLVED={display_result(prefix_from)}")
            extract_inputs = (latest_user_text(prefix),) + EXTRACT_INPUTS
            for phrase in extract_inputs:
                result = gateway.extract_date_from_text(phrase)
                print(f"EXTRACT({safe_text(phrase)[:40]})={display_result(result)}")
        except Exception as exc:
            print(f"FETCH_FAILURE={safe_text(type(exc).__name__ + ': ' + str(exc))}")
            return 1

    for phrase in ISOLATION_INPUTS:
        result = gateway.resolve_relative_date(phrase)
        print(f"STAGE2({phrase})={result or 'NONE'}")

    print("LLM_PICKED=NOT-APPLICABLE")
    print("PHRASE_PICKER=resolve_from_conversation->extract_date_from_text")
    print("OBSERVED_DEPLOYED=08/06/2026")
    print("CORRECT_TARGET=08/13/2026")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
