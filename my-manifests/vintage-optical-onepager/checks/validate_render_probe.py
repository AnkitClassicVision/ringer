#!/usr/bin/env python3
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path


def why(msg: str) -> None:
    print(f"WHY: {msg}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--html", required=True)
    args = ap.parse_args()
    pdf, html = Path(args.pdf), Path(args.html)
    failures = []
    if not html.is_file() or html.stat().st_size < 10000:
        failures.append("probe HTML missing or implausibly small")
    if not pdf.is_file() or pdf.stat().st_size < 10000:
        failures.append("probe PDF missing or implausibly small")
    if failures:
        for f in failures: why(f)
        return 1
    info = subprocess.run(["pdfinfo", str(pdf)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if info.returncode:
        failures.append("pdfinfo could not parse probe PDF: " + info.stdout.strip())
    pages = None
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            try: pages = int(line.split(":", 1)[1].strip())
            except ValueError: pass
    if pages != 1:
        failures.append(f"probe PDF must have exactly 1 page, got {pages}")
    text = subprocess.run(["pdftotext", str(pdf), "-"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if text.returncode or len(text.stdout.strip()) < 500:
        failures.append("probe PDF text extraction failed or is too short")
    if failures:
        for f in failures: why(f)
        return 1
    print(f"PASS: headless Chromium rendered one parseable page ({pdf.stat().st_size} bytes, {len(text.stdout)} extracted chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
