#!/usr/bin/env python3
"""Offline deterministic proof for the production following-weekday patch."""

import hashlib
import importlib.util
import json
import os
import re
import sys
import types
from datetime import datetime
from pathlib import Path


ORIGINAL = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGWfix2/gw-prod-extract2/bland_gateway_prod.py")
FIXED = Path(__file__).with_name("bland_gateway_fixed.py").resolve()
CASES = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workT1r3/t1-final-analysis/eval_cases.json")
MESSAGES = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workT1r3/t1-prefix-run/messages_prefix.json")
GOLDEN = Path("/mnt/d_drive/repos/mott/gw-temporal-check/gen_golden.py")

assert ORIGINAL.is_file(), f"missing pinned production base: {ORIGINAL}"
assert "raw_fetch msgs" in ORIGINAL.read_text(encoding="utf-8"), (
    f"pinned production base lacks raw_fetch msgs marker: {ORIGINAL}"
)
print(f"ORIGINAL_PATH={ORIGINAL}")
print(f"ORIGINAL_SHA={hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()[:16]}")


class QueryError(Exception):
    pass


def no_op(*_args, **_kwargs):
    return None


# Install the gateway's sibling dependency stub before importing either copy.
stub = types.ModuleType("capability_registry")
stub.QueryError = QueryError
stub.load_manifest = no_op
stub.prepare_query = no_op
stub.render_query_result = no_op
stub.__getattr__ = lambda _name: no_op
sys.modules["capability_registry"] = stub
os.environ["ECP_TENANT_ID"] = "mott"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


original = load(ORIGINAL, "gateway_original")
fixed = load(FIXED, "gateway_fixed")
golden = load(GOLDEN, "gateway_golden")


def freeze(module, iso):
    now = datetime.fromisoformat(iso)
    module._eastern_today = lambda: now


def printable(value):
    if value is None:
        return "NONE"
    if isinstance(value, tuple):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def fixed_case(case):
    freeze(fixed, case["now"] + "T12:00:00-04:00")
    if case["context"] == "correction-after-offer":
        return fixed.resolve_from_conversation(
            [{"sender": "USER", "message": case["phrase"]}]
        )[0]
    return fixed.resolve_relative_date(case["phrase"])


cases = json.loads(CASES.read_text(encoding="utf-8"))
passed = 0
for index, case in enumerate(cases, 1):
    actual = fixed_case(case)
    ok = actual == case["expected"]
    passed += int(ok)
    print(
        f"CASE={index} phrase={json.dumps(case['phrase'])} "
        f"actual={printable(actual)} expected={case['expected']} ok={int(ok)}"
    )
print(f"P1_EXT={passed}/{len(cases)}")


phrases = []
for group in golden.CORPUS.values():
    phrases.extend(group.keys() if isinstance(group, dict) else group)
phrases = list(dict.fromkeys(phrases))
freeze(original, "2026-07-27T12:00:00-04:00")
freeze(fixed, "2026-07-27T12:00:00-04:00")
allowed = re.compile(
    r"^(?:no[,!. ]+)?(?:the )?following "
    r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b",
    re.IGNORECASE,
)
diffs = []
unintended = 0
for phrase in phrases:
    before = (
        original.resolve_relative_date(phrase),
        original.extract_date_from_text(phrase),
    )
    after = (
        fixed.resolve_relative_date(phrase),
        fixed.extract_date_from_text(phrase),
    )
    if before != after:
        diffs.append((phrase, before, after))
        unintended += int(not allowed.match(phrase))
for phrase, before, after in diffs:
    print(
        f"P2_DIFF phrase={json.dumps(phrase)} "
        f"orig={printable(before)} fixed={printable(after)}"
    )
print(f"P2_DIFFS={len(diffs)} P2_UNINTENDED={unintended}")


freeze(fixed, "2026-08-03T16:58:00-04:00")
messages = json.loads(MESSAGES.read_text(encoding="utf-8"))
incident = fixed.resolve_from_conversation(messages)[0]
print(f"P3_INCIDENT={printable(incident)}")
