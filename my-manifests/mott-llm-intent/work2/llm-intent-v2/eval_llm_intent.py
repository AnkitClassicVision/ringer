#!/usr/bin/env python3
"""Run the Bedrock intent tier against the frozen raw-text corpus."""

import os
import sys
import types
from datetime import datetime


def _stub_capability_registry():
    stub = types.ModuleType("capability_registry")

    class QueryError(Exception):
        pass

    stub.QueryError = QueryError
    stub.load_manifest = lambda *args, **kwargs: {}
    stub.prepare_query = lambda *args, **kwargs: {}
    stub.render_query_result = lambda *args, **kwargs: {}
    sys.modules.setdefault("capability_registry", stub)


_stub_capability_registry()
sys.path.append("/mnt/d_drive/repos/mott/gw-temporal-check")
from gen_golden import CORPUS
import bland_gateway


def _expected(value):
    if isinstance(value, str) and value not in {"conflict", "range"}:
        return "date", value
    if value == "conflict":
        return "ambiguous", None
    if value == "range":
        return "range/asap", None
    return "none", None


def main():
    if os.environ.get("RUN_REAL") != "1" or bland_gateway._bedrock() is None:
        print("SKIPPED: set RUN_REAL=1 with working AWS credentials")
        return 0

    today = datetime(2026, 7, 27, 12, 0, 0)
    passed = 0
    cases = CORPUS["raw_text"]
    for index, (text, expected_value) in enumerate(cases.items(), 1):
        expected_intent, expected_date = _expected(expected_value)
        verdict = bland_gateway.llm_interpret_intent(text, today)
        actual = verdict["intent"] if verdict else "error"
        ok = (
            (expected_intent == "range/asap" and actual in {"range", "asap"})
            or actual == expected_intent
        )
        if ok and expected_date is not None:
            ok = verdict.get("date") == expected_date
        passed += int(ok)
        print(
            f"{index:02d} {'PASS' if ok else 'FAIL'} "
            f"expected={expected_intent:<11} actual={actual}"
        )
    print(f"LLM exam: {passed}/{len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
