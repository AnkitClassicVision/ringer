#!/usr/bin/env python3
"""Validate a research report's citations against the actual files.

The report must contain a fenced block:  ```json CITATIONS ... ```  holding a list of
{"file": "<abs path>", "quote": "<verbatim substring>"} objects. Every cited file must
exist and contain its quote verbatim. Prints exactly which citation broke.
"""
import argparse
import json
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--min-citations", type=int, default=8)
    ap.add_argument("--require", action="append", default=[],
                    help="case-insensitive regex that must appear in the report body")
    args = ap.parse_args()

    try:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(f"FAIL: cannot read report: {exc}")
        sys.exit(1)

    fails = []
    for pattern in args.require:
        if not re.search(pattern, text, re.I):
            fails.append(f"report never matches required /{pattern}/")

    m = re.search(r"```json\s*CITATIONS\s*\n(.*?)```", text, re.S | re.I)
    if not m:
        m = re.search(r"```CITATIONS\s*\n(.*?)```", text, re.S | re.I)
    if not m:
        fails.append("no ```json CITATIONS fenced block found")
        cites = []
    else:
        try:
            cites = json.loads(m.group(1))
            if isinstance(cites, dict):  # tolerate {"CITATIONS": [...]} wrapping
                cites = next((v for v in cites.values() if isinstance(v, list)), [])
            assert isinstance(cites, list)
        except Exception as exc:  # noqa: BLE001
            fails.append(f"CITATIONS block is not a JSON list: {exc}")
            cites = []

    if len(cites) < args.min_citations:
        fails.append(f"only {len(cites)} citations, need >= {args.min_citations}")

    for i, c in enumerate(cites):
        path, quote = c.get("file", ""), c.get("quote", "")
        if not path or not quote:
            fails.append(f"citation[{i}] missing file or quote")
            continue
        try:
            body = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            fails.append(f"citation[{i}] file unreadable: {path}")
            continue
        if quote not in body:
            fails.append(f"citation[{i}] quote NOT found in {path}: {quote[:80]!r}")

    if fails:
        print(f"FAIL: {len(fails)} problem(s):")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print(f"PASS: {len(cites)} citations verified verbatim; all required sections present")


if __name__ == "__main__":
    main()
