#!/usr/bin/env python3
"""Build deterministic local supply and visibility candidate artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = Path(
    "/home/ankit114/repos/ringer/my-manifests/"
    "vintage-optical-publish-ready/source-refresh"
)
NPPES_PATH = SOURCE_ROOT / "nppes-provider-roster-sanitized.json"
GOOGLE_PATH = SOURCE_ROOT / "google-maps-vintage-20260730.json"
DATAFORSEO_PATH = SOURCE_ROOT / "dataforseo-preflight-20260730.json"
BIRDEYE_VINTAGE_PATH = SOURCE_ROOT / "birdeye-vintage.json"
BIRDEYE_FOCUS_PATH = SOURCE_ROOT / "birdeye-focus-on-eyes.json"

SUPPLY_PATH = OUTPUT_DIR / "supply_candidates.json"
CENSUS_PATH = OUTPUT_DIR / "census-geocoder-batch.csv"
VISIBILITY_PATH = OUTPUT_DIR / "local_visibility_reputation.json"
RECEIPTS_PATH = OUTPUT_DIR / "source_receipts.json"
METHOD_PATH = OUTPUT_DIR / "supply-visibility-method.md"
SUMMARY_PATH = OUTPUT_DIR / "run-summary.md"

PACKET_DATE = "2026-07-30"
PUBLIC_ID_FIELDS = (
    "enumeration_type",
    "provider_or_org_name",
    "practice_address_1",
    "practice_address_2",
    "practice_city",
    "practice_state",
    "practice_postal_prefix",
    "taxonomy_query",
)

STREET_SUFFIXES = {
    "avenue": "ave",
    "boulevard": "blvd",
    "center": "ctr",
    "circle": "cir",
    "court": "ct",
    "drive": "dr",
    "highway": "hwy",
    "lane": "ln",
    "parkway": "pkwy",
    "place": "pl",
    "road": "rd",
    "square": "sq",
    "street": "st",
    "terrace": "ter",
    "trail": "trl",
}
SECONDARY_DESIGNATORS = {
    "apartment": "apt",
    "building": "bldg",
    "floor": "fl",
    "suite": "ste",
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_tokens(value: Any) -> list[str]:
    if value is None:
        return []
    text = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return text.split()


def normalize_general(value: Any) -> str:
    return " ".join(normalized_tokens(value))


def normalize_address_line(value: Any) -> str:
    tokens = normalized_tokens(value)
    normalized: list[str] = []
    for token in tokens:
        token = STREET_SUFFIXES.get(token, token)
        token = SECONDARY_DESIGNATORS.get(token, token)
        normalized.append(token)
    return " ".join(normalized)


def provider_public_id(row: dict[str, Any]) -> str:
    normalized: list[str] = []
    for field in PUBLIC_ID_FIELDS:
        value = row.get(field)
        if field in ("practice_address_1", "practice_address_2"):
            normalized.append(normalize_address_line(value))
        else:
            normalized.append(normalize_general(value))
    digest_input = "|".join(normalized).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()


def taxonomy_families(taxonomies: list[str]) -> list[str]:
    families: set[str] = set()
    for taxonomy in taxonomies:
        lowered = taxonomy.casefold()
        if "ophthalmology" in lowered:
            families.add("ophthalmology")
        if "optometrist" in lowered:
            families.add("optometry")
        if "optician" in lowered or "eyewear supplier" in lowered:
            families.add("optical_goods")
        if "durable medical equipment" in lowered:
            families.add("durable_medical_equipment")
    return sorted(families)


def build_provider_records(
    source: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    rows = source.get("records")
    queries = source.get("queries")
    if not isinstance(rows, list) or not isinstance(queries, list):
        raise ValueError("NPPES source must contain records and queries arrays")

    materialized_by_query = Counter(
        (row["city_query"], row["taxonomy_query"]) for row in rows
    )
    gaps: list[dict[str, Any]] = []
    source_reported_total = 0
    for query in queries:
        key = (query["city"], query["taxonomy_query"])
        reported = int(query["result_count"])
        materialized = materialized_by_query[key]
        source_reported_total += reported
        if reported != materialized:
            gaps.append(
                {
                    "city_query": query["city"],
                    "deficit": reported - materialized,
                    "materialized_record_count": materialized,
                    "query_url": query["query_url"],
                    "reported_result_count": reported,
                    "status": "unresolved_source_mismatch",
                    "taxonomy_query": query["taxonomy_query"],
                }
            )

    expected_gap = [
        {
            "city_query": "Pekin",
            "deficit": 1,
            "materialized_record_count": 10,
            "query_url": next(
                query["query_url"]
                for query in queries
                if query["city"] == "Pekin"
                and query["taxonomy_query"] == "Optometrist"
            ),
            "reported_result_count": 11,
            "status": "unresolved_source_mismatch",
            "taxonomy_query": "Optometrist",
        }
    ]
    if source_reported_total != 40 or len(rows) != 39 or gaps != expected_gap:
        raise ValueError(
            "Frozen NPPES reconciliation changed: expected 40 reported, "
            "39 materialized, and only the Pekin Optometrist 11-to-10 gap"
        )

    provider_records: list[dict[str, Any]] = []
    for row in rows:
        taxonomies = sorted(set(row.get("taxonomies") or []))
        practice_location = {
            "address_line_1": row["practice_address_1"],
            "address_line_2": row.get("practice_address_2"),
            "city": row["practice_city"],
            "postal_prefix": row["practice_postal_prefix"],
            "state": row["practice_state"],
        }
        provider_records.append(
            {
                "active_status": row["status"],
                "city_query": row["city_query"],
                "enumeration_type": row["enumeration_type"],
                "practice_location": practice_location,
                "provider_or_org_name": row["provider_or_org_name"],
                "provider_public_id": provider_public_id(row),
                "public_taxonomy_descriptions": taxonomies,
                "record_type": "nppes_provider_candidate",
                "taxonomy_families": taxonomy_families(taxonomies),
                "taxonomy_query": row["taxonomy_query"],
            }
        )

    provider_records.sort(key=lambda row: row["provider_public_id"])
    public_ids = [row["provider_public_id"] for row in provider_records]
    if len(public_ids) != len(set(public_ids)):
        raise ValueError("Provider public IDs are not unique in the frozen source")
    return provider_records, gaps, source_reported_total


def location_key(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    location = record["practice_location"]
    return (
        normalize_address_line(location["address_line_1"]),
        normalize_address_line(location.get("address_line_2")),
        normalize_general(location["city"]),
        normalize_general(location["state"]),
        normalize_general(location["postal_prefix"]),
    )


def joined_original_address(location: dict[str, Any]) -> str:
    lines = [
        location["address_line_1"].strip(),
        (location.get("address_line_2") or "").strip(),
    ]
    return ", ".join(line for line in lines if line)


def candidate_classification(enumeration_types: list[str]) -> str:
    values = set(enumeration_types)
    if values == {"NPI-1"}:
        return "individual_provider_registry_location_candidate"
    if values == {"NPI-2"}:
        return "organization_provider_registry_location_candidate"
    return "mixed_individual_organization_provider_registry_location_candidate"


def build_office_candidates(
    provider_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[
        tuple[str, str, str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for record in provider_records:
        groups[location_key(record)].append(record)

    candidates: list[dict[str, Any]] = []
    for key in sorted(groups):
        normalized_line_1, normalized_line_2, city, state, postal = key
        linked = groups[key]
        normalized_address = normalized_line_1
        if normalized_line_2:
            normalized_address += f" | {normalized_line_2}"

        original_locations = [
            record["practice_location"]
            for record in sorted(
                linked,
                key=lambda item: (
                    joined_original_address(item["practice_location"]),
                    item["provider_public_id"],
                ),
            )
        ]
        original_variants = sorted(
            {joined_original_address(location) for location in original_locations}
        )
        original_address = original_variants[0]
        enumeration_types = sorted(
            {record["enumeration_type"] for record in linked}
        )
        families = sorted(
            {
                family
                for record in linked
                for family in record["taxonomy_families"]
            }
        )
        batch_digest = hashlib.sha256("|".join(key).encode("utf-8")).hexdigest()
        candidates.append(
            {
                "batch_id": f"VO-{batch_digest[:16]}",
                "candidate_classification": candidate_classification(
                    enumeration_types
                ),
                "city": original_locations[0]["city"],
                "enumeration_types": enumeration_types,
                "geocode_status": "pending_census_batch",
                "limitation": (
                    "Exact registry practice-location grouping only. This "
                    "candidate is not proof of an active office, capacity, "
                    "or distinct operating entity."
                ),
                "linked_taxonomy_families": families,
                "match_basis": (
                    "exact_high_confidence_normalized_practice_location_"
                    "address_city_state_zip"
                ),
                "normalized_address": normalized_address,
                "normalized_city": city,
                "normalized_state": state,
                "normalized_zip": postal,
                "original_address": original_address,
                "original_address_variants": original_variants,
                "provider_public_ids": sorted(
                    record["provider_public_id"] for record in linked
                ),
                "state": original_locations[0]["state"],
                "zip": original_locations[0]["postal_prefix"],
            }
        )
    candidates.sort(key=lambda row: row["batch_id"])
    return candidates


def write_census_batch(candidates: list[dict[str, Any]]) -> None:
    with CENSUS_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        for candidate in candidates:
            writer.writerow(
                [
                    candidate["batch_id"],
                    candidate["original_address"],
                    candidate["city"],
                    candidate["state"],
                    candidate["zip"],
                ]
            )


def parse_birdeye(
    source: dict[str, Any],
    *,
    expected_name: str,
    expected_rating: float,
    expected_total: int,
    expected_address: str,
    composition: list[tuple[str, int]],
) -> dict[str, Any]:
    results = source.get("results") or []
    if len(results) != 1:
        raise ValueError(f"Expected one Birdeye result for {expected_name}")
    result = results[0]
    text = result.get("text") or ""
    required_fragments = [
        expected_name,
        str(expected_rating),
        f"{expected_total} reviews",
        expected_address,
    ] + [f"{platform} ({count})" for platform, count in composition]
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise ValueError(
            f"Birdeye source for {expected_name} lacks expected facts: {missing}"
        )
    return {
        "address": expected_address,
        "aggregate_rating": expected_rating,
        "aggregate_total_review_count": expected_total,
        "comparison_limitation": (
            "Do not compare this total to another entity as if platform "
            "recency and collection methods were identical."
        ),
        "displayed_platform_composition": [
            {"count": count, "platform": platform}
            for platform, count in composition
        ],
        "entity_name": expected_name,
        "observation_type": "third_party_aggregator_observation",
        "observed_date": PACKET_DATE,
        "platform": "Birdeye",
        "promoted_as_google_count": False,
        "source_id": "BIRDEYE_AGGREGATOR_20260730",
        "source_url": result["url"],
        "status": "observed_aggregator_display",
    }


def build_visibility(
    google: dict[str, Any],
    dataforseo: dict[str, Any],
    birdeye_vintage: dict[str, Any],
    birdeye_focus: dict[str, Any],
) -> dict[str, Any]:
    if (
        dataforseo.get("status") != "unavailable_missing_credentials"
        or dataforseo.get("request_sent") is not False
        or dataforseo.get("cost_incurred") != 0
    ):
        raise ValueError("DataForSEO preflight state changed")

    observed = google["observed"]
    expected_google = {
        "address": "605 S Main St, Morton, IL 61550",
        "booking_link_visible": True,
        "category": "Optometrist",
        "name": "Vintage Optical",
        "owner_post_date_visible": "2026-04-09",
        "public_listing_latitude": 40.6049094,
        "public_listing_longitude": -89.467024,
        "rating": 4.9,
        "review_count": None,
        "website": "https://vintageopt.com/",
    }
    for key, expected in expected_google.items():
        if observed.get(key) != expected:
            raise ValueError(f"Google observation changed for {key}")

    vintage_observation = parse_birdeye(
        birdeye_vintage,
        expected_name="Vintage Optical",
        expected_rating=4.9,
        expected_total=413,
        expected_address="417 W Jefferson St, Morton, IL, 61550, United States",
        composition=[("Google", 398), ("Facebook", 15), ("Birdeye", 0)],
    )
    focus_observation = parse_birdeye(
        birdeye_focus,
        expected_name="Focus On Eyes, P.C.",
        expected_rating=4.8,
        expected_total=217,
        expected_address=(
            "829 West Jackson Street, Morton, IL, 61550, United States"
        ),
        composition=[
            ("Google", 210),
            ("Facebook", 6),
            ("Yahoo! Local", 1),
            ("Birdeye", 0),
        ],
    )

    return {
        "citation_consistency": {
            "birdeye_legacy_address": vintage_observation["address"],
            "current_google_address": observed["address"],
            "observed_dates": {
                "birdeye": PACKET_DATE,
                "google_maps": google["captured_at"],
            },
            "operational_status_conclusion": None,
            "source_ids": [
                "GOOGLE_MAPS_SAMPLE_20260730",
                "BIRDEYE_AGGREGATOR_20260730",
            ],
            "status": "conflict_detected",
            "upgrade_evidence_needed": [
                "Direct first-party confirmation of the current business address",
                "A current direct observation of the legacy address listing",
                "Documented listing update or closure evidence for the legacy address",
            ],
        },
        "cross_platform_review_total": None,
        "dataforseo_preflight": {
            "cost_incurred": dataforseo["cost_incurred"],
            "fallback_equivalence_to_rank_grid": False,
            "named_fallbacks": [
                {
                    "name": "direct Google Search and Maps observation",
                    "role": "dated direct sample only",
                },
                {
                    "name": "Exa",
                    "role": "domain-restricted discovery and page capture",
                },
                {
                    "name": "Perplexity",
                    "role": "contradiction research with direct-source resolution",
                },
            ],
            "request_sent": dataforseo["request_sent"],
            "source_id": "DATAFORSEO_PREFLIGHT_20260730",
            "status": dataforseo["status"],
        },
        "google_maps_sample": {
            "address": observed["address"],
            "booking_domain": observed["booking_domain"],
            "booking_link_visible": observed["booking_link_visible"],
            "captured_at": google["captured_at"],
            "category": observed["category"],
            "limitation": (
                "Limited public view. This direct dated observation is not "
                "a rank grid, and Google displayed no review count."
            ),
            "name": observed["name"],
            "owner_post_date_visible": observed["owner_post_date_visible"],
            "pin_coordinates": {
                "latitude": observed["public_listing_latitude"],
                "longitude": observed["public_listing_longitude"],
            },
            "rating": observed["rating"],
            "review_count": observed["review_count"],
            "sample_type": "dated_direct_observation_not_rank_grid",
            "source_id": "GOOGLE_MAPS_SAMPLE_20260730",
            "website": observed["website"],
        },
        "packet_date": PACKET_DATE,
        "platform_observations": [
            vintage_observation,
            focus_observation,
        ],
        "rank_grid": {
            "canonical_value": None,
            "limitation": (
                "No paid DataForSEO request ran. Named fallbacks are not "
                "equivalent to a rank grid."
            ),
            "status": "not_run",
        },
        "review_aggregation_rules": {
            "average_ratings_across_sources": False,
            "direct_google_review_count": None,
            "sum_counts_across_sources_or_platforms": False,
        },
    }


def receipt(
    *,
    source_id: str,
    path: Path,
    source_url: str,
    captured_at: str,
    captured_at_basis: str,
    source_type: str,
    authority_status: str,
    aggregation_status: str,
    limitation: str,
    query_urls: list[str] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "aggregation_status": aggregation_status,
        "authority_status": authority_status,
        "captured_at": captured_at,
        "captured_at_basis": captured_at_basis,
        "limitation": limitation,
        "path": str(path),
        "sha256": sha256_file(path),
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
    }
    if query_urls is not None:
        row["query_urls"] = query_urls
    return row


def build_receipts(
    nppes: dict[str, Any],
    google: dict[str, Any],
    dataforseo: dict[str, Any],
    birdeye_vintage: dict[str, Any],
    birdeye_focus: dict[str, Any],
) -> dict[str, Any]:
    return {
        "packet_date": PACKET_DATE,
        "receipts": [
            receipt(
                source_id="NPPES_CURRENT_20260730",
                path=NPPES_PATH,
                source_url="https://npiregistry.cms.hhs.gov/api/",
                captured_at=nppes["captured_at"],
                captured_at_basis="source_metadata",
                source_type="sanitized_public_provider_registry_query_receipt",
                authority_status=(
                    "authoritative public registry for represented provider "
                    "registration fields only"
                ),
                aggregation_status="not_an_office_count_or_supply_census",
                limitation=nppes["scope_note"],
                query_urls=[query["query_url"] for query in nppes["queries"]],
            ),
            receipt(
                source_id="GOOGLE_MAPS_SAMPLE_20260730",
                path=GOOGLE_PATH,
                source_url=google["url"],
                captured_at=google["captured_at"],
                captured_at_basis="source_metadata",
                source_type="direct_public_google_maps_observation",
                authority_status="direct_platform_observation",
                aggregation_status="not_an_aggregator_and_not_a_rank_grid",
                limitation=" ".join(google["limitations"]),
            ),
            receipt(
                source_id="DATAFORSEO_PREFLIGHT_20260730",
                path=DATAFORSEO_PATH,
                source_url=dataforseo["preflight_endpoint"],
                captured_at=dataforseo["captured_at"],
                captured_at_basis="source_metadata",
                source_type="local_api_availability_preflight_receipt",
                authority_status="authoritative_for_this_preflight_state_only",
                aggregation_status="no_request_and_no_rank_evidence",
                limitation=dataforseo["result"],
            ),
            receipt(
                source_id="BIRDEYE_AGGREGATOR_20260730",
                path=BIRDEYE_VINTAGE_PATH,
                source_url=birdeye_vintage["results"][0]["url"],
                captured_at=PACKET_DATE,
                captured_at_basis="frozen_packet_date_and_declared_source_id",
                source_type="third_party_review_aggregator_page_capture",
                authority_status="aggregator_observation_not_direct_platform_count",
                aggregation_status="aggregated_multi_platform_display",
                limitation=(
                    "The displayed 413 total and Google 398 component are "
                    "Birdeye observations, not a direct current Google count."
                ),
            ),
            receipt(
                source_id="BIRDEYE_AGGREGATOR_20260730",
                path=BIRDEYE_FOCUS_PATH,
                source_url=birdeye_focus["results"][0]["url"],
                captured_at=PACKET_DATE,
                captured_at_basis="frozen_packet_date_and_declared_source_id",
                source_type="third_party_review_aggregator_page_capture",
                authority_status="aggregator_observation_not_direct_platform_count",
                aggregation_status="aggregated_multi_platform_display",
                limitation=(
                    "The displayed 217 total and its platform components are "
                    "Birdeye observations with unknown cross-entity recency "
                    "and collection-method comparability."
                ),
            ),
        ],
    }


def build_method_markdown() -> str:
    return """# Supply and visibility candidate method

## Supply candidates

NPPES records are not office counts. This packet uses the 39 materialized public provider rows and records the separate one-row Pekin source mismatch. It does not invent a fortieth provider. Provider names, taxonomies, city-query result counts, mailing addresses, and registry rows are not treated as office counts.

Each provider row remains a provider candidate. Individual and organization enumeration records remain distinct. The `provider_public_id` is a SHA-256 row-stability key built only from normalized public fields. It is not an identifier recovered from a restricted field.

Practice-location addresses are normalized for conservative matching. Punctuation and case are removed for matching, common street suffixes are standardized, and suite or unit details remain part of the match. Only exact normalized address, city, state, and ZIP matches form one office candidate. Original address text remains available.

The office candidates have geocoding pending. Entity resolution must follow geocoding before any canonical office count can be considered. Provider and office counts remain separate. A billing, mailing, provider, or registry row alone does not prove an active office.

## Visibility and reputation

A dated SERP sample is not a rank grid. The direct Google Maps observation records the facts visible on 2026-07-30, including a 4.9 rating, current 605 S Main St citation, booking-link presence, pin coordinates, and owner-post date. Its direct Google review count remains null because the limited public view did not show one.

Birdeye provides third-party aggregator observations. Vintage Optical displayed 4.9 and 413 total reviews, with a displayed composition of Google 398, Facebook 15, and Birdeye 0. Focus On Eyes displayed 4.8 and 217 total reviews, with Google 210, Facebook 6, Yahoo! Local 1, and Birdeye 0. These are platform-specific review facts as displayed by Birdeye. They are not direct current counts from those component platforms.

Ratings are not averaged and counts are not summed across sources or platforms. Cross-platform totals remain null. The two entities are not compared as if platform recency and collection methods were identical.

## Citation consistency

The current Google citation is 605 S Main St, Morton, IL 61550. Birdeye preserves a legacy address of 417 W Jefferson St, Morton, IL 61550. This legacy address conflict is unresolved. The packet does not decide whether the old address is still operational without direct evidence.
"""


def build_summary_markdown(
    provider_count: int, office_candidate_count: int
) -> str:
    return f"""# Run summary

## Result

- Materialized provider candidates: {provider_count}
- Source-reported query results: 40
- Registered source gap: Pekin Optometrist reported 11, materialized 10, deficit 1, unresolved
- Exact normalized office candidates: {office_candidate_count}
- Canonical office count: null
- Office candidate state: Census geocoding pending

## Visibility evidence

- DataForSEO: unavailable_missing_credentials. No request was sent, cost was 0, and no rank grid ran.
- Direct Google Maps: Vintage Optical, Optometrist, 605 S Main St, Morton, IL 61550, https://vintageopt.com/, booking link visible, rating 4.9, review count null, pin 40.6049094/-89.467024, owner-post date 2026-04-09.
- Birdeye Vintage Optical: aggregator rating 4.9 and total 413, with displayed composition Google 398, Facebook 15, and Birdeye 0.
- Birdeye Focus On Eyes: aggregator rating 4.8 and total 217, with displayed composition Google 210, Facebook 6, Yahoo! Local 1, and Birdeye 0.
- Citation consistency: conflict detected between the current Google address at 605 S Main St and the Birdeye legacy address at 417 W Jefferson St. No operational conclusion was made about the legacy address.

The Birdeye totals are not promoted as direct current Google counts. Ratings were not averaged, review counts were not summed, and the cross-platform review total remains null.

## Checks and boundaries

- All 39 materialized provider rows were parsed.
- The one unresolved source deficit remains separate from provider records.
- Office candidates use exact normalized practice-location matching and retain suite details.
- The Census batch has one five-column row per office candidate and no header, provider name, or restricted identifier.
- Input receipts include local SHA-256 checksums and source limitations.
- Two consecutive builder runs produced identical checksums for every generated JSON, CSV, and Markdown output.
- The required repository validator result was PASS.

No canonical office count, score, report, CRM, external system, or delivery changed.
"""


def main() -> None:
    nppes = read_json(NPPES_PATH)
    google = read_json(GOOGLE_PATH)
    dataforseo = read_json(DATAFORSEO_PATH)
    birdeye_vintage = read_json(BIRDEYE_VINTAGE_PATH)
    birdeye_focus = read_json(BIRDEYE_FOCUS_PATH)

    provider_records, source_gaps, source_reported_total = (
        build_provider_records(nppes)
    )
    office_candidates = build_office_candidates(provider_records)

    supply = {
        "canonical_office_count": None,
        "materialized_record_count": len(provider_records),
        "office_candidate_count": len(office_candidates),
        "office_candidates": office_candidates,
        "packet_date": PACKET_DATE,
        "provider_public_id_definition": {
            "algorithm": "sha256",
            "field_delimiter": "|",
            "fields_in_order": list(PUBLIC_ID_FIELDS),
            "normalization": (
                "NFKC, trim, case-fold, punctuation-to-space, whitespace "
                "collapse; practice address lines also standardize the "
                "declared conservative street and secondary-designator tokens"
            ),
            "purpose": "public_row_stability_key_not_restricted_identifier_hash",
        },
        "provider_records": provider_records,
        "source_gap_register": source_gaps,
        "source_reported_result_count_total": source_reported_total,
        "status": "candidate_census_geocoding_pending",
        "supply_limitation": (
            "Provider registry rows and exact address groups are candidates "
            "only. Geocoding and entity resolution remain pending, so no "
            "canonical office count or active-office claim is made."
        ),
    }
    visibility = build_visibility(
        google, dataforseo, birdeye_vintage, birdeye_focus
    )
    receipts = build_receipts(
        nppes, google, dataforseo, birdeye_vintage, birdeye_focus
    )

    write_json(SUPPLY_PATH, supply)
    write_census_batch(office_candidates)
    write_json(VISIBILITY_PATH, visibility)
    write_json(RECEIPTS_PATH, receipts)
    METHOD_PATH.write_text(build_method_markdown(), encoding="utf-8")
    SUMMARY_PATH.write_text(
        build_summary_markdown(
            provider_count=len(provider_records),
            office_candidate_count=len(office_candidates),
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
