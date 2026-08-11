# Fresh Numeric and Lineage Review

## Exact result

**PASS.** No blocking numeric, rounding, lineage, null-preservation, or cross-document consistency finding was identified.

- Both required build and render validators passed.
- Independent Python arithmetic passed for every component, contribution, weight total, full-precision total, half-up display, and Room-to-Win inversion.
- Independent PDF text extraction matched the accepted substantive values.
- Substantive lineage coverage is 100%.
- Unexplained substantive number count is 0.
- Cross-document consistency is PASS.
- The template-framed page contains no numeric claim outside the approved inventory and no dollar projection.
- External actions taken: none.

## Score checks

| Score | Full precision | Display | Arithmetic | Weight total | Result |
| --- | ---: | ---: | --- | ---: | --- |
| Market Demand-Supply | 60.50 | 61 | 16.25 + 10.00 + 9.75 + 9.75 + 9.75 + 5.00 = 60.50 | 1.00 | PASS |
| Competitive Pressure Index | 56.75 | 57 | 20.00 + 16.25 + 13.00 + 7.50 = 56.75 | 1.00 | PASS |
| Room to Win | 43.00 | 43 | 100 - 57 = 43 | Not applicable | PASS |
| Practice Competitiveness | 60.50 | 61 | 10.00 + 13.00 + 13.00 + 9.75 + 9.75 + 5.00 = 60.50 | 1.00 | PASS |
| Client Opportunity | 54.45 | 54 | 12.20 + 10.00 + 10.00 + 7.50 + 9.75 + 5.00 = 54.45 | 1.00 | PASS |
| Digital Presence | 59.75 | 60 | 12.50 + 13.00 + 13.00 + 9.75 + 6.50 + 5.00 = 59.75 | 1.00 | PASS |
| Dry eye / ocular surface | 53.00 | 53 | 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00 | 1.00 | PASS |
| Myopia management | 53.00 | 53 | 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00 | 1.00 | PASS |
| Specialty contact lenses | 50.75 | 51 | 10.00 + 7.50 + 9.75 + 7.50 + 7.50 + 5.00 + 3.50 = 50.75 | 1.00 | PASS |

All weighted scores use one final ROUND_HALF_UP step. Client Opportunity correctly remains 54 because 54.45 is below the 54.50 threshold. Room to Win is the exact inversion of the rounded Competitive Pressure Index.

## Fact checks

| Fact group | Verified values | Result |
| --- | --- | --- |
| Five-window catchment | All population, household, under-18, age 40-64, age 65-plus, and diabetes values for 5, 10, 15, 20, and 30 minutes match the accepted facts | PASS |
| Population growth | 17,172 to 17,565, change 393; 393 / 17,172 x 100 = 2.2886093641%, displayed 2.29% | PASS |
| School enrollment growth | 3,238 to 3,365, change 127; 127 / 3,238 x 100 = 3.9221741816%, displayed 3.92%; 2023-24 remains missing and not interpolated | PASS |
| Focus route | 233.4 seconds / 60 = 3.89 minutes; 2,466.8 meters = 1.53 miles after display rounding | PASS |
| Google review sample | Vintage 4.9 / 348; Focus 4.8 / 182; Tri-County 4.9 / 271; Walmart 3.5 / 8 | PASS |
| Birdeye discrepancies | 398 - 348 = 50; 210 - 182 = 28 | PASS |
| Candidate supply counts | 40 reported NPPES results, 39 materialized records, 24 location candidates, 21 geocoder matches, 3 no-matches; window candidates 4 / 4 / 8 / 16 / 20 and competitor candidates 2 / 2 / 6 / 14 / 18 | PASS |
| Null denominators | Canonical full VDU, canonical office count, rank grid, complete provider entity dedupe, patient-origin choice, live traffic, conversion, capacity, outcomes, economics, and cross-platform review total remain null or unknown | PASS |

The HTML, Markdown, standard one-pager PDF, template-framed one-pager PDF, and number-explainer PDF agree on every substantive number they display. Every reviewed score, component, promotable fact, and preserved null resolves to accepted source IDs and receipt lineage.

## Nonblocking caveat

The template-framed page labels four proof-to-unlock rows, while its First 30 Days footer lists three immediate actions. The scopes are explicitly distinct, so this does not change an approved score, fact, arithmetic result, or lineage claim.

## Release boundary

This package remains internal-only. Human Project Room approval of the exact rendered package is required before any external use.
