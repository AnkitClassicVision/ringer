#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

REQUIRED_FILES = (
    "build_report.py",
    "render_report.py",
    "onepager.html",
    "number-explainer.md",
    "number-explainer.html",
    "scores.json",
    "sources.json",
    "source_inventory.json",
    "missing_evidence.json",
    "receipt_manifest.json",
    "number_inventory.json",
    "runlog.md",
    "report-update-contract.json",
    "build-summary.md",
)
EXPECTED_SCORES = {
    "market_demand_supply": ("Market Demand-Supply", 61, 60.50),
    "competitive_pressure_index": ("Competitive Pressure Index", 57, 56.75),
    "room_to_win": ("Room to Win", 43, 43.00),
    "practice_competitiveness": ("Practice Competitiveness", 61, 60.50),
    "client_opportunity": ("Client Opportunity", 54, 54.45),
    "digital_presence": ("Digital Presence", 60, 59.75),
    "dry_eye": ("Dry eye / ocular surface", 53, 53.00),
    "myopia_management": ("Myopia management", 53, 53.00),
    "specialty_contact_lenses": ("Specialty contact lenses", 51, 50.75),
}
REQUIRED_SOURCE_IDS = {
    "GOOGLE_MAPS_SAMPLE_20260730",
    "GOOGLE_MAPS_FOCUS_SAMPLE_20260730",
    "VALHALLA_20260730",
    "TIGER2024_BG",
    "ACS2024_BG",
    "CDC_PLACES_2025",
    "CENSUS_PEP_2025",
    "MORTON709_FIRST_PARTY_ARCHIVE",
    "NPPES_CURRENT_20260730",
    "CENSUS_GEOCODER_20260730",
    "OSRM_TABLE_20260730",
    "OSRM_FOCUS_GOOGLE_PINS_20260730",
    "DATAFORSEO_PREFLIGHT_20260730",
    "BIRDEYE_AGGREGATOR_20260730",
    "CATCHMENT_DEMOGRAPHICS_20260730",
}


def why(message: str) -> None:
    print(f"WHY: {message}")


def visible_text(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html.unescape(raw).split())


def half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def close(a: float, b: float, tol: float = 0.02) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=tol)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()
    failures: list[str] = []

    for name in REQUIRED_FILES:
        path = args.dir / name
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing or empty file: {name}")
    if failures:
        for item in failures:
            why(item)
        return 1

    try:
        scores = json.loads((args.dir / "scores.json").read_text())
        sources = json.loads((args.dir / "sources.json").read_text())
        inventory = json.loads((args.dir / "source_inventory.json").read_text())
        missing = json.loads((args.dir / "missing_evidence.json").read_text())
        receipts = json.loads((args.dir / "receipt_manifest.json").read_text())
        numbers = json.loads((args.dir / "number_inventory.json").read_text())
        contract = json.loads((args.dir / "report-update-contract.json").read_text())
    except Exception as exc:
        why(f"JSON parse failed: {exc}")
        return 1

    if scores.get("directionality_guard") != "Room to Win = 100 - Competitive Pressure Index":
        failures.append("scores.json lacks the exact Room-to-Win directionality guard")
    rows = scores.get("scores") or {}
    if set(rows) != set(EXPECTED_SCORES):
        failures.append("scores.json must contain exactly the nine approved score keys")
    for key, (name, display, full) in EXPECTED_SCORES.items():
        row = rows.get(key) or {}
        if row.get("display_name") != name or row.get("score") != display:
            failures.append(f"{key} display does not match approved score {display}")
        if not close(float(row.get("full_precision_total", math.nan)), full, 0.001):
            failures.append(f"{key} full-precision total must be {full}")
        if half_up(full) != display and key != "room_to_win":
            failures.append(f"{key} approved rounded display does not recompute")
        components = row.get("components") or []
        if key == "room_to_win":
            if row.get("formula") != "100 - Competitive Pressure Index":
                failures.append("Room to Win formula is wrong")
            continue
        if not components:
            failures.append(f"{key} lacks component recomputation")
            continue
        weight_sum = contribution_sum = 0.0
        for component in components:
            try:
                value = float(component["value"])
                weight = float(component["weight"])
                contribution = float(component["contribution"])
            except Exception as exc:
                failures.append(f"{key} component schema invalid: {exc}")
                continue
            if not close(contribution, value * weight, 0.011):
                failures.append(f"{key} component does not recompute: {component.get('component')}")
            weight_sum += weight
            contribution_sum += contribution
            if not component.get("source_ids") or not component.get("rationale"):
                failures.append(f"{key} component lacks sources or rationale")
        if not close(weight_sum, 1.0, 0.001):
            failures.append(f"{key} weights do not total 1")
        if not close(contribution_sum, full, 0.011):
            failures.append(f"{key} contributions do not total {full}")
    if rows.get("room_to_win", {}).get("score") != 100 - rows.get("competitive_pressure_index", {}).get("score", -999):
        failures.append("Room to Win display is not the exact CPI inversion")

    one_html = (args.dir / "onepager.html").read_text()
    explainer_html = (args.dir / "number-explainer.html").read_text()
    explainer_md = (args.dir / "number-explainer.md").read_text()
    one_text = visible_text(one_html)
    explainer_text = visible_text(explainer_html)
    all_client = "\n".join((one_text, explainer_text, explainer_md))
    for forbidden in ("/home/", "/mnt/", "file://", "C:\\Users\\", "CANARY"):
        if forbidden in all_client:
            failures.append(f"client-visible artifact leaks forbidden text: {forbidden}")
    if "—" in all_client:
        failures.append("client-visible artifacts contain an em dash")
    for stale in ("4.07", "1.56", "244.3"):
        if stale in all_client:
            failures.append(f"client-visible artifacts retain stale route number {stale}")

    one_required = (
        "61 / 100",
        "43 / 100",
        "54 / 100",
        "60 / 100",
        "173,058",
        "283,661",
        "2.29%",
        "3.92%",
        "3.89",
        "1.53",
        "4.9",
        "348",
        "4.8",
        "182",
        "Internal",
        "Project Room",
    )
    for token in one_required:
        if token not in one_text:
            failures.append(f"one-pager visible text lacks required token: {token}")
    for label, score in (("Dry eye", 53), ("Myopia management", 53), ("Specialty contact lenses", 51)):
        if not re.search(re.escape(label) + r".{0,120}?\b" + str(score) + r"\b", one_text, re.I):
            failures.append(f"one-pager does not display {label} with approved score {score}")
    for n in (1, 2, 3):
        if one_text.count(f"Fix Card {n}") != 1:
            failures.append(f"one-pager must contain Fix Card {n} exactly once")
    if "Fix Card 4" in one_text:
        failures.append("one-pager contains more than three Fix Cards")
    if "@page" not in one_html or "size: Letter" not in one_html:
        failures.append("one-pager lacks fixed Letter page CSS")

    explainer_required = (
        "6,624",
        "2,722",
        "19,322",
        "7,873",
        "54,768",
        "23,793",
        "173,058",
        "75,244",
        "283,661",
        "120,940",
        "17,172",
        "17,565",
        "393",
        "2.29%",
        "3,238",
        "3,365",
        "127",
        "3.92%",
        "233.4",
        "3.89",
        "1.53",
        "398",
        "348",
        "50",
        "210",
        "182",
        "28",
        "Room to Win = 100 - Competitive Pressure Index",
        "What we do not know",
        "Source dictionary",
        "Receipt manifest",
        "Full VDU remains null",
        "canonical office count remains null",
        "rank grid",
        "not run",
    )
    for token in explainer_required:
        if token.lower() not in explainer_text.lower() or token.lower() not in explainer_md.lower():
            failures.append(f"both explainers must contain: {token}")
    if "2023-24" not in explainer_text or "not interpolated" not in explainer_text.lower():
        failures.append("explainer does not preserve the missing 2023-24 enrollment boundary")

    source_rows = sources.get("sources") or []
    source_ids = {row.get("source_id") for row in source_rows}
    inventory_rows = inventory.get("sources") or []
    inventory_ids = {row.get("source_id") for row in inventory_rows}
    receipt_rows = receipts.get("receipts") or []
    receipt_ids = {row.get("source_id") for row in receipt_rows}
    for source_id in REQUIRED_SOURCE_IDS:
        if source_id not in source_ids:
            failures.append(f"sources.json lacks {source_id}")
        if source_id not in inventory_ids:
            failures.append(f"source_inventory.json lacks {source_id}")
        if source_id not in receipt_ids:
            failures.append(f"receipt_manifest.json lacks {source_id}")
    for row in source_rows:
        if not row.get("direct_url") or not row.get("claim_use") or not row.get("limitation"):
            failures.append(f"source dictionary entry incomplete: {row.get('source_id')}")
        if row.get("publication_authority") is False and row.get("used_for_substantive_fact") is True:
            failures.append(f"discovery-only source was promoted: {row.get('source_id')}")
    for row in receipt_rows:
        rel = row.get("path", "")
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts:
            failures.append(f"receipt path is not package-relative: {rel}")
            continue
        actual_path = args.dir / path
        if not actual_path.is_file():
            failures.append(f"receipt file missing: {rel}")
            continue
        actual = hashlib.sha256(actual_path.read_bytes()).hexdigest()
        if actual != row.get("sha256"):
            failures.append(f"receipt checksum mismatch: {rel}")

    gap_ids = {row.get("gap_id") for row in missing.get("gaps") or []}
    for required in (
        "GAP_OFFICE_CENSUS_INCOMPLETE",
        "GAP_NPPES_SOURCE_DEFICIT",
        "GAP_GEOCODER_NO_MATCHES",
        "GAP_RANK_GRID_NOT_RUN",
        "GAP_FULL_VDU_INCOMPLETE",
        "GAP_PROVIDER_ENTITY_DEDUPE",
        "GAP_LIVE_TRAFFIC",
    ):
        if required not in gap_ids:
            failures.append(f"missing_evidence.json lacks {required}")

    if numbers.get("substantive_lineage_coverage_percent") != 100:
        failures.append("number inventory is not 100% complete")
    if numbers.get("unexplained_substantive_number_count") != 0:
        failures.append("number inventory has unexplained substantive numbers")
    entries = numbers.get("entries") or []
    if not entries:
        failures.append("number inventory has no entries")
    for row in entries:
        if row.get("classification") == "substantive":
            for field in ("visible_value", "artifact", "meaning", "directionality", "source_or_formula", "confidence", "limitation"):
                if not row.get(field):
                    failures.append(f"substantive number inventory entry lacks {field}")

    if contract.get("status") != "APPROVED_FOR_INTERNAL_REBUILD_ONLY" or contract.get("external_delivery_authorized") is not False:
        failures.append("copied report-update contract is not the approved internal-only contract")
    runlog = (args.dir / "runlog.md").read_text()
    for phrase in (
        "external_actions_taken: none",
        "internal-only",
        "Project Room",
        "EVIDENCE_REVIEWED_REPORT_REBUILD_REQUIRED",
    ):
        if phrase.lower() not in runlog.lower():
            failures.append(f"runlog lacks: {phrase}")
    if "render pending" not in runlog.lower() and "render complete" not in runlog.lower():
        failures.append("runlog lacks a render state")

    if failures:
        for item in failures:
            why(item)
        return 1
    print(
        "PASS: rebuilt one-pager and explainer sources, nine scores, accepted facts, "
        "null gates, source dictionary, package receipts, and 100% number inventory "
        "verify before rendering"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
