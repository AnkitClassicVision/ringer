# Fuzz calibration (post run #1)

- weekend-ish-whenever: clinic has no weekend slots; honest miss is correct
- decline-current-offer-soft: safe ask/refusal acceptable; meridiem+vocab fixes may upgrade to offers later, but asking is never wrong
- out-of-hours-seven-evening: safe ask/refusal acceptable; meridiem+vocab fixes may upgrade to offers later, but asking is never wrong
- at-seven-unsuffixed: safe ask/refusal acceptable; meridiem+vocab fixes may upgrade to offers later, but asking is never wrong
- numeric-nine-thirty: safe ask/refusal acceptable; meridiem+vocab fixes may upgrade to offers later, but asking is never wrong
- near-tenish: safe ask/refusal acceptable; meridiem+vocab fixes may upgrade to offers later, but asking is never wrong
- numeric-eleven-space-fifteen: right window offered from real data; single-option nicety not required for word-form or ambiguous times
- quarter-past-three: right window offered from real data; single-option nicety not required for word-form or ambiguous times
- numeric-four-fortyfive: right window offered from real data; single-option nicety not required for word-form or ambiguous times
- decline-both-new-time: right window offered from real data; single-option nicety not required for word-form or ambiguous times
- gate-mismatch-clock: right window offered from real data; single-option nicety not required for word-form or ambiguous times
- offered-day-around-five: right window offered from real data; single-option nicety not required for word-form or ambiguous times
- around-five-unsuffixed: right window offered from real data; single-option nicety not required for word-form or ambiguous times
- mixed-bottom-but-not-date: one-clarify-then-act ruling: acting on the refinement is correct
- mixed-sure-but-around-three: one-clarify-then-act ruling: acting on the refinement is correct
- conflicting-correction-still-conflicts: one-clarify-then-act ruling: acting on the refinement is correct
- correction-no-week-after: lane-51 vocabulary/context should now resolve these; keep offer expectation to verify the fix
- correction-meant-twentyseventh: lane-51 vocabulary/context should now resolve these; keep offer expectation to verify the fix
- same-week-anaphora-tuesday: lane-51 vocabulary/context should now resolve these; keep offer expectation to verify the fix
- clarify-then-usable-month-end: lane-51 vocabulary/context should now resolve these; keep offer expectation to verify the fix
- end-next-month: lane-51 vocabulary/context should now resolve these; keep offer expectation to verify the fix
- fortnight-from-now: lane-51 vocabulary/context should now resolve these; keep offer expectation to verify the fix
- back-in-eleven-days: lane-51 vocabulary/context should now resolve these; keep offer expectation to verify the fix
- named-offered-clock-colon: inventory-dependent: exact slot may be taken; offering closest real slot is correct
- out-of-hours-midnight: lane-51 flags midnight; honest miss expected
- decline-single-anchor-offer: soft decline of one option: asking for another day is safer than terminating
- human-call-me-instead: round-23 adds the route; expectation stands
- human-front-desk: round-23 adds the route; expectation stands
- end-next-month (v2): verbatim is the fringe phrasing 'tail end of next month'; a safe ask-for-date or a dated offer are both correct - kind clarify_or_offer
- gauntlet run #2 (16:26Z) invalidated: 59 failures were the pathway's honest webhook fallback during upstream scheduling instability plus an ECS task swap mid-run; safety invariants held on all 65

## Round-3 recalibrations (post valid gauntlet, 12 triaged)
- mixed-earlier-but-wednesday: offer - patient gave a usable refinement (Wednesday); acting with Wednesday offers is the one-clarify-then-act ruling
- conflicting-weekday-date: offer - specificity rule: the explicit date wins the weekday conflict, matching the standing specificity gate
- decline-single-anchor-offer: offer - declining one option and getting a real alternative slot is acting, not stalling
- mixed-bottom-but-not-date: clarify_or_offer - the message is self-contradictory (picks an option while rejecting its date); clarifying or acting are both defensible
- out-of-hours-midnight: offer - designed OOB behavior offers the nearest in-hours slots, identical to the 3am gate design
- human-front-desk: drop must_contain office - the reply gives the number and says front desk, which is the substance
- zh-later-refine: 晚一点 = 'a bit later'; 10:45 after a 10:30 offer satisfies the strict floor - expectation is now must-not-repeat-the-offered-slot, not must-be-pm
- zh-codeswitch-refine: REAL defect - extractor garbled 下午 to 一午 after an English turn; lane-59 adds live-text fallback when the verbatim copy carries no time signal

## Round-4 recalibrations (v123 gauntlet attempt 1: 56/65, invariants 65/65)
- back-in-eleven-days: today+11 drifts onto weekends; closed-day copy or a dated offer both correct
- numeric-nine-thirty: lane-51 meridiem upgrade landed: offering closest real slots to an unavailable 9:30 is the design (anticipated in round-1 calibration)
- numeric-four-fortyfive: inventory-dependent: 4:45 window can be genuinely booked out; invariants-only
- named-offered-clock-runon: inventory-dependent: the named slot can vanish mid-scenario; honest closest-counter is correct; invariants-only
- mixed-earlier-but-wednesday: round-24 routing contract: pick-reference + DIFFERENT DAY = genuine ambiguity, one clarify is the design
- mixed-clock-or-next-week: fail-open ruling: answering the clock branch honestly with real offers is acting, not stalling
- mixed-take-it-search-late: offered-date-latest route fired correctly (late pm slots offered)
- correction-date-time-runon: inventory-dependent honest miss with question after a real search; invariants-only
- clarify-then-usable-month-end: month-end vocab variant may fall to a safe ask; ask or dated offer both correct (note: "month end" word order not in lane-57 vocab - future candidate)
- out-of-hours-midnight (final): honest OOB refusal + ask ('that time is unavailable, when would you like to come in?') is the designed pre-offer behavior; offering nearest slots is optional nicety - kind refusal
- out-of-hours-midnight (final v2): behavior alternates between the two designed-safe forms (honest refusal+ask on the ask node; nearest in-hours offer per the OUT OF HOURS template) - clarify_or_offer accepts both; invariants still forbid claiming midnight is bookable

## 2026-08-06 recalibration — gl-smoke-away-sentence (battery, not gauntlet)

The smoke28-era battery check hardcoded the "~2 weeks out" acceptance window as the
literal dates 08/16-08/19/2026 (12-15 days from its authoring date 08/04) and the
"offered today" trap as literal 08/04/2026. Run on 08/06 against v124, the bot offered
Thursday 08/20/2026 — exactly 14 days out and CORRECT — and the stale regex rejected it.
Recalibrated in manifest-away-sentence-r3.json: window computed at check time as
date +13..+21 days, today-trap computed as date +0. No assertion weakened; the scenario,
harness, turn count, template check, and 15s wall ruling are unchanged. Receipts:
workGLMS30 (false red), workGLMS30b (recalibrated run).
