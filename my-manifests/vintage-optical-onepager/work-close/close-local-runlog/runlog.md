# Build Runlog

## Confirmed intake

- practice_name: Vintage Optical
- website_url: https://www.vintageopt.com/
- locations: 605 S Main St, Morton, IL 61550
- owner_intent: grow
- data_mode: public_only
- existing_client_check: not an existing MyBCAT client

## Prior Ringer evidence

- Ringer research run ID: `vintage-optical-onepager-20260730T002531Z-p576497`
- Ringer research result: PASS
- Chromium probe run ID: `vintage-optical-onepager-20260730T002846Z-p601257`
- Chromium probe result: PASS

## Files created

- `intake.md`
- `data/evidence.md`
- `data/sources.json`
- `scores.json`
- `onepager.html`
- `runlog.md`

## Builder verification

- Command: `python3 /home/ankit114/repos/ringer/my-manifests/vintage-optical-onepager/checks/validate_build.py --dest /mnt/d_drive/repos/optometry-competition-analyzer-rubric/reports/vintage-optical-morton/2026-07-29 --research-scores /home/ankit114/repos/ringer/my-manifests/vintage-optical-onepager/work-research/score-and-brief/scores_recommendation.json --ledger /mnt/d_drive/repos/vintage-optical-competitive-analysis/RESEARCH/Paul_Velting_Vintage_Optical/04_evidence_ledger.csv --notes notes.md`
- Result: PASS - canonical build valid; 16 clickable E-IDs, 28 source rows, scores reconciled, pre-existing files preserved.

## Gates

- Render status: PASS via final deterministic Ringer local-shell render
- Human delivery gate: pending Ankit review
- No external delivery occurred.

## Decision residue

- Hardest decision: whether numeric client-safe scores were defensible without peer percentiles. The plan chose conservative qualitative rubric bands, visible direction cues, strict separation of verified facts from inference, and Confidence C.
- Alternatives rejected: reusing the long report without the canonical score stack; calling visible specialty services proven white space; treating sampled search placement as a stable local ranking; converting demographic or operating hypotheses into dollar forecasts; and recommending longer hours, new services, or broad paid awareness before measurement.
- Least-confident assumption: the reviewed public competitor set and straight-line bands are sufficient to place pressure at the lower edge of High. Drive-time, provider-deduplication, and reputation work could move the score materially.

<!-- RINGER-RENDER-RECEIPT:START -->
## Deterministic render receipt

- Render status: PASS
- Renderer: Google Chrome 150 headless, local-shell via Ringer
- PDF: `onepager.pdf`
- Visual QA image: `onepager-qa.png` at 150 DPI
- Extracted text: `data/onepager-text.txt`
- External delivery: none
<!-- RINGER-RENDER-RECEIPT:END -->

<!-- FINAL-QA-RECEIPT:START -->
## Final QA receipt

- Canonical build run: `vintage-optical-onepager-20260730T003218Z-p627059` - PASS
- Layout-correction run: `vintage-optical-onepager-20260730T003824Z-p670681` - PASS
- Final render run: `vintage-optical-onepager-20260730T004028Z-p686488` - PASS
- Mechanical build and PDF validators: PASS
- Final PDF: exactly one US Letter page, 70,894 bytes, 15 unique HTTP links
- Final PDF SHA-256: `d60c5c5f338f78f44c1b64870af3210ceccad7ffa211c8257ba8bd63fae59c78`
- Visual QA: PASS after one Ringer layout-correction round
- Fresh report-only review run: `vintage-optical-onepager-20260730T004139Z-p695483` - READY, no fatal or material issues
- Highest true state: local artifacts tested and ready for Ankit's human delivery gate
- Human delivery gate: pending
- External delivery: none
<!-- FINAL-QA-RECEIPT:END -->
