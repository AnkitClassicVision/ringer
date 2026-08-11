# Vintage Optical staged current-number refresh

## Boundary and highest true state

- Stage: internal publish-candidate only
- Project Room: `inventory_review_required`
- Visibility: internal-only, unroomed, not for external use
- Highest true state: tested local artifacts
- External actions: none
- Forms submitted: none
- Contacts, sends, uploads, publications, commits, pushes, merges, and deployments: none

## Changed facts

1. Current Morton village population changed from the displayed 2024 estimate of 17,557 to the official 2025 PEP estimate of 17,565. S17 is the current population authority.
2. Historical lineage remains intact. The earlier official 2024-vintage PEP file reports 17,557 for 2024, so `population_estimate_2024` remains 17,557.
3. The official 2025-vintage PEP file revises its 2024 back-series estimate to 17,555. That later revision is documented but does not overwrite the 17,557 value previously reported from the earlier vintage.
4. QuickFacts age shares remain 25.9% under age 18 and 23.1% age 65 or older, with S14 retained as their authority.
5. The refreshed R01 route remains 244.3 seconds, which rounds to 4.07 minutes. No route value changed.
6. Project Room status is now stated as `inventory_review_required`. The visible use boundary remains internal-only, unroomed, and not for external use.
7. No fixed-window fact changed. Population and all other unavailable demographic, VDU, supply, provider, and ratio fields remain null for the 5, 10, 15, 20, and 30-minute windows.

## Changed files

- `updated-scores.json`
  - Updated Project Room status to `inventory_review_required`.
  - Added S17 to the market source lineage.
  - Added S17 to both copies of the Market Demand-Supply demand-strength and market-data-confidence lineages.
  - Added S17 to the Client Opportunity computed market-demand lineage.
  - Changed no score, band, weight, formula, rationale, Fix Card, specialty module, peer tier, route, or confidence grade.
- `updated-market_inputs.json`
  - Set current `city_context_only.population` to 17,565.
  - Retained `population_estimate_2024` at 17,557.
  - Added `population_estimate_2025` at 17,565.
  - Added S17 to `city_context_only.source_ids`.
  - Left every fixed-window population null and every routed-alternative record unchanged.
- `updated-sources.json`
  - Advanced the registry-level access date to 2026-07-30.
  - Preserved all 23 prior source IDs.
  - Narrowed S14 claim use to the current QuickFacts age, income, density, and commute facts.
  - Added S17 with the official 2025 PEP URL, `us_census_pep_official_file` family, 2026-07-30 access date, Morton village 17,565 claim, high confidence, `fetched_frozen` status, and village-versus-catchment limitation.
  - Final registry count is 24 unique records.
- `updated-evidence.md`
  - Added the current 17,565 population fact, historical 17,557 lineage, revised 17,555 back-series note, current 4.07-minute route confirmation, no-score-change finding, and updated Project Room boundary.
  - Made the city-context boundary explicit: the village figures are not a drive-time catchment measurement.
- `updated-research_notes.md`
  - Added the population source-vintage decision, current route confirmation, unchanged age shares, unchanged score stack, city-versus-catchment boundary, and updated Project Room status.
- `updated-scoring_notes.md`
  - Added a current-number refresh section, retained the full score stack, explained why no band moved, added the source-vintage decision, and updated Project Room status.
- `updated-onepager.html`
  - Replaced the visible 17,557 and 2024 label with 17,565 and `2025 city estimate`.
  - Preserved the visual score ring and normalized its accessible Client Opportunity label to `54 / 100`.
  - Cited the population cell directly to S17.
  - Kept 25.9% and 23.1% cited to S14.
  - Added S17 where current city-population authority is relevant in the hero context, market introduction, Market Demand-Supply note, method, and limits.
  - Updated the Project Room sentence while preserving the internal-only and unroomed labels.
  - Preserved the visual structure, every prior unique link, all higher-is-better cues, and exactly three Fix Cards.
- `build_report.md`
  - Replaced the prior build note with this refresh receipt, including changed facts and files, unchanged scores, formula and band rationale, source-vintage decision, limitations, proof, and external-action status.

## Unchanged score stack

| Measure | Result | Direction or read |
|---|---:|---|
| Market Demand-Supply | 57 | higher is better |
| Competitive Pressure, internal | 57 | higher is more pressure |
| Room to Win | 43 | higher is better |
| Practice Competitiveness | 58 | higher is better |
| Client Opportunity | 54 | higher is better |
| Digital Presence | 57 | higher is better |
| Dry eye / ocular surface | 52 | research next |
| Myopia management | 52 | research next |
| Specialty contact lenses | 51 | research next |
| Confidence | C | public-only directional proof |

## Formula and band rationale

The current-number refresh changes a city-boundary context fact. It does not provide a measured drive-time catchment population, VDU, complete supply census, patient-origin choice set, peer-normalized reputation measure, conversion result, capacity result, or economics result. No base component gains or loses evidence sufficient to leave its locked manual band of 20, 35, 50, 65, or 80.

Independent recomputation from the unchanged inputs:

- Market Demand-Supply: 56.75 rounds half up to 57.
- Competitive Pressure: 56.75 rounds half up to 57.
- Room to Win: `100 - 57 = 43`.
- Practice Competitiveness: 57.50 rounds half up to 58.
- Client Opportunity: 53.65 rounds half up to 54.
- Digital Presence: 56.75 rounds half up to 57.
- Dry eye / ocular surface: 51.50 rounds half up to 52.
- Myopia management: 51.50 rounds half up to 52.
- Specialty contact lenses: 50.75 rounds half up to 51.

All canonical weight sets still sum to 1.00. Client Opportunity still uses the computed Market Demand-Supply score of 57. Room to Win remains the exact high-good inversion of the internal pressure score.

## Source-vintage decision

Recommendation applied: use the newest official file for the current displayed year while preserving the authority of the file that produced each historical value.

- S17 and its frozen receipt establish 17,565 as the current 2025 estimate.
- The earlier official 2024-vintage file remains the authority for the historical 17,557.
- The 2025-vintage file's revised 2024 value of 17,555 is a back-series revision. It is recorded for transparency but does not retroactively change the earlier report's stated source vintage.
- S14 remains the authority for the current 25.9% and 23.1% QuickFacts age shares.
- R01 remains the route authority, with the frozen current check confirming 4.07 minutes.

## Limitations

- Morton village population and age facts are village-boundary context, not drive-time catchment measurements.
- All 5, 10, 15, 20, and 30-minute population fields remain unknown.
- Routed alternatives remain a bounded subject-origin set, not a complete office census or population-weighted patient-choice model.
- The 4.07-minute route has no live traffic or time-of-day model.
- Official practice pages prove published offers and access paths, not utilization, conversion, capacity, outcomes, patient draw, or economics.
- The Project Room still requires inventory review. These artifacts remain internal-only, unroomed, and not for external use.

## Verification

- JSON parsing: passed for all three updated JSON files.
- Locked-structure comparison: passed for scores, base components, weights, formula inputs, specialties, Fix Cards, fixed-window routes, and Confidence C.
- Formula recomputation: passed for all six core measures, Room to Win, and all three specialty scores.
- Source registry: 23 prior IDs preserved, S17 added, 24 unique IDs total.
- Citation resolution: all 80 visible citation occurrences resolve to the registered URL for their source ID.
- Link preservation: all 21 prior unique links remain; S17 raises the total to 22.
- HTML assertions: one visible 17,565 value, no visible 17,557, one 2025 city-estimate label, Client Opportunity `54 / 100`, unchanged age shares, unchanged higher-is-better cue count, and exactly three Fix Cards.
- File-scope check: only the eight authorized outputs were created beside the harness-owned `worker.log`.
- Print proof: WeasyPrint produced one Letter page at 612 by 792 points. Visual review of the 150 dpi render found no clipping, overlap, missing section, broken logo, or lost boundary label.
- Chrome proof: unavailable in this sandbox because both installed Chrome lanes stopped before page load on the crash-reporter socket permission gate. This is an environment limitation; no Chrome pass is claimed.

## Report-only review

- R1, current facts: PASS. The display and current market value are 17,565 for 2025; age shares and route value match the frozen receipt.
- R2, historical lineage: PASS. The 2024-vintage 17,557 value is retained separately from the 2025-vintage file's revised 17,555 back-series value.
- R3, source contract: PASS. S17 has every required field and all 23 prior source IDs remain present.
- R4, score lock: PASS. Scores, bands, weights, formulas, specialty reads, Fix Cards, peer tiers, routes, and Confidence C are unchanged.
- R5, page contract: PASS with a renderer limitation. The fallback render is exactly one Letter page, all prior unique links remain, 17,557 is absent from the page, age shares remain cited to S14, and exactly three Fix Cards remain.
- R6, boundary and scope: PASS. All outputs say or preserve internal-only, unroomed, not-for-external-use boundaries; only the eight authorized files were written; external actions remain none.
- Review verdict: PASS for the bounded internal staged refresh. Project Room inventory review remains required.

## Decision residue

- Hardest decision: preserve source-vintage lineage while updating the current display.
- Alternative rejected: replace the historical 17,557 with the 2025 file's revised 2024 value of 17,555. That would erase the earlier file's actual authority.
- Alternative rejected: place 17,565 into a 20-minute or other drive-time window. No isochrone population join exists.
- Least-confident assumption: Chrome outside this restricted worker will reproduce the verified one-page layout. The fixed Letter CSS, one-page fallback render, and visual QA reduce this risk, but the local Chrome gate remains unavailable.
