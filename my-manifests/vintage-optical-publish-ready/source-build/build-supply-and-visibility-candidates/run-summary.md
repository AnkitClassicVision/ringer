# Run summary

## Result

- Materialized provider candidates: 39
- Source-reported query results: 40
- Registered source gap: Pekin Optometrist reported 11, materialized 10, deficit 1, unresolved
- Exact normalized office candidates: 24
- Canonical office count: null
- Office candidate state: Census geocoding pending

## Visibility evidence

- DataForSEO: unavailable_missing_credentials. No request was sent, cost was 0, and no rank grid ran.
- Direct Google Maps: Vintage Optical, Optometrist, 605 S Main St, Morton, IL 61550, https://vintageopt.com/, booking link visible, rating 4.9, review count null, pin 40.6049094/-89.467024, owner-post date 2026-04-09.
- Birdeye Vintage Optical: aggregator rating 4.9 and total 413, with displayed composition Google 398, Facebook 15, and Birdeye 0.
- Birdeye Focus On Eyes: aggregator rating 4.8 and total 217, with displayed composition Google 210, Facebook 6, Yahoo! Local 1, and Birdeye 0.
- Citation consistency: conflict detected between the current Google address at 605 S Main St and the Birdeye legacy address at 417 W Jefferson St. No operational conclusion was made about the legacy address.

The Birdeye totals are not promoted as direct current Google counts. Ratings were not averaged, review counts were not summed, and the cross-platform review total remains null.

## Checks and boundaries

- All 39 materialized provider rows were parsed.
- The one unresolved source deficit remains separate from provider records.
- Office candidates use exact normalized practice-location matching and retain suite details.
- The Census batch has one five-column row per office candidate and no header, provider name, or restricted identifier.
- Input receipts include local SHA-256 checksums and source limitations.
- Two consecutive builder runs produced identical checksums for every generated JSON, CSV, and Markdown output.
- The required repository validator result was PASS.

No canonical office count, score, report, CRM, external system, or delivery changed.
