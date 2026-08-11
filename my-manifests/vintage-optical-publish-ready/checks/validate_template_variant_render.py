#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

from PIL import Image


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    failures: list[str] = []
    for path in (args.source, args.pdf, args.png, args.receipt):
        if not path.is_file():
            failures.append(f"missing variant artifact: {path.name}")
    if failures:
        for item in failures:
            print(f"WHY: {item}")
        return 1
    receipt = json.loads(args.receipt.read_text())
    if receipt.get("status") != "PASS":
        failures.append("template render receipt is not PASS")
    if receipt.get("source", {}).get("sha256") != digest(args.source):
        failures.append("template render receipt source hash mismatch")
    if receipt.get("pdf", {}).get("sha256") != digest(args.pdf):
        failures.append("template render receipt PDF hash mismatch")

    info = subprocess.run(["pdfinfo", str(args.pdf)], text=True, capture_output=True, check=True).stdout
    if not re.search(r"^Pages:\s+1$", info, re.M) or "612 x 792" not in info:
        failures.append("template-framed PDF is not exactly one Letter page")
    with tempfile.TemporaryDirectory() as temp:
        bbox = Path(temp) / "bbox.html"
        subprocess.run(["pdftotext", "-bbox-layout", str(args.pdf), str(bbox)], check=True)
        raw = bbox.read_text(encoding="utf-8", errors="replace")
    words = [(float(x1), float(y1), float(x2), float(y2), re.sub(r"<[^>]+>", "", word)) for x1, y1, x2, y2, word in re.findall(r'<word[^>]*xMin="([0-9.]+)"[^>]*yMin="([0-9.]+)"[^>]*xMax="([0-9.]+)"[^>]*yMax="([0-9.]+)"[^>]*>(.*?)</word>', raw)]
    if not words:
        failures.append("template-framed PDF has no extractable word boxes")
        margin = 0.0
    else:
        margin = 792.0 - max(row[3] for row in words)
        if margin < 20.0:
            failures.append(f"template-framed PDF bottom text margin is only {margin:.2f} points")
        if any(x1 < -0.5 or y1 < -0.5 or x2 > 612.5 or y2 > 792.5 for x1, y1, x2, y2, _ in words):
            failures.append("template-framed PDF contains out-of-page word boxes")
    text = " ".join(row[4] for row in words)
    compact = " ".join(text.split()).lower()
    for token in (
        "where vintage optical can win its next patient dollar",
        "market support is real. proof is the bottleneck.",
        "54 / 100",
        "173,058",
        "283,661",
        "+2.29%",
        "+3.92%",
        "57 / 100",
        "43 / 100",
        "vintage 4.9 / 348",
        "focus 4.8 / 182",
        "tri-county 4.9 / 271",
        "walmart 3.5 / 8",
        "visibility baseline",
        "reputation source control",
        "booking completion",
        "specialty evidence",
        "dry eye 53",
        "myopia management 53",
        "specialty contact lenses 51",
        "decision rule:",
        "return with rank-grid visibility, source-controlled reputation, and a complete booking denominator.",
        "approve the 30-day measurement sprint",
        "human project room approval required",
        "rank grid did not run",
    ):
        if token not in compact:
            failures.append(f"template-framed PDF lacks visible message: {token}")
    for forbidden in ("$", "/home/", "/mnt/", "file://", "CANARY", "4.07", "1.56", "244.3"):
        if forbidden.lower() in compact:
            failures.append(f"template-framed PDF contains forbidden text: {forbidden}")

    image = Image.open(args.png).convert("RGB")
    width, height = image.size
    if (width, height) != (1275, 1650):
        failures.append(f"unexpected template image dimensions: {width}x{height}")
    last_dark_row = -1
    for y in range(height):
        dark = 0
        for x in range(0, width, 5):
            pixel = cast(tuple[int, int, int], image.getpixel((x, y)))
            if max(pixel) < 100:
                dark += 1
        if dark > width // 100:
            last_dark_row = y
    raster_margin = height - 1 - last_dark_row
    if raster_margin < 18:
        failures.append(f"template-framed raster content ends only {raster_margin} pixels above page edge")

    if failures:
        for item in failures:
            print(f"WHY: {item}")
        return 1
    print(f"PASS: template-framed one-pager is one Letter page with all truthful messages, {margin:.2f} PDF points and {raster_margin} raster pixels of bottom safety")
    return 0


if __name__ == "__main__":
    sys.exit(main())
