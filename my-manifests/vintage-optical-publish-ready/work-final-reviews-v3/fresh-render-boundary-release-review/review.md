# Fresh render and boundary release review

Verdict: PASS

No fatal, material, or minor issues

Highest true state: READY_FOR_PROJECT_ROOM_REVIEW

Project Room status: `inventory_review_required`

External use authorized: no

This is a technical and boundary readiness result. It does not promote the Project Room, authorize external use, or replace the required human source-inventory review.

## Command-derived proof

### PDF geometry, density, and text bounds

PyMuPDF 1.26.7 opened the live packet PDFs directly.

- `onepager.pdf` contains exactly 1 page. Its page rectangle is exactly `612.000 x 792.000` points, the required Letter geometry. The scan examined 185 text spans and found 0 spans outside the page rectangle.
- `number-explainer.pdf` contains exactly 11 pages, within the required 4 to 15 page range. Every page rectangle is exactly `612.000 x 792.000` points. The scan examined 1,468 text spans and found 0 spans outside the page rectangles.
- Explainer extracted-character counts by page are `541, 3628, 4052, 4119, 3445, 3259, 3698, 3277, 3848, 4099, 3421`. No page is empty.
- Page 1 is the intentional dark cover. Its deterministic raster has 79.69 percent non-white ink. Pages 2 through 11 have 3,259 to 4,119 extracted characters and 12.17 to 15.21 percent non-white ink. Page 11 has 3,421 characters and 491 words. No blank or anomalously sparse spill page exists.

`pdfinfo` independently reported `Pages: 1` and `Page size: 612 x 792 pts (letter)` for the one-pager, and `Pages: 11` and the same Letter geometry for the explainer.

### HTML links and print CSS

BeautifulSoup parsed the HTML anchor targets, and PyMuPDF read the URI annotations from the rendered PDFs.

- One-pager: 81 valid HTTP or HTTPS anchors and 81 PDF URI annotations, with the same 22 unique URLs. Missing occurrences: 0. Extra occurrences: 0. Invalid or empty targets: 0.
- Explainer: 206 valid HTTP or HTTPS anchors and 206 PDF URI annotations, with the same 25 unique URLs. Missing occurrences: 0. Extra occurrences: 0. Invalid or empty targets: 0.

No network request was made. Link validity here means valid HTTP or HTTPS target syntax and exact preservation from HTML into the PDF.

Both HTML files declare Letter print geometry with `@page`. The one-pager also declares exact print-color adjustment. The explainer contains `thead { display: table-header-group; }`, `tfoot { display: table-footer-group; }`, row break-avoid rules, and 13 semantic tables, all 13 with a `thead`.

Extracted page text confirms that continued structural tables repeat their headers. Page 6 restates `Component / Band / Weight / Contribution / Why assigned / Sources / Unknown` after the dry-eye table crosses the page boundary. Page 9 restates `Number or identifier / What it means / What it does not mean`. The source dictionary structure appears with `ID / Claim use / Confidence or status / Limitation` on pages 10 and 11.

### Pagination structure and final ending

The `Room to Win: 43 / 100` score section begins at the top of page 4. Its question, inversion formula, result, direction, explanation, and calculation table follow on the same page. The HTML section also carries the `avoid-break` class. The heading is not orphaned.

Page 11 begins with `Source dictionary: receipts and routes`, continues through the source table and `Receipt manifest`, then ends with `Final interpretation` and the internal boundary footer. Its 3,421 extracted characters, 491 words, and 12.17 percent ink coverage confirm a purposeful source and receipt ending rather than an accidental spill page.

### Package-relative receipts and internal-path check

The explainer visibly lists five package-relative audit paths:

- `data/receipt_summary.json`
- `data/source_receipts/census-pep-sub-est2025.csv`
- `data/source_receipts/census-pep-sub-est2024.csv`
- `data/source_receipts/quickfacts-live-audit-extract.json`
- `data/source_receipts/osrm-r01-current.json`

All five resolve to regular files inside the report packet. Searches of the explainer HTML, Markdown, visible HTML text, and extracted PDF text found 0 visible `/home/` paths and 0 visible `/mnt/` paths.

The independent explainer polish validator also returned:

`PASS: polished explainer has no internal path leaks, uses package-relative receipts, protects Room to Win pagination, repeats table headers, and balances the final source/receipt sections`

### Deterministic visual QA

Every shipped QA image was compared with a fresh PyMuPDF raster of the current PDF at the packet's recorded scale.

- The one-pager page image matched the current PDF page exactly at `918 x 1188` pixels. Exact pages: 1 of 1. Mean absolute error: 0.0.
- All explainer page images matched the corresponding current PDF pages exactly at `765 x 990` pixels. Exact pages: 11 of 11. Maximum mean absolute error: 0.0.
- The explainer page-image set is exactly pages 1 through 11, with no missing or extra numbered page.
- A fresh in-memory reconstruction of the two-column contact sheet matched `number-explainer-qa-contact-sheet.png` exactly at `1080 x 4200` pixels. Difference bounding box: none. Mean absolute error: 0.0. The unused twelfth cell is uniformly RGB `225, 225, 225`.
- `onepager-qa.png` and `onepager-page-1.png` have the same SHA-256 hash.

The runlog records both `Publish-candidate visual QA: PASS` and `Post-S18 visual QA: PASS`. The independent rendered-explainer validator returned:

`PASS: explainer renders as 11 Letter pages with 25 links, 37398 extracted characters, and no out-of-bounds text`

### Runlog hashes

`sha256sum` on the live PDFs returned:

- `onepager.pdf`: `b6e18c05cf73987772436ba80c4a9eeb0a3643058f3ddf8b20d41ad6ec789b05`
- `number-explainer.pdf`: `30bdb7f0aa6196f1081fe5e1b47f89a865c69b97fdb56114151070f98cbe431e`

The runlog contains 6 PDF-hash occurrences: 4 one-pager occurrences and 2 explainer occurrences. Every occurrence equals the current artifact hash. Unmatched runlog PDF hashes: 0.

### Project Room and external boundary

The Project Room state file was read directly without MCP, Apps, or a state-changing room command. It reports:

- `status`: `inventory_review_required`
- `last_reviewed_at`: `null`
- `stale_reasons`: empty
- inventoried sources: 4
- sources marked `pending_human_review`: 4

Boundary labels were checked across `scores.json`, `data/competitor_set.json`, `intake.md`, evidence and research notes, the prior internal review note, `README.md`, `runlog.md`, both HTML files, both rendered PDFs, and the Project Room state. They consistently identify the packet as internal-only or unroomed, require Project Room inventory review before outward use, and do not authorize an external action. The room-label validator returned:

`PASS: competitor data and historical notes distinguish initial state from current inventory_review_required with no stale external-readiness labels`

The runlog, explainer cover, explainer ending, evidence file, and research notes record external actions as none. No room promotion or external-use authorization is present.

## Check results

- `onepager_one_letter`: PASS
- `explainer_letter_pages`: PASS
- `links_valid`: PASS
- `visual_qa`: PASS
- `no_internal_paths`: PASS
- `no_clipping`: PASS
- `room_boundary`: PASS
- `hashes_match`: PASS
- `external_actions_none`: PASS

The packet is issue-free for the requested technical and boundary review. It is ready for human Project Room source-inventory review and remains blocked from external use.
