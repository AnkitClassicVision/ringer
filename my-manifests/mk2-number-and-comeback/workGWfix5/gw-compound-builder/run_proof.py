#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import types
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ORIGINAL = Path("/home/ankit114/repos/gw-diag-snap/container/bland_gateway.py")
FIXED = Path(__file__).with_name("bland_gateway_fixed.py")
GOLDEN = Path("/mnt/d_drive/repos/mott/gw-temporal-check/gen_golden.py")
EVAL = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workT1r3/t1-final-analysis/eval_cases.json")
MESSAGES = Path("/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workT1r3/t1-prefix-run/messages_prefix.json")
EASTERN = ZoneInfo("America/New_York")


def stub_registry() -> None:
    module = types.ModuleType("capability_registry")

    class QueryError(Exception):
        pass

    module.QueryError = QueryError
    module.load_manifest = lambda *_a, **_k: {}
    module.prepare_query = lambda *_a, **_k: {}
    module.render_query_result = lambda *_a, **_k: {}
    sys.modules["capability_registry"] = module


def load(path: Path, name: str, now: datetime):
    os.environ["ECP_TENANT_ID"] = "mott"
    os.environ["ECP_DATE_ORDINAL_FALLBACK"] = "1"
    stub_registry()
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module._eastern_today = lambda: now
    return module


def phrase_corpus():
    spec = importlib.util.spec_from_file_location("proof_golden", GOLDEN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {GOLDEN}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    phrases = []
    for group in module.CORPUS.values():
        phrases.extend(group.keys() if isinstance(group, dict) else group)
    return list(dict.fromkeys(phrases))


def intended_compound(phrase: str) -> bool:
    weekday = r"(?:mon(?:day)?|tue(?:sday|s)?|wed(?:nesday)?|thu(?:rsday|rs|r)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"
    month = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    ordinal = r"(?:the\s+)?\d{1,2}(?:st|nd|rd|th)"
    explicit = rf"{month}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{4}})?"
    return bool(re.search(rf"\b(?:{weekday}.{{0,12}}(?:{ordinal}|{explicit})|(?:{ordinal}|{explicit}).{{0,12}}{weekday})\b", phrase, re.I))


def main() -> int:
    if not ORIGINAL.is_file() or b"raw_fetch msgs" not in ORIGINAL.read_bytes():
        return 1
    frozen = datetime(2026, 8, 3, 12, 0, tzinfo=EASTERN)
    original = load(ORIGINAL, "proof_original", frozen)
    fixed = load(FIXED, "proof_fixed", frozen)
    print(f"ORIGINAL_PATH={ORIGINAL}")
    print(f"ORIGINAL_SHA={hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()}")

    p4 = {
        "Friday the 14th": "08/14/2026",
        "friday the 14th works": "08/14/2026",
        "Friday August 14": "08/14/2026",
    }
    p4_ok = True
    for phrase, expected in p4.items():
        result = fixed.extract_date_from_text(phrase)
        print(f"EXTRACT_FIXED({phrase!r})={result}")
        p4_ok &= isinstance(result, str) and result == expected
    print(f"P4_COMPOUND={'OK' if p4_ok else 'FAIL'}")

    conflict = fixed.extract_date_from_text("next Friday the 17th")
    conflict_dates = set(conflict[1:3]) if isinstance(conflict, tuple) and conflict[:1] == ("conflict",) else set()
    p5_ok = conflict_dates == {"08/07/2026", "08/17/2026"}
    print(f"EXTRACT_FIXED('next Friday the 17th')={conflict}")
    print(f"P5_CONFLICT={'PRESERVED' if p5_ok else 'FAIL'}")

    differences = []
    unintended = 0
    for phrase in phrase_corpus():
        for function in ("resolve_relative_date", "extract_date_from_text"):
            before = getattr(original, function)(phrase)
            after = getattr(fixed, function)(phrase)
            if before != after:
                intended = function == "extract_date_from_text" and intended_compound(phrase)
                differences.append((function, phrase, before, after, intended))
                unintended += not intended
                print(f"P2_DIFF function={function} phrase={phrase!r} original={before!r} fixed={after!r} intended={intended}")
    print(f"P2_DIFFS={len(differences)} P2_UNINTENDED={unintended}")

    passed = 0
    for index, case in enumerate(json.loads(EVAL.read_text()), 1):
        case_now = datetime.fromisoformat(case["now"]).replace(hour=12, tzinfo=EASTERN)
        fixed._eastern_today = lambda case_now=case_now: case_now
        result = fixed.extract_date_from_text(case["phrase"], case["prior_offer"])
        ok = result == case["expected"]
        passed += ok
        print(f"P1_CASE={index} RESULT={result!r} EXPECTED={case['expected']!r} OK={ok}")
    print(f"P1_EXT={passed}/12")

    incident_now = datetime.fromisoformat("2026-08-03T16:58:00-04:00")
    fixed._eastern_today = lambda: incident_now
    incident = fixed.resolve_from_conversation(json.loads(MESSAGES.read_text()))[0]
    print(f"P3_INCIDENT={incident}")

    return 0 if (p4_ok and p5_ok and unintended == 0 and passed == 12 and incident == "08/13/2026") else 1


if __name__ == "__main__":
    raise SystemExit(main())
