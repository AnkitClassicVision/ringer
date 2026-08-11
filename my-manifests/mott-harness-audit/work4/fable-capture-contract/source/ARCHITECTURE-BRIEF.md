# Mott recall pathway: architecture review brief

The pathway has been patched four times in one evening, each time against the last symptom
the owner reported, and it is still failing. The owner's diagnosis is that the work has been
local optimisation rather than architecture, and that is correct. This brief exists so an
architectural review can start from measured facts rather than from the patch history.

## What the system is

An SMS agent texts existing patients of an optometry practice to book an eye exam. It runs
on a conversational-pathway platform: a graph of nodes, where a node is either a small
language model with a prompt, or a silent webhook call. A gateway service stands between
the platform and the practice management system.

Flow today: identity lookup, then ask when they want to come, then search the schedule,
then offer times, then verify the chosen time, then write the booking, then confirm.

## Three failures from live conversations, all still open

### 1. Multi-field capture fails partially, and a partial capture is fatal

Latest live conversation. The patient chose a time and asked to book it:

```
chosen_start  = '07/28/2026 05:15 pm'    captured correctly
chosen_end    = None                     not captured
chosen_doctor = None                     not captured
```

The booking payload therefore carried nulls, the gateway rejected the request, and the
patient was told scheduling was unavailable. The prompt asked the model to copy three
values, character for character, out of a list it had been given. It copied one.

This is the THIRD instance of the same class. Earlier: five preference fields, where
"next week" landed in a date field that only accepts weekday words or dates, and
"afternoon" landed in a clock-time field. Measured failure rate on one phrasing was 2 runs
in 6. Each round of tightening the field descriptions moved the rate without fixing it.

The pattern: every time a small model is asked to carry structured data across a boundary,
some fields arrive wrong or empty, and empty is fatal because the platform substitutes an
unfilled variable as a real JSON null, which the gateway rejects as a type error.

### 2. The search window is set once and never re-scoped

Same conversation:

> **Patient:** "Do you have anything later than that on any other day?"
> **Agent:** "I only have availability for Tuesday, July 28th."

The first message said "Tuesday afternoon", so the search ran Tuesday to Tuesday. When the
patient asked about other days, nothing widened the window. The agent answered truthfully
about the data it held and completely missed the intent.

### 3. Positional slot reading cannot reason

Before the current version, the offer step read fixed positions out of the slot list:
position 0 and 1 for "soonest", position 8 for "afternoon", position 16 for "latest".

> "What's the latest I can come in" answered **3:00 pm**. The real answer was **5:15 pm**.
> "Anything later than that?" answered with a time EARLIER than the one just offered,
> because each search restarted from a fixed position with no memory of what was shown.

Giving the model the whole list fixed the reasoning: last time, times near a requested
hour, and total count all became correct against ground truth. But it introduced failure 1,
because a model that picks freely must then carry the payload for what it picked.

## Measured platform constraints, all verified

Do not design around anything contradicting these.

**Extraction of response data into variables:**

| expression | result |
|---|---|
| `$.result.slots[0].start` | works, any fixed positive index |
| `$.result.slots[*].start` | works, returns the whole list |
| `$.result.slots` | works, whole array of objects |
| `$.result.slots.length` | works, returns a number |
| `$.result.slots[-1].start` | **not supported** |
| `$.result.slots[?(@.start =~ /pm/)]` | **not supported** |
| `$.result.slots[?(@.start contains 'pm')]` | **not supported** |

So the whole list is reachable, but the platform cannot filter or index from the end.

**Routing conditions** compare one variable against one string literal, with `==`, `!=`,
`>=`. There is no AND, no OR, and no substring test. Comparing against a template such as
`{{other_var}}` is unproven and should be treated as unavailable.

**An unfilled variable is substituted as JSON null**, which strips the quotes out of a body
template. The gateway answers HTTP 400 `field 'x' must be a string`. The literal word
`none` is accepted and ignored, so it is the current sentinel for "not specified".

**A node either waits for the patient or continues immediately** (`skipUserResponse`). A
node that speaks and then waits cannot also act in the same turn.

**Interpolated variables cannot be reformatted by the model.** The platform substitutes the
value straight into the outgoing message. Proven three times.

## Measured gateway contract

`POST /availability` with `store`, `from`, `to`, `after`, `before`, `time_pref`,
`slot_minutes`. Returns `result.count` and `result.slots`, each slot carrying `start`,
`end`, `doctor_id`, `store_id`, `store_name`. Times are strings like `07/28/2026 05:15 pm`,
clinic local, with no human-readable variant.

- `from` / `to` accept weekday words, `tomorrow`, `august 3`, `08/03/2026`, `2026-08-03`,
  and now `next week`. They REJECT `august 3rd` with an ordinal suffix.
- **`time_pref`, `after` and `before` are accepted and then IGNORED.** Identical responses
  with and without them. A day with 27 openings, 22 of them afternoon, returns all 27 in
  time order regardless. This is a known gateway defect, filed, not yet fixed, and owned by
  another team.
- Spans are capped at 14 days.

`POST /conflict-check` with `store`, `doctor`, `start`, `end`. Returns
`result.overlapping_appt_id` and `result.reason`. A time that is not a real opening returns
`reason: "outside schedule template"` with an EMPTY overlap field, so both must be checked.
This is the only server-side validation that a proposed time is genuinely bookable.

`POST /sign` with `verb: appt.book`, `target`, `store`, `reason`, and params `doctor`,
`start`, `end`, `type`. This is the only permitted write.

## Non-negotiable constraints on any design

- Anything reaching a booking payload must be traceable to a gateway response. A booking
  must never be written from a value the model composed.
- The conflict check must be structurally impossible to skip before a write.
- Only the confirmation step may tell a patient an appointment exists.
- No patient-facing message may contain an internal field name or a raw identifier.
- No node may claim a day or time has no availability unless it can actually see that.
- The gateway defects above cannot be assumed fixed. Design for the gateway as measured.

## What the review needs to produce

Not a patch to the current graph. A judgement on whether this architecture can meet the
requirement at all, and if so what the right shape is.

Specifically: where should intent interpretation live, given that the model is the only
thing that can read intent and the least reliable thing to carry data? What is the minimum
the model must carry across a boundary for a booking to be safe, and can that minimum be
reduced to something a small model gets right every time? How should the search window be
scoped and re-scoped as a conversation moves? And which of the three failures above are
symptoms of one root cause rather than three separate bugs?
