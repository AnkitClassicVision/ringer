# Formula and Band Audit

Verdict: PASS

All six core scores and all three specialty scores recompute exactly from the lowest-level recorded components. Every true base component is one of the five allowed Manual bands: 20, 35, 50, 65, or 80. All canonical weight sets sum to 1.00. The computed Market Demand-Supply score, 57, is correctly used as the Client Opportunity market input rather than being replaced by a base band. The internal Competitive Pressure score is 57 and is correctly inverted to the visible, high-good Room to Win score of 43.

## Method

The calculation authority is `CALCULATIONS.md`, with component definitions and score direction confirmed against `RUBRIC.md`, `OUTPUT_SCHEMA.md`, and `WEBSITE_POSITIONING.md`. `FIX_IT_PLAYBOOK.md` confirms that public-only unknown operating and economics inputs must not be turned into invented forecast values. The report authority is the current `scores.json`; visible parity was checked against the current `onepager.html`. The publish-readiness plan requires an independent recomputation from base components and forbids changing a source score to obtain a pass.

Each weighted composite was calculated at full precision, then rounded once to the nearest whole number. A value ending in `.50` rounds up. No component was pre-rounded because all true base inputs are already whole-number bands.

## Manual bands and unknown 50s

The allowed base bands are exactly 20, 35, 50, 65, and 80. A 50 marked as unknown is neutral handling, not a measured average, not zero, and not positive evidence. It contributes its weighted midpoint to a formula while preventing missing evidence from mechanically depressing a score to zero or inflating it. The accompanying rationale must still state what is missing and make no directional claim.

Not every numeric formula input is a base band. Client Opportunity must use the already computed Market Demand-Supply score of 57. Room to Win must use the already computed internal Competitive Pressure score of 57. Those two derived values are allowed because the canonical formulas explicitly require them; they are not exceptions to the base-band rule.

## Market Demand-Supply

Formula:

`0.25 × Demand Strength + 0.20 × Supply Balance + 0.15 × Payer / Income Fit + 0.15 × Growth / Future Demand + 0.15 × Specialty Demand Load + 0.10 × Market Data Confidence`

| Input | Band | Weight | Contribution | Why the band was assigned |
|---|---:|---:|---:|---|
| Demand Strength | 65 | 0.25 | 16.25 | Morton city evidence shows supportive under-18 and 65-plus shares. This supports a directional family and age-related demand hypothesis, but the city figures are not treated as a drive-time catchment measurement. |
| Supply Balance | 50 | 0.20 | 10.00 | Neutral unknown. There is no complete geocoded and deduplicated office census, provider join, weighted supply total, VDU, or VDU-per-office denominator for the catchment. |
| Payer / Income Fit | 65 | 0.15 | 9.75 | Morton city median household income is a favorable public proxy. Actual payer mix, commercial coverage, and collections remain unknown. |
| Growth / Future Demand | 50 | 0.15 | 7.50 | Neutral unknown. No catchment growth series, permit pipeline, school growth evidence, or mobility growth vector was available. |
| Specialty Demand Load | 65 | 0.15 | 9.75 | City age shares directionally support pediatric, senior, and chronic eye-care need. Catchment-weighted health, search, contact-lens, and referral-density inputs are missing. |
| Market Data Confidence | 35 | 0.10 | 3.50 | City context and stored routes are reproducible, but the fixed-window demographics, VDU, office, provider, and patient-choice measures required for stronger market proof are missing. |

Line-by-line total:

1. `0.25 × 65 = 16.25`
2. `0.20 × 50 = 10.00`
3. `0.15 × 65 = 9.75`
4. `0.15 × 50 = 7.50`
5. `0.15 × 65 = 9.75`
6. `0.10 × 35 = 3.50`
7. `16.25 + 10.00 + 9.75 + 7.50 + 9.75 + 3.50 = 56.75`
8. Rounding `56.75` to the nearest whole number gives `57`, matching `scores.json` and the page.

## Competitive Pressure

This is the internal diagnostic where higher means more pressure. It is not displayed as a high-good page score.

Formula:

`0.40 × Supply Saturation + 0.25 × Patient Choice Pressure + 0.20 × Competitor Strength + 0.15 × Access / Differentiation Pressure`

| Input | Band | Weight | Contribution | Why the band was assigned |
|---|---:|---:|---:|---|
| Supply Saturation | 50 | 0.40 | 20.00 | Neutral unknown. The named peers are not a complete supply census, and no office or provider denominator exists. |
| Patient Choice Pressure | 65 | 0.25 | 16.25 | Stored routes show three named alternatives within 20 minutes and five within 30 minutes, including a direct peer at 4.07 routed minutes and a retail substitute near 14 minutes. This is directional because the set is not complete or population-weighted. |
| Competitor Strength | 65 | 0.20 | 13.00 | Official peer pages show broad routine, medical, optical, dry-eye, and myopia overlap. Those pages support stated-service competition, not utilization or patient draw. |
| Access / Differentiation Pressure | 50 | 0.15 | Neutral mixed input. Vintage publishes six-day hours, same-day emergency availability, and booking access, while peers also publish overlapping access and services. Live availability and peer-normalized performance are unknown. |

Line-by-line total:

1. `0.40 × 50 = 20.00`
2. `0.25 × 65 = 16.25`
3. `0.20 × 65 = 13.00`
4. `0.15 × 50 = 7.50`
5. `20.00 + 16.25 + 13.00 + 7.50 = 56.75`
6. Rounding `56.75` gives internal Competitive Pressure `57`, matching `scores.json`.

## Room to Win

Formula:

`100 - internal Competitive Pressure`

Line by line:

1. Internal Competitive Pressure recomputes to `57`.
2. `100 - 57 = 43`.
3. Room to Win is therefore `43`, matching both `scores.json` and the page.

The inversion is necessary for page direction. Competitive Pressure is high-bad, while Room to Win is high-good. The page displays only Room to Win, so all displayed scores retain the same higher-is-better meaning.

## Practice Competitiveness

Formula:

`0.20 × Visibility vs Peers + 0.20 × Access / Booking vs Peers + 0.20 × Review Trust vs Peers + 0.15 × Service-Line Differentiation + 0.15 × Website / Conversion Clarity + 0.10 × Location Convenience`

| Input | Band | Weight | Contribution | Why the band was assigned |
|---|---:|---:|---:|---|
| Visibility vs Peers | 50 | 0.20 | 10.00 | Neutral unknown. A dated query sample shows Vintage and a Book online action, but no rank grid, complete result set, or peer-normalized visibility measure exists. |
| Access / Booking vs Peers | 65 | 0.20 | 13.00 | The subject publishes Monday-through-Saturday hours, same-day emergency appointments, a prominent appointment path, and a vendor flow that reaches service and provider selection. Live slots and completed bookings are unverified. |
| Review Trust vs Peers | 50 | 0.20 | 10.00 | Neutral unknown. The 4.9 sample lacks count, recency, response behavior, and equivalent peer fields, so it cannot support a peer-normalized reputation score. |
| Service-Line Differentiation | 65 | 0.15 | 9.75 | Vintage publishes broad routine, medical, dry-eye, myopia, specialty-contact, and optical services. Peer overlap prevents a stronger lane-ownership claim. |
| Website / Conversion Clarity | 65 | 0.15 | 9.75 | The site has service pages, named providers, location and hours, and an appointment path. Owned conversion, mobile, and speed measures are absent. |
| Location Convenience | 50 | 0.10 | 5.00 | Neutral mixed input. The official page states parking and the current Main Street location, but a direct peer is 4.07 routed minutes away and patient-origin convenience is unmeasured. |

Line-by-line total:

1. `0.20 × 50 = 10.00`
2. `0.20 × 65 = 13.00`
3. `0.20 × 50 = 10.00`
4. `0.15 × 65 = 9.75`
5. `0.15 × 65 = 9.75`
6. `0.10 × 50 = 5.00`
7. Total `57.50`
8. Rounding `57.50` half up gives `58`, matching `scores.json` and the page.

## Client Opportunity

Formula:

`0.20 × computed Market Demand-Supply + 0.20 × Competitive Pressure Opportunity + 0.20 × Practice Differentiation Upside + 0.15 × Access Fixability + 0.15 × Digital Visibility Fixability + 0.10 × Execution Simplicity`

| Input | Value | Weight | Contribution | Why the value or band was assigned |
|---|---:|---:|---:|---|
| Computed Market Demand-Supply | 57 | 0.20 | 11.40 | This is the required computed market input. It is not a manually assigned base band. |
| Competitive Pressure Opportunity | 50 | 0.20 | 10.00 | Neutral unknown. Pressure is directionally present, but no competitor-weakness cluster, demand leakage, or capacity-supported white space is proven. |
| Practice Differentiation Upside | 50 | 0.20 | 10.00 | Neutral measure-first position. The public offer is already broad and peers overlap on important lanes, so conversion proof is needed before claiming expansion upside. |
| Access Fixability | 50 | 0.15 | 7.50 | Neutral unknown. Public access exists, but call handling, availability, abandonment, cancellations, and no-shows have not been measured. |
| Digital Visibility Fixability | 65 | 0.15 | 9.75 | The practice has public location, service, provider, and booking surfaces, while rank-grid, review, response, directory, and channel baselines are missing. Establishing those baselines is a bounded and plausible fix. |
| Execution Simplicity | 50 | 0.10 | 5.00 | Neutral unknown. The first steps are bounded measurements, but ownership, staff capacity, and operating cadence are not evidenced. |

Line-by-line total:

1. `0.20 × 57 = 11.40`
2. `0.20 × 50 = 10.00`
3. `0.20 × 50 = 10.00`
4. `0.15 × 50 = 7.50`
5. `0.15 × 65 = 9.75`
6. `0.10 × 50 = 5.00`
7. Total `53.65`
8. Rounding `53.65` gives `54`, matching `scores.json` and both page occurrences.

## Digital Presence

Formula:

`0.25 × Findability + 0.20 × Reputation + 0.20 × Bookability + 0.15 × Site Quality + 0.10 × Content & Specialty Signal + 0.10 × Social / Local Proof`

| Input | Band | Weight | Contribution | Why the band was assigned |
|---|---:|---:|---:|---|
| Findability | 50 | 0.25 | 12.50 | Neutral unknown. The dated Maps sample shows the subject but is not a rank grid or complete local-pack measurement. |
| Reputation | 50 | 0.20 | 10.00 | Neutral unknown. The 4.9 sample has no count, velocity, recency, response behavior, or peer comparison. |
| Bookability | 65 | 0.20 | 13.00 | A public call to action reaches service and provider selection, and the sample displays Book online. Slot selection, completion, and conversion are unknown. |
| Site Quality | 65 | 0.15 | 9.75 | The public site exposes location, hours, providers, and service-specific pages. Mobile rendering, Core Web Vitals, speed, and conversion were not measured. |
| Content & Specialty Signal | 65 | 0.10 | 6.50 | Dedicated dry-eye, myopia-management, and specialty-contact pages create clear signals, although peers publish overlapping lanes. |
| Social / Local Proof | 50 | 0.10 | 5.00 | Neutral unknown. The evidence pack contains no verified social activity, local-link, community-mention, or directory-consistency comparison. |

Line-by-line total:

1. `0.25 × 50 = 12.50`
2. `0.20 × 50 = 10.00`
3. `0.20 × 65 = 13.00`
4. `0.15 × 65 = 9.75`
5. `0.10 × 65 = 6.50`
6. `0.10 × 50 = 5.00`
7. Total `56.75`
8. Rounding `56.75` gives `57`, matching `scores.json` and the page.

## Specialty scores

All three lanes use the canonical formula:

`0.20 × Local Demand Fit + 0.15 × Competitive Gap + 0.15 × Current Capability + 0.15 × Access / Capacity Fit + 0.15 × Revenue / Reimbursement Potential + 0.10 × Referral Ecosystem Fit + 0.10 × Evidence Confidence`

### Dry eye / ocular surface

| Input | Band | Weight | Contribution | Why the band was assigned |
|---|---:|---:|---:|---|
| Local Demand Fit | 65 | 0.20 | 13.00 | Morton city age context supports a directional ocular-surface demand hypothesis, but no catchment clinical-demand or search-demand measure exists. |
| Competitive Gap | 35 | 0.15 | 5.25 | Tri-County and Vision Care Center publish direct dry-eye offerings, so the public lane is contested. |
| Current Capability | 65 | 0.15 | 9.75 | Vintage publishes a dedicated dry-eye service and modalities, proving the public offer but not volume, outcomes, staffing, or throughput. |
| Access / Capacity Fit | 50 | 0.15 | 7.50 | Neutral unknown. Specialty slots, chair time, staffing, rooms, follow-up, and capacity are unmeasured. |
| Revenue / Reimbursement Potential | 50 | 0.15 | 7.50 | Neutral unknown. Pricing, payer, collections, margin, and contribution are unmeasured. |
| Referral Ecosystem Fit | 50 | 0.10 | 5.00 | Neutral unknown. No verified referral relationships or referral-density study exists. |
| Evidence Confidence | 35 | 0.10 | 3.50 | The offer and competitor overlap are verified, while demand, capacity, conversion, referrals, and economics remain unmeasured. |

The full-precision sum is `51.50`; nearest-whole half-up Rounding gives `52`, matching `scores.json` and the page.

### Myopia management

| Input | Band | Weight | Contribution | Why the band was assigned |
|---|---:|---:|---:|---|
| Local Demand Fit | 65 | 0.20 | 13.00 | Morton's under-18 city share supports a directional family-demand hypothesis, but no catchment, school-density, or search-demand study exists. |
| Competitive Gap | 35 | 0.15 | 5.25 | Vision Care Center publishes multiple myopia-control approaches, so the public lane is contested. |
| Current Capability | 65 | 0.15 | 9.75 | Vintage publishes a dedicated myopia-management service, proving the public offer but not starts, retention, outcomes, or capacity. |
| Access / Capacity Fit | 50 | 0.15 | 7.50 | Neutral unknown. Follow-up capacity, chair time, staff skill, appointment availability, and protocol evidence are absent. |
| Revenue / Reimbursement Potential | 50 | 0.15 | 7.50 | Neutral unknown. Price, payment, retention, collections, and margin evidence are absent. |
| Referral Ecosystem Fit | 50 | 0.10 | 5.00 | Neutral unknown. No verified school, pediatric, parent, or provider referral relationships are included. |
| Evidence Confidence | 35 | 0.10 | 3.50 | The offer, child-share proxy, and competitor overlap are verified, while conversion, capacity, referrals, and economics remain unmeasured. |

The full-precision sum is `51.50`; nearest-whole half-up Rounding gives `52`, matching `scores.json` and the page.

### Specialty contact lenses

| Input | Band | Weight | Contribution | Why the band was assigned |
|---|---:|---:|---:|---|
| Local Demand Fit | 50 | 0.20 | 10.00 | Neutral unknown. No catchment contact-lens population, keratoconus burden, search demand, or referral-density evidence exists. |
| Competitive Gap | 50 | 0.15 | 7.50 | Neutral unknown. Peers publish general contact-lens services, but equivalent specialty-contact depth and an independent gap have not been established. |
| Current Capability | 65 | 0.15 | 9.75 | Vintage publishes a specialty-contact page and lens types, proving the offer but not fitting volume, success, chair time, or capacity. |
| Access / Capacity Fit | 50 | 0.15 | 7.50 | Neutral unknown. Specialty fitting availability, doctor time, staff skill, rooms, and follow-up are unmeasured. |
| Revenue / Reimbursement Potential | 50 | 0.15 | 7.50 | Neutral unknown. Pricing, payer, collections, remakes, chair-time cost, and margin are unmeasured. |
| Referral Ecosystem Fit | 50 | 0.10 | 5.00 | Neutral unknown. No verified ophthalmology, optometry, or keratoconus referral relationships are included. |
| Evidence Confidence | 35 | 0.10 | 3.50 | The public offer is verified, but local demand, competitive gap, referrals, conversion, capacity, and economics remain unmeasured. |

The full-precision sum is `50.75`; nearest-whole Rounding gives `51`, matching `scores.json` and the page.

## Weight and page cross-checks

Each canonical weighted composite sums to 1.00:

- Market Demand-Supply: `0.25 + 0.20 + 0.15 + 0.15 + 0.15 + 0.10 = 1.00`
- Competitive Pressure: `0.40 + 0.25 + 0.20 + 0.15 = 1.00`
- Practice Competitiveness: `0.20 + 0.20 + 0.20 + 0.15 + 0.15 + 0.10 = 1.00`
- Client Opportunity: `0.20 + 0.20 + 0.20 + 0.15 + 0.15 + 0.10 = 1.00`
- Digital Presence: `0.25 + 0.20 + 0.20 + 0.15 + 0.10 + 0.10 = 1.00`
- Each specialty: `0.20 + 0.15 + 0.15 + 0.15 + 0.15 + 0.10 + 0.10 = 1.00`

The page displays Client Opportunity 54, Market Demand-Supply 57, Room to Win 43, Practice Competitiveness 58, Digital Presence 57, Dry Eye 52, Myopia Management 52, and Specialty Contact Lenses 51. Each matches `scores.json`. Every displayed score is explicitly higher = better. The high-bad Competitive Pressure score of 57 remains internal and is represented on the page only through the high-good Room to Win inversion.

## Logical reconciliation

The combined scores answer different questions, so their modest divergence is expected and reconcilable.

- Market Demand-Supply is 57 because supportive city demand and income proxies are offset by unknown supply and growth plus limited market-data confidence.
- Internal Competitive Pressure is also 57 because observed nearby alternatives and service overlap raise pressure, while incomplete supply and access measurements remain neutral. Its inversion produces Room to Win 43.
- Practice Competitiveness is 58 and Digital Presence is 57 because the subject has broad public service pages and a usable booking path. Unknown peer-normalized visibility, reputation, conversion, and convenience prevent stronger scores.
- Client Opportunity is 54 because it correctly incorporates the computed market score of 57, then combines it with four neutral 50 inputs and one directionally positive 65 for digital visibility fixability.
- Dry eye and myopia each reach 52 because supportive demand and a verified offer at 65 are offset by a contested competitive gap and limited evidence at 35, with operating and economics unknowns held at 50.
- Specialty contact lenses reaches 51 because current public capability is 65 and evidence confidence is 35, while demand, gap, capacity, economics, and referrals remain neutral 50s.

No source score was changed. There are no fatal or material formula issues.
