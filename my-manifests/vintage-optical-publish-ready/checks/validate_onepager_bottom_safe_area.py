#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

from PIL import Image, ImageStat


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    args = parser.parse_args()
    failures: list[str] = []
    if not args.pdf.is_file() or not args.png.is_file():
        print("WHY: PDF or page image missing")
        return 1

    info = subprocess.run(["pdfinfo", str(args.pdf)], text=True, capture_output=True, check=True).stdout
    if not re.search(r"^Pages:\s+1$", info, re.M):
        failures.append("one-pager is not exactly one PDF page")
    if "612 x 792" not in info:
        failures.append("one-pager is not Letter size")

    with tempfile.TemporaryDirectory() as temp:
        bbox = Path(temp) / "bbox.html"
        subprocess.run(["pdftotext", "-bbox-layout", str(args.pdf), str(bbox)], check=True)
        raw = bbox.read_text(encoding="utf-8", errors="replace")
    words = [(float(y), re.sub(r"<[^>]+>", "", word)) for y, word in re.findall(r'<word[^>]*yMax="([0-9.]+)"[^>]*>(.*?)</word>', raw)]
    if not words:
        failures.append("PDF has no extractable word boxes")
        max_y = 792.0
    else:
        max_y = max(y for y, _ in words)
        if 792.0 - max_y < 20.0:
            failures.append(f"PDF text bottom safety margin is only {792.0 - max_y:.2f} points; require at least 20")
    text = " ".join(word for _, word in words)
    for token in ("Kill rule:", "Stop if capacity or ownership is unavailable.", "Rendered internal candidate", "HUMAN PROJECT ROOM APPROVAL REQUIRED"):
        if token.lower() not in text.lower():
            failures.append(f"bottom content missing from PDF text: {token}")

    image = Image.open(args.png).convert("RGB")
    width, height = image.size
    if (width, height) != (1275, 1650):
        failures.append(f"unexpected 150 dpi image dimensions: {width}x{height}")
    bottom_rows = image.crop((0, max(0, height - 18), width, height))
    mean = ImageStat.Stat(bottom_rows).mean
    if min(mean) < 245:
        failures.append(f"bottom 18-pixel gutter is not clean white: RGB means {mean}")
    last_dark_row = -1
    for y in range(height):
        dark = 0
        for x in range(0, width, 5):
            pixel = cast(tuple[int, int, int], image.getpixel((x, y)))
            r, g, b = pixel
            if max(r, g, b) < 100:
                dark += 1
        if dark > width // 100:
            last_dark_row = y
    raster_margin = height - 1 - last_dark_row
    if raster_margin < 18:
        failures.append(f"dark footer ends only {raster_margin} pixels above page edge; require at least 18")

    if failures:
        for item in failures:
            print(f"WHY: {item}")
        return 1
    print(f"PASS: one-pager bottom is protected by {792.0 - max_y:.2f} PDF points and {raster_margin} raster pixels with complete Fix Card and footer text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
