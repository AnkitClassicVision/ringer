# Logic and Claim-Boundary Review

## Verdict

PASS. The rendered package follows the rubric, preserves the required claim boundaries, and has no blocking logic finding. The build-source validator and rendered-report validator both passed. Visual QA is also PASS.

## Strongest claim

The strongest substantive claims are the five modeled catchment rows and the two observed local growth series. Each is bounded by geography, source vintage, method, and limitations. Catchment values are described as area-weighted modeled estimates rather than patient counts. Village population and district enrollment are described as observed changes rather than forecasts, patient growth, or realized demand.

The score-direction claim is stronger still as a deterministic check: Competitive Pressure is 57, and Room to Win is exactly 43.

## Weakest claim

The least complete directional claims are the 65 bands for Patient Choice Pressure and review-based trust or reputation. Point routes establish proximity, not patient choice. The review evidence is one dated same-page Google sample, not a complete peer export and not an analysis of review recency, themes, responses, outcomes, or clinical quality.

These claims remain acceptable for this internal confidence C package because the limitations are explicit, no severe or top band is claimed, and the missing evidence is named. A complete choice model or peer-review export could change the scores.

## Score-direction check

PASS.

`Room to Win = 100 - Competitive Pressure Index`

Competitive Pressure remains 57. Room to Win is not independently banded and recomputes as `100 - 57 = 43`.

The changed scores follow named rubric components:

- Market Demand-Supply changes from 57 to 61 because observed population and enrollment evidence moves Growth / Future Demand from 50 to 65, while complete fixed-window demographics moves Market Data Confidence from 35 to 50. Supply Balance stays 50 because canonical supply and full VDU are unresolved.

- Practice Competitiveness changes from 58 to 61 because only Review Trust vs Peers moves from 50 to 65 on the bounded direct Google comparison.

- Digital Presence changes from 57 to 60 because only Reputation moves from 50 to 65. Findability stays 50 because no rank grid ran.

- Dry eye and myopia each change from 52 to 53 because Evidence Confidence moves from 35 to 50. Their demand, capacity, referral, outcome, conversion, and economics boundaries do not move.

The unchanged scores remain justified. Competitive Pressure stays 57 because route correction does not change proximity, candidate supply cannot establish saturation, and the bounded review evidence does not cross another strength band. Client Opportunity stays 54 because the revised full-precision value is 54.45 and the other fixability inputs remain unproven. Specialty contact lenses stays 51 because the new evidence is not lane-specific.

## Null boundaries

PASS. These required fields remain null:

- `canonical_full_vdu`
- `canonical_office_count`
- `rank_grid`
- `complete_provider_entity_dedupe`
- `cross_platform_review_total`

Unknown is never treated as zero, average, normal, no demand, no competition, or no problem. Candidate counts do not become office counts, and unresolved denominators remain not calculable.

## Contradictions

Four contradictions are preserved and resolved without overclaiming:

1. Birdeye Google components of 398 and 210 differ from direct Google counts of 348 and 182. The sources stay separate, the differences of 50 and 28 are explicit, and no cross-platform total is created.

2. The direct Google observation uses the current address while Birdeye shows a legacy address. The direct listing pin is used for the current route, and the legacy citation conflict is retained without claiming that the legacy location is operating.

3. NPPES reported 40 results but only 39 candidate records materialized. Both counts remain visible, and canonical provider and office totals stay null.

4. The prior Focus route was 4.07 minutes, while the corrected direct-pin route is 3.89 minutes. The corrected route supersedes the stale value without changing the nearby-peer score state.

No unresolved contradiction blocks the internal package.

## Three-Fix-Card check

PASS. Exactly three Fix Cards appear in the rendered one-pager: Visibility baseline, Reputation source control, and Booking completion. Each appears once, and no fourth card exists.

## Remaining risk

The largest remaining risk is model sensitivity to evidence that has not been collected. A complete active-office census and six-term VDU could move supply and pressure in either direction. A rank grid and complete peer-review export could change visibility and reputation scores. Patient-origin and traffic-aware evidence could change practical peer relevance. Authorized operating evidence could change opportunity and specialty-lane scores.

## Internal status and human requirement

This remains an internal-only, public-data, confidence C rendered candidate. It is not authorized for delivery, upload, publication, outreach, CRM use, or any other external action.

Human Project Room approval of the exact rendered package is required before external use.
