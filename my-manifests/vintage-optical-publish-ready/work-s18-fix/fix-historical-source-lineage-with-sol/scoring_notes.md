# Vintage Optical GROW scoring notes

## Boundary

- Schema: `2.0`
- Product: `single_practice`
- Method: `manual_directional_banding_public_only`
- Visibility: `internal_only_unroomed_draft`
- Project Room: `inventory_review_required`
- Use: `INTERNAL-ONLY / NOT FOR EXTERNAL USE`
- External actions taken: `none`

The score stack remains grounded in the named rubric files and verified evidence pack. This refresh names S17 as the current city-population authority and S18 as the frozen historical authority for 17,557 without changing any score input. The score effect is none. The invalid prior headline scores 59, 56, 72, and 66 and their continuous component values were not used.

## Scoring discipline

Every base component is 20, 35, 50, 65, or 80. Unknowns receive 50 and `neutral_unknown_no_directional_claim`. Each component has a parallel basis record in `scores.json` with a band label, self-contained rationale, source IDs, confidence, and unknown handling.

Composites use the canonical weights and nearest-whole-point rounding. Client Opportunity uses the computed Market Demand-Supply Score at 20 percent. Room to Win is exactly 100 minus the internal Competitive Pressure Index.

## Score read

- Market Demand-Supply: 57, mixed. The current Morton village population is 17,565 for 2025, while city age and income context remains directionally supportive. Fixed-window demand, VDU, supply, growth, and choice measurements are missing.
- Internal Competitive Pressure: 57, high pressure. Named routes and service overlap support a directional pressure read, but the supply and patient-choice census is incomplete.
- Room to Win: 43, tight. This is the direct inversion of internal pressure.
- Practice Competitiveness: 58, mixed. Public booking, hours, service pages, and specialty breadth are useful, while visibility, reputation, location convenience, and operating performance lack peer-normalized proof.
- Client Opportunity: 54 by the canonical calculation. The measurement and digital-proof work is actionable, but no leakage, capacity, or specialty economics is assumed.
- Digital Presence: 57 by the canonical calculation. The site and booking surface are directionally useful, while findability, reputation, and social/local proof remain neutral or unmeasured.
- Confidence: C. This is public data plus a directional local and competitor scan.

## Current-number refresh

- S17 reports the current Morton village, Illinois 2025 population estimate as 17,565.
- S18, the earlier official 2024-vintage PEP file, remains the authority for the historical 17,557 used in the previous report.
- The official 2025-vintage PEP file revises its 2024 estimate to 17,555. That back-series revision is documented but does not overwrite the earlier vintage's historical lineage.
- S14 continues to support the current QuickFacts age shares of 25.9% under age 18 and 23.1% age 65 or older.
- The frozen route refresh again resolves Focus On Eyes at 4.07 minutes.
- These refreshed facts do not move a manual band. Market Demand-Supply remains 57, internal Competitive Pressure remains 57, Room to Win remains 43, Practice Competitiveness remains 58, Client Opportunity remains 54, Digital Presence remains 57, specialty scores remain 52, 52, and 51, and Confidence remains C.

## Hidden raw pressure metadata

The internal Competitive Pressure Index is 57. Its components are supply saturation 50, patient choice pressure 65, competitor strength 65, and access/differentiation pressure 50. The result is not a complete-market pressure measurement because supply, provider density, patient-origin choice, peer reputation, and live access are incomplete.

## Missing evidence that would upgrade the read

- Polygon isochrones and block-group joins for all five fixed windows
- Complete geocoded and deduplicated office census
- NPPES provider join and address cleaning
- Catchment-weighted VDU and clinical-demand inputs
- Population-weighted patient-choice distribution
- Independent review export and rank-grid or owned visibility data
- Booking, call, slot, cancellation, no-show, and unmet-request summaries
- Lane-level inquiry, start, completion, capacity, and staffing data
- Review, referral, recall, and optical-capture baselines
- Payer, collections, margin, and lane economics

## Disconfirmers

1. A complete supply census could move pressure materially in either direction.
2. Vintage already publishes broad specialty services and a booking path, so lack-of-offer and lack-of-access claims are disproven.
3. Regional peers publicly overlap on dry eye and myopia, so public breadth does not establish lane ownership.
4. The 4.9 Maps sample may not represent peer-normalized reputation once count, recency, response, and peer fields are collected.
5. Subject-origin point routes may not represent actual patient origins, live traffic, or willingness to travel.
6. Public pages may overstate or understate actual conversion, capacity, outcomes, and economics.
7. Morton city demographics may differ from the 20-minute catchment.

## Scoring limitations

- City demographic values are context only and are not substituted into drive-time windows.
- The S17 current estimate of 17,565 and S18 historical 17,557 lineage are village-boundary values, not population inputs for any 5, 10, 15, 20, or 30-minute window.
- Known routed alternatives are not treated as a complete office census.
- Sampled query visibility is directional, not a rank grid.
- The 4.9 Maps sample has no review count and does not support peer-normalized reputation.
- Official pages prove public claims and paths, not utilization, completed visits, operating capacity, referral strength, conversion, or financial performance.
- Neutral 50s preserve uncertainty. They do not reward missing evidence.
- Specialty scores remain research-next reads because capacity, conversion, referral proof, and economics are absent.
- Fix Card math is sensitivity or plug-in math only. It is not a patient, revenue, or dollar forecast.

## Decision residue

- Hardest decision: separate real directional signals from missing proof without turning public claims into operating performance. Public age and income context, stored routes, hours, booking flow, and service pages justified a few 65 bands. Missing catchment, supply, reputation, capacity, conversion, referral, and economics inputs stayed neutral 50.
- Source-vintage decision: use S17 for the current 2025 estimate, keep S18 and the earlier 2024-vintage file authoritative for the historical 17,557, and document the 2025 file's revised 2024 back-series value without treating it as a score change. Score effect: none.
- Rejected alternative: convert the prior continuous values into nearest manual bands. That would preserve invalid prior assumptions rather than rescore from the verified pack.
- Rejected alternative: score the 4.9 Maps sample above neutral reputation. Without count, recency, responses, and peer fields, it cannot establish comparative trust.
- Rejected alternative: infer specialty white space from Vintage's service breadth. Tri-County and Vision Care Center show public overlap, and no lane-level operating proof exists.
- Least-confident assumption: the bounded named peer set is representative enough for a directional 65 patient-choice and competitor-strength band. A complete supply census or patient-origin analysis could change both.

## Verification target

The scoring artifact should pass four checks: valid JSON, every base component in the allowed five-band set, exact canonical weight recomputation, and Room to Win equal to 100 minus internal Competitive Pressure.
