#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import math
import re
import sys
from pathlib import Path

REQUIRED_COLORS = ("#1A242C", "#006064", "#00838F", "#00ACC1", "#D3AF5E", "#F4F6F8")
REQUIRED_SCORES = {
    "Market Demand-Supply": 61,
    "Competitive Pressure": 57,
    "Room to Win": 43,
    "Practice Competitiveness": 61,
    "Client Opportunity": 54,
    "Digital Presence": 60,
    "Dry eye": 53,
    "Myopia management": 53,
    "Specialty contact lenses": 51,
}
CATCHMENT_ROWS = (
    ("5 min", "6,624", "2,722", "1,712", "1,811", "1,311", "9.6%"),
    ("10 min", "19,322", "7,873", "4,571", "5,843", "4,291", "10.9%"),
    ("15 min", "54,768", "23,793", "11,707", "17,431", "10,939", "12.4%"),
    ("20 min", "173,058", "75,244", "38,652", "53,102", "32,473", "13.2%"),
    ("30 min", "283,661", "120,940", "64,831", "86,558", "53,258", "12.3%"),
)


def visible(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html.unescape(raw).split())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, type=Path)
    args = parser.parse_args()
    failures: list[str] = []
    if not args.path.is_file() or args.path.stat().st_size < 8000:
        print("WHY: onepager.html is missing or too small to implement the template")
        return 1
    raw = args.path.read_text(encoding="utf-8")
    text = visible(raw)

    if "@page" not in raw or "size: Letter" not in raw:
        failures.append("missing fixed Letter print geometry")
    page_rule = re.search(r"\.page\s*\{([^}]*)\}", raw, re.I | re.S)
    if not page_rule or not re.search(r"width\s*:\s*8\.5in", page_rule.group(1), re.I) or not re.search(r"height\s*:\s*11in", page_rule.group(1), re.I):
        failures.append("missing exact 8.5in by 11in page frame")
    else:
        bottom_padding = re.search(r"padding-bottom\s*:\s*([0-9.]+)in", page_rule.group(1), re.I)
        if not bottom_padding or float(bottom_padding.group(1)) < 0.12:
            failures.append("page must reserve at least 0.12in of white bottom safety gutter")
    read_rule = re.search(r"\.read\s*\{([^}]*)\}", raw, re.I | re.S)
    if not read_rule:
        failures.append("missing The Read layout rule")
    else:
        body = read_rule.group(1)
        basis = re.search(r"flex\s*:\s*0\s+0\s+([0-9.]+)in", body, re.I)
        minimum = re.search(r"min-height\s*:\s*([0-9.]+)in", body, re.I)
        heights = [float(m.group(1)) for m in (basis, minimum) if m]
        if not heights or max(heights) < 0.64:
            failures.append("The Read strip must reserve at least 0.64in so its full sentence is visible")
    for color in REQUIRED_COLORS:
        if color.lower() not in raw.lower():
            failures.append(f"missing template palette color {color}")
    for token in ("class=\"hero\"", "class=\"ring\"", "class=\"ring-center\"", "class=\"zones\"", "class=\"zone", "class=\"bar-track\"", "class=\"bar-fill"):
        if token not in raw:
            failures.append(f"missing template structure: {token}")
    if raw.count("<circle") < 2 or "viewBox=\"0 0 100 100\"" not in raw:
        failures.append("missing SVG circular gauge")
    dash = re.search(r"stroke-dasharray=\"([0-9.]+)\s+([0-9.]+)\"", raw)
    if not dash:
        failures.append("main gauge lacks a numeric stroke-dasharray")
    else:
        arc, circumference = map(float, dash.groups())
        if not math.isclose(circumference, 276.5, abs_tol=0.5) or not math.isclose(arc / circumference, 0.54, abs_tol=0.01):
            failures.append("main circular gauge does not encode Client Opportunity 54")
    if raw.count("class=\"bar-track\"") < 8 or raw.count("class=\"bar-fill") < 8:
        failures.append("fewer than eight colored score/lane meters")
    if "Client Opportunity Score" not in text or not re.search(r"\b54\b\s*/\s*100", text):
        failures.append("main gauge is not labeled Client Opportunity 54 / 100")

    for label, score in REQUIRED_SCORES.items():
        if label not in text:
            failures.append(f"missing score label {label}")
        window = re.search(re.escape(label) + r".{0,100}?\b" + str(score) + r"\b", text, re.I)
        if not window:
            failures.append(f"{label} does not display approved score {score}")
    if "Higher = more pressure" not in text or "Higher = better" not in text:
        failures.append("score direction cues are incomplete")
    if "Room to Win = 100 - 57 = 43" not in text:
        failures.append("exact Room-to-Win inversion is missing")

    for row in CATCHMENT_ROWS:
        for token in row:
            if token not in text:
                failures.append(f"catchment table lacks {token}")
    for token in (
        "The Read",
        "Your Market",
        "Your Competition",
        "Your Opportunity",
        "First 30 Days",
        "17,172",
        "17,565",
        "+2.29%",
        "3,238",
        "3,365",
        "+3.92%",
        "233.4 seconds",
        "3.89 minutes",
        "1.53 miles",
        "Vintage 4.9 / 348",
        "Focus 4.8 / 182",
        "Tri-County 4.9 / 271",
        "Walmart 3.5 / 8",
        "rank grid did not run",
        "canonical office count",
        "Full VDU",
        "Internal-only",
        "Project Room",
        "Rendered internal candidate",
    ):
        if token.lower() not in text.lower():
            failures.append(f"missing required visible content: {token}")
    for n in (1, 2, 3):
        if text.count(f"Fix Card {n}") != 1:
            failures.append(f"Fix Card {n} must appear exactly once")
    if "Fix Card 4" in text:
        failures.append("a fourth Fix Card appears")

    for forbidden in ("4.07", "1.56", "244.3", "/home/", "/mnt/", "file://", "Render pending", "CANARY"):
        if forbidden in raw or forbidden in text:
            failures.append(f"forbidden or stale content remains: {forbidden}")
    if "—" in text:
        failures.append("visible text contains an em dash")
    if "$" in text:
        failures.append("one-pager contains unsupported dollar projections")
    if "http://" in raw or "https://" in raw:
        failures.append("one-pager contains external URLs rather than a self-contained internal page")
    image_sources = re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", raw, re.I)
    if not image_sources or 'class="brand-logo"' not in raw:
        failures.append("one-pager lacks the approved embedded MyBCAT logo")
    elif any(not source.startswith("data:image/png;base64,") for source in image_sources):
        failures.append("one-pager contains a non-embedded image asset")

    if failures:
        for item in failures:
            print(f"WHY: {item}")
        return 1
    print("PASS: one-pager matches the MyBCAT template spine with a 54-point circular gauge, colored meters, full approved evidence, nine scores, and three Fix Cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
