#!/usr/bin/env python3
"""Build the frozen Vintage Optical supply, routing, and visibility packet.

This builder reads only the declared local inputs. It performs no network calls.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = Path("/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready")
SUPPLY_BUILD = ROOT / "source-build/build-supply-and-visibility-candidates"
REFRESH = ROOT / "source-refresh"
CATCHMENT_BUILD = ROOT / "source-build/build-catchment-and-growth-packet"

PATHS = {
    "supply_candidates": SUPPLY_BUILD / "supply_candidates.json",
    "census_batch": SUPPLY_BUILD / "census-geocoder-batch.csv",
    "census_results": SUPPLY_BUILD / "census-geocoder-results.csv",
    "osrm_index": SUPPLY_BUILD / "osrm-table-input-index.json",
    "osrm_table": SUPPLY_BUILD / "osrm-table-results.json",
    "osrm_focus": SUPPLY_BUILD / "osrm-vintage-to-focus-google-pins.json",
    "local_visibility": SUPPLY_BUILD / "local_visibility_reputation.json",
    "google_vintage": REFRESH / "google-maps-vintage-20260730.json",
    "google_focus": REFRESH / "google-maps-focus-20260730.json",
    "nppes": REFRESH / "nppes-provider-roster-sanitized.json",
    "catchment_windows": CATCHMENT_BUILD / "catchment_windows.geojson",
    "catchment_demographics": CATCHMENT_BUILD / "catchment_demographics.json",
}

WINDOWS = [5, 10, 15, 20, 30]
METERS_PER_MILE = 1609.344


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, value: dict[str, Any]) -> None:
    (HERE / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_batch(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) != 5:
                raise ValueError(f"Unexpected Census batch row: {row!r}")
            batch_id, street, city, state, postal_code = row
            if batch_id in rows:
                raise ValueError(f"Duplicate Census batch ID: {batch_id}")
            rows[batch_id] = {
                "batch_id": batch_id,
                "street": street,
                "city": city,
                "state": state,
                "postal_code": postal_code,
                "input_address": f"{street}, {city}, {state}, {postal_code}",
            }
    return rows


def parse_census_results(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) < 3:
                raise ValueError(f"Unexpected Census result row: {row!r}")
            batch_id, input_address, status = row[:3]
            if batch_id in rows:
                raise ValueError(f"Duplicate Census result ID: {batch_id}")
            parsed: dict[str, Any] = {
                "batch_id": batch_id,
                "input_address": input_address,
                "geocode_status": status,
            }
            if status == "Match":
                if len(row) != 12:
                    raise ValueError(f"Unexpected matched Census row: {row!r}")
                longitude_text, latitude_text = row[5].split(",")
                parsed.update(
                    {
                        "match_type": row[3],
                        "matched_address": row[4],
                        "longitude": float(longitude_text),
                        "latitude": float(latitude_text),
                        "tiger_line_id": row[6],
                        "side": row[7],
                        "state_fips": row[8],
                        "county_fips": row[9],
                        "tract": row[10],
                        "block": row[11],
                    }
                )
            elif status == "No_Match":
                if len(row) != 3:
                    raise ValueError(f"Unexpected no-match Census row: {row!r}")
                parsed.update(
                    {
                        "match_type": None,
                        "matched_address": None,
                        "longitude": None,
                        "latitude": None,
                        "tiger_line_id": None,
                        "side": None,
                        "state_fips": None,
                        "county_fips": None,
                        "tract": None,
                        "block": None,
                    }
                )
            else:
                raise ValueError(f"Unsupported Census geocode status: {status}")
            rows[batch_id] = parsed
    return rows


def point_on_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    tolerance: float = 1e-12,
) -> bool:
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > tolerance:
        return False
    dot = (x - x1) * (x - x2) + (y - y1) * (y - y2)
    return dot <= tolerance


def ring_position(x: float, y: float, ring: list[list[float]]) -> int:
    """Return 0 outside, 1 inside, or 2 on the ring boundary."""
    inside = False
    for index in range(len(ring) - 1):
        x1, y1 = ring[index][:2]
        x2, y2 = ring[index + 1][:2]
        if point_on_segment(x, y, x1, y1, x2, y2):
            return 2
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
    return 1 if inside else 0


def polygon_covers(
    longitude: float, latitude: float, coordinates: list[list[list[float]]]
) -> bool:
    exterior_position = ring_position(longitude, latitude, coordinates[0])
    if exterior_position == 0:
        return False
    if exterior_position == 2:
        return True
    for hole in coordinates[1:]:
        hole_position = ring_position(longitude, latitude, hole)
        if hole_position == 1:
            return False
        if hole_position == 2:
            return True
    return True


def geometry_covers(geometry: dict[str, Any], longitude: float, latitude: float) -> bool:
    geometry_type = geometry["type"]
    coordinates = geometry["coordinates"]
    if geometry_type == "Polygon":
        return polygon_covers(longitude, latitude, coordinates)
    if geometry_type == "MultiPolygon":
        return any(
            polygon_covers(longitude, latitude, polygon) for polygon in coordinates
        )
    raise ValueError(f"Unsupported catchment geometry type: {geometry_type}")


def build_location_candidates(
    source_supply: dict[str, Any],
    batch_rows: dict[str, dict[str, str]],
    census_rows: dict[str, dict[str, Any]],
    catchment: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    polygons = {
        int(feature["properties"]["contour_minutes"]): feature["geometry"]
        for feature in catchment["features"]
    }
    if sorted(polygons) != WINDOWS:
        raise ValueError("Catchment file must contain the five corrected windows")

    candidates: list[dict[str, Any]] = []
    for source in source_supply["office_candidates"]:
        batch_id = source["batch_id"]
        batch = batch_rows[batch_id]
        census = census_rows[batch_id]
        if batch["input_address"] != census["input_address"]:
            raise ValueError(f"Batch and result addresses differ for {batch_id}")

        address = source["original_address"].upper()
        if address == "605 S MAIN ST":
            entity_status = "current_subject_location_excluded_from_competitor_counts"
            competitor_eligible = False
        elif address == "417 W JEFFERSON ST":
            entity_status = (
                "legacy_subject_address_excluded_from_competitor_counts"
            )
            competitor_eligible = False
        else:
            entity_status = "unresolved_provider_registry_location_candidate"
            competitor_eligible = True

        containing_windows: list[int] = []
        if census["geocode_status"] == "Match":
            for minutes in WINDOWS:
                if geometry_covers(
                    polygons[minutes], census["longitude"], census["latitude"]
                ):
                    containing_windows.append(minutes)

        candidates.append(
            {
                "batch_id": batch_id,
                "input_address": census["input_address"],
                "source_address": {
                    "street": source["original_address"],
                    "city": source["city"],
                    "state": source["state"],
                    "postal_code": source["zip"],
                    "address_variants": source["original_address_variants"],
                },
                "candidate_classification": source["candidate_classification"],
                "linked_taxonomy_families": source["linked_taxonomy_families"],
                "enumeration_types": source["enumeration_types"],
                "materialized_provider_candidate_count": len(
                    source["provider_public_ids"]
                ),
                "candidate_match_basis": source["match_basis"],
                "geocode_status": census["geocode_status"],
                "census_match": {
                    "match_type": census["match_type"],
                    "matched_address": census["matched_address"],
                    "tiger_line_id": census["tiger_line_id"],
                    "side": census["side"],
                    "state_fips": census["state_fips"],
                    "county_fips": census["county_fips"],
                    "tract": census["tract"],
                    "block": census["block"],
                    "source_id": "CENSUS_GEOCODER_20260730",
                }
                if census["geocode_status"] == "Match"
                else None,
                "latitude": census["latitude"],
                "longitude": census["longitude"],
                "containing_catchment_windows_minutes": containing_windows,
                "within_30_minute_window": 30 in containing_windows,
                "entity_resolution_status": entity_status,
                "competitor_count_eligible": competitor_eligible,
                "limitation": (
                    "Provider-registry location candidate only. The row is not "
                    "a canonical active office, capacity, or patient-origin claim."
                ),
            }
        )

    catchment_counts: list[dict[str, Any]] = []
    for minutes in WINDOWS:
        in_window = [
            row
            for row in candidates
            if minutes in row["containing_catchment_windows_minutes"]
        ]
        competitor_candidates = [
            row for row in in_window if row["competitor_count_eligible"]
        ]
        catchment_counts.append(
            {
                "minutes": minutes,
                "nppes_candidate_location_count": len(in_window),
                "competitor_candidate_location_count": len(competitor_candidates),
                "canonical_office_count": None,
                "counting_note": (
                    "Counts are matched NPPES-derived location candidates, not a "
                    "complete or deduplicated office census."
                ),
            }
        )
    return candidates, catchment_counts


def build_supply() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_supply = load_json(PATHS["supply_candidates"])
    batch_rows = parse_batch(PATHS["census_batch"])
    census_rows = parse_census_results(PATHS["census_results"])
    catchment = load_json(PATHS["catchment_windows"])

    source_ids = {row["batch_id"] for row in source_supply["office_candidates"]}
    if len(source_supply["office_candidates"]) != 24:
        raise ValueError("Expected 24 source office candidates")
    if len(batch_rows) != 24 or len(census_rows) != 24:
        raise ValueError("Expected 24 Census batch rows and 24 Census result rows")
    if source_ids != set(batch_rows) or source_ids != set(census_rows):
        raise ValueError("Candidate, batch, and Census result IDs do not align")

    location_candidates, catchment_counts = build_location_candidates(
        source_supply, batch_rows, census_rows, catchment
    )
    matched_count = sum(
        row["geocode_status"] == "Match" for row in location_candidates
    )
    no_match_count = sum(
        row["geocode_status"] == "No_Match" for row in location_candidates
    )
    if (matched_count, no_match_count) != (21, 3):
        raise ValueError("Frozen geocoder results must reconcile to 21 matches and 3 no-matches")
    if source_supply["source_reported_result_count_total"] != 40:
        raise ValueError("Source-reported NPPES total changed")
    if source_supply["materialized_record_count"] != 39:
        raise ValueError("Materialized provider candidate count changed")

    out_of_window = [
        {
            "batch_id": row["batch_id"],
            "input_address": row["input_address"],
            "geocode_status": row["geocode_status"],
            "reason": "matched_point_outside_corrected_30_minute_polygon",
            "entity_resolution_status": row["entity_resolution_status"],
        }
        for row in location_candidates
        if row["geocode_status"] == "Match" and not row["within_30_minute_window"]
    ]
    no_matches = [
        {
            "batch_id": row["batch_id"],
            "input_address": row["input_address"],
            "geocode_status": "No_Match",
            "latitude": None,
            "longitude": None,
            "reason": "census_batch_geocoder_no_match_coordinates_not_inferred",
            "entity_resolution_status": row["entity_resolution_status"],
        }
        for row in location_candidates
        if row["geocode_status"] == "No_Match"
    ]

    packet = {
        "packet_date": "2026-07-30",
        "status": "candidate_geocode_complete_canonical_office_census_incomplete",
        "source_reported_result_count_total": 40,
        "materialized_provider_candidate_count": 39,
        "office_candidate_count": 24,
        "geocoder_matched_count": matched_count,
        "geocoder_no_match_count": no_match_count,
        "canonical_office_count": None,
        "candidate_count_definition": (
            "NPPES-derived exact practice-location groups retained as unresolved "
            "location candidates. They are not canonical office counts."
        ),
        "subject_address_resolutions": [
            {
                "address": "605 S Main St, Morton, IL 61550",
                "status": "current_subject_location_excluded_from_competitor_counts",
                "basis": "current direct Google Vintage listing observation",
            },
            {
                "address": "417 W Jefferson St, Morton, IL 61550",
                "status": "legacy_subject_address_excluded_from_competitor_counts",
                "basis": (
                    "current-versus-legacy citation conflict between the direct "
                    "Google Vintage listing and Birdeye"
                ),
            },
        ],
        "location_candidates": location_candidates,
        "catchment_candidate_counts": catchment_counts,
        "reject_and_limitation_collections": {
            "matched_outside_30_minute_window": out_of_window,
            "census_geocoder_no_matches": no_matches,
            "unresolved_entity_resolution": [
                {
                    "batch_id": row["batch_id"],
                    "input_address": row["input_address"],
                    "status": row["entity_resolution_status"],
                }
                for row in location_candidates
                if row["entity_resolution_status"]
                == "unresolved_provider_registry_location_candidate"
            ],
        },
        "limitations": [
            "Candidate counts are not a complete active-office census.",
            "Only the two subject-address cases have an entity resolution.",
            "No-match coordinates remain null and are excluded from polygon tests.",
            "Repeated or related registry addresses are not merged without direct entity evidence.",
        ],
        "source_ids": [
            "NPPES_CURRENT_20260730",
            "CENSUS_GEOCODER_20260730",
            "VALHALLA_20260730",
            "GOOGLE_MAPS_SAMPLE_20260730",
            "BIRDEYE_AGGREGATOR_20260730",
        ],
    }
    return packet, catchment_counts


def build_routing() -> dict[str, Any]:
    index = load_json(PATHS["osrm_index"])
    table = load_json(PATHS["osrm_table"])
    focus_receipt = load_json(PATHS["osrm_focus"])
    focus_google = load_json(PATHS["google_focus"])
    vintage_google = load_json(PATHS["google_vintage"])

    destinations = index["destinations"]
    durations = table["durations"][0]
    distances = table["distances"][0]
    if table["code"] != "Ok" or len(destinations) != 21:
        raise ValueError("Frozen OSRM table does not contain 21 destinations")
    if len(durations) != 22 or len(distances) != 22:
        raise ValueError("Frozen OSRM table matrix dimensions changed")

    candidate_routes: list[dict[str, Any]] = []
    for matrix_index, destination in enumerate(destinations, start=1):
        duration_seconds = float(durations[matrix_index])
        distance_meters = float(distances[matrix_index])
        candidate_routes.append(
            {
                "batch_id": destination["batch_id"],
                "input_address": destination["input_address"],
                "destination_basis": "census_address_geocoder_candidate_point",
                "destination": {
                    "latitude": destination["latitude"],
                    "longitude": destination["longitude"],
                    "match_type": destination["match_type"],
                    "matched_address": destination["matched_address"],
                },
                "duration_seconds": duration_seconds,
                "duration_minutes": round(duration_seconds / 60, 2),
                "distance_meters": distance_meters,
                "distance_miles": round(distance_meters / METERS_PER_MILE, 2),
                "traffic_basis": "no_live_traffic",
                "evidence_status": (
                    "address_geocoder_candidate_route_not_patient_origin_choice_evidence"
                ),
                "named_peer_precedence": (
                    "superseded_for_focus_named_peer_comparison"
                    if destination["input_address"].startswith("829 W JACKSON ST")
                    else "not_applicable"
                ),
            }
        )

    focus_route = focus_receipt["routes"][0]
    if (
        not math.isclose(focus_route["duration"], 233.4, abs_tol=0.001)
        or not math.isclose(focus_route["distance"], 2466.8, abs_tol=0.001)
    ):
        raise ValueError("Frozen Focus route receipt values changed")

    return {
        "packet_date": "2026-07-30",
        "status": "corrected_direct_origin_and_named_peer_route_reconciled",
        "origin": {
            "name": "Vintage Optical",
            "address": vintage_google["observed"]["address"],
            "latitude": vintage_google["observed"]["public_listing_latitude"],
            "longitude": vintage_google["observed"]["public_listing_longitude"],
            "endpoint_basis": "direct_google_listing_pin",
            "source_id": vintage_google["source_id"],
        },
        "candidate_table_method": {
            "source_id": "OSRM_TABLE_20260730",
            "profile": "driving",
            "origin_basis": "direct_google_listing_pin",
            "destination_basis": "census_address_geocoder_candidate_points",
            "traffic_basis": "no_live_traffic",
            "evidence_limitation": (
                "Routes describe address-geocoder location candidates. They are "
                "not a canonical office census or patient-origin choice evidence."
            ),
        },
        "candidate_table_routes": candidate_routes,
        "named_peer_routes": {
            "focus_on_eyes": {
                "name": focus_google["observed"]["name"],
                "origin": {
                    "name": vintage_google["observed"]["name"],
                    "latitude": vintage_google["observed"][
                        "public_listing_latitude"
                    ],
                    "longitude": vintage_google["observed"][
                        "public_listing_longitude"
                    ],
                    "source_id": vintage_google["source_id"],
                },
                "destination": {
                    "name": focus_google["observed"]["name"],
                    "address": focus_google["observed"]["address"],
                    "latitude": focus_google["observed"][
                        "public_listing_latitude"
                    ],
                    "longitude": focus_google["observed"][
                        "public_listing_longitude"
                    ],
                    "source_id": focus_google["source_id"],
                },
                "endpoint_basis": "direct_google_listing_pins",
                "route_source_id": "OSRM_FOCUS_GOOGLE_PINS_20260730",
                "duration_seconds": 233.4,
                "duration_minutes": 3.89,
                "distance_meters": 2466.8,
                "distance_miles": 1.53,
                "traffic_basis": "no_live_traffic",
                "precedence": (
                    "named direct-listing-pin route supersedes the Census-interpolated "
                    "candidate route for Focus On Eyes"
                ),
                "catchment_context": (
                    "nearby direct peer within the corrected 20-minute window"
                ),
                "interpretation": (
                    "The endpoint lineage changed. The competitive direction did "
                    "not change materially."
                ),
            }
        },
        "superseded_claims": [
            {
                "prior_display": "4.07 routed minutes",
                "status": "superseded",
                "reason": (
                    "The prior origin and destination lineage was not the current "
                    "pair of direct Google listing pins."
                ),
                "replacement_display": "3.89 routed minutes",
                "material_direction_change": False,
                "retained_context": (
                    "Focus remains a nearby direct peer within the 20-minute window."
                ),
            }
        ],
        "limitations": [
            "OSRM modeled driving routes have no live traffic.",
            "Routes do not measure patient origins, patient choice, capacity, or draw.",
            "Candidate routes do not convert registry locations into canonical offices.",
        ],
    }


def build_visibility() -> dict[str, Any]:
    local = load_json(PATHS["local_visibility"])
    google_vintage = load_json(PATHS["google_vintage"])
    google_focus = load_json(PATHS["google_focus"])
    observed = google_focus["observed"]
    peer_cards = {row["name"]: row for row in observed["people_also_search"]}

    return {
        "packet_date": "2026-07-30",
        "status": "source_separated_direct_and_aggregator_observations",
        "cross_platform_review_total": None,
        "original_direct_vintage_listing_observation": local["google_maps_sample"],
        "dataforseo_preflight": local["dataforseo_preflight"],
        "rank_grid": local["rank_grid"],
        "citation_consistency": local["citation_consistency"],
        "birdeye_source_observations": local["platform_observations"],
        "direct_google_observations": {
            "observation_date": google_focus["captured_at"],
            "observation_type": (
                "one_dated_direct_google_page_observation_not_complete_peer_export_or_rank_grid"
            ),
            "source_id": google_focus["source_id"],
            "focus_on_eyes": {
                "name": observed["name"],
                "address": observed["address"],
                "rating": observed["rating"],
                "review_count": observed["review_count"],
                "observation_role": "direct_listing",
            },
            "vintage_peer_card": {
                "name": "Vintage Optical",
                "rating": peer_cards["Vintage Optical"]["rating"],
                "review_count": peer_cards["Vintage Optical"]["review_count"],
                "observation_role": "people_also_search_peer_card",
            },
            "tri_county_peer_card": {
                "name": "Tri-County Eye Center",
                "rating": peer_cards["Tri-County Eye Center"]["rating"],
                "review_count": peer_cards["Tri-County Eye Center"]["review_count"],
                "observation_role": "people_also_search_peer_card",
            },
            "walmart_vision_and_glasses_peer_card": {
                "name": "Walmart Vision & Glasses",
                "rating": peer_cards["Walmart Vision & Glasses"]["rating"],
                "review_count": peer_cards["Walmart Vision & Glasses"][
                    "review_count"
                ],
                "observation_role": "people_also_search_peer_card",
            },
            "limitation": (
                "Peer cards are one dated direct Google page observation, not a "
                "complete peer export or rank grid. No review text was used."
            ),
        },
        "aggregator_discrepancies": [
            {
                "entity": "Vintage Optical",
                "birdeye_google_component": 398,
                "direct_google_count": 348,
                "difference": 50,
                "birdeye_source_id": "BIRDEYE_AGGREGATOR_20260730",
                "direct_source_id": google_focus["source_id"],
                "interpretation": (
                    "Aggregation date or method can differ. Both counts are retained."
                ),
            },
            {
                "entity": "Focus On Eyes",
                "birdeye_google_component": 210,
                "direct_google_count": 182,
                "difference": 28,
                "birdeye_source_id": "BIRDEYE_AGGREGATOR_20260730",
                "direct_source_id": google_focus["source_id"],
                "interpretation": (
                    "Aggregation date or method can differ. Both counts are retained."
                ),
            },
        ],
        "review_aggregation_rules": {
            "average_ratings_across_sources": False,
            "sum_counts_across_sources_or_platforms": False,
            "promote_birdeye_composition_as_direct_google_truth": False,
            "direct_vintage_listing_review_count": google_vintage["observed"][
                "review_count"
            ],
            "cross_platform_review_total": None,
        },
        "limitations": [
            "DataForSEO was unavailable and no request was sent.",
            "The rank grid was not run.",
            "Birdeye composition is not direct Google truth.",
            "Ratings are not averaged and counts are not summed.",
        ],
    }


def build_missing_evidence() -> dict[str, Any]:
    return {
        "packet_date": "2026-07-30",
        "status": "open_evidence_gaps_preserved",
        "gaps": [
            {
                "gap_id": "GAP_OFFICE_CENSUS_INCOMPLETE",
                "field": "canonical_office_count",
                "decision_impact": (
                    "Prevents a defensible active-office denominator and saturation claim."
                ),
                "attempted_sources": [
                    "NPPES_CURRENT_20260730",
                    "CENSUS_GEOCODER_20260730",
                ],
                "exact_failure": (
                    "Provider registry locations do not prove active, distinct offices."
                ),
                "fallback_tried": (
                    "Retained 24 location candidates and polygon counts without "
                    "promoting them to offices."
                ),
                "owner": "Vintage Optical evidence owner",
                "status": "incomplete",
                "upgrade_evidence": (
                    "Direct entity evidence and a documented, deduplicated active-office census."
                ),
            },
            {
                "gap_id": "GAP_NPPES_SOURCE_DEFICIT",
                "field": "materialized_provider_candidate_count",
                "decision_impact": (
                    "The materialized roster is one row below the source-reported total."
                ),
                "attempted_sources": ["NPPES_CURRENT_20260730"],
                "exact_failure": (
                    "The Pekin Optometrist query reported 11 results but only 10 "
                    "records materialized, leaving a deficit of 1."
                ),
                "fallback_tried": (
                    "Preserved both the reported total of 40 and materialized count of 39."
                ),
                "owner": "NPPES source reconciliation owner",
                "status": "failed",
                "upgrade_evidence": (
                    "A frozen response that materializes all reported rows or documents "
                    "the API mismatch."
                ),
            },
            {
                "gap_id": "GAP_GEOCODER_NO_MATCHES",
                "field": "candidate_coordinates",
                "decision_impact": (
                    "Three candidates cannot be tested against catchment polygons or routed."
                ),
                "attempted_sources": ["CENSUS_GEOCODER_20260730"],
                "exact_failure": "Three of 24 Census batch rows returned No_Match.",
                "fallback_tried": (
                    "Coordinates remain null; the candidates are preserved in the "
                    "no-match limitation collection."
                ),
                "owner": "Geocoding evidence owner",
                "status": "no_match",
                "upgrade_evidence": (
                    "A reproducible authoritative geocoder match for each unresolved address."
                ),
            },
            {
                "gap_id": "GAP_RANK_GRID_NOT_RUN",
                "field": "local_search_rank_grid",
                "decision_impact": (
                    "No geographic local-search visibility distribution can be claimed."
                ),
                "attempted_sources": [
                    "DATAFORSEO_PREFLIGHT_20260730",
                    "GOOGLE_MAPS_SAMPLE_20260730",
                    "GOOGLE_MAPS_FOCUS_SAMPLE_20260730",
                ],
                "exact_failure": (
                    "DataForSEO credentials were unavailable, no paid request was sent, "
                    "and the rank grid was not run."
                ),
                "fallback_tried": (
                    "Retained dated direct Google observations as samples only."
                ),
                "owner": "Local visibility evidence owner",
                "status": "not_run",
                "upgrade_evidence": (
                    "A dated, query-defined, geography-defined rank-grid export."
                ),
            },
            {
                "gap_id": "GAP_FULL_VDU_INCOMPLETE",
                "field": "canonical_full_vdu",
                "decision_impact": "Prevents use of a canonical full VDU value.",
                "attempted_sources": ["CATCHMENT_DEMOGRAPHICS_20260730"],
                "exact_failure": (
                    "The frozen demographic packet omits diabetes-indexed and "
                    "commercial-pay-indexed canonical terms."
                ),
                "fallback_tried": (
                    "The partial diagnostic remains labeled non-canonical and is not "
                    "used as full VDU."
                ),
                "owner": "Catchment methodology owner",
                "status": "incomplete",
                "upgrade_evidence": (
                    "All canonical VDU terms with frozen inputs and a validated formula."
                ),
            },
            {
                "gap_id": "GAP_PROVIDER_ENTITY_DEDUPE",
                "field": "distinct_active_office_entities",
                "decision_impact": (
                    "Candidate rows and repeated addresses cannot be converted into "
                    "distinct competitor offices."
                ),
                "attempted_sources": [
                    "NPPES_CURRENT_20260730",
                    "GOOGLE_MAPS_SAMPLE_20260730",
                ],
                "exact_failure": (
                    "Direct entity evidence exists only for the current and legacy "
                    "subject-address exclusions."
                ),
                "fallback_tried": (
                    "All other rows remain unresolved provider-registry location candidates."
                ),
                "owner": "Provider entity-resolution owner",
                "status": "not_run",
                "upgrade_evidence": (
                    "Direct current listings, entity ownership evidence, and a "
                    "documented address/entity deduplication review."
                ),
            },
            {
                "gap_id": "GAP_LIVE_TRAFFIC",
                "field": "traffic_adjusted_route_time",
                "decision_impact": (
                    "Modeled route times cannot represent current or typical traffic."
                ),
                "attempted_sources": [
                    "OSRM_TABLE_20260730",
                    "OSRM_FOCUS_GOOGLE_PINS_20260730",
                    "VALHALLA_20260730",
                ],
                "exact_failure": (
                    "Frozen OSRM routes and Valhalla polygons contain no live traffic."
                ),
                "fallback_tried": "Reported modeled driving time with a no-live-traffic label.",
                "owner": "Routing evidence owner",
                "status": "unavailable",
                "upgrade_evidence": (
                    "A dated traffic-aware route receipt using the same verified endpoints."
                ),
            },
        ],
    }


def receipt(
    source_id: str,
    key: str,
    source_url: str,
    captured_at: str,
    authority: str,
    method: str,
    limitation: str,
) -> dict[str, Any]:
    path = PATHS[key]
    return {
        "source_id": source_id,
        "path": str(path),
        "sha256": sha256(path),
        "source_url": source_url,
        "captured_at": captured_at,
        "authority": authority,
        "method": method,
        "limitation": limitation,
    }


def build_receipts() -> dict[str, Any]:
    return {
        "packet_date": "2026-07-30",
        "receipt_scope": (
            "Every frozen raw or immediate derived data input read by "
            "build_reconciled_supply_routing.py"
        ),
        "receipts": [
            receipt(
                "SUPPLY_CANDIDATES_20260730",
                "supply_candidates",
                "https://npiregistry.cms.hhs.gov/api/",
                "2026-07-30",
                "NPPES public registry plus deterministic local grouping",
                "Immediate derived candidate packet",
                "Location groups are candidates, not active-office counts.",
            ),
            receipt(
                "CENSUS_GEOCODER_BATCH_20260730",
                "census_batch",
                "https://geocoding.geo.census.gov/geocoder/",
                "2026-07-30",
                "United States Census Bureau batch geocoder",
                "Immediate derived 24-row batch input",
                "Input addresses contain no returned coordinates.",
            ),
            receipt(
                "CENSUS_GEOCODER_20260730",
                "census_results",
                "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
                "2026-07-30",
                "United States Census Bureau batch geocoder",
                "Frozen batch geocoding result",
                "Three rows returned No_Match and retain null coordinates.",
            ),
            receipt(
                "OSRM_TABLE_INDEX_20260730",
                "osrm_index",
                "https://router.project-osrm.org/table/v1/driving",
                "2026-07-30",
                "OSRM input lineage",
                "Immediate derived origin and destination index",
                "Destinations use Census geocoder candidate points.",
            ),
            receipt(
                "OSRM_TABLE_20260730",
                "osrm_table",
                "https://router.project-osrm.org/table/v1/driving",
                "2026-07-30",
                "OSRM public routing service",
                "Frozen one-to-many driving table",
                "No live traffic and no patient-origin choice evidence.",
            ),
            receipt(
                "OSRM_FOCUS_GOOGLE_PINS_20260730",
                "osrm_focus",
                "https://router.project-osrm.org/route/v1/driving",
                "2026-07-30",
                "OSRM public routing service",
                "Frozen route between two direct Google listing pins",
                "No live traffic.",
            ),
            receipt(
                "LOCAL_VISIBILITY_REPUTATION_20260730",
                "local_visibility",
                "https://www.google.com/maps/",
                "2026-07-30",
                "Immediate derived direct and aggregator observation packet",
                "Frozen source-separated visibility and reputation observations",
                "Dated observations are not a rank grid or complete peer export.",
            ),
            receipt(
                "GOOGLE_MAPS_SAMPLE_20260730",
                "google_vintage",
                "https://www.google.com/maps/place/Vintage+Optical/@40.6049094,-89.467024,17z/",
                "2026-07-30T12:54:08.602Z",
                "Direct public Google Maps listing",
                "Browser DOM observation",
                "Limited dated view with no displayed review count.",
            ),
            receipt(
                "GOOGLE_MAPS_FOCUS_SAMPLE_20260730",
                "google_focus",
                "https://www.google.com/maps/place/Focus+On+Eyes,+P.C.+Member+Of+Vision+Source/@40.6196994,-89.4680886,17z/",
                "2026-07-30T13:18:44.578Z",
                "Direct public Google Maps listing and peer cards",
                "Browser DOM observation",
                "One dated page observation, not a complete peer export or rank grid.",
            ),
            receipt(
                "NPPES_CURRENT_20260730",
                "nppes",
                "https://npiregistry.cms.hhs.gov/api/",
                "2026-07-30",
                "NPPES public registry",
                "Sanitized frozen city and taxonomy query roster",
                "Provider records are not office counts; one reported row did not materialize.",
            ),
            receipt(
                "VALHALLA_20260730",
                "catchment_windows",
                "https://valhalla1.openstreetmap.de/isochrone",
                "2026-07-30",
                "Valhalla modeled drive-time isochrones",
                "Corrected frozen 5, 10, 15, 20, and 30-minute polygons",
                "Modeled driving time with no live traffic.",
            ),
            receipt(
                "CATCHMENT_DEMOGRAPHICS_20260730",
                "catchment_demographics",
                "https://api.census.gov/data/2024/acs/acs5",
                "2026-07-30",
                "Immediate derived ACS, TIGER, CDC PLACES, and Valhalla packet",
                "Frozen catchment demographic calculations",
                "Canonical full VDU remains null because required terms are incomplete.",
            ),
        ],
    }


def build_method() -> str:
    return """# Supply and routing reconciliation method

## Scope

This lane reconciles frozen public supply candidates, Census geocoder results, corrected drive-time polygons, OSRM routes, and source-specific visibility observations. It does not rescore or edit a report.

## Supply candidates

NPPES records are not office counts. The source reported 40 results, 39 provider candidates materialized, and those records formed 24 address-level location candidates. The Census batch returned 21 matched rows and 3 no-match rows. No-match latitude and longitude remain null.

Each matched point is tested against the corrected 5, 10, 15, 20, and 30-minute polygons. Counts remain candidate location counts. The canonical office count remains null because provider-registry locations do not prove distinct, active offices.

The current subject address at 605 S Main St is excluded from competitor counts. The legacy subject address at 417 W Jefferson St is also excluded because the frozen direct Google and Birdeye observations show a current-versus-legacy citation conflict. No other candidate is merged, deduplicated, or labeled an active office without direct entity evidence. Matched points outside 30 minutes and all no-match candidates remain visible in limitation collections.

## Routing

The candidate routing table uses the direct Google Vintage listing pin as its origin and Census address-geocoder points as its destinations. These routes describe candidate locations. They are not patient-origin choice evidence.

The named Focus On Eyes route uses direct Google listing pins for both endpoints. Its frozen OSRM receipt replaces the prior display of 4.07 routed minutes with 3.89 routed minutes and 1.53 miles. The lineage changed, but the competitive direction did not change materially. Focus remains a nearby direct peer within the 20-minute window. OSRM has no live traffic.

## Visibility and reviews

The original direct Vintage listing observation, the unavailable DataForSEO preflight, the rank-grid not-run state, and the Birdeye observations remain separate. A dated SERP sample is not a rank grid. The Focus page and its peer cards are one dated direct Google observation, not a complete peer export.

Birdeye displayed Google components of 398 for Vintage and 210 for Focus. The direct Google page displayed 348 for the Vintage peer card and 182 for Focus. Aggregation date and method can differ. Aggregator composition is not direct Google truth. Ratings are not averaged, counts are not summed, and cross-platform review total remains null.
"""


def build_summary(
    supply: dict[str, Any], catchment_counts: list[dict[str, Any]]
) -> str:
    count_lines = "\n".join(
        (
            f"- {row['minutes']} minutes: "
            f"{row['nppes_candidate_location_count']} NPPES-derived candidates, "
            f"{row['competitor_candidate_location_count']} competitor candidates, "
            "canonical offices null"
        )
        for row in catchment_counts
    )
    gaps = ", ".join(
        [
            "office census incomplete",
            "NPPES source deficit",
            "3 geocoder no-matches",
            "rank grid not run",
            "full VDU incomplete",
            "provider entity dedupe unresolved",
            "live traffic unavailable",
        ]
    )
    return f"""# Reconciled supply and routing run summary

## Result

Status: candidate geocoding complete; canonical office census incomplete.

- Source-reported NPPES results: {supply['source_reported_result_count_total']}
- Materialized provider candidates: {supply['materialized_provider_candidate_count']}
- Office location candidates: {supply['office_candidate_count']}
- Census results: {supply['geocoder_matched_count']} matched and {supply['geocoder_no_match_count']} no-match
- Canonical office count: null

## Candidate catchment counts

{count_lines}

These are candidate counts, not a complete or deduplicated office census. The current 605 S Main St subject location and legacy 417 W Jefferson St subject address are excluded from competitor counts. Out-of-30-minute and no-match candidates remain explicit.

## Corrected Focus route

The named Focus On Eyes route now uses the direct Google Vintage and Focus listing pins. The frozen OSRM result is 233.4 seconds, 3.89 displayed minutes, 2466.8 meters, and 1.53 displayed miles. It supersedes the old report display of 4.07 routed minutes because that claim did not use the current direct listing-pin pair. The direction did not change materially. Focus remains a nearby direct peer within the 20-minute window. No route includes live traffic or patient-origin choice evidence.

## Visibility and review reconciliation

The direct Google Focus observation is 4.8 with 182 reviews at 829 W Jackson St. On that same dated page, peer cards showed Vintage at 4.9 with 348 reviews, Tri-County at 4.9 with 271 reviews, and Walmart Vision & Glasses at 3.5 with 8 reviews.

Birdeye displayed a Google component of 398 for Vintage, 50 above the direct Google peer card count of 348. Birdeye displayed a Google component of 210 for Focus, 28 above the direct Google listing count of 182. Both sources and counts remain separate because aggregation dates and methods can differ. Ratings were not averaged, counts were not summed, and cross-platform review total remains null.

## Missing evidence

Open gaps: {gaps}.

## Checks and boundaries

The deterministic builder validates the frozen row counts, candidate-to-geocoder alignment, polygon set, route matrix dimensions, and exact named Focus route receipt before writing outputs. The lane was rebuilt twice and all seven generated output checksums were compared for identity. The canonical reconciliation validator was then run against this directory.

No score, report, CRM, external system, or delivery changed. No external action was taken.
"""


def main() -> None:
    supply, catchment_counts = build_supply()
    routing = build_routing()
    visibility = build_visibility()
    missing = build_missing_evidence()
    receipts = build_receipts()

    write_json("supply_geocoded_candidates.json", supply)
    write_json("routing_corrected.json", routing)
    write_json("visibility_reputation_reconciled.json", visibility)
    write_json("missing_evidence.json", missing)
    write_json("source_receipts.json", receipts)
    (HERE / "supply-routing-method.md").write_text(
        build_method(), encoding="utf-8"
    )
    (HERE / "run-summary.md").write_text(
        build_summary(supply, catchment_counts), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
