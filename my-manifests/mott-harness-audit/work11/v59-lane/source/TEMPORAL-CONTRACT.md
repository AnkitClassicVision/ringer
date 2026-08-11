# Temporal contract — canonical (rev 3: Monday probe results, Codex Q1/Q2 corrections)

Owner decision: Ankit, 2026-07-26. Rev 2 incorporates the binding Codex rulings
(R1.1, R5.3, R5.6, R5.7), Gemini's H2 alternative and probe addition, and the owner's
same-evening ask-don't-guess amendment.
Supersedes: the conflicting instructions in graph/build_v57.py PREFERENCE_VARS and the
bare-weekday guidance at graph/build_v56.py:59 / build_v57.py:59.

## 1. Semantic rule (owner's, settled)

A week qualifier ("next week", "nxt wk", 下周) means the **calendar week AFTER the
current one, anchored on Monday**. On a Monday, "tues nxt wk" means eight days out,
never tomorrow, because tomorrow's Tuesday belongs to the current week.

Target-date table (what the patient MEANS), for "tuesday next week" by day of send:

| today is | current wk (Mon-anchored) | patient means |
|---|---|---|
| Mon 07/27 | 07/27–08/02 | Tue 08/04 |
| Tue 07/28 | 07/27–08/02 | Tue 08/04 |
| Wed 07/29 | 07/27–08/02 | Tue 08/04 |
| Thu 07/30 | 07/27–08/02 | Tue 08/04 |
| Fri 07/31 | 07/27–08/02 | Tue 08/04 |
| Sat 08/01 | 07/27–08/02 | Tue 08/04 |
| **Sun 08/02** | 07/27–08/02 | **Tue 08/04** |

A vague "next week" with no day means the Monday–Friday span of that same target week.
A bare weekday with no qualifier means the soonest occurrence of that weekday.

## 2. Measured gateway behavior (wire encoding, evidence to date)

The gateway resolves phrases against its own clock. Three same-day data points from ONE
measurement session, **Sunday 2026-07-26** (two probes, one live scenario — not three
independent sessions; Codex R5.3):

| sent | gateway returned | owner target | match? |
|---|---|---|---|
| `monday next week` (probe) | 08/03 | 07/27 | **NO, +7d** |
| `wednesday next week` (probe) | 08/05 | 07/29 | **NO, +7d** |
| `tuesday next week` (live scenario, offered slots) | 08/04 | 07/28 | **NO, +7d** |

Working hypothesis H1: **the gateway anchors weeks on Sunday.** Under H1 all three
data points are exact, and Sunday is the ONLY day the gateway's resolution of a
qualified weekday diverges from the owner's target; Monday through Saturday they agree.

Alternative H2 (Gemini R3): the gateway resolves the weekday's next occurrence and adds
seven days. H1 and H2 predict identical Sunday outputs; they diverge on other days for
some phrases. The Monday probe's `monday next week` case discriminates (H1: 08/03; H2
with exclusive next-occurrence: 08/10).

**PROBE RESULT, gateway-verified Monday 2026-07-27 00:06 ET: H1 IS DEAD. H2 stands.**

| sent | returned | H1 predicted | H2 predicted | owner target |
|---|---|---|---|---|
| `tuesday` | 07/28 | 07/28 | 07/28 | 07/28 ✓ |
| `tuesday next week` | 08/04 | 08/04 | 08/04 | 08/04 ✓ |
| `monday next week` | **08/10** | 08/03 | **08/10** | 08/03 ✗ |
| `friday next week` | 08/07 | 08/07 | 08/07 | 08/07 ✓ |
| `next week` | 08/03 | — | — | 08/03 ✓ |

H2-exclusive fits all seven data points that test it across both measured days (the
bare `next week` observation has no H2 prediction — it supports the v59 span's start
phrase but does not test the hypothesis; Codex correction). Consequences:

- The divergence is NOT Sunday-only (rev-1 claim, now falsified). Under H2, `X next
  week` overshoots by +7 exactly when weekday X has already occurred this week or is
  today: the gateway adds a week to an already-next-week X. The set of broken phrases
  GROWS through the week (Monday: only `monday next week`; by Saturday: most of them).
- Conversely, bare `X` equals the owner's "X of next week" precisely in those wrapped
  cases — but choosing between the two forms requires knowing today's weekday, which
  the model deliberately does not. No static phrase-level encoding can express the
  owner's calendar-week semantics under H2. The gateway dependency (calendar-anchored
  `X next week` per §4, or an ambiguity flag) is therefore the ONLY complete fix.
- HAZARD found before certification: v58 maps a vague week to the span
  `monday next week`..`friday next week`. Under H2 on a Monday that is 08/10..08/07, an
  INVERTED range. Measured same probe: bare `next week` resolves to the owner-target
  week start (08/03), so the vague-week span encoding must move to
  from=`next week`, to=`friday next week` (pending reviewer approval).

## 3. Extraction rule for the pathway (proposed, pending approval)

- PRESERVE the week qualifier always. "tues nxt wk" → `tuesday next week`. Never strip
  to a bare weekday: on a Monday, bare `tuesday` books tomorrow, one week early — a
  worse error than the qualified overshoot, and one the send-window makes common.
- Vague week → from `next week`, to `friday next week` (v59 encoding; Codex Q1).
  The prior mapping, `monday next week`..`friday next week`, produces an INVERTED
  range on Mondays under H2 (08/10..08/07) and is banned. Pair-probe receipt,
  gateway-verified Monday 2026-07-27: from=`next week` to=`friday next week` returned
  136 slots spanning exactly 2026-08-03..2026-08-07, the owner-target week. Other
  send-days remain unmeasured for the pair.
- Bare weekday stays bare.
- The model never computes calendar dates. The gateway is the resolver.

## 4. OPEN DEFECT: weekday-qualified resolution overshoot (RELEASE-BLOCKING)

Superseding the rev-2 "Sunday-only" framing, which the Monday probe falsified: under
H2, `X next week` overshoots by +7 whenever weekday X is today or already past this
week. The broken set GROWS through the week (Monday: `monday next week` only; by
Saturday: most qualified phrases). Codex Q2 ruling, 2026-07-27: **the gateway fix is a
PRECONDITION for certification and campaign** — patient-visible dates and
re-negotiation are recovery mechanisms, not correct temporal behavior, and the owner's
directive that temporal behavior ship complete controls.

**Required gateway fix (either form):** resolve every qualified weekday against the
owner's Monday-anchored calendar week; or flag every request whose phrase-level
resolution would differ from the owner-target week — not merely Sundays — and let the
pathway route the flag to the owner's clarify question ("do you mean tomorrow, or the
week after?"), with the CLOSER week as the no-answer default (owner decision,
2026-07-26 evening). The model stays date-blind either way; the gateway knows the date.

**Interim exposure bounds, all enforced or verified in code:**
- Outbound weekend sends are hard-blocked in the sender (not just by practice).
- Every offer displays its explicit MM/DD/YYYY date; only the confirmation step may
  state a booking exists, and it names the exact dated time. Silent wrong-week BOOKING
  cannot occur; wrong-week OFFERING can, on any day, for qualified phrases naming a
  weekday at or before the current one, and the patient-visible date plus
  re-negotiation ("no, tomorrow" is an accepted form) is the recovery path. These
  bounds justify DIAGNOSTIC operation only; per Codex Q2 they do NOT justify
  certification or campaign while the gateway defect stands.
- Suite certification additionally requires the gateway fix above; the Mon–Sat window
  (§5) remains as the second, independent condition.

## 5. Proof obligations and certification window

- **Monday 2026-07-27 resolver probe** (Codex-required before any campaign):
  `tuesday`→07/28, `tuesday next week`→08/04, `monday next week`→08/03,
  `friday next week`→08/07, plus bare `next week` as a range discriminator. Compare
  returned slot DATES, not HTTP status. The probe self-calibrates the gateway's day
  (resolve "tomorrow", subtract one) and FAILS CLOSED off-Monday; a pass is reported
  as consistent-with, never proof-of, a hypothesis (Codex R1.5, R5.7).
- Suite assertions check **resolved dates** of offered slots against the owner-target
  week computed from the run date, plus clock floors, not just extracted strings.
- **Certification window: Monday through Saturday.** A Sunday suite run is diagnostic
  only and exits nonzero even at 30/30, because the documented divergence makes
  temporal assertions unrepresentative that day (resolves Codex R5.6).
- The Sunday divergence can only be re-measured on a Sunday; H1's prediction for
  2026-08-02 sends: `tuesday next week` → 08/11 (owner target 08/04).
