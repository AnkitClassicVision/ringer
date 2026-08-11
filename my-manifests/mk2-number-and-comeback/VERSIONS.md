# Mott scheduling — version genealogy (as of 2026-08-05)

Every version/lane: why it had to exist → what it produced. Canonical copies live in
OB_mybcat (topics `version-history` + `mott-scheduling`); this file is the local mirror.
OB_company is intended as a second destination but has no connected server on this surface.

## Pathway versions (Bland goal-loop)

| ver | why it had to exist | result |
|---|---|---|
| v96 | production baseline; linear flow couldn't negotiate dates ("in 2 weeks" → today's slots) | replaced by goal-loop; its 5 extractors frozen byte-for-byte as the compatibility contract |
| v103/104 | first goal-loop live tests | flow worked, first live booking; context misreads remained (owner: "flow great, intent clunky") |
| v111 | owner: bot "picks first words, not the whole sentence"; away-sentence bug; slower than v96 | away-override fixed; ~8s replies accepted under the 15s ruling |
| v113 | overnight-monitor stabilization era | surfaced booking-claim + wrong-pick classes |
| v114/115 | "1115" wouldn't book; typo "1040" → false booking claim, off-grid time | node-based single-slot pick, TIME-GRID + NO-BOOKING-CLAIM markers, anchor search |
| v116 | owner ruling: named time goes straight to confirm | per-branch confirm nodes, template-verbatim copy |
| v117 | accumulation; live during owner's "after one → nothing available?!" escalation | exposed the fabricated-negative class → red-team mandate, rounds 21-25 |
| v118 (draft) | round-21/22 working draft | never flipped; the diff-base that proved assertion 22 had teeth |
| v119 | red-team graph audit: compound conditions, router overload, no context anchor | context_date on all 5 webhooks, anchor_route enum, router diet, TIME-SILENT, 22 assertions; 11/11 battery; gauntlet #1 baseline 37/65 (invariants 65/65) |
| v120 | fuzz: "can someone call me?" got scheduling copy | office-referral edges (assertion 23); battery exposed week-anaphora wrong 5/6 → gateway lane 52; then 11/11 + 4/4 determinism receipt |
| v121 | gauntlet: "later one, unless u have after 4" → fabricated "nothing after 4" (no search ran) | NEGATIVE-REQUIRES-SEARCH routing + marker (assertion 24); 11/11 battery; replay now searches (offers real 4:15/4:30); owner's live test booked EXACTLY as confirmed — first zero-defect test |
| v122 | owner test: "the 15th?" (Saturday) → bare "no match", no reason | CLOSED-DAY copy + closed_day mapping (assertion 25); live-tested by owner (great) + Rachel (3 defects found) |
| v123 | Rachel v122 test: 下午 ignored (routing vocab EN-only), Sunday miss said "unavailable" on the ASK node | round-26: CLOSED-DAY on n_goal_ask, Chinese examples in offered-time edge (assertion 26); 11/11 battery; Rachel's 3 sequences replay-proven fixed |

## Gateway lanes (single-file overlays, byte-verified in ECR before deploy)

| lane | why | result |
|---|---|---|
| 38-43 | date interpretation moved from LLM to gateway (relative, week-of, ordinals, specificity, away, latest) | foundation era; lane-42 broke the 3am OOB flag, lane-43 fixed with reference-window bounds → both permanent live gates; handler-seam-proof + suite-floor lessons |
| 44-46 | id-pinned search regression + continuation (truth commit :63) | cumulative pytest tree becomes the contract |
| 47-48 | anchor-closest ordering silently flattened | ordering restored + permanent anchor live-gate pair |
| 49 | anchor_exact misreported | fixed; first deploy failed gates, redone same day |
| 50 | consume round-22 context_date; deterministic anchor_route enum | context routing live (taskdef :67); 11 standing live gates |
| 51 | gauntlet: bare hours read AM ("around 5"→5am), midnight, fortnight/eleven-days/end-of-month unparsed | meridiem inference, midnight OOB, vocab2, 91 tests; deployed :69 AFTER the ungated-deploy outage (~6-10 min, rolled back) → guarded-deploy pattern born |
| 52 | week-anaphora wrong 5/6 (extractor wording load-bearing) | resolve_anaphoric_week at handler seam: verbatim "that week" + context_date wins over extraction wording; 100 tests; :70; 4/4 live receipt |
| 53 | "fortnight from now" (no article), spelled ordinals, "tail end of next month" | 107 tests, gates RED-verified; shipped inside lane 54 |
| 54 | owner test: extractor hallucinated "3:00 am" for "either 3 or 4" → wrong closest (11am vs 4:15pm) | verbatim meridiem authority (strip invented am/pm, keep patient-stated) + closed_day flag; 116 tests; was live at :71 |
| 55 | battery: "No Thursday the 27" → extraction dropped the 27, invented "next week" → wrong Thursday | verbatim ordinal + that-weekday authority; 127 tests; shipped inside :73 |
| 56 | Rachel: "Friday afternoon" → morning offers twice (extraction dropped "afternoon") | verbatim day-part authority (morning/afternoon/evening windows, greeting guard); 137 tests; :73/:74 |
| 57 | coverage sweep: 18 safe-ask gaps in 6 families | vocab4 consolidated (week-after-next, following-week, month-parts, day-part idioms, verbatim windows, spelled clocks); 162 tests; :73; F6 spelled clocks = open item (offline-proven, not firing live) |
| 58 | Rachel: "any other later time?" → EARLIER slots; 下午 ignored by day-part table | later/earlier floor strictly past context_date time + Chinese day-parts; 174 tests; :74 |
| 59 | zh gauntlet: extractor garbled 下午 → 一午 after an English turn, suppressing the signal | live-text fallback when the verbatim copy has no time signal (verbatim still wins when it has one); 182 tests; live at :75 |

## Operational facts that keep biting

- Version flips are the owner's dashboard action (`/v1/sms/update` 500s).
- Cancel = `/sign` verb `appt.cancel` envelope; bare `/cancel` is 404.
- Deploys: 4-task guarded manifest (push, byte-verify, guarded deploy, live gates); rollback = one `update-service` to the prior revision.
- Never run the behavior gauntlet concurrent with a deploy.
- Test constants: repo `AGENTS.md`.
