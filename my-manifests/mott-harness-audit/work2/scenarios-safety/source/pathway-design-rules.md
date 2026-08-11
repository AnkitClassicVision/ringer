# Bland pathway design rules

Learned by building the Mott recall pathway from version 20 through 34, mostly by
breaking it in production. Every rule below cost a failed live conversation or a
real defect. Read this before designing or editing any pathway.

## Routing

**Comparison values in `responsePathways` must be STRING literals.** Write
`"true"`, `"false"`, `"1"` — never the boolean `true` or the integer `1`. Values
extracted from a webhook response arrive as strings, so a boolean literal never
matches, the node falls through to no condition at all, and the conversation stops
dead with no message and no timeout. A rebuild introduced 19 of 25 comparisons as
booleans and the pathway could not route past its first webhook for days.

**Never route a decision on a boolean field.** Route on counts, status codes and
string fields. `$.ok` and `$.success` are booleans and are unusable as decision
signals. Use `$.result.count`, `$.http_status`, or a string field the response
provides.

**Put the boolean health check LAST.** `["gw_ok", "!=", "true", -> failure]` as the
final pathway is an always-true catch-all, which is exactly what you want at the
end. Put it first and it fires immediately on every call. A mature production
pathway on the same account had it last; copying that ordering was the fix.

**Order the complement onto the conservative branch.** Some condition must always
match, and the one that catches the unknown case must be the safe outcome:

```
["conflict_ok", "!=", "true",  -> failure exit]   gateway did not answer cleanly
["overlap_id",  "!=", "",      -> negotiate]      anything but an explicit clear
["overlap_id",  "==", "",      -> book]           only an explicit clear books
```

A missing or malformed value then lands on "treat it as not clear" rather than on
"book it". Never let a complement land on a booking node.

**Cover the real value range.** A complement like `slot_count != "1"` catches zero,
two and twenty alike. Route the counts that actually occur and make sure the node
each one reaches is written for that case.

**Never compare against a template.** `["patient_id", "!=", "{{recall_id}}", ...]`
is unproven — whether the platform interpolates on the right-hand side is not
documented, and a guard that silently never fires is worse than no guard.

## Edges

**An edge needs a unique `id` and `type: "custom"` or it does not exist.** This is
not cosmetic. Webhook nodes route on `responsePathways` and globals fire on their
label, so a missing edge id breaks **only** conversational routing — the node
composes a reply and never transitions. It looks like the model ignoring you. The
canvas showing floating nodes with no connectors is the visible symptom of the same
cause.

Full edge shape:

```json
{"id": "edge-<source>-<target>-<slug>", "type": "custom", "animated": true,
 "source": "n_a", "target": "n_b", "sourceHandle": null, "targetHandle": null,
 "data": {"label": "...", "description": "...", "isHighlighted": false}}
```

**Every node needs `position`, `x`, `y`, `width`, `height`.** Without them the
canvas cannot lay the graph out and nobody can inspect or edit it.

**No duplicate node names.** Per the platform consultant: "make sure you change the
name if it didn't change automatically, otherwise routing issues." Unique ids are
not enough; the display names must differ too.

## Prompts

**The model running node prompts is small and does not infer context.** Structure
every patient-facing prompt as Background / Goal / Task / Never:

- **Background** — who the assistant is, where this patient stands, what has
  already happened, and what happens immediately after this node
- **Goal** — the single outcome this node exists to produce
- **Task** — numbered concrete steps
- **Never** — the prohibitions, *after* the context rather than instead of it

Prompts written as pure rules and prohibitions produce drift, fabrication, and the
model asking for values it already has. In the consultant's words: "it's clear to
me and you but it isn't a great understanding without giving more of an
understanding of the world within" and "the reason it's asking for a patient ID is
because it's unclear what it's supposed to do here."

**Tell a node it is inside a loop.** A negotiation node that does not know a search
runs immediately after it will behave as though it is the end of the conversation.

**You cannot reformat an interpolated variable.** The platform substitutes
`{{slot_1_start}}` into the message directly; the model never gets a chance to
transform it. Proven three times across three versions. Values must arrive already
formatted, from the gateway or a separate display variable.

**Never say a template is to be sent "verbatim" while also asking for rendering.**
Those instructions contradict, and the model resolves the contradiction by shipping
the raw value.

## Structure

**Only the confirmation node may claim a booking.** Structural gating stops the
*write*; nothing stops the *claim*. A negotiation node once told a live patient "I
have you down for 11:45" while nothing had been written, and then reinforced it on
the next turn. Every other patient-facing node needs an explicit prohibition on
saying or implying that an appointment exists.

**Detours auto-return; exits do not.** A node answering a question is part of an
answer-the-request loop and must set `enableGlobalAutoReturn: true` and end with an
explicit return to the goal. A node that ends the conversation must not.

**A timeout cannot be a global.** Globals fire by matching a patient message and
silence produces none. Wire the timeout as an explicit edge from every node that
actually waits on the patient.

**Silence after a confirmation is success, not a no-reply.** Most patients who
receive "you are booked" never answer. Route the post-booking timeout to the booked
outcome, or the ordinary success path records `no_reply` and the booking rate reads
near zero while bookings are actually happening.

**Anything reaching a write payload comes from a webhook response mapping, never
from model extraction.** This is what decides webhook versus tool call.
Conversational work may use a tool; anything that becomes a real record may not.

## Credentials

**A stored secret must hold the complete header value.** If the gateway expects
`Bearer <token>` and the secret holds the bare token, every webhook returns 401 and
the pathway looks like a routing failure. Check the gateway access log for the
platform user agent before debugging the graph.

**Expect propagation lag after updating a stored secret.** Calls seconds apart
resolved old and new values inconsistently, producing intermittent 401s that
self-healed on retry.

## Operations

**Build pathways by JSON import, not by hand in the canvas.** Recommended by the
platform consultant and it makes every rule above enforceable by a validator.

**Verify a booking against the source system, never against the message.** The
conversation saying "booked" proves nothing; the appointment appearing in the
practice system does.

**A conversation that reaches an end node is finished.** Replies to it are silently
discarded, so a patient who answers a terminal error message gets nothing back.

## Outcome tracking

There is no built-in outcome tracking. Design for that from the start.

**The pathway-level analysis schema may not persist.** On at least one account,
`analysis_options` submitted with a pathway version comes back null on readback,
and no version on the account carries one. Verify by reading the version back
rather than assuming the field was accepted.

**What does persist is an outcome tag on every terminal node.** Give each end node
a distinct outcome value — booked, declined, no_reply, office, wrong_person,
stopped, identity_failed, gateway_failed, booking_failed — and never let two
different failure modes share one tag, or downstream analytics cannot tell a
gateway outage from a patient-matching failure.

**Nothing collects those tags for you.** A campaign needs a separate collector:
either a post-conversation webhook on the line, if the gateway serves that route,
or a job that reads conversations by run and aggregates the outcome tags. Confirm
the route exists before pointing a line at it; an unauthenticated probe that
returns 401 for every path, including nonexistent ones, proves nothing.

**Verify a write against the source system, not the outcome tag.** The tag records
what the pathway believed happened. Only the practice or record system knows what
actually did.
