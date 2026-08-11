# Date Handling Architecture

## Summary

- The model is a transport layer for patient-literal date text, not a calendar: it copies date cues into `preference_from` / `preference_to` and never derives or substitutes a weekday.
- `resolve_relative_date` becomes the deterministic calendar layer: it normalizes ordinals, recognizes explicit dates, and evaluates every cue in a compound phrase while preserving the deployed Monday-anchored week behavior.
- An explicit calendar date wins a disagreement with a relative cue; agreement is accepted, while unresolved ambiguity fails closed for clarification rather than searching a guessed day.

## Model Layer

The extraction guidance in `build_v62.py` should impose one rule: **copy the patient's date phrase; never calculate, translate, correct, or enrich it.** In particular, a weekday may appear in an extracted value only if that weekday token appeared in the patient's message. The model must not derive a weekday from a month/day, from `tomorrow`, from `next week`, or from conversation time.

For a single requested date or period, put the copied phrase in `preference_from` and leave `preference_to` empty. Use `preference_to` only when the patient explicitly supplies a second endpoint, such as “July 28th through July 30th”; each endpoint is copied literally. Do not manufacture a range endpoint.

| Patient wording | `preference_from` | `preference_to` |
|---|---|---|
| “july 28th” | `july 28th` | empty |
| “tomorrow” | `tomorrow` | empty |
| “next week” | `next week` | empty |
| “tuesday” | `tuesday` | empty |
| “tomorrow july 28th” | `tomorrow july 28th` | empty |

Keeping the whole compound in one variable is required because Bland exposes no raw-message variable. Dropping either cue would prevent deterministic conflict detection. The model may trim surrounding conversational words and whitespace, but it must preserve the explicit date tokens and their order. `day_part` remains only the patient's stated time-of-day preference, such as `morning`; it must not carry or reinterpret a date.

## Gateway Layer

`resolve_relative_date` remains the sole calendar authority. Its existing clean single-phrase grammar, including relative words, bare weekdays, and Monday-anchored week resolution, remains intact. Add a normalization and compound-parsing front end before that existing logic:

1. Lowercase and collapse whitespace without changing meaning.
2. Strip English ordinal suffixes only when attached to a numeric day token: `1st`, `2nd`, `3rd`, `4th` … `31st` become `1`, `2`, `3`, `4` … `31`. Conceptually, match a word-boundary day number followed by `st|nd|rd|th`, case-insensitively. Thus `july 28th` becomes `july 28`, and `28th` becomes `28`.
3. Recognize explicit month-plus-day and bare-day tokens in addition to the currently accepted single phrases. Resolve a month/day to the next non-past occurrence using the gateway's business timezone and reference date. Resolve a bare day only when the surrounding booking context supplies an unambiguous month; otherwise return a clarification error, not a guess.
4. Tokenize a compound into independently resolvable cues, for example `tomorrow` and `july 28`. Run the existing resolver semantics on each cue, then apply the conflict rule below.

The parser must validate real calendar dates and reject values such as February 30. This extension must wrap, not replace, the existing `next week` / week-family branch so the deployed Monday anchor is unchanged.

## Conflict Rule

If all cues resolve to the same calendar date, accept that date. On Monday July 27, both `tomorrow` and `july 28th` resolve to July 28, so the compound is corroborated.

If an explicit calendar cue and a relative cue resolve differently, the explicit month/day wins. It is the patient's higher-precision statement and does not depend on the message timestamp or timezone interpretation. The gateway should record a non-sensitive conflict reason for observability and the agent should confirm the selected explicit date before booking.

If two equally precise explicit cues disagree, or a cue cannot be resolved safely, do not search either guessed date. Return a structured clarification outcome. A bare weekday is not allowed to override an explicit month/day merely because the model placed it in the variable.

## Kenneth Walkthrough

Assume the gateway's local reference date is Monday July 27.

1. Kenneth says, “Tomorrow july 28th.”
2. The extraction guidance in `build_v62.py` copies `tomorrow july 28th` into `preference_from`; `preference_to` is empty and `day_part` is unchanged/empty. No weekday is generated.
3. `resolve_relative_date` normalizes the value to `tomorrow july 28`.
4. It resolves `tomorrow` from July 27 to July 28 and resolves `july 28` to July 28.
5. The cues agree, so the resolver returns 07/28. The gateway searches 07/28, never the invented Thursday 07/30.

## Migration

Deploy gateway support first. Add ordinal, explicit-date, and compound handling to `resolve_relative_date`, while regression-testing every currently accepted phrase and the Monday-anchored week cases. This is backward compatible with the current model output.

After that deployment is verified, independently deploy the `build_v62.py` extraction-guidance change that sends patient-literal phrases. Gateway-first avoids a window where the model emits `july 28th` or a compound but the old gateway returns 409. During rollback, revert the model guidance first; the expanded gateway can continue accepting the old clean phrases safely.

## What This Still Cannot Do

This design cannot recover date words the extraction model omits or alters because Bland provides no raw message. It cannot safely resolve a bare ordinal without month context, locale-ambiguous numeric dates, contradictory explicit dates, or timezone uncertainty without clarification. It also does not prove the model copied exactly; production monitoring should count 409s, clarification outcomes, and cue conflicts, with tests covering literal-copy failures and date-boundary cases.
