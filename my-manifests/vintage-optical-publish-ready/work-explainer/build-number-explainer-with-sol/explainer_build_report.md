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
| U5 | Verify scope, structure, print length, and prohibited language | Canonical explainer validator plus in-memory Letter render | Passed after one wording correction |

## Inputs read

### Current staged report authority

- `work-stage-report/stage-current-number-refresh-with-sol/updated-scores.json`
- `work-stage-report/stage-current-number-refresh-with-sol/updated-market_inputs.json`
- `work-stage-report/stage-current-number-refresh-with-sol/updated-sources.json`
- `work-stage-report/stage-current-number-refresh-with-sol/updated-evidence.md`
- `work-stage-report/stage-current-number-refresh-with-sol/updated-scoring_notes.md`
- `work-stage-report/stage-current-number-refresh-with-sol/updated-research_notes.md`
- `work-stage-report/stage-current-number-refresh-with-sol/updated-onepager.html`
- `work-stage-report/stage-current-number-refresh-with-sol/build_report.md`

The three staged JSON files were treated as the current report authority for scores, market inputs, source IDs, URLs, and limitations.

### Independent audits

- `work-audit/inventory-every-visible-number/number_inventory.json`
- `work-audit/inventory-every-visible-number/numeric_audit.md`
- `work-audit/recompute-every-score-and-formula/formula_audit.json`
- `work-audit/recompute-every-score-and-formula/formula_audit.md`
- `work-audit/challenge-sources-and-logic/source_checks.json`
- `work-audit/challenge-sources-and-logic/source_logic_audit.md`

### Refresh receipts

- `work-refresh-v3/freeze-current-public-number-receipts-v2/receipt_summary.json`
- Frozen 2025 PEP CSV
- Frozen 2024-vintage PEP CSV
- Saved QuickFacts audit extract
- Saved current R01 OSRM response

### Canonical methodology and plan

- `/mnt/d_drive/repos/optometry-competition-analyzer-rubric/CALCULATIONS.md`
- `/mnt/d_drive/repos/optometry-competition-analyzer-rubric/RUBRIC.md`
- `/mnt/d_drive/repos/optometry-competition-analyzer-rubric/WEBSITE_POSITIONING.md`
- `/mnt/d_drive/repos/optometry-competition-analyzer-rubric/FIX_IT_PLAYBOOK.md`
- `plan.md`, the Vintage Optical publish-readiness yardstick

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
- Repeating table headers
- Row-level break avoidance and overflow wrapping
- 33 unique `data-number-id` values on substantive rows and sections
- 24 unique public URLs
- 198 clickable source-ID occurrences
- Markdown and HTML facts generated from the same Markdown source

## Verification

1. Canonical command:

   `python3 checks/validate_explainer.py --dir <build-directory>`

   Initial result: one exact wording failure because the prose said "current displayed city estimate" rather than the required phrase "2025 city estimate."

2. Correction:

   The current population sentence now says "current displayed 2025 city estimate."

3. Recheck target:

   - required sections and formulas
   - internal Project Room boundary
   - prohibited readiness language absent
   - no em dash
   - at least 13 unique number IDs
   - at least 12 unique public links
   - Letter print CSS

4. In-memory render:

   - renderer: WeasyPrint
   - page size: Letter
   - page count: 12
   - extra render artifacts written: none

The in-memory render checks page count and page geometry. It is not a saved PDF or screenshot review because the user limited file writes to the three deliverables.

## Limitations

- Project Room inventory review is still required.
- The evidence remains public-only and directional.
- No measured drive-time population or demographic catchment exists.
- The peer routes do not form a complete supply or patient-choice census.
- Provider counts and VDU are unknown.
- The Maps sample is not a rank grid or peer-normalized reputation export.
- Live access, booking conversion, capacity, outcomes, referrals, economics, and execution capacity are unknown.
- The logo is referenced at the allowed relative path and is expected to be supplied by the downstream artifact renderer.
- No saved PDF or visual contact sheet was created under the three-file write boundary.

## Decision residue

- Hardest decision: preserve full methodology detail while keeping a 12-page practice-owner read and distinguishing raw facts, directional bands, derived scores, and structural numbers.
- Alternative rejected: summarize only the final scores. That would omit component rationale, missing evidence, Fix Card denominators, source limitations, and repeated-value reconciliation.
- Alternative rejected: treat public service breadth, city demographics, routes, or a 4.9 Maps sample as operating performance.
- Least-confident assumption: the 12-page in-memory render will match the downstream browser renderer's pagination exactly. Letter geometry, conservative break rules, and repeated table headers reduce the risk, but no saved browser proof was produced.

## Highest true state

Local internal artifact with deterministic content validation and an in-memory 12-page Letter render. Project Room review remains required. External actions: none.
