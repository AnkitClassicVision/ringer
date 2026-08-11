# Date Handling Architecture, rev 2 (post-panel)

Supersedes DESIGN.md (rev 1). Rev 1 was reviewed by three independent Codex
lanes (contrarian, verifier, operator) and correctly rejected as over-built and
carrying two logic errors. This rev implements their consensus recommendation.

## What changed from rev 1

- **Dropped compound tokenization and the gateway conflict engine.** Rev 1 put a
  natural-language parser into the shared gateway. The panel showed that turns an
  allowlisted grammar into substring interpretation on a PHI-adjacent gateway,
  and enables negation/correction misreads ("July 28, no, tomorrow"). Removed.
- **Corrected two factual errors in rev 1.** (a) A yearless month/day DOES depend
  on the reference date and timezone: the resolver picks the next non-past
  occurrence from Eastern `today` (bland_gateway.py:590-602). (b) The resolver
  returns `str | None`, so it cannot emit a "structured clarification" or bind a
  confirmation; `None` simply leaves `from` unresolved. The confirmation backstop
  therefore lives in the pathway (patient confirms the shown date), not the gateway.

## The measured facts this rests on

- The resolver `resolve_relative_date` is exact-match, branch by branch. Every
  accepted phrase returns before the final `return None` (bland_gateway.py:504-602).
  A new date form only ever reaches that final `return None`.
- Mott and CVC are **separate deployments of the same code**. `TENANT_ID` is a
  per-process env var (bland_gateway.py:52); consumer auth binds each caller to
  its tenant (bland_gateway.py:923). A change deployed to Mott's service does not
  touch CVC's running service.
- Bland exposes no raw-message variable, so date text must pass through a
  model-extracted variable (`preference_from` / `preference_to`).

## Layer 1: Gateway (Mott service only, behind an off-by-default flag)

Add one env flag `ECP_DATE_ORDINAL_FALLBACK` (module constant
`_DATE_ORDINAL_FALLBACK`, default False). Immediately before the final
`return None` in `resolve_relative_date`, add a legacy-first ordinal fallback:

    if _DATE_ORDINAL_FALLBACK:
        stripped = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1", t)
        if stripped != t:
            return resolve_relative_date(stripped)
    return None

Properties, all machine-proven by the differential gate:

- **Legacy-first:** the new code runs only on inputs the existing logic already
  failed to resolve. No accepted phrase, English or Chinese, can change. Zero drift.
- **Flag-off is byte-identical to today** for every phrase, so CVC (flag off) is
  provably untouched even though the code is shared.
- Strips an ordinal suffix only when attached to a 1-2 digit day, then re-resolves
  through the existing grammar. `july 28th` -> `july 28` -> existing `%B %d`
  path -> 07/28. `28th` -> `28` -> still None (no bare-day branch): fail closed.
  The recursion terminates because the stripped string has no ordinal.
- No compound parsing. No conflict rule. The gateway never sees a compound because
  Layer 2 sends a single token.
- Pre-existing behaviors are NOT touched (they would change CVC): the yearless
  Feb-29 -> Feb-28 mutation (line 597-601) stays as-is; documented, out of scope.

## Layer 2: Model extraction (Mott pathway, later lane)

One rule: **copy the single most explicit date token the patient literally typed;
never compute, translate, or invent a weekday.**

- Prefer an explicit month+day (`july 28th`, `july 28`) over a relative word
  (`tomorrow`) over a literally-spoken weekday (`tuesday`). Picking the most
  explicit token is ranking/extraction, not calendar math, so it cannot invent a
  weekday, which was the Kenneth failure.
- Put that one token in `preference_from`. Preserve the current build's
  `preference_to` contract exactly (verify in build_v62 before changing anything).
- `day_part` stays time-of-day only.

## Layer 3: Confirmation backstop (Mott pathway, decision approved)

The slot offer states the resolved calendar date in words, and the patient
confirms before any booking. This is the safety net for the model's imperfect
extraction (e.g. a correction the ranking rule misses): the patient sees the date
and can reject it before a write. Approved by Ankit 2026-07-27.

## Migration and isolation

1. Gateway first, Mott service only, flag ON only in Mott's deployment. CVC
   service is not redeployed and its flag stays off.
2. Verify with the differential gate (below) before deploy, then a read-only Mott
   canary with zero booking writes, then Ankit approves the exact image/service.
3. Then, separately, the Layer 2 + 3 pathway change (build_v62 -> v63).
4. Rollback: gateway is a flag flip (turn `ECP_DATE_ORDINAL_FALLBACK` off) or an
   image revert; because flag-off equals old behavior, rollback is exact.

## The differential gate (executed proof)

`gw-temporal-check/check_gateway_datefix.py` against a frozen golden baseline
(`golden_baseline.json`, Mon 2026-07-27 Eastern, 106 phrases):

- flag OFF: byte-identical to OLD for all 106 phrases (CVC-untouched proof).
- flag ON, 96 legacy phrases: byte-identical to OLD (no-regression proof).
- flag ON, 10 new ordinal phrases: resolve to the intended date and were None
  before; bare ordinals, bad calendar dates, and compounds stay None.

RED proof (already executed): run the check against the current unfixed gateway
and it fails on all 10 new phrases. The gate has teeth.

## What this still cannot do

- Cannot recover date words the model omits or garbles (no raw message). The
  Layer 3 confirmation is the backstop.
- Does not resolve a bare ordinal without a month, locale-ambiguous numeric
  dates, or a patient correction inside one message. Those fail closed or rely on
  confirmation.
- Does not change the pre-existing Feb-29 yearless mutation.
