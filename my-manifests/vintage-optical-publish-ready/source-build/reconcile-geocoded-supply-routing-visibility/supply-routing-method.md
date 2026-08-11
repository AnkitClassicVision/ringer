# Supply and routing reconciliation method

## Scope

This lane reconciles frozen public supply candidates, Census geocoder results, corrected drive-time polygons, OSRM routes, and source-specific visibility observations. It does not rescore or edit a report.

## Supply candidates

NPPES records are not office counts. The source reported 40 results, 39 provider candidates materialized, and those records formed 24 address-level location candidates. The Census batch returned 21 matched rows and 3 no-match rows. No-match latitude and longitude remain null.

Each matched point is tested against the corrected 5, 10, 15, 20, and 30-minute polygons. Counts remain candidate location counts. The canonical office count remains null because provider-registry locations do not prove distinct, active offices.

The current subject address at 605 S Main St is excluded from competitor counts. The legacy subject address at 417 W Jefferson St is also excluded because the frozen direct Google and Birdeye observations show a current-versus-legacy citation conflict. No other candidate is merged, deduplicated, or labeled an active office without direct entity evidence. Matched points outside 30 minutes and all no-match candidates remain visible in limitation collections.

## Routing

The candidate routing table uses the direct Google Vintage listing pin as its origin and Census address-geocoder points as its destinations. These routes describe candidate locations. They are not patient-origin choice evidence.

The named Focus On Eyes route uses direct Google listing pins for both endpoints. Its frozen OSRM receipt replaces the prior display of 4.07 routed minutes with 3.89 routed minutes and 1.53 miles. The lineage changed, but the competitive direction did not change materially. Focus remains a nearby direct peer within the 20-minute window. OSRM has no live traffic.

## Visibility and reviews

The original direct Vintage listing observation, the unavailable DataForSEO preflight, the rank-grid not-run state, and the Birdeye observations remain separate. A dated SERP sample is not a rank grid. The Focus page and its peer cards are one dated direct Google observation, not a complete peer export.

Birdeye displayed Google components of 398 for Vintage and 210 for Focus. The direct Google page displayed 348 for the Vintage peer card and 182 for Focus. Aggregation date and method can differ. Aggregator composition is not direct Google truth. Ratings are not averaged, counts are not summed, and cross-platform review total remains null.
