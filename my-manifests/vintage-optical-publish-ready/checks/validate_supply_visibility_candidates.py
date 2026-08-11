#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

REQUIRED_FILES = (
    "build_supply_visibility_candidates.py",
    "supply_candidates.json",
    "census-geocoder-batch.csv",
    "local_visibility_reputation.json",
    "source_receipts.json",
    "supply-visibility-method.md",
    "run-summary.md",
)


def why(message: str) -> None:
    print(f"WHY: {message}")


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
        supply = json.loads((args.dir / "supply_candidates.json").read_text())
        visibility = json.loads((args.dir / "local_visibility_reputation.json").read_text())
        receipts = json.loads((args.dir / "source_receipts.json").read_text())
    except Exception as exc:
        why(f"JSON parse failed: {exc}")
        return 1

    if supply.get("canonical_office_count") is not None:
        failures.append("canonical office count must remain null before geocoding and entity resolution")
    if supply.get("status") != "candidate_census_geocoding_pending":
        failures.append("supply status must remain candidate_census_geocoding_pending")
    providers = supply.get("provider_records") or []
    if len(providers) != 39:
        failures.append(f"expected all 39 materialized NPPES candidate records, got {len(providers)}")
    if supply.get("source_reported_result_count_total") != 40:
        failures.append("source-reported NPPES query total must remain 40")
    if supply.get("materialized_record_count") != 39:
        failures.append("materialized NPPES record count must remain 39")
    gaps = supply.get("source_gap_register") or []
    matching_gaps = [
        row
        for row in gaps
        if row.get("city_query") == "Pekin"
        and row.get("taxonomy_query") == "Optometrist"
        and row.get("reported_result_count") == 11
        and row.get("materialized_record_count") == 10
        and row.get("deficit") == 1
        and row.get("status") == "unresolved_source_mismatch"
    ]
    if len(matching_gaps) != 1:
        failures.append("Pekin Optometrist one-record source deficit is not registered exactly once")
    public_ids: list[str] = []
    for row in providers:
        token = row.get("provider_public_id")
        if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{64}", token):
            failures.append("provider record lacks a SHA-256 public identifier")
        else:
            public_ids.append(token)
        if "npi" in row or "raw_npi" in row:
            failures.append("provider record exposes a raw NPI field")
        if row.get("record_type") not in (None, "nppes_provider_candidate"):
            failures.append("a source gap or placeholder was inserted into provider records")
        if not row.get("enumeration_type") or not row.get("practice_location"):
            failures.append("provider record lacks enumeration type or practice location")
    if len(set(public_ids)) != len(public_ids):
        failures.append("provider public identifiers are not unique")

    offices = supply.get("office_candidates") or []
    if not offices:
        failures.append("no office candidates were produced")
    batch_ids = []
    for row in offices:
        if row.get("geocode_status") != "pending_census_batch":
            failures.append("office candidate is not marked pending Census geocoding")
        if not row.get("normalized_address") or not row.get("provider_public_ids"):
            failures.append("office candidate lacks address or linked provider IDs")
        batch_ids.append(row.get("batch_id"))
    if len(batch_ids) != len(set(batch_ids)):
        failures.append("office candidate batch IDs are not unique")

    with (args.dir / "census-geocoder-batch.csv").open(newline="") as handle:
        batch_rows = list(csv.reader(handle))
    if len(batch_rows) != len(offices):
        failures.append("geocoder batch row count does not equal office candidate count")
    if any(len(row) != 5 for row in batch_rows):
        failures.append("each Census geocoder batch row must have five columns")
    if batch_rows and batch_rows[0][0].lower() in ("id", "batch_id", "unique_id"):
        failures.append("Census geocoder batch must not contain a header")
    if {row[0] for row in batch_rows} != set(batch_ids):
        failures.append("geocoder batch IDs do not reconcile to office candidates")

    preflight = visibility.get("dataforseo_preflight") or {}
    if preflight.get("status") != "unavailable_missing_credentials":
        failures.append("DataForSEO preflight status is not recorded accurately")
    if preflight.get("request_sent") is not False or preflight.get("cost_incurred") != 0:
        failures.append("DataForSEO preflight falsely implies a paid request or spend")
    rank_grid = visibility.get("rank_grid") or {}
    if rank_grid.get("status") != "not_run":
        failures.append("rank grid must remain not_run")
    if rank_grid.get("canonical_value") is not None:
        failures.append("rank grid canonical value must remain null")
    google = visibility.get("google_maps_sample") or {}
    if google.get("rating") != 4.9 or google.get("review_count") is not None:
        failures.append("Google sample must preserve 4.9 rating and null review count")
    if google.get("sample_type") != "dated_direct_observation_not_rank_grid":
        failures.append("Google observation is not labeled as a dated sample")
    if visibility.get("cross_platform_review_total") is not None:
        failures.append("cross-platform review total must remain null")
    observations = visibility.get("platform_observations") or []
    if not observations:
        failures.append("platform observations are missing")
    for row in observations:
        if not row.get("platform") or not row.get("source_id"):
            failures.append("platform observation lacks platform or source")
        if row.get("promoted_as_google_count") is True:
            failures.append("an aggregator count was promoted as a direct Google count")

    receipt_rows = receipts.get("receipts") or []
    ids = {row.get("source_id") for row in receipt_rows}
    for required in (
        "NPPES_CURRENT_20260730",
        "GOOGLE_MAPS_SAMPLE_20260730",
        "DATAFORSEO_PREFLIGHT_20260730",
        "BIRDEYE_AGGREGATOR_20260730",
    ):
        if required not in ids:
            failures.append(f"source receipt missing: {required}")
    for row in receipt_rows:
        path = Path(row.get("path", ""))
        if not path.is_file():
            failures.append(f"receipt path missing: {path}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != row.get("sha256"):
            failures.append(f"receipt checksum mismatch: {path.name}")
        if not row.get("source_url") or not row.get("captured_at"):
            failures.append(f"receipt metadata incomplete: {row.get('source_id')}")

    method = (args.dir / "supply-visibility-method.md").read_text()
    for phrase in (
        "NPPES records are not office counts",
        "geocoding pending",
        "entity resolution",
        "provider and office counts remain separate",
        "A dated SERP sample is not a rank grid",
        "platform-specific",
        "cross-platform",
        "review count remains null",
    ):
        if phrase.lower() not in method.lower():
            failures.append(f"method note missing: {phrase}")
    for name in ("supply-visibility-method.md", "run-summary.md"):
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
        "PASS: 39 materialized NPPES provider candidate records and the one-record "
        "Pekin source deficit remain separate from deduplicated "
        "geocoding-pending office candidates, while DataForSEO, Google, and "
        "platform-specific review limitations are represented truthfully"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
