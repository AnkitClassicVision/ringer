# Fresh render and boundary release review

Verdict: FAIL

The requested technical render, visual, link, hash, receipt, and boundary checks pass. The packet is not issue-free because `README.md` contains one minor copy defect: its data inventory line repeats `24-record` three times.

Highest true state: NOT_READY_FOR_PROJECT_ROOM_REVIEW

Project Room status: `inventory_review_required`

External use authorized: no

## Issues

Fatal issues: none.

Material issues: none.

Minor issue:

- `MINOR-001`, `README.md`: the current line reads `- data/: 24-record 24-record 24-record source registry, evidence, peer tiers, routes, market inputs, and notes`. Reduce this to one `24-record`, then rerun the release review. This is a packet-copy defect. It does not invalidate the PDF renders or boundary controls, but it prevents an issue-free verdict.

## Command-derived proof

### PDF geometry and text bounds

A PyMuPDF 1.26.7 inspection of `onepager.pdf` returned exactly 1 page at `612.0 x 792.0` points. A span-by-span bounding-box test found 0 text spans outside the page rectangle.

The same inspection of `number-explainer.pdf` returned exactly 11 pages. Every page was `612.0 x 792.0` points, within the required 4 to 15 page range. The scan examined every non-empty text span and found 0 out-of-bounds spans.

No page was empty. Extracted character counts by explainer page were:

`541, 3623, 4052, 4119, 3445, 3259, 3658, 3277, 3831, 4091, 3149`

Page 1 is an intentional cover rather than an anomalously sparse spill page. Although it has 541 extracted characters, a deterministic 72 dpi grayscale render measured 79.911 percent non-white content because of the full-page cover treatment. Pages 2 through 11 contained 3,149 to 4,119 extracted characters each. Page 11 contained 3,149 characters and 454 words.

### Links and print CSS

BeautifulSoup and PyMuPDF link-set comparisons produced exact preservation:

- One-pager: 81 HTML anchors and 81 PDF URI annotations, representing the same 22 unique URLs. Missing URLs: 0. Extra URLs: 0. Empty or invalid anchor targets: 0.
- Explainer: 198 HTML anchors and 198 PDF URI annotations, representing the same 24 unique URLs. Missing URLs: 0. Extra URLs: 0. Empty or invalid anchor targets: 0.

Both HTML files declare Letter sizing in `@page` print CSS. The explainer also contains `thead { display: table-header-group; }` and row break-avoid rules. Extracted PDF text confirmed the structural source-table header `ID / Claim use / Confidence or status / Limitation` on both pages 10 and 11.

### Pagination structure and ending

`Room to Win: 43 / 100` appears on page 4. Its question, inversion formula, result, direction, and explanatory paragraph follow on that same page before the next score section, so the heading is not orphaned.

The final page begins with `Source dictionary: receipts and routes`, continues through `Receipt manifest` and `Final interpretation`, and ends with the internal boundary footer. Its 3,149 extracted characters and 454 words show that it is a purposeful source and receipt ending, not a blank or accidental spill page.

### Receipt paths and internal-path leakage

The explainer lists four package-relative receipt files, and all four resolve inside the packet:

- `data/source_receipts/census-pep-sub-est2024.csv`
- `data/source_receipts/census-pep-sub-est2025.csv`
- `data/source_receipts/osrm-r01-current.json`
- `data/source_receipts/quickfacts-live-audit-extract.json`

Searches of the explainer HTML, Markdown, and extracted PDF text found no visible `/home/` or `/mnt/` path. The local polish validator also returned:

`PASS: polished explainer has no internal path leaks, uses package-relative receipts, protects Room to Win pagination, repeats table headers, and balances the final source/receipt sections`

### Deterministic visual QA

Fresh PyMuPDF rasterization was compared pixel-for-pixel with the shipped QA images:

- `onepager-page-1.png` matched page 1 of the current one-pager PDF at 918 by 1,188 pixels with 100.0 percent exact pixels and mean absolute error 0.0.
- All 11 `number-explainer-page-N.png` files matched the corresponding current PDF pages at 765 by 990 pixels with 100.0 percent exact pixels and mean absolute error 0.0.
- The packet contains exactly page images 1 through 11, with no missing or extra numbered page image in the final snapshot.
- A deterministic reconstruction of the two-column contact sheet from the current PDF matched `number-explainer-qa-contact-sheet.png` at 1,080 by 4,200 pixels with 100.0 percent exact pixels and mean absolute error 0.0. The unused twelfth grid cell is uniformly RGB `225,225,225`.
- `onepager-qa.png` and `onepager-page-1.png` have the same SHA-256 hash.

The runlog records `Publish-candidate visual QA: PASS.` The independent rendered-explainer validator returned:

`PASS: explainer renders as 11 Letter pages with 24 links, 37056 extracted characters, and no out-of-bounds text`

### Hashes

`sha256sum` returned:

- `onepager.pdf`: `b6e18c05cf73987772436ba80c4a9eeb0a3643058f3ddf8b20d41ad6ec789b05`
- `number-explainer.pdf`: `3c7b1b92c5089654f39c035c3e228bf4349b9c5e34b14c7a7b12555c0abb5158`

Both values exactly match the final hashes recorded in `runlog.md`. Every PDF hash occurrence parsed from the runlog maps to one of these current artifacts.

### Project Room and external boundary

The Project Room JSON was read directly without an MCP call or state-changing room command. It reports:

- `status`: `inventory_review_required`
- `last_reviewed_at`: `null`
- `stale_reasons`: empty
- 4 inventoried sources, all marked `pending_human_review`

The explainer repeats `Project Room review required` on every page. Its cover and ending both say `External actions: none`. The one-pager remains labeled internal-only and not for external use. The runlog records `External actions: none`, and no room promotion or external authorization is present.

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
- `packet_copy_integrity`: FAIL

The issue-free phrase and `READY_FOR_PROJECT_ROOM_REVIEW` state are intentionally withheld because one minor issue remains.
