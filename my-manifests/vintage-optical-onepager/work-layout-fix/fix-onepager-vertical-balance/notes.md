# Files changed

- Canonical `onepager.html`: balanced the four body sections across the available page height.
- `onepager-preview.html`: local verification copy of the edited canonical page.

# Visual defect addressed

The body now uses explicit proportional rows, and each existing section vertically centers its content within its assigned row. Modest increases to body text, gaps, and padding use the available space without changing the story, wording, scores, headings, citations, links, palette, CTA, footer, or Letter page boundary.

# Verification

- Required validator result: `PASS: canonical build valid; 16 clickable E-IDs, 28 source rows, scores reconciled, pre-existing files preserved`.
- The preview is copied directly from the edited canonical HTML before validation.
- Deterministic Chromium/PDF visual QA remains a separate local-shell Ringer round.

# Remaining gate

Render the preview through the deterministic Chromium/PDF round and confirm there is no large uninterrupted white band between First 30 Days and the CTA while the PDF remains exactly one Letter page.
