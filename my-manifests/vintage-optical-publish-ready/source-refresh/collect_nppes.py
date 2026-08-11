#!/usr/bin/env python3
"""Collect a sanitized public NPPES roster for named local cities.

The output intentionally omits NPI identifiers and phone numbers. It is a
provider-registry snapshot, not proof of active capacity or a complete
isochrone-based supply census.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

CAPTURED_AT = "2026-07-30"
CITIES = ("Morton", "Washington", "East Peoria", "Pekin")
TAXONOMIES = ("Optometrist", "Ophthalmology")
OUT = Path(__file__).with_name("nppes-provider-roster-sanitized.json")


def display_name(item: dict) -> str:
    basic = item.get("basic", {})
    if item.get("enumeration_type") == "NPI-1":
        return " ".join(
            str(value)
            for value in (
                basic.get("first_name"),
                basic.get("middle_name"),
                basic.get("last_name"),
                basic.get("credential"),
            )
            if value
        )
    return basic.get("organization_name") or basic.get("name") or "Organization"


def location(item: dict) -> dict:
    addresses = item.get("addresses") or []
    locations = [address for address in addresses if address.get("address_purpose") == "LOCATION"]
    return (locations or addresses or [{}])[0]


def main() -> None:
    rows: list[dict] = []
    queries: list[dict] = []
    for city in CITIES:
        for taxonomy in TAXONOMIES:
            params = {
                "version": "2.1",
                "city": city,
                "state": "IL",
                "taxonomy_description": taxonomy,
                "limit": "200",
            }
            url = "https://npiregistry.cms.hhs.gov/api/?" + urllib.parse.urlencode(params)
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "MyBCAT-public-research/1.0"},
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
            queries.append(
                {
                    "city": city,
                    "taxonomy_query": taxonomy,
                    "result_count": payload.get("result_count", 0),
                    "query_url": url,
                }
            )
            for item in payload.get("results", []):
                basic = item.get("basic", {})
                practice = location(item)
                rows.append(
                    {
                        "city_query": city,
                        "taxonomy_query": taxonomy,
                        "provider_or_org_name": display_name(item),
                        "enumeration_type": item.get("enumeration_type"),
                        "status": basic.get("status"),
                        "last_updated_epoch": basic.get("last_updated_epoch"),
                        "practice_address_1": practice.get("address_1"),
                        "practice_address_2": practice.get("address_2"),
                        "practice_city": practice.get("city"),
                        "practice_state": practice.get("state"),
                        "practice_postal_prefix": (practice.get("postal_code") or "")[:5],
                        "taxonomies": sorted(
                            {
                                taxonomy_row.get("desc")
                                for taxonomy_row in item.get("taxonomies", [])
                                if taxonomy_row.get("desc")
                            }
                        ),
                    }
                )

    deduped: list[dict] = []
    seen: set[tuple] = set()
    for row in rows:
        key = (
            row["provider_or_org_name"],
            row["practice_address_1"],
            row["practice_city"],
            row["taxonomy_query"],
        )
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    output = {
        "captured_at": CAPTURED_AT,
        "scope_note": (
            "Public NPPES queries by named city and taxonomy. NPPES is a provider "
            "registry, not proof of active office capacity, patient draw, or a complete "
            "drive-time catchment supply census. Raw NPI and phone identifiers are "
            "intentionally omitted from this sanitized receipt."
        ),
        "queries": queries,
        "records": deduped,
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    counts = {
        f"{city}|{taxonomy}": sum(
            1
            for row in deduped
            if row["city_query"] == city and row["taxonomy_query"] == taxonomy
        )
        for city in CITIES
        for taxonomy in TAXONOMIES
    }
    print(json.dumps({"output": str(OUT), "records": len(deduped), "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
