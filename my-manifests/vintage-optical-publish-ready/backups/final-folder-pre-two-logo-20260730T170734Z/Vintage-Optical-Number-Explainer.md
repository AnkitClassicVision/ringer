# Vintage Optical Number Explainer

Internal-only. Human Project Room approval is required before external use.

Evidence-reviewed rebuild dated 2026-07-30. Public-only confidence grade: C. Rendered internal candidate.

This document explains every score, fact, arithmetic step, source ID, and boundary used in the one-page report. All score displays are higher = better except Competitive Pressure Index, where higher = more pressure.

Room to Win = 100 - Competitive Pressure Index

The approved manual bands are 20, 35, 50, 65, and 80. Each weighted score keeps its original weights, sums full-precision contributions, and uses one final ROUND_HALF_UP step. Unknown values stay null.

## Market Demand-Supply: 61 / 100

Direction: Higher means better for the client.

Full precision: 16.25 + 10.00 + 9.75 + 9.75 + 9.75 + 5.00 = 60.50. One final ROUND_HALF_UP step produces 61.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Demand Strength | 65 | 0.25 | 65 x 0.25 = 16.25 | VALHALLA_20260730, TIGER2024_BG, ACS2024_BG | medium |
| Supply Balance | 50 | 0.20 | 50 x 0.20 = 10.00 | NPPES_CURRENT_20260730, CENSUS_GEOCODER_20260730, CATCHMENT_DEMOGRAPHICS_20260730 | medium |
| Payer / Income Fit | 65 | 0.15 | 65 x 0.15 = 9.75 | ACS2024_BG | medium |
| Growth / Future Demand | 65 | 0.15 | 65 x 0.15 = 9.75 | CENSUS_PEP_2025, MORTON709_FIRST_PARTY_ARCHIVE | medium |
| Specialty Demand Load | 65 | 0.15 | 65 x 0.15 = 9.75 | ACS2024_BG, CDC_PLACES_2025, MORTON709_FIRST_PARTY_ARCHIVE | medium |
| Market Data Confidence | 50 | 0.10 | 50 x 0.10 = 5.00 | VALHALLA_20260730, TIGER2024_BG, ACS2024_BG, CDC_PLACES_2025, CENSUS_PEP_2025, MORTON709_FIRST_PARTY_ARCHIVE, NPPES_CURRENT_20260730 | medium |

The display changed from 57 to 61. Observed positive population and school-enrollment change moves Growth / Future Demand from 50 to 65. Complete fixed-window demographics move Market Data Confidence from 35 to 50. Demand Strength, Payer / Income Fit, and Specialty Demand Load remain at 65 because the new evidence confirms their supportive state but does not justify an 80 band. Supply Balance remains neutral 50 because canonical full VDU and canonical office count are still null.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Demand Strength | All five windows now have population, household, and age-band estimates, but no benchmark or realized-demand evidence supports an 80 band. | Growth is observed village and district context, not a forecast. Supply balance, canonical VDU, payer mix, and realized demand remain unknown. The recommended 61 stays in the rubric's Mixed market range. |
| Supply Balance | The NPPES locations are coverage candidates only. Canonical office count and full VDU remain null, so no VDU-per-office state exists. | Growth is observed village and district context, not a forecast. Supply balance, canonical VDU, payer mix, and realized demand remain unknown. The recommended 61 stays in the rubric's Mixed market range. |
| Payer / Income Fit | The catchment packet supplies approximate income context but not actual payer mix. The existing supportive band is preserved. | Growth is observed village and district context, not a forecast. Supply balance, canonical VDU, payer mix, and realized demand remain unknown. The recommended 61 stays in the rubric's Mixed market range. |
| Growth / Future Demand | Two direct observed series show positive change. The evidence supports a directional growth proxy, not a forecast or top band. | Growth is observed village and district context, not a forecast. Supply balance, canonical VDU, payer mix, and realized demand remain unknown. The recommended 61 stays in the rubric's Mixed market range. |
| Specialty Demand Load | Exact catchment age bands, diabetes context, and enrollment growth strengthen the existing pediatric, senior, and chronic-care support but do not establish search, referral, or realized specialty demand. | Growth is observed village and district context, not a forecast. Supply balance, canonical VDU, payer mix, and realized demand remain unknown. The recommended 61 stays in the rubric's Mixed market range. |
| Market Data Confidence | Direct, recent demographic and growth evidence resolves major gaps, but incomplete supply, full VDU, provider dedupe, and patient choice keep the aggregate market evidence mixed. | Growth is observed village and district context, not a forecast. Supply balance, canonical VDU, payer mix, and realized demand remain unknown. The recommended 61 stays in the rubric's Mixed market range. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: Growth is observed village and district context, not a forecast. Supply balance, canonical VDU, payer mix, and realized demand remain unknown. The recommended 61 stays in the rubric's Mixed market range.

## Competitive Pressure Index: 57 / 100

Direction: Higher means more competitive pressure; this is the internal diagnostic exception.

Full precision: 20.00 + 16.25 + 13.00 + 7.50 = 56.75. One final ROUND_HALF_UP step produces 57.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Supply Saturation | 50 | 0.40 | 50 x 0.40 = 20.00 | NPPES_CURRENT_20260730, CENSUS_GEOCODER_20260730 | medium |
| Patient Choice Pressure | 65 | 0.25 | 65 x 0.25 = 16.25 | OSRM_FOCUS_GOOGLE_PINS_20260730, OSRM_TABLE_20260730 | medium |
| Competitor Strength | 65 | 0.20 | 65 x 0.20 = 13.00 | GOOGLE_MAPS_FOCUS_SAMPLE_20260730, S07, S08, S09, S10, S11, S12 | medium |
| Access / Differentiation Pressure | 50 | 0.15 | 50 x 0.15 = 7.50 | S02, S06, S07, S08, S11 | medium |

The display stays 57. The corrected Focus route preserves the nearby-peer state. NPPES candidate locations cannot change Supply Saturation or Patient Choice Pressure because the roster is incomplete and not a canonical office census. The direct Google comparison reinforces the existing competitor-strength direction but does not justify a new band.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Supply Saturation | Canonical offices, provider entities, full VDU, and supply denominators remain null. | Canonical supply, patient-origin choice, complete peer reputation, live access, and live traffic remain unknown. The result remains in the High pressure band. |
| Patient Choice Pressure | Nearby routed alternatives remain directionally relevant, but candidate routes are not a complete, population-weighted patient-choice set. | Canonical supply, patient-origin choice, complete peer reputation, live access, and live traffic remain unknown. The result remains in the High pressure band. |
| Competitor Strength | Public service overlap and a bounded direct review comparison support a directional strength state, but not severe pressure or complete peer normalization. | Canonical supply, patient-origin choice, complete peer reputation, live access, and live traffic remain unknown. The result remains in the High pressure band. |
| Access / Differentiation Pressure | Published access and overlap remain mixed; live slots, conversion, and comparable peer friction are unmeasured. | Canonical supply, patient-origin choice, complete peer reputation, live access, and live traffic remain unknown. The result remains in the High pressure band. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: Canonical supply, patient-origin choice, complete peer reputation, live access, and live traffic remain unknown. The result remains in the High pressure band.

## Room to Win: 43 / 100

Direction: Higher means more room to win; exact inverse of Competitive Pressure Index.

Room to Win = 100 - Competitive Pressure Index = 100 - 57 = 43. Full precision is 43.00. It is not assigned an independent manual band.

| Input | Value | Rule |
| --- | --- | --- |
| Competitive Pressure Index | 57 | Exact display inversion |

The display stays 43. Room to Win is the exact inversion of the unchanged Competitive Pressure Index: 100 - 57 = 43. It is not independently banded.



What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: Any future change to Competitive Pressure must produce an equal and opposite change here.

## Practice Competitiveness: 61 / 100

Direction: Higher means better for the client.

Full precision: 10.00 + 13.00 + 13.00 + 9.75 + 9.75 + 5.00 = 60.50. One final ROUND_HALF_UP step produces 61.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Visibility vs Peers | 50 | 0.20 | 50 x 0.20 = 10.00 | DATAFORSEO_PREFLIGHT_20260730, GOOGLE_MAPS_FOCUS_SAMPLE_20260730 | medium |
| Access / Booking vs Peers | 65 | 0.20 | 65 x 0.20 = 13.00 | S02, S06, GOOGLE_MAPS_SAMPLE_20260730 | medium |
| Review Trust vs Peers | 65 | 0.20 | 65 x 0.20 = 13.00 | GOOGLE_MAPS_FOCUS_SAMPLE_20260730, BIRDEYE_AGGREGATOR_20260730 | medium |
| Service-Line Differentiation | 65 | 0.15 | 65 x 0.15 = 9.75 | S01, S03, S04, S05, S08, S09, S10 | medium |
| Website / Conversion Clarity | 65 | 0.15 | 65 x 0.15 = 9.75 | S01, S02, S03, S04, S05, S06 | medium |
| Location Convenience | 50 | 0.10 | 50 x 0.10 = 5.00 | S02, OSRM_FOCUS_GOOGLE_PINS_20260730 | medium |

The display changed from 58 to 61. The one dated same-page Google comparison moves Review Trust vs Peers from neutral 50 to bounded-supportive 65. Vintage shows 4.9 and 348 reviews on the peer card versus Focus at 4.8 and 182, Tri-County at 4.9 and 271, and Walmart Vision & Glasses at 3.5 and 8. All other bands remain unchanged. The sample is insufficient for an 80 band or a complete peer claim.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Visibility vs Peers | No rank grid or complete stable query set exists. | The review observation is one dated page, not a complete export, text/theme analysis, response analysis, or outcome measure. Rank, live access, conversion, and patient-origin convenience remain unknown. The recommended 61 remains in the Mixed band. |
| Access / Booking vs Peers | The public hours, emergency access, CTA, and booking path remain supportive, while live completion and equivalent peer friction are unknown. | The review observation is one dated page, not a complete export, text/theme analysis, response analysis, or outcome measure. Rank, live access, conversion, and patient-origin convenience remain unknown. The recommended 61 remains in the Mixed band. |
| Review Trust vs Peers | The direct same-page comparison supports a bounded positive volume-and-rating read. The Birdeye discrepancy prevents treating aggregator counts as direct truth. | The review observation is one dated page, not a complete export, text/theme analysis, response analysis, or outcome measure. Rank, live access, conversion, and patient-origin convenience remain unknown. The recommended 61 remains in the Mixed band. |
| Service-Line Differentiation | Vintage publishes broad services and peers publish overlapping lanes. No new evidence changes this band. | The review observation is one dated page, not a complete export, text/theme analysis, response analysis, or outcome measure. Rank, live access, conversion, and patient-origin convenience remain unknown. The recommended 61 remains in the Mixed band. |
| Website / Conversion Clarity | Public service, provider, location, hours, and booking paths remain visible. Conversion remains unmeasured. | The review observation is one dated page, not a complete export, text/theme analysis, response analysis, or outcome measure. Rank, live access, conversion, and patient-origin convenience remain unknown. The recommended 61 remains in the Mixed band. |
| Location Convenience | The corrected route confirms a nearby peer but does not measure patient origins or trip tolerance. | The review observation is one dated page, not a complete export, text/theme analysis, response analysis, or outcome measure. Rank, live access, conversion, and patient-origin convenience remain unknown. The recommended 61 remains in the Mixed band. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: The review observation is one dated page, not a complete export, text/theme analysis, response analysis, or outcome measure. Rank, live access, conversion, and patient-origin convenience remain unknown. The recommended 61 remains in the Mixed band.

## Client Opportunity: 54 / 100

Direction: Higher means better for the client.

Full precision: 12.20 + 10.00 + 10.00 + 7.50 + 9.75 + 5.00 = 54.45. One final ROUND_HALF_UP step produces 54.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Computed Market Demand-Supply | 61 | 0.20 | 61 x 0.20 = 12.20 | VALHALLA_20260730, ACS2024_BG, CDC_PLACES_2025, CENSUS_PEP_2025, MORTON709_FIRST_PARTY_ARCHIVE | medium |
| Competitive Pressure Opportunity | 50 | 0.20 | 50 x 0.20 = 10.00 | GOOGLE_MAPS_FOCUS_SAMPLE_20260730, S07, S08, S09, S10, S11, S12 | medium |
| Practice Differentiation Upside | 50 | 0.20 | 50 x 0.20 = 10.00 | S01, S03, S04, S05, S08, S09, S10 | medium |
| Access Fixability | 50 | 0.15 | 50 x 0.15 = 7.50 | S02, S06 | medium |
| Digital Visibility Fixability | 65 | 0.15 | 65 x 0.15 = 9.75 | S01, S02, S03, S04, S05, S06, GOOGLE_MAPS_FOCUS_SAMPLE_20260730 | medium |
| Execution Simplicity | 50 | 0.10 | 50 x 0.10 = 5.00 | S01, S02, S06 | medium |

The display stays 54. The required computed Market Demand-Supply input changes from 57 to 61, raising the full-precision total from 53.65 to 54.45. The rounded score remains 54 because 54.45 does not reach the .50 half-up threshold. Review evidence does not prove competitor weakness, leakage, capacity, conversion, or execution ownership, so the other component bands stay fixed.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Computed Market Demand-Supply | The canonical formula uses the recomputed market result rather than a manual band. | Demand leakage, fixable competitor weakness, conversion, capacity, owner cadence, and execution capacity remain unknown. The score stays in the At Risk band. |
| Competitive Pressure Opportunity | Pressure exists, but no complete weakness cluster, leakage, or capacity-supported wedge is proven. | Demand leakage, fixable competitor weakness, conversion, capacity, owner cadence, and execution capacity remain unknown. The score stays in the At Risk band. |
| Practice Differentiation Upside | The offer is broad and lanes overlap. No new evidence establishes defensible ownership or unmet need. | Demand leakage, fixable competitor weakness, conversion, capacity, owner cadence, and execution capacity remain unknown. The score stays in the At Risk band. |
| Access Fixability | Public access exists, but access failure and recoverability remain unmeasured. | Demand leakage, fixable competitor weakness, conversion, capacity, owner cadence, and execution capacity remain unknown. The score stays in the At Risk band. |
| Digital Visibility Fixability | Existing surfaces and source discrepancies make measurement and reconciliation bounded actions, but no result is yet proven. | Demand leakage, fixable competitor weakness, conversion, capacity, owner cadence, and execution capacity remain unknown. The score stays in the At Risk band. |
| Execution Simplicity | The first actions remain bounded, but ownership and staff capacity are unknown. | Demand leakage, fixable competitor weakness, conversion, capacity, owner cadence, and execution capacity remain unknown. The score stays in the At Risk band. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: Demand leakage, fixable competitor weakness, conversion, capacity, owner cadence, and execution capacity remain unknown. The score stays in the At Risk band.

## Digital Presence: 60 / 100

Direction: Higher means better for the client.

Full precision: 12.50 + 13.00 + 13.00 + 9.75 + 6.50 + 5.00 = 59.75. One final ROUND_HALF_UP step produces 60.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Findability | 50 | 0.25 | 50 x 0.25 = 12.50 | DATAFORSEO_PREFLIGHT_20260730, GOOGLE_MAPS_FOCUS_SAMPLE_20260730 | medium |
| Reputation | 65 | 0.20 | 65 x 0.20 = 13.00 | GOOGLE_MAPS_FOCUS_SAMPLE_20260730, BIRDEYE_AGGREGATOR_20260730 | medium |
| Bookability | 65 | 0.20 | 65 x 0.20 = 13.00 | S06, GOOGLE_MAPS_SAMPLE_20260730 | medium |
| Site Quality | 65 | 0.15 | 65 x 0.15 = 9.75 | S01, S02, S03, S04, S05 | medium |
| Content / Specialty Signal | 65 | 0.10 | 65 x 0.10 = 6.50 | S03, S04, S05, S08, S09, S10 | medium |
| Social / Local Proof | 50 | 0.10 | 50 x 0.10 = 5.00 | S01, GOOGLE_MAPS_FOCUS_SAMPLE_20260730 | medium |

The display changed from 57 to 60. The direct same-page Google comparison moves Reputation from neutral 50 to bounded-supportive 65. Findability remains 50 because DataForSEO was unavailable and no rank grid ran. Bookability, Site Quality, Content / Specialty Signal, and Social / Local Proof remain unchanged.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Findability | A dated Google observation is not a rank grid or complete query-coverage measure. | The review comparison is one dated page, not a complete peer export. Rank distribution, review recency and themes, responses, booking completion, performance testing, directory coverage, and local proof remain unknown. The recommended 60 remains Mixed. |
| Reputation | The same-page direct comparison supports a bounded positive read, while source discrepancies block a stronger or cross-platform claim. | The review comparison is one dated page, not a complete peer export. Rank distribution, review recency and themes, responses, booking completion, performance testing, directory coverage, and local proof remain unknown. The recommended 60 remains Mixed. |
| Bookability | The public CTA and Book online path remain visible. Completion and conversion are unmeasured. | The review comparison is one dated page, not a complete peer export. Rank distribution, review recency and themes, responses, booking completion, performance testing, directory coverage, and local proof remain unknown. The recommended 60 remains Mixed. |
| Site Quality | The site exposes services, providers, location, and hours. No new performance or conversion testing changes the band. | The review comparison is one dated page, not a complete peer export. Rank distribution, review recency and themes, responses, booking completion, performance testing, directory coverage, and local proof remain unknown. The recommended 60 remains Mixed. |
| Content / Specialty Signal | Dedicated specialty pages remain present, and peer overlap prevents a stronger ownership state. | The review comparison is one dated page, not a complete peer export. Rank distribution, review recency and themes, responses, booking completion, performance testing, directory coverage, and local proof remain unknown. The recommended 60 remains Mixed. |
| Social / Local Proof | No complete social activity, local links, community mentions, or directory comparison was collected. | The review comparison is one dated page, not a complete peer export. Rank distribution, review recency and themes, responses, booking completion, performance testing, directory coverage, and local proof remain unknown. The recommended 60 remains Mixed. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: The review comparison is one dated page, not a complete peer export. Rank distribution, review recency and themes, responses, booking completion, performance testing, directory coverage, and local proof remain unknown. The recommended 60 remains Mixed.

## Dry eye / ocular surface: 53 / 100

Direction: Higher means better for the client.

Full precision: 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00. One final ROUND_HALF_UP step produces 53.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Local Demand Fit | 65 | 0.20 | 65 x 0.20 = 13.00 | ACS2024_BG, CDC_PLACES_2025 | medium |
| Competitive Gap | 35 | 0.15 | 35 x 0.15 = 5.25 | S08, S09 | medium |
| Current Capability | 65 | 0.15 | 65 x 0.15 = 9.75 | S03 | medium |
| Access / Capacity Fit | 50 | 0.15 | 50 x 0.15 = 7.50 | S03, S06 | medium |
| Revenue / Reimbursement Potential | 50 | 0.15 | 50 x 0.15 = 7.50 | S03 | medium |
| Referral Ecosystem Fit | 50 | 0.10 | 50 x 0.10 = 5.00 | S03 | medium |
| Evidence Confidence | 50 | 0.10 | 50 x 0.10 = 5.00 | ACS2024_BG, CDC_PLACES_2025, S03, S08, S09 | medium |

The display changed from 52 to 53. Exact 5- through 30-minute 40-64, 65-plus, and diabetes context strengthens Evidence Confidence from 35 to 50. Local Demand Fit stays 65 because the evidence confirms a supportive demand proxy but does not establish search demand, referral density, conversion, or lane economics. The competitive, capability, capacity, revenue, and referral bands do not change.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Local Demand Fit | Exact catchment age and diabetes proxies support the existing directional band, but do not establish realized lane demand. | No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next. |
| Competitive Gap | Peers publish overlapping dry-eye offers, and no new complete lane audit changes the contested state. | No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next. |
| Current Capability | Vintage publishes a dedicated service and modalities, while operating proof remains absent. | No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next. |
| Access / Capacity Fit | Slots, staff, rooms, chair time, and follow-up capacity remain unknown. | No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next. |
| Revenue / Reimbursement Potential | Price, payer, collections, and margin remain unknown. | No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next. |
| Referral Ecosystem Fit | Relationships and referral density remain unknown. | No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next. |
| Evidence Confidence | Direct recent catchment demand proxies resolve the prior city-only limitation, but market and operating proof remain incomplete. | No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: No search-demand, capacity, referral, outcome, conversion, price, payer, collection, or margin evidence exists. The recommended 53 remains Research next.

## Myopia management: 53 / 100

Direction: Higher means better for the client.

Full precision: 13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 5.00 = 53.00. One final ROUND_HALF_UP step produces 53.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Local Demand Fit | 65 | 0.20 | 65 x 0.20 = 13.00 | ACS2024_BG, MORTON709_FIRST_PARTY_ARCHIVE | medium |
| Competitive Gap | 35 | 0.15 | 35 x 0.15 = 5.25 | S09, S10 | medium |
| Current Capability | 65 | 0.15 | 65 x 0.15 = 9.75 | S04 | medium |
| Access / Capacity Fit | 50 | 0.15 | 50 x 0.15 = 7.50 | S04, S06 | medium |
| Revenue / Reimbursement Potential | 50 | 0.15 | 50 x 0.15 = 7.50 | S04 | medium |
| Referral Ecosystem Fit | 50 | 0.10 | 50 x 0.10 = 5.00 | S04 | medium |
| Evidence Confidence | 50 | 0.10 | 50 x 0.10 = 5.00 | ACS2024_BG, MORTON709_FIRST_PARTY_ARCHIVE, S04, S09, S10 | medium |

The display changed from 52 to 53. Exact catchment child counts and observed Morton CUSD 709 enrollment growth strengthen Evidence Confidence from 35 to 50. Local Demand Fit stays 65 because the new evidence confirms family-demand support but does not establish search demand, willingness to pay, referrals, conversion, or follow-up capacity. All other component bands stay fixed.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Local Demand Fit | Exact child counts and positive observed enrollment change support the existing family-demand band without proving realized myopia demand. | The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next. |
| Competitive Gap | A peer publishes several myopia-control approaches, and no new lane-depth audit changes the contested state. | The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next. |
| Current Capability | Vintage publishes a dedicated service. Starts, retention, outcomes, and capacity remain unknown. | The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next. |
| Access / Capacity Fit | Follow-up capacity, chair time, staff skill, and protocols remain unknown. | The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next. |
| Revenue / Reimbursement Potential | Price, payment, retention, collections, and margin remain unknown. | The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next. |
| Referral Ecosystem Fit | School, pediatric, parent, and provider referral relationships remain unknown. | The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next. |
| Evidence Confidence | Direct catchment and first-party school evidence resolve the prior city-only family proxy, while operating and referral proof remain incomplete. | The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: The school series has no observed 2023-24 value. Search demand, parent willingness to pay, capacity, referrals, outcomes, retention, conversion, and economics remain unknown. The recommended 53 remains Research next.

## Specialty contact lenses: 51 / 100

Direction: Higher means better for the client.

Full precision: 10.00 + 7.50 + 9.75 + 7.50 + 7.50 + 5.00 + 3.50 = 50.75. One final ROUND_HALF_UP step produces 51.

| Component | Band/value | Weight | Contribution | Source IDs | Confidence |
| --- | --- | --- | --- | --- | --- |
| Local Demand Fit | 50 | 0.20 | 50 x 0.20 = 10.00 | S05, ACS2024_BG | medium |
| Competitive Gap | 50 | 0.15 | 50 x 0.15 = 7.50 | S07, S08, S12 | medium |
| Current Capability | 65 | 0.15 | 65 x 0.15 = 9.75 | S05 | medium |
| Access / Capacity Fit | 50 | 0.15 | 50 x 0.15 = 7.50 | S05, S06 | medium |
| Revenue / Reimbursement Potential | 50 | 0.15 | 50 x 0.15 = 7.50 | S05 | medium |
| Referral Ecosystem Fit | 50 | 0.10 | 50 x 0.10 = 5.00 | S05 | medium |
| Evidence Confidence | 35 | 0.10 | 35 x 0.10 = 3.50 | S05, S07, S08, S12 | medium |

The display stays 51. The new catchment, growth, routing, and review evidence does not establish contact-lens population, keratoconus burden, search demand, referral demand, complete specialty-depth competition, fitting capacity, outcomes, or economics. No component crosses a rubric band.

| Component | Why this band changed or stayed | Limitation |
| --- | --- | --- |
| Local Demand Fit | General demographics do not establish contact-lens or keratoconus demand. | Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next. |
| Competitive Gap | Peers publish contact-lens services, but equivalent specialty depth remains unknown. | Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next. |
| Current Capability | Vintage publishes specialty lens types and an offer, but operating proof remains absent. | Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next. |
| Access / Capacity Fit | Fitting availability, doctor time, staff skill, and room capacity remain unknown. | Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next. |
| Revenue / Reimbursement Potential | Pricing, payer, remakes, chair-time cost, and margin remain unknown. | Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next. |
| Referral Ecosystem Fit | Ophthalmology, optometry, and keratoconus referral flows remain unknown. | Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next. |
| Evidence Confidence | The public offer and general overlap remain the only lane-specific evidence. The new packets do not resolve lane demand or operations. | Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next. |

What would move it: replace the named nulls or bounded samples with complete, reproducible evidence that crosses an approved 20 / 35 / 50 / 65 / 80 band. Weights and formulas do not change during this report.

Confidence: C: public-only directional evidence

Limitation: Demand, specialty gap, fitting volume, success, chair time, capacity, referrals, pricing, remakes, payer mix, and margin remain unknown. The score remains Research next.

# Catchment values and method

| Window | Population | Households | Under 18 | Age 40-64 | Age 65+ | Diabetes |
| --- | --- | --- | --- | --- | --- | --- |
| 5 minutes | 6,624 | 2,722 | 1,712 | 1,811 | 1,311 | 9.6% |
| 10 minutes | 19,322 | 7,873 | 4,571 | 5,843 | 4,291 | 10.9% |
| 15 minutes | 54,768 | 23,793 | 11,707 | 17,431 | 10,939 | 12.4% |
| 20 minutes | 173,058 | 75,244 | 38,652 | 53,102 | 32,473 | 13.2% |
| 30 minutes | 283,661 | 120,940 | 64,831 | 86,558 | 53,258 | 12.3% |

These are area-weighted modeled catchment estimates, not patient counts and not a full VDU. Full VDU remains null.

Method: the origin is the direct Google listing pin for Vintage Optical. Corrected Valhalla auto-profile polygons define the 5, 10, 15, 20, and 30-minute windows. The polygons were intersected with 2024 TIGER Illinois block groups in EPSG:5070. Population, households, and age bands use 2024 ACS 5-year block-group estimates allocated by intersection area. Negative ACS sentinels remain null.

Income context uses a household-weighted mean of valid block-group median household incomes. It is an approximation, not a true catchment median and not actual payer mix. Diabetes context uses adult-population and tract-area weighted crude prevalence from the CDC PLACES 2025 release, 2023 data year.

The model has no live traffic or patient-origin evidence. Patient willingness to travel is unmeasured. The canonical six-term VDU also requires diabetes-prevalence-indexed population and commercial-pay-indexed population with complete frozen lineage. Those terms are incomplete, so canonical full VDU is null.

Source IDs: GOOGLE_MAPS_SAMPLE_20260730, VALHALLA_20260730, TIGER2024_BG, ACS2024_BG, CDC_PLACES_2025, and CATCHMENT_DEMOGRAPHICS_20260730.

# Observed population and school series

## Morton village population

| Year | Morton village population |
| --- | --- |
| 2020 | 17,172 |
| 2021 | 17,196 |
| 2022 | 17,361 |
| 2023 | 17,552 |
| 2024 | 17,555 |
| 2025 | 17,565 |

Derivation: 17,565 - 17,172 = 393. Then 393 / 17,172 x 100 = 2.2886093641%, displayed as 2.29%.

This is observed Morton village population change from 2020 to 2025. It is not catchment growth, forecast growth, patient growth, or realized demand. Source ID: CENSUS_PEP_2025.

## Morton CUSD 709 enrollment

| School year | Enrollment | Status |
| --- | --- | --- |
| 2022-2023 | 3,238 | Observed |
| 2023-24 | missing | Not interpolated |
| 2024-25 | 3,299 | Observed |
| 2025-26 | 3,365 | Observed |

Derivation: 3,365 - 3,238 = 127. Then 127 / 3,238 x 100 = 3.9221741816%, displayed as 3.92%.

The 2023-24 value is missing and not interpolated. Enrollment is an observed district proxy, not catchment population, forecast growth, patient growth, myopia starts, or realized demand. Source ID: MORTON709_FIRST_PARTY_ARCHIVE.

# Candidate supply reconciliation

The NPPES city-and-taxonomy queries reported 40 results, while 39 provider candidate records materialized. Deterministic grouping produced 24 location candidates. The Census batch geocoder matched 21 and returned 3 no-match rows.

| Window | Candidate locations | Competitor candidates | Canonical offices |
| --- | --- | --- | --- |
| 5 minutes | 4 | 2 | null |
| 10 minutes | 4 | 2 | null |
| 15 minutes | 8 | 6 | null |
| 20 minutes | 16 | 14 | null |
| 30 minutes | 20 | 18 | null |

Candidate counts are 4 / 4 / 8 / 16 / 20 across the five windows. Competitor-candidate counts are 2 / 2 / 6 / 14 / 18 after the directly supported subject-address exclusions.

These are coverage and contradiction counts. NPPES is a provider registry, not proof of active distinct offices. Repeated addresses, organizations, individual providers, ownership, current status, and service type are not completely resolved. One reported result did not materialize, three locations did not geocode, and the collection is not a complete 30-minute active-office sweep.

The canonical office count remains null. Population per office, full VDU per office, Supply Balance, Supply Saturation, and patient-choice denominators cannot be calculated from these candidates. Source IDs: NPPES_CURRENT_20260730 and CENSUS_GEOCODER_20260730.

# Route, reputation, and visibility lineage

## Corrected Focus route

The current route uses direct Google listing pins for Vintage Optical and Focus On Eyes. The frozen OSRM result is 233.4 seconds and 2,466.8 meters. The report displays 233.4 / 60 = 3.89 minutes and 1.53 miles.

The direct-pin route supersedes the earlier candidate-geocoder lineage without repeating the stale values. The peer remains nearby, so no approved score band changes. The route has no live traffic, time-of-day adjustment, patient origins, patient choice, capacity, or draw evidence.

Source IDs: GOOGLE_MAPS_SAMPLE_20260730, GOOGLE_MAPS_FOCUS_SAMPLE_20260730, and OSRM_FOCUS_GOOGLE_PINS_20260730.

## One bounded direct Google comparison

| Entity | Direct Google rating | Direct Google reviews | Observation role |
| --- | --- | --- | --- |
| Vintage Optical | 4.9 | 348 | Peer card |
| Focus On Eyes | 4.8 | 182 | Direct listing |
| Tri-County Eye Center | 4.9 | 271 | Peer card |
| Walmart Vision & Glasses | 3.5 | 8 | Peer card |

This is one dated same-page direct Google observation. The rank grid did not run, and this is not a complete peer export. No review text, themes, recency distribution, owner-response rate, conversion, outcomes, or clinical-quality inference is included.

## Source-separated Birdeye discrepancies

| Entity | Birdeye Google component | Direct Google | Difference |
| --- | --- | --- | --- |
| Vintage Optical | 398 | 348 | 50 |
| Focus On Eyes | 210 | 182 | 28 |

Arithmetic: 398 - 348 = 50 for Vintage Optical. 210 - 182 = 28 for Focus On Eyes. Birdeye components are aggregator observations, not direct current Google counts. Aggregation dates and methods may differ. Ratings are not averaged, counts are not summed, and the cross-platform review total remains null.

DataForSEO status is unavailable_missing_credentials. request_sent is false. cost is 0. The rank grid status is not_run. Direct Google samples, Exa discovery, and Perplexity discovery are not equivalent to a rank grid.

Source IDs: GOOGLE_MAPS_FOCUS_SAMPLE_20260730, BIRDEYE_AGGREGATOR_20260730, and DATAFORSEO_PREFLIGHT_20260730.

# What we do not know

The canonical office count remains null because provider-registry and candidate-location records are not a complete, current, classified, geocoded, and deduplicated active-office census.

Full VDU remains null because the six-term canonical formula lacks complete diabetes-indexed and commercial-pay-indexed inputs with validated lineage.

Complete provider entity dedupe remains null. The rank grid remains null and not run. Patient-origin choice, live traffic, conversion, capacity, outcomes, economics, actual payer mix, realized specialty demand, and a defensible cross-platform review total remain unknown.

These unknowns do not mean zero, average, normal, no demand, no competition, or no problem. They block office ratios, patient-choice claims, forecasts, revenue claims, capacity claims, outcome claims, and investment conclusions.

The report remains internal-only. External delivery, publishing, upload, CRM write, outreach, or any other external action requires human Project Room approval of the exact rendered package.

# Source dictionary

Every substantive source ID maps to a direct public URL and a bounded use. Exa and Perplexity are discovery coverage only and are never publication authority.

| Source ID | Source | Direct public URL | Authority/type | Observed/vintage | Claim use | Confidence | Limitation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ACS2024_BG | 2024 ACS 5-year block-group detailed tables | https://api.census.gov/data/2024/acs/acs5 | Accepted public source | 2026-07-30 | Population, households, age bands, and household-weighted income approximation. | high | Survey estimates have sampling error; negative sentinels are null. |
| BIRDEYE_AGGREGATOR_20260730 | Birdeye source-separated aggregator observations | https://reviews.birdeye.com/focus-on-eyes-pc-155729242849867 | aggregator_observation_not_direct_platform_count | 2026-07-30 | Birdeye-displayed components and discrepancies, kept separate from direct Google. | medium within the stated bounded use | The displayed 217 total and its platform components are Birdeye observations with unknown cross-entity recency and collection-method comparability. |
| CATCHMENT_DEMOGRAPHICS_20260730 | Accepted derived catchment demographics | https://api.census.gov/data/2024/acs/acs5 | Immediate derived ACS, TIGER, CDC PLACES, and Valhalla packet | 2026-07-30 | Accepted derived five-window values and full-VDU null gate. | high | Canonical full VDU remains null because required terms are incomplete. |
| CDC_PLACES_2025 | CDC PLACES 2025 release, 2023 data year | https://www.cdc.gov/places/ | Accepted public source | 2026-07-30 | Tract-level modeled diabetes prevalence context. | high | Modeled tract crude prevalence, not patient-level clinical data. |
| CENSUS_GEOCODER_20260730 | United States Census batch geocoder results | https://geocoding.geo.census.gov/geocoder/geographies/addressbatch | United States Census Bureau batch geocoder | 2026-07-30 | Matched and no-match candidate-address reconciliation. | medium within the stated bounded use | Three rows returned No_Match and retain null coordinates. |
| CENSUS_PEP_2025 | Census Vintage 2025 Population Estimates | https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/cities/totals/sub-est2025.csv | Accepted public source | 2026-07-30 | Observed Morton village population series and growth derivation. | high | Annual estimates may be revised in later Census vintages. |
| DATAFORSEO_PREFLIGHT_20260730 | DataForSEO availability preflight | https://api.dataforseo.com/v3/appendix/user_data | authoritative_for_this_preflight_state_only | 2026-07-30T11:54:00Z | Unavailable credentials, no request, zero cost, and rank grid not run. | high | DataForSEO credentials were not configured in the active environment, so no paid API request or rank grid ran. |
| GOOGLE_MAPS_FOCUS_SAMPLE_20260730 | Direct Google Maps same-page Focus comparison | https://www.google.com/maps/place/Focus+On+Eyes,+P.C.+Member+Of+Vision+Source/@40.6196994,-89.4680886,17z/ | Direct public Google Maps listing and peer cards | 2026-07-30T13:18:44.578Z | Bounded same-page Google rating and review-count comparison plus Focus listing pin. | medium within the stated bounded use | One dated page observation, not a complete peer export or rank grid. |
| GOOGLE_MAPS_SAMPLE_20260730 | Direct Google Maps observation: Vintage Optical | https://www.google.com/maps/place/Vintage+Optical/@40.6049094,-89.467024,17z/ | Accepted public source | 2026-07-30T12:54:08.602Z | Subject identity, current listing pin, address, and public booking-link observation. | high | One dated public listing observation; not patient-origin evidence. |
| MORTON709_FIRST_PARTY_ARCHIVE | Morton CUSD 709 first-party and archived enrollment pages | https://www.morton709.org/our-district/about-morton-709 | Accepted public source | 2024-01-17 | Observed Morton CUSD 709 enrollment series and missing-year boundary. | high | Archived first-party page snapshot. |

# Source dictionary, continued

Every substantive source ID maps to a direct public URL and a bounded use. Exa and Perplexity are discovery coverage only and are never publication authority.

| Source ID | Source | Direct public URL | Authority/type | Observed/vintage | Claim use | Confidence | Limitation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NPPES_CURRENT_20260730 | NPPES sanitized provider candidate roster | https://npiregistry.cms.hhs.gov/api/ | authoritative public registry for represented provider registration fields only | 2026-07-30 | Candidate provider coverage and source-result deficit only; not office count. | medium within the stated bounded use | Public NPPES queries by named city and taxonomy. NPPES is a provider registry, not proof of active office capacity, patient draw, or a complete drive-time catchment supply census. Raw NPI and phone identifiers are intentionally omitted from this sanitized receipt. |
| OSRM_FOCUS_GOOGLE_PINS_20260730 | OSRM direct-pin route from Vintage to Focus | https://router.project-osrm.org/route/v1/driving | OSRM public routing service | 2026-07-30 | Corrected Focus route duration and distance. | high | No live traffic. |
| OSRM_TABLE_20260730 | OSRM candidate route table | https://router.project-osrm.org/table/v1/driving | OSRM public routing service | 2026-07-30 | Candidate route coverage only; not patient choice. | medium within the stated bounded use | No live traffic and no patient-origin choice evidence. |
| S01 | Official Subject Website | https://www.vintageopt.com/ | official_subject_website | 2026-07-29 | Subject identity, routine and medical eye-care breadth, dry-eye and myopia links, optical, on-site lab, three named optometrists, and public appointment CTA. | high | Practice-controlled claims do not prove utilization, outcomes, capacity, conversion, or economics. |
| S02 | Official Subject Website | https://www.vintageopt.com/hours-location/ | official_subject_website | 2026-07-29 | Current address, posted hours, parking statement, same-day emergency claim, and appointment link. | high | Posted access does not prove live appointment availability, phone performance, or realized demand. |
| S03 | Official Subject Service Page | https://www.vintageopt.com/medical-eye-care/dry-eye-treatment/ | official_subject_service_page | 2026-07-29 | Public dry-eye service and modality evidence. | high | Confirms the public offer only, not case volume, clinical outcomes, capacity, or contribution margin. |
| S04 | Official Subject Service Page | https://www.vintageopt.com/medical-eye-care/myopia-management/ | official_subject_service_page | 2026-07-29 | Public myopia-management service and treatment-option evidence. | high | Confirms the public offer only, not starts, retention, outcomes, or economics. |
| S05 | Official Subject Service Page | https://www.vintageopt.com/contact-lenses/specialty-contact-lenses/ | official_subject_service_page | 2026-07-29 | Public specialty-contact service and lens-type evidence. | high | Does not establish referral volume, chair time, fit success, capacity, or economics. |
| S06 | Subject Linked Public Booking Vendor | https://scheduleyourexam.com/v3/index.php/5788 | subject_linked_public_booking_vendor | 2026-07-29 | Public booking path reached a service and provider selection flow. | high | No service, provider, slot, appointment, or form was selected or submitted. Slot depth and completion rate remain unknown. |
| S07 | Official Peer Website | https://visionsource-focusoneyes.com/ | official_peer_website | 2026-07-29 | Focus On Eyes entity, Morton address, comprehensive examinations, disease care, lenses, frames, contacts, posted weekday and Saturday hours, and appointment request. | high | Peer-controlled content. No independent review export, live slot inventory, utilization, or capacity evidence was collected. |

# Source dictionary, continued

Every substantive source ID maps to a direct public URL and a bounded use. Exa and Perplexity are discovery coverage only and are never publication authority.

| Source ID | Source | Direct public URL | Authority/type | Observed/vintage | Claim use | Confidence | Limitation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S08 | Official Peer Website | https://www.tricountyeyecenter.com/ | official_peer_website | 2026-07-29 | Washington entity and address plus eye examinations, disease treatment, dry-eye clinic, contact lenses, macular-health center, emergency care, and eyewear. | high | Peer-controlled service claims do not prove capacity, volume, outcomes, or patient draw from Morton. |
| S09 | Official Peer Website | https://vcc2020.com/ | official_peer_website | 2026-07-29 | Vision Care Center entity and specialty overlap, including dry-eye diagnostics and therapy. | high | Peer-controlled content. No independent review export, utilization, outcomes, capacity, or Morton patient-origin evidence was collected. |
| S10 | Official Peer Service Page | https://vcc2020.com/service/myopia-control/ | official_peer_service_page | 2026-07-29 | Vision Care Center myopia-control options including atropine, multifocal contacts and glasses, and Ortho-K. | high | Confirms public positioning, not starts, outcomes, capacity, or economics. |
| S11 | Official Peer Location Page | https://www.bardoptical.com/eye-doctor-peoria-east/ | official_peer_location_page | 2026-07-29 | Bard Optical East Peoria entity, exact address, eye-care and optical model, appointment request, and public access information. | high | Official page does not prove how much demand originates in Morton or provide independent review normalization. |
| S12 | Official Peer Location Page | https://www.illinoiseyecenter.com/location/washington/ | official_peer_location_page | 2026-07-29 | Current Washington location at 93 Eastgate Drive and routine, medical, contact-lens, and optical service breadth. | high | The official entity is current, but the supplied Nominatim attempt returned no match and no OSRM route was produced. |
| TIGER2024_BG | 2024 TIGER/Line Illinois block groups | https://www2.census.gov/geo/tiger/TIGER2024/BG/tl_2024_17_bg.zip | Accepted public source | 2026-07-30 | Geographic allocation boundaries for modeled catchment estimates. | high | Boundaries allocate aggregate estimates; they do not locate people. |
| VALHALLA_20260730 | Valhalla corrected drive-time isochrones | https://valhalla.github.io/valhalla/api/isochrone/api-reference/ | Accepted public source | 2026-07-30 | Corrected 5, 10, 15, 20, and 30-minute drive-time polygon boundaries. | high | Modeled auto drive times with no live traffic. |

# Receipt manifest

Receipt paths below are package-relative audit references. They do not authorize external delivery.

| Source ID | Package-relative receipt | SHA-256 | Captured/vintage | Authority/method | Claim use | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-30 | Accepted public-source lineage dictionary used by the approved scoring review; Accepted immediate derived packet copied byte-for-byte | Accepted public-source lineage dictionary used by the approved scoring review | This derived dictionary preserves accepted page lineage; it is not a fresh page capture. |
| ACS2024_BG | data/source_receipts/ACS2024_BG__1637b18a9688__acsdt5y2024-b01001.dat | 1637b18a96881b81e050df1cd3d5ac38a33208b9b69b40e1dbeb3c4e13718f0e | 2026-07-30 | Accepted public source; Frozen upstream receipt | Population, households, age bands, and household-weighted income approximation. | Survey estimates have sampling error; negative sentinels are null. |
| ACS2024_BG | data/source_receipts/ACS2024_BG__77200c3d9c0d__acsdt5y2024-b11001.dat | 77200c3d9c0d99773bc7f78208bc96f25170e5d4d175a5de320620b478ceaff5 | 2026-07-30 | Accepted public source; Frozen upstream receipt | Population, households, age bands, and household-weighted income approximation. | Survey estimates have sampling error; negative sentinels are null. |
| ACS2024_BG | data/source_receipts/ACS2024_BG__b25a176b0e6c__acsdt5y2024-b19013.dat | b25a176b0e6c339b6f3a2a0d3d8446bf06f5f080b4395993ec9a8313efb1c229 | 2026-07-30 | Accepted public source; Frozen upstream receipt | Population, households, age bands, and household-weighted income approximation. | Block-group medians support only an approximate weighted context. |
| BIRDEYE_AGGREGATOR_20260730 | data/source_receipts/BIRDEYE_AGGREGATOR_20260730__4fc44053abac__birdeye-focus-on-eyes.json | 4fc44053abac59f875bf6cf6e541e69beba44079f28cfc9207aab6354eb4985c | 2026-07-30 | aggregator_observation_not_direct_platform_count; third_party_review_aggregator_page_capture | Birdeye-displayed components and discrepancies, kept separate from direct Google. | The displayed 217 total and its platform components are Birdeye observations with unknown cross-entity recency and collection-method comparability. |
| BIRDEYE_AGGREGATOR_20260730 | data/source_receipts/BIRDEYE_AGGREGATOR_20260730__d365aad9b4ba__birdeye-vintage.json | d365aad9b4ba5fd3314402c86c73cf1a1296cebb7bf45f7289d90f874ad1ee34 | 2026-07-30 | aggregator_observation_not_direct_platform_count; third_party_review_aggregator_page_capture | Birdeye-displayed components and discrepancies, kept separate from direct Google. | The displayed 413 total and Google 398 component are Birdeye observations, not a direct current Google count. |
| CATCHMENT_DEMOGRAPHICS_20260730 | data/source_receipts/CATCHMENT_DEMOGRAPHICS_20260730__5ba62163d5f3__catchment_demographics.json | 5ba62163d5f3cd1316c8f9b39ab27818e1ec208d277dd05210f1453d2f55885f | 2026-07-30 | Immediate derived ACS, TIGER, CDC PLACES, and Valhalla packet; Frozen catchment demographic calculations | Accepted derived five-window values and full-VDU null gate. | Canonical full VDU remains null because required terms are incomplete. |
| CATCHMENT_DEMOGRAPHICS_20260730 | data/source_receipts/CATCHMENT_DEMOGRAPHICS_20260730__5ba62163d5f3__catchment_demographics.json | 5ba62163d5f3cd1316c8f9b39ab27818e1ec208d277dd05210f1453d2f55885f | 2026-07-30 | Accepted derived ACS, TIGER, CDC PLACES, and Valhalla catchment packet; Accepted immediate derived packet copied byte-for-byte | Accepted derived five-window values and full-VDU null gate. | Area-weighted modeled estimates; canonical full VDU remains null. |

# Receipt manifest, continued

Receipt paths below are package-relative audit references. They do not authorize external delivery.

| Source ID | Package-relative receipt | SHA-256 | Captured/vintage | Authority/method | Claim use | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| CDC_PLACES_2025 | data/source_receipts/CDC_PLACES_2025__6261efb3665d__cdc-places-2025-five-counties-diabetes.json | 6261efb3665d058dfd250693b9071539a06fb6d10ed9c41d09de599be9dd0d6b | 2026-07-30 | Accepted public source; Frozen upstream receipt | Tract-level modeled diabetes prevalence context. | Modeled tract crude prevalence, not patient-level clinical data. |
| CENSUS_GEOCODER_20260730 | data/source_receipts/CENSUS_GEOCODER_20260730__18a6593c071f__census-geocoder-results.csv | 18a6593c071f7a879e1df83564db1fba84c042882565f5b1b788fef4faba11d2 | 2026-07-30 | United States Census Bureau batch geocoder; Frozen batch geocoding result | Matched and no-match candidate-address reconciliation. | Three rows returned No_Match and retain null coordinates. |
| CENSUS_GEOCODER_BATCH_20260730 | data/source_receipts/CENSUS_GEOCODER_BATCH_20260730__e54c0ef1c85e__census-geocoder-batch.csv | e54c0ef1c85e3b5d85fbcd98d359a81a077d214b393bcbbdc7cfab12ffb62aa0 | 2026-07-30 | United States Census Bureau batch geocoder; Immediate derived 24-row batch input | Evidence lineage and bounded audit support. | Input addresses contain no returned coordinates. |
| CENSUS_PEP_2025 | data/source_receipts/CENSUS_PEP_2025__e3508f520146__sub-est2025.csv | e3508f5201465913476d4ddf91740f191f7977c9f2614a2a7e30b5fd22027934 | 2026-07-30 | Accepted public source; Frozen upstream receipt | Observed Morton village population series and growth derivation. | Annual estimates may be revised in later Census vintages. |
| DATAFORSEO_PREFLIGHT_20260730 | data/source_receipts/DATAFORSEO_PREFLIGHT_20260730__2a1bcc852acd__dataforseo-preflight-20260730.json | 2a1bcc852acd43a0a5f2cb3c924c5defb9c2eeab293c37a2cf3cfb1c4e31dcab | 2026-07-30T11:54:00Z | authoritative_for_this_preflight_state_only; local_api_availability_preflight_receipt | Unavailable credentials, no request, zero cost, and rank grid not run. | DataForSEO credentials were not configured in the active environment, so no paid API request or rank grid ran. |
| GOOGLE_MAPS_FOCUS_SAMPLE_20260730 | data/source_receipts/GOOGLE_MAPS_FOCUS_SAMPLE_20260730__aabf66762ddb__google-maps-focus-20260730.json | aabf66762ddb1ac51c3eb42ae53f25700ce5e98af682b275fc0a3238e030bdbb | 2026-07-30T13:18:44.578Z | Direct public Google Maps listing and peer cards; Browser DOM observation | Bounded same-page Google rating and review-count comparison plus Focus listing pin. | One dated page observation, not a complete peer export or rank grid. |
| GOOGLE_MAPS_SAMPLE_20260730 | data/source_receipts/GOOGLE_MAPS_SAMPLE_20260730__ff0b01b46425__google-maps-vintage-20260730.json | ff0b01b4642535487a7d3fcf494b151b8490d564a517e4e5c58da007ec449616 | 2026-07-30T12:54:08.602Z | Accepted public source; Frozen upstream receipt | Subject identity, current listing pin, address, and public booking-link observation. | One dated public listing observation; not patient-origin evidence. |
| GOOGLE_MAPS_SAMPLE_20260730 | data/source_receipts/GOOGLE_MAPS_SAMPLE_20260730__ff0b01b46425__google-maps-vintage-20260730.json | ff0b01b4642535487a7d3fcf494b151b8490d564a517e4e5c58da007ec449616 | 2026-07-30T12:54:08.602Z | direct_platform_observation; direct_public_google_maps_observation | Subject identity, current listing pin, address, and public booking-link observation. | Google displayed a limited public view without a review count. This is one dated direct observation, not a rank grid or complete query set. The rating is platform-specific and cannot be combined with aggregator counts without a documented deduplication method. The map pin is used as the public routing origin for the listed street address, not as patient-origin evidence. |

# Receipt manifest, continued

Receipt paths below are package-relative audit references. They do not authorize external delivery.

| Source ID | Package-relative receipt | SHA-256 | Captured/vintage | Authority/method | Claim use | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| GOOGLE_MAPS_SAMPLE_20260730 | data/source_receipts/GOOGLE_MAPS_SAMPLE_20260730__ff0b01b46425__google-maps-vintage-20260730.json | ff0b01b4642535487a7d3fcf494b151b8490d564a517e4e5c58da007ec449616 | 2026-07-30T12:54:08.602Z | Direct public Google Maps listing; Browser DOM observation | Subject identity, current listing pin, address, and public booking-link observation. | Limited dated view with no displayed review count. |
| GROWTH_EVIDENCE_20260730 | data/source_receipts/GROWTH_EVIDENCE_20260730__76c9ce4068b4__growth_evidence.json | 76c9ce4068b42c10a127132e2a2a0753d46249aaca227025d7e2969b06d2d4d8 | 2026-07-30 | Accepted derived observed-growth packet; Accepted immediate derived packet copied byte-for-byte | Accepted derived observed-growth packet | Village and district observations are context, not forecasts or patient growth. |
| LOCAL_VISIBILITY_REPUTATION_20260730 | data/source_receipts/LOCAL_VISIBILITY_REPUTATION_20260730__1a56d2092b07__local_visibility_reputation.json | 1a56d2092b07279c82b9416faf30c97ca476b2ba73f7e898e7ab81c1b6510c76 | 2026-07-30 | Immediate derived direct and aggregator observation packet; Frozen source-separated visibility and reputation observations | Evidence lineage and bounded audit support. | Dated observations are not a rank grid or complete peer export. |
| MISSING_EVIDENCE_RECONCILED_20260730 | data/source_receipts/MISSING_EVIDENCE_RECONCILED_20260730__0334e77fba10__missing_evidence.json | 0334e77fba1059c73c39ac1320c05d2e9172ecf581a444dcf938c561854acb1d | 2026-07-30 | Accepted seven-gap evidence register; Accepted immediate derived packet copied byte-for-byte | Accepted seven-gap evidence register | Unknown states are preserved and never converted to zero. |
| MORTON709_FIRST_PARTY_ARCHIVE | data/source_receipts/MORTON709_FIRST_PARTY_ARCHIVE__3a2e38c98bbf__morton709-archive-20240117.html | 3a2e38c98bbf1e993cc530cab7656da21333c0ec75c3a1163a45780f140d73eb | 2024-01-17 | Accepted public source; Frozen upstream receipt | Observed Morton CUSD 709 enrollment series and missing-year boundary. | Archived first-party page snapshot. |
| MORTON709_FIRST_PARTY_ARCHIVE | data/source_receipts/MORTON709_FIRST_PARTY_ARCHIVE__62b2380a6735__morton709-enrollment-series.json | 62b2380a67352c20d2a3f544e06cad75e55388140065bbc3788816cc9b5694dd | 2026-07-30 | Accepted public source; Frozen upstream receipt | Observed Morton CUSD 709 enrollment series and missing-year boundary. | The district did not provide an observed 2023-24 value here. |
| MORTON709_FIRST_PARTY_ARCHIVE | data/source_receipts/MORTON709_FIRST_PARTY_ARCHIVE__a88d1b7df912__morton709-archive-20250912.html | a88d1b7df912bb6811bd84ed7b721cc6366fa5b59b4755dce70329bb9e0a35f0 | 2025-09-12 | Accepted public source; Frozen upstream receipt | Observed Morton CUSD 709 enrollment series and missing-year boundary. | Archived first-party page snapshot. |
| MORTON709_FIRST_PARTY_ARCHIVE | data/source_receipts/MORTON709_FIRST_PARTY_ARCHIVE__dc59e4c7ed17__morton709-live-20260730.html | dc59e4c7ed1790348ca84d150d196b0e3a523070032f7b4d2f81e89e4ca5d9b7 | 2026-07-30 | Accepted public source; Frozen upstream receipt | Observed Morton CUSD 709 enrollment series and missing-year boundary. | Dated capture of a live first-party page. |

# Receipt manifest, continued

Receipt paths below are package-relative audit references. They do not authorize external delivery.

| Source ID | Package-relative receipt | SHA-256 | Captured/vintage | Authority/method | Claim use | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| NPPES_CURRENT_20260730 | data/source_receipts/NPPES_CURRENT_20260730__c53c847d05ff__nppes-provider-roster-sanitized.json | c53c847d05ff99fb673aa8bafde18e3e6ee31d19bb834c8f79a8ec1778a53e23 | 2026-07-30 | authoritative public registry for represented provider registration fields only; sanitized_public_provider_registry_query_receipt | Candidate provider coverage and source-result deficit only; not office count. | Public NPPES queries by named city and taxonomy. NPPES is a provider registry, not proof of active office capacity, patient draw, or a complete drive-time catchment supply census. Raw NPI and phone identifiers are intentionally omitted from this sanitized receipt. |
| NPPES_CURRENT_20260730 | data/source_receipts/NPPES_CURRENT_20260730__c53c847d05ff__nppes-provider-roster-sanitized.json | c53c847d05ff99fb673aa8bafde18e3e6ee31d19bb834c8f79a8ec1778a53e23 | 2026-07-30 | NPPES public registry; Sanitized frozen city and taxonomy query roster | Candidate provider coverage and source-result deficit only; not office count. | Provider records are not office counts; one reported row did not materialize. |
| OSRM_FOCUS_GOOGLE_PINS_20260730 | data/source_receipts/OSRM_FOCUS_GOOGLE_PINS_20260730__1329262f989c__osrm-vintage-to-focus-google-pins.json | 1329262f989ce7d7a8f6c935f22cadfebd699b7a51fca91208e52a839941235f | 2026-07-30 | OSRM public routing service; Frozen route between two direct Google listing pins | Corrected Focus route duration and distance. | No live traffic. |
| OSRM_TABLE_20260730 | data/source_receipts/OSRM_TABLE_20260730__053bacdf7034__osrm-table-results.json | 053bacdf7034bd52df37c923291e1cf0af137231b50beed7ac20ce1ad766a801 | 2026-07-30 | OSRM public routing service; Frozen one-to-many driving table | Candidate route coverage only; not patient choice. | No live traffic and no patient-origin choice evidence. |
| OSRM_TABLE_INDEX_20260730 | data/source_receipts/OSRM_TABLE_INDEX_20260730__aadc4efd95d8__osrm-table-input-index.json | aadc4efd95d83ca438c2b870635d78412e8ba27e8f7fd356537b45176f1348f8 | 2026-07-30 | OSRM input lineage; Immediate derived origin and destination index | Evidence lineage and bounded audit support. | Destinations use Census geocoder candidate points. |
| ROUTING_CORRECTED_20260730 | data/source_receipts/ROUTING_CORRECTED_20260730__e00bfe8ff708__routing_corrected.json | e00bfe8ff708876b6c3d16ae4e03d7a4081507e33ac12d61a8befe636dc750e8 | 2026-07-30 | Accepted corrected route-lineage packet; Accepted immediate derived packet copied byte-for-byte | Accepted corrected route-lineage packet | No live traffic, patient origins, choice, capacity, or draw. |
| S01 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_subject_website; Accepted source dictionary lineage from the reviewed report scaffold | Subject identity, routine and medical eye-care breadth, dry-eye and myopia links, optical, on-site lab, three named optometrists, and public appointment CTA. | Practice-controlled claims do not prove utilization, outcomes, capacity, conversion, or economics. Underlying page captures were not listed in the three accepted receipt manifests. |
| S02 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_subject_website; Accepted source dictionary lineage from the reviewed report scaffold | Current address, posted hours, parking statement, same-day emergency claim, and appointment link. | Posted access does not prove live appointment availability, phone performance, or realized demand. Underlying page captures were not listed in the three accepted receipt manifests. |

# Receipt manifest, continued

Receipt paths below are package-relative audit references. They do not authorize external delivery.

| Source ID | Package-relative receipt | SHA-256 | Captured/vintage | Authority/method | Claim use | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| S03 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_subject_service_page; Accepted source dictionary lineage from the reviewed report scaffold | Public dry-eye service and modality evidence. | Confirms the public offer only, not case volume, clinical outcomes, capacity, or contribution margin. Underlying page captures were not listed in the three accepted receipt manifests. |
| S04 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_subject_service_page; Accepted source dictionary lineage from the reviewed report scaffold | Public myopia-management service and treatment-option evidence. | Confirms the public offer only, not starts, retention, outcomes, or economics. Underlying page captures were not listed in the three accepted receipt manifests. |
| S05 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_subject_service_page; Accepted source dictionary lineage from the reviewed report scaffold | Public specialty-contact service and lens-type evidence. | Does not establish referral volume, chair time, fit success, capacity, or economics. Underlying page captures were not listed in the three accepted receipt manifests. |
| S06 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | subject_linked_public_booking_vendor; Accepted source dictionary lineage from the reviewed report scaffold | Public booking path reached a service and provider selection flow. | No service, provider, slot, appointment, or form was selected or submitted. Slot depth and completion rate remain unknown. Underlying page captures were not listed in the three accepted receipt manifests. |
| S07 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_peer_website; Accepted source dictionary lineage from the reviewed report scaffold | Focus On Eyes entity, Morton address, comprehensive examinations, disease care, lenses, frames, contacts, posted weekday and Saturday hours, and appointment request. | Peer-controlled content. No independent review export, live slot inventory, utilization, or capacity evidence was collected. Underlying page captures were not listed in the three accepted receipt manifests. |
| S08 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_peer_website; Accepted source dictionary lineage from the reviewed report scaffold | Washington entity and address plus eye examinations, disease treatment, dry-eye clinic, contact lenses, macular-health center, emergency care, and eyewear. | Peer-controlled service claims do not prove capacity, volume, outcomes, or patient draw from Morton. Underlying page captures were not listed in the three accepted receipt manifests. |
| S09 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_peer_website; Accepted source dictionary lineage from the reviewed report scaffold | Vision Care Center entity and specialty overlap, including dry-eye diagnostics and therapy. | Peer-controlled content. No independent review export, utilization, outcomes, capacity, or Morton patient-origin evidence was collected. Underlying page captures were not listed in the three accepted receipt manifests. |
| S10 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_peer_service_page; Accepted source dictionary lineage from the reviewed report scaffold | Vision Care Center myopia-control options including atropine, multifocal contacts and glasses, and Ortho-K. | Confirms public positioning, not starts, outcomes, capacity, or economics. Underlying page captures were not listed in the three accepted receipt manifests. |

# Receipt manifest, continued

Receipt paths below are package-relative audit references. They do not authorize external delivery.

| Source ID | Package-relative receipt | SHA-256 | Captured/vintage | Authority/method | Claim use | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| S11 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_peer_location_page; Accepted source dictionary lineage from the reviewed report scaffold | Bard Optical East Peoria entity, exact address, eye-care and optical model, appointment request, and public access information. | Official page does not prove how much demand originates in Morton or provide independent review normalization. Underlying page captures were not listed in the three accepted receipt manifests. |
| S12 | data/source_receipts/ACCEPTED_PUBLIC_SOURCE_DICTIONARY_20260730__70e21a80ef25__updated-sources.json | 70e21a80ef25a737bdc4edc21b256bcf6622e3dd6237ff5d624a3ea6fa78e3db | 2026-07-29 | official_peer_location_page; Accepted source dictionary lineage from the reviewed report scaffold | Current Washington location at 93 Eastgate Drive and routine, medical, contact-lens, and optical service breadth. | The official entity is current, but the supplied Nominatim attempt returned no match and no OSRM route was produced. Underlying page captures were not listed in the three accepted receipt manifests. |
| SUPPLY_CANDIDATES_20260730 | data/source_receipts/SUPPLY_CANDIDATES_20260730__f4cbeaa09c24__supply_candidates.json | f4cbeaa09c24b3637b4e7e00964c0cd479fe9443622a135d8f798ca85f8f63ee | 2026-07-30 | NPPES public registry plus deterministic local grouping; Immediate derived candidate packet | Evidence lineage and bounded audit support. | Location groups are candidates, not active-office counts. |
| SUPPLY_GEOCODED_CANDIDATES_20260730 | data/source_receipts/SUPPLY_GEOCODED_CANDIDATES_20260730__a77d981ed8a6__supply_geocoded_candidates.json | a77d981ed8a64ec23cb01d3e6eb52dc07826799e4b5b3775f9ec0d935419034c | 2026-07-30 | Accepted derived candidate-supply reconciliation packet; Accepted immediate derived packet copied byte-for-byte | Accepted derived candidate-supply reconciliation packet | Candidate locations are not a canonical office census. |
| TIGER2024_BG | data/source_receipts/TIGER2024_BG__38e970b3df85__tiger2024-il-block-groups.zip | 38e970b3df85f4ce93375d46749cccd14e451d6ba0c894d641be238d02eea4ec | 2026-07-30 | Accepted public source; Frozen upstream receipt | Geographic allocation boundaries for modeled catchment estimates. | Boundaries allocate aggregate estimates; they do not locate people. |
| VALHALLA_20260730 | data/source_receipts/VALHALLA_20260730__3920744be5dc__valhalla-isochrone-30.geojson | 3920744be5dc09d15c81bf077a8b78bbc67096a7a7e6fdbf658ebf912294dbca | 2026-07-30 | Accepted public source; Frozen upstream receipt | Corrected 5, 10, 15, 20, and 30-minute drive-time polygon boundaries. | Modeled auto drive times with no live traffic. |
| VALHALLA_20260730 | data/source_receipts/VALHALLA_20260730__7f733dbece1a__catchment_windows.geojson | 7f733dbece1a217e2a45854731eb823754b0abd7069c3eb2760ee5e6b2b57368 | 2026-07-30 | Accepted corrected five-window polygon packet; Accepted immediate derived packet copied byte-for-byte | Corrected 5, 10, 15, 20, and 30-minute drive-time polygon boundaries. | Modeled drive time without live traffic. |
| VALHALLA_20260730 | data/source_receipts/VALHALLA_20260730__7f733dbece1a__catchment_windows.geojson | 7f733dbece1a217e2a45854731eb823754b0abd7069c3eb2760ee5e6b2b57368 | 2026-07-30 | Valhalla modeled drive-time isochrones; Corrected frozen 5, 10, 15, 20, and 30-minute polygons | Corrected 5, 10, 15, 20, and 30-minute drive-time polygon boundaries. | Modeled driving time with no live traffic. |

# Receipt manifest, continued

Receipt paths below are package-relative audit references. They do not authorize external delivery.

| Source ID | Package-relative receipt | SHA-256 | Captured/vintage | Authority/method | Claim use | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| VALHALLA_20260730 | data/source_receipts/VALHALLA_20260730__9d4389ba52c6__valhalla-isochrones-05-20.geojson | 9d4389ba52c69364c1fcc20a86510a5b008d3330c0001aa9121995b06912f1cd | 2026-07-30 | Accepted public source; Frozen upstream receipt | Corrected 5, 10, 15, 20, and 30-minute drive-time polygon boundaries. | Modeled auto drive times with no live traffic. |
| VISIBILITY_REPUTATION_RECONCILED_20260730 | data/source_receipts/VISIBILITY_REPUTATION_RECONCILED_20260730__80af7ed153da__visibility_reputation_reconciled.json | 80af7ed153dab8f3c93cdce1ce334f392a49e19176a3a3490beb8be9c223fac5 | 2026-07-30 | Accepted source-separated visibility and reputation packet; Accepted immediate derived packet copied byte-for-byte | Accepted source-separated visibility and reputation packet | Dated sample, not a rank grid or complete peer export. |
