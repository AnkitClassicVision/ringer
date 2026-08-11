# Files changed

- Repository: `intake.md`, `data/evidence.md`, `data/sources.json`, `scores.json`, `onepager.html`, `runlog.md`
- Scratch: `notes.md`, `onepager-preview.html`, `scores-preview.json`, `runlog-preview.md`

# Verification

- Canonical validator: PASS - 16 clickable E-IDs, 28 source rows, scores reconciled, and pre-existing files preserved.
- Scores: byte-for-byte copy from the accepted Ringer research artifact.
- Page contract: Letter size declared at 8.5 by 11 inches with a fixed-height, overflow-contained layout.
- Prior Chromium probe: PASS (`vintage-optical-onepager-20260730T002846Z-p601257`).

# Assumptions

- The accepted public research packet and evidence ledger are the source of truth.
- Tier 2 substitutes may be omitted from the client page when space is constrained.
- The deterministic local-shell render remains a separate gated step.

# Remaining gate

- Deterministic Ringer local-shell PDF render, then Ankit human review before delivery.
