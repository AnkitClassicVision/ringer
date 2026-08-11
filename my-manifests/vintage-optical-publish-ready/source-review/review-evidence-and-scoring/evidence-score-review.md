# Source-quality and scoring decision memo

Verdict: PASS.

All three prerequisite packet validators passed. The source packets are internally consistent, their receipts resolve, and the report can be rebuilt without inventing values. The highest truthful state is `EVIDENCE_REVIEWED_REPORT_REBUILD_REQUIRED`. External actions taken: none.

## Accepted facts

- All five modeled drive-time windows now have publishable demographic displays:

| Window | Population | Households | Under 18 | Age 40-64 | Age 65+ | Diabetes context |
|---:|---:|---:|---:|---:|---:|---:|
| 5 minutes | 6,624 | 2,722 | 1,712 | 1,811 | 1,311 | 9.6% |
| 10 minutes | 19,322 | 7,873 | 4,571 | 5,843 | 4,291 | 10.9% |
| 15 minutes | 54,768 | 23,793 | 11,707 | 17,431 | 10,939 | 12.4% |
| 20 minutes | 173,058 | 75,244 | 38,652 | 53,102 | 32,473 | 13.2% |
| 30 minutes | 283,661 | 120,940 | 64,831 | 86,558 | 53,258 | 12.3% |

Source IDs: `GOOGLE_MAPS_SAMPLE_20260730`, `VALHALLA_20260730`, `TIGER2024_BG`, `ACS2024_BG`, and `CDC_PLACES_2025`. These are area-weighted aggregate estimates inside modeled polygons. They are not patient-origin facts, and the routing has no live traffic.

- Morton village population increased from 17,172 in 2020 to 17,565 in 2025, an observed increase of 393 or 2.29%. Source: `CENSUS_PEP_2025`.
- Morton CUSD 709 enrollment increased from 3,238 in 2022-2023 to 3,365 in 2025-26, an observed increase of 127 or 3.92%. The 2023-24 value remains missing and was not interpolated. Source: `MORTON709_FIRST_PARTY_ARCHIVE`.
- The corrected Focus On Eyes route is 233.4 seconds, 3.89 minutes, and 1.53 miles using direct Google listing pins. Sources: `GOOGLE_MAPS_SAMPLE_20260730`, `GOOGLE_MAPS_FOCUS_SAMPLE_20260730`, and `OSRM_FOCUS_GOOGLE_PINS_20260730`.
- One dated direct Google page shows Vintage Optical at 4.9 with 348 reviews, Focus On Eyes at 4.8 with 182, Tri-County Eye Center at 4.9 with 271, and Walmart Vision & Glasses at 3.5 with 8. Source: `GOOGLE_MAPS_FOCUS_SAMPLE_20260730`. This supports a bounded review-trust comparison only.
- Birdeye's Google components exceed the direct Google counts by 50 for Vintage Optical and 28 for Focus On Eyes. Sources: `BIRDEYE_AGGREGATOR_20260730` and `GOOGLE_MAPS_FOCUS_SAMPLE_20260730`. Keep the observations separate.

## Rejected promotions

Canonical full VDU, canonical office count, rank grid, and complete provider entity dedupe remain null. The NPPES collection is city-query-bounded, reports 40 results but materializes 39, has three geocoder no-matches, lacks complete entity resolution, and is not a full 30-minute office sweep. It is coverage and contradiction evidence only.

Patient-origin choice, live traffic, conversion, capacity, clinical outcomes, payer mix, economics, and cross-platform review totals remain unknown. DataForSEO remains `unavailable_missing_credentials`; request sent remains false; cost remains 0; rank grid remains `not_run`. Exa and Perplexity summaries are discovery coverage, not publication evidence.

## Score decisions

The allowed manual bands remain 20, 35, 50, 65, and 80. Weighted totals retain full precision and round once to the nearest whole point, with .50 rounded up.

| Score | Current | Recommended | Decision |
|---|---:|---:|---|
| Market Demand-Supply | 57 | 61 | Change |
| Competitive Pressure Index | 57 | 57 | Preserve |
| Room to Win | 43 | 43 | Preserve |
| Practice Competitiveness | 58 | 61 | Change |
| Client Opportunity | 54 | 54 | Preserve |
| Digital Presence | 57 | 60 | Change |
| Dry eye / ocular surface | 52 | 53 | Change |
| Myopia management | 52 | 53 | Change |
| Specialty contact lenses | 51 | 51 | Preserve |

Market Demand-Supply becomes 61:

`0.25x65 + 0.20x50 + 0.15x65 + 0.15x65 + 0.15x65 + 0.10x50 = 60.50`, rounded half up to 61.

Growth / Future Demand moves from 50 to 65 because two direct observed series now show positive change. Market Data Confidence moves from 35 to 50 because all five fixed windows and the growth series are validated, while canonical supply and full VDU remain incomplete. Demand Strength, Payer / Income Fit, and Specialty Demand Load stay at 65. Supply Balance stays at 50.

Competitive Pressure remains 57:

`0.40x50 + 0.25x65 + 0.20x65 + 0.15x50 = 56.75`, rounded to 57.

The route correction does not change peer proximity. Candidate locations cannot change saturation or patient choice. The direct review comparison reinforces, but does not change, the 65 Competitor Strength band.

Room to Win remains an exact inversion:

`Room to Win = 100 - Competitive Pressure Index = 100 - 57 = 43`.

It is not independently banded.

Practice Competitiveness becomes 61:

`0.20x50 + 0.20x65 + 0.20x65 + 0.15x65 + 0.15x65 + 0.10x50 = 60.50`, rounded half up to 61.

Review Trust vs Peers moves from 50 to 65 because the same-page direct Google comparison supplies a bounded positive volume-and-rating comparison. It does not support an 80 band or a complete peer claim.

Client Opportunity remains 54:

`0.20x61 + 0.20x50 + 0.20x50 + 0.15x50 + 0.15x65 + 0.10x50 = 54.45`, rounded to 54.

The computed market input changes from 57 to 61, but the final score does not reach the .50 rounding threshold. Competitor weakness, leakage, capacity, conversion, and execution ownership remain unproved.

Digital Presence becomes 60:

`0.25x50 + 0.20x65 + 0.20x65 + 0.15x65 + 0.10x65 + 0.10x50 = 59.75`, rounded to 60.

Reputation moves from 50 to 65 on the bounded direct comparison. Findability remains 50 because no rank grid ran.

Dry eye and myopia each become 53:

`0.20x65 + 0.15x35 + 0.15x65 + 0.15x50 + 0.15x50 + 0.10x50 + 0.10x50 = 53.00`.

Evidence Confidence moves from 35 to 50 for both lanes because direct catchment evidence now replaces city-only proxies. All demand, competitive-gap, capability, capacity, revenue, and referral bands remain fixed. Both scores remain in the rubric's Research next range.

Specialty contact lenses remains 51. The new packets do not establish contact-lens demand, keratoconus burden, specialty-depth competition, fitting capacity, referrals, outcomes, or economics. No component crosses a band.

## Superseded claims

- `OLD_ROUTE_FOCUS_4_07`: replace 4.07 minutes and 1.56 miles with 3.89 minutes and 1.53 miles.
- `OLD_NO_CATCHMENT_DEMOGRAPHICS`: replace the claim that fixed-window demographics are unavailable with the validated five-row catchment table.
- `OLD_NO_GROWTH_EVIDENCE`: replace the no-growth-evidence claim with observed Morton population and Morton CUSD 709 enrollment changes.

## Contradictions and blockers

Birdeye displays Vintage Optical at the legacy 417 W Jefferson St address while the direct Google observation lists 605 S Main St. The old address remains a citation conflict, not an operating-status conclusion.

The Birdeye review components and direct Google counts disagree. The report must retain both source-specific observations and must not average ratings, sum counts, or call an aggregator component direct Google truth.

The report remains blocked from release until the one-pager and explainer are rebuilt, all substantive numbers have source lineage, both PDFs pass visual QA, internal paths are absent, fresh numeric, logic, and technical reviews pass, and the human Project Room owner approves the exact package.

Next rebuild action: apply `report-update-contract.json` to rebuild the HTML, Markdown, and PDFs without changing the approved scoring formulas or promoting null fields.
