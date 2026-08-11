#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FILES = ("onepager.html", "number-explainer.md", "number-explainer.html")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    failures = []
    try:
        receipt = json.loads(args.receipt.read_text())
    except Exception as exc:
        print(f"WHY: receipt parse failed: {exc}")
        return 1
    if receipt.get("status") != "PASS" or receipt.get("external_actions_taken") != "none":
        failures.append("receipt status or external-action boundary is wrong")
    if {row.get("file") for row in receipt.get("files") or []} != set(FILES):
        failures.append("receipt does not cover exactly the three visible source files")
    for name in FILES:
        path = args.dir / name
        if not path.is_file():
            failures.append(f"missing {name}")
            continue
        text = path.read_text(encoding="utf-8")
        if "Render pending" in text:
            failures.append(f"stale visible status remains in {name}")
        if text.count("Rendered internal candidate") != 1:
            failures.append(f"corrected visible status count is not one in {name}")
    if failures:
        for item in failures:
            print(f"WHY: {item}")
        return 1
    print("PASS: exactly three report sources show the corrected internal render status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
