# ROOT CAUSE

VERDICT: NOT-REPRODUCED

The round-3 incident-time prefix does not reproduce the deployed raw-text result: `resolve_from_conversation` selects the newest USER message, which is `No the following Thursday`, and passes that whole message to `extract_date_from_text`; the executed result is `PREFIX_RESOLVED=NONE`. The extractor also returns `NONE` for that full text because its negation check kills candidate windows after the leading `No`, while `resolve_relative_date` has no pattern for `the following thursday`. The deployed 08/06/2026 is therefore not produced by the checked prefix harness or checked module. The isolation table proves only the final possible scan: if some unobserved deployed step reduced the phrase to bare `thursday`, `extract_date_from_text`'s one-token window would call `resolve_relative_date("thursday")`, whose bare-weekday branch returns the next future Thursday, 08/06/2026. Evidence identifying the missing reduction step, or showing a different deployed artifact/configuration at 2026-08-03T20:58:06Z, stands between this harness and the deployed behavior; phrase-picking versus artifact/runtime drift cannot be adjudicated from the supplied executed evidence.

# EVIDENCE

Literal round-3 output:

```text
PREFIX_MSGS=11
PREFIX_RESOLVED=NONE
EXTRACT(No the following Thursday)=NONE
EXTRACT(the following thursday)=08/06/2026
STAGE2(thursday)=08/06/2026
STAGE2(the following thursday)=NONE
STAGE2(following thursday)=NONE
STAGE2(thursday next week)=08/13/2026
OBSERVED_DEPLOYED=08/06/2026
CORRECT_TARGET=08/13/2026
```

These results reconcile as follows: the full correction message is rejected; a standalone extractor probe can still find the shorter bare-weekday window inside `the following thursday`; and the stage-2 resolver itself lacks following-weekday vocabulary. The round-2 full-conversation `PIPELINE_RESOLVED=NONE` is less incident-specific because later messages had already become the newest conversation state, while round 3 freezes the prefix at the incident and still returns `NONE`.

# MECHANISM

- `bland_gateway_live.py:853-869`: `resolve_from_conversation` filters USER messages, chooses the maximum `created_at` at lines 863-864, reads that message at line 867, and calls `extract_date_from_text` at line 868. In the supplied 11-message prefix, the selected message is `No the following Thursday`.
- `bland_gateway_live.py:637-652`: `extract_date_from_text` normalizes the complete selected message.
- `bland_gateway_live.py:668-702`: `no` is a negator, and `killed(start)` rejects a date candidate when a negator occurs before it. This accounts for executed `EXTRACT(No the following Thursday)=NONE`.
- `bland_gateway_live.py:588-602`: `resolve_relative_date` recognizes `weekday after next`, `weekday next week`, and then bare/this/next/on/coming weekday forms, but not `the following weekday` or `following weekday`. The executed STAGE2 table verifies those omissions.
- `bland_gateway_live.py:514-516,600-602`: when the input is bare `thursday`, the bare-weekday branch calls `next_weekday(3)` and returns 08/06/2026 from Monday 2026-08-03. This is the verified final scan that could explain the deployed date only if an unobserved step supplied bare `thursday`.
- `bland_gateway_live.py:841-849`: after candidate generation, the extractor prefers explicit, then bare ordinal, then the earliest successful window. This explains executed `EXTRACT(the following thursday)=08/06/2026`: its four- and three-token windows fail, but a later one-token `thursday` window succeeds and becomes the earliest successful window candidate.

# PROPOSED FIX

Add a resolver pattern immediately before the generic bare-weekday branch at `bland_gateway_live.py:600`, matching `(?:the )?following (weekday)` and mapping it to `calendar_weekday(weekday, 1)`. This gives both `the following Thursday` and `following Thursday` the same Monday-anchored next-calendar-week semantics as `Thursday next week`, while leaving `Thursday after next` unchanged.

Also change `extract_date_from_text` candidate scanning so a recognized multi-token following-weekday expression occupies its span and is selected before constituent one-token weekday windows. Without that extractor change, the new longer match may coexist with a bare `thursday` candidate and the current earliest-window rule can still preserve the wrong result. Correction-context handling is needed: a leading discourse `No` that rejects the prior offered date must not negate the replacement phrase. Scope this narrowly to correction-after-offer context, or to a grammar such as `^no\s+(?:the\s+)?following\s+<weekday>$`; do not globally remove `no` from the negator list because phrases such as `no Friday works` must remain rejected. Add the supplied correction cases and plain following-weekday cases to the corpus in the style of `gen_golden.py`, with a frozen clock and explicit prior-offer context where applicable.

# CVC PORTABILITY

The resolver vocabulary change is tenant-neutral and portable because it extends an existing English relative-date grammar without relying on Mott-specific data. The correction rule should be portable only where the caller supplies a trusted prior-offer context; otherwise a leading `No` remains semantically ambiguous. CVC should run the same frozen-clock corpus plus its existing negation regressions before adoption.
