#!/usr/bin/env python3
"""Reproduce the deployed Mott raw-text date-authority pipeline."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime
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


def load_gateway():
    # These values are read at import time. Mott selects the deployed parser's
    # tenant-specific conflict semantics; the model setting is honored even
    # though this raw path never invokes Bedrock.
    os.environ["ECP_TENANT_ID"] = "mott"
    os.environ.setdefault("ECP_LLM_MODEL_ID", DEFAULT_MODEL)
    spec = importlib.util.spec_from_file_location("mott_raw_text_authority_repro", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load source module: {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def frozen_datetime() -> datetime:
    raw = os.environ.get("FROZEN_NOW", "").strip()
    if not raw:
        raise ValueError("FROZEN_NOW is required (ISO8601 with offset)")
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("FROZEN_NOW must include a UTC offset")
    return value


def fetch_with_120_second_timeout(module, conversation_id):
    # Preserve the module's endpoint ordering, headers, validation, response
    # parsing, redirect policy, and fallback behavior. Only widen its opener's
    # per-call timeout to the reproduction contract's 120 seconds.
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
        gateway = load_gateway()
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
