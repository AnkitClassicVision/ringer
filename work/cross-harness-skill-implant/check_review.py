#!/usr/bin/env python3
"""Validate a report-only review and prove the reviewer did not edit the repo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_repo(repo: Path) -> dict:
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, text=True, capture_output=True, check=True).stdout.splitlines()
    files: dict[str, str] = {}
    for line in status:
        if not line:
            continue
        rel = line[3:].strip()
        path = repo / rel
        if path.is_file():
            files[rel] = file_hash(path)
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    files[str(child.relative_to(repo))] = file_hash(child)
    return {"status": status, "files": files}


def run_checked(argv: list[str], repo: Path) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(argv, cwd=repo, env=env, text=True, capture_output=True, timeout=300)
    if proc.returncode:
        print(proc.stdout[-3000:])
        print(proc.stderr[-3000:])
        raise AssertionError(f"verification failed: {argv}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    review = Path(args.review)
    repo = Path(args.repo).resolve()
    snapshot_path = Path(args.snapshot)
    if not review.is_file() or review.stat().st_size < 800:
        raise AssertionError("review.md missing or too small")
    text = review.read_text(encoding="utf-8")
    upper = text.upper()
    for marker in ("REQUIREMENTS TRACE", "FINDINGS", "TEST EVIDENCE", "SCOPE", "VERDICT"):
        if marker not in upper:
            raise AssertionError(f"review missing section: {marker}")
    for unit in ("U1", "U2", "U3", "U4", "U5"):
        if unit not in text:
            raise AssertionError(f"review does not trace {unit}")
    match = re.search(r"VERDICT\s*[:\-]?\s*(ALLOW|REVISE|BLOCK|ESCALATE)", upper)
    if not match:
        raise AssertionError("review verdict must be ALLOW, REVISE, BLOCK, or ESCALATE")
    if "NO FINDINGS" not in upper:
        for marker in ("Evidence:", "Impact:", "Fix:", "Priority:", "Confidence:"):
            if marker not in text:
                raise AssertionError(f"review findings missing label: {marker}")

    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    actual_before = snapshot_repo(repo)
    if actual_before != expected:
        raise AssertionError("repo changed before review validation; reviewer may have edited owned files")

    run_checked([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], repo)
    run_checked([sys.executable, "/mnt/d_drive/repos/ringer/work/cross-harness-skill-implant/check_implant_workflow.py", "--repo", str(repo)], repo)

    actual_after = snapshot_repo(repo)
    if actual_after != expected:
        raise AssertionError("verification or reviewer changed repository state")
    print(f"PASS: report-only review valid, verdict={match.group(1)}, U1-U5 traced, tests green, repo unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
