#!/usr/bin/env python3
"""Validate a live-harness phase transcript: RESULT line present, zero failures."""
import argparse
import pathlib
import re
import sys

sys.dont_write_bytecode = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="transcript.txt")
    ap.add_argument("--phase", required=True)
    ap.add_argument("--total", type=int, required=True)
    args = ap.parse_args()

    path = pathlib.Path(args.file)
    if not path.is_file():
        print(f"FAIL: {args.file} does not exist — the harness run produced no transcript")
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"RESULT {args.phase}: passed=(\d+) failed=(\d+) waived=(\d+) total=(\d+)", text)
    if not m:
        print(f"FAIL: no 'RESULT {args.phase}:' summary line — the run died before finishing; transcript tail:")
        for line in text.strip().splitlines()[-6:]:
            print(f"  {line[:200]}")
        return 1
    passed, failed, waived, total = map(int, m.groups())
    if total != args.total:
        print(f"FAIL: ran {total} scenarios, expected {args.total} — selection drifted")
        return 1
    if failed:
        print(f"FAIL: {failed} scenario(s) failed:")
        for line in re.findall(r"^\[FAIL\].*$|^\s+->.*$", text, re.M)[:40]:
            print(f"  {line[:200]}")
        return 1
    print(f"PASS: {args.phase} — {passed}/{total} scenarios passed, {waived} waived claim-rule hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
