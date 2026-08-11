# Numeric and Lineage Review

Result: **PASS**. The rendered internal package is numerically clean within the approved formulas and source boundaries. Both build and render validators passed. Independent PDF extraction and Python Decimal arithmetic found no blocking findings.

Substantive numeric lineage is 100%. Unexplained substantive numbers: 0. Cross-document consistency: PASS.

## Score checks

| Score | Display | Full precision | Weight total | Recomputed arithmetic | Rounding | Result |
| --- | ---: | ---: | ---: | --- | --- | --- |
| Market Demand-Supply | 61 | 60.50 | 1.00 | 16.25 + 10.00 + 9.75 + 9.75 + 9.75 + 5.00 = 60.50 | ROUND_HALF_UP to 61 | PASS |
| Competitive Pressure Index | 57 | 56.75 | 1.00 | 20.00 + 16.25 + 13.00 + 7.50 = 56.75 | ROUND_HALF_UP to 57 | PASS |
| Room to Win | 43 | 43.00 | Not applicable | 100 - 57 = 43 | Exact inversion after the pressure score is rounded | PASS |
| Practice Competitiveness | 61 | 60.50 | 1.00 | 10.00 + 13.00 + 13.00 + 9.75 + 9.75 + 5.00 = 60.50 | ROUND_HALF_UP to 61 | PASS |
| Client Opportunity | 54 | 54.45 | 1.00 | 12.20 + 10.00 + 10.00 + 7.50 + 9.75 + 5.00 = 54.45 | ROUND_HALF_UP to 54 | PASS |
| Digital Presence | 60 | 59.75 | 1.00 | 12.50 + 13.00 + 13.00 + 9.75 + 6.50 + 5.00 = 59.75 | ROUND_HALF_UP to 60 | PASS |
| Dry eye / ocular surface | 53 | 53.00 | 1.00 | 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00 | ROUND_HALF_UP to 53 | PASS |
| Myopia management | 53 | 53.00 | 1.00 | 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00 | ROUND_HALF_UP to 53 | PASS |
| Specialty contact lenses | 51 | 50.75 | 1.00 | 10.00 + 7.50 + 9.75 + 7.50 + 7.50 + 5.00 + 3.50 = 50.75 | ROUND_HALF_UP to 51 | PASS |

Every component value, weight, and contribution recomputed exactly. Every weighted score had a 1.00 weight total. Each score source ID resolves in both the source dictionary and receipt manifest.

## Fact checks

| Fact group | Exact check | Result |
| --- | --- | --- |
| Five-window catchment | All population, household, under-18, age 40-64, age 65-plus, and diabetes values match for 5, 10, 15, 20, and 30 minutes | PASS |
| Population growth | 17,565 - 17,172 = 393; 393 / 17,172 x 100 = 2.2886093641%, displayed as 2.29% | PASS |
| School enrollment growth | 3,365 - 3,238 = 127; 127 / 3,238 x 100 = 3.9221741816%, displayed as 3.92%; 2023-24 remains missing and not interpolated | PASS |
| Corrected Focus route | 233.4 seconds / 60 = 3.89 minutes; 2,466.8 meters = 1.5327984570 miles, displayed as 1.53 | PASS |
| Direct Google sample | Vintage 4.9 / 348; Focus 4.8 / 182; Tri-County 4.9 / 271; Walmart 3.5 / 8 | PASS |
| Birdeye discrepancies | 398 - 348 = 50; 210 - 182 = 28; counts remain source-separated | PASS |
| Candidate supply counts | NPPES 40 reported and 39 materialized; 24 location candidates; geocoder 21 matched plus 3 no-match; window counts 4 / 4 / 8 / 16 / 20 and 2 / 2 / 6 / 14 / 18 | PASS |
| Null denominators | All 11 canonical nulls remain null: full VDU, office count, rank grid, provider entity dedupe, patient-origin choice, live traffic, conversion, capacity, outcomes, economics, and cross-platform review total | PASS |

The one-pager HTML and PDF agree. The number explainer Markdown, HTML, and PDF agree. The stale route values 4.07, 1.56, and 244.3 are absent.

## Nonblocking caveats

- Room to Win is defined from the rounded Competitive Pressure Index display. It is 100 - 57 = 43, not an inversion of the 56.75 weighted total.
- Catchment values are modeled area-weighted estimates without live traffic or patient-origin evidence. They are not patient counts or a full VDU.
- The Google comparison is one dated same-page sample. Birdeye counts remain source-separated, and candidate supply counts are not canonical office counts.
- The preserved nulls correctly prevent office-ratio, patient-choice, cross-platform-total, operating, and financial claims.

## Release boundary

This package remains internal-only. Human Project Room approval of the exact rendered package is required before any external use.
