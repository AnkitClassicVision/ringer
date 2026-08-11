#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

UA = "MyBCAT-OptometryAnalyzer/1.0 (public research; contact: ankit@mybcat.com)"
SUBJECT = {
    "id": "SUBJECT",
    "name": "Vintage Optical",
    "query": "605 South Main Street, Morton, Illinois 61550",
    "expected_city": "Morton",
    "candidate_tier": "subject",
    "category": "independent_optometry",
}
TARGETS = [
    {"id":"R01","name":"Focus On Eyes","query":"Focus On Eyes, Morton, Illinois","expected_city":"Morton","candidate_tier":"tier_1","category":"independent_optometry"},
    {"id":"R02","name":"Walmart Vision Center Morton","query":"155 East Courtland Street, Morton, Illinois 61550","expected_city":"Morton","candidate_tier":"tier_2","category":"retail_optical_with_od"},
    {"id":"R03","name":"Tri-County Eye Center Washington","query":"100 Hillcrest Drive, Washington, Illinois 61571","expected_city":"Washington","candidate_tier":"tier_1","category":"regional_eye_care_group"},
    {"id":"R04","name":"Vision Care Center Washington","query":"1009 North Cummings Lane, Washington, Illinois 61571","expected_city":"Washington","candidate_tier":"tier_1","category":"regional_optometry_specialty_peer"},
    {"id":"R05","name":"Bard Optical East Peoria","query":"412 Riverside Drive, East Peoria, Illinois 61611","expected_city":"East Peoria","candidate_tier":"tier_2","category":"retail_optical_with_eye_care"},
    {"id":"R06","name":"Illinois Eye Center Washington","query":"93 Eastgate Drive, Washington, Illinois 61571","expected_city":"Washington","candidate_tier":"tier_2","category":"ophthalmology_medical_surgical"},
]


def get_json(url: str):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def geocode(item):
    url = "https://nominatim.openstreetmap.org/search?" + urlencode({
        "q": item["query"], "format": "jsonv2", "limit": 5,
        "addressdetails": 1, "countrycodes": "us",
    })
    data = get_json(url)
    chosen = None
    for candidate in data:
        display = candidate.get("display_name", "")
        if item["expected_city"].lower() in display.lower():
            chosen = candidate
            break
    if chosen is None and data:
        chosen = data[0]
    return url, data, chosen


def route(origin, destination):
    coords = f"{origin['lon']},{origin['lat']};{destination['lon']},{destination['lat']}"
    url = "https://router.project-osrm.org/route/v1/driving/" + quote(coords, safe=";,.-") + "?overview=false&steps=false&alternatives=false"
    data = get_json(url)
    return url, data


def main() -> int:
    out = Path.cwd()
    receipts = {
        "schema_version": "route-receipts-v1",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "geocoder": "Nominatim/OpenStreetMap public endpoint",
        "router": "OSRM public route endpoint",
        "subject": None,
        "targets": [],
        "limitations": [
            "Point-to-point practice-origin routes are not polygon isochrones or patient-origin choice sets.",
            "Nominatim entity matches require review against official addresses before scoring.",
            "Traffic and time-of-day variation are not represented by the public OSRM route."
        ],
    }
    geocode_url, candidates, chosen = geocode(SUBJECT)
    if not chosen:
        raise SystemExit("WHY: subject geocoding returned no result")
    origin = {"lat": float(chosen["lat"]), "lon": float(chosen["lon"])}
    receipts["subject"] = {
        **SUBJECT, "geocode_url": geocode_url, "candidates": candidates,
        "selected": chosen, "lat": origin["lat"], "lon": origin["lon"],
    }
    time.sleep(1.1)
    for item in TARGETS:
        try:
            gu, candidates, selected = geocode(item)
            record = {**item, "geocode_url": gu, "candidates": candidates, "selected": selected}
            if selected:
                dest = {"lat": float(selected["lat"]), "lon": float(selected["lon"])}
                ru, rd = route(origin, dest)
                record.update({"lat": dest["lat"], "lon": dest["lon"], "route_url": ru, "route_response": rd})
                routes = rd.get("routes") or []
                if routes:
                    record["route_minutes"] = round(routes[0]["duration"] / 60, 2)
                    record["route_miles"] = round(routes[0]["distance"] / 1609.344, 2)
                    record["status"] = "routed"
                else:
                    record["status"] = "route_missing"
            else:
                record["status"] = "geocode_missing"
            receipts["targets"].append(record)
        except Exception as exc:
            receipts["targets"].append({**item, "status":"error", "error":f"{type(exc).__name__}: {exc}"})
        time.sleep(1.1)
    (out / "route_receipts.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    summary = {
        "subject": {"name": SUBJECT["name"], "lat": origin["lat"], "lon": origin["lon"], "selected_display_name": chosen.get("display_name")},
        "routes": [
            {k: r.get(k) for k in ["id","name","candidate_tier","category","status","lat","lon","route_minutes","route_miles"]}
            | {"selected_display_name": (r.get("selected") or {}).get("display_name")}
            for r in receipts["targets"]
        ],
        "limitations": receipts["limitations"],
    }
    (out / "routing_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
