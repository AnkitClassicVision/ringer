# Throttle Verdict

VERDICT: THROTTLING-ONLY

## Summary

- The measured non-SMS pathway latency was approximately 1.5 seconds per turn on both v56 and v62, ruling out an inherent v62 slowdown.
- The slow SMS messages were `queued` with no error and later delivered, which fits transient carrier/provider throttling rather than a bot or hard-delivery defect.
- Today’s outcomes show 9 of 15 conversations delivered, 2 failed only because of deliberate STOP tests, and 0 stuck.

## Alternatives Ruled Out

- **Pathway and prompt:** The chat-endpoint test isolates pathway processing from SMS delivery. Both v56 and v62 completed turns in approximately 1.5 seconds despite v62’s extraction prompt growing from 15,600 to 28,700 characters. The parity rules out measurable latency from either the v62 pathway or the near-doubled prompt in the tested flow.
- **Gateway availability call:** The evidence does not show a gateway error or a pathway-side latency increase. The observed delay occurred after the message entered the provider/carrier path as `queued`, then cleared without an error. That status sequence does not support the availability call as the cause.
- **Hard delivery failure:** The slow messages later delivered, and none remained stuck. The only 2 failures among 15 conversations were deliberate STOP-test failures with error code 21610; 9 conversations delivered. This rules out a genuine delivery failure as the explanation for the slow messages.

## Throttle vs Opt-Out

The slow-message pattern was `queued`, no error, then delivered. That is a transient delay consistent with provider or carrier throttling.

The opt-out control produced a different terminal state twice: `failed` with error code 21610 after a deliberate STOP test. Because the slow messages did not show 21610 or a failed state, opt-out blocking does not explain them.

## What Would Change This

The verdict would change if new records showed materially higher v62 chat latency than v56, gateway-call timing that matched the SMS delays, a non-21610 failure affecting the slow messages, queued messages that never delivered, or recurrence across numbers without heavy texting. Any of those findings would weaken or refute the throttling-only diagnosis.

## Assumptions

- The approximately 1.5-second figures compare equivalent turns through the same non-SMS chat endpoint.
- The 28,700-character prompt was active in the measured v62 run.
- The status history correctly links each initially `queued` slow message to its later delivered state.
- The daily counts use one consistent scope: 15 conversations, 9 delivered, 2 intentional 21610 failures, and 0 stuck.
