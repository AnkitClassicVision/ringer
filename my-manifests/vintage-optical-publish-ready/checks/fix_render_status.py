#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FILES = ("onepager.html", "number-explainer.md", "number-explainer.html")
OLD = "Render pending"
NEW = "Rendered internal candidate"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    root = args.dir.resolve()
    receipt = args.receipt.resolve()
    if not root.is_dir():
        raise SystemExit("FAIL: report directory missing")
    if root in receipt.parents or receipt == root:
        raise SystemExit("FAIL: receipt must remain in the isolated task directory")

    rows = []
    for name in FILES:
        path = root / name
        if not path.is_file():
            raise SystemExit(f"FAIL: missing {name}")
        text = path.read_text(encoding="utf-8")
        count = text.count(OLD)
        if count not in (0, 1):
            raise SystemExit(f"FAIL: expected zero or one stale status in {name}, got {count}")
        before = digest(path)
        if count == 1:
            path.write_text(text.replace(OLD, NEW), encoding="utf-8")
        after_text = path.read_text(encoding="utf-8")
        if OLD in after_text or NEW not in after_text:
            raise SystemExit(f"FAIL: status correction did not verify in {name}")
        rows.append({"file": name, "before_sha256": before, "after_sha256": digest(path), "replacements": count})

    data = {
        "status": "PASS",
        "change": f"{OLD} -> {NEW}",
        "files": rows,
        "external_actions_taken": "none",
        "other_report_files_modified": [],
    }
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("PASS: visible render status corrected in exactly three report source files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
