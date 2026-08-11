# GW54: verbatim meridiem authority and closed-day flag

## What changed

- `enforce_verbatim_meridiem_authority(time_pref, verbatim_text)` is a pure function at the availability handler seam. The handler applies it before anchor routing and `clamp_availability_range` applies it before `user_verbatim` and `user_text` are removed.
- `availability_window_closed(store, from_value, to_value)` uses the existing `CVC_HOURS_JSON`, holiday list, and `_day_window` logic. The `/availability` result now includes `closed_day`.

## Exact meridiem trigger

The extractor's `am` or `pm` is removed only when all conditions hold:

1. `time_pref` is an `anchor=` clock with explicit `am` or `pm`.
2. The current verbatim text contains the same hour as digits, optionally with minutes, or as an English number from one through twelve.
3. The verbatim contains no `am`, `pm`, dotted equivalent, `morning`, `afternoon`, `evening`, `night`, `tonight`, `noon`, or `midnight` anywhere in the message.

The stripped anchor is parsed by the existing lane-51 rule: 1 through 7 resolve to PM, 8 through 11 to AM, and 12 to noon. Bare anchors and patient-stated meridiems remain unchanged.

## Closed-day semantics

`closed_day=true` only when every date in the resolved inclusive `from..to` window has no configured operating window, including configured holidays. A window containing any open day is false. Slot count is deliberately ignored, so an open but fully booked day remains `closed_day=false`.

## Known limitations

- Spelled-hour matching supports the English words one through twelve only.
- Meridiem words are treated message-wide, conservatively. A different clock with a meridiem in the same message prevents stripping.
- Unknown stores and unparseable or inverted date windows return false rather than claiming the clinic is closed.
