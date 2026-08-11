# Numeric and Lineage Review

Exact result: **PASS**. The fresh report-only review found no blocking numeric or lineage findings. Both required validators passed. Independent PDF extraction and Python Decimal arithmetic confirmed all score calculations, factual arithmetic, source lineage, preserved nulls, and cross-document values.

## Score checks

| Score | Full precision | Display | Arithmetic result |
| --- | ---: | ---: | --- |
| Market Demand-Supply | 60.50 | 61 | PASS |
| Competitive Pressure Index | 56.75 | 57 | PASS |
| Room to Win | 43.00 | 43 | PASS |
| Practice Competitiveness | 60.50 | 61 | PASS |
| Client Opportunity | 54.45 | 54 | PASS |
| Digital Presence | 59.75 | 60 | PASS |
| Dry eye / ocular surface | 53.00 | 53 | PASS |
| Myopia management | 53.00 | 53 | PASS |
| Specialty contact lenses | 50.75 | 51 | PASS |

All 49 weighted components reproduce their stated contributions. Every weighted score has a 1.00 weight total. Contribution sums match all full-precision totals, and one final ROUND_HALF_UP step produces each displayed score. Room to Win is the exact display inversion: `100 - 57 = 43`.

## Fact checks

| Fact group | Verified result |
| --- | --- |
| Five-window catchment | PASS. All population, household, under-18, age 40-64, age 65-plus, and diabetes values match at 5, 10, 15, 20, and 30 minutes across HTML, Markdown, and PDF. |
| Population growth | PASS. The full 2020-2025 series matches. `17,565 - 17,172 = 393`; `393 / 17,172 x 100 = 2.2886093641%`, displayed as 2.29%. |
| School enrollment growth | PASS. The observed series matches. `3,365 - 3,238 = 127`; `127 / 3,238 x 100 = 3.9221741816%`, displayed as 3.92%. The 2023-24 value remains missing and is not interpolated. |
| Corrected Focus route | PASS. `233.4 / 60 = 3.89` minutes. `2,466.8 / 1,609.344 = 1.5327` miles, displayed as 1.53. Superseded route values are absent. |
| Direct Google sample | PASS. Vintage Optical is 4.9 and 348; Focus On Eyes is 4.8 and 182; Tri-County Eye Center is 4.9 and 271; Walmart Vision & Glasses is 3.5 and 8. |
| Birdeye discrepancies | PASS. `398 - 348 = 50` for Vintage Optical and `210 - 182 = 28` for Focus On Eyes. Counts remain source-separated. |
| Candidate supply | PASS. NPPES reports 40 results, 39 records materialized, grouping produced 24 location candidates, and geocoding produced 21 matches plus 3 no-matches. Window candidate counts are 4, 4, 8, 16, and 20; competitor-candidate counts are 2, 2, 6, 14, and 18. |
| Preserved nulls | PASS. Canonical full VDU, canonical office count, rank grid, complete provider entity dedupe, patient-origin choice, live traffic, conversion, capacity, outcomes, economics, and cross-platform review total remain null. |

Substantive lineage coverage is 100%, with 0 unexplained substantive numbers. All substantive inventory entries have an explanation and source or formula, and all cited source identifiers resolve in both the source dictionary and receipt manifest. Cross-document consistency is PASS.

## Nonblocking caveat

The evidence remains public-only and directional. Catchment values are modeled estimates, while review and route observations are bounded dated samples. In the explainer PDF, the Client Opportunity contribution of 12.20 wraps to the next visual line, but the band, weight, contribution, full-precision total, Markdown, and HTML are consistent.

## Release boundary

This package remains internal-only. Human Project Room approval of the exact rendered package is required before any external use.
