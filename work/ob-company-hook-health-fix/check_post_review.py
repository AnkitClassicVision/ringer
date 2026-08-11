#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
import sys

VALIDATOR = Path("/mnt/d_drive/repos/ringer/templates/review-swarm/checks/review-swarm.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--surface", required=True)
    args = parser.parse_args()

    spec = importlib.util.spec_from_file_location("review_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        print(f"WHY: could not load review validator at {VALIDATOR}")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    failures = module.validate_report(args.report, args.surface)
    if failures:
        for failure in failures:
            print(failure)
        return 1

    text = args.report.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^Verdict:\s*(ALLOW|REVISE|BLOCK)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        print("WHY: report must contain exact standalone Verdict: ALLOW|REVISE|BLOCK")
        return 1
    verdict = match.group(1).upper()
    priorities = {item.upper() for item in re.findall(r"Priority:\s*(P[0-3])\b", text, re.IGNORECASE)}
    if verdict == "ALLOW" and priorities.intersection({"P0", "P1"}):
        print("WHY: ALLOW cannot coexist with unresolved P0/P1 findings")
        return 1
    if "source-work" not in text:
        print("WHY: report must identify the reviewed source-work snapshot")
        return 1
    print(f"PASS: {args.surface} review contract and verdict are coherent ({verdict})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
