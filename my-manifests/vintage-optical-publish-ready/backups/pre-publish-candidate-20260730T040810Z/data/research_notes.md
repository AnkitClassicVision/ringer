# Research Notes

## What changed from the invalid first run

1. Replaced the prior noncanonical one-pager assumptions with the exact cleared GROW intake, including the existing-client gate and confirmed prospect relationship.
2. Applied `report_visibility: internal_only_unroomed_draft` because Project Room preflight was blocked and room status is EMPTY / UNROOMED.
3. Rebuilt Tier 1 direct peers and Tier 2 substitutes with official entity/service evidence, explicit model and overlap logic, source confidence, and stored route linkage.
4. Replaced older straight-line distances with the five successful point-to-point OSRM durations from the supplied receipts.
5. Added exactly 5, 10, 15, 20, and 30-minute fixed-window records while keeping all unavailable demographic, VDU, office, provider, and ratio fields null.
6. Kept Morton Census values under `city_context_only` instead of substituting them into route windows.
7. Downgraded prior analyst decisions E033 through E036 to hypotheses.
8. The evidence round stopped before scoring. No final score stack, Digital Presence Score, specialty score, or Fix Card math was calculated inside that bounded round. Subsequent scoring, positioning, and Fix Card artifacts are recorded separately in `scores.json` and `data/scoring_notes.md` after assembly.

## Exact fetch and route limitations

- Vintage Optical, Focus On Eyes, Tri-County Eye Center, Vision Care Center, Bard Optical, Illinois Eye Center, and Census public pages were reachable on 2026-07-29.
- The direct Walmart official Vision Center page was bot-blocked. It is recorded as `blocked`; no Walmart official service, access, booking, or review claim is treated as fetched. The Nominatim-matched Walmart Supercenter entity supports location context only.
- The Google Maps sample dated 2026-07-29 supports only a 4.9 subject rating and a Book online action. It does not support a review count, review recency, response comparison, peer normalization, or complete Maps result set.
- The route receipts were collected at 2026-07-30T01:35:21.143554+00:00 using Nominatim/OpenStreetMap and the OSRM public endpoint.
- Successful subject-origin routes are Focus On Eyes 4.07 minutes, Walmart store entity 5.71, Bard Optical East Peoria 14.00, Tri-County Eye Center Washington 20.94, and Vision Care Center Washington 22.41.
- Illinois Eye Center Washington had current official entity evidence but no Nominatim match and no OSRM route.
- OSRM observations are point-to-point practice-origin routes. They are not polygon isochrones, patient-origin choice sets, live-traffic estimates, or time-of-day measurements.

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
- Project Room status: EMPTY / UNROOMED.
- Report visibility: `internal_only_unroomed_draft`.
- Client-ready or prospect-ready claim: prohibited.
- External actions: none.
- Forms submitted: none.
- Appointments selected or booked: none.
- Contacts, sends, commits, pushes, publications, and deployments: none.

## Decision residue

- Hardest decision: selecting the market type while preserving the required peer relevance and refusing to turn point routes or city context into catchment measurements. The chosen classification is exurban, medium confidence, with 20-minute primary and 30-minute extended windows.
- Alternatives rejected: rural/small-town with a 25 to 30-minute primary and optional 45-minute diagnostic, because the available Census density and 16.6-minute commute did not justify the stronger rural assumption; urban/suburban, because the named 20.94 and 22.41-minute peers would be pushed outside its standard 20-minute extended window; reusing straight-line mileage, because exact OSRM receipts supersede it.
- Least-confident assumption: the required named peer set is directionally representative of realistic alternatives. A complete geocoded and deduplicated office census, provider join, patient-origin analysis, or live route study could materially change pressure and tier relevance.
- Prior E033 hypothesis: measure specialty conversion before adding an undifferentiated service. Status remains hypothesis because owned conversion, capacity, and economics are missing.
- Prior E034 hypothesis: run an access diagnostic before changing hours or staffing. Status remains hypothesis because call, slot, cancellation, and no-show evidence is missing.
- Prior E035 hypothesis: compound recall, referral, review, optical, and listing loops before broad awareness spending. Status remains hypothesis because owned funnel and channel evidence is missing.
- Prior E036 hypothesis: test transferability of specialty care and relationships. Status remains hypothesis and is outside this GROW Stage 0 and Stage 1 evidence round.
