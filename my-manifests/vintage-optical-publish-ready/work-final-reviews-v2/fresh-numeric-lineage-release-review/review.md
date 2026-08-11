# Final Numeric and Lineage Release Review

CANARY: blue paperclip

Verdict: FAIL

External use authorized: no

Project Room status: `inventory_review_required`

Highest true state: NOT_READY_FOR_PROJECT_ROOM_REVIEW

## Release issue

One minor issue remains. `data/competitor_set.json` records `project_room_status` as `EMPTY`. The current Project Room JSON, both Project Room fields in `scores.json`, the one-page report, and the explainer record `inventory_review_required`. The runlog also states that both status fields were corrected. This stale final-data value does not alter a score and does not authorize external use, but it contradicts the packet lineage. The packet therefore does not meet the no-issues condition for `READY_FOR_PROJECT_ROOM_REVIEW`.

Fatal issues: none.

Material issues: none.

Minor issues: 1.

## Independent recomputation

All manual base components are in the allowed set `{20, 35, 50, 65, 80}`. The stored weights match the canonical formulas and sum to 1.00, allowing normal floating-point representation. Full precision was retained and rounding was applied once.

| Result | Independent calculation | Result |
|---|---:|---:|
| Market Demand-Supply | 56.75 | 57 |
| Competitive Pressure, internal high-pressure input | 56.75 | 57 |
| Room to Win | 100 - 57 | 43 |
| Practice Competitiveness | 57.50 | 58 |
| Client Opportunity | 53.65 | 54 |
| Digital Presence | 56.75 | 57 |
| Dry eye / ocular surface | 51.50 | 52 |
| Myopia management | 51.50 | 52 |
| Specialty contact lenses | 50.75 | 51 |

The repeated values are not conflated. Market Demand-Supply, internal Competitive Pressure, and Digital Presence each round from 56.75 but use different components and answer different questions. Dry eye and myopia both round from 51.50 because they share the same band pattern, while their source basis remains lane-specific. Neutral 50, supportive 65, and constrained 35 bands are explained as bands rather than measured results.

## Numeric lineage

- S17 resolves to the frozen official 2025 PEP file. Morton village has `POPESTIMATE2025 = 17,565`.
- S18 resolves to the frozen official 2024-vintage PEP file. Its historical `POPESTIMATE2024 = 17,557`.
- The newer S17 file contains a revised 2024 back-series value of 17,555. The explainer identifies that revision without replacing the historical S18 lineage.
- S14 and the saved QuickFacts audit support 25.9% under age 18 and 23.1% age 65 or older.
- The frozen R01 receipt reports 244.3 seconds. `244.3 / 60 = 4.0717`, which rounds to 4.07 minutes.
- All source IDs referenced by `scores.json`, the one-page HTML and PDF text, and the explainer HTML, Markdown, and PDF text resolve to the 25-record registry. The HTML source links match the registered URLs.
- The one-page and explainer agree on 54, 57, 43, 58, 57, 52, 52, and 51. The one-page shows the current 17,565 value and does not show the historical 17,557 value.
- Every substantive number visible on the one-page is classified and explained in the explainer. Structural values such as section numbers, tier labels, Fix Card IDs, the 100-point scale, 30 days, the street number, source-ID digits, age thresholds, and report years are explicitly separated from performance measurements.

## Fix Card math

The explainer defines each numerator and denominator for F-001, F-002, and F-003. Its global zero-denominator rule applies to every rate: if a denominator is zero, missing, or not final, the result is `null / not calculable`, never zero. Missing counts also remain null. The 30-day review-velocity denominator is a fixed observation period rather than an opportunity count.

## Check result

- `all_visible_numbers_accounted`: pass
- `scores_recomputed`: pass
- `source_registry_resolves`: pass
- `refresh_values_current`: pass
- `cross_document_values_match`: pass
- `fix_card_math_safe`: pass
- `packet_status_consistent`: fail

No report or source file was modified. No external action was taken.
