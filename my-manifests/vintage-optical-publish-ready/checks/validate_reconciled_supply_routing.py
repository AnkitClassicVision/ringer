#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

WINDOWS = [5, 10, 15, 20, 30]
REQUIRED_FILES = (
    "build_reconciled_supply_routing.py",
    "supply_geocoded_candidates.json",
    "routing_corrected.json",
    "visibility_reputation_reconciled.json",
    "missing_evidence.json",
    "source_receipts.json",
    "supply-routing-method.md",
    "run-summary.md",
)


def why(message: str) -> None:
    print(f"WHY: {message}")


def close(a: float, b: float, tol: float = 0.02) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=tol)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()
    failures: list[str] = []

    for name in REQUIRED_FILES:
        p = args.dir / name
        if not p.is_file() or p.stat().st_size == 0:
            failures.append(f"missing or empty file: {name}")
    if failures:
        for item in failures:
            why(item)
        return 1

    try:
        supply = json.loads((args.dir / "supply_geocoded_candidates.json").read_text())
        routes = json.loads((args.dir / "routing_corrected.json").read_text())
        vis = json.loads((args.dir / "visibility_reputation_reconciled.json").read_text())
        gaps = json.loads((args.dir / "missing_evidence.json").read_text())
        receipts = json.loads((args.dir / "source_receipts.json").read_text())
    except Exception as exc:
        why(f"JSON parse failed: {exc}")
        return 1

    if supply.get("status") != "candidate_geocode_complete_canonical_office_census_incomplete":
        failures.append("supply packet has the wrong truthful status")
    if supply.get("canonical_office_count") is not None:
        failures.append("canonical office count must remain null")
    expected_counts = {
        "source_reported_result_count_total": 40,
        "materialized_provider_candidate_count": 39,
        "office_candidate_count": 24,
        "geocoder_matched_count": 21,
        "geocoder_no_match_count": 3,
    }
    for key, value in expected_counts.items():
        if supply.get(key) != value:
            failures.append(f"{key} must be {value}, got {supply.get(key)}")

    candidates = supply.get("location_candidates") or []
    if len(candidates) != 24:
        failures.append("location candidate count must remain 24")
    matched = [row for row in candidates if row.get("geocode_status") == "Match"]
    no_match = [row for row in candidates if row.get("geocode_status") == "No_Match"]
    if len(matched) != 21 or len(no_match) != 3:
        failures.append("candidate geocode statuses do not reconcile to 21 matched and 3 no-match")
    if any(row.get("latitude") is None or row.get("longitude") is None for row in matched):
        failures.append("matched candidate lacks coordinates")
    if any(row.get("latitude") is not None or row.get("longitude") is not None for row in no_match):
        failures.append("no-match candidate contains invented coordinates")
    legacy = [row for row in candidates if row.get("input_address", "").startswith("417 W JEFFERSON ST")]
    if len(legacy) != 1 or legacy[0].get("entity_resolution_status") != "legacy_subject_address_excluded_from_competitor_counts":
        failures.append("417 W Jefferson legacy subject address is not excluded correctly")

    counts = supply.get("catchment_candidate_counts") or []
    if [row.get("minutes") for row in counts] != WINDOWS:
        failures.append("candidate catchment counts must cover exactly 5, 10, 15, 20, 30 minutes")
    previous = -1
    for row in counts:
        value = row.get("nppes_candidate_location_count")
        if not isinstance(value, int) or value < previous:
            failures.append("NPPES candidate location counts must be nonnegative and monotonic")
        previous = value if isinstance(value, int) else previous
        if row.get("canonical_office_count") is not None:
            failures.append("a candidate window populated canonical office count")

    origin = routes.get("origin") or {}
    if not close(float(origin.get("latitude", math.nan)), 40.6049094, 0.000001):
        failures.append("routing origin latitude does not match the direct Google listing")
    if not close(float(origin.get("longitude", math.nan)), -89.467024, 0.000001):
        failures.append("routing origin longitude does not match the direct Google listing")
    table_routes = routes.get("candidate_table_routes") or []
    if len(table_routes) != 21:
        failures.append("OSRM candidate table must contain 21 matched destinations")
    focus = routes.get("named_peer_routes", {}).get("focus_on_eyes") or {}
    if focus.get("endpoint_basis") != "direct_google_listing_pins":
        failures.append("Focus route must use direct Google listing pins")
    if not close(float(focus.get("duration_seconds", math.nan)), 233.4, 0.1):
        failures.append("Focus route seconds do not match the frozen OSRM receipt")
    if not close(float(focus.get("duration_minutes", math.nan)), 3.89, 0.01):
        failures.append("Focus route minutes must display as 3.89")
    if not close(float(focus.get("distance_miles", math.nan)), 1.53, 0.01):
        failures.append("Focus route miles must display as 1.53")
    superseded = routes.get("superseded_claims") or []
    if not any(row.get("prior_display") == "4.07 routed minutes" and row.get("status") == "superseded" for row in superseded):
        failures.append("the old 4.07-minute route is not explicitly superseded")

    if vis.get("cross_platform_review_total") is not None:
        failures.append("cross-platform review total must remain null")
    if vis.get("rank_grid", {}).get("status") != "not_run":
        failures.append("rank grid must remain not_run")
    focus_google = vis.get("direct_google_observations", {}).get("focus_on_eyes") or {}
    vintage_card = vis.get("direct_google_observations", {}).get("vintage_peer_card") or {}
    if focus_google.get("rating") != 4.8 or focus_google.get("review_count") != 182:
        failures.append("direct Focus Google observation must be 4.8 and 182")
    if vintage_card.get("rating") != 4.9 or vintage_card.get("review_count") != 348:
        failures.append("direct Vintage peer-card observation must be 4.9 and 348")
    discrepancies = vis.get("aggregator_discrepancies") or []
    needed = {("Vintage Optical", 398, 348, 50), ("Focus On Eyes", 210, 182, 28)}
    observed = {
        (row.get("entity"), row.get("birdeye_google_component"), row.get("direct_google_count"), row.get("difference"))
        for row in discrepancies
    }
    if not needed.issubset(observed):
        failures.append("Birdeye versus direct Google count discrepancies do not recompute")

    gap_rows = gaps.get("gaps") or []
    gap_ids = {row.get("gap_id") for row in gap_rows}
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
            failures.append(f"missing evidence register lacks {required}")
    for row in gap_rows:
        for field in ("field", "decision_impact", "attempted_sources", "exact_failure", "fallback_tried", "owner", "status", "upgrade_evidence"):
            if field not in row:
                failures.append(f"gap {row.get('gap_id')} lacks {field}")

    receipt_rows = receipts.get("receipts") or []
    ids = {row.get("source_id") for row in receipt_rows}
    for required in (
        "CENSUS_GEOCODER_20260730",
        "OSRM_TABLE_20260730",
        "OSRM_FOCUS_GOOGLE_PINS_20260730",
        "GOOGLE_MAPS_SAMPLE_20260730",
        "GOOGLE_MAPS_FOCUS_SAMPLE_20260730",
        "NPPES_CURRENT_20260730",
        "VALHALLA_20260730",
    ):
        if required not in ids:
            failures.append(f"source receipt missing: {required}")
    for row in receipt_rows:
        p = Path(row.get("path", ""))
        if not p.is_file():
            failures.append(f"receipt path missing: {p}")
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != row.get("sha256"):
            failures.append(f"receipt checksum mismatch: {p.name}")
        if not row.get("source_url") or not row.get("captured_at"):
            failures.append(f"receipt metadata incomplete: {row.get('source_id')}")

    method = (args.dir / "supply-routing-method.md").read_text()
    for phrase in (
        "NPPES records are not office counts",
        "canonical office count remains null",
        "21 matched",
        "3 no-match",
        "legacy subject address",
        "direct Google listing pins",
        "no live traffic",
        "A dated SERP sample is not a rank grid",
        "aggregator composition",
    ):
        if phrase.lower() not in method.lower():
            failures.append(f"method note missing: {phrase}")
    for name in ("supply-routing-method.md", "run-summary.md"):
        text = (args.dir / name).read_text()
        if "—" in text:
            failures.append(f"{name} contains an em dash")
        if "CANARY" in text:
            failures.append(f"{name} contains a canary")

    if failures:
        for item in failures:
            why(item)
        return 1
    print(
        "PASS: 24 NPPES-derived location candidates reconcile to 21 Census matches and "
        "3 no-matches, the legacy subject address is excluded, corrected routing uses "
        "direct listing pins, review sources remain separated, and canonical office "
        "count stays null"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
