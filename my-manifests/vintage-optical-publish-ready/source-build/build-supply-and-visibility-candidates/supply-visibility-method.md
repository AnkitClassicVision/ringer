# Supply and visibility candidate method

## Supply candidates

NPPES records are not office counts. This packet uses the 39 materialized public provider rows and records the separate one-row Pekin source mismatch. It does not invent a fortieth provider. Provider names, taxonomies, city-query result counts, mailing addresses, and registry rows are not treated as office counts.

Each provider row remains a provider candidate. Individual and organization enumeration records remain distinct. The `provider_public_id` is a SHA-256 row-stability key built only from normalized public fields. It is not an identifier recovered from a restricted field.

Practice-location addresses are normalized for conservative matching. Punctuation and case are removed for matching, common street suffixes are standardized, and suite or unit details remain part of the match. Only exact normalized address, city, state, and ZIP matches form one office candidate. Original address text remains available.

The office candidates have geocoding pending. Entity resolution must follow geocoding before any canonical office count can be considered. Provider and office counts remain separate. A billing, mailing, provider, or registry row alone does not prove an active office.

## Visibility and reputation

A dated SERP sample is not a rank grid. The direct Google Maps observation records the facts visible on 2026-07-30, including a 4.9 rating, current 605 S Main St citation, booking-link presence, pin coordinates, and owner-post date. Its direct Google review count remains null because the limited public view did not show one.

Birdeye provides third-party aggregator observations. Vintage Optical displayed 4.9 and 413 total reviews, with a displayed composition of Google 398, Facebook 15, and Birdeye 0. Focus On Eyes displayed 4.8 and 217 total reviews, with Google 210, Facebook 6, Yahoo! Local 1, and Birdeye 0. These are platform-specific review facts as displayed by Birdeye. They are not direct current counts from those component platforms.

Ratings are not averaged and counts are not summed across sources or platforms. Cross-platform totals remain null. The two entities are not compared as if platform recency and collection methods were identical.

## Citation consistency

The current Google citation is 605 S Main St, Morton, IL 61550. Birdeye preserves a legacy address of 417 W Jefferson St, Morton, IL 61550. This legacy address conflict is unresolved. The packet does not decide whether the old address is still operational without direct evidence.
