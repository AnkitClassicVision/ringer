#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import re
import sys
from pathlib import Path

EXPECTED_LOGO_SHA256 = "1e969dcafdefe20f809f4a393b6be0ca41a226ad5efeaa207d683a6c0fa36942"


def visible(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html.unescape(raw).split())


def embedded_logo_hashes(raw: str) -> list[str]:
    sources = re.findall(r'<img\b[^>]*class="[^"]*brand-logo[^"]*"[^>]*src="data:image/png;base64,([A-Za-z0-9+/=]+)"', raw, re.I | re.S)
    hashes = []
    for source in sources:
        hashes.append(hashlib.sha256(base64.b64decode(source)).hexdigest())
    return hashes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--variant", required=True, type=Path)
    parser.add_argument("--logo", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    failures: list[str] = []
    if hashlib.sha256(args.logo.read_bytes()).hexdigest() != EXPECTED_LOGO_SHA256:
        failures.append("approved logo source hash changed")

    raws = {}
    for name, path in (("current", args.current), ("variant", args.variant)):
        if not path.is_file() or path.stat().st_size < 100000:
            failures.append(f"{name} one-pager is missing or too small to embed the approved logo")
            continue
        raw = path.read_text(encoding="utf-8")
        raws[name] = raw
        hashes = embedded_logo_hashes(raw)
        if hashes != [EXPECTED_LOGO_SHA256]:
            failures.append(f"{name} one-pager does not embed exactly one byte-matched approved MyBCAT logo")
        if 'alt="MyBCAT logo"' not in raw or 'class="brand-logo"' not in raw:
            failures.append(f"{name} one-pager lacks accessible MyBCAT logo markup")
        if "http://" in raw or "https://" in raw or re.search(r'<img\b[^>]*src="(?!data:image/png;base64,)', raw, re.I):
            failures.append(f"{name} one-pager is not self-contained")
        page = re.search(r"\.page\s*\{([^}]*)\}", raw, re.I | re.S)
        if not page or not re.search(r"width\s*:\s*8\.5in", page.group(1), re.I) or not re.search(r"height\s*:\s*11in", page.group(1), re.I):
            failures.append(f"{name} one-pager lacks exact Letter page frame")
        if not page or not re.search(r"padding-bottom\s*:\s*0\.18in", page.group(1), re.I):
            failures.append(f"{name} one-pager lacks the proven 0.18in bottom safety gutter")

    current = raws.get("current", "")
    if current and args.baseline and args.baseline.is_file():
        if visible(current) != visible(args.baseline.read_text(encoding="utf-8")):
            failures.append("retained one-pager visible text changed while adding the logo")

    variant = raws.get("variant", "")
    text = visible(variant)
    for token in (
        "Vintage Optical",
        "Where Vintage Optical can win its next patient dollar",
        "Market support is real. Proof is the bottleneck.",
        "The Read",
        "Your Market",
        "Your Competition",
        "Your Opportunity",
        "First 30 Days",
        "Client Opportunity Score",
        "54 / 100",
        "Market Demand-Supply",
        "61 / 100",
        "Competitive Pressure",
        "57 / 100",
        "Room to Win",
        "43 / 100",
        "Practice Competitiveness",
        "Digital Presence",
        "60 / 100",
        "Dry eye 53",
        "Myopia management 53",
        "Specialty contact lenses 51",
        "Room to Win = 100 - 57 = 43",
        "173,058",
        "283,661",
        "+2.29%",
        "+3.92%",
        "Vintage 4.9 / 348",
        "Focus 4.8 / 182",
        "Tri-County 4.9 / 271",
        "Walmart 3.5 / 8",
        "Vintage leads review volume in this bounded same-page Google sample.",
        "Four proof-to-unlock growth tests, ranked by what to measure first.",
        "Visibility baseline",
        "Reputation source control",
        "Booking completion",
        "Specialty evidence",
        "Rank grid",
        "Source-specific baseline",
        "Funnel denominator",
        "Authorized economics",
        "Decision rule:",
        "Return with rank-grid visibility, source-controlled reputation, and a complete booking denominator.",
        "Approve the 30-day measurement sprint",
        "Internal-only",
        "Human Project Room approval required",
        "canonical office count",
        "Full VDU",
        "patient choice",
        "live traffic",
        "rank grid did not run",
    ):
        if token.lower() not in text.lower():
            failures.append(f"template-framed variant lacks required truthful message: {token}")
    if variant.count('class="growth-lane"') != 4:
        failures.append("template-framed variant must contain exactly four proof-to-unlock rows")
    for n in (1, 2, 3):
        if variant.count(f'data-fix-card="{n}"') != 1:
            failures.append(f"template-framed variant must contain Fix Card {n} exactly once")
    if "data-fix-card=\"4\"" in variant:
        failures.append("template-framed variant contains a fourth Fix Card")
    dash = re.search(r'stroke-dasharray="([0-9.]+)\s+([0-9.]+)"', variant)
    if not dash or abs(float(dash.group(1)) / float(dash.group(2)) - 0.54) > 0.01:
        failures.append("template-framed variant circular gauge does not encode 54")
    for forbidden in (
        "$",
        "own the lane",
        "winnable revenue",
        "combined directional upside",
        "competitors are weak",
        "no local competitor clearly owns",
        "cash-pay",
        "patient growth",
        "guaranteed",
        "4.07",
        "1.56",
        "244.3",
        "/home/",
        "/mnt/",
        "file://",
        "CANARY",
        "—",
    ):
        if forbidden.lower() in variant.lower() or forbidden.lower() in text.lower():
            failures.append(f"template-framed variant contains forbidden claim or text: {forbidden}")

    if failures:
        for item in failures:
            print(f"WHY: {item}")
        return 1
    print("PASS: retained one-pager preserves its visible content with the approved embedded logo, and the new template-framed variant uses the sample's persuasive spine without unsupported projections or claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
