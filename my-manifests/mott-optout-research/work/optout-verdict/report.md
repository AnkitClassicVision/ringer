# Mott SMS Opt-Out Verdict

VERDICT: CARRIER-LEVEL-SUFFICIENT

## Summary

- Twilio's STOP block is attached to the sending phone number, so `messaging_service_sid = null` does not disable it.
- For the stated requirement that a patient who replies STOP is never texted again from that number, Twilio's HTTP 400 error 21610 is the compliance hard stop; an internal suppression READ is operationally useful but not required for that control.
- Make the sender's pre-send suppression READ best-effort: continue on GET 404, keep writing opt-outs internally, and confirm the Twilio block with the live STOP/resend/START test before launch.

## The Null Question

Yes, STOP-blocking still applies when `messaging_service_sid = null`. The staged evidence says Twilio block-lists the recipient against the **sending phone number**, not only against a Messaging Service. Each of the clinic's numbers is therefore protected at the phone-number level even though neither has a Messaging Service SID. On a later send from that same number to that recipient, Twilio rejects the attempt with HTTP 400 error 21610 until the recipient opts back in with START.

## Compliance vs Operational

**Compliance control:** For the compliance question defined here, Twilio's carrier-level block is sufficient independently of an internal suppression READ. After a recipient replies STOP, Twilio prevents another message from that sending number from being sent, returns error 21610, and does not charge for the unsent message. The batch sender cannot override that block.

**Operational control:** A local suppression READ would still have value. It could prevent futile send attempts, reduce 21610 noise, support an internal audit trail, and allow campaign reporting before requests reach Twilio. Those benefits do not make it a prerequisite for the stated compliance outcome because Twilio remains the final enforcement point. Continue writing opt-outs to the gateway so the internal record is retained.

## Minimal Change

Do **not** block launch on building a new READ endpoint. Change the batch sender's pre-send suppression lookup from fail-closed to best-effort: when the gateway returns GET 404 because no READ endpoint exists, skip that lookup and continue. Preserve the existing opt-out WRITE path. Treat Twilio error 21610 as the hard delivery stop and record that result as an opted-out rejection rather than retrying it.

This is the minimal change because the current launch failure is caused by the sender treating an unavailable optional lookup as fatal, while the phone-number-level Twilio block already enforces the required no-resend behavior.

## Confirming Test

Run this test separately for each actual sending number before a real campaign:

1. Send a test SMS from the specific clinic number to a controlled recipient.
2. From that recipient, reply **STOP** to that same sending number.
3. Attempt another SMS from the same sending number to the same recipient.
4. Pass only if Twilio blocks the resend and returns HTTP 400 error **21610**; verify that no SMS arrives and the attempt is unsent.
5. From the recipient, reply **START** to the same sending number to restore messaging.
6. Attempt a final controlled SMS and verify delivery resumes.

Documentation establishes the expected behavior; the STOP-then-resend result confirms it for this account and number.

## Sources

- Twilio, Advanced Opt-Out: https://www.twilio.com/docs/messaging/tutorials/advanced-opt-out
- Twilio, Error 21610: https://www.twilio.com/docs/api/errors/21610

## Assumptions

- The verdict is limited to messages sent through Twilio from the same sending phone number that received STOP; changing sending numbers or providers is outside this conclusion.
- The staged task statement accurately reproduces the evidence: Bland sends through Twilio, STOP creates the phone-number-level block, error 21610 rejects resends, and START removes the block.
- `./source/EVIDENCE.md` was absent during this run. The source URLs above are the Twilio pages identified by the staged subject matter, but they could not be checked against an evidence-file URL list.
- This verdict answers the stated opt-out enforcement question only; it does not assess consent acquisition, message content, quiet hours, record-retention rules, or other campaign obligations.
