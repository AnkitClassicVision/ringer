#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

report = Path("review.md")
if not report.is_file() or report.stat().st_size < 400:
    raise SystemExit("FAIL: review.md is missing or too small")
text = report.read_text(encoding="utf-8", errors="replace")
first = next((line.strip() for line in text.splitlines() if line.strip()), "")
if first != "VERDICT: PASS":
    raise SystemExit(f"FAIL: fresh review did not pass; first line was {first!r}")
for marker in ("SEVERITY: BLOCK", "SEVERITY: HIGH"):
    if marker in text:
        raise SystemExit(f"FAIL: fresh review contains {marker}")
required = ("effective model", "OpenRouter", "retry", "registry")
missing = [marker for marker in required if marker.lower() not in text.lower()]
if missing:
    raise SystemExit(f"FAIL: review did not cover required seams: {missing}")
print("PASS: fresh report-only review returned PASS with no BLOCK/HIGH findings")
