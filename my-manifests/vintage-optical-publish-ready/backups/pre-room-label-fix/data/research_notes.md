# Research Notes

## What changed from the invalid first run

1. Replaced the prior noncanonical one-pager assumptions with the exact recorded GROW intake, including the existing-client gate and recorded prospect relationship.
2. Applied `report_visibility: internal_only_unroomed_draft` because Project Room preflight was blocked and room status is EMPTY / UNROOMED.
3. Rebuilt Tier 1 direct peers and Tier 2 substitutes with official entity/service evidence, explicit model and overlap logic, source confidence, and stored route linkage.
4. Replaced older straight-line distances with the five successful point-to-point OSRM durations from the supplied receipts.
5. Added exactly 5, 10, 15, 20, and 30-minute fixed-window records while keeping all unavailable demographic, VDU, office, provider, and ratio fields null.
6. Updated the current Morton village population to the official 2025 PEP estimate of 17,565 under `city_context_only`, retained the historical 2024-vintage estimate of 17,557 in lineage, and did not substitute either value into route windows. [S17, S18]
7. Downgraded prior analyst decisions E033 through E036 to hypotheses.
8. The evidence round stopped before scoring. No final score stack, Digital Presence Score, specialty score, or Fix Card math was calculated inside that bounded round. Subsequent scoring, positioning, and Fix Card artifacts are recorded separately in `scores.json` and `data/scoring_notes.md` after assembly.

## Exact fetch and route limitations

- Vintage Optical, Focus On Eyes, Tri-County Eye Center, Vision Care Center, Bard Optical, Illinois Eye Center, and Census public pages were reachable on 2026-07-29.
- The direct Walmart official Vision Center page was bot-blocked. It is recorded as `blocked`; no Walmart official service, access, booking, or review claim is treated as fetched. The Nominatim-matched Walmart Supercenter entity supports location context only.
- The Google Maps sample dated 2026-07-29 supports only a 4.9 subject rating and a Book online action. It does not support a review count, review recency, response comparison, peer normalization, or complete Maps result set.
- The route receipts were collected at 2026-07-30T01:35:21.143554+00:00 using Nominatim/OpenStreetMap and the OSRM public endpoint.
- Successful subject-origin routes are Focus On Eyes 4.07 minutes, Walmart store entity 5.71, Bard Optical East Peoria 14.00, Tri-County Eye Center Washington 20.94, and Vision Care Center Washington 22.41.
- The frozen current-route check again returned 244.3 seconds for Focus On Eyes, which rounds to 4.07 minutes. The current route value is unchanged.
- Illinois Eye Center Washington had current official entity evidence but no Nominatim match and no OSRM route.
- OSRM observations are point-to-point practice-origin routes. They are not polygon isochrones, patient-origin choice sets, live-traffic estimates, or time-of-day measurements.

## Population source vintage

- Current value: the official 2025 PEP file reports 17,565 for Morton village, Illinois. [S17]
- Historical lineage: the earlier official 2024-vintage PEP file reports 17,557 for 2024, which remains the authority for the value shown in the previous report. [S18]
- Revision handling: the 2025-vintage file revises its 2024 estimate to 17,555. That revised back-series value is retained as a vintage note, not substituted for the earlier file's historical 17,557. [S18]
- QuickFacts scope: the current 25.9% under-18 share and 23.1% age-65-plus share remain sourced to S14.
- Catchment boundary: all population and age facts remain village-boundary context. Every 5, 10, 15, 20, and 30-minute population field remains null.
- Score effect: none. The refresh changes no manual band, weight, formula, score, specialty score, Fix Card, peer tier, route value, or Confidence C grade.

## Missing evidence

- Complete supply census, meaning a complete geocoded and deduplicated eye-care office census: missing.
- NPPES provider join and address cleaning: missing.
- Independent review export with rating, count, recency, and responses for subject and peers: missing.
- Polygon isochrones for 5, 10, 15, 20, and 30 minutes: missing.
- Census block-group intersection for each isochrone: missing.
- CDC PLACES overlay: missing.
- Population-weighted patient-choice distribution: missing.
- Owned conversion, call handling, appointment availability, no-show, recall, specialty-start, optical-capture, capacity, staffing, payer, collections, margin, and economics data: missing.

## Market classification

Morton is classified as `exurban` with medium confidence. Census city context shows a small, lower-density, car-oriented community, and routed regional peers at 20.94 and 22.41 minutes are relevant within the repository's 30-minute exurban extended context. The selected primary window is 20 minutes and the extended window is 30 minutes. This classification could change with a catchment density surface, trip-tolerance evidence, or patient-origin data.

## Project Room and action status

- Project Room preflight: BLOCKED.
- Project Room status: `inventory_review_required`.
- Report visibility: `internal_only_unroomed_draft`.
- External-use claim: prohibited.
- External actions: none.
- Forms submitted: none.
- Appointments selected or booked: none.
- Contacts, sends, commits, pushes, publications, and deployments: none.

## Decision residue

- Hardest decision: selecting the market type while preserving the required peer relevance and refusing to turn point routes or city context into catchment measurements. The chosen classification is exurban, medium confidence, with 20-minute primary and 30-minute extended windows.
- Current refresh decision: use S17, the official 2025 PEP file, for the displayed 17,565 current estimate; preserve S18, the earlier 2024-vintage file, as authority for the historical 17,557; and record the later file's revised 17,555 back-series value without rewriting prior lineage. Score effect: none.
- Alternatives rejected: rural/small-town with a 25 to 30-minute primary and optional 45-minute diagnostic, because the available Census density and 16.6-minute commute did not justify the stronger rural assumption; urban/suburban, because the named 20.94 and 22.41-minute peers would be pushed outside its standard 20-minute extended window; reusing straight-line mileage, because exact OSRM receipts supersede it.
- Least-confident assumption: the required named peer set is directionally representative of realistic alternatives. A complete geocoded and deduplicated office census, provider join, patient-origin analysis, or live route study could materially change pressure and tier relevance.
- Prior E033 hypothesis: measure specialty conversion before adding an undifferentiated service. Status remains hypothesis because owned conversion, capacity, and economics are missing.
- Prior E034 hypothesis: run an access diagnostic before changing hours or staffing. Status remains hypothesis because call, slot, cancellation, and no-show evidence is missing.
- Prior E035 hypothesis: compound recall, referral, review, optical, and listing loops before broad awareness spending. Status remains hypothesis because owned funnel and channel evidence is missing.
- Prior E036 hypothesis: test transferability of specialty care and relationships. Status remains hypothesis and is outside this GROW Stage 0 and Stage 1 evidence round.
