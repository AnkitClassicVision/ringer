#!/usr/bin/env python3
"""Check that the Sales Ops live boundary blocks without approval."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"WHY: {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    proc = subprocess.run(
        [sys.executable, str(args.boundary), "--queue", str(args.queue), "--out", str(args.out)],
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        fail(f"boundary probe should block cleanly with rc=0, got {proc.returncode}\n{proc.stdout}\n{proc.stderr}")
    if not args.out.exists() or args.out.stat().st_size == 0:
        fail("boundary output missing")
    data = json.loads(args.out.read_text(encoding="utf-8"))
    if data.get("allowed") is not False or data.get("decision") != "block":
        fail("boundary did not block")
    if data.get("send_receipt") or data.get("hubspot_receipt"):
        fail("boundary produced live receipts")
    if data.get("external_actions_taken"):
        fail("boundary recorded external actions")
    needed = {"missing_live_env_flag", "missing_approval_file", "row_not_approved_to_send"}
    reasons = set(data.get("reasons") or [])
    missing = sorted(needed - reasons)
    if missing:
        fail(f"boundary reasons missing {missing}")
    print("PASS: live boundary blocks without approval, env flag, and passing QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
