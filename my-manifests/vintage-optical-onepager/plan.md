# Vintage Optical canonical one-pager plan

## Product contract

Create the GROW-lane competitive-analysis one-pager for Vintage Optical in the canonical Optometry Competition Analyzer report folder. Use only public evidence. The artifact must answer: how hard is it for Vintage to win the next patient dollar, and where can it still win despite competition?

## Inputs

- Practice: Vintage Optical
- Website: https://www.vintageopt.com/
- Location: 605 S Main St, Morton, IL 61550
- Owner intent: grow
- Existing client check: not an existing MyBCAT client
- Data mode: public_only
- Source research: `/mnt/d_drive/repos/vintage-optical-competitive-analysis/RESEARCH/Paul_Velting_Vintage_Optical/`
- Canonical runbook: `/mnt/d_drive/repos/optometry-competition-analyzer-rubric/RUNBOOK_COMPETITIVE_ANALYSIS.md`

## Units and proof

- U1 Intake: create `intake.md`. Proof: all five GROW intake fields are present and no field is guessed.
- U2 Evidence and scores: create source-labeled public evidence plus schema-shaped `scores.json`. Proof: validator parses JSON, checks score direction, verifies Room to Win = 100 - CPI, and rejects unsupported URLs or dollar forecasts.
- U3 One-page build: create `onepager.html` from the approved template pattern. Proof: required sections and source/confidence markers are present.
- U4 Render: create exactly one Letter-size `onepager.pdf`. Proof: PDF page count = 1, text extraction contains The Read, and visual render has no clipping.
- U5 Run record: create `runlog.md` with commands, QA outcomes, source limits, and the human delivery gate. Proof: runlog records every gate and states no external delivery occurred.

## Acceptance criteria

- Client-facing scores are high-good or carry an explicit direction cue.
- Every claim has source and confidence.
- Tier 3 is absent from the client artifact.
- Public-only confidence ceiling is respected.
- No PHI, login-only data, private financial data, invented review counts, or public-data revenue forecast.
- No email, HubSpot write, external send, commit, push, merge, or deploy.

## Non-goals

- No valuation or buy/no-buy conclusion.
- No owner-dependence conclusion.
- No broad website audit beyond evidence relevant to the score and fix list.
- No unsupported exact drive-time or market-share claim.

## Decision residue

- Hardest decision: whether the public-only evidence is sufficient for numeric client-safe scoring. Use conservative qualitative-to-numeric bands and a C/D confidence ceiling rather than fake peer percentiles.
- Rejected alternative: reuse the eight-page report without the canonical score stack. It does not satisfy the requested one-page process.
- Least-confident assumption: straight-line competitor bands and limited ratings can stand in only as directional context until drive-time and GBP exports are available.
