# Competitive-analysis runbook source and explainer upgrade

## Product contract

The runbook must prevent the evidence gaps exposed by the Vintage Optical number explainer from recurring. A completed engagement must produce a source-complete, reproducible public-data packet, one client-facing one-pager, and a separate number-by-number explainer. Missing data stays null and visible until a named fallback is exhausted.

Success means:

1. The source hierarchy distinguishes discovery tools from evidence authorities.
2. Perplexity, Exa, DataForSEO, Google Search/Maps, official APIs, first-party sites, NPPES, Census/ACS/TIGER, CDC PLACES, and routing/isochrone services have explicit jobs and fallback rules.
3. Every promoted fact resolves to a direct source URL or official API response with access time, query parameters, geography, source vintage, and a frozen receipt.
4. Required 5, 10, 15, 20, and 30-minute catchments are measured with saved polygon geometry or remain null with a gap receipt.
5. Provider rows, office locations, retail optical locations, and ophthalmology locations are separately classified, geocoded, and deduplicated. NPPES rows are never treated as office counts without cleaning.
6. Local ranking and reputation fields identify platform, query, coordinates or locality, observation time, aggregation behavior, and limitations. A dated public SERP sample is never called a rank grid.
7. Full VDU is calculated only when every required term is sourced. Any reduced diagnostic is labeled partial and cannot silently replace canonical VDU.
8. `number-explainer.md`, `.html`, and `.pdf` are required engagement artifacts. Every substantive visible number has source, date, units, derivation, formula, direction, interpretation, confidence, limitation, and cross-document consistency status.
9. Technical, visual, numeric-lineage, source-freshness, logic, and Project Room gates pass before human delivery approval.
10. The runbook remains public-data-only by default and does not weaken external-send, PHI, credential, or human-approval boundaries.

## Implementation units

### RB-1: Canonical artifact contract

Add source inventory, missing-evidence register, frozen receipts, one-pager source/render, explainer source/render, score model, and runlog to the required engagement package.

Proof: validator finds every required artifact name and the required explainer formats.

### RB-2: Source hierarchy and fallback ladder

Define direct/official evidence first, structured local-search acquisition next, discovery and cross-check tools after that, and manual verification when automation fails. Name DataForSEO, Google Search/Maps, Exa, and Perplexity. State that AI/search summaries are leads, not final evidence.

Proof: validator finds each tool, the discovery/evidence distinction, direct URL or API resolution, frozen receipts, and explicit failure handling.

### RB-3: Completeness rules for market data

Require fixed isochrones, ACS block-group intersections, provider/office cleaning, review/rank context, source vintage, and visible nulls. Prevent city-to-catchment substitution, provider-to-office substitution, cross-platform review blending, and incomplete VDU promotion.

Proof: validator checks these invariants and the five fixed windows.

### RB-4: Mandatory number explainer

Add a dedicated build step and minimum explainer contents, including the source dictionary, receipt manifest, unknowns, disconfirmers, repeated-number reconciliation, and score recomputation.

Proof: validator finds the explainer step, required formats, and complete numeric-lineage fields.

### RB-5: Ringer and release gates

Define checked Ringer lanes for intake, fetch, transform/dedupe, source audit, catchment, scoring, explainer, rendering, and fresh review. Keep final delivery human-gated through the Project Room.

Proof: validator finds executable checks, independent review, Project Room approval, and no autonomous delivery.

## Decision residue

Hardest decision: how to use broad search tools without letting their summaries become evidence. Decision: Perplexity and Exa discover and cross-check; DataForSEO and Google provide structured or directly observed local-search facts; publication still requires the underlying direct URL or API payload and a frozen receipt.

Alternatives rejected:

- Treating any search answer or aggregator count as self-authenticating.
- Requiring one paid provider with no fallback.
- Filling unavailable fields with estimates or neutral scores without a visible gap record.
- Putting all lineage into the one-page executive report.

Least-confident assumption: the exact availability and cost of DataForSEO will vary by environment. The runbook therefore requires a preflight and a labeled fallback rather than assuming credentials exist.
