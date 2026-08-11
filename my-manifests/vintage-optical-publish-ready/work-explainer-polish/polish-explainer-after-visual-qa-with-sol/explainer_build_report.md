# Vintage Optical number-explainer build report

## Boundary and result

- Deliverable state: internal local artifact
- Project Room: `inventory_review_required`
- Visible boundary: Internal publish-candidate; Project Room review required
- Data mode: public-only
- Confidence: C
- Files written: `number-explainer.md`, `number-explainer.html`, `explainer_build_report.md`
- Reports and source files modified: none
- External actions: none
- Contacts, forms, submissions, sends, uploads, publications, commits, pushes, merges, and deployments: none

## Requirements yardstick

| Unit | Requirement | Proof target | Result |
|---|---|---|---|
| U1 | Explain every substantive number family and distinguish structural values | Number map, public-fact lineage, route math, structural-number dictionary | Covered |
| U2 | Recompute all six headline measures and three specialty lanes | Component, band, weight, contribution, full-precision total, rounding, result | Covered and independently checked |
| U3 | Preserve source and logic boundaries | Neutral-unknown rule, city-versus-catchment boundary, bounded-route boundary, disconfirmers | Covered |
| U4 | Produce equivalent Markdown and self-contained print HTML | Both formats derive from the same Markdown facts; HTML has source links and number hooks | Covered |
| U5 | Verify scope, structure, print length, and prohibited language | Exact polish validator plus Letter render | Passed exact validator; 12-page in-memory Letter render inspected |

## Visual-polish correction pass

This bounded pass addresses the three findings from the first 11-page Chrome render. It does not change any report result, source record, formula, limitation, or the Project Room boundary.

1. **Finding:** The Room to Win heading landed at the bottom of page 3 while its formula moved to page 4.
   **Fix:** The complete Room to Win block now sits in an HTML section with `data-section="room-to-win"` and the `avoid-break` class. Print CSS applies `break-inside: avoid-page` and `page-break-inside: avoid` so the heading, question, formula `100 - 57 = 43`, result direction, interpretation, and mover explanation stay together.
2. **Finding:** The Structural numbers table continued on page 9 without a repeated column header.
   **Fix:** Every data table retains direct semantic `thead` and `tbody` elements. Print CSS explicitly sets `thead { display: table-header-group; }`, allowing the Structural numbers header and every other continued-table header to repeat.
3. **Finding:** Page 11 was sparse and exposed internal workspace paths.
   **Fix:** The ending is now divided into `Source dictionary: public sources` for S01-S17 and `Source dictionary: receipts and routes` for N00 and R01-R06. The second section includes a package-relative manifest for the five receipt files shipped in the report packet, followed by `Final interpretation`, which reconciles every headline and unchanged specialty result while preserving Project Room review required.

External actions: none.

## Inputs read

### Current staged report authority

- Current scores JSON
- Current market inputs JSON
- Current sources JSON
- Current evidence, scoring notes, and research notes
- Current one-page HTML and its build report

The three staged JSON files were treated as the current report authority for scores, market inputs, source IDs, URLs, and limitations.

### Independent audits

- Every-visible-number inventory and numeric audit
- Independent score and formula audit
- Source and logic challenge audit

### Refresh receipts

- `data/receipt_summary.json`
- `data/source_receipts/census-pep-sub-est2025.csv`
- `data/source_receipts/census-pep-sub-est2024.csv`
- `data/source_receipts/quickfacts-live-audit-extract.json`
- `data/source_receipts/osrm-r01-current.json`

These package-relative files are shipped in the report packet.

### Canonical methodology and plan

- `CALCULATIONS.md`
- `RUBRIC.md`
- `WEBSITE_POSITIONING.md`
- `FIX_IT_PLAYBOOK.md`
- The Vintage Optical publication-review yardstick

## Number families covered

1. Headline and internal score family:
   - Client Opportunity 54 / 100
   - Market Demand-Supply 57 / 100
   - internal Competitive Pressure 57
   - Room to Win 43 / 100
   - Practice Competitiveness 58 / 100
   - Digital Presence 57 / 100

2. Specialty score family:
   - Dry eye / ocular surface 52 / 100
   - Myopia management 52 / 100
   - Specialty contact lenses 51 / 100

3. Public fact and route family:
   - current 2025 Morton village estimate 17,565
   - historical 2024-vintage estimate 17,557
   - under-18 share 25.9%
   - age-65-plus share 23.1%
   - R01 duration 244.3 seconds
   - route conversion `244.3 / 60 = 4.0717`, rounded to 4.07 minutes

4. Method and plan family:
   - 20-minute primary and 30-minute extended method
   - exactly three Tier 1 and three Tier 2 entries
   - exactly three Fix Cards
   - exactly three specialty lanes
   - one consolidated lane table
   - 30-day measurement window

5. Structural family:
   - section 1/2/3
   - Tier 1/2 labels
   - F-001/F-002/F-003 identifiers
   - 24 source IDs
   - 100-point scale
   - street number 605
   - age thresholds 18 and 65
   - seconds-per-minute factor 60
   - 2024/2025 source vintages
   - 2026 copyright year

## Logical decisions

### 1. Current and historical Census values remain separate

The current display uses 17,565 from S17 and the frozen 2025 PEP receipt. The earlier 17,557 remains the historical value from the official 2024-vintage file. The newer file's revised 2024 back-series value of 17,555 is disclosed as a vintage note and does not overwrite the earlier source lineage.

### 2. The population refresh does not change a score

Neither 17,557 nor 17,565 is placed into a 20- or 30-minute catchment. Fixed-window population, VDU, supply, provider, and ratio fields remain null. The refresh therefore changes no component band, contribution, full-precision total, rounded score, specialty read, Fix Card, or Confidence C.

### 3. All report scores use one direction

Every displayed report result is higher = better. The internal Competitive Pressure value is higher = more pressure and is clearly identified as an internal calculation input. Room to Win is its exact high-good inversion: `100 - 57 = 43`.

### 4. Neutral 50 is missing-evidence handling

The explainer defines neutral unknown 50 as a midpoint used when proof is absent, not measured average performance and not zero. A few 50 bands represent mixed public evidence, but none is used as positive operating proof.

### 5. Repeated values are reconciled

Market Demand-Supply, Competitive Pressure, and Digital Presence each reach 56.75 and round to 57 through different components. Dry eye and myopia each total 51.50 and round half up to 52 because their current band patterns match. Shared results are arithmetic coincidences under the current evidence, not duplicated meanings.

### 6. Specialty lanes remain RESEARCH NEXT

The public offers are verified, but the analysis lacks catchment demand, conversion, capacity, outcomes, referrals, and economics. Competitor overlap also prevents dry-eye or myopia white-space claims. The scores are research priorities, not patient or revenue forecasts.

### 7. Fix Card math remains plug-in measurement

Every numerator and denominator is defined. A zero, missing, or unfinished denominator returns null / not calculable, never zero. The 30-day period is a baseline window. No patient, leakage, revenue, or dollar outcome is assumed.

### 8. External links and local receipts are different

All 24 registry IDs link to their registered public URLs. The frozen CSV and JSON receipt paths are separately labeled local lineage artifacts rather than public links.

## HTML construction

- Self-contained CSS and document structure
- Only allowed relative asset: `assets/mybcat-logo.png`
- `@page { size: Letter; }`
- Print margins and bottom footer with page counter
- Restrained navy, teal, sand, and gray MyBCAT visual system
- Print-only `thead { display: table-header-group; }` for repeated table headers
- Direct semantic `thead` and `tbody` in all 13 data tables
- Room to Win keep-together section with `avoid-break` print rules
- Row-level break avoidance and overflow wrapping
- Deliberate page break between the two source dictionaries
- Package-relative receipt manifest and final interpretation on the closing source page
- 33 unique `data-number-id` values on substantive rows and sections
- 24 unique public URLs
- 198 clickable source-ID occurrences
- Markdown and HTML facts generated from the same Markdown source

## Verification

1. Exact polish validator:

   `python3 checks/validate_explainer_polish.py --dir .`

   Result: `PASS: polished explainer has no internal path leaks, uses package-relative receipts, protects Room to Win pagination, repeats table headers, and balances the final source/receipt sections`

2. Structural preservation audit:

   - 33 unique number families before and after
   - 24 unique public links before and after
   - 24 source-dictionary records before and after
   - 13 HTML data tables, each with direct `thead` and `tbody`
   - no absolute or internal workspace path in either explainer
   - no em dash or prohibited outward-use language in any deliverable

3. In-memory Letter render:

   - renderer: WeasyPrint 67.0
   - page size: Letter
   - page count: 12
   - Room to Win heading, formula, direction, interpretation, and mover explanation stay together on page 4
   - Structural numbers table and its column header appear together on page 9
   - `Source dictionary: public sources` occupies page 11 with 17 records
   - `Source dictionary: receipts and routes`, the package receipt manifest, and `Final interpretation` occupy page 12
   - final text baseline: page 11 at 516.5 points and page 12 at 608.6 points on a 792-point page
   - no saved PDF or contact sheet added to the deliverables

4. Chrome check:

   Headless Chrome 150 was attempted twice with no document output. The managed sandbox blocked Chrome's Crashpad and sandbox-host socket operations before rendering. This environment failure does not change the exact-validator result, but Chrome-specific pagination remains unverified in this pass.

The rendered pages used for local visual inspection were temporary and were not retained as deliverables.

## Limitations

- Project Room inventory review is still required.
- The evidence remains public-only and directional.
- No measured drive-time population or demographic catchment exists.
- The peer routes do not form a complete supply or patient-choice census.
- Provider counts and VDU are unknown.
- The Maps sample is not a rank grid or peer-normalized reputation export.
- Live access, booking conversion, capacity, outcomes, referrals, economics, and execution capacity are unknown.
- The logo is referenced at the allowed relative path and is expected to be supplied by the downstream artifact renderer.
- Chrome-specific pagination could not be verified because the managed sandbox blocked the browser before document rendering.
- No saved PDF or visual contact sheet was retained under the three-file write boundary.

## Decision residue

- Hardest decision: rebalance the final source material without changing any source record, shrinking body copy, or weakening the internal review boundary.
- Alternative rejected: summarize only the final scores. That would omit component rationale, missing evidence, Fix Card denominators, source limitations, and repeated-value reconciliation.
- Alternative rejected: treat public service breadth, city demographics, routes, or a 4.9 Maps sample as operating performance.
- Least-confident assumption: the 12-page in-memory render will match the downstream Chrome renderer's pagination exactly. Explicit keep-together, repeated-header, and source-section page-break rules reduce the risk, but the managed sandbox prevented Chrome proof.

## Highest true state

Local internal artifact with deterministic content validation and an in-memory 12-page Letter render. Project Room review remains required. External actions: none.
