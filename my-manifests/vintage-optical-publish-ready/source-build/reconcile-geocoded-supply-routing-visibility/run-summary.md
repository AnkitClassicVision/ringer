# Reconciled supply and routing run summary

## Result

Status: candidate geocoding complete; canonical office census incomplete.

- Source-reported NPPES results: 40
- Materialized provider candidates: 39
- Office location candidates: 24
- Census results: 21 matched and 3 no-match
- Canonical office count: null

## Candidate catchment counts

- 5 minutes: 4 NPPES-derived candidates, 2 competitor candidates, canonical offices null
- 10 minutes: 4 NPPES-derived candidates, 2 competitor candidates, canonical offices null
- 15 minutes: 8 NPPES-derived candidates, 6 competitor candidates, canonical offices null
- 20 minutes: 16 NPPES-derived candidates, 14 competitor candidates, canonical offices null
- 30 minutes: 20 NPPES-derived candidates, 18 competitor candidates, canonical offices null

These are candidate counts, not a complete or deduplicated office census. The current 605 S Main St subject location and legacy 417 W Jefferson St subject address are excluded from competitor counts. Out-of-30-minute and no-match candidates remain explicit.

## Corrected Focus route

The named Focus On Eyes route now uses the direct Google Vintage and Focus listing pins. The frozen OSRM result is 233.4 seconds, 3.89 displayed minutes, 2466.8 meters, and 1.53 displayed miles. It supersedes the old report display of 4.07 routed minutes because that claim did not use the current direct listing-pin pair. The direction did not change materially. Focus remains a nearby direct peer within the 20-minute window. No route includes live traffic or patient-origin choice evidence.

## Visibility and review reconciliation

The direct Google Focus observation is 4.8 with 182 reviews at 829 W Jackson St. On that same dated page, peer cards showed Vintage at 4.9 with 348 reviews, Tri-County at 4.9 with 271 reviews, and Walmart Vision & Glasses at 3.5 with 8 reviews.

Birdeye displayed a Google component of 398 for Vintage, 50 above the direct Google peer card count of 348. Birdeye displayed a Google component of 210 for Focus, 28 above the direct Google listing count of 182. Both sources and counts remain separate because aggregation dates and methods can differ. Ratings were not averaged, counts were not summed, and cross-platform review total remains null.

## Missing evidence

Open gaps: office census incomplete, NPPES source deficit, 3 geocoder no-matches, rank grid not run, full VDU incomplete, provider entity dedupe unresolved, live traffic unavailable.

## Checks and boundaries

The deterministic builder validates the frozen row counts, candidate-to-geocoder alignment, polygon set, route matrix dimensions, and exact named Focus route receipt before writing outputs. The lane was rebuilt twice and all seven generated output checksums were compared for identity. The canonical reconciliation validator was then run against this directory.

No score, report, CRM, external system, or delivery changed. No external action was taken.
