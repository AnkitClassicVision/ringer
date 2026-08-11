# HANDOFF — Mott scheduling agent (mk2-number-and-comeback)

CANARY: blue paperclip
Updated 2026-08-05 ~17:00 ET, mid-session (supersedes HANDOFF-2026-08-04-archive.md).
Operating rule (non-negotiable, from Ankit): **Fable = brain/decisions ONLY; ALL
implementation/probes/monitors run as Ringer lanes** (`cd /home/ankit114/repos/ringer &&
./ringer.py run …`, identity `fable-chief`, one run_name `mk2-number-and-comeback`, Ringside
HUD http://127.0.0.1:8700). Ankit flips pathway versions in the Bland dashboard
(`/v1/sms/update` 500s). Openers are coordinator-only, never a worker.

## Live state (verify, never assume)

- **Pathway: v123 bound to the 509 test line** (+1 509 561 1012). Verify via `GET /v1/sms/numbers`.
- **Gateway:** ECS `stack2` / `mott-booking-gateway`, taskdef **:75**, image **mott-lane-59**.
  Rollback = one `update-service` to :74 (printed in every deploy receipt).
- **Test identities** (also in repo AGENTS.md): Ankit Patel cell 6157793629 / patient 4362694474;
  Rachel Test cell 6468942428 / patient 4376662466; store 711. Rachel must be CLEAN before a
  test: cancel appts via `/sign` verb `appt.cancel` (reason MUST be `patient-request`; bare
  `/cancel` is 404, reason `test-cleanup` is a 422), delete her Bland conversations
  (`DELETE /v1/sms/conversations/<id>`), then send the opener
  (`checks/send_rachel_sample.py --agent-number +15095611012 --version <bound> --send` under
  secret_exec with HARNESS_PATIENT_ID/CELL/STORE env).

## What v123 + lanes 55-59 contain (all envelope-diagnosed, replay-proven)

Pathway rounds 19–26 and gateway lanes 47–58. Full genealogy: `VERSIONS.md` here + OB_mybcat
topics `version-history` + `mott-scheduling`. Today's last fixes (from Rachel's v122 live test):
"any other later time?" now floors strictly past the offered slot (was offering EARLIER);
Chinese day-parts 下午/早上/晚上/中午 window correctly (was repeating morning offers);
weekends say "The office is closed that day, we are not open weekends" (was "unavailable").

## Receipts already green (run records under ~/.ringer/runs, artifacts on the run page)

- v123 mint + 11-task battery: 11/11 first-attempt (workGLMS28).
- Rachel's three defect sequences replayed FIXED on v123 (scratchpad env123-later/zh/sun).
- Gateway: full standing gate stack + lanes 51–58 probes green on :74; byte-verify receipt
  (workVerify58b): mott-lane-58 = mott-lane-52 base chain + ONE full-file overlay byte-equal
  to `workR26/gw-later-floor-zh/fixed-bland_gateway.py`. NOTE: images 56/57/58 all sit on the
  lane-52 base with one full-file overlay each — functionally sound (the top layer wholly
  replaces the module); receipts assert top-layer byte-match + live gates, not tidy chains.
- Date/time coverage: 51-phrase sweep green (workCoverage57d) — zero wrong-answer classes;
  remaining misses fail SAFE (bot asks for a date).

## DAY-END STOPPING POINT (2026-08-05 ~19:00 ET) — pick up here

Bar was met and **v123 IS FLIPPED AND LIVE** on the 509 line. Receipts: EN gauntlet 65/65
(64 in the solo run `workFinalGauntlet/gl-final-gauntlet-en` + the recalibrated midnight
slice `workFinalSlice`), ZH gauntlet 6/6 (`workFinalGauntlet/gl-final-gauntlet-zh`),
battery 11/11 (workGLMS28), gates green on taskdef :75 / image mott-lane-59.

**Ankit's live v123 test: PERFECT** — Wednesday→Afternoon→Later→pick 2→YES booked
Wednesday 08/12 12:30 pm, schedule verified exact match, closeout copy correct.

PICKUP LIST — 2026-08-06 morning verification (runs workRachelV123 + workRachelV123b, both PASS):
1. ~~Ankit's test booking 08/12 12:30 pm~~ — **GONE from the schedule as of 08/06 ~09:15 ET**:
   appt-list for patient 4362694474 returns count 0 even with --include-past (same tool that
   saw it at wrap). Cancelled between wrap and now — NOT by this session. Nothing to cancel.
2. ~~Rachel's v123 test~~ — **NEVER RAN: she did not reply to the opener.** Raw conv detail
   (7f2f8002-…145b16): pathway v123 confirmed, opener delivered 2026-08-05T22:19:34Z with
   correct EN+ZH copy, exactly 1 message (AGENT), still active, parked at n_goal_ask,
   zero appointments for patient 4376662466. No defect, no booking, nothing to triage or
   cancel. Thread left ACTIVE deliberately — if she replies, the live test resumes on v123.
3. **Ankit's LIVE CHINESE RETEST PASSED (2026-08-06 ~09:40 ET)** — conv fe42be63 on v123:
   vague "下周什么时候有空" handled, ZH day-part+anchor fix proven live ("周三下午…两三点左右"
   → Wed 2:00/2:15 pm offers), booked Wed 08/12 2:00 pm, schedule EXACT match
   (appt 4390774072), cancelled via /sign patient-request, post-list 0. Lanes
   workAnkitRetest / workAnkitRetestV / workAnkitRetestC, all first-attempt PASS.
   Soft observation (not a defect): asked "Mon afternoon OR Wed/Thu", it offered Wed
   MORNING (no Wed day-part given yet — allowed interpretation, user steered, then correct).
   Rachel re-ping now optional — Ankit's ZH pass covers the second-human-datapoint gap.
   NEXT OPEN ITEM: production rollout discussion (real patient traffic policy, monitor,
   thread timeout toggle).

## 2026-08-06 afternoon — welcome-message edit incident and v124 (all receipts in this dir)

- Ankit hand-edited the welcome copy into LIVE v123 in the dashboard; the edit also flipped
  n_goal_ask userWait OFF and pushed the prompt to 2211 chars (>2200 cap). Round-26 validator
  vs live v123: 5/548 FAIL (workWelcomeVerify). Node diff: only n_goal_ask (prompt, userWait)
  + n_post_booking cosmetics.
- Fix: corrected draft = canonical round-26 draft + Ankit's welcome copy (whitespace-only trim
  2211→2195, visible-text equality asserted), validated PASS, minted **v124** (workMint124).
- **Ankit flipped the 509 line to v124** and live-tested via dashboard chat (no SMS thread):
  booked Tue 08/11 2:00 pm correctly on the real schedule; cancelled via /sign patient-request
  (appt 4391523571, workAnkitRetestC2, FINAL_COUNT=0). Verified bound: v124, userWait=True,
  prompt 2195, zh name present (workAnkitRetest3).
- **RESOLVED: v124 battery mystery → 10/10 GREEN.** The all-red workGLMS29 run was a DIRTY
  FIXTURE: Rachel's dummy patient had a residue booking (Thu 08/13 12:00, likely from the
  dashboard test panel which defaults to her sample data), so the identity webhook CORRECTLY
  routed every chat to n_post_booking/e_existing. Proof (workBatteryTriage): stored v124 ==
  sent draft (0 diffs); start markers identical v123/v124 (n_identity isStart); 6/6 chat
  repros on BOTH versions hit n_post_booking; battery turn-1 variables showed appt_count=1.
  Rachel cleaned (workRachelClean). Re-run workGLMS30: 9/10 first-attempt green; the one red
  (gl-smoke-away-sentence) was a STALE CHECKER (hardcoded 08/16-19 window from authoring
  date 08/04 rejecting a correct 08/20 offer) — recalibrated to dynamic +13..+21d windows
  (justification in workRedTeam/CALIBRATION.md), re-run green first-attempt (workGLMS30b).
  **v124 battery receipts complete: ready-for-list gate MET.**
  RULE for future batteries: task zero must be a Rachel clean-slate check, and all date
  windows in checks must be computed at check time, never hardcoded.
- **OPEN: 72h thread timeout has never saved** — sms_config time_out=null on three separate
  reads after two dashboard attempts. Needs another pass in the SMS config page (or the API
  path that currently 500s).
- **OPEN: standing drift monitor** promised to Ankit: scheduled lane running the
  live-vs-draft conformance check (manifest-live123-conformance pattern, retargeted at the
  bound version + draft-v124.json) so silent dashboard edits get caught automatically.
- Prevention rule agreed with Ankit: copy changes go through chat → validate → mint → he
  flips; if he dashboard-edits anyway, ping immediately for the 30-second conformance lane.

## 2026-08-06 PILOT LIVE — first real patient traffic (v124, 509 line)

- **10-patient recall list sent 10/10** (~12:30 ET) via `checks/send_recall_list.py`
  (coordinator-only, fail-closed preflight on bound version, masked receipts). List file:
  `/mnt/d_drive/repos/mott/recall/test list.csv` (PHI — path-only handoff, never in chat).
- Delivery truth (message-level, workDeliveryCheck): 9/10 delivered; conv 9b6b05 opted out
  (STOP honored, confirmation blocked by carrier 21610 = benign/expected); conv 9fb938
  opener undelivered (carrier 30003 unreachable handset) → retried ~17:00 ET as NEW conv
  a8d3c016 (not in monitor v4's list — check in evening pass).
- Snapshot #1 emailed to client owner **Kenneth Ma <kennethm@mkeyewear.com>** (msg id
  19fd8db15f798699, verified SENT; CSV of all threads attached; **deliberately NO HubSpot
  BCC — PHI attachment, HubSpot stays aggregate-only**). Promised him an updated snapshot.
- **Monitor v4 live** (workPilotMon4) until 23:59Z: per-thread digests, opt-out (incl.
  e_stop-family end nodes), delivery-fail, filler alerts, gateway cross-check on bookings.
- **HARD-WON: secret_exec buffers child stdout via communicate() until exit** — a
  long-running lane looks like a 0-byte hang while perfectly healthy. Two healthy monitors
  were killed on that false read. Standing pattern for long lanes: dual-write every line to
  a side `live.txt` (line-buffered, child-owned) and tail THAT; stdout still feeds the
  end-of-run check. Judge liveness from /proc fds or the side channel, never the wrapper's
  stdout file.
- PHI notes: two patient names + formatted cells briefly printed unmasked during list
  validation (regex missed (xxx)xxx-xxxx format) — mistake-ledgered; all tooling now
  last-4-mask only, no row echo, no message bodies in chat.
- Still open: 72h thread timeout NEVER saves (time_out=null, 3 reads); recurring drift
  monitor for silent dashboard edits; scale/rollout decision after pilot evidence.
- **2026-08-07 WARNING — do NOT reuse ANKIT_TAIL="5793629" from older manifests**
  (retest-prep/2/3, thread-clean): it is an off-by-one slice of cell 6157793629 whose true
  last-7 is "7793629". The wrong tail made every conversation-cleanup a vacuous no-op with
  passing checks. Standing pattern now: clean up by EXACT conversation id with post-delete
  GET=404 proof, and any suffix filter needs a known-positive sentinel before trusting 0.
4. Optional monitor on the live line (night-monitor manifest pattern) — park until rollout.

## Done at wrap (do not redo)

Truth committed+pushed through lane 59 (51794a0); VERSIONS.md and OB_mybcat genealogies
current through v123/lane-59; defect-triage tooling documented in the pickup list above.

## Open items (decided — do NOT relitigate without Ankit)

- **F6 spelled clock idioms** ("half past four", "quarter to five"): proven at the offline
  handler seam (`enforce_verbatim_clock_idiom_authority`, exact live-shaped inputs return
  anchor=16:30) but do NOT fire live; explicit anchors work live. Documented open item;
  revisit only if a real patient hits it. Debug evidence in the 2026-08-05 session log.
- **Accepted safe-asks:** negations ("anything but Monday"), holiday math ("after Labor Day"),
  "next Friday" ambiguity (reads as the nearest Friday). All degrade to asking for a day.
- **Chinese CLAIM-regex gap:** fuzz_runner's fabricated-booking-claim regex is English-only.
  Structural protection = booking-gate templates + node routing. Extend if Chinese volume grows.
- Parked with Ankit: SMS thread timeout (72h dashboard toggle; API 500s), reply-speed work
  (~8s replies, within his 15s ruling).

## Hard-won rules (violations caused real incidents — do not repeat)

1. **Deploy manifests are HAND-AUTHORED per deploy, never cloned-and-string-replaced.** Chained
   replaces corrupted base tags/asserts three times on 2026-08-05 (all caught fail-closed).
   Before launch, print BASE_TAG / NEW_TAG / BASE_REV / artifact path from the parsed manifest
   and eyeball them. Template: `manifest-gwdeploy22c.json` + `manifest-verify58b.json`.
2. **Every production-mutating task re-proves its preconditions in its own spec** (ECR tag
   exists + last-layer byte-match vs artifact) before `update_service`. Ringer serial order is
   NOT failure gating — later tasks run even when earlier ones failed. The one outage
   (~6-10 min, 2026-08-05 morning) came from violating this.
3. **Extraction nondeterminism must never be load-bearing.** Fix interpretation in the gateway
   at the handler seam, keyed on `user_verbatim` + `context_date`. Prompt tuning alone has
   never permanently fixed a defect class in this project.
4. **Measure n>=6 before believing a nondeterministic fix**; envelope captures (variables +
   reply per turn, diffed good-vs-bad run) are the diagnosis tool. A 2-run A/B lied once.
5. **RED before green:** validator assertions watched failing on the prior draft; live gates
   watched failing pre-deploy. This caught checker defects repeatedly.
6. **Gauntlet validity:** solo runs only; triage the honest webhook-fallback signature before
   calling failures behavioral; safety invariants ≠ behavior expectations; every recalibration
   needs written justification in `workRedTeam/CALIBRATION.md`.
7. **Inventory-dependent assertions must accept honest-empty** (windowed-or-empty) — the
   schedule moves under you as real bookings land.
8. **Local-shell discipline:** retries append prose bash chokes on — design for attempt-1 pass;
   all checks are FILES under `checks/`; `expect_files` lists FILES never directories; run
   `lint` separately (the serial warning exits nonzero — never gate `run` on `lint &&`).
9. Always `cd /home/ankit114/repos/ringer` before `./ringer.py` (cwd drifts constantly).
10. Mints are validate-then-mint in one task, unattached, Bland auto-increments; battery tasks
    read `VERSION=` from the mint task's mint.txt — never hardcode versions.

## Where everything lives

- Manifests/checks/work dirs: this directory. Key checks: `gw_gates*.py` +
  `check_gw_gates*.py` (live gate stacks, 49→58), `capture_envelope.py` (the workhorse),
  `fuzz_runner.py` (+ `fuzz-scenarios.json`, `zh-scenarios.json`, `CALIBRATION.md`),
  `gw_datetime_coverage.py` (51-phrase sweep), `gw_appt.py` (list/cancel), 
  `send_rachel_sample.py` (opener), `anaphora_ab.py` (A/B replays).
- Round/lane artifacts: `workR26/` holds BOTH the v123 pathway source
  (`gl-round26-fix/pathway-goalloop-draft.json`, validator with 26 assertions) and the deployed
  lane-58 gateway (`gw-later-floor-zh/fixed-bland_gateway.py`, 174-test cumulative suite in
  `gwtest/`). Earlier lanes: workGW5x / workR2x / workGLD31.
- Mint command: `python3 /home/ankit114/repos/mott-v21-snap/scripts/mint_graph_version.py
  <draft>` under secret_exec. Secrets: BLAND_API_KEY=mybcat/ai/api-keys/bland (JSON envelope —
  unwrap api_key|key|value), GW_TOKEN=conductor/agents/bland-mott/api-key (Bearer prefix).
  Never print secrets; never cat *.env/secret-named files; mask 7+ digit runs in outputs.
- Memory: OB_mybcat — Work Ledger checkpoints, both version genealogies, the lessons-learned
  reference, mistake-ledger entries (ungated deploy outage, gauntlet-during-deploy,
  clone-corruption). **OB_company has NO connected server on this surface — state the gap,
  never skip silently.**
- Frozen extractors: byte-identical through every round (`frozen-extractors.json`),
  validator-enforced; extraction changes are forbidden without Ankit.
- Gateway truth repo: `/home/ankit114/repos/gw-diag-snap`, branch `prod-truth-2026-08-04`.

## Suggested skills for the next session

`ringer` (load FIRST — HUD up before specs), `fable-chief-agent` (auto-loads on Fable),
`handoff` (when compacting again). Honor: AGENTS.md status-block format, single-line bash rule
(Stop hook enforces), Mistake Ledger for costly errors, no secrets/PHI in specs or captures.
