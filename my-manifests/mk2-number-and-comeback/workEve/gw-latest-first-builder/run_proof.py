#!/usr/bin/env python3
"""Offline proof for opt-in availability ordering and parser parity."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import types
from datetime import datetime
from pathlib import Path


ORIGINAL = Path("/home/ankit114/repos/gw-diag-snap/container/bland_gateway.py")
FIXED = Path(__file__).with_name("bland_gateway_fixed.py")
GOLDEN = Path("/mnt/d_drive/repos/mott/gw-temporal-check/gen_golden.py")


def install_stubs():
    class QueryError(Exception):
        pass

    stub = types.ModuleType("capability_registry")
    stub.QueryError = QueryError
    stub.load_manifest = lambda *args, **kwargs: {}
    stub.prepare_query = lambda *args, **kwargs: {}
    stub.render_query_result = lambda *args, **kwargs: {}
    sys.modules["capability_registry"] = stub


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if hasattr(module, "_eastern_today"):
        module._eastern_today = lambda: datetime(2026, 7, 27, 12, 0, 0)
    return module


def corpus_phrases(corpus):
    phrases = []
    for value in corpus.values():
        phrases.extend(value.keys() if isinstance(value, dict) else value)
    return list(dict.fromkeys(phrases))


def main() -> int:
    if not ORIGINAL.is_file() or b"raw_fetch msgs" not in ORIGINAL.read_bytes():
        print("BASE_ERROR=pinned production base missing or invalid")
        return 1
    original_sha = hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    print(f"ORIGINAL_PATH={ORIGINAL}")
    print(f"ORIGINAL_SHA={original_sha}")

    install_stubs()
    original = load(ORIGINAL, "proof_original_gateway")
    fixed = load(FIXED, "proof_fixed_gateway")
    golden = load(GOLDEN, "proof_golden_corpus")

    times = [
        "08:00 am", "08:30 am", "09:00 am", "09:30 am",
        "10:00 am", "11:30 am", "12:00 pm", "12:30 pm",
        "01:30 pm", "03:00 pm", "04:30 pm", "05:00 pm",
    ]
    fixture = [
        {"start": f"08/06/2026 {clock}", "end": f"08/06/2026 {clock}",
         "doctor_id": f"D{index:02d}", "store_id": "958", "store_name": "Mott"}
        for index, clock in enumerate(times)
    ]

    latest = fixed.availability_envelope(copy.deepcopy(fixture), "latest")
    expected_latest = [fixture[-1]["start"], fixture[-2]["start"]]
    actual_latest = [slot["start"] for slot in latest["slots"][:2]]
    if actual_latest != expected_latest:
        raise AssertionError(("P6", actual_latest, expected_latest))
    print("P6_LATEST=OK")

    anchored = fixed.availability_envelope(copy.deepcopy(fixture), "anchor=12:00")
    expected_anchor = [fixture[6]["start"], fixture[5]["start"]]
    actual_anchor = [slot["start"] for slot in anchored["slots"][:2]]
    if actual_anchor != expected_anchor:
        raise AssertionError(("P7", actual_anchor, expected_anchor))
    print("P7_ANCHOR=OK")

    original_default = original.availability_envelope(copy.deepcopy(fixture))
    fixed_default = fixed.availability_envelope(copy.deepcopy(fixture))
    original_bytes = json.dumps(original_default, ensure_ascii=False, separators=(",", ":")).encode()
    fixed_bytes = json.dumps(fixed_default, ensure_ascii=False, separators=(",", ":")).encode()
    if fixed_bytes != original_bytes:
        raise AssertionError("P8 default envelope bytes differ")
    print("P8_DEFAULT_PARITY=OK")

    diffs = 0
    for phrase in corpus_phrases(golden.CORPUS):
        for function_name in ("resolve_relative_date", "extract_date_from_text"):
            before = getattr(original, function_name)(phrase)
            after = getattr(fixed, function_name)(phrase)
            if before != after:
                diffs += 1
                print(f"P9_DIFF phrase={phrase!r} function={function_name} original={before!r} fixed={after!r}")
    print(f"P9_DIFFS={diffs}")
    return 0 if diffs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
