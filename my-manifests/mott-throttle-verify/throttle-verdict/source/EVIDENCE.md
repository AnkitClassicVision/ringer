# Evidence: is the v62 SMS slowness only carrier throttling?

## Pathway latency (rules out bot/prompt as the cause)
Measured via the chat endpoint (no SMS, no carrier layer), same messages, both versions:
- v56: turns 1.5s, 1.5s, scheduling turn 1.5s
- v62: turns 1.5s, 1.5s, scheduling turn 1.6s
v62 is NOT slower than v56 at the pathway level, despite v62 having ~28,700 chars of
extraction prompt vs v56's ~15,600 (nearly double). The prompt-size increase added no
measurable per-turn latency. The pathway responds in ~1.5s on both.

## Delivery evidence (the actual symptom)
The owner tested by texting the live number ~15 times today (this is heavy for one
destination). Current message statuses across those 15 conversations:
- 9 delivered
- 2 failed, both error_code 21610 (these were an INTENTIONAL STOP/opt-out test)
- 0 stuck
Earlier in the day several agent replies showed status "queued" with no error and did
not deliver for minutes; those same messages have since moved to "delivered". A separate
plain probe also queued-then-cleared.

## Distinguishing the states
- A carrier OPT-OUT block presents as status "failed" + error_code 21610 (seen twice,
  from the deliberate STOP test).
- The slow messages presented as status "queued" + NO error, then delivered later. That
  is a transient provider-side queue / rate hold, not an opt-out and not a hard failure.

## Prior independent diagnosis
A separate reviewer (Codex) already diagnosed the queued-no-error pattern as a temporary
provider-side anti-abuse hold triggered by repeated sends to one destination, clearing on
its own, needing no reset.

## The claim to test
The v62 slowness the owner experienced is ENTIRELY transient carrier/provider throttling
of one heavily-texted number, now cleared, and NOT a pathway, prompt, gateway, or bot
defect.
