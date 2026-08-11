#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

WINDOWS = [5, 10, 15, 20, 30]
PARTIAL_FORMULA = (
    "population + 0.35 * children_under_18 + 0.30 * population_40_to_64 "
    "+ 0.60 * population_65_plus"
)
REQUIRED_FILES = (
    "build_catchment_growth.py",
    "catchment_demographics.json",
    "catchment_windows.geojson",
    "growth_evidence.json",
    "source_receipts.json",
    "catchment_method.md",
    "run-summary.md",
)


def why(message: str) -> None:
    print(f"WHY: {message}")


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
        catch = json.loads((args.dir / "catchment_demographics.json").read_text())
        geo = json.loads((args.dir / "catchment_windows.geojson").read_text())
        growth = json.loads((args.dir / "growth_evidence.json").read_text())
        receipts = json.loads((args.dir / "source_receipts.json").read_text())
    except Exception as exc:
        why(f"JSON parse failed: {exc}")
        return 1

    origin = (catch.get("subject") or {}).get("public_origin") or {}
    if not close(float(origin.get("latitude", math.nan)), 40.6049094, tol=0.000001):
        failures.append("subject origin latitude does not match the direct Google Maps receipt")
    if not close(float(origin.get("longitude", math.nan)), -89.467024, tol=0.000001):
        failures.append("subject origin longitude does not match the direct Google Maps receipt")
    rows = catch.get("windows") or []
    if [row.get("minutes") for row in rows] != WINDOWS:
        failures.append(f"catchment windows must be {WINDOWS}")
    if catch.get("canonical_full_vdu") is not None:
        failures.append("canonical_full_vdu must remain null")
    partial = catch.get("partial_diagnostic") or {}
    if partial.get("label") != "partial_diagnostic_not_canonical_vdu":
        failures.append("partial diagnostic label is missing or wrong")
    if partial.get("formula") != PARTIAL_FORMULA:
        failures.append("partial diagnostic formula is not the required four-term expression")
    omitted = set(partial.get("omitted_canonical_terms") or [])
    for term in ("diabetes_prevalence_indexed_population", "commercial_pay_indexed_population"):
        if term not in omitted:
            failures.append(f"partial diagnostic must name omitted term: {term}")

    prior_pop = prior_households = -1.0
    partial_rows = {row.get("minutes"): row for row in partial.get("windows") or []}
    for row in rows:
        minutes = row.get("minutes")
        try:
            pop = float(row["population_raw"])
            households = float(row["households_raw"])
            child = float(row["children_under_18_raw"])
            age40 = float(row["population_40_to_64_raw"])
            age65 = float(row["population_65_plus_raw"])
        except Exception as exc:
            failures.append(f"window {minutes} missing numeric demographic fields: {exc}")
            continue
        if pop <= prior_pop or households <= prior_households:
            failures.append(f"window {minutes} population and households must increase strictly")
        prior_pop, prior_households = pop, households
        if pop <= 0 or households <= 0 or min(child, age40, age65) < 0:
            failures.append(f"window {minutes} has impossible nonpositive demographics")
        if child > pop or age40 > pop or age65 > pop or child + age40 + age65 > pop * 1.01:
            failures.append(f"window {minutes} age bands exceed population")
        if row.get("acs_vintage") != "2024 ACS 5-year":
            failures.append(f"window {minutes} missing 2024 ACS 5-year vintage")
        if row.get("allocation_method") != "area_weighted_block_group_intersection_epsg5070":
            failures.append(f"window {minutes} has wrong allocation method")
        source_ids = set(row.get("source_ids") or [])
        if not {
            "ACS2024_BG",
            "TIGER2024_BG",
            "VALHALLA_20260730",
            "GOOGLE_MAPS_SAMPLE_20260730",
        }.issubset(source_ids):
            failures.append(f"window {minutes} missing canonical source IDs")
        if row.get("diabetes_crude_pct") is not None and "CDC_PLACES_2025" not in source_ids:
            failures.append(f"window {minutes} diabetes value lacks CDC source ID")
        p = partial_rows.get(minutes) or {}
        expected = pop + 0.35 * child + 0.30 * age40 + 0.60 * age65
        if not close(float(p.get("value_raw", math.nan)), expected):
            failures.append(f"window {minutes} partial diagnostic does not recompute")
        if p.get("canonical_full_vdu") is not None:
            failures.append(f"window {minutes} partial row populated canonical VDU")

    features = geo.get("features") or []
    contours = sorted(int(f.get("properties", {}).get("contour_minutes")) for f in features)
    if contours != WINDOWS:
        failures.append(f"GeoJSON contours must be {WINDOWS}, got {contours}")
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in ("Polygon", "MultiPolygon") or not geometry.get("coordinates"):
            failures.append("GeoJSON contains an invalid or empty feature")

    pop_series = growth.get("population") or {}
    pop_records = pop_series.get("records") or []
    years = [record.get("year") for record in pop_records]
    if not {2020, 2021, 2022, 2023, 2024, 2025}.issubset(set(years)):
        failures.append("population series must cover 2020 through 2025")
    if pop_series.get("source_id") != "CENSUS_PEP_2025":
        failures.append("population series must use the Census PEP source")
    school = growth.get("school_enrollment") or {}
    school_records = school.get("records") or []
    observed_school_years = {record.get("school_year") for record in school_records}
    if not {"2022-2023", "2024-25", "2025-26"}.issubset(observed_school_years):
        failures.append("school series is missing a required first-party year")
    if school.get("source_id") != "MORTON709_FIRST_PARTY_ARCHIVE":
        failures.append("school series must use the archived/current first-party source")
    for series in (pop_series, school):
        for metric in series.get("growth_metrics") or []:
            start = float(metric["start_value"])
            end = float(metric["end_value"])
            expected = (end - start) / start * 100
            if not close(float(metric["percent_change"]), expected, tol=0.005):
                failures.append(f"growth metric does not recompute: {metric}")

    receipt_rows = receipts.get("receipts") or []
    ids = {row.get("source_id") for row in receipt_rows}
    for required in (
        "VALHALLA_20260730",
        "GOOGLE_MAPS_SAMPLE_20260730",
        "TIGER2024_BG",
        "ACS2024_BG",
        "CDC_PLACES_2025",
        "CENSUS_PEP_2025",
        "MORTON709_FIRST_PARTY_ARCHIVE",
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
        if not row.get("official_url") or not row.get("captured_at"):
            failures.append(f"receipt metadata incomplete: {row.get('source_id')}")

    method = (args.dir / "catchment_method.md").read_text()
    for phrase in (
        "area-weighted block-group intersection",
        "EPSG:5070",
        "not a patient-origin model",
        "not a true median",
        "Full VDU remains null",
        "partial diagnostic",
        "no live traffic",
    ):
        if phrase.lower() not in method.lower():
            failures.append(f"method note missing: {phrase}")
    for name in ("catchment_method.md", "run-summary.md"):
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
        "PASS: five isochrones, 2024 ACS catchment demographics, tract-weighted "
        "CDC context, official population and first-party enrollment growth, "
        "receipts, and the null full-VDU boundary all verify"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
