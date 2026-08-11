# HANDOFF — Mott scheduling structural fix (fresh-context pickup)

CANARY: blue paperclip
Written 2026-08-04 ~12:00 ET by the fable-chief session. Working dir: `/home/ankit114/repos/ringer`.
Operating rules from Ankit, non-negotiable: **Fable/lead model = brain and decisions ONLY; ALL
implementation, monitoring, audit, probes, and model calls run as Ringer lanes** (`./ringer.py run`,
identity `fable-chief`, run_name `mk2-number-and-comeback` for everything — one artifact page).
Ringside: `./ringer.py hud` → http://127.0.0.1:8700.

## Source of truth (read these first, in order)
1. `my-manifests/mk2-number-and-comeback/WAYFINDER-MAP.md` — full decision/evidence log of both days.
2. `my-manifests/mk2-number-and-comeback/WAYFINDER-TICKETS.md` — per-ticket resolutions (T1–T9).
3. `my-manifests/mk2-number-and-comeback/workV94d4/amend-reference-point/SPEC-v94-draft4.md` — the
   approved goal-loop spec (persistent goal, UPDATE→ATTEMPT→RESPOND, reference-point search).
4. OB_mybcat: Work Ledger checkpoints under topics `mott`, `work-ledger` (session_/project_checkpoint).

## Live production state (verified)
- **Bland pathway v96 serves the 509 line** (Ankit flips versions in the Bland dashboard; agent
  number +15095611012, pathway id 94abad8b-fbe2-4e67-9c64-d9b586dd2653).
- **Gateway = ECS `stack2/mott-booking-gateway` taskdef :54, image `eyecloud-fargate-runner:mott-lane-38`.**
  Fully proven live: following-weekday vocabulary, offer-relative corrections (offered+7),
  weekday-ordinal compound rule, negation handling, and reference-point search
  (`time_pref: "latest"` returns true end-of-day descending; `time_pref: "anchor=HH:MM"` returns
  nearest-to-anchor; booked slots excluded — proven by book/requery/cancel probe; closed days
  return count=0). Rollbacks: taskdef :52 (pre-latest), :51, :50 — one `update-service` command.
- Gateway source of truth: `github.com/AnkitClassicVision/cvc-booking-gateway` branch
  `prod-truth-2026-08-03` (local clone `/home/ankit114/repos/gw-diag-snap`, 3 commits incl. deploy doc).
- Known v96 gaps (accepted floor): time-of-day asks can stall to office-referral; fillers present.

## The active build: goal-loop pathway (v96's replacement)
Five debug rounds so far, each fixed a Bland runtime-convention class and encoded it as a validator
assertion (all documented in the round DEBUG.md files):
1. Prose edge labels → must be executable conditions (`count == 1`) — `workGLD/`
2. Patient-facing waiting processor → silent auto-advance — `workGLD2/`
3. Generated guard node invented a time → derived-not-generated strategy — `workGLDER/`
4. Respond layer summarized/invented slot times → verbatim slot-variable wiring — `workGLD3/`
5. **ROUND-5 SMOKE RED → HARD STOP TRIPPED → the 2026-08-04 evening flip was CALLED OFF.**
   Evidence (workGLMS5, mint v101): one patient reply was the LITERAL unrendered template
   `{{slot_1_day_name}} {{slot_1_start}}`; the other scenarios hallucinated dates from 2018/2024.
   DIAGNOSIS: the derived loop's search webhook does not execute/populate variables at runtime in
   chat mode, even though its config is byte-derived from the working n_search. The template
   discipline worked; the data layer under it is dead.
- **NEXT SESSION'S FIRST LANE (the measurement rounds 1-5 never took): platform-level diff.**
  Drive one turn against LIVE v96 that fires n_search (e.g. "thursday please" after hi) and one
  against the loop mint (v101), capturing the FULL raw chat-response JSON both times (not just
  assistant_responses/current_node_id - everything: variables, webhook traces if present). Diff the
  envelopes. Suspects: the loop's search node may need the request body/URL/auth fields exactly as
  Bland stores them (check for fields the derivation dropped), the responsePathways wiring, or
  chat-mode requiring the webhook node to be reached via a specific edge type. Fix the derivation,
  add validator assertion #6, re-smoke. Do NOT attempt fixes before this measurement.
- v96+lane-38 is the standing floor; there is no urgency that justifies skipping the smoke gates.
- Mint discipline: validate-then-mint only (`workV95T8/t8-guard-builder/validate_and_mint.py` for
  v91-family graphs; goal-loop uses its own validator `check_goalloop_graph.py` + the same
  validate-before-mint sequence in one task). Minted-so-far: v97–v100 all unattached test mints
  (quarantined). Bland auto-increments; use the number from `VERSION=` in mint output.
- Smoke pattern: clone `manifest-gl-mint-smoke4.json`, repoint artifact paths, run. Checks assert:
  no promise copy (semantic list), no termination on valid dates, true late-day slots on the
  frozen ask, 08/14 convergence.
- After smoke green: full ladder = `workGL/gl-scenarios-builder/phase_run_goalloop.py <version>`
  (37 scenarios incl. this week's incidents) — **only after 17:30 ET** (standing gate: no sustained
  harness load during business hours Mon 11:00–17:30, Tue–Fri 10:30–17:30 ET). Then flip packet →
  Ankit flips → post-flip: re-trigger opener + his phone test + a night monitor lane.

## In-flight background tasks (check before starting anything)
- `bu0vlr7zs` — round-5 respond-wiring fix (codex, workGLD3).
- `bwbojk75k` — daytime promise-silence monitor (runs to 17:35 ET; output buffered by secret_exec
  until exit; exits 1 = ESCALATE → alert Ankit; exit 3 = monitor broken).
- Runs land in `~/.ringer/runs/mk2-number-and-comeback-*.json`; artifacts under the manifest dir's work* folders.

## Traps this session paid for (do not relearn)
- `./ringer.py lint` exits NONZERO on the "tasks will run serially" warning → never gate `run` on
  `lint &&` for serial pipelines; run lint separately.
- Shell cwd drifts (earlier `cd` persists); always `cd /home/ankit114/repos/ringer &&` or absolute paths.
- `secret_exec.py` BUFFERS child stdout until exit (transcripts appear empty mid-run; process liveness
  via `ps`/`/proc`).
- The Bland API key secret is a JSON envelope — unwrap `api_key|key|value` before use as auth header.
- `ECP_LLM_INTENT` gates the gateway LLM layer (default off); prod runs `authoritative`.
- Bedrock invoke works via the default AWS profile (grant added); `deploy-admin` SSO expires every
  few hours — re-auth via `aws sso login --profile deploy-admin --use-device-code`, Ankit approves
  the code from his phone (30s).
- ECR pushes are idempotent by content digest — treat LayerAlreadyExists/ImageAlreadyExists as success.
- 12-hour clock strings do not sort lexicographically — parse before comparing.
- Exact-string filler bans fail against generative paraphrase — ban the semantic class + wire
  template-literal copy.
- Local-shell retry appends failure prose to the spec (bash chokes) — treat local-shell retries as
  single-attempt; fix and relaunch fresh.
- Bland conversations: to END one, DELETE `/v1/sms/conversations/{id}` works (destroys history);
  PATCH with `is_active` boolean is the softer close. 97 stale threads were deleted — the old
  incident conversation records are GONE from the API (evidence preserved on disk in work dirs).
  **Consequence: the opener-sender needs Ankit's cell fresh** (it used to read it from a deleted
  conversation record). Ask him or use a current conversation.
- Opener sends are COORDINATOR-ONLY (never a Ringer worker):
  `checks/send_rachel_sample.py --agent-number +15095611012 --version <bound> [--send]` — its
  preflight fail-closes unless the line is bound to the exact version. Env: HARNESS_PATIENT_ID/CELL/STORE
  via `secret_exec.py --secret-env BLAND_API_KEY=mybcat/ai/api-keys/bland` (+ GW_TOKEN=conductor/agents/bland-mott/api-key for gateway calls).
- Test subject for harness work: the Rachel dummy (id/cell in existing manifests; harness masks digits).
  Ankit's personal cell: last4 3629 on record only — never print more.

## Ankit's standing rulings (embedded in the spec; do not re-litigate)
Hybrid interpretation stays; ONE clarify max then fail-open-to-search (never fail-stay); ≤15s answers,
fillers dead; clock times only from fresh slot data, only at offer steps; corrections = offered date +7;
reference-point search is the ordering primitive; true-latest for last-slot asks; valid dates never
terminate a conversation; unattached mints only; Ankit flips; no booking retry (until the offer_id/
idempotency layer from the spec's transactional section is built); CVC out of scope for now.

## Immediate next actions (in order)
1. Check `bu0vlr7zs` result → if green: clone mint-smoke manifest to `workGLD3` artifacts → smoke.
2. Smoke fully clean → hold for 17:30 ET → run the 37-scenario ladder vs the new mint → audit-worker
   review → flip packet to Ankit (include rollback + post-flip night-monitor lane + opener re-trigger).
3. Smoke not clean → tell Ankit the slip per the hard stop; capture state to OB; plan tomorrow's round.
4. After any flip: update MAP/TICKETS, OB Work Ledger, MODEL-NOTES (`docs/MODEL-NOTES.md`) if runs
   taught model lessons, and commit any new gateway truth to the GitHub branch.

## Suggested skills for the next session
- `ringer` (load FIRST — all execution goes through it; HUD up before specs)
- `fable-chief-agent` (auto-loads on Fable; brain/worker discipline Ankit demands)
- `handoff` (when compacting again)
- `agent-team` (if Ankit asks for ensemble diagnosis — run lanes AS Ringer tasks)
- `make-it-make-sense` (if Ankit says "make sense" — full protocol, no em-dashes)
Also honor: AGENTS.md status-block format, single-line bash rule (Stop hook enforces), Work Ledger
captures to OB_mybcat, Mistake Ledger for costly errors.

## Lessons locked in (2026-08-05, rounds 19-25 / lanes 47-54) — read before ANY new round

State at capture: v121 live on the test line; owner's live phone test booked exactly what he
confirmed (Friday 5:00 pm), verified via appt-list, then cancelled via /sign appt.cancel
(bare /cancel is a 404). First zero-defect owner test of the project. Lane-54 + round-25 in
flight; then guarded deploy → v122 mint+battery → solo gauntlet receipt → flip ping.

The rules that made it converge (full version in OB_mybcat, topics `lessons-learned` +
`mott-scheduling`; OB_company still has no connected server here):

1. Extraction nondeterminism must never be load-bearing. Move every interpretation to a
   deterministic gateway seam fed with user_verbatim + conversational anchors (context_date),
   and let it OVERRIDE the extractor's wording: anaphoric week → context week; extractor-invented
   am/pm on a bare-hour utterance → stripped and re-inferred; negative claims → only after a
   fresh search with that exact constraint (NEGATIVE-REQUIRES-SEARCH routing).
2. Measure with n>=6 per arm before believing a nondeterministic fix. A 2-run A/B said the
   anaphora fix worked; 6 envelopes said 5/6 broken. Envelope captures (variables + reply,
   diffed good-vs-bad run) pin every defect in one look.
3. RED before green: validator assertion watched failing on the prior draft; live gates watched
   failing against the pre-deploy service. No exception — this caught checker defects twice.
4. Serial task order is NOT failure gating. Ringer continues past failed tasks; any
   production-mutating task re-verifies its preconditions in its own spec (ECR tag exists +
   byte-match) before update-service. This rule exists because its absence caused a ~6-10 min
   live gateway outage (see mistake ledger `gwdeploy15-string-surgery-ungated-deploy`).
5. Never string-surgery serialized JSON manifests. Parsed-field edits + assert every referenced
   path exists. The outage's other parent.
6. Gauntlet validity: never run the behavior gauntlet concurrent with a deploy or heavy load —
   59/65 false failures from the honest webhook fallback (mistake ledger
   `gauntlet-during-deploy-window`). Triage failures for the fallback signature first. Safety
   invariants are separate from behavior expectations; recalibrate expectations to the DESIGN
   with written justification in workRedTeam/CALIBRATION.md.
7. Receipts that cannot drift: one run_name; battery reads VERSION= from mint.txt; truth commits
   only from byte-verified-in-ECR artifacts; booking verified end-to-end (asked == confirmed ==
   appt-list) before claiming success to Ankit.
