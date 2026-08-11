# Temporal negotiation: architecture brief

The owner's diagnosis, and it is correct: this has been a sequence of fixes for individual
situations rather than a designed model of how time is negotiated. Each new phrasing a
patient used produced a new patch. This brief asks for the model itself.

## The job

A patient is texted to book an eye exam. Everything they say about WHEN has to be turned
into a scheduler query, and whatever comes back has to be turned into an offer they can
accept. That loop repeats until they take a time, decline, or drift out of scope.

The current design has three captured fields and a fixed three-page read. It fails
whenever a patient expresses time in a way those three fields cannot hold.

## Every temporal thing a real patient has actually said in testing

Each of these came from a live conversation or a scripted run against the live system.

| what they said | current outcome |
|---|---|
| "Tuesday afternoon" | works |
| "sometime next week" | works |
| "I need a late afternoon appointment next week" | works |
| "August 12 in the afternoon" | works |
| "what's the latest you have?" | works, but only within the current day's three pages |
| "anything later in the day?" | works, climbs one page |
| "anything later still?" | works, climbs to the last page |
| "the week after, say Wednesday" | works only because "wednesday next week" happens to parse |
| **"no, the week after that in August"** | **cannot be expressed; now asks for a date** |
| **"do you have anything later on any other day?"** | **answers about the current day only** |
| **"anything earlier?"** | **untested; no page moves backwards** |
| **"first thing in the morning"** | **untested** |
| **"any day, as long as it is after 4"** | **cannot be expressed: no day, only a time bound** |
| **"Monday or Wednesday, whichever is earlier"** | **cannot be expressed** |
| **"not Friday"** | **cannot be expressed** |
| **"in about a month"** | **cannot be expressed** |
| **"same time as last time"** | **cannot be expressed** |

The pattern in the failures is not a missing phrase. It is that the design holds a single
day window plus one part-of-day token, and a patient's sense of time is richer than that:
it has direction (earlier, later), relativity (than what you just said, than the week we
were discussing), exclusion (not Friday), open-endedness (any day, after 4), and memory
(same as last time).

## What the scheduler can actually do

Measured against the live gateway on 2026-07-26. Do not design around anything that
contradicts this.

`POST /availability` with `store`, `from`, `to`, `after`, `before`, `time_pref`,
`slot_minutes`. Returns `result.count` and `result.slots`, each slot with `start`, `end`,
`doctor_id`, `store_id`, `store_name`. Times are strings like `08/05/2026 12:30 pm`.

**`from` / `to` accepted:** a bare weekday (`wednesday` means the next one), a weekday with
a week qualifier (`wednesday next week` resolved to 08/05, `monday next week` to 08/03),
`a week from wednesday`, `tomorrow`, `next week`, month-and-day (`august 5`, `aug 5`,
`august 5 2026`, `august 12`, `8/5/2026`), and explicit dates (`08/03/2026`, `2026-08-03`).

**`from` / `to` REJECTED:** `august` alone, `the week after next`, `wednesday the week
after`, `wednesday in 2 weeks`, `next next wednesday`, `august 3rd` with an ordinal suffix,
`this week`, `in 2 weeks`, `next month`, `day after tomorrow`, `this weekend`.

**`after`, `before` and `time_pref` are accepted and then IGNORED.** A day with 27 openings,
22 of them afternoon, returns all 27 in time order whatever you send. This is a filed
gateway defect owned by another team and must be assumed unfixed.

**A range works and spans are capped at 14 days.** `monday` to `friday` returned 126
openings. `08/10/2026` to `08/14/2026` returned 135. A single day typically returns 18 to 27.

## What the platform can and cannot do

**Extraction into variables:** any fixed positive index (`slots[8].start`) works, the whole
list works (`slots[*].start`, `slots`), `.length` works. **Negative indexing does not.
Filter expressions do not.** There is no variable-indexed extraction: the index must be a
literal in the graph.

**Routing conditions** compare ONE variable against ONE string literal using `==`, `!=`,
`>=`. There is no AND, no OR, no substring test, and comparing against another variable is
unproven and must be treated as unavailable. Conditions are evaluated in order, first match
wins.

**An unfilled variable is substituted as JSON null**, which strips the quotes from a body
template and the gateway rejects it as a type error. The literal word `none` is accepted and
ignored, so it is the sentinel for "not specified".

**A node either waits for the patient or continues immediately.** It cannot do both.

**Interpolating a value into a prompt does NOT put it in the message.** The model composes
its reply freely and can name any time it has seen. A live patient was told 5:15 pm Friday
and booked at 11:30 am Monday because the node had been shown the whole day's list. The
current design therefore shows each offer node only its own two openings.

**There is no counter, no set-variable primitive, and no memory between nodes** beyond the
variables webhooks extract.

## The current design, for reference

Captured: `preference_from`, `preference_to` (day window, in the accepted forms above), and
`day_part` (exactly one of morning, afternoon, late, none).

`n_search` sends the window with `after`, `before` and `time_pref` hardcoded to `none`, then
routes on `day_part`: late goes to `n_page_3`, afternoon to `n_page_2`, otherwise `n_offer`.

`n_page_2` and `n_page_3` re-issue the identical search and read offsets 8/9 and 16/17 into
the same `slot_1_*` / `slot_2_*` names. Measured: offset 0 is morning, 8 is early afternoon,
16 is late afternoon, on all five weekdays, and the thinnest weekday holds 18 slots.

`n_offer`, `n_offer_2`, `n_offer_3` each show exactly two openings and can climb one page
later. Booking is per ordinal: a confirmation gate, then a conflict check, then the write,
with every payload field interpolated from a gateway-extracted variable.

## What is wanted

The MODEL, not more cases. Specifically:

1. **A representation of temporal intent** that can hold what patients actually express:
   direction, relativity, exclusion, open-endedness, and bounds without a day. State what it
   holds, what it deliberately cannot hold, and what the model must produce for each field
   given that a small model carrying more than one closed-class token per turn has failed
   three times in this project.

2. **A resolution rule** turning that representation into scheduler queries, given the
   accepted and rejected forms above, the ignored time parameters, and the 14-day cap. Say
   what happens when a request needs more than one query, and how many queries is too many.

3. **A navigation model** for moving through what came back: later, earlier, a different
   day, the latest, the earliest. The current design climbs three fixed pages one way only,
   using literal offsets, and cannot go back. Say whether paging is the right primitive at
   all given no variable indexing and no counter.

4. **A rule for what the patient is told** when their request cannot be served exactly:
   partially matched, out of range, unparseable, or empty. The current behaviour varies by
   accident of which node they happen to be on.

5. **Where each decision lives**: which are the model's, which are routing conditions, which
   belong to the gateway even if that means filing a dependency.

## Constraints no design may break

- Anything reaching a booking payload must be traceable to a gateway response, never
  composed by the model.
- The conflict check must be structurally impossible to skip before a write.
- A node must never present a time it cannot book, and never claim a day or a part of a day
  is empty unless it can actually see that.
- Only the confirmation step may say an appointment exists.
- Assume the ignored `after` / `before` / `time_pref` stay ignored. If a design only works
  once they are fixed, say so explicitly and give the interim shape as well.
