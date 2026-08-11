# KNOWN-GOOD Bland availability/scheduling wiring map

Source: `/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json`. Python traversal verified **42 nodes and 114 edges**.

## Availability nodes

### `n_search`: Search by preference (silent)

Type: `Webhook`. Endpoint: `POST https://mott-booking-gw.mail.mybcat.com/availability`.

Full body JSON:

```json
{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}","after":"{{time_after}}","before":"none","time_pref":"none","slot_minutes":"15","callID":"{{callID}}","user_text":"{{lastUserMessage}}","user_verbatim":"{{user_verbatim}}"}
```

Full `responseData` (`name` ← `jsonpath`):

```json
[
  {
    "name": "ok",
    "jsonpath": "$.ok"
  },
  {
    "name": "slot_count",
    "jsonpath": "$.result.count"
  },
  {
    "name": "slot_1_start",
    "jsonpath": "$.result.slots[0].start"
  },
  {
    "name": "slot_1_end",
    "jsonpath": "$.result.slots[0].end"
  },
  {
    "name": "slot_1_doctor",
    "jsonpath": "$.result.slots[0].doctor_id"
  },
  {
    "name": "slot_1_day_name",
    "jsonpath": "$.result.slots[0].day_name"
  },
  {
    "name": "slot_2_start",
    "jsonpath": "$.result.slots[1].start"
  },
  {
    "name": "slot_2_end",
    "jsonpath": "$.result.slots[1].end"
  },
  {
    "name": "slot_2_doctor",
    "jsonpath": "$.result.slots[1].doctor_id"
  },
  {
    "name": "slot_2_day_name",
    "jsonpath": "$.result.slots[1].day_name"
  },
  {
    "name": "time_pref_relaxed",
    "jsonpath": "$.result.time_pref_relaxed"
  },
  {
    "name": "conflict_option_1",
    "jsonpath": "$.result.date_conflict[3]"
  },
  {
    "name": "conflict_option_2",
    "jsonpath": "$.result.date_conflict[4]"
  },
  {
    "name": "date_conflict_detected",
    "jsonpath": "$.result.date_conflict[0]"
  }
]
```

Full `responsePathways` in evaluation order:

```json
[
  {
    "condition": "preference_from == unclear",
    "destination": "n_clarify",
    "destination_name": "Could not read the week they meant"
  },
  {
    "condition": "ok != true",
    "destination": "n_miss_unread",
    "destination_name": "Search rejected or unavailable"
  },
  {
    "condition": "day_part == outside",
    "destination": "n_miss_time",
    "destination_name": "Requested clock time is outside clinic hours"
  },
  {
    "condition": "date_conflict_detected == conflict",
    "destination": "n_date_conflict",
    "destination_name": "Two dates disagree"
  },
  {
    "condition": "slot_count == 0",
    "destination": "n_miss_empty",
    "destination_name": "Window checked and empty"
  },
  {
    "condition": "day_part == late",
    "destination": "n_page_3",
    "destination_name": "Asked for late in the day"
  },
  {
    "condition": "day_part == afternoon",
    "destination": "n_page_2",
    "destination_name": "Asked for the afternoon"
  },
  {
    "condition": "slot_count == 1",
    "destination": "n_offer",
    "destination_name": "One opening found"
  },
  {
    "condition": "slot_count >= 2",
    "destination": "n_offer",
    "destination_name": "Two or more found"
  }
]
```

### `n_page_2`: Afternoon openings (silent)

Type: `Webhook`. Endpoint: `POST https://mott-booking-gw.mail.mybcat.com/availability`.

Full body JSON:

```json
{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}","after":"{{time_after}}","before":"none","time_pref":"afternoon","slot_minutes":"15","callID":"{{callID}}","user_text":"{{lastUserMessage}}","user_verbatim":"{{user_verbatim}}"}
```

Full `responseData` (`name` ← `jsonpath`):

```json
[
  {
    "name": "ok",
    "jsonpath": "$.ok"
  },
  {
    "name": "slot_count",
    "jsonpath": "$.result.count"
  },
  {
    "name": "slot_1_start",
    "jsonpath": "$.result.slots[0].start"
  },
  {
    "name": "slot_1_end",
    "jsonpath": "$.result.slots[0].end"
  },
  {
    "name": "slot_1_doctor",
    "jsonpath": "$.result.slots[0].doctor_id"
  },
  {
    "name": "slot_1_day_name",
    "jsonpath": "$.result.slots[0].day_name"
  },
  {
    "name": "slot_2_start",
    "jsonpath": "$.result.slots[1].start"
  },
  {
    "name": "slot_2_end",
    "jsonpath": "$.result.slots[1].end"
  },
  {
    "name": "slot_2_doctor",
    "jsonpath": "$.result.slots[1].doctor_id"
  },
  {
    "name": "slot_2_day_name",
    "jsonpath": "$.result.slots[1].day_name"
  },
  {
    "name": "time_pref_relaxed",
    "jsonpath": "$.result.time_pref_relaxed"
  }
]
```

Full `responsePathways` in evaluation order:

```json
[
  {
    "condition": "ok != true",
    "destination": "n_miss_unread",
    "destination_name": "Search rejected or unavailable"
  },
  {
    "condition": "time_pref_relaxed != ",
    "destination": "n_offer_near",
    "destination_name": "Band empty, closest offered instead"
  },
  {
    "condition": "slot_count == 0",
    "destination": "n_miss_thin",
    "destination_name": "Nothing in the afternoon that day"
  },
  {
    "condition": "slot_count >= 1",
    "destination": "n_offer_2",
    "destination_name": "Afternoon openings found"
  }
]
```

### `n_page_3`: Late openings (silent)

Type: `Webhook`. Endpoint: `POST https://mott-booking-gw.mail.mybcat.com/availability`.

Full body JSON:

```json
{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}","after":"{{time_after}}","before":"none","time_pref":"late","slot_minutes":"15","callID":"{{callID}}","user_text":"{{lastUserMessage}}","user_verbatim":"{{user_verbatim}}"}
```

Full `responseData` (`name` ← `jsonpath`):

```json
[
  {
    "name": "ok",
    "jsonpath": "$.ok"
  },
  {
    "name": "slot_count",
    "jsonpath": "$.result.count"
  },
  {
    "name": "slot_1_start",
    "jsonpath": "$.result.slots[0].start"
  },
  {
    "name": "slot_1_end",
    "jsonpath": "$.result.slots[0].end"
  },
  {
    "name": "slot_1_doctor",
    "jsonpath": "$.result.slots[0].doctor_id"
  },
  {
    "name": "slot_1_day_name",
    "jsonpath": "$.result.slots[0].day_name"
  },
  {
    "name": "slot_2_start",
    "jsonpath": "$.result.slots[1].start"
  },
  {
    "name": "slot_2_end",
    "jsonpath": "$.result.slots[1].end"
  },
  {
    "name": "slot_2_doctor",
    "jsonpath": "$.result.slots[1].doctor_id"
  },
  {
    "name": "slot_2_day_name",
    "jsonpath": "$.result.slots[1].day_name"
  },
  {
    "name": "time_pref_relaxed",
    "jsonpath": "$.result.time_pref_relaxed"
  }
]
```

Full `responsePathways` in evaluation order:

```json
[
  {
    "condition": "ok != true",
    "destination": "n_miss_unread",
    "destination_name": "Search rejected or unavailable"
  },
  {
    "condition": "time_pref_relaxed != ",
    "destination": "n_offer_near",
    "destination_name": "Band empty, closest offered instead"
  },
  {
    "condition": "slot_count == 0",
    "destination": "n_page_near",
    "destination_name": "Too thin for late, offer the closest"
  },
  {
    "condition": "slot_count >= 1",
    "destination": "n_offer_3",
    "destination_name": "Late openings found"
  }
]
```

### `n_page_near`: Closest openings to a late request (silent)

Type: `Webhook`. Endpoint: `POST https://mott-booking-gw.mail.mybcat.com/availability`.

Full body JSON:

```json
{"store":"{{store}}","from":"{{preference_from}}","to":"{{preference_to}}","after":"{{time_after}}","before":"none","time_pref":"afternoon","slot_minutes":"15","callID":"{{callID}}","user_text":"{{lastUserMessage}}","user_verbatim":"{{user_verbatim}}"}
```

Full `responseData` (`name` ← `jsonpath`):

```json
[
  {
    "name": "ok",
    "jsonpath": "$.ok"
  },
  {
    "name": "slot_count",
    "jsonpath": "$.result.count"
  },
  {
    "name": "slot_1_start",
    "jsonpath": "$.result.slots[0].start"
  },
  {
    "name": "slot_1_end",
    "jsonpath": "$.result.slots[0].end"
  },
  {
    "name": "slot_1_doctor",
    "jsonpath": "$.result.slots[0].doctor_id"
  },
  {
    "name": "slot_1_day_name",
    "jsonpath": "$.result.slots[0].day_name"
  },
  {
    "name": "slot_2_start",
    "jsonpath": "$.result.slots[1].start"
  },
  {
    "name": "slot_2_end",
    "jsonpath": "$.result.slots[1].end"
  },
  {
    "name": "slot_2_doctor",
    "jsonpath": "$.result.slots[1].doctor_id"
  },
  {
    "name": "slot_2_day_name",
    "jsonpath": "$.result.slots[1].day_name"
  },
  {
    "name": "time_pref_relaxed",
    "jsonpath": "$.result.time_pref_relaxed"
  }
]
```

Full `responsePathways` in evaluation order:

```json
[
  {
    "condition": "ok != true",
    "destination": "n_miss_unread",
    "destination_name": "Search rejected or unavailable"
  },
  {
    "condition": "slot_count == 0",
    "destination": "n_miss_thin",
    "destination_name": "Nothing in the afternoon either"
  },
  {
    "condition": "slot_count >= 1",
    "destination": "n_offer_near",
    "destination_name": "Closest openings found"
  }
]
```

### How the four differ

- `n_search` is unbanded (`time_pref:"none"`). It uniquely handles unclear input, webhook failure, outside-hours input, date conflicts, empty results, and afternoon/late dispatch. It also maps the three conflict values.
- `n_page_2` requests `time_pref:"afternoon"`; relaxation goes to `n_offer_near`, zero to `n_miss_thin`, and a positive count to `n_offer_2`.
- `n_page_3` requests `time_pref:"late"`; relaxation goes to `n_offer_near`, zero continues to `n_page_near`, and a positive count goes to `n_offer_3`.
- `n_page_near` is the late-search fallback but requests `time_pref:"afternoon"`; zero goes to `n_miss_thin` and a positive count to `n_offer_near`.
- Otherwise, the bodies share the same parameters, including `after:"{{time_after}}"`, `before:"none"`, 15-minute slots, and `callID:"{{callID}}"`. The three follow-ups map the same 11 response fields; `n_search` adds three conflict fields.

## Variable provenance

### `{{time_after}}`

Every producing node found by scanning `extractVars`: `n_ask`, `n_date_conflict`, `n_miss_empty`, `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, `n_miss_time`, `n_negotiate`. The instruction text is identical in all eight. `n_ask` uses a six-element entry with trailing control flags; the other seven use a three-element entry.

Full extraction definition, quoted without omission (the six-element `n_ask` form):

```json
[
  "time_after",
  "string",
  "## Role\n- You are an earliest-acceptable-time extraction bot.\n- You monitor the conversation between the user and the assistant to determine the specific clock time the user wants to be seen AFTER for a new appointment.\n- Your only job is to extract that earliest acceptable clock time.\n\n## Default Behavior\n- If the user named no specific clock time, write none.\n- When in doubt, use the last clock time the user clearly asked for. Never extract null.\n\n## Critical Rules\n- Covers phrases like after 2, after 2pm, not before 3, 2 o'clock or later, anything after noon. Not before 3 means after 3.\n- A clock time the user rejects, or mentions only as context such as being busy until 2, still means they need a time AFTER it. Busy until 2 becomes 02:00 PM.\n- If they said only morning, afternoon, or late with no specific clock time, write none: the part of day is captured separately.\n\n## Interpretation\n- Write the time in 12-hour format with AM or PM, such as 02:00 PM or 10:00 AM.\n- Noon and 12pm both become 12:00 PM.\n\n## Null Prevention\n- This field must never be null or empty under any circumstances. Use none when no specific clock time was named.\n\n## Output Requirement\n- Return a 12-hour clock time with AM or PM, such as 02:00 PM, or the single word none.",
  false,
  false,
  true
]
```

Full producer/shape inventory:

```json
{
  "three_element_nodes": [
    "n_date_conflict",
    "n_miss_empty",
    "n_miss_unread",
    "n_miss_thin",
    "n_miss_unbookable",
    "n_miss_time",
    "n_negotiate"
  ],
  "six_element_nodes": [
    "n_ask"
  ],
  "three_element_definition": [
    "time_after",
    "string",
    "## Role\n- You are an earliest-acceptable-time extraction bot.\n- You monitor the conversation between the user and the assistant to determine the specific clock time the user wants to be seen AFTER for a new appointment.\n- Your only job is to extract that earliest acceptable clock time.\n\n## Default Behavior\n- If the user named no specific clock time, write none.\n- When in doubt, use the last clock time the user clearly asked for. Never extract null.\n\n## Critical Rules\n- Covers phrases like after 2, after 2pm, not before 3, 2 o'clock or later, anything after noon. Not before 3 means after 3.\n- A clock time the user rejects, or mentions only as context such as being busy until 2, still means they need a time AFTER it. Busy until 2 becomes 02:00 PM.\n- If they said only morning, afternoon, or late with no specific clock time, write none: the part of day is captured separately.\n\n## Interpretation\n- Write the time in 12-hour format with AM or PM, such as 02:00 PM or 10:00 AM.\n- Noon and 12pm both become 12:00 PM.\n\n## Null Prevention\n- This field must never be null or empty under any circumstances. Use none when no specific clock time was named.\n\n## Output Requirement\n- Return a 12-hour clock time with AM or PM, such as 02:00 PM, or the single word none."
  ],
  "six_element_suffix": [
    false,
    false,
    true
  ]
}
```

Thus `time_after` originates in LLM extraction on conversation, retry, conflict, and negotiation nodes and may be refreshed before a later search.

### `{{callID}}`

No node has an `extractVars` entry named `callID`, and no graph-level field declares or assigns it. The only occurrences are consumers in the four availability body strings. The artifact therefore establishes `callID` as Bland runtime/system context, not a pathway-produced variable. It does not expose the lower-level binding, so no more specific origin is provable from this JSON.

## Offer prompts

### `n_offer`: Offered, first openings

Relevant verbatim sentences:

> If they ask for something later in the day, a different time of day, or the latest you have, do NOT name any time: say you will look and take the path for later in the day.

Semantic check: No factual slot claim about afternoon, lateness, or closeness. Its instruction to route later-day requests is consistent with its edge to `n_page_2` and the unbanded source query.

### `n_offer_2`: Offered, afternoon

Relevant verbatim sentences:

> They are in the afternoon.

> If they ask for something later still, or the latest you have, do NOT name any time: say you will look and take the path for later in the day.

Semantic check: True for its only inbound route, assuming the gateway honors `time_pref`: `n_page_2` asks for afternoon and diverts any non-empty relaxation marker before the positive-count route.

### `n_offer_3`: Offered, late in the day

Relevant verbatim sentences:

> They are late in the day.

> These are as late as this day goes.

> If they want something later, say plainly that this is the latest the office has that day and offer to look at another day.

> Never suggest there is anything later that day than these two.

Semantic check: “Late” is true under the same gateway-contract assumption because `n_page_3` asks for late and diverts relaxed results first. “Latest/as late as this day goes” is not proven: no mapped field says the returned pair are the final slots of the day.

### `n_offer_near`: Offered, closest to what they asked for

Relevant verbatim sentences:

> This patient asked for something LATE in the day and that day does not have one.

> These two are the closest the day has, and they are earlier than what was asked for.

> I don't have anything that late that day.

> The closest I have is {{slot_1_day_name}} {{slot_1_start}} or {{slot_2_day_name}} {{slot_2_start}} at MK2 Optical.

Semantic check: Not true on every inbound route. It fits relaxed late results and the late-zero → afternoon fallback. But `n_page_2` can also send a relaxed afternoon request here, so “asked for LATE” is false on that route. “Closest” relies on gateway relaxation/ordering semantics and is not independently proven by a mapped response field.

## Dropped nodes

### `n_date_conflict`: Clarify conflicting dates

- Type: `Default`
- Purpose: clarification. Its prompt says, “The patient gave two dates that disagree.” It asks, “Did you mean {{conflict_option_1}} or {{conflict_option_2}}?” and re-extracts the selected preference before returning to search.
- Inbound edges:
  - `n_search -> n_date_conflict` [date_conflict_detected == conflict]
- Outbound edges:
  - `n_date_conflict -> n_search` [patient chooses one conflicting date]

### `n_help`: HELP response

- Type: `Default`
- Purpose: global HELP/INFO response. Its prompt identifies the scheduling assistant, gives the help number and STOP instruction, and says booking continues. Metadata sets `isGlobal:true` and `enableGlobalAutoReturn:true`.
- Inbound edges:
  - None in `edges`; the HELP node is invoked globally.
- Outbound edges:
  - None in `edges`; HELP returns through global auto-return metadata.

## EDGE LIST

Every explicit edge touching the nodes covered above (56 edges):

- `n_ask -> n_search` [says any day, weekday, date, week, weekend, or time preference — including Saturday, this weekend, next week, or a month and day]
- `n_date_conflict -> n_search` [patient chooses one conflicting date]
- `n_miss_empty -> n_search` [names any day, weekday, date, week, or weekend — including Saturday, Sunday, this weekend, next week, or a month and day]
- `n_miss_unread -> n_search` [names any day, weekday, date, week, or weekend — including Saturday, Sunday, this weekend, next week, or a month and day]
- `n_miss_thin -> n_search` [names any day, weekday, date, week, or weekend — including Saturday, Sunday, this weekend, next week, or a month and day]
- `n_miss_unbookable -> n_search` [names any day, weekday, date, week, or weekend — including Saturday, Sunday, this weekend, next week, or a month and day]
- `n_miss_time -> n_search` [names any day, weekday, date, week, or weekend — including Saturday, Sunday, this weekend, next week, or a month and day]
- `n_clarify -> n_search` [names any day, weekday, date, week, or weekend — including Saturday, Sunday, this weekend, next week, or a month and day]
- `n_recheck -> n_search` [looking again with the same preference]
- `n_offer_near -> n_which_intent` [both selects an opening and asks for a different day or time]
- `n_offer_near -> n_gate_1` [takes only the first opening offered]
- `n_offer_near -> n_gate_2` [takes only the second opening offered]
- `n_offer_near -> n_negotiate` [wants a different day]
- `n_offer_near -> e_declined` [declines this offer]
- `n_offer_near -> e_timeout` [72-hour timeout]
- `n_offer -> n_which_intent` [both selects an opening and asks for a different day or time]
- `n_offer -> n_gate_1` [takes only the first opening offered]
- `n_offer -> n_gate_2` [takes only the second opening offered]
- `n_offer -> n_page_2` [wants later in the day]
- `n_offer_2 -> n_which_intent` [both selects an opening and asks for a different day or time]
- `n_offer_2 -> n_gate_1` [takes only the first opening offered]
- `n_offer_2 -> n_gate_2` [takes only the second opening offered]
- `n_offer_2 -> n_page_3` [wants later still in the day]
- `n_offer_2 -> n_negotiate` [wants a different day]
- `n_offer_2 -> e_declined` [declines this offer]
- `n_offer_2 -> e_timeout` [72-hour timeout]
- `n_offer_3 -> n_which_intent` [both selects an opening and asks for a different day or time]
- `n_offer_3 -> n_gate_1` [takes only the first opening offered]
- `n_offer_3 -> n_gate_2` [takes only the second opening offered]
- `n_offer_3 -> n_negotiate` [wants a different day]
- `n_offer_3 -> e_declined` [declines this offer]
- `n_offer_3 -> e_timeout` [72-hour timeout]
- `n_offer -> n_negotiate` [wants a different day or time]
- `n_offer -> e_declined` [declines this offer]
- `n_offer -> e_timeout` [72-hour timeout]
- `n_negotiate -> n_search` [preference collected]
- `n_search -> n_clarify` [preference_from == unclear]
- `n_search -> n_miss_unread` [ok != true]
- `n_search -> n_miss_time` [day_part == outside]
- `n_search -> n_date_conflict` [date_conflict_detected == conflict]
- `n_search -> n_miss_empty` [slot_count == 0]
- `n_search -> n_page_3` [day_part == late]
- `n_search -> n_page_2` [day_part == afternoon]
- `n_search -> n_offer` [slot_count == 1]
- `n_search -> n_offer` [slot_count >= 2]
- `n_page_2 -> n_miss_unread` [ok != true]
- `n_page_2 -> n_offer_near` [time_pref_relaxed != ]
- `n_page_2 -> n_miss_thin` [slot_count == 0]
- `n_page_2 -> n_offer_2` [slot_count >= 1]
- `n_page_3 -> n_miss_unread` [ok != true]
- `n_page_3 -> n_offer_near` [time_pref_relaxed != ]
- `n_page_3 -> n_page_near` [slot_count == 0]
- `n_page_3 -> n_offer_3` [slot_count >= 1]
- `n_page_near -> n_miss_unread` [ok != true]
- `n_page_near -> n_miss_thin` [slot_count == 0]
- `n_page_near -> n_offer_near` [slot_count >= 1]

## WIRING

Preference-bearing nodes feed `n_search`, which validates the request and either offers unbanded openings or dispatches afternoon and late searches. `n_page_2` feeds afternoon offers; `n_page_3` feeds late offers; relaxed results feed `n_offer_near`; and a zero-result late search falls through `n_page_near`, which queries afternoon as the nearest fallback. All offers converge on selection gates, negotiation, decline, and timeout routes. `n_date_conflict` resolves one of two gateway-returned dates and loops to search; `n_help` is an edge-less global interruption with auto-return. Restoration must preserve eight `time_after` extractors and runtime-supplied `callID`, while recognizing that `n_offer_3` overclaims “latest” and `n_offer_near` has an afternoon-relaxation inbound route that contradicts its categorical late-request wording.

```json CITATIONS
{
  "CITATIONS": [
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_search\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_page_2\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_page_3\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_page_near\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_offer\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_offer_near\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_date_conflict\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"id\": \"n_help\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"time_pref_relaxed\""
    },
    {
      "file": "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v86.json",
      "quote": "\"date_conflict_detected\""
    }
  ]
}
```
