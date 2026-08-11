# Source and logic audit

Verdict: PASS

This is an internal, unroomed audit of the Vintage Optical 2026-07-30 report packet. I tried to disprove the report against its 23-record source registry, current public pages, stored route receipts, market inputs, peer set, score stack, HTML, extracted PDF text, and the repository rules. I found no fatal or material inconsistency. Three source checks carry limitations: QuickFacts has advanced to a newer population vintage, the Census ACS registry URL is dataset documentation rather than a frozen value query, and the OSRM route could not be fetched live through the audit layer. None changes the internal report's stated logic or vintaged values.

## Disconfirming checks

- **Could the city figures be masquerading as catchment measurements?** No. All demographic, VDU, office, provider, and ratio fields for the 5, 10, 15, 20, and 30-minute windows remain null. The PDF explicitly says the city values do not describe the 20-minute catchment.
- **Could the named routes be presented as complete local supply?** No. Every window's completeness flag is false, the competitor set denies a complete office census and provider join, and the page calls the alternatives a bounded peer set.
- **Could missing evidence be converted into favorable proof?** No. Every component labeled `neutral_unknown_no_directional_claim` is exactly 50. The report calls those inputs unmeasured and never describes 50 as average or benchmark performance.
- **Could a visible high-bad score invert the meaning?** No. The extracted PDF contains nine “higher = better” cues. The raw Competitive Pressure Index remains internal; visible Room to Win is `100 - 57 = 43`.
- **Could public service pages be treated as operating or clinical proof?** No. The page limits them to identity, stated offers, hours, and access paths, then separately says starts, completed visits, capacity, throughput, outcomes, patient draw, and economics are unknown.
- **Could specialty scores be forecasts or white-space declarations?** No. All three lanes are labeled `RESEARCH NEXT`, and the competing dry-eye and myopia pages are used to constrain rather than inflate the gap.
- **Could the Fix Cards hide forecast assumptions?** No. They define ratios and counts to populate after 30 days and expressly reject assumed patient, revenue, leakage, and dollar effects.
- **Could visible citations point somewhere other than the registry?** No. The registry contains 23 unique IDs. Scores, market inputs, the competitor set, and all 20 unique visible IDs resolve. All 75 HTML citation occurrences match the URL registered for the displayed ID.

The independently recomputed directional stack also reconciles: Market Demand-Supply `56.75 → 57`, internal Competitive Pressure `56.75 → 57`, Room to Win `100 - 57 = 43`, Practice Competitiveness `57.5 → 58`, Client Opportunity `53.65 → 54`, Digital Presence `56.75 → 57`, and specialty lanes `51.5 → 52`, `51.5 → 52`, and `50.75 → 51`.

## City context and catchment

The visible `17,557`, `25.9%`, and `23.1%` are identified as Morton village city context. They are not inserted into a drive-time polygon, used as fixed-window population, or divided by the bounded peer count. `market_inputs.json` keeps every fixed-window population, household, age, VDU, supply, provider, and saturation field null.

S14 has a freshness nuance. The live QuickFacts page now defaults to a July 1, 2025 estimate of `17,565`; it still shows `25.9%` under 18, `23.1%` age 65+, `$94,402` median household income, `1,336.4` people per square mile, and a `16.6`-minute commute. The report clearly labels `17,557` as the 2024 city estimate, and an indexed official Census V2024 result confirms it. This is a vintage difference, not a contradiction.

S15 confirms the 2024 ACS 5-year dataset and its place/block-group coverage. It also supports the report's negative claim: no block-group-to-isochrone intersection was completed. The hidden ACS population `16,595` and median age `41.4` were corroborated, but the registry URL is documentation rather than a frozen parameterized value response. Those hidden values are not substituted into a fixed window or displayed as report facts.

## Route limitations

R01's saved raw OSRM response contains `code: Ok`, `244.3` seconds, and `2504.2` meters. Those values independently round to `4.07` minutes and `1.56` miles. The live route URL returned an audit-tool internal error, so this audit does not claim a live OSRM verification.

The saved receipt remains adequate for the internal point-route observation because it preserves provider output, collection time, origin/destination coordinates, duration, and distance. The report also carries the necessary limitations: no live traffic, no time-of-day model, no polygon isochrone, no patient-origin weighting, and no complete choice set. R06 remains route-unknown rather than being estimated.

## Unknown handling

Twenty-two base or specialty components use `neutral_unknown_no_directional_claim`; all 22 equal 50. The report does not describe those 50s as measured average performance. Its visible copy says complete supply, peer reputation, access conversion, capacity, collection, and economics remain unmeasured.

Verified public signals can still support a limited 65 band without converting unrelated unknowns into proof. Examples are city age/income context, a public booking path, service-page breadth, and named route observations. Each such band is labeled directional or proxy-only and carries the missing evidence that could change it. The report never converts null catchment, provider, review, conversion, capacity, or economics fields to zero.

## Score direction

Every score displayed in the PDF is high-good: Client Opportunity 54, Market Demand-Supply 57, Room to Win 43, Practice Competitiveness 58, Digital Presence 57, and specialty scores 52, 52, and 51. Each score block has a “higher = better” cue.

The high-bad Competitive Pressure Index of 57 appears only in internal `scores.json` metadata. It is not present in extracted PDF text. The visible substitution is the canonical high-good inversion, Room to Win `43`.

## Peer tiers

The peer set is bounded to three Tier 1 direct peers and three Tier 2 substitutes. Focus On Eyes is a close Morton independent peer. Tri-County and Vision Care Center are extended-context Tier 1 peers because their official pages show broad or specialty overlap and their saved routes are 20.94 and 22.41 minutes. Bard and Illinois Eye fit the repository's Tier 2 substitute definitions. Walmart remains a low-confidence Tier 2 location-context record because its official page was blocked and its route ends at the matched Supercenter entity.

No Tier 3 comparator is shown. No peer is called a complete supply count. The page discloses that a full office and provider census could move Room to Win in either direction. The least-confident tier assumption is therefore bounded and visible rather than smuggled in as market completeness.

## Fix Card math

All three cards are measurement instructions:

1. F-001 calculates inquiry-to-book, book-to-start, and completion rates after lane counts are collected.
2. F-002 calculates an observed access-gap count and rate, with any later sensitivity tied to a measured gap and tested recovery rate.
3. F-003 calculates listing accuracy, review velocity, referral booking, and recall booking from tracked or eligible denominators.

The cards state that patient, revenue, leakage, and dollar forecasts are unsupported. Missing counts remain null. If these formulas are later automated, zero denominators should also remain null or undefined rather than being coerced to zero.

## Source freshness

S01, S07, S08, S10, S11, and S12 were directly re-fetched from their current official public pages and still support the registered identity, address, offer, access, and overlap claims. Their limitations remain important: first-party pages are evidence of published claims, not independent operating or clinical proof.

S14 is current but mutable and now defaults to Vintage 2025. The retained Vintage 2024 population is properly labeled, but a frozen official receipt would make the lineage stronger. S15 is current official dataset documentation, not a Morton value response. R01 was not live-accessible in this audit, so only the saved raw receipt was accepted. These are `PASS_WITH_LIMITATION` source checks, not live-verification claims.

## Publication boundary

The packet remains **INTERNAL-ONLY, UNROOMED, and NOT FOR EXTERNAL USE**. This PASS means the current internal report has no fatal or material source/logic inconsistency under its stated public-only and directional boundaries. It does not promote the room, authorize delivery, or make the packet client-ready.

Before any external use, the human source-authority and Project Room gates still apply. The exact Census value responses should be frozen, mutable city facts and point routes should be refreshed, and any denominator-zero behavior in implemented Fix Card calculations should be explicit. No external action was taken by this audit.
