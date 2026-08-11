# Numeric and Lineage Review

Result: **PASS**. The rendered internal package is numerically clean. Both requested validators passed, all nine scores recomputed, every named fact group passed, substantive lineage coverage is 100%, unexplained substantive numbers are 0, and cross-document consistency is PASS.

The review covered the one-page HTML and PDF plus the number explainer in Markdown, HTML, and PDF. Independent checks used PDF text extraction and direct decimal arithmetic. The source score review, score contract, source dictionary, receipt manifest, and substantive number inventory also reconcile.

## Score checks

| Score | Display | Full precision | Weight total | Arithmetic and rounding | Result |
| --- | ---: | ---: | ---: | --- | --- |
| Market Demand-Supply | 61 | 60.50 | 1.00 | 16.25 + 10.00 + 9.75 + 9.75 + 9.75 + 5.00 = 60.50; half-up = 61 | PASS |
| Competitive Pressure Index | 57 | 56.75 | 1.00 | 20.00 + 16.25 + 13.00 + 7.50 = 56.75; half-up = 57 | PASS |
| Room to Win | 43 | 43.00 | Not applicable | 100 - rounded Competitive Pressure Index 57 = 43 | PASS |
| Practice Competitiveness | 61 | 60.50 | 1.00 | 10.00 + 13.00 + 13.00 + 9.75 + 9.75 + 5.00 = 60.50; half-up = 61 | PASS |
| Client Opportunity | 54 | 54.45 | 1.00 | 12.20 + 10.00 + 10.00 + 7.50 + 9.75 + 5.00 = 54.45; half-up = 54 | PASS |
| Digital Presence | 60 | 59.75 | 1.00 | 12.50 + 13.00 + 13.00 + 9.75 + 6.50 + 5.00 = 59.75; half-up = 60 | PASS |
| Dry eye / ocular surface | 53 | 53.00 | 1.00 | 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00; half-up = 53 | PASS |
| Myopia management | 53 | 53.00 | 1.00 | 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00; half-up = 53 | PASS |
| Specialty contact lenses | 51 | 50.75 | 1.00 | 10.00 + 7.50 + 9.75 + 7.50 + 7.50 + 5.00 + 3.50 = 50.75; half-up = 51 | PASS |

Every component contribution equals value times weight. Every weighted score totals 1.00. Each full-precision total matches the sum of its contributions, and each display uses one final half-up rounding step. Room to Win is the declared exception because it is not independently weighted.

## Fact checks

| Fact group | Independent result | Cross-document result |
| --- | --- | --- |
| Five-window catchment | All five rows match: population, households, under 18, age 40-64, age 65+, and diabetes | PASS |
| Population growth | 17,565 - 17,172 = 393; 393 / 17,172 x 100 = 2.288609364081062...%; display 2.29% | PASS |
| School enrollment growth | 3,365 - 3,238 = 127; 127 / 3,238 x 100 = 3.922174181593576...%; display 3.92%; 2023-24 remains missing and not interpolated | PASS |
| Corrected Focus route | 233.4 / 60 = 3.89 minutes; 2,466.8 / 1,609.344 = 1.532798457011055... miles; display 1.53 miles | PASS |
| Direct Google sample | Vintage 4.9 / 348; Focus 4.8 / 182; Tri-County 4.9 / 271; Walmart 3.5 / 8 | PASS |
| Birdeye discrepancies | 398 - 348 = 50; 210 - 182 = 28; source separation preserved | PASS |
| Candidate supply | NPPES 40 reported, 39 materialized, 1 deficit; 24 location candidates; 21 geocoder matches and 3 no-matches; window counts 4 / 4 / 8 / 16 / 20 and competitor counts 2 / 2 / 6 / 14 / 18 | PASS |
| Null denominators | All declared nulls and the missing school value remain unfilled; unknown-to-zero conversions: 0 | PASS |

The preserved nulls cover canonical full VDU, canonical office count, all five canonical-office window cells, full VDU per office, complete provider entity dedupe, rank grid, cross-platform review total, negative ACS sentinels, three no-match geocoder coordinates, and 2023-24 school enrollment. Population per office, full VDU per office, canonical supply ratios, and patient-choice denominators remain uncomputed as required.

## Lineage result

- Substantive inventory entries checked: 2,593
- Cross-format numeric assertions: 147
- Required-field failures: 0
- Unregistered source-ID failures: 0
- Artifact visibility failures: 0
- Substantive lineage coverage: 100%
- Unexplained substantive numbers: 0
- Evidence review to score contract: exact match
- HTML, Markdown, and PDF semantic values: PASS

## Nonblocking caveats

Room to Win records 43.00 because the approved formula inverts the rounded Competitive Pressure Index display: 100 - 57 = 43. The raw complement of the unrounded 56.75 would be 43.25, but that is not the package formula.

The compact one-page PDF places the Google comparison beside route text. PDF text extraction interleaves those adjacent columns around the Tri-County row, but 4.9 and 271 are present on the same rendered row and match the HTML and explainer.

## Release boundary

This is an internal-only rendered candidate. PASS does not authorize external delivery. Human Project Room approval of the exact rendered package remains required before any external use.
