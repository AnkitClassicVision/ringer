# GW57 vocabulary round 4

## Scope

This change extends the lane-51 through lane-56 gateway only at the existing date and time authority seams. The patient's current-turn verbatim remains authoritative when extraction drops one of the six covered date/time families. Explicit extracted time bounds remain authoritative.

## Code locations

- `resolve_anaphoric_week`: adds context-required following-week and same-day-next-week forms.
- `resolve_verbatim_date_window`: adds standalone week-after-next and month-part windows.
- `enforce_verbatim_time_window_authority`: restores dropped patient-stated clock bounds.
- `enforce_verbatim_clock_idiom_authority`: converts half/quarter idioms into the existing `anchor=HH:MM` path.
- `enforce_verbatim_daypart_authority`: extends lane 56's guarded day-part mapping.
- `clamp_availability_range`: invokes those helpers before the existing normalization and unresolved-date behavior.

## Trigger regexes and mappings

| Family | Trigger | Mapping |
|---|---|---|
| F1 | `\b(?:the )?week after next\b` | Monday through Sunday containing `today + 14 days`; start clipped to today |
| F2 | `\b(?:the following week|the week after)\b` | Monday through Sunday after `context_date`'s week |
| F2 | `\bsame day next week\b` | `context_date + 7 days`, single-day window |
| F3 | `\bend of the month\b` | Current month day 25 through last day; start clipped to today |
| F3 | `\b(?:beginning of next month|early next month)\b` | Next month days 1 through 7 |
| F3 | `\b(?:middle of next month|mid next month)\b` | Next month days 10 through 20 |
| F3 | `\b(?:middle of the month|mid-month)\b` | Current month days 10 through 20, clipped to today; next month if day 20 passed |
| F4 | `\bafter lunch\b` | `after=01:00 pm` |
| F4 | `\b(?:lunchtime|around lunch)\b` | `after=11:00 am`, `before=02:00 pm` |
| F4 | `\bafter work\b` | `after=04:00 pm` |
| F4 | `\bfirst thing\b` | `before=12:00 pm`; default slot ordering is already earliest first |
| F5 | `\bbetween <clock> and <clock>\b` | First clock to `after`, second to `before` |
| F5 | `\b(?:no earlier than|not before) <clock>\b` | Clock to `after` |
| F5 | `\b(?:before|by) noon\b` | `before=12:00 pm` |
| F5 | `\b(?:no later than|by) <clock>\b` | Clock to `before` |
| F6 | `\b(half past|quarter past|quarter to) <hour> [am|pm]\b` | `:30`, `:15`, or prior hour `:45`, then existing anchor routing |

`<clock>` accepts a digit or the words one through twelve, optional minutes for digits, and optional am/pm. `<hour>` accepts digits or one through twelve. Bare clocks use lane 51 meridiem inference.

## Precedence and guards

- F4, F5, and F6 run only when `after` and `before` are absent/`none` and `time_pref` has no anchor.
- Existing anchors outrank all day-part windows.
- Existing `latest` behavior still blocks day-part inference.
- The lane-56 negative lookbehind still excludes `good morning`, `good afternoon`, and equivalent greetings.
- A valid explicit ordinal in verbatim outranks F2, including mixed phrases whose entire text survives extraction.
- F2 returns no override without a parseable `context_date` prefix.
- Lane-51/53 `end of this month`, `end of next month`, and `tail end` code is unchanged.

## Known limitations

- Clock idioms cover only the requested half-past, quarter-past, and quarter-to grammar. They do not interpret forms such as “twenty to five.”
- Month-part words use fixed requested bands rather than locale- or patient-specific meanings.
- Bare-hour meridiem retains lane 51's existing inference, including its ambiguity boundaries.
- The proof uses the host's `date.today()` as required. Production date resolution continues to use the gateway's Eastern-time helper.

## Verification

- `cd gwtest && pytest -q`
- `./proof_vocab4.py`
