# Date-handling architecture: the real constraints (measured 2026-07-27)

## The failure that triggered this
A real patient texted "Tomorrow july 28th". The small node model extracted
preference_from = preference_to = "thursday". The next Thursday from Mon 07/27 is 07/30,
so the gateway correctly resolved "thursday" and offered 07/30 -- two days off. The model
COMPUTED a weekday (and got it wrong: 07/28 is a Tuesday, not Thursday) instead of
passing the patient's words through. Prompt rules already say "never work out a calendar
date yourself" and the model disobeyed. Four prior reviews called this the extraction
model's reliability ceiling; prompt-tightening is documented-insufficient.

## Hard constraint 1: Bland exposes NO raw-message variable
The full pathway variable set available to a webhook body is exactly:
BlandStatusCode, callID, campaign, channel, count, day_part, exam_type_id, from, now,
now_utc, ok, patient_first, patient_id, preference_from, preference_to, recall_cell,
recall_patient_id, recall_ref, slot_1_*, slot_2_*, slot_count, store, timezone, to, today.
There is NO variable holding the raw inbound patient text. Whatever reaches the gateway
MUST pass through a model-extracted variable. We cannot bypass the model.

## Hard constraint 2: the gateway resolver rejects raw / compound / ordinal phrasing
Measured against the live gateway resolver (resolve_relative_date in bland_gateway.py):
- "Tomorrow july 28th" -> 409 bad --from: unrecognized
- "tomorrow july 28"   -> 409
- "july 28th"          -> 409  (ordinal suffix rejected)
- "28th"               -> 409
- "tomorrow"           -> OK (07/28)
- "tuesday"            -> OK (07/28, next occurrence)
- "next tuesday"       -> OK (07/28)
- "july 28" / "aug 5" / "08/05/2026" / "2026-08-03" -> OK
The resolver's accepted grammar is in source/bland_gateway.py resolve_relative_date.

## Hard constraint 3: the model computes weekdays WRONG
The model must never infer or compute a weekday from a date. It rendered 07/28 as
"thursday". It cannot be trusted to derive a weekday.

## What is wanted
A design for how "any real patient date phrasing" reliably becomes the correct gateway
date, given the three constraints. It spans TWO layers and must say exactly what each does:
- The MODEL (extraction on n_ask / n_negotiate etc): the smallest, safest transformation
  that cannot invent a weekday. For example: copy the patient's most explicit date token
  verbatim; only emit a weekday word if the patient literally said that weekday; never
  derive one from a date or from "tomorrow".
- The GATEWAY resolver (bland_gateway.py resolve_relative_date): what it must additionally
  accept so the model can pass patient-literal phrasing through -- for example strip an
  ordinal suffix ("28th" -> "28"), accept "july 28th", and a rule for a compound carrying
  two date cues (prefer the explicit month-day; define conflict handling).
Also state where "tomorrow" is handled (the gateway already does it) and the rule when the
patient gives BOTH a relative word and an explicit date that agree, and when they disagree.
Note the Monday-anchored week fix already deployed; do not undo it.
