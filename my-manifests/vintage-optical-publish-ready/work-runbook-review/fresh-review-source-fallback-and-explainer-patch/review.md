# Fresh-context patch review

Verdict: PASS

Readiness: REVIEWED_PATCH_READY_TO_APPLY

Changed file: RUNBOOK_COMPETITIVE_ANALYSIS.md

Scoring formulas changed: no

External-action authority changed: no

No fatal, material, or minor issues

Patch may be applied for human review

## Materialization and commands

The source repository was not modified. The current runbook retained SHA-256 `4c0a2d0bb5bf7fe1b5544fc289d7a5909c857c801634fbe694ee1342fd3f50d7` before and after review, and `git status --short -- RUNBOOK_COMPETITIVE_ANALYSIS.md` remained empty.

The patch was materialized under `/tmp/runbook-source-explainer-review.vmlmRe` with:

```bash
review_tmp_dir=$(mktemp -d /tmp/runbook-source-explainer-review.XXXXXX)
cp /mnt/d_drive/repos/optometry-competition-analyzer-rubric/RUNBOOK_COMPETITIVE_ANALYSIS.md "$review_tmp_dir/RUNBOOK_COMPETITIVE_ANALYSIS.md"
(
  cd "$review_tmp_dir"
  patch -p1 < /home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/artifacts/runbook-source-explainer-upgrade.patch
)
```

Result: `patching file RUNBOOK_COMPETITIVE_ANALYSIS.md`. The materialized file has 423 lines and SHA-256 `0e5bf3a1b7eebc3fa969d4898c657b4c4e6a105f21e4d8a2523f28413a7243b5`.

The canonical validator was run with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 /home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_competitive_runbook_upgrade.py \
  --path "$review_tmp_dir/RUNBOOK_COMPETITIVE_ANALYSIS.md"
```

Result:

```text
PASS: competitive-analysis runbook defines the required source ladder, fallbacks, completeness rules, mandatory number explainer, checked Ringer lanes, and human Project Room gate
```

Repository applicability and scope were checked without applying the patch:

```bash
git -C /mnt/d_drive/repos/optometry-competition-analyzer-rubric apply --check \
  /home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/artifacts/runbook-source-explainer-upgrade.patch

git -C /mnt/d_drive/repos/optometry-competition-analyzer-rubric apply --numstat \
  /home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/artifacts/runbook-source-explainer-upgrade.patch
```

Results: `git apply --check` exited 0. Numstat reported `416  58  RUNBOOK_COMPETITIVE_ANALYSIS.md`. Patch headers name only `a/RUNBOOK_COMPETITIVE_ANALYSIS.md` and `b/RUNBOOK_COMPETITIVE_ANALYSIS.md`.

An independent formula assertion confirmed that the full VDU block in materialized lines 230-240 exactly matches `CALCULATIONS.md` lines 53-63. It also confirmed three exact occurrences of `Room to Win = 100 - Competitive Pressure Index`, in scoring, explainer recomputation, and release QA.

## Yardstick evidence

| Check | Result | Concrete patch evidence |
|---|---|---|
| `contract_traceability` | PASS | Materialized lines 5-23 preserve the product question, GROW and `public_only` scope, one-page executive deliverable, five-business-day SLA, PHI boundary, human intake and delivery, higher-good reporting, three-card limit, and the no-formula-change rule. |
| `source_hierarchy` | PASS | `Source hierarchy and fallback ladder`, lines 78-105, names official APIs, first-party pages, DataForSEO, Google Search/Maps, Exa, Perplexity, direct public directories, and frozen receipts. |
| `dataforseo_preflight` | PASS | `DataForSEO preflight`, lines 95-105, checks endpoint, fields, authentication, availability, quota, expected cost, geography, language, device, result depth, cost stop, and fallback before any paid request. |
| `fallbacks` | PASS | Lines 105-107 fail closed on missing configuration, authentication, credentials, quota, HTTP access, empty results, or cost stop and name Google Search/Maps, Exa, and Perplexity fallbacks. |
| `discovery_evidence_separation` | PASS | Lines 80-93 prohibit discovery output, snippets, generated summaries, citation lists, and uncaptured browser statements from becoming publication evidence without an underlying direct URL or official API and frozen receipt. |
| `local_seo_context` | PASS | Lines 162-176 require query, geography or coordinates, radius or grid point, device, language, timestamp and timezone, result position, URL, entity match, platform, source ID, and receipt. Lines 176 and 107 distinguish a true grid from a dated sample. |
| `review_handling` | PASS | Lines 178-184 keep rating, count, recency, velocity, response behavior, and aggregator composition platform-specific and prohibit silent cross-platform averaging or summing. |
| `catchment_completeness` | PASS | Lines 186-200 require polygon GeoJSON for 5, 10, 15, 20, and 30-minute windows, polygon validation, ACS/TIGER block-group intersection, separate city/ZIP/county context, and explicit point-route limitations. |
| `supply_census` | PASS | Lines 202-224 state that NPPES records are not office counts and require geocoding, classification, deduplication, match confidence, preserved raw candidates, merge maps, duplicate groups, rejects, stale and legacy addresses, and exclusion reasons for every named entity class. |
| `vdu_gate` | PASS | Lines 226-246 preserve every canonical VDU term exactly, require source lineage for all six terms, keep incomplete full VDU null, and confine reduced models to labeled partial diagnostics. |
| `gap_register` | PASS | Lines 109-134 require attempted sources, exact failure, fallback, owner, status, and upgrade evidence, preserve gap history, keep missing values null, and prohibit interpreting unknown as zero or average. |
| `number_explainer` | PASS | Lines 270-304 require Markdown, HTML, and PDF plus source/date, units/geography, formula, direction, interpretation, confidence, limitations, unknown handling, consistency, repeated values, structural tokens, disconfirmers, source dictionary, receipt manifest, and `What we do not know`. |
| `release_qa` | PASS | Lines 339-376 require 100 percent number lineage, formula recomputation, source resolution, current-vintage and link checks, render and visual checks, stale-output cleanup, path and sensitive-data scans, and three independent fresh-context reviews. Failed gates reopen the owning step and all affected checks. |
| `ringer_lanes` | PASS | Lines 391-423 define checked intake/preflight, fetch, transform/dedupe, source-audit, catchment, scoring, explainer, render, and fresh-review lanes. Failure returns to the owning lane and reruns dependents. No lane may deliver, email, write HubSpot, publish, commit, push, merge, or deploy. |
| `human_boundary` | PASS | Lines 13-16 and 325-337 keep intake, Project Room approval, external use, and delivery human-owned. Line 337 states that the runbook does not authorize email, HubSpot writes, uploads, publishing, or any other external action. |
| `formula_preservation` | PASS | Lines 23 and 250 prohibit engagement-level formula or weight changes. Lines 230-246 match canonical VDU. Lines 262, 302, and 355 preserve the exact Room to Win inversion. No rubric or calculation file is changed. |
| `one_file_scope` | PASS | Patch headers and `git apply --numstat` identify only `RUNBOOK_COMPETITIVE_ANALYSIS.md`. |
| `style` | PASS | The canonical validator found no em dash. An independent scan found no leaked canary, report-specific Vintage/Morton value, absolute internal path, private-key marker, bearer token, or common access-key marker in the materialized runbook. |

## Review conclusion

The patch is executable as a general runbook rule set, preserves the existing product and scoring contracts, closes the source and number-lineage gaps documented by the supplied explainer, and adds no autonomous external authority.
