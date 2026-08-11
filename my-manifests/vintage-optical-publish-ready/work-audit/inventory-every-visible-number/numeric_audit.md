# Vintage Optical numeric-lineage audit

Verdict: PASS

Scope: rendered `onepager.html` and `onepager.pdf` for Vintage Optical, Morton, dated 2026-07-30. The artifacts remain internal and unroomed. This audit authorizes no delivery, publication, form submission, contact, or external action.

The HTML and PDF have the same multiset of 122 visible digit-bearing tokens. Four visible spelled-number occurrences bring the content inventory to 126 atomic numeric occurrences. Every substantive occurrence is traced; every display-only number is classified and explained in `number_inventory.json`.

## Headline scores

All scores use manual directional bands and nearest-whole-point rounding. The displayed scores are high-good. Competitive Pressure is the sole high-worse internal score and is intentionally represented on the page by its high-good inversion, Room to Win.

| Score | Display | Independent calculation | Result | Evidence boundary |
|---|---:|---|---:|---|
| Market Demand-Supply | 57 / 100 | `0.25×65 + 0.20×50 + 0.15×65 + 0.15×50 + 0.15×65 + 0.10×35 = 56.75` | 57 | Directional public-only score; city context is not catchment proof. |
| Competitive Pressure, internal | not displayed | `0.40×50 + 0.25×65 + 0.20×65 + 0.15×50 = 56.75` | 57 | Named routed peers are not a complete supply or patient-choice census. |
| Room to Win | 43 / 100 | `100 - 57` | 43 | Exact high-good inversion of internal pressure. |
| Practice Competitiveness | 58 / 100 | `0.20×50 + 0.20×65 + 0.20×50 + 0.15×65 + 0.15×65 + 0.10×50 = 57.50` | 58 | Public booking and service breadth are positive; peer-normalized visibility, reputation, live access, and operations are missing. |
| Client Opportunity | 54 / 100 | `0.20×57 + 0.20×50 + 0.20×50 + 0.15×50 + 0.15×65 + 0.10×50 = 53.65` | 54 | No leakage, capacity, economics, or execution capacity is assumed. |
| Digital Presence | 57 / 100 | `0.25×50 + 0.20×50 + 0.20×65 + 0.15×65 + 0.10×65 + 0.10×50 = 56.75` | 57 | Bookability, site structure, and specialty content are directional; rank, reputation, conversion, and social/local proof remain neutral or unmeasured. |

Specialty scores also recompute exactly:

| Lane | Display | Independent calculation | Result | Read |
|---|---:|---|---:|---|
| Dry eye / ocular surface | 52 / 100 | `0.20×65 + 0.15×35 + 0.15×65 + 0.15×50 + 0.15×50 + 0.10×50 + 0.10×35 = 51.50` | 52 | Research next |
| Myopia management | 52 / 100 | Same component pattern as dry eye = `51.50` | 52 | Research next |
| Specialty contact lenses | 51 / 100 | `0.20×50 + 0.15×50 + 0.15×65 + 0.15×50 + 0.15×50 + 0.10×50 + 0.10×35 = 50.75` | 51 | Research next |

The repeated denominator `100` appears eight times. It is the common display scale, not eight raw facts. The three visible `57` occurrences refer to Market Demand-Supply once and Digital Presence twice; the separate internal Competitive Pressure value of 57 is not visible.

## Raw public facts

| Visible value | Lineage | Why it is present | Limitation |
|---|---|---|---|
| 17,557, labeled 2024 city estimate | Census QuickFacts S14 → `data/market_inputs.json` | City population context | Not a 20-minute catchment population |
| 25.9%, under age 18 | Census QuickFacts S14 → `under_18_percent_2020_2024` | Directional family-demand proxy | The `18` is the age threshold, not a separate measured value; city is not catchment |
| 23.1%, age 65 or older | Census QuickFacts S14 → `age_65_plus_percent_2020_2024` | Directional age-demand proxy | The `65` is the age threshold, not a separate measured value; city is not catchment |
| 605 S Main St | Official location S02 plus geocode receipt N00 | Identifies the analyzed location | `605` is an address number, not a quantity |

No other values present in `market_inputs.json`, such as income, density, commute, ACS population, or median age, are displayed on the page.

## Route values

The page displays one route magnitude: **4.07 routed minutes** from Vintage Optical to Focus On Eyes. R01 stores an OSRM duration of 244.3 seconds; `244.3 / 60 = 4.071666…`, displayed as 4.07. The route is a single subject-origin point-to-point observation with no live traffic or time-of-day model. It is not an isochrone, a complete supply census, or a patient-origin choice set.

The visible **20-minute** phrase is the selected exurban primary-window method and, more importantly, a limitation: Morton city facts do not describe that drive-time catchment. Canonical `CALCULATIONS.md` assigns exurban markets a 20-minute primary and 30-minute extended window. This run's exurban classification is directional because no catchment density surface or trip-tolerance study was completed.

Other stored route values and the 30-minute extended window are not displayed as numeric route facts on this page. Source IDs R03, R04, and R05 are visible citations, not displayed route durations.

## Fix Card math

The **30-day** timing appears eight times: seven plan/action/owner/proof occurrences plus one formula denominator in F-003. It is a baseline-measurement window, not a forecast period.

- F-001: `inquiry-to-book = booked evaluations / inquiries`; `book-to-start = starts / booked evaluations`; `completion = completed plans / starts`.
- F-002: `access gap = unanswered or abandoned calls + incomplete booking attempts + requests without acceptable slots`; `gap rate = access gap / total access attempts`.
- F-003: `listing accuracy = correct tracked listings / tracked listings`; `review velocity = new verified reviews / 30 days`; referral or recall booking rate = `booked / eligible inquiries or contacts`.

These are plug-in formulas only. No current count, rate, patient result, revenue result, or forecast is asserted. Denominator scope, zero-denominator handling, disposition rules, listing scope, verified-review rules, and referral/recall eligibility must be defined before use.

The page says **Exactly three GROW Fix Cards**, matching F-001, F-002, and F-003 in `scores.json` and the runbook maximum of three do-now cards. It says **three existing specialty lanes**, matching the three `specialty_options`. F-001 requires **one table** as the consolidated proof artifact. Those are plan counts, not performance metrics.

## Structural numbers

Every structural number is structural for a specific reason:

- Section **1**, **2**, and **3** are ordinal navigation labels for Your Market, Your Competition, and Your Opportunity. They neither measure nor rank anything.
- **TIER 1** appears twice and **TIER 2** once. These numerals name peer-taxonomy classes. They are not competitor counts, measured ranks, or scores.
- **F-001**, **F-002**, and **F-003** are stable Fix Card identifiers. Their numeric suffixes encode identity/order, not magnitude.
- The score denominator **100** is a repeated scale/formula token.
- **© 2026** is the copyright year only.
- No printed URL exists. Numeric strings confined to link targets, SVG geometry, CSS, PDF metadata, or ARIA text are not visible occurrences and are excluded. Visible URL-only tokens: zero.

## Source identifiers

There are 75 visible source-ID occurrences across 20 distinct IDs:

| ID | Occurrences | Registered evidence |
|---|---:|---|
| S01 | 7 | Official subject website |
| S02 | 4 | Official subject hours/location |
| S03 | 5 | Official dry-eye page |
| S04 | 5 | Official myopia page |
| S05 | 5 | Official specialty-contact page |
| S06 | 8 | Public booking flow |
| S07 | 2 | Focus On Eyes official site |
| S08 | 4 | Tri-County official site |
| S09 | 3 | Vision Care Center official site |
| S10 | 2 | Vision Care Center myopia page |
| S11 | 1 | Bard Optical East Peoria page |
| S12 | 2 | Illinois Eye Center Washington page |
| S14 | 8 | Census QuickFacts |
| S15 | 2 | Census ACS documentation |
| S16 | 7 | Dated partial Google Maps sample |
| N00 | 2 | Subject Nominatim geocode receipt |
| R01 | 3 | Focus On Eyes OSRM route receipt |
| R03 | 2 | Tri-County OSRM route receipt |
| R04 | 2 | Vision Care Center OSRM route receipt |
| R05 | 1 | Bard Optical OSRM route receipt |

The digits inside these labels identify registry entries. They are not observations. S13, R02, and R06 are registered and used in the underlying evidence/scoring pack but are not visibly cited on the rendered page.

## Duplicates and repetition

The repeated score values reconcile:

- 54 appears twice, both Client Opportunity.
- 43 appears twice, both Room to Win.
- 58 appears twice, both Practice Competitiveness.
- 57 appears three times: once for Market Demand-Supply and twice for Digital Presence.
- 52 appears twice for two distinct specialty lanes with the same component pattern.
- 51 appears once for specialty contact lenses.
- 100 appears eight times as the shared score-scale denominator.
- 30 appears eight times across the common baseline window and the F-003 review-velocity formula.

HTML and PDF token counts match exactly, so there is no numeric drift between the two rendered forms.

## Limitations

- PASS means numeric lineage is complete for the rendered page. It does not mean the public-only analysis is client-ready, room-reviewed, or authorized for external use.
- Neutral 50 component bands are explicit unknown handling. They are not measured average performance.
- The Market Demand-Supply, Competitive Pressure, Practice Competitiveness, Client Opportunity, Digital Presence, and specialty scores are directional bands, not source-of-record operating measurements.
- Morton city facts are not drive-time catchment facts.
- Routed peers are a bounded named set, not a complete office/provider census or patient-origin model.
- Official pages verify published claims and paths, not utilization, conversion, capacity, outcomes, patient draw, or economics.
- The dated Maps sample is not a peer-normalized reputation export.
- Fix Card formulas define future measurement. They contain no current performance result.

Unexplained substantive numbers: none
