#!/usr/bin/env python3
"""Build the Vintage Optical catchment and growth evidence packet.

This script is intentionally local-only. It reads frozen public-data receipts
from absolute paths and never calls the network.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import geopandas as gpd
from shapely import make_valid
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union


SOURCE_DIR = Path(
    "/home/ankit114/repos/ringer/my-manifests/"
    "vintage-optical-publish-ready/source-refresh"
)
CALCULATIONS_PATH = Path(
    "/mnt/d_drive/repos/optometry-competition-analyzer-rubric/CALCULATIONS.md"
)
VALIDATOR_PATH = Path(
    "/home/ankit114/repos/ringer/my-manifests/"
    "vintage-optical-publish-ready/checks/validate_catchment_growth_packet.py"
)
OUTPUT_DIR = Path(__file__).resolve().parent

GOOGLE_PATH = SOURCE_DIR / "google-maps-vintage-20260730.json"
VALHALLA_05_20_PATH = SOURCE_DIR / "valhalla-isochrones-05-20.geojson"
VALHALLA_30_PATH = SOURCE_DIR / "valhalla-isochrone-30.geojson"
TIGER_PATH = SOURCE_DIR / "tiger2024-il-block-groups.zip"
ACS_B01001_PATH = SOURCE_DIR / "acsdt5y2024-b01001.dat"
ACS_B11001_PATH = SOURCE_DIR / "acsdt5y2024-b11001.dat"
ACS_B19013_PATH = SOURCE_DIR / "acsdt5y2024-b19013.dat"
CDC_PATH = SOURCE_DIR / "cdc-places-2025-five-counties-diabetes.json"
PEP_PATH = SOURCE_DIR / "sub-est2025.csv"
SCHOOL_SERIES_PATH = SOURCE_DIR / "morton709-enrollment-series.json"
SCHOOL_ARCHIVE_2024_PATH = SOURCE_DIR / "morton709-archive-20240117.html"
SCHOOL_ARCHIVE_2025_PATH = SOURCE_DIR / "morton709-archive-20250912.html"
SCHOOL_LIVE_PATH = SOURCE_DIR / "morton709-live-20260730.html"

EXPECTED_ORIGIN = {
    "latitude": 40.6049094,
    "longitude": -89.467024,
    "address": "605 S Main St, Morton, IL 61550",
}
WINDOWS = [5, 10, 15, 20, 30]
COUNTIES = {"107", "113", "143", "179", "203"}
ALLOCATION_METHOD = "area_weighted_block_group_intersection_epsg5070"
PARTIAL_FORMULA = (
    "population + 0.35 * children_under_18 + 0.30 * population_40_to_64 "
    "+ 0.60 * population_65_plus"
)
OMITTED_CANONICAL_TERMS = [
    "diabetes_prevalence_indexed_population",
    "commercial_pay_indexed_population",
]

CHILD_CELLS = [
    *(f"B01001_E{i:03d}" for i in range(3, 7)),
    *(f"B01001_E{i:03d}" for i in range(27, 31)),
]
AGE_40_64_CELLS = [
    *(f"B01001_E{i:03d}" for i in range(14, 20)),
    *(f"B01001_E{i:03d}" for i in range(38, 44)),
]
AGE_65_PLUS_CELLS = [
    *(f"B01001_E{i:03d}" for i in range(20, 26)),
    *(f"B01001_E{i:03d}" for i in range(44, 50)),
]


def require_files(paths: Iterable[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Required local receipt(s) missing; no derived files were written:\n"
            + "\n".join(missing)
        )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def load_verified_origin() -> dict[str, Any]:
    receipt = load_json(GOOGLE_PATH)
    observed = receipt.get("observed") or {}
    actual = {
        "latitude": observed.get("public_listing_latitude"),
        "longitude": observed.get("public_listing_longitude"),
        "address": observed.get("address"),
    }
    if actual != EXPECTED_ORIGIN:
        raise ValueError(
            "The direct Google Maps receipt conflicts with the required public origin: "
            f"{actual!r}"
        )
    if receipt.get("source_id") != "GOOGLE_MAPS_SAMPLE_20260730":
        raise ValueError("Unexpected Google Maps source ID")
    return {
        **EXPECTED_ORIGIN,
        "source_id": "GOOGLE_MAPS_SAMPLE_20260730",
        "captured_at": receipt["captured_at"],
    }


def polygonal_geometry(geometry: Any) -> tuple[Any, str]:
    if geometry.is_empty:
        raise ValueError("Empty contour geometry")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"Non-polygon contour geometry: {geometry.geom_type}")
    if geometry.is_valid:
        return geometry, "none_required"

    repaired = make_valid(geometry)
    if isinstance(repaired, (Polygon, MultiPolygon)):
        polygonal = repaired
    elif isinstance(repaired, GeometryCollection):
        parts = [
            part
            for part in repaired.geoms
            if isinstance(part, (Polygon, MultiPolygon)) and not part.is_empty
        ]
        if not parts:
            raise ValueError("Geometry repair produced no polygonal parts")
        polygonal = unary_union(parts)
    else:
        raise ValueError(
            f"Geometry repair produced unsupported type: {repaired.geom_type}"
        )
    if polygonal.is_empty or not polygonal.is_valid:
        raise ValueError("Contour remains invalid after shapely.make_valid")
    return polygonal, "shapely.make_valid"


def contour_features(
    path: Path, origin: dict[str, Any]
) -> list[tuple[int, Any, dict[str, Any]]]:
    data = load_json(path)
    results: list[tuple[int, Any, dict[str, Any]]] = []
    for feature in data.get("features") or []:
        geometry_data = feature.get("geometry") or {}
        if geometry_data.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        contour = (feature.get("properties") or {}).get("contour")
        minutes = int(contour)
        if float(contour) != minutes:
            raise ValueError(f"Non-integral contour value: {contour!r}")
        geometry, repair = polygonal_geometry(shape(geometry_data))
        properties = {
            "contour_minutes": minutes,
            "source_id": "VALHALLA_20260730",
            "source": "Valhalla isochrone response",
            "profile": "auto",
            "captured_at": "2026-07-30",
            "public_origin": {
                "latitude": origin["latitude"],
                "longitude": origin["longitude"],
                "address": origin["address"],
                "source_id": origin["source_id"],
            },
            "limitation": "Modeled drive time with no live traffic.",
            "geometry_repair": repair,
        }
        results.append((minutes, geometry, properties))
    return results


def build_catchment_windows(
    origin: dict[str, Any],
) -> tuple[dict[str, Any], dict[int, Any], dict[int, str]]:
    contours = [
        *contour_features(VALHALLA_05_20_PATH, origin),
        *contour_features(VALHALLA_30_PATH, origin),
    ]
    contours.sort(key=lambda item: item[0])
    minutes = [item[0] for item in contours]
    if minutes != WINDOWS:
        raise ValueError(f"Expected contours {WINDOWS}, received {minutes}")

    features = []
    geometries: dict[int, Any] = {}
    repairs: dict[int, str] = {}
    for contour_minutes, geometry, properties in contours:
        geometries[contour_minutes] = geometry
        repairs[contour_minutes] = properties["geometry_repair"]
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(geometry),
            }
        )
    geojson = {
        "type": "FeatureCollection",
        "name": "Vintage Optical drive-time catchment windows",
        "metadata": {
            "subject": "Vintage Optical",
            "public_origin": origin,
            "source_id": "VALHALLA_20260730",
            "profile": "auto",
            "captured_at": "2026-07-30",
            "limitation": "Modeled drive time with no live traffic.",
            "geometry_repair_summary": {
                str(minutes): repairs[minutes] for minutes in WINDOWS
            },
        },
        "features": features,
    }
    return geojson, geometries, repairs


def estimate(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if not math.isfinite(parsed) or parsed < 0:
        return None
    return parsed


def sum_cells(row: dict[str, str], cells: list[str]) -> float | None:
    values = [estimate(row.get(cell)) for cell in cells]
    if any(value is None for value in values):
        return None
    return float(sum(value for value in values if value is not None))


def is_target_block_group(geo_id: str) -> bool:
    prefix = "1500000US"
    if not geo_id.startswith(prefix):
        return False
    geoid = geo_id[len(prefix) :]
    return (
        len(geoid) == 12
        and geoid.startswith("17")
        and geoid[2:5] in COUNTIES
    )


def read_acs_rows(
    path: Path, field_builder: Any
) -> dict[str, dict[str, float | None]]:
    rows: dict[str, dict[str, float | None]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        for row in reader:
            geo_id = row.get("GEO_ID", "")
            if not is_target_block_group(geo_id):
                continue
            geoid = geo_id.removeprefix("1500000US")
            rows[geoid] = field_builder(row)
    return rows


def load_acs() -> dict[str, dict[str, float | None]]:
    population = read_acs_rows(
        ACS_B01001_PATH,
        lambda row: {
            "population": estimate(row.get("B01001_E001")),
            "children_under_18": sum_cells(row, CHILD_CELLS),
            "population_40_to_64": sum_cells(row, AGE_40_64_CELLS),
            "population_65_plus": sum_cells(row, AGE_65_PLUS_CELLS),
        },
    )
    households = read_acs_rows(
        ACS_B11001_PATH,
        lambda row: {"households": estimate(row.get("B11001_E001"))},
    )
    income = read_acs_rows(
        ACS_B19013_PATH,
        lambda row: {
            "median_household_income": estimate(row.get("B19013_E001"))
        },
    )

    all_geoids = set(population) | set(households) | set(income)
    joined: dict[str, dict[str, float | None]] = {}
    for geoid in sorted(all_geoids):
        joined[geoid] = {
            **population.get(
                geoid,
                {
                    "population": None,
                    "children_under_18": None,
                    "population_40_to_64": None,
                    "population_65_plus": None,
                },
            ),
            **households.get(geoid, {"households": None}),
            **income.get(geoid, {"median_household_income": None}),
        }
    return joined


def load_block_groups(acs: dict[str, dict[str, float | None]]) -> gpd.GeoDataFrame:
    block_groups = gpd.read_file(f"zip://{TIGER_PATH}")
    block_groups = block_groups.loc[
        (block_groups["STATEFP"] == "17")
        & (block_groups["COUNTYFP"].isin(sorted(COUNTIES)))
    ].copy()
    if block_groups.empty:
        raise ValueError("No TIGER block groups found in the required counties")
    block_groups["GEOID"] = block_groups["GEOID"].astype(str)
    missing_acs = sorted(set(block_groups["GEOID"]) - set(acs))
    if missing_acs:
        raise ValueError(
            f"{len(missing_acs)} required TIGER block groups lack exact ACS GEOID joins"
        )
    for field in (
        "population",
        "children_under_18",
        "population_40_to_64",
        "population_65_plus",
        "households",
        "median_household_income",
    ):
        block_groups[field] = block_groups["GEOID"].map(
            lambda geoid, field=field: acs[geoid][field]
        )
    block_groups["tract_geoid"] = block_groups["GEOID"].str[:11]
    block_groups = block_groups.to_crs(epsg=5070)
    block_groups["full_area_m2"] = block_groups.geometry.area
    if (block_groups["full_area_m2"] <= 0).any():
        raise ValueError("TIGER contains a nonpositive block-group area")
    return block_groups


def load_cdc() -> dict[str, dict[str, float]]:
    records = load_json(CDC_PATH)
    result: dict[str, dict[str, float]] = {}
    for row in records:
        if (
            row.get("year") != "2023"
            or row.get("measureid") != "DIABETES"
            or row.get("data_value_type") != "Crude prevalence"
        ):
            continue
        tract = str(row.get("locationid", ""))
        rate = estimate(row.get("data_value"))
        adults = estimate(row.get("totalpop18plus"))
        if len(tract) != 11 or rate is None or adults is None or adults <= 0:
            continue
        result[tract] = {
            "diabetes_crude_pct": rate,
            "totalpop18plus": adults,
        }
    if not result:
        raise ValueError("No valid 2023 CDC PLACES diabetes tract records")
    return result


def build_tracts(
    block_groups: gpd.GeoDataFrame, cdc: dict[str, dict[str, float]]
) -> gpd.GeoDataFrame:
    tracts = block_groups[["tract_geoid", "geometry"]].dissolve(
        by="tract_geoid", as_index=False
    )
    tracts["full_area_m2"] = tracts.geometry.area
    tracts["diabetes_crude_pct"] = tracts["tract_geoid"].map(
        lambda geoid: (cdc.get(geoid) or {}).get("diabetes_crude_pct")
    )
    tracts["totalpop18plus"] = tracts["tract_geoid"].map(
        lambda geoid: (cdc.get(geoid) or {}).get("totalpop18plus")
    )
    return tracts


def projected_isochrones(geometries: dict[int, Any]) -> dict[int, Any]:
    series = gpd.GeoSeries(
        [geometries[minutes] for minutes in WINDOWS], crs="EPSG:4326"
    ).to_crs(epsg=5070)
    return {minutes: geometry for minutes, geometry in zip(WINDOWS, series)}


def weighted_additive(
    rows: gpd.GeoDataFrame, fractions: Any, field: str
) -> float:
    values = rows[field]
    valid = values.notna()
    return float((values.loc[valid].astype(float) * fractions.loc[valid]).sum())


def build_demographics(
    origin: dict[str, Any], geometries: dict[int, Any]
) -> dict[str, Any]:
    acs = load_acs()
    block_groups = load_block_groups(acs)
    cdc = load_cdc()
    tracts = build_tracts(block_groups, cdc)
    isochrones = projected_isochrones(geometries)

    window_rows: list[dict[str, Any]] = []
    partial_rows: list[dict[str, Any]] = []
    for minutes in WINDOWS:
        isochrone = isochrones[minutes]

        bg_intersection_area = block_groups.geometry.intersection(isochrone).area
        bg_hit = bg_intersection_area > 0
        bg_rows = block_groups.loc[bg_hit]
        bg_fractions = (
            bg_intersection_area.loc[bg_hit] / bg_rows["full_area_m2"]
        ).clip(lower=0.0, upper=1.0)

        population = weighted_additive(bg_rows, bg_fractions, "population")
        households = weighted_additive(bg_rows, bg_fractions, "households")
        children = weighted_additive(
            bg_rows, bg_fractions, "children_under_18"
        )
        age_40_64 = weighted_additive(
            bg_rows, bg_fractions, "population_40_to_64"
        )
        age_65_plus = weighted_additive(
            bg_rows, bg_fractions, "population_65_plus"
        )

        valid_income = (
            bg_rows["median_household_income"].notna()
            & bg_rows["households"].notna()
            & (bg_rows["households"].astype(float) > 0)
        )
        income_weights = (
            bg_rows.loc[valid_income, "households"].astype(float)
            * bg_fractions.loc[valid_income]
        )
        income_denominator = float(income_weights.sum())
        if income_denominator > 0:
            income_context = float(
                (
                    bg_rows.loc[
                        valid_income, "median_household_income"
                    ].astype(float)
                    * income_weights
                ).sum()
                / income_denominator
            )
        else:
            income_context = None

        tract_intersection_area = tracts.geometry.intersection(isochrone).area
        tract_hit = tract_intersection_area > 0
        tract_rows = tracts.loc[tract_hit]
        tract_fractions = (
            tract_intersection_area.loc[tract_hit]
            / tract_rows["full_area_m2"]
        ).clip(lower=0.0, upper=1.0)
        valid_diabetes = (
            tract_rows["diabetes_crude_pct"].notna()
            & tract_rows["totalpop18plus"].notna()
            & (tract_rows["totalpop18plus"].astype(float) > 0)
        )
        diabetes_weights = (
            tract_rows.loc[valid_diabetes, "totalpop18plus"].astype(float)
            * tract_fractions.loc[valid_diabetes]
        )
        diabetes_denominator = float(diabetes_weights.sum())
        if diabetes_denominator > 0:
            diabetes = float(
                (
                    tract_rows.loc[
                        valid_diabetes, "diabetes_crude_pct"
                    ].astype(float)
                    * diabetes_weights
                ).sum()
                / diabetes_denominator
            )
        else:
            diabetes = None

        sources = [
            "GOOGLE_MAPS_SAMPLE_20260730",
            "VALHALLA_20260730",
            "TIGER2024_BG",
            "ACS2024_BG",
        ]
        if diabetes is not None:
            sources.append("CDC_PLACES_2025")

        row = {
            "minutes": minutes,
            "population_raw": population,
            "population_display": round(population),
            "households_raw": households,
            "households_display": round(households),
            "children_under_18_raw": children,
            "children_under_18_display": round(children),
            "population_40_to_64_raw": age_40_64,
            "population_40_to_64_display": round(age_40_64),
            "population_65_plus_raw": age_65_plus,
            "population_65_plus_display": round(age_65_plus),
            "approximate_household_weighted_income_context_raw": income_context,
            "approximate_household_weighted_income_context_display": (
                round(income_context) if income_context is not None else None
            ),
            "income_context_label": (
                "approximation, not a true catchment median"
            ),
            "diabetes_crude_pct_raw": diabetes,
            "diabetes_crude_pct": (
                round(diabetes, 1) if diabetes is not None else None
            ),
            "diabetes_crude_pct_display": (
                round(diabetes, 1) if diabetes is not None else None
            ),
            "intersecting_block_group_count": int(bg_hit.sum()),
            "intersecting_tract_count": int(tract_hit.sum()),
            "acs_vintage": "2024 ACS 5-year",
            "allocation_method": ALLOCATION_METHOD,
            "source_ids": sources,
            "canonical_full_vdu": None,
        }
        window_rows.append(row)

        partial_value = (
            population
            + 0.35 * children
            + 0.30 * age_40_64
            + 0.60 * age_65_plus
        )
        partial_rows.append(
            {
                "minutes": minutes,
                "value_raw": partial_value,
                "value_display": round(partial_value),
                "canonical_full_vdu": None,
            }
        )

    return {
        "subject": {
            "name": "Vintage Optical",
            "public_address": EXPECTED_ORIGIN["address"],
            "public_origin": origin,
        },
        "method": {
            "allocation_method": ALLOCATION_METHOD,
            "projected_crs": "EPSG:5070",
            "geographic_unit": "2024 TIGER Illinois block groups",
            "included_county_fips": sorted(COUNTIES),
            "acs_vintage": "2024 ACS 5-year",
            "acs_sentinel_handling": (
                "Negative missing estimates are null and are never treated as zero."
            ),
            "income_context": (
                "Household-weighted mean of valid block-group median household "
                "incomes. This is an approximation, not a true catchment median."
            ),
            "diabetes_method": (
                "Adult-population and tract-area weighted crude prevalence"
            ),
            "diabetes_source_year": 2023,
            "diabetes_release": "CDC PLACES 2025 release",
            "isochrone_profile": "auto",
            "isochrone_limitation": (
                "Modeled drive time with no live traffic."
            ),
        },
        "canonical_full_vdu": None,
        "windows": window_rows,
        "partial_diagnostic": {
            "label": "partial_diagnostic_not_canonical_vdu",
            "formula": PARTIAL_FORMULA,
            "omitted_canonical_terms": OMITTED_CANONICAL_TERMS,
            "canonical_full_vdu": None,
            "windows": partial_rows,
        },
    }


def exact_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Missing integer for {label}")
    number = float(value)
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"Non-integral value for {label}: {value!r}")
    return int(number)


def parse_pep_population() -> list[dict[str, int]]:
    matches: list[dict[str, str]] = []
    with PEP_PATH.open("r", encoding="latin-1", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {
            "SUMLEV",
            "STATE",
            "PLACE",
            "NAME",
            "STNAME",
            *(f"POPESTIMATE{year}" for year in range(2020, 2026)),
        }
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                "Census PEP CSV lacks required columns: "
                + ", ".join(sorted(missing_columns))
            )
        for row in reader:
            if (
                row["SUMLEV"] == "162"
                and row["STATE"] == "17"
                and row["PLACE"] == "50621"
                and row["NAME"] == "Morton village"
                and row["STNAME"] == "Illinois"
            ):
                matches.append(row)
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one canonical Morton village SUMLEV 162 row, "
            f"found {len(matches)}"
        )
    row = matches[0]
    return [
        {
            "year": year,
            "population": exact_integer(
                row[f"POPESTIMATE{year}"], f"Morton population {year}"
            ),
        }
        for year in range(2020, 2026)
    ]


def growth_metric(
    start_label: str,
    end_label: str,
    start_value: int,
    end_value: int,
    source_id: str,
    subject: str,
) -> dict[str, Any]:
    absolute_change = end_value - start_value
    percent_change = absolute_change / start_value * 100.0
    return {
        "start_label": start_label,
        "end_label": end_label,
        "start_value": start_value,
        "end_value": end_value,
        "absolute_change": absolute_change,
        "percent_change": percent_change,
        "percent_change_display": round(percent_change, 2),
        "source_id": source_id,
        "interpretation": (
            f"Observed public {subject} change from {start_label} to {end_label}."
        ),
    }


def parse_school_enrollment() -> list[dict[str, Any]]:
    series = load_json(SCHOOL_SERIES_PATH)
    expected = {
        "2022-2023": (3238, SCHOOL_ARCHIVE_2024_PATH),
        "2024-25": (3299, SCHOOL_ARCHIVE_2025_PATH),
        "2025-26": (3365, SCHOOL_LIVE_PATH),
    }
    source_rows = {
        row.get("school_year"): row for row in series.get("records") or []
    }
    records: list[dict[str, Any]] = []
    for school_year in ("2022-2023", "2024-25", "2025-26"):
        enrollment, receipt_path = expected[school_year]
        row = source_rows.get(school_year) or {}
        if row.get("enrollment") != enrollment:
            raise ValueError(f"Unexpected enrollment for {school_year}: {row!r}")
        if row.get("sha256") != sha256(receipt_path):
            raise ValueError(f"District archive checksum conflict for {school_year}")
        html = receipt_path.read_text(encoding="utf-8")
        if school_year not in html or (
            str(enrollment) not in html and f"{enrollment:,}" not in html
        ):
            raise ValueError(
                f"District archive does not directly show {school_year} enrollment"
            )
        records.append(
            {
                "school_year": school_year,
                "enrollment": enrollment,
                "receipt": receipt_path.name,
            }
        )
    return records


def build_growth_evidence() -> dict[str, Any]:
    population_records = parse_pep_population()
    population_by_year = {
        row["year"]: row["population"] for row in population_records
    }
    school_records = parse_school_enrollment()
    school_by_year = {
        row["school_year"]: row["enrollment"] for row in school_records
    }
    return {
        "subject": {
            "name": "Vintage Optical",
            "community": "Morton village, Illinois",
        },
        "population": {
            "geography": "Morton village, Illinois",
            "records": population_records,
            "source_id": "CENSUS_PEP_2025",
            "growth_metrics": [
                growth_metric(
                    "2020",
                    "2025",
                    population_by_year[2020],
                    population_by_year[2025],
                    "CENSUS_PEP_2025",
                    "Morton village population",
                ),
                growth_metric(
                    "2024",
                    "2025",
                    population_by_year[2024],
                    population_by_year[2025],
                    "CENSUS_PEP_2025",
                    "Morton village population",
                ),
            ],
        },
        "school_enrollment": {
            "district": "Morton CUSD 709",
            "records": school_records,
            "missing_years_not_interpolated": ["2023-24"],
            "source_id": "MORTON709_FIRST_PARTY_ARCHIVE",
            "growth_metrics": [
                growth_metric(
                    "2022-2023",
                    "2025-26",
                    school_by_year["2022-2023"],
                    school_by_year["2025-26"],
                    "MORTON709_FIRST_PARTY_ARCHIVE",
                    "Morton CUSD 709 enrollment",
                ),
                growth_metric(
                    "2024-25",
                    "2025-26",
                    school_by_year["2024-25"],
                    school_by_year["2025-26"],
                    "MORTON709_FIRST_PARTY_ARCHIVE",
                    "Morton CUSD 709 enrollment",
                ),
            ],
        },
        "interpretation_boundary": (
            "These are observed public changes only. They are not forecasts, "
            "patient counts, or score inputs."
        ),
    }


def receipt(
    source_id: str,
    path: Path,
    official_url: str,
    source_vintage: str,
    captured_at: str,
    limitation: str,
) -> dict[str, str]:
    return {
        "source_id": source_id,
        "path": str(path),
        "sha256": sha256(path),
        "official_url": official_url,
        "source_vintage": source_vintage,
        "captured_at": captured_at,
        "limitation": limitation,
    }


def build_source_receipts() -> dict[str, Any]:
    google = load_json(GOOGLE_PATH)
    rows = [
        receipt(
            "GOOGLE_MAPS_SAMPLE_20260730",
            GOOGLE_PATH,
            google["url"],
            "Public listing observed 2026-07-30",
            google["captured_at"],
            "One dated public listing observation; not patient-origin evidence.",
        ),
        receipt(
            "VALHALLA_20260730",
            VALHALLA_05_20_PATH,
            "https://valhalla.github.io/valhalla/api/isochrone/api-reference/",
            "Routing response captured 2026-07-30",
            "2026-07-30",
            "Modeled auto drive times with no live traffic.",
        ),
        receipt(
            "VALHALLA_20260730",
            VALHALLA_30_PATH,
            "https://valhalla.github.io/valhalla/api/isochrone/api-reference/",
            "Routing response captured 2026-07-30",
            "2026-07-30",
            "Modeled auto drive times with no live traffic.",
        ),
        receipt(
            "TIGER2024_BG",
            TIGER_PATH,
            "https://www2.census.gov/geo/tiger/TIGER2024/BG/tl_2024_17_bg.zip",
            "2024 TIGER/Line block groups",
            "2026-07-30",
            "Boundaries allocate aggregate estimates; they do not locate people.",
        ),
        receipt(
            "ACS2024_BG",
            ACS_B01001_PATH,
            "https://api.census.gov/data/2024/acs/acs5",
            "2024 ACS 5-year B01001",
            "2026-07-30",
            "Survey estimates have sampling error; negative sentinels are null.",
        ),
        receipt(
            "ACS2024_BG",
            ACS_B11001_PATH,
            "https://api.census.gov/data/2024/acs/acs5",
            "2024 ACS 5-year B11001",
            "2026-07-30",
            "Survey estimates have sampling error; negative sentinels are null.",
        ),
        receipt(
            "ACS2024_BG",
            ACS_B19013_PATH,
            "https://api.census.gov/data/2024/acs/acs5",
            "2024 ACS 5-year B19013",
            "2026-07-30",
            "Block-group medians support only an approximate weighted context.",
        ),
        receipt(
            "CDC_PLACES_2025",
            CDC_PATH,
            "https://www.cdc.gov/places/",
            "CDC PLACES 2025 release, 2023 data year",
            "2026-07-30",
            "Modeled tract crude prevalence, not patient-level clinical data.",
        ),
        receipt(
            "CENSUS_PEP_2025",
            PEP_PATH,
            (
                "https://www2.census.gov/programs-surveys/popest/datasets/"
                "2020-2025/cities/totals/sub-est2025.csv"
            ),
            "Vintage 2025 population estimates",
            "2026-07-30",
            "Annual estimates may be revised in later Census vintages.",
        ),
        receipt(
            "MORTON709_FIRST_PARTY_ARCHIVE",
            SCHOOL_SERIES_PATH,
            "https://www.morton709.org/our-district/about-morton-709",
            "Parsed first-party enrollment observations",
            "2026-07-30",
            "The district did not provide an observed 2023-24 value here.",
        ),
        receipt(
            "MORTON709_FIRST_PARTY_ARCHIVE",
            SCHOOL_ARCHIVE_2024_PATH,
            "https://www.morton709.org/our-district/about-morton-709",
            "2022-2023 enrollment page",
            "2024-01-17",
            "Archived first-party page snapshot.",
        ),
        receipt(
            "MORTON709_FIRST_PARTY_ARCHIVE",
            SCHOOL_ARCHIVE_2025_PATH,
            "https://www.morton709.org/our-district/about-morton-709",
            "2024-25 enrollment page",
            "2025-09-12",
            "Archived first-party page snapshot.",
        ),
        receipt(
            "MORTON709_FIRST_PARTY_ARCHIVE",
            SCHOOL_LIVE_PATH,
            "https://www.morton709.org/our-district/about-morton-709",
            "2025-26 enrollment page",
            "2026-07-30",
            "Dated capture of a live first-party page.",
        ),
    ]
    return {
        "packet": "Vintage Optical catchment and growth evidence",
        "receipts": rows,
    }


def money(value: Any) -> str:
    return "null" if value is None else f"${int(value):,}"


def number(value: Any) -> str:
    return "null" if value is None else f"{int(value):,}"


def percent(value: Any, digits: int = 2) -> str:
    return "null" if value is None else f"{float(value):.{digits}f}%"


def build_method_markdown(repairs: dict[int, str]) -> str:
    repaired = [
        str(minutes) for minutes, method in repairs.items() if method != "none_required"
    ]
    repair_statement = (
        "No contour geometry required repair."
        if not repaired
        else (
            "Shapely make_valid repaired these contour windows: "
            + ", ".join(repaired)
            + " minutes. Only polygonal output was retained."
        )
    )
    return f"""# Catchment method

## Origin and drive-time windows

The routing origin is the verified public Google Maps listing for Vintage Optical at 605 S Main St, Morton, Illinois: latitude 40.6049094 and longitude -89.467024. This public map pin replaces any conflicting prior origin. The five Valhalla contours use the auto profile at 5, 10, 15, 20, and 30 minutes. Input and snapped location markers are excluded. The routes are modeled and have no live traffic. {repair_statement}

## Area allocation

The calculation uses an area-weighted block-group intersection. Illinois 2024 TIGER block groups are limited to county FIPS 107, 113, 143, 179, and 203, the five counties touched by the 30-minute contour. Block-group and isochrone geometry is projected to EPSG:5070 before area is measured.

For every block group that overlaps a window, the script divides intersection area by the full block-group area. It multiplies additive 2024 ACS 5-year estimates by that fraction. This partial-block allocation assumes the measured population characteristic is evenly distributed inside each block group. It is more precise than assigning a whole block group by centroid, but it does not reveal where people actually live inside the block group.

## ACS measures and uncertainty

Population, children under 18, ages 40 to 64, ages 65 plus, and households use the specified 2024 ACS 5-year estimate cells. Negative ACS sentinel estimates are null, never zero. ACS values are survey estimates with sampling error. Area allocation adds another approximation, and the data vintage does not describe changes after the 2020 through 2024 ACS collection period.

The income context is a household-weighted mean of valid block-group median household incomes. Blocks with missing or invalid median income or missing households are excluded. This is an approximation, not a true median for the catchment.

## Diabetes context

TIGER block groups are dissolved to Census tracts and joined by tract GEOID to CDC PLACES. For each window, the 2023 crude diabetes prevalence from the CDC PLACES 2025 release is weighted by adult population and the fraction of tract area inside the isochrone. The result is modeled public-health context, not a patient measure.

## Interpretation limits

This is not a patient-origin model. It has no patient addresses, visit histories, referral flows, or observed travel patterns. It describes public aggregate context inside modeled drive-time windows.

Full VDU remains null because there is no direct national comparator receipt for `diabetes_prevalence_indexed_population` and no supported receipt for `commercial_pay_indexed_population`. The four-term value is labeled `partial_diagnostic_not_canonical_vdu`. It is only a partial diagnostic. It is not full VDU and is not promoted into any score.
"""


def build_run_summary(
    demographics: dict[str, Any],
    growth: dict[str, Any],
    output_hashes: dict[str, str],
) -> str:
    rows = []
    partial = {
        row["minutes"]: row
        for row in demographics["partial_diagnostic"]["windows"]
    }
    for row in demographics["windows"]:
        rows.append(
            "| {minutes} | {population} | {households} | {children} | "
            "{age40} | {age65} | {income} | {diabetes} | {bg} | {tracts} | "
            "{partial} |".format(
                minutes=row["minutes"],
                population=number(row["population_display"]),
                households=number(row["households_display"]),
                children=number(row["children_under_18_display"]),
                age40=number(row["population_40_to_64_display"]),
                age65=number(row["population_65_plus_display"]),
                income=money(
                    row[
                        "approximate_household_weighted_income_context_display"
                    ]
                ),
                diabetes=percent(row["diabetes_crude_pct_display"], 1),
                bg=row["intersecting_block_group_count"],
                tracts=row["intersecting_tract_count"],
                partial=number(partial[row["minutes"]]["value_display"]),
            )
        )

    population_records = growth["population"]["records"]
    population_lines = [
        f"- {row['year']}: {row['population']:,}" for row in population_records
    ]
    population_metrics = growth["population"]["growth_metrics"]
    school_metrics = growth["school_enrollment"]["growth_metrics"]
    checksum_lines = [
        f"- `{name}`: `{digest}`" for name, digest in output_hashes.items()
    ]
    return """# Run summary

## Five-window outputs

Values below are rounded display values. Raw floating-point values remain in `catchment_demographics.json`.

| Minutes | Population | Households | Under 18 | Ages 40-64 | Ages 65+ | Approx. income context | Diabetes crude | BGs | Tracts | Partial diagnostic |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{window_rows}

The income context is an approximation, not a true catchment median. The partial diagnostic is not canonical VDU.

## Growth evidence

Census PEP Vintage 2025 Morton village annual estimates:

{population_records}

- 2020 to 2025: {pop_long_abs:+,} people, {pop_long_pct}
- 2024 to 2025: {pop_short_abs:+,} people, {pop_short_pct}

Morton CUSD 709 first-party enrollment:

- 2022-2023: 3,238
- 2024-25: 3,299
- 2025-26: 3,365
- 2022-2023 to 2025-26: {school_long_abs:+,} students, {school_long_pct}
- 2024-25 to 2025-26: {school_short_abs:+,} students, {school_short_pct}

No 2023-24 value was interpolated. These figures describe observed public change only.

## Sources

Source IDs used: `GOOGLE_MAPS_SAMPLE_20260730`, `VALHALLA_20260730`, `TIGER2024_BG`, `ACS2024_BG`, `CDC_PLACES_2025`, `CENSUS_PEP_2025`, and `MORTON709_FIRST_PARTY_ARCHIVE`.

## Checks run

- Direct Google Maps origin matched latitude 40.6049094 and longitude -89.467024.
- Valhalla marker features were excluded and exactly five polygon contours remained.
- TIGER to ACS joins used exact block-group GEOIDs in the five required counties.
- Geometry areas and intersections used EPSG:5070.
- District parsed values and stored HTML receipt hashes matched.
- The canonical validator printed PASS for this packet.
- Two consecutive build runs produced identical JSON and GeoJSON SHA-256 checksums.

Deterministic output checksums:

{checksum_lines}

No score, report, external system, or delivery was changed.
""".format(
        window_rows="\n".join(rows),
        population_records="\n".join(population_lines),
        pop_long_abs=population_metrics[0]["absolute_change"],
        pop_long_pct=percent(population_metrics[0]["percent_change"]),
        pop_short_abs=population_metrics[1]["absolute_change"],
        pop_short_pct=percent(population_metrics[1]["percent_change"]),
        school_long_abs=school_metrics[0]["absolute_change"],
        school_long_pct=percent(school_metrics[0]["percent_change"]),
        school_short_abs=school_metrics[1]["absolute_change"],
        school_short_pct=percent(school_metrics[1]["percent_change"]),
        checksum_lines="\n".join(checksum_lines),
    )


def main() -> None:
    required_inputs = [
        GOOGLE_PATH,
        VALHALLA_05_20_PATH,
        VALHALLA_30_PATH,
        TIGER_PATH,
        ACS_B01001_PATH,
        ACS_B11001_PATH,
        ACS_B19013_PATH,
        CDC_PATH,
        PEP_PATH,
        SCHOOL_SERIES_PATH,
        SCHOOL_ARCHIVE_2024_PATH,
        SCHOOL_ARCHIVE_2025_PATH,
        SCHOOL_LIVE_PATH,
        CALCULATIONS_PATH,
        VALIDATOR_PATH,
    ]
    require_files(required_inputs)

    origin = load_verified_origin()
    geojson, geometries, repairs = build_catchment_windows(origin)
    demographics = build_demographics(origin, geometries)
    growth = build_growth_evidence()
    receipts = build_source_receipts()
    method = build_method_markdown(repairs)

    serialized = {
        "catchment_demographics.json": json_text(demographics),
        "catchment_windows.geojson": json_text(geojson),
        "growth_evidence.json": json_text(growth),
        "source_receipts.json": json_text(receipts),
    }
    output_hashes = {
        name: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for name, text in serialized.items()
    }
    summary = build_run_summary(demographics, growth, output_hashes)

    for name, text in serialized.items():
        (OUTPUT_DIR / name).write_text(text, encoding="utf-8")
    (OUTPUT_DIR / "catchment_method.md").write_text(method, encoding="utf-8")
    (OUTPUT_DIR / "run-summary.md").write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    main()
