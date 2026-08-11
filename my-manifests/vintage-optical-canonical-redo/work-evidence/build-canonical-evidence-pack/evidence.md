# Stage 1 Evidence Ledger

Report visibility: `internal_only_unroomed_draft`

Project Room: `EMPTY / UNROOMED`

External-use status: internal-only, unroomed draft. It is not client-ready or prospect-ready.

Evidence labels in this file are claim-level states. `VERIFIED` means the cited source directly supports the narrow statement. `INFERRED` means the statement is a bounded interpretation of cited evidence. `UNKNOWN` means the required evidence is absent and no proxy is substituted.

## Subject

- VERIFIED: Vintage Optical's current public location is 605 S Main St, Morton, IL 61550. The official page publishes the address and the Nominatim receipt matches the exact street address. [S02, N00]
- VERIFIED: The public site presents routine eye exams, pediatric care, medical eye care, dry-eye treatment, myopia management, glaucoma management, retinal care, optical, contact lenses, specialty contact lenses, and Neurolens. [S01, S03, S04, S05]
- VERIFIED: The public site names three optometrists and provides a public appointment CTA. [S01, S06]
- VERIFIED: The public location page lists Monday through Saturday hours and says same-day emergency appointments are offered. [S02]
- VERIFIED: A dated, limited Google Maps sample displayed 4.9 and a Book online action for Vintage Optical on 2026-07-29. [S16]
- UNKNOWN: Independent review count, review recency, owner-response behavior, and comparison with peers. The dated sample does not contain the required export fields. [S16]
- UNKNOWN: Public evidence does not establish patient volume, completed visits, call leakage, booking conversion, specialty starts, optical capture, capacity, staffing sufficiency, payer mix, revenue, contribution margin, or economics. [S01, S02, S03, S04, S05, S06]

## Peer evidence and tier logic

- VERIFIED: Focus On Eyes publishes a Morton address, comprehensive examinations, disease care, lenses, frames, contacts, weekday hours through 6 p.m., Saturday hours, and an appointment request. [S07]
- VERIFIED: OSRM returned 4.07 minutes from Vintage Optical to Focus On Eyes. [R01]
- INFERRED: Focus On Eyes is Tier 1 because it is a close routed independent practice with strong routine, family, disease-care, contact-lens, and optical overlap. [S07, R01]
- VERIFIED: Tri-County Eye Center publishes a Washington address and eye examinations, disease treatment, dry-eye clinic, contact lenses, macular-health, emergency-care, and eyewear services. [S08]
- VERIFIED: OSRM returned 20.94 minutes from Vintage Optical to Tri-County Eye Center. [R03]
- INFERRED: Tri-County is Tier 1 because its service overlap is broad and it falls just outside the exurban 20-minute primary window but inside the 30-minute extended context. [S08, R03, S14]
- VERIFIED: Vision Care Center publishes dry-eye diagnostics and therapies plus myopia-control approaches including atropine, multifocal contacts and glasses, and Ortho-K. [S09, S10]
- VERIFIED: OSRM returned 22.41 minutes from Vintage Optical to Vision Care Center Washington. [R04]
- INFERRED: Vision Care Center is Tier 1 because it is a regional optometry peer with direct specialty overlap inside the 30-minute extended context. [S09, S10, R04]
- VERIFIED: Bard Optical's official East Peoria page identifies the entity and address and provides eye-care, optical, and appointment-request access. [S11]
- VERIFIED: OSRM returned 14.00 minutes from Vintage Optical to Bard Optical East Peoria. [R05]
- INFERRED: Bard is Tier 2 because its regional retail-optical model can substitute for routine eye care and optical demand but is not a like-for-like independent specialty practice. [S11, R05]
- VERIFIED: Illinois Eye Center's official Washington page identifies a current location at 93 Eastgate Drive and publishes routine, medical, contact-lens, and optical breadth. [S12]
- VERIFIED: The supplied Nominatim request for Illinois Eye Center Washington returned no match, so no OSRM route was produced. [R06]
- INFERRED: Illinois Eye Center is Tier 2 because its medical-surgical, optometry, contact-lens, and optical model can divert part of demand and can also be referral or co-management context. Route relevance remains unmeasured. [S12, R06]
- VERIFIED: The Walmart first-party location-page fetch was blocked. [S13]
- VERIFIED: The stored route to the Nominatim-matched Walmart Supercenter entity returned 5.71 minutes. [R02]
- INFERRED: Walmart Vision Center Morton remains a required Tier 2 named substitute, but its current service overlap is not verified here and the route supports store-location context only. [S13, R02]

## Market inputs

- VERIFIED: The peer travel observations use stored subject-origin point-to-point drive-time receipts. They are not measured polygon isochrones, live-traffic estimates, or patient-origin choice sets. [R01, R02, R03, R04, R05, R06]
- VERIFIED: The repository uses 20 minutes primary and 30 minutes extended for an exurban market. The market classification is evidence-linked but remains interpretive. [S14, R03, R04]
- VERIFIED: Census QuickFacts reports Morton city context including a 2024 population estimate of 17,557, 25.9% under age 18, 23.1% age 65 or older, median household income of $94,402, 2020 density of 1,336.4 per square mile, and 16.6-minute mean commute. Prior ACS material reports a 2024 5-year population of 16,595 and median age 41.4. [S14, S15]
- INFERRED: Morton is best treated as exurban for this run because it is a lower-density, car-oriented small community and relevant regional peers sit between 20 and 30 minutes. Confidence is medium. [S14, R03, R04]
- UNKNOWN: Population, households, age bands, VDU, offices, providers, weighted offices, population per office, and VDU per office for every fixed 5, 10, 15, 20, and 30-minute window. No city or ZIP value is substituted. [S14, S15]
- VERIFIED: The fixed-window `known_routed_alternatives` fields contain only the five successful stored routes that fall within each minute threshold. [R01, R02, R03, R04, R05]
- UNKNOWN: Complete supply count and population-weighted patient choice. The routed alternatives are not a complete office census. [R01, R02, R03, R04, R05, R06]

## Source authority and risks

- VERIFIED: Official subject and peer pages are direct sources for current public identity, address, hours, booking links, and stated services. [S01, S02, S07, S08, S09, S10, S11, S12]
- INFERRED: Official pages are high-authority for what each organization claims publicly, but not independent evidence of utilization, outcomes, patient draw, capacity, or financial performance. [S01, S02, S07, S08, S09, S10, S11, S12]
- VERIFIED: Census is the source-of-record public authority used for city context. [S14, S15]
- VERIFIED: Nominatim and OSRM receipts provide reproducible entity/geocode and route observations, subject to match and routing limitations. [N00, R01, R02, R03, R04, R05, R06]
- VERIFIED: The Google Maps evidence is a dated partial sample, not an independent review export or rank grid. [S16]
- VERIFIED: The direct Walmart first-party fetch was blocked. The Nominatim store entity is used only for location context. [S13, R02]
- INFERRED: Review strength cannot be normalized because count, recency, responses, and equivalent peer fields were not collected. [S16]

## Missing inputs

- UNKNOWN: Polygon isochrones for all fixed windows.
- UNKNOWN: Census block-group intersections and population-weighted demographic joins.
- UNKNOWN: Complete geocoded and deduplicated eye-care office census.
- UNKNOWN: NPPES provider join and provider-address cleaning.
- UNKNOWN: CDC PLACES overlay and catchment-weighted chronic-demand inputs.
- UNKNOWN: Independent review export with rating, count, recency, and response fields for subject and peers.
- UNKNOWN: Owned conversion, appointment availability, call handling, capacity, staffing, service-line starts, collections, optical capture, payer mix, and economics.

## Disconfirmers and hypothesis control

- VERIFIED: The subject already publishes a broad routine, medical, specialty, optical, and online-booking surface. This disconfirms a simple claim that the practice lacks public specialty breadth or any booking path. [S01, S03, S04, S05, S06]
- VERIFIED: Specialty overlap is visible at Tri-County and Vision Care Center, so public subject breadth alone does not prove a defensible specialty gap. [S08, S09, S10]
- UNKNOWN: Strong public pages may not correspond to strong conversion or capacity for either the subject or peers.
- UNKNOWN: A complete supply census could materially change the apparent pressure.
- UNKNOWN: Live traffic, time of day, patient willingness to travel, referrals, and actual patient origins could change route relevance.
- INFERRED: Prior analyst decisions E033 through E036 are hypotheses only. None is treated as verified fact in this evidence pack because owned operating and transferability evidence is absent.

## Evidence-round boundary

- VERIFIED: This bounded round establishes Stage 0 and Stage 1 evidence inputs only.
- VERIFIED: No final score stack is calculated inside this evidence round. Subsequent scoring, positioning, and Fix Card artifacts are recorded separately in `scores.json` and `data/scoring_notes.md` after assembly.
- VERIFIED: No external actions were taken.
