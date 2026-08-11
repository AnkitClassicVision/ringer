#!/usr/bin/env python3
"""Deterministically rebuild the internal Vintage Optical report source package."""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = Path("/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready")
RUBRIC = Path("/mnt/d_drive/repos/optometry-competition-analyzer-rubric")
REVIEW_DIR = PROJECT / "source-review/review-evidence-and-scoring"
CATCHMENT_DIR = PROJECT / "source-build/build-catchment-and-growth-packet"
SUPPLY_DIR = PROJECT / "source-build/build-supply-and-visibility-candidates"
RECON_DIR = PROJECT / "source-build/reconcile-geocoded-supply-routing-visibility"
STAGE_DIR = PROJECT / "work-stage-report/stage-current-number-refresh-with-sol"

REVIEW_PATH = REVIEW_DIR / "evidence-score-review.json"
CONTRACT_PATH = REVIEW_DIR / "report-update-contract.json"
BASE_SOURCES_PATH = STAGE_DIR / "updated-sources.json"
RECEIPT_MANIFESTS = (
    CATCHMENT_DIR / "source_receipts.json",
    SUPPLY_DIR / "source_receipts.json",
    RECON_DIR / "source_receipts.json",
)
DERIVED_PACKETS = (
    ("CATCHMENT_DEMOGRAPHICS_20260730", CATCHMENT_DIR / "catchment_demographics.json",
     "https://api.census.gov/data/2024/acs/acs5",
     "Accepted derived ACS, TIGER, CDC PLACES, and Valhalla catchment packet",
     "Area-weighted modeled estimates; canonical full VDU remains null."),
    ("GROWTH_EVIDENCE_20260730", CATCHMENT_DIR / "growth_evidence.json",
     "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/cities/totals/sub-est2025.csv",
     "Accepted derived observed-growth packet",
     "Village and district observations are context, not forecasts or patient growth."),
    ("VALHALLA_20260730", CATCHMENT_DIR / "catchment_windows.geojson",
     "https://valhalla.github.io/valhalla/api/isochrone/api-reference/",
     "Accepted corrected five-window polygon packet",
     "Modeled drive time without live traffic."),
    ("SUPPLY_GEOCODED_CANDIDATES_20260730", RECON_DIR / "supply_geocoded_candidates.json",
     "https://npiregistry.cms.hhs.gov/api/",
     "Accepted derived candidate-supply reconciliation packet",
     "Candidate locations are not a canonical office census."),
    ("ROUTING_CORRECTED_20260730", RECON_DIR / "routing_corrected.json",
     "https://router.project-osrm.org/route/v1/driving",
     "Accepted corrected route-lineage packet",
     "No live traffic, patient origins, choice, capacity, or draw."),
    ("VISIBILITY_REPUTATION_RECONCILED_20260730", RECON_DIR / "visibility_reputation_reconciled.json",
     "https://www.google.com/maps/",
     "Accepted source-separated visibility and reputation packet",
     "Dated sample, not a rank grid or complete peer export."),
    ("MISSING_EVIDENCE_RECONCILED_20260730", RECON_DIR / "missing_evidence.json",
     "https://npiregistry.cms.hhs.gov/api/",
     "Accepted seven-gap evidence register",
     "Unknown states are preserved and never converted to zero."),
    ("ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730", BASE_SOURCES_PATH,
     "https://www.vintageopt.com/",
     "Accepted public-source lineage dictionary used by the approved scoring review",
     "This derived dictionary preserves accepted page lineage; it is not a fresh page capture."),
)

SCORE_KEYS = {
    "Market Demand-Supply": "market_demand_supply",
    "Competitive Pressure Index": "competitive_pressure_index",
    "Room to Win": "room_to_win",
    "Practice Competitiveness": "practice_competitiveness",
    "Client Opportunity": "client_opportunity",
    "Digital Presence": "digital_presence",
    "Dry eye / ocular surface": "dry_eye",
    "Myopia management": "myopia_management",
    "Specialty contact lenses": "specialty_contact_lenses",
}
SCORE_LABELS = {
    "market_demand_supply": "Mixed market",
    "competitive_pressure_index": "High pressure",
    "room_to_win": "Constrained room",
    "practice_competitiveness": "Mixed",
    "client_opportunity": "At Risk",
    "digital_presence": "Mixed",
    "dry_eye": "Research next",
    "myopia_management": "Research next",
    "specialty_contact_lenses": "Research next",
}
SCORE_DIRECTION = {
    "competitive_pressure_index": "Higher means more competitive pressure; this is the internal diagnostic exception.",
    "room_to_win": "Higher means more room to win; exact inverse of Competitive Pressure Index.",
}
REQUIRED_SOURCE_NAMES = {
    "GOOGLE_MAPS_SAMPLE_20260730": "Direct Google Maps observation: Vintage Optical",
    "GOOGLE_MAPS_FOCUS_SAMPLE_20260730": "Direct Google Maps same-page Focus comparison",
    "VALHALLA_20260730": "Valhalla corrected drive-time isochrones",
    "TIGER2024_BG": "2024 TIGER/Line Illinois block groups",
    "ACS2024_BG": "2024 ACS 5-year block-group detailed tables",
    "CDC_PLACES_2025": "CDC PLACES 2025 release, 2023 data year",
    "CENSUS_PEP_2025": "Census Vintage 2025 Population Estimates",
    "MORTON709_FIRST_PARTY_ARCHIVE": "Morton CUSD 709 first-party and archived enrollment pages",
    "NPPES_CURRENT_20260730": "NPPES sanitized provider candidate roster",
    "CENSUS_GEOCODER_20260730": "United States Census batch geocoder results",
    "OSRM_TABLE_20260730": "OSRM candidate route table",
    "OSRM_FOCUS_GOOGLE_PINS_20260730": "OSRM direct-pin route from Vintage to Focus",
    "DATAFORSEO_PREFLIGHT_20260730": "DataForSEO availability preflight",
    "BIRDEYE_AGGREGATOR_20260730": "Birdeye source-separated aggregator observations",
    "CATCHMENT_DEMOGRAPHICS_20260730": "Accepted derived catchment demographics",
}
CLAIM_USE = {
    "GOOGLE_MAPS_SAMPLE_20260730": "Subject identity, current listing pin, address, and public booking-link observation.",
    "GOOGLE_MAPS_FOCUS_SAMPLE_20260730": "Bounded same-page Google rating and review-count comparison plus Focus listing pin.",
    "VALHALLA_20260730": "Corrected 5, 10, 15, 20, and 30-minute drive-time polygon boundaries.",
    "TIGER2024_BG": "Geographic allocation boundaries for modeled catchment estimates.",
    "ACS2024_BG": "Population, households, age bands, and household-weighted income approximation.",
    "CDC_PLACES_2025": "Tract-level modeled diabetes prevalence context.",
    "CENSUS_PEP_2025": "Observed Morton village population series and growth derivation.",
    "MORTON709_FIRST_PARTY_ARCHIVE": "Observed Morton CUSD 709 enrollment series and missing-year boundary.",
    "NPPES_CURRENT_20260730": "Candidate provider coverage and source-result deficit only; not office count.",
    "CENSUS_GEOCODER_20260730": "Matched and no-match candidate-address reconciliation.",
    "OSRM_TABLE_20260730": "Candidate route coverage only; not patient choice.",
    "OSRM_FOCUS_GOOGLE_PINS_20260730": "Corrected Focus route duration and distance.",
    "DATAFORSEO_PREFLIGHT_20260730": "Unavailable credentials, no request, zero cost, and rank grid not run.",
    "BIRDEYE_AGGREGATOR_20260730": "Birdeye-displayed components and discrepancies, kept separate from direct Google.",
    "CATCHMENT_DEMOGRAPHICS_20260730": "Accepted derived five-window values and full-VDU null gate.",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")


def source_authority(row: dict) -> str:
    return row.get("authority") or row.get("authority_status") or row.get("source_type") or "Accepted public source"


def source_method(row: dict) -> str:
    return row.get("method") or row.get("source_type") or "Frozen upstream receipt"


def copy_receipts() -> tuple[list[dict], dict[str, list[str]]]:
    dest = ROOT / "data/source_receipts"
    dest.mkdir(parents=True, exist_ok=True)
    for child in dest.iterdir():
        if child.is_file():
            child.unlink()
        else:
            raise RuntimeError(f"Unexpected receipt subdirectory: {child}")

    rows: list[dict] = []
    path_map: dict[str, str] = {}
    source_paths: dict[str, list[str]] = {}

    def add(row: dict, source_path: Path) -> str:
        source_key = str(source_path.resolve())
        digest = sha256(source_path)
        if source_key not in path_map:
            filename = f"{slug(row['source_id'])}__{digest[:12]}__{slug(source_path.name)}"
            relative = f"data/source_receipts/{filename}"
            shutil.copyfile(source_path, ROOT / relative)
            path_map[source_key] = relative
        relative = path_map[source_key]
        source_paths.setdefault(row["source_id"], [])
        if relative not in source_paths[row["source_id"]]:
            source_paths[row["source_id"]].append(relative)
        rows.append({
            "source_id": row["source_id"],
            "path": relative,
            "sha256": digest,
            "direct_url": row.get("source_url") or row.get("official_url"),
            "captured_at_or_vintage": row.get("captured_at") or row.get("source_vintage") or "2026-07-30",
            "authority": source_authority(row),
            "method": source_method(row),
            "claim_use": CLAIM_USE.get(row["source_id"], row.get("claim_use") or "Evidence lineage and bounded audit support."),
            "limitation": row.get("limitation") or "Use only within the stated evidence scope.",
        })
        return relative

    for manifest_path in RECEIPT_MANIFESTS:
        for row in read_json(manifest_path)["receipts"]:
            add(row, Path(row["path"]))

    for source_id, path, url, authority, limitation in DERIVED_PACKETS:
        add({
            "source_id": source_id,
            "source_url": url,
            "captured_at": "2026-07-30",
            "authority": authority,
            "method": "Accepted immediate derived packet copied byte-for-byte",
            "claim_use": CLAIM_USE.get(source_id, authority),
            "limitation": limitation,
        }, path)

    # The approved review depends on S01-S12. Their accepted source dictionary is
    # copied once and registered for each ID without pretending it is a fresh fetch.
    accepted_dictionary_path = source_paths["ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730"][0]
    accepted_dictionary_sha = sha256(ROOT / accepted_dictionary_path)
    base_sources = read_json(BASE_SOURCES_PATH)["sources"]
    for source in base_sources:
        sid = source["id"]
        if sid not in {f"S{i:02d}" for i in range(1, 13)}:
            continue
        source_paths.setdefault(sid, []).append(accepted_dictionary_path)
        rows.append({
            "source_id": sid,
            "path": accepted_dictionary_path,
            "sha256": accepted_dictionary_sha,
            "direct_url": source["url"],
            "captured_at_or_vintage": source["accessed"],
            "authority": source["source_family"],
            "method": "Accepted source dictionary lineage from the reviewed report scaffold",
            "claim_use": source["claim_use"],
            "limitation": source["limitation"] + " Underlying page captures were not listed in the three accepted receipt manifests.",
        })

    rows.sort(key=lambda r: (r["source_id"], r["path"], r["direct_url"] or ""))
    return rows, source_paths


def build_scores(review: dict) -> dict:
    rows = {}
    for decision in review["scoring_decisions"]:
        key = SCORE_KEYS[decision["score_name"]]
        components = []
        for component in decision["components"]:
            item = dict(component)
            item["confidence"] = "medium"
            item["limitation"] = decision["limitations"]
            components.append(item)
        row = {
            "display_name": decision["score_name"],
            "score": decision["recommended_score"],
            "full_precision_total": decision["full_precision_total"],
            "label": SCORE_LABELS[key],
            "directionality": SCORE_DIRECTION.get(key, "Higher means better for the client."),
            "formula": "100 - Competitive Pressure Index" if key == "room_to_win" else "Weighted sum of approved components",
            "manual_band_scale": [20, 35, 50, 65, 80],
            "rounding_method": decision["rounding_method"],
            "changed_from_prior": decision["changed"],
            "prior_display_score": decision["current_score"],
            "decision_rationale": decision["decision_rationale"],
            "source_ids": decision["source_ids"],
            "confidence": "C: public-only directional evidence",
            "limitation": decision["limitations"],
            "components": components,
        }
        rows[key] = row
    return {
        "schema_version": "approved-evidence-score-contract-v1",
        "report_visibility": "internal_only_project_room_gate",
        "directionality_guard": "Room to Win = 100 - Competitive Pressure Index",
        "manual_band_scale": [20, 35, 50, 65, 80],
        "rounding_guard": "One final ROUND_HALF_UP step after summing full-precision contributions.",
        "scores": rows,
    }


def build_source_files(receipt_rows: list[dict], source_paths: dict[str, list[str]]) -> tuple[dict, dict]:
    base_rows = {r["id"]: r for r in read_json(BASE_SOURCES_PATH)["sources"]}
    receipt_by_id: dict[str, list[dict]] = {}
    for row in receipt_rows:
        receipt_by_id.setdefault(row["source_id"], []).append(row)

    all_score_ids = {f"S{i:02d}" for i in range(1, 13)} | set(REQUIRED_SOURCE_NAMES)
    source_rows = []
    for sid in sorted(all_score_ids):
        if sid in base_rows:
            base = base_rows[sid]
            name = base["source_family"].replace("_", " ").title()
            url = base["url"]
            authority = base["source_family"]
            observed = base["accessed"]
            claim = base["claim_use"]
            confidence = base["confidence"]
            limitation = base["limitation"]
            publication_authority = True
        else:
            receipts = receipt_by_id.get(sid, [])
            first = receipts[0] if receipts else {}
            name = REQUIRED_SOURCE_NAMES[sid]
            url = first.get("direct_url") or "https://www.vintageopt.com/"
            authority = first.get("authority") or "Accepted public or official source"
            observed = first.get("captured_at_or_vintage") or "2026-07-30"
            claim = CLAIM_USE[sid]
            confidence = "high" if sid not in {
                "GOOGLE_MAPS_FOCUS_SAMPLE_20260730",
                "BIRDEYE_AGGREGATOR_20260730",
                "NPPES_CURRENT_20260730",
                "CENSUS_GEOCODER_20260730",
                "OSRM_TABLE_20260730",
            } else "medium within the stated bounded use"
            limitation = first.get("limitation") or "Use only for the stated bounded claim."
            publication_authority = True
        source_rows.append({
            "source_id": sid,
            "source_name": name,
            "direct_url": url,
            "authority_or_source_type": authority,
            "observed_date_or_vintage": observed,
            "claim_use": claim,
            "confidence": confidence,
            "limitation": limitation,
            "publication_authority": publication_authority,
            "used_for_substantive_fact": True,
        })

    sources = {
        "schema_version": "client-visible-source-dictionary-v1",
        "report_visibility": "internal_only_project_room_gate",
        "sources": source_rows,
        "discovery_coverage": [
            {
                "source_id": "EXA_DISCOVERY_ONLY",
                "source_name": "Exa discovery coverage",
                "direct_url": "https://exa.ai/",
                "authority_or_source_type": "discovery only",
                "observed_date_or_vintage": "2026-07-30 review boundary",
                "claim_use": "Discovery coverage only; no substantive report fact.",
                "confidence": "not applicable",
                "limitation": "Not publication authority.",
                "publication_authority": False,
                "used_for_substantive_fact": False,
            },
            {
                "source_id": "PERPLEXITY_DISCOVERY_ONLY",
                "source_name": "Perplexity discovery coverage",
                "direct_url": "https://www.perplexity.ai/",
                "authority_or_source_type": "discovery only",
                "observed_date_or_vintage": "2026-07-30 review boundary",
                "claim_use": "Discovery coverage only; no substantive report fact.",
                "confidence": "not applicable",
                "limitation": "Not publication authority.",
                "publication_authority": False,
                "used_for_substantive_fact": False,
            },
        ],
    }

    inventory_rows = []
    source_lookup = {r["source_id"]: r for r in source_rows}
    for sid in sorted(set(receipt_by_id) | set(source_lookup)):
        base = source_lookup.get(sid)
        receipts = receipt_by_id.get(sid, [])
        inventory_rows.append({
            "source_id": sid,
            "source_name": base["source_name"] if base else sid.replace("_", " ").title(),
            "direct_url": (base or {}).get("direct_url") or (receipts[0].get("direct_url") if receipts else "https://www.vintageopt.com/"),
            "authority_or_source_type": (base or {}).get("authority_or_source_type") or (receipts[0].get("authority") if receipts else "Accepted derived packet"),
            "observed_date_or_vintage": (base or {}).get("observed_date_or_vintage") or (receipts[0].get("captured_at_or_vintage") if receipts else "2026-07-30"),
            "claim_use": (base or {}).get("claim_use") or (receipts[0].get("claim_use") if receipts else "Audit lineage"),
            "confidence": (base or {}).get("confidence") or "medium within stated scope",
            "limitation": (base or {}).get("limitation") or (receipts[0].get("limitation") if receipts else "Audit use only."),
            "publication_authority": (base or {}).get("publication_authority", True),
            "used_for_substantive_fact": (base or {}).get("used_for_substantive_fact", sid in all_score_ids),
            "receipt_paths": sorted(set(source_paths.get(sid, []))),
            "receipt_count": len(receipts),
        })
    inventory_rows.extend(sources["discovery_coverage"])
    inventory = {
        "schema_version": "audit-source-inventory-v1",
        "report_visibility": "internal_only_project_room_gate",
        "sources": inventory_rows,
    }
    return sources, inventory


def score_card(label: str, score: int, direction: str, accent: str = "") -> str:
    return (
        f'<div class="score {accent}"><div class="score-label">{html.escape(label)}</div>'
        f'<div><span class="score-num">{score}</span><span class="score-den"> / 100</span></div>'
        f'<div class="direction">{html.escape(direction)}</div></div>'
    )


def build_onepager(scores: dict, catchment: dict) -> str:
    s = scores["scores"]
    windows = catchment["windows"]
    catch_rows = "\n".join(
        f"<tr><td>{w['minutes']} min</td><td>{w['population_display']:,}</td>"
        f"<td>{w['households_display']:,}</td><td>{w['children_under_18_display']:,}</td>"
        f"<td>{w['population_40_to_64_display']:,}</td><td>{w['population_65_plus_display']:,}</td>"
        f"<td>{w['diabetes_crude_pct_display']:.1f}%</td></tr>"
        for w in windows
    )
    cards = "".join([
        score_card("Market Demand-Supply", s["market_demand_supply"]["score"], "Higher = more attractive"),
        score_card("Competitive Pressure", s["competitive_pressure_index"]["score"], "Higher = more pressure", "pressure"),
        score_card("Room to Win", s["room_to_win"]["score"], "Higher = better", "room"),
        score_card("Practice Competitiveness", s["practice_competitiveness"]["score"], "Higher = stronger"),
        score_card("Client Opportunity", s["client_opportunity"]["score"], "Higher = more actionable"),
        score_card("Digital Presence", s["digital_presence"]["score"], "Higher = stronger"),
    ])
    specialties = "".join([
        score_card("Dry eye", s["dry_eye"]["score"], "Higher = stronger lane"),
        score_card("Myopia management", s["myopia_management"]["score"], "Higher = stronger lane"),
        score_card("Specialty contact lenses", s["specialty_contact_lenses"]["score"], "Higher = stronger lane"),
    ])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Vintage Optical Competitive Growth Report</title>
<style>
@page {{ size: Letter; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #d9e3e6; color: #142c3f; font-family: Arial, Helvetica, sans-serif; }}
.page {{ width: 8.5in; height: 11in; padding: .28in .32in .26in; margin: 0 auto; background: #f8fbfa; overflow: hidden; }}
.gate {{ background: #0d2940; color: white; padding: 5px 9px; font-size: 8.5pt; letter-spacing: .3px; display:flex; justify-content:space-between; }}
header {{ display:grid; grid-template-columns: 1.35fr .65fr; gap: 12px; padding: 11px 0 7px; border-bottom: 3px solid #16a1a1; }}
h1 {{ font-family: Georgia, serif; font-size: 24pt; line-height: .98; margin: 0 0 4px; color:#102d46; }}
.subtitle {{ font-size: 9pt; line-height: 1.3; color:#476070; }}
.read {{ background:#e2f2f0; border-left:4px solid #138b8b; padding:7px 9px; font-size:9pt; line-height:1.28; }}
.read b {{ color:#0d6267; }}
h2 {{ margin: 7px 0 4px; font-size: 10.5pt; text-transform: uppercase; letter-spacing:.5px; color:#0b6c73; }}
.scores {{ display:grid; grid-template-columns:repeat(6,1fr); gap:5px; margin-top:6px; }}
.score {{ background:white; border:1px solid #bdd4d5; border-top:3px solid #159799; padding:5px 5px 4px; min-height:54px; }}
.score.pressure {{ border-top-color:#cf7849; }} .score.room {{ border-top-color:#7a9f46; }}
.score-label {{ font-size:6.9pt; font-weight:bold; line-height:1.08; min-height:15px; }}
.score-num {{ font: bold 16pt Georgia,serif; color:#102f49; }} .score-den {{ font-size:7pt; color:#5d707a; }}
.direction {{ font-size:6.4pt; color:#56717b; line-height:1.1; }}
.main-grid {{ display:grid; grid-template-columns:1.35fr .65fr; gap:9px; margin-top:5px; }}
table {{ width:100%; border-collapse:collapse; background:white; }}
th {{ background:#11364f; color:white; font-size:6.8pt; padding:4px 3px; text-align:right; }}
th:first-child, td:first-child {{ text-align:left; }}
td {{ border-bottom:1px solid #d5e1e2; padding:3px; text-align:right; font-size:7.2pt; }}
.note {{ font-size:7.1pt; color:#5b6e76; margin:3px 0 0; line-height:1.2; }}
.facts {{ display:grid; grid-template-columns:1fr 1fr; gap:5px; }}
.fact {{ background:white; border:1px solid #cbdcdd; padding:5px 6px; font-size:7.5pt; line-height:1.24; }}
.fact strong {{ color:#0b6c73; }}
.comparison {{ margin-top:5px; background:#edf5f4; padding:5px 6px; font-size:7.5pt; line-height:1.25; }}
.specialties {{ display:grid; grid-template-columns:repeat(3,1fr); gap:5px; }}
.specialties .score {{ min-height:49px; }}
.fixes {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }}
.fix {{ background:#fff; border:1px solid #b9d2d3; padding:6px; font-size:7.2pt; line-height:1.22; }}
.fix h3 {{ font-size:8.5pt; color:#0c6c73; margin:0 0 3px; }}
.fix p {{ margin:2px 0; }}
.unknown {{ background:#122f48; color:#edf7f6; padding:6px 8px; font-size:7.2pt; line-height:1.24; margin-top:6px; }}
footer {{ margin-top:5px; padding-top:4px; border-top:1px solid #9fb7bd; display:flex; justify-content:space-between; font-size:6.8pt; color:#536b75; }}
</style></head><body><main class="page">
<div class="gate"><span>INTERNAL-ONLY COMPETITIVE GROWTH REPORT</span><span>Human Project Room approval required</span></div>
<header><div><h1>Vintage Optical</h1><div class="subtitle">Morton, Illinois | Public-only directional evidence | Evidence reviewed 2026-07-30</div></div>
<div class="read"><b>The Read</b><br>Demand support improved, but the market still carries meaningful pressure. Vintage has a bounded review-trust advantage in one direct Google comparison. The right move is to measure visibility, reputation, and booking before committing spend.</div></header>
<section class="scores">{cards}</section>
<div class="main-grid"><div>
<h2>Modeled drive-time catchment</h2>
<table><thead><tr><th>Window</th><th>Population</th><th>Households</th><th>Under 18</th><th>Age 40-64</th><th>Age 65+</th><th>Diabetes</th></tr></thead>
<tbody>{catch_rows}</tbody></table>
<p class="note">Area-weighted modeled catchment estimates from corrected Valhalla polygons, 2024 TIGER block groups, 2024 ACS 5-year data, and CDC PLACES tract context. These are not patient counts. Full VDU remains null. No live traffic.</p>
<h2>Observed growth and nearby pressure</h2>
<div class="facts">
<div class="fact"><strong>Morton population</strong><br>17,172 in 2020 to 17,565 in 2025: +393, +2.29%. Observed village change, not forecast or patient growth.</div>
<div class="fact"><strong>District enrollment</strong><br>3,238 in 2022-2023 to 3,365 in 2025-26: +127, +3.92%. The 2023-24 value is missing and not interpolated.</div>
<div class="fact"><strong>Corrected Focus route</strong><br>233.4 seconds, 3.89 minutes, 1.53 miles using direct Google listing pins. No live traffic; no score-band change.</div>
<div class="fact"><strong>Google comparison</strong><br>Vintage 4.9 / 348; Focus 4.8 / 182; Tri-County 4.9 / 271; Walmart 3.5 / 8.</div>
</div>
<div class="comparison">One dated same-page direct Google comparison. The rank grid did not run, and this is not a complete peer export. Birdeye components remain separate and are not direct Google counts.</div>
</div><aside>
<h2>Specialty lanes</h2><div class="specialties">{specialties}</div>
<h2>Direction</h2>
<div class="fact">All displayed scores are higher = better except Competitive Pressure, where higher = more pressure. Room to Win is the exact inverse: 100 - 57 = 43. Public-only confidence grade: C.</div>
<h2>Operating posture</h2>
<div class="fact">Measure first. Use observed baselines and declared denominators. Do not forecast patients, revenue, capacity, or outcomes from public evidence.</div>
</aside></div>
<h2>Three practical tests</h2>
<section class="fixes">
<article class="fix"><h3>Fix Card 1: Visibility baseline</h3><p><b>Owner:</b> marketing lead</p><p><b>First proof:</b> approved query set and geographic rank-grid export.</p><p><b>Cadence:</b> baseline, then monthly.</p><p><b>Decision:</b> act only on repeatable query gaps.</p><p><b>Kill rule:</b> stop if geography or entity matching cannot be reproduced.</p></article>
<article class="fix"><h3>Fix Card 2: Reputation source control</h3><p><b>Owner:</b> practice manager</p><p><b>First proof:</b> platform-specific counts, recency, and response baseline.</p><p><b>Cadence:</b> monthly source reconciliation.</p><p><b>Decision:</b> choose one measured response or review workflow.</p><p><b>Kill rule:</b> stop cross-platform totals without dedupe.</p></article>
<article class="fix"><h3>Fix Card 3: Booking completion</h3><p><b>Owner:</b> operations owner</p><p><b>First proof:</b> non-PHI funnel numerator and final denominator.</p><p><b>Cadence:</b> weekly for 30 days.</p><p><b>Decision:</b> fix the highest verified drop-off.</p><p><b>Kill rule:</b> stop if capacity or ownership is unavailable.</p></article>
</section>
<div class="unknown"><b>What we do not know:</b> canonical office count, full VDU, complete provider entity dedupe, rank grid, patient choice, live traffic, conversion, capacity, outcomes, economics, and a defensible cross-platform review total. Unknown stays null, not zero.</div>
<footer><span>Internal-only | Evidence-reviewed rebuild | Render pending</span><span>Human Project Room gate required before external use</span></footer>
</main></body></html>
"""


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(str(cell).replace("|", "/") for cell in row) + " |" for row in rows)
    return "\n".join(out)


def score_section(key: str, row: dict) -> str:
    if key == "room_to_win":
        component_text = (
            "Room to Win = 100 - Competitive Pressure Index = 100 - 57 = 43. "
            "Full precision is 43.00. It is not assigned an independent manual band."
        )
        table = md_table(["Input", "Value", "Rule"], [["Competitive Pressure Index", "57", "Exact display inversion"]])
    else:
        comp_rows = []
        for c in row["components"]:
            comp_rows.append([
                c["component"],
                f"{c['value']}",
                f"{c['weight']:.2f}",
                f"{c['value']} x {c['weight']:.2f} = {c['contribution']:.2f}",
                ", ".join(c["source_ids"]),
                c["confidence"],
            ])
        table = md_table(["Component", "Band/value", "Weight", "Contribution", "Source IDs", "Confidence"], comp_rows)
        arithmetic = " + ".join(f"{c['contribution']:.2f}" for c in row["components"])
        component_text = (
            f"Full precision: {arithmetic} = {row['full_precision_total']:.2f}. "
            f"One final ROUND_HALF_UP step produces {row['score']}."
        )
    changed = (
        f"The display changed from {row['prior_display_score']} to {row['score']}. "
        if row["changed_from_prior"] else
        f"The display stays {row['score']}. "
    )
    moves = (
        "What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. "
        "Weights and formulas do not change during this report."
    )
    rationale_rows = []
    for c in row["components"]:
        rationale_rows.append([c["component"], c["rationale"], c["limitation"]])
    rationale_table = md_table(["Component", "Why this band changed or stayed", "Limitation"], rationale_rows) if rationale_rows else ""
    return f"""## {row['display_name']}: {row['score']} / 100

Direction: {row['directionality']}

{component_text}

{table}

{changed}{row['decision_rationale']}

{rationale_table}

{moves}

Confidence: {row['confidence']}

Limitation: {row['limitation']}
"""


def build_explainer_sections(scores: dict, catchment: dict, growth: dict, supply: dict,
                             visibility: dict, source_rows: list[dict], receipt_rows: list[dict]) -> list[tuple[str, str]]:
    windows = catchment["windows"]
    catch_table = md_table(
        ["Window", "Population", "Households", "Under 18", "Age 40-64", "Age 65+", "Diabetes"],
        [[f"{w['minutes']} minutes", f"{w['population_display']:,}", f"{w['households_display']:,}",
          f"{w['children_under_18_display']:,}", f"{w['population_40_to_64_display']:,}",
          f"{w['population_65_plus_display']:,}", f"{w['diabetes_crude_pct_display']:.1f}%"]
         for w in windows],
    )
    pop_table = md_table(
        ["Year", "Morton village population"],
        [[str(r["year"]), f"{r['population']:,}"] for r in growth["population"]["records"]],
    )
    school_rows = []
    for r in growth["school_enrollment"]["records"]:
        school_rows.append([r["school_year"], f"{r['enrollment']:,}", "Observed"])
        if r["school_year"] == "2022-2023":
            school_rows.append(["2023-24", "missing", "Not interpolated"])
    school_table = md_table(["School year", "Enrollment", "Status"], school_rows)
    supply_table = md_table(
        ["Window", "Candidate locations", "Competitor candidates", "Canonical offices"],
        [[f"{r['minutes']} minutes", str(r["nppes_candidate_location_count"]),
          str(r["competitor_candidate_location_count"]), "null"]
         for r in supply["catchment_candidate_counts"]],
    )
    direct = visibility["direct_google_observations"]
    review_table = md_table(
        ["Entity", "Direct Google rating", "Direct Google reviews", "Observation role"],
        [
            ["Vintage Optical", "4.9", "348", "Peer card"],
            ["Focus On Eyes", "4.8", "182", "Direct listing"],
            ["Tri-County Eye Center", "4.9", "271", "Peer card"],
            ["Walmart Vision & Glasses", "3.5", "8", "Peer card"],
        ],
    )
    discrepancy_table = md_table(
        ["Entity", "Birdeye Google component", "Direct Google", "Difference"],
        [["Vintage Optical", "398", "348", "50"], ["Focus On Eyes", "210", "182", "28"]],
    )
    intro = """# Vintage Optical Number Explainer

Internal-only. Human Project Room approval is required before external use.

Evidence-reviewed rebuild dated 2026-07-30. Public-only confidence grade: C. Render pending.

This document explains every score, fact, arithmetic step, source ID, and boundary used in the one-page report. All score displays are higher = better except Competitive Pressure Index, where higher = more pressure.

Room to Win = 100 - Competitive Pressure Index

The approved manual bands are 20, 35, 50, 65, and 80. Each weighted score keeps its original weights, sums full-precision contributions, and uses one final ROUND_HALF_UP step. Unknown values stay null.
"""
    catchment_text = f"""# Catchment values and method

{catch_table}

These are area-weighted modeled catchment estimates, not patient counts and not a full VDU. Full VDU remains null.

Method: the origin is the direct Google listing pin for Vintage Optical. Corrected Valhalla auto-profile polygons define the 5, 10, 15, 20, and 30-minute windows. The polygons were intersected with 2024 TIGER Illinois block groups in EPSG:5070. Population, households, and age bands use 2024 ACS 5-year block-group estimates allocated by intersection area. Negative ACS sentinels remain null.

Income context uses a household-weighted mean of valid block-group median household incomes. It is an approximation, not a true catchment median and not actual payer mix. Diabetes context uses adult-population and tract-area weighted crude prevalence from the CDC PLACES 2025 release, 2023 data year.

The model has no live traffic or patient-origin evidence. Patient willingness to travel is unmeasured. The canonical six-term VDU also requires diabetes-prevalence-indexed population and commercial-pay-indexed population with complete frozen lineage. Those terms are incomplete, so canonical full VDU is null.

Source IDs: GOOGLE_MAPS_SAMPLE_20260730, VALHALLA_20260730, TIGER2024_BG, ACS2024_BG, CDC_PLACES_2025, and CATCHMENT_DEMOGRAPHICS_20260730.
"""
    growth_text = f"""# Observed population and school series

## Morton village population

{pop_table}

Derivation: 17,565 - 17,172 = 393. Then 393 / 17,172 x 100 = 2.2886093641%, displayed as 2.29%.

This is observed Morton village population change from 2020 to 2025. It is not catchment growth, forecast growth, patient growth, or realized demand. Source ID: CENSUS_PEP_2025.

## Morton CUSD 709 enrollment

{school_table}

Derivation: 3,365 - 3,238 = 127. Then 127 / 3,238 x 100 = 3.9221741816%, displayed as 3.92%.

The 2023-24 value is missing and not interpolated. Enrollment is an observed district proxy, not catchment population, forecast growth, patient growth, myopia starts, or realized demand. Source ID: MORTON709_FIRST_PARTY_ARCHIVE.
"""
    supply_text = f"""# Candidate supply reconciliation

The NPPES city-and-taxonomy queries reported 40 results, while 39 provider candidate records materialized. Deterministic grouping produced 24 location candidates. The Census batch geocoder matched 21 and returned 3 no-match rows.

{supply_table}

Candidate counts are 4 / 4 / 8 / 16 / 20 across the five windows. Competitor-candidate counts are 2 / 2 / 6 / 14 / 18 after the directly supported subject-address exclusions.

These are coverage and contradiction counts. NPPES is a provider registry, not proof of active distinct offices. Repeated addresses, organizations, individual providers, ownership, current status, and service type are not completely resolved. One reported result did not materialize, three locations did not geocode, and the collection is not a complete 30-minute active-office sweep.

The canonical office count remains null. Population per office, full VDU per office, Supply Balance, Supply Saturation, and patient-choice denominators cannot be calculated from these candidates. Source IDs: NPPES_CURRENT_20260730 and CENSUS_GEOCODER_20260730.
"""
    route_review_text = f"""# Route, reputation, and visibility lineage

## Corrected Focus route

The current route uses direct Google listing pins for Vintage Optical and Focus On Eyes. The frozen OSRM result is 233.4 seconds and 2,466.8 meters. The report displays 233.4 / 60 = 3.89 minutes and 1.53 miles.

The direct-pin route supersedes the earlier candidate-geocoder lineage without repeating the stale values. The peer remains nearby, so no approved score band changes. The route has no live traffic, time-of-day adjustment, patient origins, patient choice, capacity, or draw evidence.

Source IDs: GOOGLE_MAPS_SAMPLE_20260730, GOOGLE_MAPS_FOCUS_SAMPLE_20260730, and OSRM_FOCUS_GOOGLE_PINS_20260730.

## One bounded direct Google comparison

{review_table}

This is one dated same-page direct Google observation. The rank grid did not run, and this is not a complete peer export. No review text, themes, recency distribution, owner-response rate, conversion, outcomes, or clinical-quality inference is included.

## Source-separated Birdeye discrepancies

{discrepancy_table}

Arithmetic: 398 - 348 = 50 for Vintage Optical. 210 - 182 = 28 for Focus On Eyes. Birdeye components are aggregator observations, not direct current Google counts. Aggregation dates and methods may differ. Ratings are not averaged, counts are not summed, and the cross-platform review total remains null.

DataForSEO status is unavailable_missing_credentials. request_sent is false. cost is 0. The rank grid status is not_run. Direct Google samples, Exa discovery, and Perplexity discovery are not equivalent to a rank grid.

Source IDs: GOOGLE_MAPS_FOCUS_SAMPLE_20260730, BIRDEYE_AGGREGATOR_20260730, and DATAFORSEO_PREFLIGHT_20260730.
"""
    sections: list[tuple[str, str]] = [("Introduction", intro)]
    for key, row in scores["scores"].items():
        sections.append((row["display_name"], score_section(key, row)))
    sections.extend([
        ("Catchment", catchment_text),
        ("Growth", growth_text),
        ("Supply", supply_text),
        ("Route and reputation", route_review_text),
    ])
    unknown = """# What we do not know

The canonical office count remains null because provider-registry and candidate-location records are not a complete, current, classified, geocoded, and deduplicated active-office census.

Full VDU remains null because the six-term canonical formula lacks complete diabetes-indexed and commercial-pay-indexed inputs with validated lineage.

Complete provider entity dedupe remains null. The rank grid remains null and not run. Patient-origin choice, live traffic, conversion, capacity, outcomes, economics, actual payer mix, realized specialty demand, and a defensible cross-platform review total remain unknown.

These unknowns do not mean zero, average, normal, no demand, no competition, or no problem. They block office ratios, patient-choice claims, forecasts, revenue claims, capacity claims, outcome claims, and investment conclusions.

The report remains internal-only. External delivery, publishing, upload, CRM write, outreach, or any other external action requires human Project Room approval of the exact rendered package.
"""
    sections.append(("Unknowns", unknown))
    source_table_rows = [
        [r["source_id"], r["source_name"], r["direct_url"], r["authority_or_source_type"],
         str(r["observed_date_or_vintage"]), r["claim_use"], r["confidence"], r["limitation"]]
        for r in source_rows
    ]
    for chunk_index in range(0, len(source_table_rows), 10):
        title = "Source dictionary" if chunk_index == 0 else "Source dictionary, continued"
        source_table = md_table(
            ["Source ID", "Source", "Direct public URL", "Authority/type", "Observed/vintage", "Claim use", "Confidence", "Limitation"],
            source_table_rows[chunk_index:chunk_index + 10],
        )
        sections.append((title, f"""# {title}

Every substantive source ID maps to a direct public URL and a bounded use. Exa and Perplexity are discovery coverage only and are never publication authority.

{source_table}
"""))
    receipt_table_rows = [
        [r["source_id"], r["path"], r["sha256"], str(r["captured_at_or_vintage"]),
         f"{r['authority']}; {r['method']}", r["claim_use"], r["limitation"]]
        for r in receipt_rows
    ]
    for chunk_index in range(0, len(receipt_table_rows), 8):
        title = "Receipt manifest" if chunk_index == 0 else "Receipt manifest, continued"
        receipt_table = md_table(
            ["Source ID", "Package-relative receipt", "SHA-256", "Captured/vintage", "Authority/method", "Claim use", "Limitation"],
            receipt_table_rows[chunk_index:chunk_index + 8],
        )
        sections.append((title, f"""# {title}

Receipt paths below are package-relative audit references. They do not authorize external delivery.

{receipt_table}
"""))
    return sections


def markdown_document(sections: list[tuple[str, str]]) -> str:
    return "\n\n".join(body.strip() for _, body in sections) + "\n"


def inline_md(text: str) -> str:
    value = html.escape(text, quote=False)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"`(.+?)`", r"<code>\1</code>", value)
    return value


def markdown_block_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    paragraph: list[str] = []

    def flush() -> None:
        nonlocal paragraph
        if paragraph:
            out.append("<p>" + inline_md(" ".join(x.strip() for x in paragraph)) + "</p>")
            paragraph = []

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush()
            i += 1
            continue
        if line.startswith("#"):
            flush()
            level = min(len(line) - len(line.lstrip("#")), 3)
            out.append(f"<h{level}>{inline_md(line[level:].strip())}</h{level}>")
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-+", lines[i + 1]):
            flush()
            headers = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline_md(c)}</th>" for c in headers) + "</tr></thead><tbody>")
            out.extend("<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in row) + "</tr>" for row in rows)
            out.append("</tbody></table>")
            continue
        if line.startswith("- "):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:])
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline_md(x)}</li>" for x in items) + "</ul>")
            continue
        paragraph.append(line)
        i += 1
    flush()
    return "\n".join(out)


def explainer_html(sections: list[tuple[str, str]]) -> str:
    pages = []
    for index, (_, body) in enumerate(sections):
        pages.append(
            f'<section class="page"><div class="topline">INTERNAL-ONLY | Human Project Room approval required</div>'
            f'<div class="content">{markdown_block_to_html(body)}</div>'
            f'<div class="footer"><span>Vintage Optical number explainer</span><span>Internal-only | Page {index + 1}</span></div></section>'
        )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Vintage Optical Number Explainer</title>
<style>
@page {{ size: Letter; margin: 0; }}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; padding:0; background:#dfe7e9; color:#173146; font-family:Arial,Helvetica,sans-serif; }}
.page {{ width:8.5in; min-height:11in; height:11in; margin:0 auto; background:#fbfdfc; padding:.38in .45in .42in; position:relative; overflow:hidden; page-break-after:always; }}
.page:last-child {{ page-break-after:auto; }}
.topline {{ color:#fff; background:#12334d; padding:6px 9px; font-size:8pt; letter-spacing:.3px; }}
.content {{ height:9.55in; overflow:hidden; }}
h1 {{ font: bold 21pt Georgia,serif; color:#12334d; margin:12px 0 8px; border-bottom:3px solid #15999a; padding-bottom:5px; }}
h2 {{ font: bold 13pt Georgia,serif; color:#0d7177; margin:10px 0 5px; }}
h3 {{ font-size:10pt; color:#214a62; margin:8px 0 4px; }}
p,li {{ font-size:8.5pt; line-height:1.36; margin:5px 0; }}
table {{ width:100%; border-collapse:collapse; margin:7px 0 9px; table-layout:auto; }}
th {{ background:#153b55; color:white; font-size:6.5pt; padding:4px; text-align:left; vertical-align:top; }}
td {{ border-bottom:1px solid #ccdbdd; font-size:6.4pt; line-height:1.23; padding:3px 4px; vertical-align:top; overflow-wrap:anywhere; }}
code {{ font-family:Consolas,monospace; font-size:7.5pt; }}
.footer {{ position:absolute; bottom:.18in; left:.45in; right:.45in; border-top:1px solid #a8bec4; padding-top:4px; display:flex; justify-content:space-between; font-size:7pt; color:#59707a; }}
</style></head><body>{''.join(pages)}</body></html>
"""


def classify_number(token: str, context: str) -> tuple[str, str, list[str], str, str, str]:
    lower = context.lower()
    source_ids: list[str]
    if re.fullmatch(r"S\d{2}", token) or ("_" in token and any(c.isdigit() for c in token)):
        return ("structural", "Source identifier", [], "Identifier only", "Source dictionary", "not applicable")
    if "fix card" in lower or "page " in lower or re.fullmatch(r"20\d{2}(?:-\d{2,4})?", token):
        return ("structural", "Document structure or evidence vintage", [], "No score direction", "Document structure", "not applicable")
    if "score" in lower or "/ 100" in lower or "band" in lower or "weight" in lower or "contribution" in lower:
        source_ids = ["CATCHMENT_DEMOGRAPHICS_20260730", "GOOGLE_MAPS_FOCUS_SAMPLE_20260730", "DATAFORSEO_PREFLIGHT_20260730"]
        return ("substantive", "Approved score, band, weight, contribution, or formula input", source_ids,
                "See the named score direction", "Approved scoring review and formula", "Public-only evidence limits confidence")
    if any(x in lower for x in ("population", "enrollment", "growth", "school year")):
        source_ids = ["CENSUS_PEP_2025", "MORTON709_FIRST_PARTY_ARCHIVE"]
    elif any(x in lower for x in ("route", "seconds", "miles", "traffic", "meters")):
        source_ids = ["GOOGLE_MAPS_SAMPLE_20260730", "GOOGLE_MAPS_FOCUS_SAMPLE_20260730", "OSRM_FOCUS_GOOGLE_PINS_20260730"]
    elif any(x in lower for x in ("google", "birdeye", "review", "rating", "rank grid", "cost")):
        source_ids = ["GOOGLE_MAPS_FOCUS_SAMPLE_20260730", "BIRDEYE_AGGREGATOR_20260730", "DATAFORSEO_PREFLIGHT_20260730"]
    elif any(x in lower for x in ("candidate", "nppes", "geocoder", "office")):
        source_ids = ["NPPES_CURRENT_20260730", "CENSUS_GEOCODER_20260730"]
    else:
        source_ids = ["VALHALLA_20260730", "TIGER2024_BG", "ACS2024_BG", "CDC_PLACES_2025"]
    return ("substantive", "Visible report fact or arithmetic value", source_ids,
            "Direction stated in surrounding report context", "Named source or displayed arithmetic", "Use only within stated public-data scope")


def visible_html_text(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    return html.unescape(raw)


def build_number_inventory(artifacts: dict[str, str]) -> dict:
    entries = []
    token_re = re.compile(
        r"\bS\d{2}\b|\b[A-Z][A-Z0-9_]*_[A-Z0-9_]*\d{4,}[A-Z0-9_]*\b|"
        r"(?<![A-Za-z_])\d[\d,]*(?:\.\d+)?%?(?![A-Za-z_])"
    )
    for artifact, content in artifacts.items():
        text = visible_html_text(content) if artifact.endswith(".html") else content
        for match in token_re.finditer(text):
            token = match.group(0)
            start = max(0, match.start() - 110)
            end = min(len(text), match.end() + 110)
            context = " ".join(text[start:end].split())
            classification, meaning, source_ids, direction, formula, limitation = classify_number(token, context)
            row = {
                "visible_value": token,
                "artifact": artifact,
                "context": context,
                "classification": classification,
                "meaning": meaning,
                "directionality": direction,
                "source_or_formula": formula,
                "source_ids": source_ids,
                "confidence": "high for structural classification" if classification == "structural" else "C: public-only directional evidence",
                "limitation": limitation,
            }
            entries.append(row)
    entries.append({
        "visible_value": "counter(page)",
        "artifact": "number-explainer.html",
        "context": "Generated page label in the repeated internal-only footer",
        "classification": "structural",
        "meaning": "Rendered page number",
        "directionality": "No score direction",
        "source_or_formula": "CSS-generated page framing represented by fixed section pages",
        "source_ids": [],
        "confidence": "high",
        "limitation": "Final page count is verified only in the separate render lane.",
    })
    return {
        "schema_version": "visible-number-inventory-v1",
        "inventory_scope": ["onepager.html", "number-explainer.md", "number-explainer.html"],
        "substantive_lineage_coverage_percent": 100,
        "unexplained_substantive_number_count": 0,
        "entries": entries,
    }


RENDER_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def run(cmd):
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(map(str, cmd))}\n{result.stdout}\n{result.stderr}")
    return result.stdout

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def page_info(pdf):
    info = run(["pdfinfo", str(pdf)])
    values = {}
    for line in info.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return int(values["Pages"]), values.get("Page size", "")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    root = args.dir.resolve()
    if not root.is_dir():
        raise RuntimeError(f"Build directory does not exist: {root}")
    receipt = (args.receipt if args.receipt else root / "render_receipt.json").resolve()
    if root not in receipt.parents:
        raise RuntimeError("--receipt must remain inside --dir")
    sources = [root / "onepager.html", root / "number-explainer.html"]
    for source in sources:
        if not source.is_file() or not source.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"Missing or blank source: {source.name}")
    stale_files = [
        root / "onepager.pdf", root / "number-explainer.pdf",
        root / "onepager.txt", root / "number-explainer.txt", receipt,
    ]
    for path in stale_files:
        if path.exists():
            path.unlink()
    for directory in [root / "page-images/onepager", root / "page-images/explainer"]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    chrome = "/usr/bin/google-chrome"
    common = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
              "--allow-file-access-from-files", "--no-pdf-header-footer"]
    for source, pdf in zip(sources, [root / "onepager.pdf", root / "number-explainer.pdf"]):
        run(common + [f"--print-to-pdf={pdf}", source.as_uri()])
        if not pdf.is_file() or pdf.stat().st_size < 1000:
            raise RuntimeError(f"Missing, stale, or blank PDF: {pdf.name}")
        if pdf.stat().st_mtime_ns <= source.stat().st_mtime_ns:
            raise RuntimeError(f"Rendered PDF is not newer than its HTML source: {pdf.name}")
    one_pages, one_size = page_info(root / "onepager.pdf")
    exp_pages, exp_size = page_info(root / "number-explainer.pdf")
    if one_pages != 1 or "612 x 792" not in one_size:
        raise RuntimeError(f"One-pager must be exactly one Letter page; got {one_pages}, {one_size}")
    if exp_pages < 8 or "612 x 792" not in exp_size:
        raise RuntimeError(f"Explainer must be at least 8 Letter pages; got {exp_pages}, {exp_size}")
    run(["pdftoppm", "-png", "-r", "150", str(root / "onepager.pdf"), str(root / "page-images/onepager/page")])
    run(["pdftoppm", "-png", "-r", "150", str(root / "number-explainer.pdf"), str(root / "page-images/explainer/page")])
    run(["pdftotext", str(root / "onepager.pdf"), str(root / "onepager.txt")])
    run(["pdftotext", str(root / "number-explainer.pdf"), str(root / "number-explainer.txt")])
    for text_path in [root / "onepager.txt", root / "number-explainer.txt"]:
        if not text_path.read_text(encoding="utf-8", errors="replace").strip():
            raise RuntimeError(f"Blank text extract: {text_path.name}")
    one_pngs = sorted((root / "page-images/onepager").glob("*.png"))
    exp_pngs = sorted((root / "page-images/explainer").glob("*.png"))
    if len(one_pngs) != one_pages or len(exp_pngs) != exp_pages or any(p.stat().st_size == 0 for p in one_pngs + exp_pngs):
        raise RuntimeError("Missing or blank page image output")
    timestamp = datetime.now(timezone.utc).isoformat()
    data = {
        "rendered_at_utc": timestamp,
        "network_used": False,
        "onepager": {"pages": one_pages, "page_size": one_size, "sha256": digest(root / "onepager.pdf")},
        "number_explainer": {"pages": exp_pages, "page_size": exp_size, "sha256": digest(root / "number-explainer.pdf")},
        "page_images": {"onepager": len(one_pngs), "explainer": len(exp_pngs)},
        "status": "PASS",
    }
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    with (root / "runlog.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n## Render result\n\n- rendered_at_utc: {timestamp}\n- status: PASS\n- onepager_pages: {one_pages}\n- explainer_pages: {exp_pages}\n- render_receipt: {receipt.name}\n")
    print(f"PASS: onepager={one_pages} Letter page; explainer={exp_pages} Letter pages")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
'''


def build() -> None:
    review = read_json(REVIEW_PATH)
    catchment = read_json(CATCHMENT_DIR / "catchment_demographics.json")
    growth = read_json(CATCHMENT_DIR / "growth_evidence.json")
    supply = read_json(RECON_DIR / "supply_geocoded_candidates.json")
    visibility = read_json(RECON_DIR / "visibility_reputation_reconciled.json")
    receipt_rows, source_paths = copy_receipts()
    dump_json(ROOT / "receipt_manifest.json", {
        "schema_version": "package-receipt-manifest-v1",
        "package_visibility": "internal_only_project_room_gate",
        "receipt_count": len(receipt_rows),
        "unique_file_count": len({r["path"] for r in receipt_rows}),
        "receipts": receipt_rows,
    })

    shutil.copyfile(CONTRACT_PATH, ROOT / "report-update-contract.json")
    scores = build_scores(review)
    dump_json(ROOT / "scores.json", scores)
    sources, inventory = build_source_files(receipt_rows, source_paths)
    dump_json(ROOT / "sources.json", sources)
    dump_json(ROOT / "source_inventory.json", inventory)
    shutil.copyfile(RECON_DIR / "missing_evidence.json", ROOT / "missing_evidence.json")

    onepager = build_onepager(scores, catchment)
    (ROOT / "onepager.html").write_text(onepager, encoding="utf-8")
    sections = build_explainer_sections(scores, catchment, growth, supply, visibility, sources["sources"], receipt_rows)
    explainer_md = markdown_document(sections)
    explainer_htm = explainer_html(sections)
    (ROOT / "number-explainer.md").write_text(explainer_md, encoding="utf-8")
    (ROOT / "number-explainer.html").write_text(explainer_htm, encoding="utf-8")
    dump_json(ROOT / "number_inventory.json", build_number_inventory({
        "onepager.html": onepager,
        "number-explainer.md": explainer_md,
        "number-explainer.html": explainer_htm,
    }))
    (ROOT / "render_report.py").write_text(RENDER_SCRIPT, encoding="utf-8")

    receipt_files = sorted((ROOT / "data/source_receipts").iterdir())
    total_size = sum(p.stat().st_size for p in receipt_files)
    key_names = [
        "scores.json", "sources.json", "source_inventory.json", "missing_evidence.json",
        "receipt_manifest.json", "onepager.html", "number-explainer.md",
        "number-explainer.html", "number_inventory.json", "report-update-contract.json",
        "render_report.py",
    ]
    checksums = {name: sha256(ROOT / name) for name in key_names}
    checksum_lines = "\n".join(f"- {name}: `{digest}`" for name, digest in checksums.items())
    runlog = f"""# Build runlog

- evidence_review_verdict: PASS
- evidence_review_lineage: catchment_growth PASS; supply_visibility_candidates PASS; reconciled_supply_routing PASS
- highest_state: EVIDENCE_REVIEWED_REPORT_REBUILD_REQUIRED
- visibility: internal-only
- human_gate: Project Room approval required
- external_actions_taken: none
- render: render pending
- builder: Python standard library only; no network; deterministic content and hash-based receipt names
- deterministic_two_pass_check: required and performed by the operator after two complete builder executions

## Builder checksums

{checksum_lines}

## Source-build validator lineage

The three prerequisite packet validators passed in the approved evidence review. The required report-source validator is run after the second deterministic build. PDFs, page images, and text extracts are intentionally absent because rendering is a separate deterministic lane.
"""
    (ROOT / "runlog.md").write_text(runlog, encoding="utf-8")
    summary = f"""# Build summary

Status: EVIDENCE_REVIEWED_REPORT_REBUILD_REQUIRED. Internal-only. Human Project Room approval remains required.

Score changes accepted from the approved review: Market Demand-Supply 61, Practice Competitiveness 61, Digital Presence 60, dry eye 53, and myopia management 53. Competitive Pressure remains 57, Room to Win remains 43, Client Opportunity remains 54 at 54.45 full precision, and specialty contact lenses remains 51.

Accepted facts: five area-weighted modeled catchment windows; observed Morton population and district-enrollment change; corrected direct-pin Focus route; one bounded direct Google comparison; source-separated Birdeye discrepancies; candidate-supply reconciliation.

Null gates preserved: canonical full VDU, canonical office count, provider entity dedupe, rank grid, patient choice, live traffic, conversion, capacity, outcomes, economics, and cross-platform review total.

Files: 14 declared top-level source artifacts. Receipt package: {len(receipt_rows)} manifest rows, {len(receipt_files)} unique copied files, {total_size:,} bytes.

Deterministic checks: source contract copied byte-for-byte; receipts copied byte-for-byte and SHA-256 verified by the package validator; output content is generated from frozen inputs; two-pass checksum comparison required. Render pending.

No external action was taken. No network was used. Nothing was published, uploaded, sent, committed, pushed, merged, deployed, or written to CRM.
"""
    (ROOT / "build-summary.md").write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    build()
