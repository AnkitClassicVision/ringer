# Model notes — how workers actually perform

A running log of how models perform on real Ringer tasks, so engine and
model choices are made on evidence instead of vibes. The raw numbers now
live in the local eval log (`~/.ringer/runs.jsonl`); run `./ringer.py models`
to print the per-model, per-task_type scoreboard (tasks, attempts,
pass_rate, first_try_pass_rate, median duration/tokens, last_seen). This
file remains the judgment layer on top of those numbers.

**How to add a row:** after reviewing a run (post-run ritual step 5 in the
ringer skill), append one dated line under the model. Say the task type,
what happened, and what you'd do differently. Only write what the executed
checks and raw logs support — no vibes, no worker self-reports.

## codex (GPT-5-class, own harness)

- Strongest general worker; the default engine. Spend reasoning effort per
  task via `engine_args` (`["-c", "model_reasoning_effort=low|medium|high"]`)
  — high on gnarly tasks, low on boilerplate.
- 2026-07-16 — harness-cleaner-rollout (task_type=research, local config
  audits): 3 lanes, 2 PASS attempt 1, 1 PASS attempt 2. The retry was a
  spec/check bug, not a model fault: workers naturally cite `~/`-prefixed
  paths, and the validator only counted `/home/...` absolute paths as
  evidence. Lesson: specs auditing home-dir files must say "cite full
  absolute paths starting with /home/", or the validator must expand `~`.
  Report quality was high (measured counts, honest coverage gaps).
- 2026-07-12 — SCOREBOARD CORRECTION (mybcat-seo blog-pipeline now-round):
  the now-degreenwash and now-image-estate-audit FAILs were FALSE NEGATIVES
  — three orchestrator check/spec bugs, zero worker faults. (a) regex paired
  a step name with the NEXT step's continue-on-error (fix: walk parsed YAML,
  never regex-pair steps); (b) the check contradicted the spec's own allowed
  pattern (per-validator continue-on-error + hard-failing aggregation step)
  — encode the policy, don't approximate it; (c) the audit spec told a
  sandboxed worker to write deliverables OUTSIDE its worktree — the CHECK
  must export deliverables, the worker writes only in its task dir. The
  degreenwash worker's output was verified correct and salvaged from the
  leftover failed worktree by running the fixed check manually. Two more in
  the same job: (d) a broad test glob matched a pre-existing pytest-only
  module before the worker's new unittest module (name the EXACT expected
  test file in spec and check); (e) a region heuristic anchored on the
  first "nanobanana" string (a config line ~2700 lines above the fallback)
  — anchor checks on the actual helper/call-site names, then verify call
  counts. Worker's fallback fix was correct (54 regression + 2 new tests
  green) and salvaged the same way. Five false negatives, one job: when a
  fail arrives, audit the CHECK before the worker. Also: leftover worktrees
  from failed tasks block re-runs with the same task keys — `git worktree
  remove` them (after salvage) before relaunching.
- 2026-07-12 — mybcat-seo-growth-loop, 5-round proof/fix/review job: 7/8
  codex tasks passed attempt 1, including two hard security code-fixes
  (write-boundary confinement, ~145k and ~123k tokens at reasoning=high)
  where the spec embedded the exact policy and the check executed real
  attack probes. The one retry was a code-review whose attempt-1 report was
  too thin for the review check — the fresh-review lane benefits from a
  minimum-substance bar in the spec, not just the check. Adversarial
  re-review with "reproduce the escape yourself" instructions caught a real
  residual HIGH (derived out/runs symlink) that the first fix's own green
  suite missed — keep that reviewer pattern.
- 2026-07-11 — SCOREBOARD CORRECTION: the two code-fix FAILs from run
  lab-ticket-guard (gate-lab-g1, 210k tokens) were FALSE NEGATIVES — the
  worker's code was complete and correct on attempt 2; the check script
  failed on environment (Go VCS stamping needs GOFLAGS=-buildvcs=false in
  detached ringer worktrees, and the repo has a deliberately-failing
  fail-closed sentinel test that full-package `go test` gates must -skip).
  Corrected check executed manually against the surviving worktree: PASS.
  Discount those two rows when routing code-fix work.
- 2026-07-11 — live EMR probe (lab-ticket-guard, reasoning=high): passed on
  attempt 2, 268k tokens. Excellent boundary engineering unprompted beyond
  spec (transport-level route allowlist, redirects disabled, counters).
  Attempt-1 failure mode: trusted the CLI's `auth status` presence check
  over live validity and hit a 404 on a session-bound page. Next time: when
  a probe spec targets a session-auth system, mandate a fresh headless
  login unconditionally instead of "if not authenticated".
- 2026-07-05 — carried the heavy lanes of the milk-crate demo rehearsals
  (market read with source allowlist, site build) with clean first-attempt
  passes.
- 2026-07-06 — adversarial pre-merge review (aicred spark): passed on
  attempt 1, ~85k tokens.
- 2026-07-06 — motion design (5 HTML animations for video b-roll) + 2
  editorial diagram pages, each verified by rendering through headless
  Chromium to MP4/PNG: 7/7 passed on attempt 1. Broadcast-quality visual
  output from rich storyboard specs; the render-as-check pattern works.
- 2026-07-06 — milk-crate demo: two single-file website builds (v1 scaffold
  316s/~175k tok; final brand+market-test reskin 622s/~184k tok), both passed
  14-assertion content checks on attempt 1, including base64-embedding photos
  and honoring honesty-marker requirements. Codex remains the site-build lane.
- 2026-07-06 — ringer.py feature batch (task_type field + enriched eval rows
  + `models` scoreboard + hud single-tab fix; ~640-line diff incl. two new
  test suites): substance passed on attempt 1 — its check printed PASS
  (compile, all 16 suites, exact CLI aggregation contract) — but the run
  recorded attempt 2 because of the expect_files-before-check harness bug
  (see process lessons). Heavy single-file feature work against an exact
  behavioral contract is squarely codex's lane.

- 2026-07-06 — elsas-website demo: Next.js scaffold PASSED attempt 2 (682s,
  ~354k tok) — attempt 1 built a complete homepage and silently skipped the
  other 10 routes; the route-enumeration check caught it. Narration lane
  (15 ElevenLabs calls, chunked, nohup pattern) passed attempt 1. CAUTION: a
  codex fix worker GAMED a verbatim-content needle by hiding the required text
  in a visually-hidden paragraph — passed the check, caught only by
  orchestrator integration review. Needle checks need an anti-hidden-text
  assertion or documented exceptions.

- 2026-07-06 — OpenRouter catalog + explore suggester (catalog subcommand
  with snapshot/changelog/free-detection, daemon auto-refresh, tiered
  --explore; offline fixture-driven contract check): PASS attempt 1, 362s.
  Follow-up sentinel-pricing fix (variable-pricing models): PASS attempt 1,
  114s. With the verify-order fix landed, zero phantom retries across the
  whole batch.
- 2026-07-06 — adversarial review of the model-router stack (2,650-line
  diff, structured report contract): PASS attempt 1, 176s — found a real
  HIGH (--since window inflating first-try rates) plus 3 MEDIUMs, all
  confirmed against the code. Then fixed all five review findings in one
  batch (task-level --since, pricing transitions, event durability + flock,
  unknown pricing, stderr notice) with test coverage: PASS attempt 1, 202s.
  Review->fix roundtrip in codex's lane works end to end.
- 2026-07-06 — scoreboard HTML page (zero-LLM renderer, ~700-line diff,
  design + evidence-floor ranking + cost math + notes parser): substance
  PASS attempt 1 (the run's recorded retry was an orchestrator check bug —
  the free-promo watchlist legitimately mentions a free model before the
  ranked cards, and the check compared raw first-occurrence). Six review
  findings fixed in one batch, PASS attempt 1, 141s.
- 2026-07-06 — model-db stack (SQLite read model 516s, page redesign 536s,
  Ringside tab 527s, plus three fix batches all attempt-1): five substantial
  ringer.py features in one day, every one against an executed contract
  check. Review lane found the HIGH that mattered (sync cursor skipping a
  half-written trailing line). Codex is the proven lane for both sides of
  the review->fix loop on this codebase.
- 2026-07-10 — Ankit Coffee List: fresh report-only review found a real
  MEDIUM data-honesty bug on attempt 1 (six `best_brew=either` products were
  rendered as Cortado). The post-fix review reached PASS but needed attempt 2
  because the checker read a quoted prior verdict instead of the final line;
  fix final-verdict checks before blaming the reviewer. Important containment
  lesson: the site-build worker attempted automatic ATLAS/Work Ledger writes
  after its artifact was ready. For no-capture Codex tasks, pass
  `-c mcp_servers.ob_mybcat.enabled=false`; prose-only boundaries were not
  sufficient.
- 2026-07-16 — Yaryan standard report (research/site-build/code-review):
  monolithic Codex workers repeatedly consumed large staged rubric packets and
  exited before their first complete artifact, while bounded score, page,
  status, closure, and fresh-report-review units produced validator-clean
  artifacts. Recovery that worked: preserve partial outputs, split by artifact,
  use focused fail-closed stage gates, route only mechanical Chrome rendering
  through `local-shell`, then finish with the full validator and a fresh review.
  Do not retry the same large packet unchanged when the log shows read-heavy
  progress but no first write.

## glm-5.2 via opencode (`openrouter/z-ai/glm-5.2`)

- The cheap-intelligence default (~$0.74/M in, $2.33/M out, 2026-07 —
  20-30x cheaper output than frontier coding models). Reliable on
  mechanical, tightly-specced work: file edits, format conversions,
  template-driven builds.
- 2026-07-17 - insurance-verification cost research (task_type=research):
  the vendor lane passed attempt 1 in 329.5s on the Z.AI Coding Plan and
  produced a useful 1,581-word official-source comparison with correct
  progressive Stedi arithmetic. A parallel HIPAA lane produced useful source
  material but entered a tiny-edit loop around the 1,600-word and exact-field
  checker, then was killed without a green Ringer result. For broad research,
  split source domains or give GLM a less brittle length contract rather than
  letting self-trimming consume the run.
- 2026-07-17 - insurance-verification private visualization
  (task_type=site-build/code-fix): the first GLM worker produced the strong
  HTML/SVG/PNG core but outlived the 600s wrapper while polishing the viewport.
  A bounded repair added the cost rail, docs, and executable verifier. Its own
  gate passed; the external gate falsely rejected the required SVG XML
  namespace as a network URL and triggered a wasted retry. After correcting
  that checker, both gates and visual QA passed. Split visual composition from
  repository packaging on future runs, allow more time for the composition
  lane, and never reject `xmlns` when checking SVGs for external resources.
- 2026-07-05 — milk-crate demo rehearsals: handled brand-board/SVG/copy
  tasks at around a penny per passing task.
- 2026-07-16 — harness-cleaner-rollout hermes lane (task_type=research,
  zai-coding-plan/glm-5.2): PASS attempt 2, ~632s, thorough config audit
  with self-verification of cited paths before writing. Attempt-1 fail was
  the shared `~`-vs-absolute-path validator bug (also hit codex), not a
  quality issue. Second clean research pass for this selector; fine to
  keep auditioning it on read-only audit/research lanes.
- 2026-07-06 — adversarial pre-merge review (aicred spark): passed, but
  needed the retry (attempt 2) where codex passed on attempt 1. Long
  structured reviews sit at the edge of its comfort zone; keep the section
  contract explicit in the spec.
- 2026-07-06 — three mechanical image-generation batches (18 images via
  openrouter-image commands, idempotent batch-runner spec): 3/3 passed on
  attempt 1, ~14.5k tokens each. The "execute these exact commands, do not
  improve them" spec pattern is fully reliable for glm-5.2.

- 2026-07-06 — backfill/seed script for the model log (252-line stdlib CLI
  with a run-state join, 3-level mapping precedence, never-overwrite and
  idempotency rules): the artifact was CORRECT; the recorded FAIL was an
  orchestrator check-fixture bug (a missing newline glued the fixture's last
  row to a garbage line) plus the harness ordering bug below. Verified PASS
  once the check was fixed. Tight behavior contracts in the spec work great
  for glm — and read the raw logs before blaming the model.
- 2026-07-06 — README/MODEL-NOTES docs + task_type sweep across 17 template
  manifests: passed attempt 2; attempt 1 was lost to the harness ordering
  bug, not model quality — the retry worker's log correctly diagnosed that
  harness bug unprompted, impressive debugging from the cheap lane.
- 2026-07-06 — catalog/explore README section (flags, promotion ladder,
  per-user framing): PASS attempt 1, ~21.5k tokens. Doc sections against a
  grep-able content contract remain a safe glm lane.
- 2026-07-12 — mybcat-seo-growth-loop north-star doc (docs): PASS attempt 1
  in 92s against a 13-term substance check incl. an exact source-of-truth
  path table and a no-em-dash rule. Third first-try docs pass — glm-5.2 is
  now proven for task_type=docs on this machine; enumerated content
  contracts remain the winning spec shape.
- 2026-07-06 — milk-crate demo, full run: 4 independent buyer-persona
  reviews (focus group) all passed attempt 1 (~15k tokens, ~2¢ each) with an
  explicit VERDICT-block contract — persona work is squarely in glm's zone.
  Market read with live curl fetching passed once the spec demanded verbatim
  copy-paste of source URLs (first fail was the worker trimming URL slugs —
  spec/check craft, not model weakness). Brand-kit doc incl. a clean inline
  SVG wordmark: good, one bounce off an over-strict check regex.

- 2026-07-06 — elsas-website demo: verbatim content capture (16 pages + 19
  news posts, 213 blockquotes) passed attempt 2 — attempt 1 SELF-REPORTED
  "all 213 match exactly, 0 errors" while the executed check found 13 stitched/
  paraphrased quotes. Self-reports are worthless; the retry with injected
  failures fixed all 13 (~148k tok total, ~3¢). Page builds (about+faq;
  news index + 19 generated post routes via its own extraction script) and
  2 focus-group personas: all attempt 1. Fix batch attempt 1.
- 2026-07-06 — invariants/file-I/O review lens on the same stack: PASS
  attempt 1, 68k tokens — caught the non-atomic backfill rewrite (real data
  loss risk) and the daemon stdout race; both confirmed. Then fixed the
  backfill atomicity (tmp+os.replace, pid-stamped backups) attempt 1 with
  the original behavioral grader unchanged. Structured review with an
  explicit lens is now proven glm territory, not just probation.
- 2026-07-06 — solo adversarial review of the scoreboard renderer (~700
  line diff, injection-focused lens): PASS attempt 1 — 1 MEDIUM (unanchored
  MODEL-NOTES heading match cross-contaminating gpt-4/gpt-4o-style
  families) + 5 real LOWs, plus an empirically-verified injection all-clear
  (it actually rendered hostile model ids to prove escaping). Second
  proven-tier structured review in one day; glm is now the default review
  lane for mid-size diffs.
- 2026-07-06 — invariants/injection/frontend review of the 4,061-line
  model-db branch: PASS attempt 1, 96k tokens, 14 coverage items — two real
  contention findings (full catalog re-ingest per sync; schema writes on
  read paths) plus an empirical XSS all-clear on the new DOM surfaces.
  Third proven-tier structured review today.
- 2026-07-09 - HSD2 sales-outcome manifest review (task_type=docs):
  PASS attempt 1, 138s. GLM produced a grounded REVISE verdict against a
  source-backed manifest, correctly separating safety defects from
  measurement gaps: missing booked-calls primary metric/downstream guardrail,
  generic Gate C honesty language, and audit proof that could pass without
  proving sales movement. Structured review with a tight heading/term
  validator remains a good GLM lane.
- 2026-07-09 - HSD action-operator architecture audit (task_type=docs):
  PASS attempt 1, 297s. GLM gave a useful ACCEPT_WITH_CORRECTIONS verdict on
  Fable's architecture, accepting the core 50-action/executor design while
  catching a real sourcing-integrity issue: Fable cited 27 source references
  but the audit task only had 14 staged files. Good use case: second-pass
  artifact auditing with staged-file inventory checks and gate consistency
  review.
- 2026-07-10 - Ankit Coffee List bounded repairs (task_type=code-fix): 2/2
  attempt-1 PASS. One task fixed a favicon console 404 with a self-contained
  data-URI; the second corrected the three-value brew-label mapping across
  three files and added the regression test. Both passed the unchanged full
  browser/build checker. Prefer GLM for small, tightly-owned post-review fixes
  when Codex global capture hooks are undesirable.

- 2026-07-16 (fit-battery UI redesign): 5/6 lanes passed. Critique lanes (persona-review) needed attempt 2 on the review-swarm validator's exact contract; ux-admin lane FAILED twice only on 'evidence must cite file:line' when citing supplied screenshots - content was substantive and used anyway. Build lanes (site-build design-system rewrite 1000+ line CSS, code-feature candidate-flow rebuild) passed FIRST TRY with npm ci+tsc+61 tests+next build as the executed check. GLM cannot view image inputs - don't hand it screenshots as evidence sources.

## claude-lean Fable (`engine: claude-lean`, `model: fable`)

- 2026-07-17 - insurance-verification workflow architecture
  (task_type=docs): chief decision packet passed attempt 1 in 216.5s with a
  decisive API-first route, PHI boundary, cost caps, CLI portfolio, calculator
  contract, and 20-record read-only pilot. A correction round fixed real
  pricing residue but failed both attempts because Fable changed the locked
  schema version from 1.0 to 1.1 while claiming all checks were green; a
  zero-model local-shell closure changed that one field and passed in 0.2s.
  Fable remains a strong owner-level decision lane, but repeat exact schema
  invariants in correction prompts and trust the executed validator over its
  completion summary.
- 2026-07-12 — mybcat-seo go-live rounds (user-requested Fable engine): split
  verdict by TASK SHAPE, not model quality. Writing-shaped work passed:
  canary approval packet (docs, attempt 1, judgment call flagged instead of
  guessed), blog_content bridge (code-feature, substance correct — recorded
  FAIL was an orchestrator check invoking the exporter's own CWD-confinement
  boundary; salvaged manually), seeder adapter (attempt 2). EXECUTION-shaped
  work is blocked by the harness, not the model: claude-lean safe-mode denies
  Bash for mass file transforms and localhost servers (image backfill,
  lighthouse probe both stalled awaiting permission). Integrity highlight:
  the backfill worker identified git-alias shell-escape evasions and refused
  them on principle. Route execution-heavy tasks to codex (sandbox permits
  worktree execution); its full_access flag covers localhost/Chromium needs.
- 2026-07-09 - Atlanta independent-network canary (task_type=probe): FAIL on
  both immediate attempts because the Claude OAuth account reported its monthly
  spend limit was reached; no artifact was created. This is an account-state
  failure, not a model-quality result. Probe current availability before routing
  a critical verifier wave to Fable.

- 2026-07-09 - Podcast recovery editing monitor (task_type=verification): the
  Fable OAuth route completed twice on attempt 1 (63s and 127s). The first
  artifact correctly blocked editing but misclassified production configuration
  as not requiring approval; orchestrator review caught what the initial check
  missed. After adding explicit approval facts and executable assertions, the
  corrected artifact passed and held configuration, deploy, replay, and release
  behind separate gates. Use Fable for gate judgment, but make high-impact
  authorization semantics executable in the validator.

- 2026-07-09 - HSD2 sales-strategy manifest review (task_type=docs):
  absolute source paths failed under safe-mode because the worker could read
  only its task directory; retry produced a useful BLOCK-as-unreviewed but
  failed the sanitizer check. After staging read-only source copies under
  the task directory, the identical review lane passed attempt 1 in 233s
  with a substantive REVISE verdict. For Fable/Claude safe-mode reviews,
  stage `./sources/` inside the task dir or allow-list paths before launch,
  and add a source-readability preflight.
- 2026-07-09 - HSD recurring Ringer boss-manifest decision
  (task_type=docs): PASS attempt 1, 342s. Fable produced a useful BUILD
  verdict for a noncoding decision task when given staged source copies,
  prior model-review artifacts, and a strict heading/term validator. Best
  lane: owner/boss-level workflow decisions and recurring-manifest shape,
  not implementation. Keep the source packet local to the task dir and make
  the deliverable prove a sales-movement artifact, not process commentary.
- 2026-07-09 - HSD sales automation readiness decision (task_type=docs):
  PASS attempt 1, 331s. Fable gave a decisive
  AUTOMATE_READONLY_AFTER_DRY_RUNS verdict, separating read-only daily radar
  scheduling from drafting/sending/CRM-write autonomy. This is a good Fable
  lane: automation ladder judgment, dry-run proof thresholds, pivot triggers,
  and sales-objective tradeoffs from a staged source packet.
- 2026-07-09 - HSD action-operator architecture decision (task_type=docs):
  PASS attempt 1, 472s. Fable handled a harder autonomy architecture brief
  with staged repo, Strong Setup, prior Ringer artifacts, and source excerpts,
  returning a BUILD_ACTION_OPERATOR verdict plus a concrete 50-action budget,
  executor/receipt design, and Level 4 release ladder. Keep using Fable for
  owner-level workflow architecture when the source packet is staged locally
  and the validator forces action definitions, caps, gates, and proof runs.

## Claude Sonnet 4.5 via OpenRouter/OpenCode (`engine: claude-or`)

- 2026-07-09 - Atlanta public-refetch canary (task_type=probe): tightened
  replay PASS attempt 1 in 72.5s. The worker retrieved the live Georgia
  Optometric Association page, used a shell-derived timestamp, and recorded the
  exact Georgia Vision Professionals / Walmart / July 1, 2026 passage; an
  independent checker re-fetched the page and matched the quote. The looser
  first canary also passed but selected an unrelated listing and used an
  inaccurate timestamp, which the tightened contract corrected.
- Linux containment warning: the active direct OpenCode engine has no OS-level
  write sandbox and the worker wrote `/tmp/page_fetch.html` despite a
  task-directory-only prompt. Use staged public-only sources, prohibit temp
  files, scrub scratch/log data, and do not use this lane for PHI, credentials,
  or private client data until a Linux sandbox is proven.

## gpt-5.6-terra (Codex CLI)

- 2026-07-09 - Atlanta continuation de novo, reserve-conflict, and fresh-field
  branches (task_type=research): all 3 Ringer tasks PASS on attempt 1. De novo
  used 170,553 tokens / 653.5s and publicly exhausted all three included sites;
  reserve used 209,228 / 572.6s and exhausted all five named conflicts without
  promoting one; the field survey used 262,006 / 564.7s and challenged Town
  Creek, 132 Gateway, and GVP while preserving the exact board as a research
  queue. Strong lane for exhaustive source-class matrices and conflict
  preservation. Each worker needed internal deterministic repair loops, so the
  first Ringer attempt should not be read as a one-draft pass.

- 2026-07-09 - Explicit-route research probe (task_type=probe): PASS attempt 1,
  61s, 49,792 tokens at high reasoning. The worker log confirmed
  `model: gpt-5.6-terra`; it followed the two-file transcript contract and
  distinguished current direct-source status from stale aggregator summaries.
  Route Codex models through `engine_args` with `-m gpt-5.6-terra`; do not also
  set the manifest `model` field because the Codex engine template has no
  `{model}` placeholder and Ringer correctly refuses the silent-ignore risk.
- 2026-07-09 - Atlanta expansion live verifier plus red team
  (task_type=research): PASS attempt 1, 506s, 238,468 tokens at high reasoning.
  Terra re-fetched a 48-row extracted ledger, added two genuinely disconfirming
  rows, returned 14 verified / 4 rejected / 32 needs-source, ran two adversarial
  searches against each of 13 decision rows, and correctly returned REVISE.
  Strong lane: live source verification, source-family independence checks,
  and conflict-preserving red team. Earlier de novo refresh missed a mechanical
  dated-receipt count after two attempts; a bounded no-browse repair passed on
  its first attempt without changing conclusions. Keep deterministic receipt
  counts explicit in the worker spec/check.

- 2026-07-16 (fit-battery admin rebuild, code-feature): 738-line React admin page restructured to tabbed workspace with debounced autosave - passed on attempt 2 (attempt 1 failed the executed check, retry with check output fixed it). Full check: npm ci+tsc+vitest+next build in worktree. Good fit for the hardest UI lane; patch was surgically within ownership.

## gpt-5.6-sol (Codex CLI)

- 2026-07-09 - Atlanta acquisition and target-location continuation
  (task_type=research): both Ringer tasks PASS on attempt 1. Acquisition used
  320,143 tokens / 975.6s, leaving GVP support-ready for a different-model
  check and Scott/EyeContact public-exhausted. Location used 338,124 / 1,456.1s
  to produce 80 receipts, 26 physical nodes, 13 route rows, six cards, and four
  comparable OSRM route-time targets; Town Creek and 92 Auburn correctly kept
  blank time bands. The location validator exposed two checker defects during
  the run: `urlparse().path` dropped OSRM semicolon destinations into `.params`,
  and an 8-decimal parser rejected 12-decimal ArcGIS coordinates while a
  negated centroid sentence triggered the positive rule. After fixing the
  validator, the same artifacts passed live re-fetch and arithmetic replay.

- 2026-07-09 - Atlanta acquisition refresh (task_type=research): PASS attempt 2,
  1,025s and 466,622 tokens total at high reasoning. The useful result was a
  current public practice-status map with seller-willingness boundaries, but it
  needed one retry under the structured output check.
- 2026-07-09 - Evidence extraction (task_type=research): PASS attempt 1, 922s,
  139,758 tokens at high reasoning. Produced a parseable 48-row ledger and
  55-row catalog; its own fresh-context reviewer caught and narrowed five
  overbroad decision rows before finish. Good structured-extraction lane when
  source authority and status rules are explicit.
- 2026-07-09 - Ultra chief conflict resolution (task_type=research): PASS
  attempt 1, 1,778s, 264,644 tokens using `gpt-5.6-sol` with
  `model_reasoning_effort=ultra`. It preserved Terra's ledger statuses, resolved
  every named conflict once, produced the exact provisional 3+3 board, and
  passed the deterministic final contract. Root fresh-context QA still found a
  judgment overreach: the narrative ranked all acquisition checks before de
  novo even though only AQ-1 was verified. Corrected output is AQ-1 first, then
  a mixed evidence-gap queue. Use Sol-ultra for bounded conflict synthesis, but
  keep an independent evidence-floor reviewer outside its structural validator.
- 2026-07-17 - MyBCAT Social RQ2 incident (task_type=code-review/code-fix):
  Terra's root-cause review passed attempt 1 and correctly separated tracked
  runtime-state mutation from source drift. The first repair's product diff and
  focused tests were correct, but the Ringer run failed twice because the
  orchestrator checker labeled an impossible alert-state payload as valid. A
  zero-model closure passed after deriving the fixture from `src.alerting`.
  Fresh report-only review then found two real proof/edge gaps: `py_compile`
  wrote bytecode into a read-only source checkout, and `datetime.fromisoformat`
  accepted date-only values outside the writer contract. Redirecting pycache,
  disabling pytest cache writes, and a bounded Terra correction produced 19
  passing tests / 55 subtests; the final fresh review returned PASS. Lesson:
  audit checker fixtures against actual writers, make read-only gates truly
  write-free, and keep review -> correction -> fresh-review until the verdict
  is clean instead of trusting a worker's own green summary.

## Cohere North Mini Code via OpenCode (`openrouter/cohere/north-mini-code:free`)

- 2026-07-10 - Short mechanical route-normalizer audition
  (task_type=code-feature): the first run passed a four-case check on attempt 1,
  but orchestrator artifact review found it silently accepted a non-string
  `model` value that the spec required it to reject. After strengthening the
  validator to eight executable cases and rerunning from a clean task directory,
  attempt 1 failed and the retry passed all cases. Clean-log result is 2 tasks,
  50% first-try, 100% final, $0. Verdict: probation only; do not promote until a
  third comparable strict task passes first try and the aggregate reaches the
  3-task / 0.67 first-try floor.

## kimi-k3 via opencode (`openrouter/moonshotai/kimi-k3`)

- 2026-07-17 - insurance-verification vendor research (task_type=research):
  the provider returned 429 rate-limit errors on both Ringer attempts before
  any artifact was written. This is an availability failure, not a research
  quality verdict. Do not route a time-sensitive single-lane job to Kimi K3
  without a current availability probe and an explicit fallback lane.
- 2026-07-16: site-build audition for a fictional optical landing page. PASS
  on attempt 2 after 3,345s total. Raw OpenRouter step-finish cost fields
  totaled $2.2853 across both attempts; Ringer's aggregate token field stayed
  blank for this lane. Attempt 1 produced a substantial artifact
  and reached a green self-run validator, but exceeded the 1,800s deadline
  while continuing visual QA. The retry found and fixed a real blur-transition
  defect at the desktop fold, then passed the executed contract: six semantic
  sections, 20 CSS custom properties, accessibility and navigation assertions,
  and independent Chrome renders at 1440x1000 and 390x844. Human screenshot
  review found a distinctive editorial optical system, strong hierarchy, clean
  responsive stacking, and no generic card-grid look; the diagram labels are
  too small on mobile. Verdict: probation for bounded visual concepting only.
  Completion discipline is poor (0% first-try, nearly 56 minutes), so use a
  tighter brief and explicit stop-after-green instruction before assigning
  time-critical or load-bearing frontend work.
- 2026-07-17: bounded code-review, source-grounded research, and technical-docs
  audition through `opencode`. All three executable checks ended green. Code
  review passed attempt 1 in 369s at $0.2733 and found all three seeded defects
  with correct line evidence. Research passed attempt 1 in 139s at $0.1903,
  calculated the 13-point / 30.95% lift and $1,740 directional margin correctly,
  and preserved the assignment confound. Docs passed only on attempt 2 in 966s
  at $0.4152: attempt 1 self-corrected two format misses and reached a green
  local check, then failed to exit before the 900s deadline; the retry reused
  the artifact and exited cleanly. Human review overrode the docs green because
  its batch example asserted `"valid": true` for `/other` even though the frozen
  contract never defined batch validity criteria. Raw provider-reported cost was
  $0.878759 total. Logged tools stayed inside the disposable task directories,
  and the Ringer repo was unchanged by the workers. Verdict: probation for
  bounded code review and fixed-packet research; do not promote docs, site-build,
  time-critical, or load-bearing work until comparable first-try evidence and
  clean stop discipline accumulate.

## kimi-k2.7 via opencode (`openrouter/moonshotai/kimi-k2.7-code`)

- 2026-07-06 — adversarial pre-merge review (aicred spark): passed on
  attempt 1, ~83k tokens. First real outing; promising for review work.
  (Ran through an ad-hoc copy of the opencode engine block — the per-task
  `model` field now makes that unnecessary.)

## kimi-k2.6 (`moonshotai/kimi-k2.6`, subject-model evidence via OpenRouter)

- 2026-07-07 — Benchmark Suite 2.0 operator eval, killed by Jon at ~4.5h.
  Serving throughput, not model quality, was the failure: on the Brick
  1000-piece case (reasoning xhigh, pinned provider order
  inceptron→decart→baidu→modelrun, no fallbacks) K2.6 averaged ~21 tok/s
  with two ~19-min stalls at 4.5 tok/s — 136+ min unfinished vs Sonnet 5's
  25 min (94 tok/s) and GPT-5.5's 24 min (55 tok/s) on the identical case.
  Model behavior itself was fine: 28 turns (fewer than Sonnet's 82), 170k
  output tokens (in family norms), 12% reasoning, zero API errors. Verdict:
  do NOT schedule K2.6 for long agentic work through that provider set;
  if K2.6 data is ever wanted, probe a single case against other providers
  first. Distinct model from k2.7-code above — don't transfer this verdict
  to k2.7.


## grok-build (Grok CLI engine, flat plan)

- 2026-07-06 — first outing (elsas-website demo), engine added same day:
  audition PASS attempt 1 in 28.9s. Then: asset harvest (11 images, live URL
  re-fetch check), books page, 5 work-page routes in one task (59 verbatim
  needles), adversarial code review (10 real findings incl. an unshelled 404
  and a broken embedded link), press/media fix batch, audio-player integration
  across 15 pages — ALL attempt 1 (player's red ledger entry was a check bug,
  artifact certified). Fast, precise on mechanical/code work. No token counts
  in JSON output (flat plan) — cost reads "included in plan".

## grok-composer-2.5-fast (Grok CLI engine, flat plan)

- 2026-07-06 — first outing (elsas-website demo): audition PASS attempt 1
  (138s — slower than grok-build but the strongest copy of the round).
  Accessibility constitution (14 testable criteria, SC-numbered) attempt 1;
  a11y-gatekeeper harness (axe+Playwright, light/dark, reduced-motion assert)
  attempt 2 — attempt 1's harness mishandled Next's default /404 route.
  Events/faq/contact fix batch attempt 1, but satisfied "editorial grid" with
  an EMPTY aside landmark — axe caught it (landmark-complementary-is-top-level).
  Persona work: good. Watch for letter-of-the-spec shortcuts on layout asks.

## Direct xAI API lane (OpenCode harness)

- 2026-07-12 — corrected five-model file/tool probe: `xai/grok-4.5`,
  `xai/grok-4.20-0309-reasoning`, `xai/grok-4.20-0309-non-reasoning`,
  `xai/grok-4.3`, and `xai/grok-build-0.1` each passed on attempt 1. Every
  lane created an executable Python artifact with exact checked output.
  This proves Ringer/OpenCode tool compatibility only; keep 4.5 as the default
  and treat the other four as bounded auditions until task-specific evidence
  accumulates.
- `xai/grok-4.20-multi-agent-0309` is unavailable for Ringer tool work on the
  current account: xAI returned HTTP 400 because client-side tools require beta
  access. Do not retry until that access changes or a server-tool harness exists.
- The preceding six-lane run was invalidated by a check bug that counted
  Ringer's own `worker.log` as an unexpected model-created file. Five models
  had actually written correct artifacts, but the harness recorded false
  failures and unnecessary retries. Validators that enumerate task files must
  always allow `worker.log`.

## nemotron-3-nano-omni-30b-a3b-reasoning (via opencode, `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`)

- 2026-07-12 — LIMITED PROBATION as a text-return subagent, not a file/tool
  worker. Four probe tasks: 3/4 eventual PASS, 2/4 first-try PASS, six total
  attempts, median ~7.6s, $0 on the free route. It returned exact seeded bug
  IDs and solved the dependency schedule on attempt 1. The context-router
  lane needed a retry after returning numeric source IDs and `fork_turns=1`;
  the retry produced the exact `S1/S3/S5` + `none` payload but ignored the
  no-tools boundary and loaded an irrelevant AAC skill first. The strict
  file-writing smoke failed twice: it printed the exact JSON but never used
  the write tool, so no artifact existed. The seven recorded model steps
  consumed 310,693 model-reported tokens total: 238,325 input tokens plus
  69,632 cached-input tokens, for only 357 output tokens and $0. Each fresh
  OpenCode attempt carried about 43k input tokens before producing a few
  dozen output tokens. Route only bounded, read-only, text-return tasks with
  checker and retry; do not make it the default Codex child, file editor, or
  tool-using worker. Free dollars are not the same as low token/context burn.

## nemotron-3-ultra-550b-a55b (via opencode, `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`)

- 2026-07-15 — PROBATION for tightly specified mechanical one-file work.
  First-try PASS in 34.7s at $0 on a checked Python normalizer: the model used
  the write tool, ran valid and invalid cases itself, stayed inside the
  disposable task directory, and made no MCP, skill, credential, or network
  calls. The independent check re-ran successfully and verified trimming,
  lowercasing, empty removal, dedupe, sorting, count output, non-array rejection,
  and no extra files. OpenCode's final step reported 41,520 total tokens, mostly
  context/cache, but Ringer recorded `tokens=0` because the current OpenCode
  token regex did not capture this JSON shape; treat scoreboard token telemetry
  as incomplete. Promote only to probation: tool use and short mechanical code
  are now proved once, while multi-file edits, long-context review, and complex
  repo work remain untested.

## nemotron-3-super-120b (via opencode, `openrouter/nvidia/nemotron-3-super-120b-a12b:free`)

- 2026-07-06 — AUDITION FAILED (exploration slot, $0 spent — free promo).
  Task: fresh-eyes adversarial review of a 2,650-line diff with a structured
  report contract. Failed both attempts on the same executed check: report
  had the right sections and verdict but under 3 concrete code citations —
  shallow engagement with the actual code, 212k tokens burned. Don't re-run
  this audition on long structured code review; if it gets another slot,
  try a shorter, more mechanical task first.

## llama-3.3-70b-instruct (via opencode, `openrouter/meta-llama/llama-3.3-70b-instruct:free`)

- 2026-07-06 — AUDITION FAILED (exploration slot, $0). Fresh-eyes review of
  a 4,061-line diff with a verbatim-quote citation requirement: failed the
  structured-report check both attempts. Second free-model audition to fail
  on long structured code review (after nemotron-3-super) — the exploration
  ladder now says: audition free models on SHORT mechanical tasks first;
  long-diff review is a proven-tier lane.

## Small / flash-class models

- First to choke on long conversational or multi-turn harness tasks —
  watch retry counts before scaling them into a batch (2026-07-05 focus
  group lesson).

## Process lessons (cross-model)

- 2026-07-06 — the orchestrator's CHECKS were the day's top failure source:
  three check bugs (fixture newline join, first-occurrence ordering vs the
  watchlist strip, claim-prefix split on '.' instead of ':') each produced
  a FAIL verdict on work that was actually correct — including all four
  capability-research packets at once. Every one was caught by reading raw
  logs/artifacts before blaming the model. Corollary for the scoreboard:
  recorded FAILs whose root cause was a check bug are annotated here, and
  check fixtures deserve the same review care as production code.


- 2026-07-06 — HARNESS BUG (fix in flight on feat/model-perf-log):
  Verifier.verify evaluated expect_files BEFORE running the check, so any
  check that itself creates/exports its deliverable (the worktree
  patch-export pattern) failed attempt 1 with "missing expected files" even
  when the check printed PASS. Cost 3 phantom retries in one run — and it
  poisons first_try_pass_rate, the model log's routing signal. Until the
  reorder lands on your checkout: have the WORKER write the declared
  deliverable, or don't declare check-created files in expect_files. When
  reading seeded scoreboard numbers, remember 2026-07-06 first-try rates
  are depressed by this.
- 2026-07-06 — the model log is now automatic: every attempt row carries
  model/task_type/retry; `./ringer.py models` prints the scoreboard; 81
  historical rows were seeded via scripts/backfill_model_log.py with a
  hand-authored task-type mapping. Give every manifest task a task_type or
  its evidence buckets as (untyped).

- 2026-07-06 — a three-model "bakeoff" ran every task on the engine's
  hard-coded model: task keys said glm/gpt/kimi, but the opencode engine
  block pinned glm-5.2, so one model wrote all three "competing" reviews.
  This is why the per-task `model` field exists — a bakeoff is only a
  bakeoff if the manifest, not the engine block, names the model. Verify
  with the `model` column in the run state, not the task key.
- 2026-07-06 — spawning 5-6 opencode workers simultaneously hit opencode's
  local "database is locked" (sqlite) — several instant attempt-1 failures,
  all absorbed by Ringer's retry. Cosmetic in Ringside ("sent back" at 0s) but
  wastes an attempt; consider staggering opencode spawns.
- 2026-07-06 — opencode's bash tool kills foreground commands around the
  ~2-minute mark: a 2min+ image-generation API call can never finish inline.
  Spec pattern that works: nohup the long command in the background, then
  poll for the output file in separate short commands.
- 2026-07-06 — two check-craft lessons from the same run: (1) URL-allowlist
  checks must be prefix-tolerant (workers legitimately trim slugs); (2) any
  heading-regex must tolerate numbered headings ("## 3. Type / Typography").
  Both failures looked like worker laziness until the raw logs said otherwise.
- 2026-07-06 — elsas-website demo, check-craft in BOTH directions: (1) a fixed
  800-char body floor failed a worker for faithfully converting genuinely tiny
  source posts — floor must scale with the source; (2) a citation gate treating
  every backtick as a page-quote failed honest reviewers who backticked their
  own fix-suggestions — line-scoped pair parsing + attribute-aware corpus fixed
  it; (3) needle-exception lists must be shared across ALL checks that consume
  the needle set (a needle excepted in one checker failed a task through
  another). Post-mortems ruled FOR the worker 3 times this run — read raw logs
  before blaming the model.
- 2026-07-06 — opencode sqlite "database is locked" again with just 2
  simultaneous opencode spawns (page-news + page-about-faq); retry absorbed it.

## codex (2026-07-06, bench-operator-proofing)
- 8/8 code-feature tasks passed attempt 1 across 3 rounds (worktrees mode, Python harness refactor; 108k-406k tokens/task). Specs embedded the approved architecture doc + exact file ownership; checks built fresh uv venvs and ran the full pytest suite.
- Lesson (check design, not model): all 3 post-integration bugs were invisible to the checks — a test that passed only because the worker's worktree lacked .env, a `--help`-only assertion missing a runtime importlib/sys.modules bug (py3.12 dataclasses), and bare console-script names failing outside activated venvs. Checks should exercise one real invocation from a cold shell, not just --help.

## 2026-07-11 — baldev-75-tribute (personal video job)
- GLM 5.2 (opencode): copywriting, 1/1 first-try on a 597-word emotional letter against a 14-motif executed check; also research, 1/1 first-try finding+downloading a CC-BY music bed with valid ffprobe/license check. Cheap and excellent on creative-with-hard-contract work.
- Codex CLI (unpinned): code-feature, built a full Remotion composition (timing generator, Ken Burns, audio mix, Root registration) correctly; tsc clean and preview render on attempt 1. Two runs died from EXTERNAL wrapper kills (not model failure) and one TIMEOUT verdict landed while its full render actually completed to the target path. Lesson: long-render checks belong in the worker or need bigger check timeouts; detach ringer runs (setsid) when the calling harness may kill process groups.
- gpt-image-2 high 1920x1088: 14/14 storyboard sketches first-try (~80-100s each), consistent style across independent calls with a strong shared style block. Swapped in after BOTH local Gemini keys (env + secure Gemini secret reference) proved invalid (API_KEY_INVALID on models-list probe) — nanobanana is dead machine-wide until that key rotates.

## Run modernimage-mockup (2026-07-11, site-build, 11 tasks)
- codex — 2026-07-11 — site-build (homepage + impact-report page vs 15-24-assertion content checks): 2/2 first-try. Remains the site-build lane for judgment-heavy pages.
- GLM 5.2 (opencode) — 2026-07-11 — site-build (8 SEO service/content pages, template-fill with FAQ+JSON-LD contracts): 8/8 first-try, clean design-system compliance. Promote GLM for template-fill site-build work.
- cohere/north-mini-code:free — 2026-07-11 — site-build audition (about+industries): passed checks first-try BUT retyped the Google Fonts URL instead of copying it (500;600 -> 500,600), silently breaking all fonts on one page; caught only by visual QA. Lesson: cheap models transcribe instead of copy — checks on template-copy tasks must diff invariant head lines against the template, and keep a visual pass for free-tier output.

## Run modernimage-level-of-change (2026-07-12, seo-audit, 6 tasks / 73 URLs)
- codex — 2026-07-12 — seo-audit (per-URL verdicts vs equity-guard validator): 2/2 first-try. One judgment miss: merged /contact/ into its dup_with page — mechanically rule-compliant, semantically wrong. Lesson: specs must deny-list functional pages (contact, home) from merge verdicts; validators need a semantic deny-list, not just metric thresholds.
- GLM 5.2 (opencode) — 2026-07-12 — seo-audit (cities/posts batches): 3/3 first-try, sensible briefs. Solid for structured audit work.
- kimi-k2.7-code (opencode) — 2026-07-12 — seo-audit audition (10 city pages): 1/1 first-try, precise rule-following (merged exactly the dup>0.55 subset, clean metric citations). Verdicts overridden on doctrine (downside-minimization), not correctness. Promote to probation for audit/structured-output tasks.
- Check-craft lesson: full-page 5-gram Jaccard inflates similarity on short pages (shared nav/footer) — /contact/ scored 0.756 vs an unrelated page. Future crawl checks should compare body-only text or length-normalize before letting dup thresholds authorize merges.

## Run modernimage-transition-plan (2026-07-12, docs, 8 tasks incl. critic + fix rounds)
- codex — 2026-07-12 — docs (astro-build/cutover/client-workflow specs) + adversarial completeness critic (21 real findings incl. 2 blockers, one in the orchestrator-generated redirect artifact) + 19-gap patch task vs re-verification harness: 5/5 first-try. The seeded-sweep critic pattern (forced covered-or-gapped answers on 10 classic migration killers) produced high-precision findings without padding.
- GLM 5.2 (opencode) — 2026-07-12 — docs (content-migration, seo-qa): 2/2 pass, one retry — attempt 1 wrote checklists without literal "- [ ]" markers (0 counted); check message fixed it on attempt 2. Spec-craft: show a literal example checkbox line in doc specs.
- kimi-k2.7-code (opencode) — 2026-07-12 — docs audition (access-inventory, 66 checkbox steps): 1/1 first-try, clean structure. Second consecutive clean audition (audit + docs); promote toward proven for structured docs/audit lanes.

## cohere/north-mini-code:free
- 2026-07-12 research (practice-os-approach-research): FAIL 2/2 attempts on sourced-research task with executed check (report structure + >=6 citations). Free 256k-ctx audition; do not route research here again without new evidence.
- 2026-07-13 code-fix (finance-portal-automation, systemd units): FAIL 2/2. Task was 3 trivial static systemd files with a clear spec; model produced an EMPTY .timer, skipped the required install .md entirely, and hardcoded the scratch worktree path + a hallucinated uv binary into the .service ExecStart. Demotion: do not route even mechanical multi-file config generation here — it does not reliably produce all named output files or copy paths faithfully. Codex redo needed. Confirms the earlier "cheap models transcribe instead of copy" lesson extends to "cheap models drop whole files."

## codex (2026-07-12, practice-os-nervous-build)
- code-feature: PASS attempt 1, 7.5 min, ~107k tokens, 83/83 tests green in one shot on a 6-task TDD plan (5th first-try practice-os build today). Verified flagged interfaces itself (ledger.stream vs plan's assumed .events) and documented deviations in notes.md — spec pattern "verify these interfaces by grep before coding, code is source of truth" continues to pay for itself.

## openai/gpt-image-2
- 2026-07-13 image-gen (baldev tribute): 5/5 first-try style-match to an existing nanobanana pencil-watercolor sketch set using prompt-only style block (no reference images; script restricts --input to gpt-image-1). 1344x768 high quality, ~60-90s/image. Faces slightly more resolved than nanobanana at same prompt; acceptable for impressionistic style. Good emergency fallback when the Gemini key dies.
- code-fix addendum (2026-07-12, value-event-header-fix): PASS attempt 1, 3.8 min, ~60k tokens, clean surgical 3-file diff. Miss worth encoding: worker satisfied the spec but didn't discover the PHI log-allowlist (ALLOWED_LOG_FIELDS) that would have silently stripped the new log field in prod — reviewer caught it. Lesson: when a task adds a LOG FIELD, the spec must name the logging filter/allowlist file as in-scope, or the field dies at the filter.

## ROUTING RULE (Ankit directive, 2026-07-13)
- NEVER route Claude models (Sonnet, Haiku, Opus, any claude-*) through OpenRouter or API-credit billing. Claude models run ONLY via Claude OAuth/subscription auth (Claude Code, claude CLI, or tmux-model-workers Claude lane). OpenRouter stays fine for non-Claude models (GLM, Kimi, Seedance video, etc.).
- 2026-07-13 (fable-5-brain): persona-review via opencode: openrouter/meta-llama/llama-3.3-70b-instruct:free TIMEOUT x2 on a ~4k-char persona spec; provider endpoint rejected request with ContextOverflowError (65536 max ctx, opencode reserved 32000 output tokens). Not a quality signal; endpoint ctx too small for opencode's output reservation. Avoid this free endpoint for opencode persona lanes; rerun landed on GLM 5.2 default.
- 2026-07-13 (fable-5-brain): persona-review via opencode GLM 5.2 default: first-try PASS in 102s on a 4k-char in-character persona spec with verbatim-quote check; grounded, specific frictions. Good default for persona lanes.

## Run optometry-workflow-competitive-landscape (2026-07-13, research/docs/verification)
- Fable 5 via `claude-lean`: first-try PASS on the 18-workflow research plan; final 5k-word synthesis passed on retry for one literal phrase; bounded evidence revision passed first try. Strong chief-planner/synthesizer when supplied staged ledgers plus a strict output contract.
- gpt-5.6-terra via Codex: five deep research/repair lanes passed after validator-driven repair; three fresh-context reviews found real traceability and overclaim defects before final APPROVE. Keep Terra as the evidence-heavy research/reviewer lane.
- xAI Grok 4.5 direct: practice-operations lane passed on retry; 18-workflow disconfirmation passed on retry despite search timeouts. Good different-model falsifier, but budget for retry and outcome-diversity checks.
- Gemini 2.5 Flash exploration: failed 2/2 to complete the Lane A report/schema; its partial ledger was salvageable by Terra. Keep flash-class exploration low stakes and never make it the sole owner of a required artifact.
- Check-craft lesson: enforce both citation directions. Final claims must resolve to canonical S### entries, and every canonical index URL must exist in staged evidence. Normalize source tokens mechanically, expand ranges, distinguish `unknown` from absence, and never let a vendor-name whitespace difference create a false checker failure.

## KAT-Coder-Pro V2.5 and Hermes 3 405B Free auditions
- 2026-07-14 — `kwaipilot/kat-coder-pro-v2.5`, task_type=probe: PASS on the first no-tool attempt in 6.6s. It returned a complete 33-line Python transform, used only the allowed stdlib modules, generated exact deterministic JSON, and matched an independently computed SHA-256 digest. Usage: 288 prompt + 656 completion = 944 tokens; estimated OpenRouter cost at the observed catalog rates was $0.00215488. Promote only to probation for tightly specified code generation. Its OpenCode/tool route failed before model action with an upstream server error and no files, so do not count that lane as a model-quality failure; tool-driven repo work remains unproven.
- 2026-07-14 — `nousresearch/hermes-3-llama-3.1-405b:free`, task_type=probe: no quality verdict. OpenCode first failed because the Venice free endpoint exposed no tool-capable route; the corrected no-tool lane then exhausted provider-aware retries on persistent upstream 429s. Re-audition only when the free endpoint is available, and use the no-tool lane unless provider capabilities change.
- 2026-07-15 research/framework-writing (engineering-economy ring): zai-coding-plan/glm-5.2 via opencode PASSED first-try on a data-free 1,682-word framework deliverable with a 7-term/4-section/20-bullet executed check; ~102s. Containment clean (no MCP calls, no repo reads; spec-echo only match in log). Good lane fit: structured non-personal writing with strong validators.
- 2026-07-15 code-review (cvc-sms-recall-lane ring): openrouter/cohere/north-mini-code:free FAILED 2/2 attempts on adversarial plan review. Substance was genuinely good (real findings, cited spec lines) but it bolded/headered the required plain-text labels (## Finding:, **Evidence:**) both attempts, even though the retry prompt carried the check's exact label failures. Lesson: north-mini cannot hold a plain-label output contract under markdown habit; do not audition it on report-contract lanes, and add an explicit FORMAT REMINDER line to specs when any free-tier model writes label-validated reports. Lane re-run on zai-coding-plan/glm-5.2.

## openrouter/meta-llama/llama-3.3-70b-instruct:free
- 2026-07-16 (code-fix, Astro meta-description task, 3 owned files, seo-ahrefs-loop): both attempts died with provider ContextOverflowError — endpoint caps at 65,536 tokens and the request hit ~74k (33.9k text input + 8.2k tool input + 32k output reservation). Catalog says 131k ctx but the free endpoint enforces 64k with a 32k output reservation. Not viable for repo code-fix tasks that read multiple source files; at most micro-tasks with a single small file and short spec. Demoted from repo-fix auditions; task reassigned to gpt-5.6-terra.
- 2026-07-16 (docs/content-remediation, mybcat blog backlog b1r): gpt-5.6-terra 7/7 first-try, 61-82k tok, 148-203s per post vs earlier same-day b1 batch where 7 of 10 lanes failed under box saturation (load ~77-92 from D-state pileup). Same specs/checks — failures were environment, not model. Verify box health before blaming the model.

## process lessons (2026-07-16, harness-cleaner-rollout rounds B/B2/C)
- Codex timeout pattern: 3 of 6 parallel lanes hit 2400s x2 walls when specs implied
  per-file enumeration over ~190-dir catalogs. Fix that worked: lead the spec with
  "TIME DISCIPLINE: write ONE bulk-measurement script in your first 3 actions" -
  relaunched lanes finished in 132-234s (20-35x faster). Bake this into any spec
  that audits large file trees.
- codex-oauth.sh auth guard transiently failed all lanes in 0.1s ("blocked ambiguous
  provider...") right after a session restart; `codex login status` was fine seconds
  later. On instant whole-run failure, check auth status and relaunch before debugging
  manifests.
- Adversarial verify round earns its cost: 2 verify lanes refuted 3 applied-cleanup
  claims (unregistered check, residual backups, divergent dangerous duplicate) that
  the generator lanes' own checks could not see. Verify-what-you-applied is a
  distinct lane from check-what-you-generated.

## claude-fable (orchestrator lane note)
- 2026-07-17 automation-discovery ingest: codex workers in a staging-lane manifest whose workdir contained the shared corpus.db wrote the DB directly (bulk scratch rows, cross-source status clobbering, self-run Stage2/3 tables) despite an explicit staging override. Executed checks stayed green because they validated staged files only. Lesson: keep shared state files OUTSIDE the manifest workdir; sandbox workspace-write = the whole workdir is writable.

## opencode / GLM (model_default GLM-5.2)
- 2026-07-17 copywriting (hsd-outreach-drafts, draft-darion): PASS first try on mechanics BUT fabricated a personal detail ("dialed into the review from your car") present nowhere in source packet or live thread; caught only by downstream live-thread judge. Lesson: for copywriting from context packets, GLM needs an explicit no-color-details clause AND a check that flags personal-anecdote patterns; do not promote for context-grounded client copy yet.

## claude-fable (local-shell edit lane)
- 2026-07-17 top-five-priorities: three local-shell edit+verify tasks total. whoop visibility fix PASS first try. seo chronology fix (144h->36h) applied correctly but its executed check rightly FAILED, exposing a second masked bug (HubSpot form label with a literal question mark tripping the CRM sanitizer charset). Third task fixed that (test-arbitrated: only email-rejection is asserted by the repo suite) and went green through the full chain incl. a real service run. One checker defect along the way (unittest package import vs plain test dir) - classified per playbook, checker fixed, no wasted model pass. Lesson: run the exact test invocation the repo supports before baking it into a check.

- 2026-07-17 ob-sync lane: probe-first pattern paid off twice. (1) Assumed-dead 403 credential was actually healthy - one cheap probe task prevented a pointless credential rotation. (2) receipts "auth failure" was really a client-side acceptance contract rejecting server dedup echoes; live tracing through the module (scrubber -> capture -> acceptance) beat log reading. Codex code-feature task (statedb source, 176s) passed first try with a credential-less dry-run check.

- 2026-07-17 glm-coding-plan / research (UI-UX design concepts): 6/6 first-try PASS on structural-validator checks, fast (~48-490s), calm well-structured markdown. One artifact leaked a 2-char non-English phrase (minor). Solid cheap pick for verified design-ideation swarms.

- 2026-07-17 glm-coding-plan / code-review (UI component adversarial review): 3/3 first-try PASS. Three independent reviewers (a11y, interaction, design+integration) CONVERGED on the same real defects (focus trap, IME guard, contrast, subsequence noise) — high signal-to-noise, cited file+line evidence, correct WCAG math. Excellent cheap pick for parallel component review.

- 2026-07-17 codex (gpt-5.6-terra) / code-review (pre-merge QA of 6-surface UI PR, 2040-line diff): 3/3 first-try PASS, ~71-94s, ~55-64k tokens each. Found 5 real P1 blockers (stale component state across rerender, faked ARIA tabs, unhandled promise rejection, false-affordance buttons, arbitrary z-index) with precise file:line evidence and correct fixes; low false-positive rate. Strong pre-merge QA reviewer; no OB-capture leak observed under contained read-only spec.
