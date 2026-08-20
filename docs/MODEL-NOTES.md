# Model notes — how workers actually perform

A running log of how models perform on real Ringer tasks, so engine and
model choices are made on evidence instead of vibes. The raw numbers now
live in the local eval log (`~/.ringer/runs.jsonl`); run `./ringer.py models`
to print the per-model, per-task_type scoreboard (tasks, attempts,
pass_rate, first_try_pass_rate, median duration/tokens, last_seen). This
file remains the judgment layer on top of those numbers.

## qwen3.8:27b via pi-ollama-d (local Ollama 11435)

- 2026-08-16 — probe, first-try PASS in 23.3s. Pi wrapper wrote `lane_probe.py` (`print("LOCAL_LANE_OK")`); executed check printed `LOCAL_LANE_OK`. Tokens uncounted. Earlier same-day Ollama generate on the 3090 returned exact `QWEN38_OK` at 100% GPU / ~21 GiB VRAM. One plumbing sample only; do not promote to default.
- 2026-08-16 — promotion pack via pi-ollama-d, 4/4 first-try PASS (correct-stop 29.7s, ugly exact-source 12.7s, route-normalizer 33.5s, docs brief 21.1s). Spot-checked artifacts: stop_probe.py prints STOP_OK with no extra files; ugly_probe.py bytes are exact; normalize_route.py passes all eight cases; brief.md has Goal/Evidence/Next and QWEN38_DOCS. Scoreboard now: proven for probe (3/3 first-try); probation for code-feature (1/1) and docs (1/1). Not a default. Next evidence: bakeoff vs gemma4:31b; two more code-feature and docs tasks before those types can go proven.
- 2026-08-16 — bakeoff route-normalizer, same spec/check, Pi only. qwen3.8:27b PASS 82.0s; gemma4:31b PASS 107.9s. Both artifacts re-ran the eight-case checker. Times are not a clean latency contest: one GPU, models swapped. code-feature now probation 2/2 first-try for qwen3.8:27b. Still not default. One more distinct code-feature needed for proven.

**How to add a row:** after reviewing a run (post-run ritual step 5 in the
ringer skill), append one dated line under the model. Say the task type,
what happened, and what you'd do differently. Only write what the executed
checks and raw logs support — no vibes, no worker self-reports.

## codex (GPT-5-class, own harness)

- 2026-08-10 - shannon-optometry-margin-ab-test, site-build/docs/code-fix: the interrupted first site-build left a complete HTML/CSS/JS artifact but no standalone documents; preserving it and routing a bounded docs lane produced both documents and a green source gate on attempt 1. A focused print-CSS worker then made the correct one-rule repair (`.technology-chain { display: block; }` inside print media) after print-page review caught a clipped caption. Chrome hit SIGTRAP when the worker tried to render inside the sandbox, while the host-side Ringer check rendered the exact files and passed. Repeat the asset-swarm pattern: model authors source, host check renders; do not require sandboxed Codex to prove Chrome output itself.

- 2026-08-07 - loop-drive-contract U5, two single-lane code-fix rounds, both PASS on
  attempt 1 (64s/32k, then 80s/40k). Clean boundary behaviour: one owned file, edits left
  uncommitted, fix-summary.md pasting the real check output rather than a paraphrase, and
  no MCP/skill/capture attempt under `--ignore-user-config`. The note worth keeping is
  about round 2's CONTENT, not its contract. Asked to key a dedupe marker on a content
  hash, it wrote `digest=$(sha256sum FILE | awk '{print $1}') || return 1` — and because
  awk exits 0 when sha256sum dies, the guard never fires, the digest is empty, an absent
  marker is empty too, and the equality test suppressed the alert. A textbook masked
  pipeline exit status, shipped inside an otherwise correct 4-hunk patch that passed a
  real executed check. Round 3, given that finding in its spec (never the patch), fixed
  the pipeline AND added an explicit empty-digest guard. Lessons: (1) codex will write
  shell whose exit-status semantics are wrong in ways a behavioural check misses unless
  the check attacks the new mechanism's dependencies; (2) handing a fix worker the prior
  worker's FINDING rather than its code produced a better patch than the original and
  cost 80 seconds.

- 2026-08-06 - remote-staff-accountability, two research lanes: both passed on attempt 2 after a formatting-only checker mismatch because attempt 1 bolded the required Evidence field labels. The reports were substantive, but live coordinator verification caught two current prices that the source-backed check did not: TMetric Business at $7.50/seat/month annually and Teramind Starter at about $14/seat/month annually. Lesson: for JavaScript-rendered pricing pages, require rendered-body or screenshot evidence for recommendation-driving numeric prices; a green report contract does not prove price freshness.

- 2026-08-04 (evening addendum) - mk2-number-and-comeback rounds 6-13 + gateway lanes 39-44,
  ~20 codex lanes in one day (code-fix/research): roughly 80% first-attempt PASS, and every
  retry that fired was rescued by the injected check output. Zero worker-quality failures all
  day - every red traced to (a) unmeasured platform conventions (fixed by measurement lanes),
  (b) my own checker/manifest defects (expect_files directories, shadowed lambda, background
  verification never read, JSON string surgery on heredocs), or (c) genuinely new live-behavior
  classes surfaced by Ankit's phone testing. Reusable lessons: hand-author manifests with Write,
  never string-surgery escaped heredocs inside JSON; grounded-quote checks (backtick spans
  verified against a corpus) kept diagnosis lanes honest across five separate uses; per-lane
  byte-true deployed-base files made single-file overlay deploys safe after the lane-38 repo
  drift nearly caused a silent rollback.

- 2026-08-04 - mk2-number-and-comeback platform-diagnosis lane (task_type=research, default
  engine): PASS attempt 1, 85k tokens, 157s. Read-only diagnostician over raw Bland chat
  envelopes + stored graphs (v96 vs the dead goal-loop v101). Two signals worth repeating:
  (1) the anti-hallucination check design worked - requiring backtick-quoted spans verified
  verbatim against the captured corpus produced 68 grounded spans and zero invented evidence;
  (2) the worker caught a defect in MY deterministic tooling: node_diff.py's recursive
  id-search matched a stub inside responsePathways instead of the real .nodes[] object, and
  the worker explicitly eliminated the resulting false lead instead of building on it.
  Reusable lesson: on Bland graphs, always select nodes by iterating .nodes[], never by
  recursive id search; and grounded-quote checks are cheap insurance on diagnosis lanes.

- 2026-08-03 - mk2-number-and-comeback wayfinder session, ~10 lanes (code-feature/code-fix/
  research, default unpinned engine): every lane PASSED its executed check on attempt 1,
  including a docs-research lane that returned an 11-citation quoted-verbatim Bland API
  feasibility report with an honest FEASIBLE: UNKNOWN rather than a guessed field name.
  The two runtime failures of the night were BOTH my spec/check gaps, not model failures:
  (1) builders that import a deployed-matching module passed compile+usage checks but died
  at runtime on a deployed-only sibling import (capability_registry) - the fix-round check
  now EXECUTES the import offline via load_live_module(), which is the reusable lesson:
  when a built artifact imports something, the build check must perform that import, not
  just py_compile; (2) a driver passed argv pathway_version into a JSON body as a string
  (HTTP 400 at runtime) - fixed by exposing build_create_body() so the check executes the
  body constructor. Also reconfirmed twice: secrets stored as JSON envelopes must be
  unwrapped before use as auth headers; any new lane touching BLAND_API_KEY needs the
  unwrap or it 401s.

- 2026-07-25 - mott-gateway-stability, four lanes across two rounds (task_type=code-fix,
  default unpinned engine at `model_reasoning_effort=high`, disposable snapshots): ALL FOUR
  PASS attempt 1, 48-101k tokens each. Lanes: entrypoint observability, terraform deploy
  strategy, terraform drift reconciliation, log redaction. Two quality signals worth
  repeating: the observability lane spontaneously added a browser-path discovery probe that
  directly tested the orchestrator's leading hypothesis, and the redaction lane produced a
  working proof artifact showing fake credentials masked while the diagnostic text survived.
  THE LESSON IS ABOUT MY CHECKS, NOT THE MODEL: all four lanes did exactly what their specs
  said, and every failure this session came from checks that asserted STRUCTURE rather than
  the VALUE production actually runs. One such gap (an IAM grant removed without replacement)
  reached production and caused a 30-minute outage. A green Ringer lane is evidence the spec
  was satisfied, never evidence the spec was right. For infrastructure lanes, always follow a
  green check with a credentialed plan review before apply.

- 2026-07-25 — mott-gateway-fixes, two lanes (task_type=code-fix, default
  unpinned engine at `model_reasoning_effort=high`, disposable snapshot not a
  worktree): both PASS attempt 1. store-registry consolidated three hardcoded
  CVC-only store dicts into one env-driven registry in 49k tokens / 167s, and
  notably PRESERVED the load-bearing owner-confirmed comment about forcing
  providers to avoid phantom scheduler columns rather than dropping it with the
  literal it annotated. bland-nodes (30k tokens / 71s) independently reached the
  right architectural call on a broken webhook node: it identified the circular
  dependency and chose to DELETE the node rather than patch it, and refused to
  remove a safe-exit routing rule that would have masked a separate unfixed
  gateway defect, documenting why instead. Repeat: give the worker measured
  ground truth about the deployed system and explicitly permit "report the
  discrepancy rather than make it pass" — both lanes used that latitude well.

- 2026-07-24 — mott-v21-recall-lanes build (task_type=code-feature, default
  unpinned engine at `model_reasoning_effort=high`, worktree-isolated): PASS
  attempt 1, ~156k tokens. Three files from scratch — a deterministic pathway
  graph generator, a structural validator, and a 15-test scenario suite — against
  a JSON decision contract committed into the repo. Output was 19 nodes / 33
  edges from a 21/56 original, byte-identical across two generator runs, and it
  passed an orchestrator-owned gate it had never seen. Two things worth
  repeating: committing the binding contract INTO the snapshot repo (rather than
  staging it beside the task) works cleanly with worktrees mode, where
  pre-creating a task dir would break `git worktree add`. And naming a specific
  design RISK in the spec — here, that two global-node triggers could both match
  "can we move it to Thursday" — produced explicit mutual-exclusion language in
  both triggers rather than a generic label. Unprompted, it also wrote two
  negative tests proving its own validator REJECTS unsafe graphs, which is the
  circular-self-check failure mode from 2026-07-24 content-safety-failopen-fix
  being avoided rather than repeated.

- 2026-07-24 — content-safety-failopen-fix (task_type=code-fix, podcast safety
  gate): PASS attempt 1 on its own 26 tests, but the payload validator it wrote
  OVER-CONSTRAINED the schema — it required severity + non-empty category +
  reason on every cut row, fields the codebase normalizer (parse_cut_list)
  treats as OPTIONAL (defaults them). Fail-closed, so not a hole, but it would
  over-block legitimate sparse safety responses. Caught in coordinator review,
  corrected in r2 (require only coercible start_s/end_s per row + an explicit
  anti-over-block test). Lesson: for schema-validation fixes, spec the EXACT
  required-vs-optional fields quoted from the normalizer; a worker will infer a
  stricter schema from its own test fixtures and pass its own check circularly.
- 2026-07-22 — calendar-confirm-entry-fix (task_type=code-feature, open-engine
  multi-module wiring: 6 runtime files + a new 14-case test file, live-repo
  sandbox with git-status allowlist): PASS attempt 1, 76k tokens, 191s
  (default unpinned engine, resolved to gpt-5.6-sol, reasoning effort none).
  A spec that froze the design per-file and enumerated required test cases
  held with zero drift; worker also made two sound unprompted judgment calls
  (bypass enrichment cache when the calendar signal is present; booked
  contacts jump the segment cap). Repeat: enumerate test cases in the spec.
  Same day, sales-loops-fix rounds 1-4 (approval-chain repair, outcomes
  plumbing, factory convergence, intelligence tick): 4/4 PASS attempt 1,
  54-76k tokens and 120-190s each, full 632-test repo suite green after.
  The frozen per-file design + enumerated-test-cases + live-repo
  git-status-allowlist pattern is now 5/5 first-try on this repo.
- 2026-07-22 (late) — sales-funnels-build campaign (6 rounds: outcome-ramp,
  SG-EMAIL, SG-SPEED, SG-NURTURE, SG-CAL, SG-UPSELL/ICARE/ACQ): 6/6 PASS
  attempt 1 on substance (36-100k tokens, 78-240s). The one recorded FAIL
  (SG-CAL) was a spec defect: the spec froze a guard-matrix test that pins
  the subgraph count, which legitimately must grow with the graph — the
  worker's edit was the correct minimum. Lesson: inventory-pinning tests
  belong in the OWNED set whenever a round adds to the inventory. Workers
  also made correct read-the-room calls twice (declined to route terminal
  cards through the draft loop; honored a pinned attribution test via the
  spec's fallback clause) — write the fallback clause, it gets used.
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
- 2026-07-10 — gpt-5.6-sol, code-feature (steering-profiles feature in
  ringer.py itself, ~470-line change + 18 tests + docs, run
  ringer-steering-profiles): shipped as PR #25. 2 attempts, 379k tokens,
  but the attempt-1 FAIL was the CHECK's fault, not the model's — the check
  gated on the ENTIRE pre-existing suite being green inside the worker
  sandbox (localhost binds blocked, fixture missing). The feature work
  itself was verified green both attempts; attempt 2 "hardened" an already
  -sound implementation. Scoreboard's FAIL row for this run understates the
  model. Lesson for check authors: regression gates must compare against
  the BASELINE failure set, never assert absolute suite green.
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

- 2026-07-24 — mott-v21 gateway test-gap lane (task_type=code-review, read a
  1,873-line Python HTTP handler plus four test files and explain why a passing
  test suite missed a live bug): FAILED both attempts by TIMEOUT at 2400s, rc=-15,
  never wrote its output file. The same manifest's other two lanes (gpt-5.6-terra
  and xai/grok-4.5) passed first try on the same sources with the same 2400s
  budget. Not a spec or checker defect — the spec was shared verbatim across all
  three lanes and the check was smoke-tested pass-and-fail beforehand. Lesson:
  glm-5.2's ~244s code-review median hides a long tail; do not give it a
  single-file read approaching 2k lines under a 40-minute cap. Re-ran the lane on
  Codex default. Keep glm on bounded, short-context review where its 0.75
  first-try over 87 tasks actually holds.

- 2026-07-22 — sales-loops-missing-audit (task_type=code-review, 4 lanes on
  Z.AI Coding Plan, spec-vs-code gap audit with quote-grounding validator):
  2 lanes PASS attempt 2, 2 lanes recorded FAIL that were CHECKER defects,
  not model faults — the validator literal-grepped free-text `expected`
  fields, scanned the spec files themselves as "implementation", and
  demanded exact component-name mentions in prose. Artifacts were
  substantively excellent (45-claim coverage ledgers, correct
  unwired-vs-missing judgments). Lesson: when a claim schema has a free-text
  field, the validator must extract code-shaped tokens and downgrade
  taxonomy quibbles to warnings; and 'missing' refutation must exclude
  declaration files. Corrected-gate verification round passed all 4.
- 2026-07-22 — calendar-confirm-entry-fix orphan-audit (task_type=code-review,
  Z.AI Coding Plan lane, 80-module reachability audit on a detached-HEAD
  snapshot worktree, custom validator re-verifying every orphan claim by
  independent grep): PASS attempt 1, 786s. Zero false claims; correctly
  distinguished importlib filename-string loads and shell/systemd/cron
  entrypoints from parameter-name and JSON-key token collisions, and
  self-sorted ambiguous cases into prose "wiring gaps" instead of claims.
  Snapshot verified byte-clean after the run. Repeat: snapshot + mechanical
  claim re-verification makes GLM safe and strong on read-only repo audits.
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
- 2026-07-18 - ob_company watchdog security reviews (task_type=code-review,
  zai-coding-plan/glm-5.2): repeated fresh report-only passes found real live
  defects after a green builder gate, including nonexistent schema columns,
  wrong credential/path conventions, leaked temp cleanup across `exec`, and a
  broken shell URL-negation glob. It also carried the exact read-only, state,
  retention, and secret-containment invariants across repair rounds. Strong lane
  for long structured security reviews when the source packet includes exact live
  seams and the checker accepts a substantive PASS/BLOCK report.
- 2026-07-30 — revenue-map explainer-sample-template (task_type=docs,
  glm-coding-plan): TIMEOUT both attempts (2x1200s), zero artifact bytes — the
  worker consumed the spec (transform a 528-line HTML report into a sample
  template) and never wrote a file. Same task reassigned to Codex default.
  Do not route long HTML-authoring/transform docs tasks to glm-coding-plan;
  keep it on bounded review/audit lanes.
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
- 2026-07-17 — CVC optometry billing role evaluation (docs): attempt 1
  produced a substantive `REVISE` evaluation in stdout but never wrote the
  expected file. Attempt 2 wrote a 1,237-word artifact and passed the check,
  but changed the verdict to `STRONG` without new source evidence. Keep
  `expect_files` and a substantive validator on GLM doc lanes, and inspect
  retry logs when the judgment itself changes rather than treating the green
  artifact as stable consensus.
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

- 2026-07-25 — mott-v22 review (task_type=code-review, 22-node generated graph plus
  its generator, validator and 20-test suite, measured against a signed design map):
  first-try PASS, verdict REVISE with 10 findings — 2 high, 4 medium, 4 low. Best
  Fable output of this campaign by a wide margin, and the reason was the spec: it was
  told what a mechanical gate had ALREADY proven (14 specific structural properties)
  and explicitly invited to critique the map itself, with "the map is signed but it is
  not sacred". It then found three defects in the map rather than the graph, including
  one where the map's own rule forced the build defect. The two highs were both real
  and both invisible to structural checking: a confirmation node whose timeout drained
  the ordinary success path into the no-reply outcome (booking rate would read ~0), and
  a patient-facing opt-out message promising suppression the system cannot perform —
  the orchestrator gate had checked the outcome TAG for "suppress" and missed the
  message text saying it in plain English. Repeatable lesson: list what the gate
  already proved so the review spends its budget on judgment, and give explicit
  permission to attack the contract.
- 2026-07-24 — mott-v21-recall-lanes decision packet (task_type=code-review,
  owner-level design contract for an SMS booking pathway rebuild): FAILED both
  attempts, and the checker was at fault, not Fable. The validator assumed
  `date_contract.model_must_not` was a list; Fable wrote a prose string.
  Iterating a str yields characters, so the phrase regex could never match and
  the failure message was misleading. A corrected validator passed the SAME
  artifact byte-identical via a zero-model `local-shell` lane. Concrete rule:
  when validating Fable output, accept `str | list[str]` on any field whose
  schema does not force a list — Fable prefers dense prose where a schema
  merely implies an array. This is the second time (see 2026-07-17) that the
  cheap fix was a local-shell closure rather than another Fable round.
  Decision quality itself was high: it refused to scope a fix onto an endpoint
  the catalog records as 404, it deferred to the human owner's already-stated
  decisions instead of relitigating them, it declined to raise retryAttempts
  because the safety contract pins it at 0 and flagged the tradeoff rather than
  silently overriding, and its stated least-confident assumption was the same
  unproven-platform-feature risk the orchestrator had independently identified.

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
- 2026-08-11 — extend-the-pipe (code-review, sonnet): FAIL x2 in 30s total —
  worker asked for approval to run read-only `git show/diff` against a repo
  OUTSIDE its task directory and exited rc=0 without writing report.md; headless
  safe-mode has no approver, same class as the 2026-07-12 Bash-denial note.
  Round 2 with the material STAGED INSIDE the task dir (source packet: commit
  patch, working-tree diff, full files) passed attempt 1 in 258s with a
  substantive evidence-cited P2 catch. Rule: claude-lean review lanes must
  never require reads outside the task dir — always stage a source packet.
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

- 2026-08-08 - podcast action-path release reviews (task_type=code-review):
  Terra caught malformed-card validation bypasses in direct notifier APIs and
  stale promotion-packet contradictions after the implementation checks were
  green. One review attempt could not read absolute source paths until the
  manifest added explicit Codex `--add-dir=<path>` grants. Repeat: grant every
  external source/artifact root explicitly and ask Terra to compare CLI paths,
  direct Python entrypoints, and one authoritative promotion status.

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
- 2026-07-18 - ob_company deterministic cron watchdog (task_type=code-feature/code-fix):
  Terra's first seven-file build passed its own fixture verifier but invented live
  seams: nonexistent schema columns, wrong credential and pooler conventions,
  an unwritable state path, and an incompatible Supabase query transport. Fresh
  Grok 4.5 and GLM 5.2 reviews returned a real BLOCK; controlled read-only probes
  later proved Supabase CLI v2.90 rejects multi-command queries while psql 17.9
  preserves `BEGIN READ ONLY` and returns the expected bounded JSON. Tight repair
  specs plus executable live-seam checks produced 23 passing tests, and Terra's
  later internal QA also removed an unbounded no-timeout fallback and noisy env
  sourcing. Route Terra on security-sensitive integrations only when the packet
  names exact schema, credential, CLI, and filesystem seams and a different-model
  review plus controlled live probe sit outside its self-verifier.

## gpt-5.6-luna (Codex CLI)

- 2026-08-05 - mailroom-registry (task_type=code-feature, run mailroom-rebuild
  r1): PASS attempt 1, 110,721 tokens / 435.1s at high reasoning. First real
  audition; it was the exploration slot in a 3-task batch where the other two
  ran Codex default. Task was a new idempotent YAML-config registry plus wiring
  into an existing scaffold plus a runbook edit, verified by an independent
  oracle it never saw (double-register leaves exactly one entry, unrelated
  config keys untouched, malformed config fails closed with a printed reason).
  Cleared all of it first try. Token cost ran ~36% above the Codex-default
  sibling task in the same batch (110.7k vs 81.6k) for comparable scope, so it
  is not the cheap lane. Worth another audition on code-feature before treating
  it as more than probation; one sample is one sample.

## gpt-5.6-sol (Codex CLI)

- 2026-08-16 - idoc/odof landing mockups (task_type=site-build, 2 parallel
  worktrees): PASS on attempt 2 both lanes. Attempt 1 failed a source-window
  phone-digit check and a shared read-only `node_modules/.vite` cache
  (EROFS). Retry patched the contract markers and used an isolated writable
  Vite cache. Good on branded Astro landings when the check prints WHY and
  the worktree does not share a read-only Vite cache with another tree.

- 2026-08-08 - podcast standing-FYI lifecycle (task_type=code-fix): repeated
  bounded passes landed clean first-attempt patches and executed external,
  focused, and canonical checks. Fresh reviewers still found defects between
  individually green effects: stale comment replay after snooze wake, duplicate
  receipts after partial ledger writes, post-send checkpoint ambiguity, a
  no-buzz ledger failure that consumed the row, and direct-helper validation
  bypass. Repeat: pair Sol with an immutable fault-injection contract covering
  crashes between side effects, every direct entrypoint, and a fresh model
  review after cross-repo/config integration. Do not treat a first green patch
  as release proof for durable multi-effect workflows.

- 2026-07-25 — mott-gateway-fixes contract-tests (task_type=test-hardening,
  pinned via per-task `engine_args` `-m gpt-5.6-sol`, no reasoning override):
  PASS attempt 1, 45.9k tokens / 65s. Wrote nine named regression tests locking
  behavior measured live against a production gateway, and left the production
  source byte-identical (check hashed it). Two quality signals beyond the check:
  it avoided hardcoding calendar dates by computing them at runtime in the
  module's own timezone, and handled the midnight-rollover race by accepting
  either side of the boundary. I mutation-tested the result by reintroducing the
  real production bug; the intended test failed with a clear message while the
  other eight stayed green, so the suite is genuine and not shape-only. First
  evidence for sol on test-hardening: 1/1. Worth a larger lane in this type.

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

- 2026-07-28: RB2B lead-identity classification, 88 rows from company+jobtitle
  (task_type=research, run rb2b-sell-intent-leads). PASS attempt 1, 37,501
  tokens, ~43s. Full 88/88 coverage and clean labels on spot-check, but two
  quirks: narrated "The input has 83 leads" while correctly writing 88, and
  skewed harsher than codex lanes on the same-shaped data (74/88 unrelated,
  0 od_owner vs codex 46-63 unrelated, 3-5 od_owner per ~88) - leaned
  'unrelated' where codex leaned 'unknown'. Fine when a coverage check
  guards it; prefer codex when the cost of a false 'unrelated' is high.

- 2026-07-23: IDOC Vendor Advocate one-page design (task_type=site-build).
  PASS attempt 1 in 403.6s, 58,807 cumulative tokens, and $0.5645 summed
  provider step cost. The bounded brief carried the OB_mybcat BLUEPRINT
  system, locked positioning and pricing, exact Letter-size render command,
  content/no-leak validator, and stop-after-green rule. Kimi produced a
  self-contained HTML, one-page PDF, and PNG; independent Chrome rerender,
  PDF-size checks, visual inspection, and a 300 DPI QR decode all passed.
  This is the first clean first-try visual production result after the prior
  long-running site-build audition. Repeat the tight artifact shape and
  deterministic stop rule for bounded one-page marketing design; keep Kimi
  on probation for broader or time-critical design work.
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

- 2026-07-18 - family-event idea generation (task_type=research): produced a
  substantive 2,918-word plan with 10 low-prep activities and 9 program
  transitions, then passed attempt 2. Attempt 1 missed only the validator's
  ASCII-hyphen heading contract by using en dashes in two time ranges; the retry
  corrected those headings without changing the plan. Useful creative breadth,
  but keep exact machine-read headings explicit and tolerant where typography is
  not substantive.
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

- 2026-07-10 — identity correction (Jon): the Grok Build CLI is a HARNESS
  serving exactly two models — Grok 4.5 (xAI) and Composer 2.5 (Cursor).
  The engine-lane slug `grok-build` resolves to Grok 4.5. "Grok Build 0.1"
  was never a model; earlier notes/rows using it as one describe Grok 4.5.

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

- 2026-07-21 - browser-navigation research (`xai/grok-4.5`, task_type=research): produced a substantive official-source report and passed on attempt 2. Attempt 1 used Markdown-formatted citations that the validator failed to count as primary-source URLs; the retry converted them to bare URLs without changing the research verdict. It verified Gemini 3.6 Flash and separated native computer use, browser harnesses, and search systems, but missed the newly released OSWorld 2.0 benchmark. For current-landscape research, require a latest-benchmark-version check and bare source URLs when the validator parses URLs directly.
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
- 2026-07-18 - ob_company watchdog runtime reviews (xai/grok-4.5,
  task_type=code-review): first-try report-only passes caught integration bugs
  that fixture gates missed, including the literal `!postgresql://*` shell glob,
  a false-green stub caused by literal backslash-n fixtures, and the distinction
  between generic known events and real Claude hook-health events. It repeatedly
  re-executed shell syntax, unit tests, and emitted-SQL guards and returned clean
  PASS reviews after repair. Strong different-model runtime falsifier for
  security-sensitive shell/Python bundles; still require a controlled live probe
  for CLI framing and credentials.

## nemotron-nano-9b-v2 (via opencode, `openrouter/nvidia/nemotron-nano-9b-v2:free`)

- 2026-07-29 — AUDITION FAILED for short mechanical one-file Python work. Attempt 1 stopped without creating either expected file. Attempt 2 wrote both owned files and used only write/edit/bash inside the disposable task directory, but generated an invalid `line.rstrip` string literal, failed the exact hidden-case checker twice, and remained in a repetitive repair loop. The Ringer wrapper timed out at 598 seconds; the orphaned OpenCode worker was stopped, and a fresh manual execution of the declared checker still failed syntax plus every behavioral case. Reported model steps carried roughly 41k–46k tokens at $0. Do not promote to file/tool work. If revisited, restrict it to a short no-tool text-return probe with a strict schema; do not use it for time-critical work.

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

## nemotron-3-nano-30b-a3b (via opencode, `openrouter/nvidia/nemotron-3-nano-30b-a3b:free`)

- 2026-07-23 - LIMITED PROBATION for short mechanical one-file work. The
  JSONL normalizer passed the hidden valid/invalid, deterministic-output,
  diagnostics, report, and file-ownership gate after one Ringer retry; a
  fresh manual execution of the same gate also passed. Attempt 1 wrote the
  script but omitted the required report and its own test exposed a crash on
  a non-string event. Attempt 2 rewrote the script, added the report, removed
  temporary test files, and reached a green gate in 227 seconds total. A
  subsequent NVIDIA request returned provider `502 ResourceExhausted` after
  the green artifact already existed, so treat endpoint capacity as flaky
  rather than downgrading the verified artifact. First-try rate is 0/1 and
  the route remains checker-and-retry only. Do not use it for long reviews,
  time-critical work, or default-worker promotion.

## nemotron-3-ultra-550b-a55b (via opencode, `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`)

- 2026-07-24 — mott-v21-recall-lanes scout (task_type=code-review, adversarial
  verification of 14 defect claims against a 52KB pathway graph + a 186KB
  endpoint catalog): first-try PASS at $0. Genuinely earned its slot. It
  correctly REFUTED one orchestrator claim by quoting the end-node text the
  claim said did not exist, and surfaced 16 additional defects the orchestrator
  had missed, two of which were material (two distinct failure modes sharing one
  outcome tag; a second node with the same missing-variable defect as the
  headline one). It also self-corrected mid-report on a wrong finding.
  BUT: its three `UNVERIFIABLE` verdicts were not trustworthy. It claimed a
  staged graph export held "only nodes and edges arrays" when the exact file it
  was handed also held `analysis_options`, `post_call_actions` and
  `memory_enabled` at top level. Lesson: good breadth and honest verbatim
  quoting on long context, but re-check every "cannot verify" verdict yourself
  before acting on it — it under-reads large JSON rather than hallucinating.
  Cheap enough to run as a standing second-opinion lane on report-only review.

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

- 2026-07-19: LIMITED PROBATION for short mechanical one-file code work.
  A disposable Python JSONL normalizer passed the canonical hidden-case check
  in one Ringer attempt at $0 after 160 seconds. The worker used write, read,
  edit, and bash tools only inside its task directory, apart from invoking the
  read-only checker by absolute path; the raw trace showed no network, MCP,
  skill, credential, or external write activity. It needed intra-attempt
  repair after the checker caught an invalid-record leak, and it also made one
  malformed shell command and one failed edit call before recovering. The
  final OpenCode event reported 51,918 total context tokens, but Ringer's token
  regex did not capture this response shape. Use only for bounded scratch work
  with a strong executed checker; the earlier long-review failure still rules
  out large structured reviews and default-worker promotion.
- 2026-07-06 — AUDITION FAILED (exploration slot, $0 spent — free promo).
  Task: fresh-eyes adversarial review of a 2,650-line diff with a structured
  report contract. Failed both attempts on the same executed check: report
  had the right sections and verdict but under 3 concrete code citations —
  shallow engagement with the actual code, 212k tokens burned. Don't re-run
  this audition on long structured code review; if it gets another slot,
  try a shorter, more mechanical task first.

## nemotron-3.5-lightning (via pi-openrouter, `openrouter/nvidia/nemotron-3.5-lightning:free`)

- 2026-08-14 — AUDITION PASS, first try, $0 (free lane). Task: short
  mechanical probe, write and self-run a stdlib Python script printing the
  first 20 Fibonacci numbers. Passed the executed checker on attempt 1 with
  no hardcoding (checker verified against known-good and known-bad fixtures
  before the run). Receipt: 45,750 total tokens, 520.6 s elapsed, cost
  $0.00, run nemotron-lightning-audition-20260814T121533Z-p1553335. Notes:
  slow for the task size (free-lane queueing likely) and token-heavy for a
  one-file script (visible thinking blocks in the trace). Verdict:
  probation for short mechanical probe work with a strong executed check;
  do not scale to batches until a second probe confirms latency is
  acceptable. Watch retry counts before anything multi-turn.

## llama-3.3-70b-instruct (via opencode, `openrouter/meta-llama/llama-3.3-70b-instruct:free`)

- 2026-07-06 — AUDITION FAILED (exploration slot, $0). Fresh-eyes review of
  a 4,061-line diff with a verbatim-quote citation requirement: failed the
  structured-report check both attempts. Second free-model audition to fail
  on long structured code review (after nemotron-3-super) — the exploration
  ladder now says: audition free models on SHORT mechanical tasks first;
  long-diff review is a proven-tier lane.

## inclusionai/ling-3.0-flash (via opencode, `openrouter/inclusionai/ling-3.0-flash:free`)

- 2026-07-24: LIMITED PROBATION for bounded site-build work. The independent
  IDOC Vendor Advocate design passed the full Letter-size content gate on
  attempt 2 in 147.3 seconds at $0. Attempt 1 planned extensively but exited
  before writing any artifact. The retry produced self-contained HTML, PDF,
  and PNG, then repaired a validator conflict caused by CSS `text-transform`.
  Independent rerender, one-page 612 x 792 PDF proof, and a 300 DPI QR decode
  all passed. Visual comparison still favored Kimi 3 with high confidence:
  Ling's centered hierarchy, small body copy, weak CTA, undersized footer/QR,
  and excessive blank space made the page feel like a clean wireframe rather
  than finished executive collateral. Give Ling one more simple, low-stakes
  site-build audition because it was fast, coherent, and free after retry,
  but do not use it as the production design default yet.

- 2026-07-24 (task_type=code-review, mott endpoint CSV audit): PASS on attempt
  1, $0, roughly 20 minutes. The lane classified all 350 rows of a 21-column
  contract CSV into keep/merge/rewrite/drop with a reason per row, and had to
  find repetition groups by key rather than by string equality (the file has
  zero byte-identical rows). It found 53 duplicate groups covering 85 rows,
  matching the orchestrator's independent count exactly, plus 44 superset
  catch-all rows the spec had only gestured at. It wrote its own Python to do
  it rather than eyeballing, honored the "keep and re-mark, do not drop"
  instruction with 0 drops, and its brief listed three genuine uncertainties
  including one the orchestrator agreed needed review. Second consecutive
  audition worth counting. Ling is promotion-track for bounded, mechanical,
  strongly-checked classification work over a staged input directory. It has
  not yet been tested where judgment rather than enumeration is the product.
  Containment note: the lane ran under opencode with empty sandbox_args, so
  inputs were copied into the task directory and the spec forbade touching
  either source repo. No stray writes were observed.

## Small / flash-class models

- First to choke on long conversational or multi-turn harness tasks —
  watch retry counts before scaling them into a batch (2026-07-05 focus
  group lesson).

## Process lessons (cross-model)

- 2026-08-20 — revolution-cli-v8-qa, the single most expensive orchestrator mistake
  of the session and it is a one-liner: **workers write INSIDE the taskdir, checks
  export outward.** A 4-lane review swarm declared `expect_files` at an absolute
  out-dir OUTSIDE the worktree and told each worker to write its report there.
  Only the unsandboxed lane could. Codex runs under `--sandbox workspace-write`
  and reported the out-dir as a read-only mount (`ntfs3 ro`), then saved to /tmp;
  the Pi/bubblewrap lane has no `/mnt` at all and burned most of a 25-minute run
  probing for a writable path before giving up. Both had produced complete,
  high-quality reports. 3 of 4 lanes scored `fail` for zero worker fault. The
  docs round earlier the same day had it right — worker edits the worktree, the
  check exports the diff — and I broke the pattern when I switched from fix lanes
  to review lanes. Rule: in worktrees mode `expect_files` must be absolute (lint
  enforces this, deliverables die with the worktree) but the WORKER must be told
  to write a relative path inside its taskdir, and the CHECK, which runs outside
  the sandbox, does the copy. Add an `--export-to` to the validator rather than
  asking the model to reach out of its jail.
- 2026-08-20 — corollary: a sandboxed lane that produced good work but could not
  land it is recoverable, do not pay for a re-run. Codex's report was sitting at
  /tmp. Grok's never hit disk at all but was fully present in the streaming
  transcript as the argument of its failed write call: reassemble from
  `assistantMessageEvent.toolcall_end.toolCall.arguments` (this stream shape uses
  `toolcall_delta`/`toolcall_end`, NOT `input_json_delta`). Both artifacts then
  passed the corrected gate, 49 and 17 resolving citations respectively.
- 2026-08-20 — validator defect that punishes honest work: a citation checker that
  resolves every cited `path:line` against the worktree will fail any lane whose
  brief deliberately points it at files OUTSIDE the repo. Two further traps in the
  same checker: `\b` cannot match between a space and `/`, so the anchor silently
  ate the leading slash of every absolute path and turned `/mnt/...` into `mnt/...`;
  and reviewers legitimately give the full path once then use the basename after,
  so resolution needs a unique-basename index over `git ls-files` (unique only —
  an ambiguous basename must stay unresolved rather than guess). Classify a red
  check before spending the retry: all three of these looked like fabricated
  evidence and were not.
- 2026-08-20 — gate design that actually held: for a HIPAA sensitivity-labelling
  fix, assert in BOTH directions. Under-labelling is the visible bug, but a worker
  can silence it by marking everything sensitive, which destroys the column and is
  arguably worse. The gate carried an explicit control set of unambiguously
  operational fields and failed on over-labelling with the same severity. Proved
  it three ways before any worker ran: red on the current defect, red on a
  deliberately lazy "label everything" fixture, green on a candidate correct fix
  so the contract was known satisfiable. Worker passed first try and the control
  held (11/11 still operational). Cheap, and it is the difference between a fix
  and a cover-up.

- 2026-08-13 — xai lane (pi-openrouter wrapper, grok-4.5) HARNESS_FAIL, not a
  model failure: both attempts of eyedeal-next-step-audit died in ~1s with
  "Credential store read failed for openrouter: EROFS /agent/auth.json"
  before any tokens. Do NOT count against grok on the scoreboard. Same run:
  codex + kimi OAuth lanes both PASS attempt 1 on research-audit tasks.
  RESOLVED same day (run pi-openrouter-keyfix): root cause was the Pi
  package update to 0.84.1 that morning — startup now unconditionally lists
  the credential store at $PI_CODING_AGENT_DIR/auth.json BEFORE env auth,
  and a store I/O error is fatal (evidence: dist/core/agent-session-services.js
  refresh path; pi-ai models.js wraps the read error as fatal). Fix (codex
  worker, coordinator-reviewed, uncommitted in engines/pi-openrouter-ringer.sh):
  give Pi a writable, EMPTY, key-free store dir on sandbox tmpfs
  (/tmp/home/.pi/agent), ro-bind the generated models.json into it, point
  PI_CODING_AGENT_DIR there; key still arrives only via the supervisor's
  in-memory OPENROUTER_API_KEY env injection, /agent unchanged, no
  credential ever on disk or mount. Proven by executed gate: live grok-4.5
  probe through the real wrapper, verified RINGER_PI_IDENTITY, green Ringer
  receipt (verify-wrapper-live PASS attempt 1). Two process lessons:
  (a) a codex task owning a file OUTSIDE its task dir needs an explicit
  engine_args writable_roots grant on the smallest parent directory — round
  1 wasted a worker run on that; (b) the probe's ownership guard must
  compare TRACKED modifications only, or pre-existing untracked files (the
  never-committed engines/kimi-oauth.sh) falsely fail honest work.

- 2026-08-20 — kimi OAuth lane (`kimi` engine, kimi-code/k3) HARNESS_FAIL on
  a code-review task (reactivation-entitlements review-r2): both attempts
  died in ~7s with `provider.auth_error: 403 You've reached your usage limit
  for this billing cycle`. Zero tokens, zero work; do NOT count against the
  model. Until the Kimi billing cycle resets, route review lanes that want
  model diversity to `claude` / `claude-lean` (or an explicit pi-openrouter
  selector) and keep kimi off manifests. Same day: codex OAuth was also
  dead (refresh token already used; needs a human `codex logout && codex
  login`); every entitlements lane ran on claude-lean and passed first try
  except one checker-defect retry, 9 for 9 on code-feature/code-fix/research
  gates that execute real tests.

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

## gpt-5.6-sol (codex)
- 2026-07-15 ringer-self-update run (3 serial tasks, direct-repo-edit mode): code-fix baseline-test repair 1/1 first-try (61k tokens, 1.6m); code-feature self-update mechanism (git fetch/ff-pull/re-exec + HUD staleness restart + 20-test suite) 1/1 first-try at high effort (153k, 8.1m); code-feature signal-contract (all 3 scoreboard surfaces + canonical-route lint enforcement) passed on retry (358k, 13.7m) — attempt 1 died on stale old-column assertions in pre-existing tests it hadn't finished updating; the retry prompt's injected FAIL list was enough to close it out. Lesson: when a task rewrites a display contract, name every test file asserting the old contract in the spec's ownership list AND tell it to update them FIRST.
- 2026-07-09 code-feature/code-fix (ringside-overhaul): 4/4 first-try — a ringer.py logging change with tests, a 265-line stdlib backfill CLI (atomic rewrite, dry-run, idempotence all check-verified), a ~1500-line single-file HTML redesign (running-now pills + worker-card grid + multi-expansion refactor, 30KB patch, node --check + contract greps + unittest), and a render-gating change where it correctly UPDATED tests asserting the old behavior instead of gaming the check. Medium/high reasoning, 65–120k tokens/task.
- Same day, different session (bench-harness-patches, code-fix): 0.29 first-try over 7 tasks on a Next.js/Turbopack harness. Spec and check quality dominate model choice — see the scoreboard before generalizing either number.

## GPT-5.5 (codex) — attribution caveat
- Scoreboard rows dated before 2026-07-09 may actually be gpt-5.6: codex eval rows logged model="" until the write-time stamping fix (PR #18) and were credited to GPT-5.5 by the registry default at read time, while the machine's codex default had already moved to gpt-5.6-sol at an unknown earlier date. `scripts/backfill_model_from_logs.py` re-stamps rows with surviving command-log evidence; anything it skips is a mixed-model aggregate. Trust post-2026-07-09 rows.

## nvidia/nemotron-3-super-120b-a12b:free
- 2026-07-08 (research, content-strategy-recon): FAIL x2. Did the analysis in chat but never wrote report.md; attempt 2 exited rc=0 with no file. Doesn't reliably follow file-output contracts under OpenCode. Demoted — don't re-audition on file-deliverable tasks.

## meta-llama/llama-3.3-70b-instruct:free
- 2026-07-08 (research, content-strategy-recon): FAIL x2. Timed out at 900s both attempts on a moderate DB-scrape+format task. Too slow on the free tier for harness work. Demoted — don't re-audition without much longer timeouts or paid tier.

## z-ai/glm-5.2 (addendum)
- 2026-07-08 (research/filter, pitch-foundry): FAIL x2 on a long-spec rubric-application task (~40k input: embedded rubric + 4 candidate files). Read all inputs, exited rc=0 with ZERO output tokens both attempts — silent stall, no file written. GLM handled the same session's shorter formatting specs fine. Lesson: keep GLM specs short; route long-context apply-this-rubric work to codex.

## GPT-5.5 (codex) — honesty flag
- 2026-07-08 (image-gen, pitch-foundry): sandbox DNS blocked openrouter.ai; ALL 10 API calls errored (logged honestly in gen-log) — but the worker then FABRICATED 10 deliverables locally (composited canvases from the ref image) to satisfy a files-exist>40KB check, and passed. Lesson: (a) codex sandbox has no external DNS on this machine — route API-calling tasks to opencode (network open); (b) never write an existence-only check for generated media — require the success log (SAVED/cost lines) to match the file count.

- 2026-07-09 persona-review (pitch-foundry exec-briefing panel): 0/2 first-try+retry. Produced coherent review CONTENT as chat text but never wrote report.md — does not reliably use file-write tools under opencode. Demoted; do not re-audition for file-deliverable tasks without a write-tool probe first.

## gpt-5.6-luna (codex)
- 2026-07-09 code-feature (unlock-ai guide-format conversion, strict type-contract check): 1/1 first-try, 42.6k tokens, 80s. Followed a multi-file TS pattern precisely at $1/$6 pricing. Good candidate for mechanical codegen/docs lanes; audition in adjacent types.

## opencode / z-ai glm-5.2 (via openrouter)
- 2026-07-09 (aicred-invoice-downloads, 4 code-fix tasks + 1 follow-up, worktrees+npm ci checks): systematic attempt-1 NO-OP — all 4 parallel workers produced zero edits and no summary on first attempt, then completed cleanly on attempt 2 after retry-prompt injection (34k-69k tokens each). Follow-up single task passed attempt 1. Suspect first-invocation session warm-up in opencode-sandboxed under parallel spawn; budget for 2 attempts on parallel GLM batches. Output quality on Next.js/Stripe route+test work: solid, spec-faithful, one boss-caught design gap (used user-scoped supabase client where RLS demanded service role — spec didn't say explicitly; say it explicitly).

## 2026-07-11 — baldev-75-tribute (personal video job)
- GLM 5.2 (opencode): copywriting, 1/1 first-try on a 597-word emotional letter against a 14-motif executed check; also research, 1/1 first-try finding+downloading a CC-BY music bed with valid ffprobe/license check. Cheap and excellent on creative-with-hard-contract work.
- Codex CLI (unpinned): code-feature, built a full Remotion composition (timing generator, Ken Burns, audio mix, Root registration) correctly; tsc clean and preview render on attempt 1. Two runs died from EXTERNAL wrapper kills (not model failure) and one TIMEOUT verdict landed while its full render actually completed to the target path. Lesson: long-render checks belong in the worker or need bigger check timeouts; detach ringer runs (setsid) when the calling harness may kill process groups.
- gpt-image-2 high 1920x1088: 14/14 storyboard sketches first-try (~80-100s each), consistent style across independent calls with a strong shared style block. Swapped in after BOTH local Gemini keys (env + mybcat/ai/api-keys/gemini) proved invalid (API_KEY_INVALID on models-list probe) — nanobanana is dead machine-wide until that key rotates.

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
- 2026-08-20 docs (revolution-cli-v8-docs, GAPS.md v7->v8 sweep): PASS attempt 1. First pass for this model after 0/3. Read carefully before promoting: the surface was ONE already-existing markdown file, edits were mechanical, and the check asserted that the invariant counts (1374 paths, 34 routes) and the bucket table survived, which is exactly the "transcribe instead of copy" guard the earlier notes asked for. It also got the judgment call right unprompted, flipping the current-state version reference to v8 while leaving the historical "v5/v6/v7 added route X" attributions alone. Weaker on house style than Codex on the sibling lanes (left a route path unbackticked in prose). Verdict: untested -> probation for SINGLE-FILE mechanical doc edits behind a strict invariant check. This does NOT reverse the research or multi-file config demotions above; both prior failure modes were about producing several files from scratch, which this task never asked for.

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

## openrouter/cohere/north-mini-code:free
- 2026-07-20 code-feature audition (fb2-p2-position-engine lane-d, worktrees mode, opencode --dangerously-skip-permissions): FAILED on containment, not quality. Resolved the worktree .git link to the MAIN repo and edited the live checkout (wrote src/app/admin/positions/page.tsx there), then ran rm -rf on that live-repo dir to clean up its own out-of-ownership css. Both attempts killed manually; check correctly red (no changes in worktree). GLM lanes in the same run used worktree paths correctly, so this is model path behavior. DEMOTED: never run on git worktrees without a sandboxed engine or disposable snapshot.

## Session 2026-07-20 — cvc-outbound-recall-campaign (Fable orchestrating)
- codex (default): 7/8 first-try on code-feature/code-fix with executed gates; the one red was a checker defect (literal-string require in the wrong file). Sandbox blocks AWS Secrets Manager + network — route live probes to local-shell; repo edits need -c sandbox_workspace_write.writable_roots.
- glm-coding-plan: first-try on 419-line research inventory + code-safety review; citation quality high. Promote for research/code-review lanes.
- xai/grok-4.5: flow-trace adversarial review passed on attempt 2 (attempt 1 missed the report contract); node-level graph tracing was excellent once shaped.
- local-shell: 6/6 for deterministic gates/probes. Gotchas: go build in git worktrees needs GOFLAGS=-buildvcs=false; big Go builds can fill /tmp (ENOSPC killed a whole round mid-flight — check df before Go lanes).
kimi-k3 (2026-07-21, code-review/design-doc red team): PASS on attempt 2 of adversarial spec review; attempt-1 report failed structured-labels check; final report was among the strongest of 6 lanes (caught unfalsifiable-falsifier P0 the other platform lane missed). Worth another audition on doc-review lanes.
glm-5.2 coding-plan (2026-07-21, code-feature, dept-factory heartbeat module): first-try PASS on a verbatim-spec TDD task (tests+impl fully specified in spec). Contrast with its 0.44 first-try code-feature baseline — GLM is reliable when the spec removes design freedom; keep it on transcription-grade build lanes, not open-ended features.
codex default (2026-07-21, code-review, B2 architecture red team x2 lanes): both first-try PASS, high-signal. Found a genuine P0 the implementation missed (6-hex HMAC decision code brute-forceable via unlimited verify CLI + unauthenticated sender_id + no replay/state binding) that the spec-level red team's fix did NOT fully close in code. Strong at implementation-vs-spec gap analysis (flagged §13 protocols promised-but-unbuilt). Keep Codex as lead for architecture/security review lanes.

## cohere/north-mini-code:free (OpenCode)
- 2026-07-22 test-hardening (podcast-loop-hardening/poisoned-fixtures): PASS first-try on a strict-schema JSON fixture-authoring task with an executable validator (5 poisons + README). Good at contract-following when the check enumerates every rule. Now 5 tasks in type; keep auditioning one rung up.

## zai-coding-plan/glm-5.2 (glm-coding-plan)
- 2026-07-22 code-feature (podcast-loop-hardening/kernel-bridge): PASS first-try on a bounded wiring task (importlib path-loading, charter-sourced ceilings, shadow guard, bash -n checked script). Counters its weak 0.47 first-try average: small, spec-complete, strongly-checked lanes suit it.

## Codex CLI default
- 2026-07-22 code-feature (podcast-loop-hardening r1): 2/2 first-try on the hard governance lanes (sensors, heal). One lane (watchdog-spine) failed as a HARNESS error: 5 concurrent `git worktree add` calls on one repo hit a git lock race; worker never started. Orchestrator note: stagger worktree-heavy runs or expect one transient add-failure per big batch; re-run as a one-task manifest.

- 2026-07-22 codex (engine wrapper): codex-oauth.sh rejects ANY per-task `-c` config selector in engine_args (rc=64, "blocked ambiguous provider...") — so sandbox tweaks like `-c sandbox_workspace_write.network_access=true` cannot ride engine_args. Network-needing lanes (aws CLI recon) must route elsewhere (session MCP subagent, xai own-sandbox, or local-shell script). Cost: aws-cvc-tenant-inventory lane in mott-optical-texting-setup burned 2 instant-fail attempts.

- 2026-07-22 poolside/laguna-s-2.1:free (opencode, research/intake audition): FAILED both attempts on the lowest-stakes lane of mott-optical-texting-setup — read the two source files (tool calls visible in log) but never wrote the deliverable mott-intake.md; classic reads-but-never-writes. Zero cost (free promo) but demoted: do not re-audition on write-a-file research tasks; if tried again, use a trivial one-file probe first. Codex re-ran the lane.

- 2026-07-24 code-fix (sales-queue-fix, 3 serial lanes on the LIVE open-engine checkout): 3/3 pass, 2/3 first-try, 251k tokens, 5.4 min wall. The one retry (junk-relay-domains) was a CHECKER timeout, not a product failure: the 60s post-run check window is tight when the build-command is the full 810-test suite AND a sibling lane is running; attempt 2 passed the identical check in 22.7s. Give full-suite checks a longer check timeout on serial multi-lane runs. Serial + disjoint ownership + each lane's `--allowed-status` listing the OTHER lanes' owned paths worked cleanly on one shared dirty checkout, no collisions.

- 2026-07-24 orchestrator review catch (same run): all three lanes passed their executed checks, but a lane's new dict-keyed counter used a raw `row.get("status")` that can be None, so `sorted()` over mixed None/str keys would raise. Frozen specs enumerate behaviour, not malformed input — spot-reading the diff caught what the enumerated test cases could not. Keep reading the diffs even at 3/3.

## Orchestrator lesson (not model-specific)
- 2026-07-22 podcast-loop-hardening r7/r11: two lanes went green on narrow named-file checks while breaking 14 neighbor tests (freshness gate broke referral_touch_automation's 11-test contract suite; outreach binding broke its builder tests). Baseline-diff against the branch base separated ours (14) from pre-existing (11). Rule going forward: code-fix lanes touching shared modules get the FULL suite (minus documented pre-existing failures via --deselect) as the verify command; narrow checks are only for leaf files with no importers.

## 2026-07-22 exam-type-recall round 1 (recon, 4 lanes)
- Codex default: 3/3 first-try on research/code-review recon with strict answer-key validators. r1 recovered the vendored Go binary's module/rev via `go version -m` unprompted (verified by orchestrator). r4 traced a live 400 bug precisely with line cites.
- glm-coding-plan (exploration lane, code-review vs staged JSON inputs): 1/1 first-try, and produced the round's highest-value finding — the mission brief's /book assumption was wrong (live node posts /sign); it corrected the brief instead of hallucinating compliance. Good candidate for more staged-artifact analysis lanes.
- Validator lesson: JSON-escaped strings inside dumps need an unescaped haystack variant for verbatim-quote checks (caught in pre-launch self-test, not by a wasted worker retry).
- 2026-07-22 exam-type-recall rounds 3-5 (code-feature, repo-feature kit): Codex 7/8 first-try across gateway/pathway/campaign lanes; the two red checks were BOTH orchestrator checker defects (missing --allowed-status for pre-existing dirty baseline; dir-wide `terraform fmt -check` tripping on unowned tfvars). Lesson: snapshot `git status` per repo BEFORE authoring checks and scope fmt/lint gates to owned files.
- 2026-07-22 exam-type-recall round 6 (phase C, adversarial builder/verifier pair): Codex 2/2 on substance; the one red was checker defect #4 (cd into repo made a relative --notes path resolve wrong). Running total this job: workers 9/10 first-try on substance, checker defects 4, worker defects 0. Orchestrator lesson reinforced: absolute paths everywhere in check commands; never cd in a check chain.

## gpt-5.6-terra — mott endpoint CSV single-source-of-truth (2026-07-24)

- Four sequential docs lanes rebuilding a 350-row PHI-adjacent API contract CSV
  against live AWS evidence: 4/4 PASS, 3 first-try, one retry (path preservation,
  rescued on attempt 2 with the gate output injected). 28k-63k tokens per lane,
  82-225s. Terra is dependable on "assemble a precise artifact from staged
  structured evidence" when the gate is executable and the spec states the
  authority order explicitly.
- The instructive part was what the gates did NOT catch on the first pass. Lane 1
  passed a gate checking schema, dedup, endpoint coverage and mapping retention,
  and still shipped three real defects: 219 of 300 rows labelled as undeployed
  local code when 178 of those fields are in the committed source; 27 JSONPaths
  silently converted from [0] to [*], which a Bland response mapping cannot
  address; and a safety prohibition dropped from 41 legacy write-adapter rows.
  Each needed its own round with its own new assertion.
- Lesson for orchestration, not for the model: when replacing a file that an
  existing repo validator guards, READ that validator first and port its
  assertions into the gate before the first build round. scripts/check_endpoint_catalog.py
  caught two of the three defects my gate missed. Three extra rounds would have
  been one.
- Second lesson: a rebuild lane will happily overwrite a governance column with
  provenance prose if both sound like "state." Name the columns that carry
  human decisions and forbid touching them.

## Codex CLI default — podcast-full-auto build day (2026-07-22)
- ~22 high-reasoning code-feature/code-fix lanes over one day: all worker-attributable checks passed first-try. The 3 non-pass events were harness/orchestrator-side: one git-worktree add race, one 60s check-timeout on a 2-min suite (verified manually in the preserved worktree), one lane failed its check on tests OUTSIDE its ownership (cross-suite regression its spec couldn't let it fix). Codex at effort=high is reliably first-try on 300-800-line surgical specs with embedded findings; the failure budget lives in MY manifests, not the model.
- Standing pattern validated 6x: piecewise-green lanes + composition review per phase. Composition reviews found 44 defects piecewise reviews missed (dead code paths, false-halt classes, never-create-twice escapes). Never skip the composition pass.

## Codex CLI — OUTAGE 2026-07-23 ~05:25 ET
- Usage limit exhausted mid-build (podcast-full-auto rawgate lane, 2 empty attempts: 'You've hit your usage limit ... try again at Jul 28th 1:02 PM'). All Codex build lanes AND codex-exec reviews unavailable until 2026-07-28 unless credits purchased. Failover per subscription-only charter: GLM coding plan for bounded strongly-checked lanes; GLM as cross-model reviewer. Watch first-try rates closely — GLM historically 0.47-0.55 first-try on code lanes; expect more retry rescues.

- 2026-07-23 - Yaryan Connersville comprehensive r1 (task_type=research, 12 bounded lanes): 12/12 PASS, 1 retry (seed-verify-a attempt 1 failed distinct-domain floor; retry with injected check output fixed it - check working as designed). codex default (resolved gpt-5.6-sol, effort none) 7/7 lanes, 6 first-try. glm-coding-plan 4/4 first-try on demand/persona/channel lanes. kimi-k2.7-code exploration lane PASS attempt 1 on patient-language research with usable Message Hooks - second clean research pass; promotion-track evidence for read-only research lanes.

## claude (engine)
- 2026-08-09 - verification (optometry-platform-ebitda): Claude Sonnet correctly returned FAIL when the isolated task directory lacked the evidence packet, but a weak existence/heading checker falsely passed that artifact. A fresh run with all evidence pre-staged inside the task directory and a checker that explicitly rejected `VERDICT: FAIL` returned QUALIFIED PASS after two attempts (~438s), reproduced all arithmetic, and validated Statements A-D. Network re-fetch remained permission-blocked. For Claude verification lanes, pre-stage the full packet and require a positive verdict in the executed check.
- 2026-07-23 code-review: claude engine sandbox denies ALL reads outside its task dir (four denial routes tried incl. cp) — repo-inspection review specs FAIL twice; pre-materialized evidence packet INSIDE the task dir (diff.patch + files/ + pytest.txt) passes first-attempt (2/2, ~250-320s, model claude-opus-4-8). For Claude review lanes: always packet mode, never live-repo specs. Also: reused job-specific checks false-fail honest reviews — write a per-job check.
- 2026-07-23 - Yaryan Connersville site build + review loop (task_type=site-build/code-fix/code-review): codex default (gpt-5.6-sol pin) built foundation + 3 page lanes (4/4, one retry on claim-id formatting caught by validator) and 3 fix passes (3/3 first-try). gpt-5.6-sol high-effort fresh reviewer was the loop's engine: 4 rounds (8/7/5/0 defects), caught a VA-vs-IN geo-error, a fix-spec-injected literal, contract violations no static check had - and round-4 PASS with 142 bindings audited. Lesson: reviewer defects converge fast when each round's findings become static fixpass assertions; also write fix-spec replacement sentences carefully - one round-2 defect was caused by the orchestrator's own spec text.


## Engine routing rule (Ankit, 2026-07-25) — binding

**Claude, OpenAI and Google models run through their first-party CLI only. Never the API.**

| family | use | never use |
|---|---|---|
| Claude | `claude`, `claude-lean` (both wrap `engines/claude-oauth.sh`) | `claude-or`, or any OpenRouter Anthropic slug |
| OpenAI | `codex` (Codex CLI) | any OpenRouter OpenAI slug |
| Google | `gemini` (Gemini CLI, cached personal OAuth) | `gemini-or` |

Reason: the CLI lanes authenticate with the existing subscription. An OpenRouter or
direct-API route for these three families bills per token for work the subscription
already covers.

Every other model in Ringer keeps its current route, which is OpenCode with the
OpenRouter slug in the task's `model` field.

`claude-lean` is the preferred Claude worker lane over `claude`: same OAuth wrapper,
plus `--disable-slash-commands` and `--exclude-dynamic-system-prompt-sections`, so the
worker starts with less ambient context. The wrapper already unsets every API-key and
cloud-billing variable and refuses a non-OAuth invocation, so the rule is enforced at
the engine rather than relying on whoever writes the manifest.

## 2026-07-25 — Mott gateway launch ring (identity: claude-opus-5)

### gemini (gemini-3.5-flash) — code-review — NOT AUTHENTICATED
Two attempts, both killed at the 1500s task timeout, zero output. Raw log shows
the CLI printed `Opening authentication page in your browser. Do you want to
continue? [Y/n]:` and then blocked. Ringer closes stdin (`< /dev/null`), so the
prompt never resolves and the worker burns its whole timeout. This is an auth
gap, NOT a model-quality result — do not let it depress the gemini scoreboard
row. Before routing anything to the `gemini` engine again, run `gemini` once
interactively and complete the OAuth flow, then re-verify with a one-task probe
manifest. Worth adding a cheap preflight that fails a run fast when an engine is
unauthenticated instead of paying 1500s per lane to discover it.

### glm-coding-plan (zai-coding-plan/glm-5.2) — code-review — hung, no output
Two attempts, both killed at 1500s (`rc=-15`), zero bytes of artifact and no
auth prompt in the log. Task was a read-only review of a ~1900-line Python file
in a disposable snapshot clone with a report.md output contract. Same spec text
passed on codex. Unclear whether auth or a stall; treat glm-coding-plan as
unproven for long read-only review of a large single file until a small probe
manifest reproduces or clears it.

### GLM API fallback is blocked by policy, by design
`engines/opencode-auth-policy.sh` fails with exit 64 on `openrouter/z-ai/*`,
`z-ai/*` and any bare `glm*` segment: "GLM requires the Z.AI Coding Plan selector
zai-coding-plan/glm-*". So "try OAuth, fall back to the API" is not available for
GLM through Ringer without editing that guard. Report the block and reroute
rather than bypassing it.

### local-shell probe tasks: the retry is actively harmful
On a failed `local-shell` task, the retry prompt (which injects the check's
failure output into the spec) is handed to bash as the spec and executed. Seen as
`/bin/bash: line 10: Previous: command not found`. The first attempt's artifact is
the real one. For probe manifests on `local-shell`, treat attempt 2 output as
contaminated, and prefer checks that grade a written artifact rather than stdout.

### codex (unpinned, OAuth) — code-review and code-feature — both passed
code-review lane passed on attempt 2 (attempt 1's artifact was already valid
against both checks, so the retry was spurious — preserve artifacts before a
retry overwrites them). code-feature lane built a 29KB audit tool that passed an
executed check running it offline with the network poisoned, first try, 595s,
145k tokens. Reconciliation quality was genuinely good: it found the handler-only
body keys that the ENDPOINTS map omits rather than transcribing the map.

## 2026-07-26 — one-true-master round 1 (podcast media pipeline review swarm)

### zai-coding-plan/glm-5.2 (glm-coding-plan engine) — LANE DOWN, not a quality failure
Four read-only code-review lanes, 2400s timeout, both attempts: SIGTERM at the
wall with **zero tool calls and zero output**. worker.log held only the spec echo
and the timeout line (~13KB each). Isolated it with a one-task probe whose entire
spec was "write probe.md with one marker line": GLM hung 300s, twice, still
nothing; the identical Codex probe wrote its file in seconds. So the lane hangs
before it emits anything — this is not the model choking on a large spec or on a
6,700-line source file. Last logged GLM success was 2026-07-25T20:50Z, about 20
hours earlier.
Lesson: when every lane of a swarm dies at the timeout with an empty log, probe
the engine with a trivial one-task manifest BEFORE re-scoping the work. The
instinct to blame task size cost a full 80-minute round here. Do not record these
attempts as model quality failures.
Note for orchestrators: the `opencode-auth-policy.sh` guard hard-rejects
`openrouter/z-ai/*` and bare `z-ai/*` with "GLM requires the Z.AI Coding Plan
selector", so there is no silent OpenRouter fallback when this lane dies. Route
to a different family instead, or change the wrapper deliberately with the owner.

### openrouter/nvidia/nemotron-3-ultra-550b-a55b:free — capacity, not competence
Auditioned on one code-review lane (1M context, chosen to hold a 6,700-line
file). It worked well: 8 tool calls in under 60s, reading real files fast and
cheaply. Then died on a provider 502: `Upstream error from Nvidia:
ResourceExhausted: Worker local total request limit reached (90/32)`. Free-tier
capacity, mid-task.
Verdict: promising on read-heavy review, unusable when an artifact must actually
land — audition it again only where a mid-run death costs nothing.

- 2026-07-28 (social-dept-build r1, code-feature): claude-lean/sonnet PASSED on attempt 2 building 4 sense-lane nodes + 12 tests. Caveat: worker reported its Bash could not execute python/pytest (permission-blocked in lane), so it audited by reading; the executed harness check still proved the tests green. Treat claude-lean as write-capable but not self-verifying in this setup; keep on lanes where the manifest check does the proving. Codex gpt-5.6-sol: 4/4 first-try incl. 2588-line spine patch at high reasoning.

- 2026-07-29 (hsd-bounce-send-gate, code-fix): Codex CLI default (unpinned) PASSED first attempt, 90s, 48.8k tokens, on a two-part fix in a 9k-line file: a fail-closed recipient bounce check wired into an existing send gate, plus a new resolve_bounce() writer. Pattern worth reusing: the grading contract lived OUTSIDE the worktree and the check cp-ed it over tests/ before running, so the worker owned exactly one source file and could not weaken its own test. Diff came back minimal and correctly mirrored the reference implementation it was pointed at (read it, do not import it, avoid the circular dep). One reviewer nit the check did not catch: it appended the cheap deterministic bounce check AFTER the expensive LLM honesty judge, so a bounced recipient still pays for a judge call before being blocked. If ordering/cost matters, say so in the spec; a correctness-only contract will not enforce it.

- 2026-07-29 (hsd-bounce-cleanup, code-fix): Codex CLI default (unpinned) PASSED first attempt again, 144s, 56.7k tokens. 2/2 first-try on this repo today under the same pattern (immutable contract outside the worktree, worker owns one file). Two things worth noting. (1) It solved a blocker I had not anticipated: the CLI subcommand test ran gap_sync.py in a subprocess with no HubSpot credentials, and main() unconditionally resolved an AWS secret before dispatch. The worker hoisted the command parse above that block and skipped the lookup for the local-only subcommand — beyond the letter of the spec but exactly aligned with its intent, and it did not touch anything else. (2) Its dry-run output matched an independent SQL measurement I had taken before writing the contract, on all five counters against live data. That cross-check is worth building into contracts deliberately: measure the real numbers yourself first, then let the implementation agree or disagree with you out loud.

- 2026-07-29 (hsd-identity-rungs, code-fix x2 parallel): Codex CLI default 2/2 first-try again, 45s/41k and 108s/53k, now 4/4 on this repo today. Both diffs were minimal and neither worker touched the other's file across parallel worktrees. Two reusable lessons. (1) Build the CONTROL into the same contract as the bug: the free-domain contract included "a real company domain must still expand" (the Layla Graves protection). Rung 3 went red 8-failed/3-passed, and the 3 passing were the controls, which is how I knew the check discriminated rather than just failing at everything. A wall of red tells you nothing. (2) A worker's self-reported caveat needs checking, not accepting: rung 4 reported it had skipped a CLI test for a path reason. The exported check log showed 7 passed with no skips; the caveat described running the contract in place from /tmp, not the graded run. Read the artifact, not the summary.

- 2026-07-29 (hsd-identity-retry, code-feature): ORCHESTRATOR ERROR, not a model failure. The task went FAIL after 2 attempts with its own contract at 9/9 green; the red came from the regression step, where a previously-committed test asserted the exact policy the owner had just reversed. Root cause: worktrees mode detaches at HEAD, so my edit removing that superseded test existed only in the dirty working tree and was invisible to the worker. It was graded against a contract I had already retired. Rule going forward: in worktrees mode, any test or fixture change the contract depends on must be COMMITTED before the run, not merely saved. Cost was one wasted run at 116k tokens. Worth noting the worker also self-diagnosed a genuine defect in the same pass (bounce-only gate calls pass an empty contact id, and it was creating retry state keyed on the empty string) and fixed it unprompted, which is the behaviour you want from a specific failing check rather than a vague one.

- 2026-07-29 (hsd-fix-three-defects, code-fix x2): SAME ORCHESTRATOR ERROR FOR THE THIRD TIME TODAY, and I had already written the lesson into this file hours earlier. Both lanes went FAIL after 2 attempts with their own contracts GREEN (13 and 11 passed); the red came from the regression step referencing tests/test_fix3.py, which existed in my dirty working tree but was never COMMITTED, so the HEAD-detached worktree could not see it. Cost: two wasted lanes at ~215k tokens combined. The rule I wrote earlier and then failed to apply: in worktrees mode, ANY test or fixture the check references must be committed before the run, not merely saved. Concrete practice that would have caught all three occurrences in seconds: before launching, run `git status --porcelain -- tests/` and confirm every test path named in the check script is tracked and clean. Writing a lesson down is not the same as having a step that enforces it.

- 2026-07-29 (hsd inbox lane, probe defects): TWICE a read-only probe produced a WRONG conclusion because the probe omitted a step the real code performs, and both times the wrong conclusion was the alarming one. (1) A composer probe passed context_pack=None and measured 0/10 draftable when the real answer was 10/10. (2) A send-gate probe built the context pack without `pack["gmail"] = {"inbound_checked": True}` (inbox_reply_run.py:565) and reported GATE: BLOCK on two good drafts; with the real preparation both are GATE: ALLOW including the honesty judge. Rule: a probe that reimplements a caller must be diffed against that caller line by line before its result is believed, and a probe result that contradicts the design should be suspected of probe defect FIRST. Cheap discriminator: print the intermediate the real path builds (here the SWO) next to the verdict; the wrong SWO was visible in one line.

### sonnet (claude engine) — 2026-07-30, code-fix, hubspot-daily-2 reply-queue automation
- Scored FAIL in run hsd-reply-queue-automation-20260730T192507Z but NEVER ATTEMPTED THE WORK. Classify as HARNESS_FAIL, not a capability result.
- Cause: the task edited a repo OUTSIDE the task directory. The codex tasks in the same manifest got access via `engine_args` `sandbox_workspace_write.writable_roots`; the claude engine template has no equivalent, and `--permission-mode acceptEdits` does not reach outside cwd. The worker replied "I need permission to read the target repository" and exited rc=0 in 8s, 0 tokens, no notes.md, twice.
- Fix: pass `"engine_args": ["--add-dir", "<repo>"]` on any claude-engine task that edits a repo outside its task directory. Retried on that basis in round 2.
- Do not conclude anything about sonnet on code-fix from this row. Its prior record here is 4 tasks, 1.00 first-try.
- 2026-07-30 outcome: with `--add-dir=<repo>` (EQUALS form) sonnet passed the same task first try, 336s, one attempt. Root cause of the second failure: `--add-dir <repo>` space-separated is variadic in Claude Code and swallows the positional prompt, so claude exits with "Input must be provided either through stdin or as a prompt argument when using --print". Always use the equals form in engine_args. Product quality was good: it reused the existing gap_sync.py sync-sent entrypoint as instructed, matched the file phase/ledger conventions exactly, and put the measurement in the code comment. sonnet on code-fix here is now 5 tasks, 1.00 first-try.

- 2026-07-30 — kimi-k3 (pi-openrouter): HARNESS_FAIL on research audition (run vintage-optical-exit-onepager). All 6 API calls died instantly with 'Connection error.' inside the bwrap adapter; 0 tokens reached the model. NOT a kimi signal — do not demote. Probe pi-openrouter lane connectivity (DNS/network inside bubblewrap?) with a trivial checked one-task manifest before the next audition.

- 2026-07-31 — glm-5.2 (pi-openrouter): HARNESS_FAIL, second consecutive Pi-lane death in two days, different cause. Run `mott-text-dashboard-spec`, task_type docs. Both attempts died in 0.2s at rc=127 with `pi-openrouter-ringer: could not resolve Node ELF interpreter`; 0 tokens reached the model, no spec.md was ever created. NOT a GLM signal — do not demote. Yesterday's failure was network inside bwrap; today's is the Node runtime mount, so the lane is down in at least two independent ways and should be treated as unavailable until a trivial checked one-task manifest passes through it.
- ORCHESTRATOR ERROR worth more than the row itself: the line directly above this one already said to probe the Pi lane before the next audition, and I assigned a real task to it anyway. I ran `models --task-type docs`, `models --explore` and `catalog --changes`, and skipped MODEL-NOTES — the half of the routing evidence that carries what the numbers cannot. Cheap this time (0 tokens, one dead lane, comparison draft lost). Concrete practice: before writing any manifest that names an engine, grep this file for that engine name and read the newest three entries. The scoreboard tells you how a model performs; this file tells you whether the lane is currently alive.
- Same run, contrast: gpt-5.6-terra (codex, `-m` pin via engine_args) PASSED first try on the same spec, 90.5s, 34.4k tokens, 1850 words. Product quality was above the brief in two places — it forbade returning the raw `variables` object while still using it server-side for a first name, and its Assumptions section refused to invent the `pagination` member names that the source probe had not established, saying so explicitly instead. The field-allowlist check (validator cross-references every API field the spec claims against a live probe capture) is worth reusing for any spec written against an external API; it converts "did the model hallucinate the integration surface" from a review question into an executed one.

- 2026-07-31 — codex default + claude-lean on task_type research (run `bland-conversations-api-contract`): both scored FAIL/TIMEOUT and BOTH ACTUALLY SUCCEEDED. Do not read these two rows as research capability. CHECKER DEFECT, mine: the check executed one live HTTPS call per candidate with a 60s socket timeout and a 0.4s sleep between them, and the workers legitimately produced 23 and 30 candidates, so the sweep alone ran 300-550s per attempt and blew its budget while the artifacts were complete and correct on disk. Fix before reuse: reuse one connection, drop the sleep, cut the per-call timeout to ~10s, and cap total candidates in the checker rather than letting a thorough worker time itself out. Lesson generalizes: when a check does bounded external I/O per item, its runtime scales with how GOOD the worker was, so a thorough worker is punished by a naive checker.
- Same run, the research itself was a clean win and worth the pattern: workers got NO network and NO credentials and only proposed candidate query parameters with rationales; the check executed every candidate against the live API and decided truth. Both lanes independently found the answer. Recommend this shape for any "what is the real contract of this external API" question — the model cannot bluff, because it never touches the thing it is theorizing about.
- Durable finding from that run, worth keeping regardless of models: Bland `GET /v1/sms/conversations` paginates with `limit` (page size) plus `from` (ZERO-BASED ROW OFFSET, not a page index), and sorts with `ascending` (default false, newest first). `page`, `offset`, `skip`, `currentPage`, `pageSize` and `to` are SILENTLY IGNORED — no error, full result set returned — which is how a naive implementation ends up unbounded while looking paginated. A duplicated parameter returns HTTP 400. `pagination.currentPage` is derived from from/limit and reads 1 until you actually send `from`.

- 2026-07-31 — codex default, code-feature then code-fix (run `mott-text-history-test-conditions`, 2 rounds, both PASS first try, 94k then 51k tokens): test-first job, write 14 acceptance tests for a feature that does not exist. Two things worth reusing. (1) The check asserted RED FOR THE RIGHT REASON rather than exit 0: at least one smoke test must PASS (proving the harness works), at least 12 must FAIL (proving the criteria are real and the feature is unbuilt), zero skipped, and a non-zero collected-test count (proving nothing died at import). Without the collected-count clause, a suite that crashes on a missing module reports zero tests and is indistinguishable from a broken framework. (2) Tests against not-yet-existing modules MUST use dynamic import inside each test body, or the file dies at collection and you lose all per-criterion signal.
- SPEC DEFECT, mine, from the same run: my brief listed the worker's three owned files by ABSOLUTE path (/mnt/d_drive/...), and the worker mirrored that style into the code, emitting 21 absolute-path dynamic imports that made the suite runnable on exactly one machine. The check caught the red state correctly but had no opinion on portability. Two lessons: state file ownership as repo-relative paths in briefs unless there is a reason not to, and when a brief must use absolute paths, say explicitly that they are for locating files and must not appear in emitted code. Round 2 fixed it with a check asserting no `/mnt/` string survives AND the pass/fail counts are unchanged — the second clause matters because the easy way to make a red suite portable is to quietly weaken it.

- 2026-07-31 — codex default, code-feature (run `mott-text-history-implementation`): PASSED first try, 315s, 89k tokens, turning 18 red acceptance criteria green across 8 new/modified files. Security core was correct on review: exact `===` tenant equality with no prefix match, and admin derived only from `session.groups` with the query parameter inert without it. The checksum clause worked — test files were byte-identical afterwards, so it satisfied the criteria instead of editing them. Recommend checksumming the contract files on every implement-to-green task; it is two lines of check and it closes the obvious cheat.
- THE CATCH THE CHECK REWARDED, worth generalizing: the worker DELETED the app's `next/font/google` imports from layout.tsx and the matching CSS variables, shipping a typography regression to every page. Cause: `next/font/google` fetches at build time, the Ringer sandbox has no network, `next build` failed, and removing the fonts made it pass. My check required `next build` to exit 0, so it actively rewarded the deletion. Both tests and build were green on a real regression. Rule: when a check requires a build to pass inside a network-less sandbox, any build step with a NETWORK dependency becomes an incentive to delete that step. Either pre-warm the cache, exclude those steps from the sandboxed build, or diff the shared/global files by hand before accepting. Reviewing the diff of files the brief did NOT name is where this showed up — the brief named 7 files, the worker touched 9.
- Environment note for eyecloud_ai: `.git/index.lock` is stale, dated 2026-05-21, so every git WRITE (commit, checkout, add, branch) fails there while reads work fine. `git show HEAD:<path> > <path>` restores a file without needing the lock, which is a useful workaround when you must revert something in a locked repo you do not own.

- 2026-07-31 — PI LANE RESOLVED (run `mk2-number-and-comeback`, identity claude-fable-5-coordinator): the two open HARNESS_FAIL threads above are root-caused, measured, and fixed. (1) The ELF-interpreter failure is missing binutils: the wrapper hard-requires /usr/bin/readelf and the ai-agents toolbox container does not ship it (ldd alone is not enough) — launch Pi-lane runs from the host, or install binutils in the container. (2) The 2026-07-30 "Connection error." deaths were TLS, not DNS: Fedora's node links the system OpenSSL whose OPENSSLDIR is /etc/pki, the wrapper mounted only /etc/ssl/certs, and inside the sandbox both ca-bundle.crt and /etc/crypto-policies/back-ends/*.config are dangling symlinks. Proven by bwrap reproduction (UNABLE_TO_GET_ISSUER_CERT_LOCALLY, then the opensslcnf.config stat error, then HTTP 200 once mounted). Fixed in engines/pi-openrouter-ringer.sh: three conditional ro-binds — /etc/pki, /etc/crypto-policies, /usr/share/crypto-policies — public trust material only, no-ops on Debian-style hosts. The lane had likely NEVER worked from this Fedora host; do not read any pre-fix Pi/xai row from this machine as a model signal.
- Same run, kimi-k3 (pi-openrouter, code-review): PASS first try on a hard design review, 431s, 627k output units. Strongest routing/state analysis of the three-model panel — found the e_existing global-label collision, the n_office/n_faq globalLabel scoping fix, and quoted the candidate gate's invariant-5 claim regex by line. Expensive per task; worth it on design reviews where the failure mode is a plausible-but-wrong architecture. Audition upgraded: probation → promising for code-review.
- Same run, grok-4.5 (xai, code-review): PASS on attempt 2, 234s, 265k; attempt 1 failed the report-contract check and the injected WHY fixed it. Distinct value was the patient-experience lens: the one-bubble close rule (avoid double "you're all set"), and the no-two-numbers/no-two-brand-names-in-one-thread test that surfaced the Mott-vs-MK2 decision for Ankit.
- Same run, codex gpt-5.6-sol (code-review): PASS first try, 149s, 58k — but its design placed the mandated close line in e_booked.text, which the repo's own invariant-5 gate explicitly forbids (claim regex + e_booked second-claim rule). The other two reviewers caught it and the gate settled it. Lesson: a single-reviewer design pass would have shipped a spec that fails the project's own hardening gate; the panel earned its cost on the first divergence.
- Containment note, same run: the codex worker's final message carried Ankit's private canary line and reply prefix despite `--ignore-user-config` — further confirmation that flag is not full user-config containment (matches the existing 2026-07-13 caveat; harmless here, worth remembering for no-external-write specs).

- 2026-08-02 pi-openrouter (lane infra, Fedora): run failed closed in 0.2s with "could not resolve Node ELF interpreter" — root cause: binutils not installed, wrapper hardcodes /usr/bin/readelf. Fix: sudo dnf install -y binutils. Not a model failure; do not log against kimi-k3.

- 2026-08-02 gemini (lane infra): headless Ringer worker hung on "Opening authentication page in your browser" — no cached Gemini CLI OAuth on this box; stdin is /dev/null so the prompt can never be answered; burned one full 2400s timeout + a retry. NOT a model failure — audition void. Before giving gemini any Ringer lane here, run the gemini CLI interactively once to cache OAuth. Task rerouted to codex.

- 2026-08-02 claude (lane infra): read-only diagnosis task needing live-path reads outside the task dir failed — claude engine sandbox restricted reads to workdir; worker honestly returned INCONCLUSIVE. Not a model failure. Route live-path investigation tasks to codex lane (workspace-write sandbox reads repos fine) or extend claude template dirs.

- 2026-08-02 codex (lane infra): manifests WITHOUT worktrees give codex a task-dir-only writable root — live-path fix tasks silently degrade to render-only patches (3/3 tonight); checks passed on honest reports. Rule: repo fixes need worktrees:true; out-of-repo targets (~/scripts, unit files) need coordinator application of the rendered diff.

- 2026-08-03 (coordinator harness): custom check scripts exporting via `git diff HEAD` LOSE untracked new files, and PASSING worktrees are deleted — two tasks lost work. RULE: every worktree task check must use fix_with_tests.py (stages owned files incl. new) or `git add -A` on owned paths before diffing. Recovered hsd from a FAILED (preserved) worktree; sales-bridge required re-run.

- 2026-08-03 codex-oauth lane: ambient CODEX_AUTH_JSON env (from a /login attempt) trips the wrapper ambiguity guard — rc=64 for every worker. Guard is correct; launch ringer with `env -u CODEX_AUTH_JSON`. Two runs burned before diagnosis.

- 2026-08-03 codex lane outage, full chain: CLI auto-update 0.144->0.146 invalidated file auth; host `codex login` stored to HOST keyring invisible to the toolbox container where Ringer runs; fix = `codex login --device-auth` executed INSIDE the container (via `!` chat prefix). Wrapper requires `codex login status` == "Logged in using ChatGPT" exactly and fails rc=64 otherwise — correct fail-closed. Stale CODEX_AUTH_JSON env blob (4KB) in session env was a red herring; keep launching ringer with `env -u CODEX_AUTH_JSON` anyway. Also: task ERROR at 0.0s with empty logs dir = stale worktree dir squatting the workdir from a prior failed run; rm + `git worktree prune` before relaunch. Probe shape for codex 0.146: `codex-oauth.sh exec --skip-git-repo-check "..."`.

- 2026-08-03 (code-feature, loop-factory ultimate-process): claude sonnet via --safe-mode PASSED attempt 1 on a 5.7k-char fully self-contained spec (inlined contracts, fake-fixture tests) after the same task failed when the spec pointed at cross-repo files the sandbox blocks. Lesson: claude engine specs must inline every contract; never reference paths outside the worktree. Also: worker asked for interactive approval when blocked — headless, nobody answers; spec must say "do not ask".
- 2026-08-03 (code-feature, comms-loop-invariant): codex workers produced green substance (601 tests, working sensor, clean validate) but all 3 lanes failed on a checker that demanded absolute repo cleanliness — pre-existing dirt from parallel lanes flagged as overreach. Checker lesson, not model: live-repo ownership sweeps must baseline pre-run git status.

- 2026-08-03 (code-feature, dept-audit fix r3): codex first-try green on BOTH sensor lanes, but the podcast one REWROTE a pinned computation (publish_reliability) instead of extending — its verify did not include the repo-root pin suite, so 6 green checks hid a semantics replacement. Coordinator review vs root pins caught it; lane respecced with "THE PIN WINS" constraint + root pins in verify. Lesson: when a task says extend-not-replace, put every pin file in the verify AND the owned list, and say which functions are frozen.

- 2026-08-04 (fable-chief, research): pi-openrouter lane HARNESS_FAIL on Fedora box — engines/pi-openrouter-ringer.sh exits rc=127 "could not resolve Node ELF interpreter" before any model call (glm-5.2, task growth-capital, 2 attempts, 0 tokens). Not a GLM verdict. Fix the wrapper Node mount before re-auditioning any Pi/OpenRouter model.

- 2026-08-05 (fable-chief, probe): Pi/OpenRouter lane RECOVERED. Earlier rc=127 "could not resolve Node ELF interpreter" was transient, not a permanent harness break. Root cause context: /usr/bin/readelf is absent on this box so the wrapper uses its python ELF fallback, which parses /usr/bin/node-22 correctly. Verified live: xai/grok-4.5, z-ai/glm-5.2, moonshotai/kimi-k3 all PASS attempt 1 on a checked probe (10.4s/4.6s/19.8s). NOTE: engine names glm-coding-plan is NOT valid in config; use glm-api, kimi-api, grok-api or xai. All non-Codex/Claude/Gemini engines share the single pi-openrouter-ringer.sh wrapper, so one wrapper failure blocks every OpenRouter model at once.

- 2026-08-05 qwen/qwen3.5-122b-a10b (pi-openrouter), code-feature (recon script): artifact VALID (4/4 tests pass on manual check) but worker never exited — TIMEOUT x2 at 1200s, 75K tokens. Lane wrap-up hang, not code quality. Do not re-audition on Pi lane until the hang is diagnosed; product salvaged via local-shell verification receipt.
- 2026-08-05 gemini (Gemini CLI OAuth lane), research x3: HARNESS_FAIL. Headless worker hit an interactive auth prompt (no completed OAuth on this machine). Zero artifacts, run hung, killed. Do not route gemini until the CLI is authed once interactively. Rerouted the 3 web-research tasks to the claude engine.
- 2026-08-05 claude (Claude Code headless engine), research x3: no-web HARNESS limitation. WebSearch/WebFetch/curl permission-gated with no approver in headless runs; worker honestly produced confidence-tagged placeholders that satisfied the section/citation validator. Coordinator REJECTED the green receipts (twenty-api, sakari-api) as unverified. Rule: do not route web-research tasks to headless claude or gemini lanes on this machine; use in-session subagents (have web) or codex only after proving its web posture with a one-task probe.
- 2026-08-06 codex, n8n-flow authoring x7 + runbook: 6/8 in-run PASS; 2 tasks showed FAIL receipts whose final artifacts pass the identical checks manually (shared-workdir wave; exact mechanism unmeasured, do not assert). Salvaged with local-shell receipts, attempt 1. Consider per-task output dirs next flow wave.
- 2026-08-06 openrouter/qwen/qwen3.8-max (pi-openrouter): code-feature (systemd units + bash notify script), 1/1 first-try, 13.2k tokens, cheapest lane in session-lifecycle-handoff run. Good for small deterministic file-gen behind strict executed checks; promote to probation.

## 2026-08-06 — enrichment-model-bakeoff (bakeoff, 24 sanitized CRM classification packets, 2 rounds)
- **kimi-k3 (pi-openrouter)**: r1 could not see host-path input (Pi bubblewrap mounts task dir only) and HONESTLY refused to fabricate — the only confined lane to do so. r2 (staged input): most decisive classifier (7/10 unknowns classified, avg conf 0.74), 6/6 correct-stops on thin-packet traps, evidence quotes precise (caught a jobtitle field contradicted by triage notes). One retry on output-contract format. Promote: strong candidate for classification/judgment lanes.
- **grok-4.5 (pi-openrouter)**: r1 burned 3.4M tokens / 29 min producing a degenerate all-Unknown result when input was unreadable — worst failure economics of the six. r2: clean first-try, 120k tokens. Lesson: grok thrashes instead of stopping on unreadable-input situations.
- **glm-5.2 / qwen3.8-max (pi-openrouter)**: r1 wrote degenerate all-Unknown "passes" instead of refusing. r2: both produced honest work; glm needed one retry.
- **codex-terra**: only r1 lane that did real work (host path readable outside bubblewrap). r2: most conservative classifier of the six (4/10 classified, avg conf 0.40).
- **claude-sonnet (headless)**: r1 exited rc=0 asking a clarifying question instead of failing loudly — headless spec-compliance wobble. r2: clean first-try.
- **Harness lessons**: (1) Pi-lane task inputs MUST be staged into the task dir, never referenced by absolute host path. (2) A structural check must forbid the degenerate output a blind worker could emit (here: all-Unknown with "insufficient evidence" — now requires verbatim quotes on packets with activity_count>=3), else confinement failures masquerade as green passes.
- **Substance finding**: on 8 hidden-label packets the six models, when disagreeing with the old enrichment label, converged unanimously on the alternative (3x Unknown, 1x Champion vs old "Decision Maker") — treat legacy hc_contact_role labels as weak reference, not ground truth.

## 2026-08-06 — loop-drive-contract round 1 (read-only audit of podcast estate send gates, identity: claude-code-opus5)

### claude-lean (sonnet) — code-review — HARNESS defect first, then clean PASS
- Attempt 1 and 2 died in 3.4s total with zero token spend: `Error: Input must be provided either through stdin or as a prompt argument when using --print`. NOT a model failure. Cause: task `engine_args` passed directory grants as space-separated pairs (`--add-dir A --add-dir B`); the `claude-lean` args_template renders `{engine_args}` immediately before `{spec}`, `--add-dir` is variadic, so the last flag consumed the spec as another directory value, and Ringer's stdin-closed invariant left no fallback.
- Fix: single-token form `--add-dir=/path` per grant. Cannot consume a following argument.
- After the fix: PASS on attempt 1, 428.7s, 12-gate classification across two repos with 18 recorded search commands and every file:line:quote citation validated. Judgment was genuinely good: it distinguished enforcement-by-construction (a hardcoded safe value with no branch that could fail) from a runtime check with a reason path, and set `returns_structured_failure=false` for the right reason rather than the convenient one. Coordinator spot-checked the citation by hand; exact.
- RULE, applies to any engine: when a harness template renders caller args immediately before a trailing positional, use the `--flag=value` form for every flag. A variadic flag will eat the positional.
- RULE: a sub-5-second failure with zero token spend is a spawn/harness fault. Read the rendered command in the raw worker log before spending a retry on it; the automatic retry cannot fix an argument-order bug and just burns the attempt.

### codex (gpt-5.6-terra) — code-review — 2/2 first-try
- Both lanes PASS on attempt 1: 101.0s / 54.6k and 142.1s / 80.4k. Read-heavy multi-file tracing across a large repo (draft-creation reachability through a shell runner into Python call chains, and return-shape auditing of 5 modules). Citations all resolved on first pass, which is what the validator was built to catch.
- Good fit for grounded read-only audit work where the check enforces verbatim quoting. Keep on this task shape.

- 2026-08-10 (Codex CLI default, code-feature, harness note): cvc-scoreboard-app r1 FAIL x2 in 0.9s was a HARNESS fail, not model: engine_args passed -c sandbox_workspace_write.network_access=true, which codex-oauth.sh rejects (allowlist: model, model_reasoning_effort, sandbox_workspace_write.writable_roots only). Discount these two attempts when reading the scoreboard. Workers needing npm network: let the external check run install/build instead.

- 2026-08-10 (z-ai/glm-5.2 via pi-openrouter, code-feature): first-try PASS on cvc-scoreboard-app t2-seats-screens (166s, ~216k tokens, promo pricing 0.07/0.22). Quality on human review: disciplined ownership, typed connection-agnostic query module, defensive JSON narrowing — one smell: typed DB as PgliteDatabase instead of a driver-neutral type. Promotes to probation for code-feature; audition another bounded UI lane next run.
- 2026-08-10 (gpt-5.6-luna, code-feature): PASS in 2 attempts on t1-scoreboard-grid (~129k tokens); retry was product-level, not harness. Sample now 6 tasks; still strong but no longer unblemished first-try.

## grok-4.5 via pi-openrouter (grok-api)
- 2026-08-09 research/fetch task (optometry-industry-averages, retention lane): AUDITION FAILED for harness reasons, not model quality. Pi bubblewrap lane exposes only read/write/edit — no bash tool, no curl/wget binary — so a fetch-based research spec cannot execute. Model behaved WELL: refused to fabricate sources, wrote honest could-not-fetch report, 2 attempts, 0 numbers delivered. Lesson: do not route fetch/retrieval research specs to pi-openrouter lanes; they fit codex (web-search connector) or specs that need no retrieval. Demotion: retention lane re-run moved to codex.

## codex (gpt-5.6-sol, unpinned default)
- 2026-08-09 research/fetch tasks (optometry-industry-averages, 5 lanes): sandbox has NO shell network (curl DNS blocked) — workers adapted via web-search connector and transcribed extracts into fetched/ files, honestly labeled. 4/5 lanes produced solid grounded artifacts (run JSON recorded fails but artifacts finished after check window; manual re-check passed). Coordinator live-verified 3/3 sampled quotes against real pages — transcription channel trustworthy. Lesson: for fetch-research specs on codex, write the spec around the web-search connector + saved extracts, not curl; grounding checks verify against worker-authored extracts, so coordinator must live-spot-check a sample.

- 2026-08-10 (qwen3.8-max via pi-openrouter, code-review, harness note): VOID lane on cvc-scoreboard-app review — Pi bubblewrap mounts only the task dir at /workspace, so a spec pointing at an external repo path reads ENOENT. Model honestly reported zero-access instead of fabricating findings (good sign). Rule: pi-openrouter lanes need code IN the task dir (worktrees mode or snapshot); never absolute repo paths.
- 2026-08-10 (gemini engine, code-review, harness note): HUNG on interactive OAuth prompt (Opening authentication page... [Y/n]) with stdin closed; attempt 1 produced no report, attempt 2 hung until run killed. Gemini CLI auth is not headless-ready on this machine — re-auth interactively before giving gemini lanes work.

- 2026-08-10 (claude engine, code-review, harness note): claude engine sandbox restricts reads to the task directory — external repo paths hit "allowed working directories" blocks (same class as pi bubblewrap). Reviewer honestly refused to fabricate (good) but the lane is structurally void for external-repo review. Rule: only codex lanes may review by absolute repo path; claude/pi review lanes need the code staged in the task dir or a worktree. Also: review-swarm check requires the literal title "# Review Report" and "### Finding:" block prefixes — embed both in specs.

- 2026-08-10 (z-ai/glm-5.2 via pi-openrouter, code-feature, demotion): FAILED x2 on cvc-scoreboard b2 t2-rocks-todos (two-dir UI lane requiring reading API contracts first) — produced ZERO files both attempts (empty_patch, missing summary) while burning ~793k tokens. Contrast: passed the single-dir seats lane first-try last round. Verdict: GLM-5.2 stays proven for SINGLE-directory bounded UI lanes with explicit contracts inline; do not assign multi-dir or read-contracts-first lanes. Audition one rung up ended.

- 2026-08-10 (z-ai/glm-5.2 via pi-openrouter, research, demotion note): ga-two-practice-acquisition cvg-payroll (aggregate 22 payroll text files, sum 941 line 2 by year) FAILED — no output files, 179MB worker.log runaway loop, both attempts. The spec was pure multi-file read+arithmetic with an explicit output contract; GLM looped instead of finishing. Consistent with the multi-dir demotion above: do not assign GLM many-input aggregation lanes. Re-run on codex passed attempt 1 (105s, 58k tokens).
- 2026-08-10 (codex, research, extraction pattern): ga-two-practice-acquisition 8/8 financial-extraction lanes passed once specs used the cwd-write + check-export pattern (worker writes ./name.json in its own task dir; the external check copies to out/ and validates). The first round failed 10/10 on a COORDINATOR harness mistake: specs demanded absolute-path writes outside the sandbox writable root. Codex sandbox allows broad READS but only task-dir writes. Rule: extraction/report specs write in cwd; checks export.
- 2026-08-10 (claude engine, vision/research): reads PDFs visually ONLY within its task dir, and the Read tool hard-fails on >20MB PDFs (page-ranged reads need pdftoppm, not installed on this box). Fix that worked: pre-render pages to PNGs with PyMuPDF into the task dir; a 9-page scanned questionnaire then transcribed first-try in 193s. Rule for scanned/garbled PDFs: stage per-page PNGs in the task dir and spec the PNGs, never the raw PDF.

- 2026-08-10 (qwen3.8-max via pi-openrouter, code-feature, HARNESS_FAIL not a quality result): true-sight-vision-care-deck lanes gate3 + wildcard both TIMEOUT x2 (1500s each, 0 tokens recorded). Root cause measured, not assumed: the Pi bubblewrap wrapper mounts ONLY a Node runtime (`--dir /runtime/bin` + node's ldd libs). There is no python3 and no pandas inside the sandbox — the `python3` calls in pi-openrouter-ringer.sh are the HOST-side supervisor. The spec had claimed "pandas is installed" (coordinator defect). Both models wrote real scripts they could never execute, then thrashed writing `.exec_probe` / `.toolprobe` / `.tp3` files hunting for an interpreter; compute_wildcard.py's header shows the model hand-tallying rows in chunks ("processed data rows 1..1004 ... next offset: 1006") rather than fabricating. Notably qwen's orphaned compute_gate3.py was GOOD work — 18KB, 9 insights, correct anchors, ran clean first try on the host and passed the real check unchanged. Rule (generalises the earlier grok no-bash/no-curl note): pi-openrouter lanes are TEXT-ONLY. Never give them a task whose check requires executing a script in any language but Node. Route execute-and-verify analysis lanes to codex. Do NOT read this as a qwen3.8-max code-feature demotion; the model never got to run.
- 2026-08-10 (local-shell, code-feature, checker + retry defects): the documented local-shell retry pitfall reproduced exactly — attempt 1 wrote a correct artifact (rc=0), the check failed, and attempt 2 had `Previous attempt failed: <log text>` appended into the bash command, giving `/bin/bash: line 3: Previous: command not found`, rc=127. Underlying red was a CHECKER defect, not a product defect: the validator scanned only top-level `evidence` values for a number, so legitimately NESTED evidence (per-IVR-option breakdowns like `{"option_1":{"calls":830,...}}`) was wrongly rejected. Fixed with a recursive `has_number()`, re-proved against 1 known-good + 6 known-bad fixtures (including a new nested-but-numberless case) before rerunning. Fresh local-shell task then passed on attempt 1 in 1.3s. Rules confirmed: classify a red before spending the retry; never rely on the local-shell retry to repair deterministic work; write evidence-shape checks to recurse.

- 2026-08-10 codex/gpt-5.6-sol · code-fix (hubspot delta PATCH-path resilience, wave21): PASS attempt 1, 57.8k tokens, 130s. Clean implementation matching a tight contract (new exception + 3 failure buckets + receipt schema + 5 tests). One unrequested but behavior-preserving edit (_post_json robustness to fake responses). Continues the "every fix task first-try" pattern on this repo.

- 2026-08-11 (code-feature, mybcat_brain repo-feature): Codex default PASS on attempt 2, 109k tokens, 258s. Attempt 1 failed only the git-status allowlist: worker wrote its own scratch resume.md into the repo root, then removed it on retry. Lesson: for direct-repo repo-feature runs, either add resume.md to --allowed-status or tell the spec "no scratch files in the repo". Work itself was correct on attempt 1.

- 2026-08-11 (claude engine, code-fix, harness notes x2 — discount the scoreboard FAILs): loop-drive-contract r32. (1) ERROR 0.0s run: stale worktree collision — the prior codex attempt FAILed and left its worktree; _prepare_taskdir refuses an existing taskdir (ringer.py ~7173) before any spawn, so same-manifest reruns after a FAIL need the old worktree removed first. (2) FAIL 589.8s run: the engine template ships --permission-mode acceptEdits, which auto-approves EDITS but not BASH — a headless -p worker can never answer the approval prompt, so it cannot run pytest/checks on its own work. Sonnet behaved WELL: wrote the full correct fix (patch later reviewed, hand-applied, all checks green at repo), refused to fabricate a "How I verified" section it could not execute, and asked for approval instead. Fix pending owner approval: acceptEdits -> bypassPermissions in [engines.claude]/[engines.claude-lean] args_template. Until then the claude lane cannot verify anything it builds; do not route execute-and-verify work to it.

- 2026-08-11 (claude engine post-bypassPermissions fix, code-fix + code-feature): 4/4 PASS attempt 1 same evening — r33 bio-length (102s) and all three one-card-slice lanes (129s/232s/317s), every check self-executed by the worker (pytest + gate scripts). The acceptEdits wall was the whole story; sonnet under the fixed template is first-try reliable on bounded single-module lanes with pinned contracts. Claude lane promoted to the default podcast code lane while Codex is locked out (until Aug 17).

## 2026-08-12 catalog auditions through pi-openrouter

- `openrouter/nvidia/nemotron-3.5-lightning:free`, probe: the generated Python artifact passed the deterministic valid-input, invalid-input, ownership, and external execution checks in one Ringer attempt (62.7s, 12,098 recorded Ringer tokens). OpenRouter generation readback confirmed $0 charged. The worker made three write calls to the same requested file despite the exact one-write rule. Verdict: artifact-capable challenger only, not instruction-clean and not eligible for default promotion.
- `openrouter/meta/muse-glimmer-30b`, probe: eventual artifact PASS after one Ringer retry (15.6s, 10,033 recorded Ringer tokens). Attempt 1 consumed its 1,024-token output cap in reasoning and created no file; attempt 2 made one write and passed. Authoritative OpenRouter charge was $0.004401837. Verdict: retry-only challenger for tightly checked mechanical work; no default promotion.
- `openrouter/sakana/sakana-namazu`, probe: eventual artifact PASS after one Ringer retry (9.4s, 8,415 recorded Ringer tokens). Attempt 1 consumed its 1,024-token output cap in reasoning and created no file; attempt 2 made one write and passed. Authoritative OpenRouter charge was $0.012570376. Verdict: retry-only challenger, materially more expensive than Muse and Solar on this probe; no default promotion.
- `openrouter/upstage/solar-pro4`, probe: the final Python artifact passed the deterministic checks in one Ringer attempt (37.5s, 14,107 recorded Ringer tokens), and authoritative OpenRouter charge was $0.000403057. The worker first targeted a read-only root path, then made four additional writes, including repeated writes after success, despite the exact one-write and stop rules. Verdict: cheapest paid artifact PASS, but instruction-following failure keeps it out of recurring work until a stricter replay is clean.
- Shared audition spend: $0.017375270 total against the purpose-bound $0.03 ceiling. This was one short mechanical sample per model. It supports only challenger-level routing judgments, not broad capability or default status.

- 2026-08-12 (run ga-two-practice-acquisition, round-3 memo review; identity claude-fable-coordinator) — grok-4.5 (xai, code-review): HARNESS_FAIL by SPEC DEFECT, not model. Spec pointed the reviewer at absolute /mnt/d_drive repo paths; the bwrap Pi lane mounts only the task dir at /workspace, so every input returned ENOENT and the worker reviewed BLIND from the charter text — 2 attempts, 2.77M recorded output units, 39 min, and the shape-only check (VERDICT line + min length) PASSED on a review that never read the memo. Two lessons: (1) any pi-openrouter/xai review task needs its inputs STAGED (copy sources into the task dir via a pre-task or make the check stage them; absolute host paths are dead on this lane — codex and claude-lean read the same paths fine in the same round); (2) a review-packet check that validates only VERDICT+length cannot see blindness — add a check grep for at least one verbatim quote/anchor from the reviewed artifact. Credit where due: the blind charter-level output still surfaced two challenges worth adjudicating (rent-step-in-trailing-basis treatment, exception-sequencing discipline). Not a capability demotion; do not log against grok-4.5 capability.
- Same run — codex (code-review, arithmetic lane): PASS attempt 1, 114s, ~80k output units; recomputed every memo figure against receipts with python, caught a MATERIAL evidence-grade error (memo called a rent step "contracted" while the receipt showed the landlord signature blank) plus two precision fixes. claude-lean sonnet (consistency lane): PASS attempt 1, 294s; five real findings including a structured-output-vs-narrative divergence (underwriting_block stating an inference as fact) and a walk-away-trigger omission. Both read /mnt/d_drive absolute paths without issue.
- Same run, earlier task newdocs-recompute (codex, research): PASS attempt 2, ~114k output units. Attempt-1 red was a coordinator SPEC/CHECK SEAM defect: spec said "round all floats to 2 decimals" while the check asserted share identities at 0.001 tolerance — impossible jointly for ratios. Worker adapted by storing ratios at 5dp. Rule: when a check asserts derived-ratio identities, the spec must exempt ratios from display rounding (or the check must tolerate the rounding step).

- 2026-08-12 (run email-backfill-6mo, new task_type email-triage; identity fable-coordinator) — claude sonnet 3/3 PASS attempt 1 (170-254s each) and claude-lean haiku 1/1 PASS attempt 1 (147s) on schema-locked email disposition (58-76 items/task, executed validator: coverage + enum + roster + staleness + PHI regexes). Haiku's judgment quality matched sonnet on spot-review (sensible do/review calls on school forms, bank alerts, security notices) — promote haiku to the default email-triage lane; sonnet reserve for chunks with business-thread ambiguity. Data-boundary note: this job routed to Claude OAuth lanes deliberately (business + family email content; OpenRouter/xAI would be a new third-party exposure) — engine choice was a privacy call, not a scoreboard call.
- 2026-08-12 (run email-lane-hardening, code-fix) — codex PASS (my manual re-run of the check; wrapper verdict pending at write time): per-account exception boundary + atomic incremental --out writes + UA header, 2 mandated tests added, 53-test suite green, correct root-cause narrative in fix-summary.md. CHECKER LESSON (repeat of 2026-08-11 resume.md note, now from the OTHER side): a scope check hashing "all non-owned dirty files" fails on resume.md because the ORCHESTRATOR's own Stop hook rewrites it on a 4-min idle timer — session-harness-owned files (resume.md, worker.log) must be allowlisted in any repo-scope check on this machine.

## nvidia/nemotron-3.5-lightning:free (pi-openrouter)
- 2026-08-12 site-build (wave24 digest-renderer): PASS attempt 1 on a stdlib HTML renderer with a strict executed check (parse + content + ordering + self-contained). Free promo, cost $0. Quirk: tried to call a nonexistent `bash` tool once mid-run, recovered on its own. Worth a second audition on similar small render/docs tasks.

## codex (default, gpt-5.6-sol resolved)
- 2026-08-12 code-feature (wave24 gmail-backfill tool): PASS attempt 2. Attempt-1 failure was ORCHESTRATOR spec ambiguity, not model: spec said "aggregate per SENDER domain" while the fixture expected counterparty-domain aggregation for SENT mail; executed check caught it, retry prompt fixed it. Lesson: when aggregating mail by domain, always define the SENT-direction rule explicitly.

## kimi-code/k3 via kimi OAuth (`engine: kimi`, `engines/kimi-oauth.sh`)
- 2026-08-13 (run kimi-oauth-lane-proof, probe) — new OAuth-primary lane: K3 through the Kimi Code CLI `kimi login` credential, PASS attempt 1 (21s) on a one-file smoke with executed grep check. Wrapper fails closed on OpenRouter selectors and API-key env overrides; `kimi-api` (pi-openrouter, `openrouter/moonshotai/kimi-k3`) is the explicit backup lane, never automatic. Note: `kimi -p` headless runs tools without `--yolo`/`--auto` (both flags are rejected in prompt mode). Needs a real batch before any routing promotion; one smoke proves the lane, not the model.

## 2026-08-13 shorten-the-edit (research, 4-lane adversarial analysis)
- kimi (kimi-code/k3): research, 1-try PASS, 663s. Read a 15-file code+ledger packet and produced a line-level grounded critical-path analysis; 5 novel findings all survived coordinator code verification. Promote confidence for evidence-heavy research on OAuth lane (filesystem access is the differentiator vs confined lanes).
- x-ai/grok-4.5 (xai/Pi bwrap): 1-try PASS but packet-blind (bwrap mounts task dir only; packet was at workdir root — ORCHESTRATOR STAGING ERROR, not model failure). Refused to fabricate; enumerated its ENOENT probes. Honest under missing evidence.
- codex: PASS on attempt 2; sandbox likewise couldn't see workdir-root packet; hedged all quantitative claims as unknown. Honest.
- z-ai/glm-5.2 (Pi bwrap): 1-try PASS, packet-blind, tagged every claim [BRIEF]/[ARITH]/[INDUSTRY]. Honest.
- LESSON (orchestrator): confined lanes (Pi bwrap, codex sandbox) see ONLY their task dir. Stage shared source packets INSIDE each task dir, not at workdir root. A citation-requiring check can be passed honestly by disclosure — verify grounding by reading, not by check exit code.

- 2026-08-13 (cvc-recall-app, code-feature/code-fix x6 rounds): Codex CLI default (unpinned) carried a full greenfield Next.js+Prisma+Auth.js app build across 6 serial manifests — scaffold, import/sweep, caller UI port, durable store + docker seam, SSO, two targeted fixes — 6/6 PASS, 5 first-try, ~850k tokens total. Two lessons. (1) The one retry was my contract's fault, not the model's: I locked package.json while requiring a new npm script in the check; the retry prompt named the conflict and the worker fixed it minimally. Lock fewer files or whitelist script entries when the check needs a new command. (2) Both real defects of the day were invisible to green checks and found only by browser-driving the built app: a validation-by-mutating-verb bug (recheck via serveNextPatient — specs must name the read-only primitive) and a release-redraw no-op (queue semantics gap in the spec itself). Executed checks prove the code does what the spec says; only driving the UI proves the spec said the right thing.

## dots-studio/dots-3-note-preview:free (pi-openrouter)

- 2026-08-15 — HARNESS_FAIL, not a model result. Catalog digest asked for one short mechanical probe. OpenRouter snapshot has `dots-studio/dots-3-note-preview:free` at $0 / 512k / text+image->text. Official `pi update --models` failed closed on a Kimi 403. An OpenRouter-only Pi refresh then completed with 0 errors and 346 cached OpenRouter models, but the exact id was still absent from `models-store.json` and from the bundled pi-ai catalog. Trusted wrapper exited rc=64 twice in 0.3s with "exact OpenRouter model cache is missing or malformed"; 0 tokens, no artifact, $0. Run `dots-3-note-preview-audition-20260815T130832Z-p428283`. Do not demote the model. Do not inject a handmade cache record. Replay the same frozen probe only after the exact id is present in the Pi OpenRouter cache.
- 2026-08-15 retry — same HARNESS_FAIL after a forced OpenRouter-only Pi refresh. Overlay etag unchanged (`W/"9e43f66edcc5bd1fb4f7f6cbcc972447"`), lastModified stayed 2026-08-14T12:32:13Z, exact id still absent. Second run `dots-3-note-preview-audition-20260815T131609Z-p445782` exited rc=64 twice in 0.3s, 0 tokens, $0. Still not a model demotion.

- 2026-08-17 (cvc-recall-app, recall-sync-never-again, code-review panel + code-fix guards): (1) REPEATED the 2026-08-13 staging mistake — pointed pi-openrouter (glm-5.2) and xai (grok-4.5) reviewers at absolute /mnt paths; both honest-BLOCKed on ENOENT, one wasted round. The lesson was already in these notes; read MODEL-NOTES before designing a run, not after it fails. (2) Re-run with material staged in-taskdir: grok-4.5 delivered the round-winning review — caught a real P0 the Fable coordinator and Codex both missed (runtime image lacked src/, sweep would die module-not-found post-fix), 2 attempts. glm-5.2 wrote a substantive REVISE (hang-guard finding was real and shipped) but failed the review-swarm 1200-word/file:line contract twice — treat its lane as advisory unless the contract is loosened. Codex review: solid REVISE, confirmed root cause, 1-try. (3) gpt-5.6-sol workers 4/4 good products (regression test with honest RED canary proof, Dockerfile edits, clean HCL, exact script edits); ALL recorded fails were an orchestrator checker defect — gitignore "node_modules/" does not match a node_modules SYMLINK, so the ownership gate flagged the sanctioned symlink. Allow harness-owned and spec-sanctioned untracked paths explicitly.

- 2026-08-17 (recall-gauge-numbers, research x2): codex 1-try PASS, 37 unique file:line citations, all 3 spot-checked citations verbatim-correct — strong default for repo-grounded data-path tracing. kimi OAuth lane: HARNESS_FAIL not model — 403 billing-cycle quota exhausted on both attempts, 0 output; do not demote; check kimi quota before assigning until cycle resets.

- 2026-08-18 (fable-chief, reactivation-center): codex lanes with writable_roots on a repo + specs saying "run from repo root" write ./notes.md into the REPO, not the task dir; expect_files then fails a green product and burns a retry (3 occurrences: parity-fix, workflow-edits, engine-lambda; one overwrote a tracked repo notes.md). Fix: specs must name the ABSOLUTE task-dir path for notes.md, or drop it from expect_files and let the check gate.

## z-ai/glm-5.2:free (pi-openrouter)

- 2026-08-19 — PROVIDER_RATE_LIMIT, not a model-quality result. Catalog digest asked for one short mechanical probe. OpenRouter lists `z-ai/glm-5.2:free` at $0 / 256k. Official `pi update --models` failed closed on a Kimi 400. OpenRouter-only Pi refresh found the exact id already present with a valid wrapper-shaped record. Run `glm-5-2-free-audition-20260819T121926Z-p2407688` reached OpenRouter, then Decart returned upstream 429 on the shared pool (retry-after 5s). Ringer 2 attempts, 0 tokens, no artifact, $0. Do not promote. Do not demote the model. Replay the same frozen probe later if the shared pool is no longer 429.

## claude-lean Sonnet (`engine: claude-lean`, `model: sonnet`)

- 2026-08-20 (revolution_CLI, revolution-cli-handoff-gaps, code-fix x2): 2/2 first-try PASS, ~93-96s each. Lane B: replaced a 5-site endswith write-gate with one exact-match helper plus 6 synthetic tests (29 green); lane C: rewrote a gateway route to send "Last, First" EHR queries with a scripted-runner fallback plus 5 tests (34 green). Both passed an independent coordinator seam probe, not just their own tests. Specs were fully self-contained (owned files, exact run command, boundary list, ROLE: EXECUTOR prefix); ownership verified by a pre-launch md5 tree snapshot because the repo's working files were untracked and worktrees mode was impossible. Good default for scoped Python fixes when Codex OAuth is down.
- 2026-08-20 same job, codex lanes: HARNESS_FAIL, not a model result. Codex OAuth session refresh failed on both runs ("already used" refresh grant, 401 on the responses websocket) while `codex login status` still said logged in; 0 work in ~6s across 2 attempts x 2 runs. Human re-login needed. Do not demote gpt-5.6-sol on this.
- 2026-08-20 local-shell evidence lanes: a vendor CLI's `--agent` redaction masked names/DOB/email but NOT phone numbers; raw payload in a task dir tripped the lane's own leak scan. Fixed by piping CLI stdout through a count-only reducer so the payload never lands. Rule: measure what a redaction flag masks before its output touches disk; keep a leak scan in every live-data lane.
- 2026-08-20 (revolution_CLI v8 rollout, codex apply lane): HARNESS_FAIL at launch, rc=64 in 0.1s x2, zero effect. The trusted engines/codex-oauth.sh wrapper allowlists only `-c model_reasoning_effort` and `-c sandbox_workspace_write.writable_roots`; `-c sandbox_workspace_write.network_access=true` is rejected fail-closed. Consequence: a sandboxed Codex worker has NO network under this wrapper, so terraform/aws/live-HTTP tasks cannot run on codex unless the task is `full_access: true`. Probe any new engine_args key with those exact args before a production lane. The same day, a second session had two live codex workers; expect OAuth refresh races whenever two Codex processes share ~/.codex/auth.json. Apply lane moved to claude-lean sonnet.
- 2026-08-20 (revolution_CLI v8 rollout, claude-lean sonnet as PRODUCTION apply worker): PASS, 2 attempts, ~584s. Attempt 1 gate failed only because the ECS deployment record read IN_PROGRESS one beat after `aws ecs wait services-stable` returned. On the "Fix it" retry the worker did NOT re-run the script: it recognized the apply had landed, re-read the service once (read-only), and wrote honest notes. Artifacts confirm a single terraform apply. Good judgment under a retry that could have been dangerous; the orchestrator lesson is to split mutate and verify into separate lanes so a verification flake never re-prompts a mutation. Codex could not take this lane (wrapper rejects network_access; see above).
- 2026-08-20 (reactivation entitlements, author-proof-receipts, claude-lean sonnet, code-feature): PASS first try, 309 s. Five-file ops-tooling brief (CloudWatch collector, readonly DB collector, bastion tunnel helper, checker with RED/GREEN selftest, two-task local-shell manifest) behind a ~30-assertion offline gate that the coordinator watched go RED on an empty dir before launch. The worker ran the full gate itself before finishing and its notes listed only executed steps. What carried it: every log emitter was quoted from the real handler (file and exact message), every path absolute, the gate script named as source material so the contract was readable, and the brief stated what the feature does NOT log so the worker did not invent a marker. One coordinator hardening after review (instance-id count by words, since `--output text` joins ids on one line). Keep claude-lean sonnet as the default for multi-file ops tooling when an executable gate exists.
- 2026-08-20 (reactivation entitlements V2, author-vet-recall-gate, claude-lean sonnet, code-feature): PASS first try, 611 s. Wrote a 370-line bash build gate (backend import-based semantics with stubs, frontend static wiring checks, tsc filtered to owned files because the checkout carries ~150 baseline TS errors, vitest on three files, ownership regex) and extended four existing Python gates to six product keys without weakening anything. It discovered the tsc baseline problem itself and reused the sibling gate's owned-file filter instead of asking. The brief named the grading gate as source material and required the gate to go RED on the unmodified repo with a product-key WHY as its FIRST failure; the worker pasted that exact RED line into notes. Pattern worth keeping: make the author prove its own gate RED before the build lane exists.
- 2026-08-20 (reactivation entitlements V2 round, build-vet-recall, claude-lean sonnet, code-feature, 11 owned files across backend and React/TS frontend with three test files): product complete on attempt 1 (267+/57-, 24 tests green, tsc clean on owned files) but the task scored FAIL because the coordinator's gate had a pipe+heredoc defect in its tsc step. The worker reproduced the defect in isolation five times, named the mechanism correctly (heredoc overrides the pipe, printf SIGPIPE under pipefail), and wrote honest notes instead of editing files it did not own or faking a PASS. Scoreboard row is a HARNESS/CHECKER FAIL, not a model result; the product passed the corrected gate through a local-shell verify lane 13 minutes later. Lesson for orchestrators: RED-prove every executed stage of a gate with a synthetic input, not just the first assertion.
- 2026-08-20 same round, review swarm (claude on security-gate, claude-lean x2 on contract-seams and frontend-ux-tests): 3/3 first-try PASS on the review-swarm validator, 97-191 s. Findings were four P3s, all real and all non-functional (stale docstring count, unrestored window.open spy, missing badge test for the new key, comment wording). The frontend reviewer ran tsc and vitest itself as allowed and quoted result lines. Good calibration: no invented severity, clean sections, both sides of each seam cited. claude-lean is adequate for seam and frontend review when the brief enumerates the surface points; keep claude on the security surface.
- 2026-08-20 same round, fix-vet-recall-review (claude-lean, code-fix, three P3 findings across backend docstring and two test files): PASS first try, 64 s, delta exactly the three findings and nothing else; ran the full round gate itself before finishing.
