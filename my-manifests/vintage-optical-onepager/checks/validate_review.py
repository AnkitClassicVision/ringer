#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys


def why(msg: str) -> None: print(f"WHY: {msg}")


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--review",required=True); args=ap.parse_args()
    p=Path(args.review); failures=[]
    if not p.is_file(): failures.append(f"missing review: {p}")
    else:
        t=p.read_text(encoding="utf-8",errors="replace")
        for h in ["# Fresh Release Review","## Verdict","## Material Findings","## Evidence Discipline","## Prospect Read","## Residual Risk"]:
            if h.lower() not in t.lower(): failures.append(f"missing review section: {h}")
        if not re.search(r"(?im)^\s*(READY|HOLD)\s*$",t): failures.append("Verdict section must contain a standalone READY or HOLD line")
        words=len(re.findall(r"\b[\w'-]+\b",t))
        if not 200<=words<=1200: failures.append(f"review word count {words} outside 200..1200")
        if not any(x in t for x in ["E002","E020","E029","E037"]): failures.append("review does not cite enough artifact evidence IDs")
        if "H1" not in t or "H2" not in t or "H3" not in t: failures.append("review does not inspect all three working hypotheses")
        if "external" not in t.lower(): failures.append("review does not assess external delivery boundary")
    if failures:
        for f in failures: why(f)
        return 1
    print("PASS: fresh review is structured and verdict-bearing; orchestrator must read the verdict and findings")
    return 0

if __name__=="__main__": sys.exit(main())
