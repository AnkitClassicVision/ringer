# Vintage Optical

## Number and methodology explainer

**Morton, Illinois**  
**July 29, 2026**

**Internal publish-candidate**  
**Project Room review required**  
**Public-only analysis**  
**Confidence C**  
**External actions: none**

This document explains what every important number in the Vintage Optical analysis means, where it came from, how it was calculated, and what evidence could change it. It is an internal decision aid. Project Room status is `inventory_review_required`.

---

## How to read this analysis

The analysis uses four kinds of numbers:

1. **Raw public facts** are directly reported or observed values, such as the 2025 Morton village population estimate of **17,565**, the age shares of **25.9%** and **23.1%**, and the stored route duration of **244.3 seconds**.
2. **Directional bands** are evidence judgments on a five-value scale: **20, 35, 50, 65, 80**. A band translates incomplete public evidence into a consistent input. It is not a raw measurement.
3. **Derived scores** combine bands using fixed weights, preserve full precision through the calculation, and round once to the nearest whole point. A total ending in .50 rounds up.
4. **Structural numbers** organize the report or define a method. Examples include section 1/2/3, Tier 1/2, Fix Card IDs F-001/F-002/F-003, the 100-point display scale, a 30-day measurement window, the street number 605, and the 2026 copyright year. These are not performance measurements.

**All scores displayed as report results are higher = better.** The internal Competitive Pressure input is the one high = more pressure measure. It is not presented as a report score; it is inverted into the high-good Room to Win score.

### What a neutral unknown 50 means

A **neutral unknown 50** is missing-evidence handling. It does not mean average performance was measured. It does not mean good, bad, or zero. It keeps an absent input at the midpoint while the rationale names the missing proof. Some 50 bands represent a neutral mixed public signal rather than a wholly absent fact, but they still make no favorable performance claim.

### Number map

| Number family | Value | Kind | Plain-language meaning |
|---|---:|---|---|
| Client Opportunity | **54 / 100** | Derived score | How actionable the owner upside appears under current public evidence |
| Market Demand-Supply | **57 / 100** | Derived score | Whether the local market looks attractive enough to investigate |
| Competitive Pressure | **57** | Internal calculation input | Directional pressure, where higher means more pressure |
| Room to Win | **43 / 100** | Derived score | High-good inversion of pressure: `100 - 57 = 43` |
| Practice Competitiveness | **58 / 100** | Derived score | Public-facing strength versus the bounded peer set |
| Digital Presence | **57 / 100** | Derived score | Findability, trust, booking, site, content, and local-proof read |
| Dry eye / ocular surface | **52 / 100** | Derived specialty score | RESEARCH NEXT |
| Myopia management | **52 / 100** | Derived specialty score | RESEARCH NEXT |
| Specialty contact lenses | **51 / 100** | Derived specialty score | RESEARCH NEXT |
| Current city context | **17,565** | Raw public fact | Official 2025 Morton village PEP estimate from [S17] |
| Historical city context | **17,557** | Frozen historical fact | Official 2024 estimate from the saved 2024-vintage PEP file |
| Under age 18 | **25.9%** | Raw public fact | Morton village age share from [S14] |
| Age 65 or older | **23.1%** | Raw public fact | Morton village age share from [S14] |
| Focus On Eyes route | **4.07 routed minutes** | Derived route display | `244.3 seconds / 60 = 4.0717`, rounded to 4.07, from [R01] |
| Catchment method | **20-minute primary; 30-minute extended** | Method parameter | Exurban comparison windows, not measured population polygons |
| Peer tiers | **exactly 3 Tier 1; exactly 3 Tier 2** | Structural count | A bounded comparison set, not a complete supply census |
| Action structure | **exactly 3 Fix Cards; exactly 3 specialty lanes; one table** | Plan count | The do-now measurement package |
| Measurement period | **30 days** | Plan parameter | Baseline window, not a forecast horizon |

---

# Headline scores

## Band and calculation rules

The only allowed base bands are **20, 35, 50, 65, and 80**. Each weighted score uses:

`contribution = band or required computed input × weight`

The contributions are added at full precision, then rounded once. All weights within each score sum to 1.00. Client Opportunity correctly uses the already computed Market Demand-Supply result of 57 as one input. Room to Win correctly uses the already computed Competitive Pressure result of 57.

## Market Demand-Supply: 57 / 100

**Question answered:** Does the market look attractive enough to investigate?  
**Overall read:** Mixed market. Higher = better.

| Component | Band | Weight | Contribution | Why this band is logical | Sources | What remains unknown |
|---|---:|---:|---:|---|---|---|
| Demand Strength | 65 | 0.25 | 16.25 | Morton village has directionally supportive under-18 and 65-plus shares. City facts support a demand hypothesis but are not catchment measurements. | [S14], [S15], [S17] | Catchment population, VDU, realized demand |
| Supply Balance | 50 | 0.20 | 10.00 | Neutral unknown because the named alternatives are not a complete geocoded and deduplicated supply set. | [R01], [R02], [R03], [R04], [R05], [R06] | Complete offices, providers, weighted supply, VDU per office |
| Payer / Income Fit | 65 | 0.15 | 9.75 | Morton village income is a favorable public proxy. A proxy supports a directional band, not an operating claim. | [S14], [S15] | Payer mix, commercial coverage, collections |
| Growth / Future Demand | 50 | 0.15 | 7.50 | Neutral unknown because no catchment growth series or forward growth evidence was collected. | [S14], [S15] | Permits, residential pipeline, school growth, mobility |
| Specialty Demand Load | 65 | 0.15 | 9.75 | City age shares directionally support pediatric, senior, and chronic eye-care need. | [S14], [S15] | Catchment clinical burden, search demand, contact-lens demand, referrals |
| Market Data Confidence | 35 | 0.10 | 3.50 | City facts and point routes are reproducible, but the fixed-window market evidence needed for a strong read is missing. | [S14], [S15], [S17], [R01], [R02], [R03], [R04], [R05], [R06] | All fixed-window demographics, VDU, supply, providers, patient choice |

**Full-precision calculation**

`0.25×65 + 0.20×50 + 0.15×65 + 0.15×50 + 0.15×65 + 0.10×35`  
`= 16.25 + 10.00 + 9.75 + 7.50 + 9.75 + 3.50`  
`= 56.75`  
Nearest whole point: **57 / 100**.

**What could move it:** Measured 20- and 30-minute isochrones joined to block-group demographics, a complete office and provider census, catchment VDU, growth evidence, and payer or collections summaries could move the result in either direction.

## Competitive Pressure: internal input 57

**Question answered:** How much directional pressure may realistic patient alternatives create?  
**Direction:** Higher = more pressure. This internal input is inverted before report display.

| Component | Band | Weight | Contribution | Why this band is logical | Sources | What remains unknown |
|---|---:|---:|---:|---|---|---|
| Supply Saturation | 50 | 0.40 | 20.00 | Neutral unknown because the peer list is not a complete supply census and has no office or provider denominator. | [R01], [R02], [R03], [R04], [R05], [R06] | Complete supply, providers, population and VDU denominators |
| Patient Choice Pressure | 65 | 0.25 | 16.25 | Three named alternatives route within 20 minutes and five within 30 minutes, including a direct peer at 4.07 minutes and a retail substitute at 14.00 minutes. | [R01], [R02], [R03], [R04], [R05] | Patient origins, population weighting, full choice set, live traffic |
| Competitor Strength | 65 | 0.20 | 13.00 | Official pages show routine, medical, optical, dry-eye, and myopia overlap. This proves public offers, not patient draw. | [S07], [S08], [S09], [S10], [S11], [S12] | Peer utilization, reputation normalization, conversion, capacity |
| Access / Differentiation Pressure | 50 | 0.15 | 7.50 | Neutral mixed: Vintage publishes useful access and breadth, while peers publish overlapping access and services. | [S02], [S06], [S07], [S08], [S11] | Live slots, completion, call performance, comparable peer access |

**Full-precision calculation**

`0.40×50 + 0.25×65 + 0.20×65 + 0.15×50`  
`= 20.00 + 16.25 + 13.00 + 7.50`  
`= 56.75`  
Nearest whole point: **57 internal pressure**.

**What could move it:** A complete office/provider census, patient-origin choice analysis, independent peer-reputation data, and live access comparisons could raise or lower pressure.

## Room to Win: 43 / 100

**Question answered:** After translating pressure into the common higher-is-better direction, how much room appears available?

`Room to Win = 100 - internal Competitive Pressure`  
`100 - 57 = 43`

Result: **43 / 100**, labeled tight. Higher = better.

This is an exact inversion, not a separately banded score. If better evidence moves Competitive Pressure up, Room to Win moves down by the same number of points, and vice versa.

## Practice Competitiveness: 58 / 100

**Question answered:** How strong does Vintage Optical's public face look against the bounded peer set?  
**Overall read:** Mixed. Higher = better.

| Component | Band | Weight | Contribution | Why this band is logical | Sources | What remains unknown |
|---|---:|---:|---:|---|---|---|
| Visibility vs Peers | 50 | 0.20 | 10.00 | Neutral unknown. A dated query shows Vintage and a booking action but is not a rank grid or complete result set. | [S16] | Peer-normalized rank and complete query coverage |
| Access / Booking vs Peers | 65 | 0.20 | 13.00 | The practice publishes Monday-Saturday hours, same-day emergency access, a prominent CTA, and a flow reaching service/provider selection. | [S02], [S06], [S16] | Live slots, completion, conversion, comparable peer friction |
| Review Trust vs Peers | 50 | 0.20 | 10.00 | Neutral unknown. The 4.9 sample lacks count, recency, responses, and equivalent peer fields. | [S16] | Peer-normalized reputation and review behavior |
| Service-Line Differentiation | 65 | 0.15 | 9.75 | Vintage publishes broad routine, medical, specialty, contact, and optical services, but peers overlap on key lanes. | [S01], [S03], [S04], [S05], [S08], [S09], [S10] | Lane conversion, outcomes, patient preference, ownership |
| Website / Conversion Clarity | 65 | 0.15 | 9.75 | Service pages, providers, location, hours, and appointment access are visible. | [S01], [S02], [S03], [S04], [S05], [S06] | Owned conversion, mobile performance, speed |
| Location Convenience | 50 | 0.10 | 5.00 | Neutral mixed. Parking and a current Main Street location are public, but a direct peer is 4.07 minutes away. | [S02], [R01], [N00] | Patient-origin convenience and trip tolerance |

**Full-precision calculation**

`0.20×50 + 0.20×65 + 0.20×50 + 0.15×65 + 0.15×65 + 0.10×50`  
`= 10.00 + 13.00 + 10.00 + 9.75 + 9.75 + 5.00`  
`= 57.50`  
Half-up rounding: **58 / 100**.

**What could move it:** A rank grid, independent peer review export, live appointment audit, booking funnel, mobile/site testing, and patient-origin convenience analysis.

## Client Opportunity: 54 / 100

**Question answered:** How much actionable upside is visible to the practice owner?  
**Overall read:** At risk under the canonical band label. This is not a grade. Higher = better.

| Component | Value | Weight | Contribution | Why this value is logical | Sources | What remains unknown |
|---|---:|---:|---:|---|---|---|
| Computed Market Demand-Supply | 57 | 0.20 | 11.40 | The canonical formula requires the computed market result, not a new manual band. | [S14], [S15], [S17], [R01], [R02], [R03], [R04], [R05], [R06] | See Market Demand-Supply unknowns |
| Competitive Pressure Opportunity | 50 | 0.20 | 10.00 | Neutral unknown. Pressure exists directionally, but no weakness cluster, leakage, or capacity-supported white space is proven. | [S07], [S08], [S09], [S10], [S11], [S12], [R01], [R02], [R03], [R04], [R05] | Competitor weakness, leakage, capacity-supported wedge |
| Practice Differentiation Upside | 50 | 0.20 | 10.00 | Neutral measure-first position. The offer is broad and key lanes overlap, so proof should precede expansion claims. | [S01], [S03], [S04], [S05], [S08], [S09], [S10] | Lane conversion, defensible ownership, unmet need |
| Access Fixability | 50 | 0.15 | 7.50 | Neutral unknown. Public access exists, but the analysis did not measure access failure. | [S02], [S06] | Calls, slots, abandonment, cancellations, no-shows |
| Digital Visibility Fixability | 65 | 0.15 | 9.75 | Existing public surfaces make baseline measurement and reconciliation a bounded, plausible action. | [S01], [S02], [S03], [S04], [S05], [S06], [S16] | Rank, review, directory, response, and channel baselines |
| Execution Simplicity | 50 | 0.10 | 5.00 | Neutral unknown. The first actions are bounded, but ownership and staff capacity are not evidenced. | [S01], [S02], [S06] | Owner, operating cadence, execution capacity |

**Full-precision calculation**

`0.20×57 + 0.20×50 + 0.20×50 + 0.15×50 + 0.15×65 + 0.10×50`  
`= 11.40 + 10.00 + 10.00 + 7.50 + 9.75 + 5.00`  
`= 53.65`  
Nearest whole point: **54 / 100**.

**What could move it:** Evidence of actual demand leakage, competitor weakness, specialty conversion, available capacity, access failure, clear ownership, and execution capacity.

## Digital Presence: 57 / 100

**Question answered:** Can a prospective patient find, trust, and book the practice from its public digital surface?  
**Overall read:** Mixed. Higher = better.

| Component | Band | Weight | Contribution | Why this band is logical | Sources | What remains unknown |
|---|---:|---:|---:|---|---|---|
| Findability | 50 | 0.25 | 12.50 | Neutral unknown. The dated Maps sample shows Vintage but is not a rank grid or complete local-pack measure. | [S16] | Query coverage, rank distribution, directory consistency |
| Reputation | 50 | 0.20 | 10.00 | Neutral unknown. The 4.9 sample lacks count, velocity, recency, responses, and peer comparison. | [S16] | Peer-normalized reputation |
| Bookability | 65 | 0.20 | 13.00 | A public CTA reaches service and provider selection, and the Maps sample shows Book online. | [S06], [S16] | Slots, completion, abandonment, conversion |
| Site Quality | 65 | 0.15 | 9.75 | The site exposes location, hours, providers, and service-specific pages. | [S01], [S02], [S03], [S04], [S05] | Mobile rendering, Core Web Vitals, speed, conversion |
| Content & Specialty Signal | 65 | 0.10 | 6.50 | Dedicated dry-eye, myopia, and specialty-contact pages create a clear signal, though peers overlap. | [S03], [S04], [S05], [S08], [S09], [S10] | Search performance and unique lane ownership |
| Social / Local Proof | 50 | 0.10 | 5.00 | Neutral unknown. No verified social activity, local links, community mentions, or directory comparison were collected. | [S01], [S16] | Activity, local authority, community proof |

**Full-precision calculation**

`0.25×50 + 0.20×50 + 0.20×65 + 0.15×65 + 0.10×65 + 0.10×50`  
`= 12.50 + 10.00 + 13.00 + 9.75 + 6.50 + 5.00`  
`= 56.75`  
Nearest whole point: **57 / 100**.

**What could move it:** A repeatable rank grid, complete independent review data, tracked booking completion, mobile and performance tests, directory reconciliation, and verified social/local proof.

---

# Specialty opportunities

All three specialty scores use the same canonical formula:

`0.20×Local Demand Fit + 0.15×Competitive Gap + 0.15×Current Capability + 0.15×Access/Capacity Fit + 0.15×Revenue/Reimbursement Potential + 0.10×Referral Ecosystem Fit + 0.10×Evidence Confidence`

A score from 50 to 64 means **RESEARCH NEXT** under the rubric. It does not forecast patients or revenue, declare white space, or recommend unmeasured expansion.

## Dry eye / ocular surface: 52 / 100

| Component | Band | Weight | Contribution | Why assigned | Sources | Unknown |
|---|---:|---:|---:|---|---|---|
| Local Demand Fit | 65 | 0.20 | 13.00 | City age context supports a directional demand hypothesis. | [S14], [S15] | Catchment clinical and search demand |
| Competitive Gap | 35 | 0.15 | 5.25 | Tri-County and Vision Care Center publish direct dry-eye offers, so the lane is contested. | [S08], [S09] | Comparative depth, draw, outcomes |
| Current Capability | 65 | 0.15 | 9.75 | Vintage publishes a dedicated service and modalities. | [S03] | Volume, outcomes, staffing, throughput |
| Access / Capacity Fit | 50 | 0.15 | 7.50 | Neutral unknown. | [S03], [S06] | Slots, chair time, staff, rooms, follow-up |
| Revenue / Reimbursement Potential | 50 | 0.15 | 7.50 | Neutral unknown. | [S03] | Price, payer, collections, margin |
| Referral Ecosystem Fit | 50 | 0.10 | 5.00 | Neutral unknown. | [S03] | Relationships and referral density |
| Evidence Confidence | 35 | 0.10 | 3.50 | Offer and overlap are public; operating proof is limited. | [S03], [S08], [S09], [S14], [S15] | Demand, conversion, capacity, referrals, economics |

`13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 3.50 = 51.50`  
Half-up rounding: **52 / 100 - RESEARCH NEXT**.

The lane is not a forecast or white-space claim because competitors publish overlapping offers and the analysis lacks catchment demand, conversion, capacity, referral, outcome, and economic evidence.

## Myopia management: 52 / 100

| Component | Band | Weight | Contribution | Why assigned | Sources | Unknown |
|---|---:|---:|---:|---|---|---|
| Local Demand Fit | 65 | 0.20 | 13.00 | The city under-18 share supports a directional family-demand hypothesis. | [S14], [S15] | Catchment, school, and search demand |
| Competitive Gap | 35 | 0.15 | 5.25 | Vision Care Center publishes several myopia-control approaches, so the lane is contested. | [S09], [S10] | Comparative depth, draw, outcomes |
| Current Capability | 65 | 0.15 | 9.75 | Vintage publishes a dedicated myopia-management service. | [S04] | Starts, retention, outcomes, capacity |
| Access / Capacity Fit | 50 | 0.15 | 7.50 | Neutral unknown. | [S04], [S06] | Follow-up capacity, chair time, staff skill, protocols |
| Revenue / Reimbursement Potential | 50 | 0.15 | 7.50 | Neutral unknown. | [S04] | Price, payment, retention, collections, margin |
| Referral Ecosystem Fit | 50 | 0.10 | 5.00 | Neutral unknown. | [S04] | School, pediatric, parent, provider referrals |
| Evidence Confidence | 35 | 0.10 | 3.50 | Offer, child-share proxy, and overlap are public; operating proof is limited. | [S04], [S09], [S10], [S14], [S15] | Conversion, capacity, referrals, economics |

`13.00 + 5.25 + 9.75 + 7.50 + 7.50 + 5.00 + 3.50 = 51.50`  
Half-up rounding: **52 / 100 - RESEARCH NEXT**.

It matches dry eye because both lanes currently have the same band pattern, not because the underlying services are identical.

## Specialty contact lenses: 51 / 100

| Component | Band | Weight | Contribution | Why assigned | Sources | Unknown |
|---|---:|---:|---:|---|---|---|
| Local Demand Fit | 50 | 0.20 | 10.00 | Neutral unknown. | [S05] | Contact-lens population, keratoconus burden, search and referral demand |
| Competitive Gap | 50 | 0.15 | 7.50 | Neutral unknown. Peers publish contact-lens services, but equivalent specialty depth was not established. | [S07], [S08], [S12] | Complete specialty-depth comparison |
| Current Capability | 65 | 0.15 | 9.75 | Vintage publishes specialty lens types and an offer. | [S05] | Fit volume, success, chair time, capacity |
| Access / Capacity Fit | 50 | 0.15 | 7.50 | Neutral unknown. | [S05], [S06] | Fitting availability, doctor time, staff skill, rooms |
| Revenue / Reimbursement Potential | 50 | 0.15 | 7.50 | Neutral unknown. | [S05] | Pricing, payer, remakes, chair-time cost, margin |
| Referral Ecosystem Fit | 50 | 0.10 | 5.00 | Neutral unknown. | [S05] | Ophthalmology, optometry, keratoconus referrals |
| Evidence Confidence | 35 | 0.10 | 3.50 | The offer is public, but market and operating evidence is limited. | [S05], [S07], [S08], [S12] | Demand, gap, conversion, capacity, referrals, economics |

`10.00 + 7.50 + 9.75 + 7.50 + 7.50 + 5.00 + 3.50 = 50.75`  
Nearest whole point: **51 / 100 - RESEARCH NEXT**.

The result is not a forecast or white-space claim. A complete peer service audit and measured fitting demand, outcomes, capacity, referrals, and economics could move it.

---

# Public facts and routes

## Current and historical city population

- **17,565** is the official 2025 Population Estimates Program estimate for Morton village, Illinois, from [S17]. It is the current displayed **2025 city estimate**.
- **17,557** is the historical 2024 estimate from the frozen official 2024-vintage PEP file. The newer 2025-vintage file revises its own 2024 back-series value to 17,555, but that later revision does not erase the earlier file's historical lineage.
- Changing the current display from 17,557 to 17,565 changes no score or directional band. The scoring model did not substitute either city value into a drive-time catchment. The update adds current city context, but no new catchment population, VDU, supply, growth, or choice evidence.

**Boundary:** City context is not a drive-time catchment. Population, households, age bands, VDU, offices, providers, and ratios remain null for the 5-, 10-, 15-, 20-, and 30-minute windows.

## Age shares

- **25.9% under age 18** comes from Census QuickFacts [S14]. It is a city-level family-demand proxy.
- **23.1% age 65 or older** comes from [S14]. It is a city-level senior and medical-demand proxy.

The percentages are raw public facts. Their use in 65 bands is directional because the catchment distribution, realized care demand, payer mix, and patient behavior are unknown. The ages 18 and 65 define the Census categories; they are not separate performance measures.

## Route and catchment method

The [R01] saved OSRM route from Vintage Optical to Focus On Eyes reports **244.3 seconds**:

`244.3 seconds / 60 seconds per minute = 4.0717 minutes`  
Rounded to two decimals: **4.07 routed minutes**.

This is one practice-origin, point-to-point route. It has no live traffic or time-of-day model. It is not a polygon isochrone, patient-origin model, or complete supply census.

The market method uses a **20-minute primary** and **30-minute extended** window for the medium-confidence exurban classification. Exactly three named routed alternatives fall within the primary window and five within the extended window. These are bounded observations, not complete office counts. Illinois Eye Center has an official location source [S12] but no successful route [R06].

## The bounded peer set

| Tier | Exactly three entries | Why the tier is structural, not a ranking |
|---|---|---|
| Tier 1 direct peers | Focus On Eyes; Tri-County Eye Center Washington; Vision Care Center Washington | Similar or overlapping optometry/service models judged relevant within nearby or extended context |
| Tier 2 substitutes | Bard Optical East Peoria; Illinois Eye Center Washington; Walmart Vision Center Morton | Different models that may substitute for part of demand |

Tier 1 and Tier 2 are taxonomy labels. They do not mean first place or second place. The set was intentionally bounded for directional comparison and must not be read as the complete market.

---

# Fix Card formulas

The report contains **exactly three GROW Fix Cards**, **exactly three existing specialty lanes**, and a **30-day** baseline window. F-001 calls for **one consolidated lane table**. These are plan counts, not measured results. Every formula is a plug-in measurement, not a forecast.

## F-001 - Specialty conversion baseline

Applied separately to dry eye, myopia management, and specialty contact lenses:

`inquiry-to-book rate = lane booked evaluations / lane inquiries`

- Numerator: lane inquiries that produce a booked evaluation during the defined 30-day cohort.
- Denominator: all eligible, deduplicated inquiries assigned to that same lane and cohort.

`book-to-start rate = lane starts / lane booked evaluations`

- Numerator: patients who begin the lane's defined plan or service.
- Denominator: booked evaluations eligible to produce a start under the same cohort rule.

`completion rate = lane completed plans / lane starts`

- Numerator: starts meeting the practice's predeclared completion definition.
- Denominator: eligible lane starts with enough follow-up time under the stated cohort rule.

The one table should contain lane, inquiries, booked evaluations, starts, completed plans, available slots, and owner. Cohort timing, duplicates, cancellations, reschedules, and completion rules must be defined before calculation.

## F-002 - Access diagnostic

`access gap count = unanswered or abandoned calls + booking attempts without completion + requests without an acceptable slot`

- Each term is an observed count under mutually exclusive disposition rules so one attempt is not counted twice.
- "Acceptable slot" needs a declared visit-type and time-window rule.

`realized gap rate = access gap count / total access attempts`

- Numerator: the deduplicated observed access gap count.
- Denominator: all eligible phone and digital access attempts in the same 30-day window.

`later sensitivity = measured access gap count × tested recovery rate`

- First factor: a measured count, not an assumed leakage volume.
- Second factor: a recovery rate established by a controlled follow-up test, not a guessed conversion rate.

The output diagnoses whether a fixable gap exists. It does not assume leakage, patients, or revenue.

## F-003 - Listing, review, referral, and recall baseline

`listing accuracy rate = correct tracked listings / tracked listings`

- Numerator: tracked public listings matching the declared name, address, phone, and other audited fields.
- Denominator: every surface included in the dated tracked-listing inventory.

`review velocity = new verified reviews / 30 days`

- Numerator: new reviews meeting the predeclared verification and date rules.
- Denominator: the fixed 30-day observation period, not patient count.

`referral book rate = booked referred patients / referral inquiries`

- Numerator: eligible referred inquiries that produce a booking.
- Denominator: all eligible referral inquiries in the same cohort.

`recall book rate = booked recall patients / eligible recall contacts`

- Numerator: eligible recall contacts that produce a booking.
- Denominator: all contacts meeting the predeclared recall eligibility and outreach rules.

## Zero denominator rule

For every rate, if the denominator is zero, missing, or not yet final, the result is **null / not calculable, never zero**. A zero rate would falsely claim that eligible opportunities existed and none converted. Counts missing from collection also remain null rather than being silently converted to zero.

---

# Structural numbers and identifiers

| Number or identifier | What it means | What it does not mean |
|---|---|---|
| Section 1, 2, 3 | Navigation for market, competition, and opportunity | Score, rank, or priority magnitude |
| Tier 1 and Tier 2 | Peer taxonomy classes | First place, second place, or measured quality |
| Exactly 3 Tier 1 and 3 Tier 2 | Bounded peer-set design | Complete office or provider census |
| F-001, F-002, F-003 | Stable Fix Card identifiers and order | Measured impact or importance |
| S01-S17, N00, R01-R06 | Source registry identifiers | Values, scores, or evidence strength by their digits |
| 100 | Common score denominator and inversion base | Raw fact or percentage confidence |
| 20 and 30 minutes | Selected primary and extended method windows | Measured isochrone populations |
| 30 days | Baseline collection window | Forecast horizon or promised result |
| 605 | Street number in 605 S Main St | Count or score |
| 2024 and 2025 | Source-vintage and estimate years | Score values |
| 2026 | Copyright/report year | Evidence measurement |
| 18 and 65 | Age-category thresholds | Standalone market results |
| 60 | Seconds-per-minute conversion factor | Observed route value |

---

# Logical consistency checks

## Why the scores can coexist

- **Market 57** says public age and income context is supportive, while supply, growth, VDU, and fixed-window market proof are incomplete.
- **Room to Win 43** says directional competitive pressure is tighter. It is exactly the inverse of internal pressure 57 and does not contradict Market 57. A market can have demand support and still contain meaningful alternatives.
- **Practice Competitiveness 58** says Vintage's public service breadth and access path are useful, while visibility, reputation, live access, conversion, and convenience are not peer-normalized.
- **Client Opportunity 54** combines the market result of 57 with four neutral 50 inputs and one 65 for bounded digital measurement fixability. It asks about actionable upside, not market attractiveness alone.
- **Digital Presence 57** reflects usable booking, site structure, and specialty content, offset by unmeasured rank, reputation, and social/local proof.

## Why the population refresh changes no score

The historical display of 17,557 was updated to the current 2025 estimate of 17,565. Neither value is a measured 20- or 30-minute catchment population. The update therefore does not alter Demand Strength, Specialty Demand Load, Supply Balance, Market Data Confidence, or another base band. No full-precision total or rounded score changes.

## Why values repeat

- Market Demand-Supply, internal Competitive Pressure, and Digital Presence each equal **57**, but they answer different questions and use different component sets. Each happens to total **56.75** before rounding.
- Dry eye and myopia both equal **52** because their current band patterns are identical: 65, 35, 65, 50, 50, 50, 35 under the same weights. The evidence behind those bands is lane-specific.
- **50** recurs because it is the neutral midpoint used for missing or mixed evidence. Repetition is not proof that measured performance is average.
- **65** recurs as a directionally supportive band where a public signal exists but stronger operating proof does not.
- **35** recurs where evidence confidence is limited or a specialty gap is publicly contested.
- **100** recurs only as the common score scale and Room to Win inversion base.

## Disconfirmers

1. A complete geocoded office census and provider join could move pressure, supply balance, and Room to Win materially in either direction.
2. Patient-origin analysis, live traffic, and trip-tolerance evidence could change which peers are practically relevant.
3. A rank grid and equivalent peer review fields could change visibility, reputation, Practice Competitiveness, and Digital Presence.
4. Public pages may overstate or understate actual booking completion, conversion, capacity, outcomes, and economics.
5. The public specialty breadth already visible at Vintage disproves a simple "no offer" claim, while competitor overlap disproves an uncontested white-space claim.
6. Catchment demographics may differ from Morton village context.
7. Measured operating ownership and staff capacity could make the Fix Cards easier or harder to execute than the neutral 50 implies.

---

# What we do not know

The public-only evidence does not establish:

- catchment population or households for any fixed drive-time window;
- complete eye-care supply or a deduplicated office census;
- cleaned OD/provider counts;
- Vision Demand Units, or VDU, and VDU per office;
- population-weighted patient choice;
- peer-normalized visibility or reputation;
- independent review count, recency, response behavior, and comparable peer fields;
- live appointment access, phone handling, slot depth, completion, cancellations, no-shows, or unmet requests;
- booking, inquiry, start, completion, recall, referral, or optical conversion;
- specialty capacity, staffing, chair time, rooms, protocols, and execution capacity;
- clinical outcomes or patient draw;
- referral relationships or referral density;
- payer mix, pricing, collections, margin, contribution, or other economics.

Confidence remains **C** because the analysis is public data plus a directional local and competitor scan. The missing evidence is why the specialty lanes remain RESEARCH NEXT and the Fix Cards begin with measurement.

---

# Source dictionary

The registry contains **24 unique source IDs**: S01-S17, N00, and R01-R06. Each ID below links to the registered public URL. A public URL is the external source address. A saved or frozen receipt path is a local audit artifact and is not an external link.

| ID | Claim use | Confidence / status | Limitation |
|---|---|---|---|
| [S01] | Vintage identity, service breadth, on-site lab, three named optometrists, appointment CTA | High / fetched | Practice-controlled claims do not prove utilization, outcomes, capacity, conversion, or economics. |
| [S02] | Current address, hours, parking, same-day emergency statement, appointment link | High / fetched | Posted access does not prove live availability, phone performance, or realized demand. |
| [S03] | Public dry-eye service and modalities | High / fetched | Does not prove volume, outcomes, capacity, or contribution margin. |
| [S04] | Public myopia-management service and options | High / fetched | Does not prove starts, retention, outcomes, or economics. |
| [S05] | Public specialty-contact service and lens types | High / fetched | Does not prove referrals, chair time, fit success, capacity, or economics. |
| [S06] | Public booking path reached service and provider selection | High / fetched, no submission | No selection or submission occurred; slots and completion remain unknown. |
| [S07] | Focus On Eyes identity, Morton location, services, hours, appointment request | High / fetched | Peer-controlled content; no independent reviews, live slots, utilization, or capacity. |
| [S08] | Tri-County identity, location, broad services, dry-eye overlap | High / fetched | Public claims do not prove capacity, volume, outcomes, or Morton patient draw. |
| [S09] | Vision Care Center identity and dry-eye overlap | High / fetched | No independent utilization, outcomes, capacity, or patient-origin evidence. |
| [S10] | Vision Care Center myopia-control approaches | High / fetched | Public positioning does not prove starts, outcomes, capacity, or economics. |
| [S11] | Bard East Peoria identity, address, model, appointment access | High / fetched | Does not prove demand from Morton or peer-normalized reputation. |
| [S12] | Illinois Eye Center Washington identity, address, service breadth | High / fetched | Entity is current, but the supplied geocode produced no match or route. |
| [S13] | Attempted first-party Walmart Vision Center verification | Unknown / blocked | Bot-blocked; no official service, hours, booking, or review claim is treated as fetched. |
| [S14] | Morton QuickFacts age shares, income, density, and commute | High / fetched | Mutable city-boundary context, not a drive-time catchment. |
| [S15] | 2024 ACS 5-year dataset authority and vintage | High / fetched | Documentation URL; no block-group-to-isochrone join was completed. |
| [S16] | Dated limited Maps sample showing 4.9 and Book online | Medium / partial sample | No reliable count, recency, responses, peer normalization, or complete result set; rating is not clinical proof. |
| [S17] | Official Morton village 2025 PEP estimate of 17,565 | High / fetched and frozen | Village boundary only, not a 5-, 10-, 15-, 20-, or 30-minute catchment population. |
| [N00] | Exact-address subject geocode used as route origin | High / matched | OpenStreetMap geocoding is not an official practice listing and needs entity review. |
| [R01] | Vintage to Focus On Eyes: 4.07 minutes, 1.56 route miles | High / routed | One origin route, no traffic or time-of-day model, not an isochrone or choice set. |
| [R02] | Vintage to matched Walmart Supercenter: 5.71 minutes, 2.35 miles | Medium / routed | Match is the store entity, not a separately matched Vision Center; location context only. |
| [R03] | Vintage to Tri-County Washington: 20.94 minutes, 10.85 miles | High / routed | One origin route, no traffic, not an isochrone or patient-choice set. |
| [R04] | Vintage to Vision Care Center Washington: 22.41 minutes, 16.33 miles | High / routed | One origin route, no traffic, not an isochrone or patient-choice set. |
| [R05] | Vintage to Bard East Peoria: 14.00 minutes, 9.25 miles | High / routed | One origin route, no traffic, not an isochrone or patient-choice set. |
| [R06] | Attempted Illinois Eye Center Washington geocode | Unknown / geocode missing | No coordinate match or OSRM route; identity and address rely on S12. |

## Saved and frozen receipts

These paths are local lineage artifacts, not public links:

- Current receipt summary: `work-refresh-v3/freeze-current-public-number-receipts-v2/receipt_summary.json`
- Frozen official 2025 PEP file: `work-refresh-v3/freeze-current-public-number-receipts-v2/source_receipts/census-pep-sub-est2025.csv`
- Frozen official 2024-vintage PEP file: `work-refresh-v3/freeze-current-public-number-receipts-v2/source_receipts/census-pep-sub-est2024.csv`
- Saved QuickFacts audit extract: `work-refresh-v3/freeze-current-public-number-receipts-v2/source_receipts/quickfacts-live-audit-extract.json`
- Saved current R01 response: `work-refresh-v3/freeze-current-public-number-receipts-v2/source_receipts/osrm-r01-current.json`

The registered source URLs remain the clickable public references. The local receipts preserve the exact values used for refresh and audit.

---

**Vintage Optical, Morton**  
**Internal publish-candidate - Project Room review required - Public-only - Confidence C - External actions: none**  
**© 2026 MyBCAT**

[S01]: https://www.vintageopt.com/
[S02]: https://www.vintageopt.com/hours-location/
[S03]: https://www.vintageopt.com/medical-eye-care/dry-eye-treatment/
[S04]: https://www.vintageopt.com/medical-eye-care/myopia-management/
[S05]: https://www.vintageopt.com/contact-lenses/specialty-contact-lenses/
[S06]: https://scheduleyourexam.com/v3/index.php/5788
[S07]: https://visionsource-focusoneyes.com/
[S08]: https://www.tricountyeyecenter.com/
[S09]: https://vcc2020.com/
[S10]: https://vcc2020.com/service/myopia-control/
[S11]: https://www.bardoptical.com/eye-doctor-peoria-east/
[S12]: https://www.illinoiseyecenter.com/location/washington/
[S13]: https://www.walmart.com/store/5157-morton-il/vision-center
[S14]: https://www.census.gov/quickfacts/fact/table/mortonvillageillinois/PST045224
[S15]: https://api.census.gov/data/2024/acs/acs5.html
[S16]: https://www.google.com/maps/search/optometrist+near+Morton%2C+IL
[S17]: https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/cities/totals/sub-est2025.csv
[N00]: https://nominatim.openstreetmap.org/search?q=605+South+Main+Street%2C+Morton%2C+Illinois+61550&format=jsonv2&limit=5&addressdetails=1&countrycodes=us
[R01]: https://router.project-osrm.org/route/v1/driving/-89.4669666,40.6048878;-89.4680865,40.6196077?overview=false&steps=false&alternatives=false
[R02]: https://router.project-osrm.org/route/v1/driving/-89.4669666,40.6048878;-89.4617449,40.6301455?overview=false&steps=false&alternatives=false
[R03]: https://router.project-osrm.org/route/v1/driving/-89.4669666,40.6048878;-89.432644,40.704092?overview=false&steps=false&alternatives=false
[R04]: https://router.project-osrm.org/route/v1/driving/-89.4669666,40.6048878;-89.4455579,40.7145273?overview=false&steps=false&alternatives=false
[R05]: https://router.project-osrm.org/route/v1/driving/-89.4669666,40.6048878;-89.5857929,40.6821622?overview=false&steps=false&alternatives=false
[R06]: https://nominatim.openstreetmap.org/search?q=93+Eastgate+Drive%2C+Washington%2C+Illinois+61571&format=jsonv2&limit=5&addressdetails=1&countrycodes=us
