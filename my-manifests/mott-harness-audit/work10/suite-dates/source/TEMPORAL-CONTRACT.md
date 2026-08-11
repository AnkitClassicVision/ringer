# Temporal contract — canonical (DRAFT, pending Codex approval)

Owner decision: Ankit, 2026-07-26. Encoding analysis pending red-team review.
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

The gateway resolves phrases against its own clock. Three independent measurements, all
taken **Sunday 2026-07-26**:

| sent | gateway returned | owner target | match? |
|---|---|---|---|
| `monday next week` (probe) | 08/03 | 07/27 | **NO, +7d** |
| `wednesday next week` (probe) | 08/05 | 07/29 | **NO, +7d** |
| `tuesday next week` (live scenario, offered slots) | 08/04 | 07/28 | **NO, +7d** |

Working hypothesis H1: **the gateway anchors weeks on Sunday.** Under H1 all three
measurements are exact. Under H1, Sunday is the ONLY day the gateway's resolution of a
qualified weekday diverges from the owner's target; Monday through Saturday they agree.

H1 is a hypothesis fit to three same-day data points. It is NOT proven for other days.

## 3. Extraction rule for the pathway (proposed, pending approval)

- PRESERVE the week qualifier always. "tues nxt wk" → `tuesday next week`. Never strip
  to a bare weekday: on a Monday, bare `tuesday` books tomorrow, one week early — a
  worse error than the Sunday overshoot, and one the send-window makes common.
- Vague week → `monday next week` .. `friday next week`.
- Bare weekday stays bare.
- The model never computes calendar dates. The gateway is the resolver.

## 4. Known residual defect under this rule (accepted interim, filed upstream)

On a SUNDAY, a week-qualified request resolves one week late (per H1). Bounded harm:
every offer carries its explicit date, the patient confirms an exact dated time, and
navigation ("earlier", "another day") recovers. Wrong-week BOOKING cannot occur
silently; wrong-week OFFERING can. Outbound campaigns do not send on Sundays; inbound
replies on Sundays can hit this.

Gateway dependency filed: anchor relative-week resolution on Monday, or accept explicit
dates. Until fixed, this defect is documented, not hidden.

## 5. Proof obligations

- **Monday 2026-07-27 resolver probe** (Codex-required before any campaign):
  `tuesday`→07/28, `tuesday next week`→08/04, `monday next week`→08/03,
  `friday next week`→08/07. Compare returned slot DATES, not HTTP status.
- Suite assertions must check **resolved dates** of offered slots against the target
  week computed from the run date, not just extracted strings.
- The Sunday divergence can only be re-measured on a Sunday; H1's prediction for
  2026-08-02 sends: `tuesday next week` → 08/11 (owner target 08/04).
