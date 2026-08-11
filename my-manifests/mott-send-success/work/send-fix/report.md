# Send Success Check Fix

## Summary

- Updated `send_one` to validate the measured `/v1/sms/send` response envelope.
- Real `processing` and `queued` responses now succeed and are counted.
- Ambiguous or explicit failure responses remain fail-closed.

## Before/After

Before: success depended on top-level `status`, `success`, or `ok`, while failure detection read singular `error`.

After: after the existing 2xx check, `errors` must be falsy and `data` must be an object containing either an allowed status (`processing`, `queued`, `success`, or `created`) or a truthy `conversation_id`.

## Tests Added

Added coverage for a real `processing` response counted by `run()`, a `queued` response accepted by `send_one`, non-empty `errors`, non-2xx HTTP status, and a malformed body with no `data`. Existing fake sends now default to the real nested response shape.

## Fail-Closed

Non-2xx responses, non-empty `errors`, missing or non-object `data`, and data without either an allowed status or a conversation ID still raise `Refusal`.

## Assumptions

An empty `errors` list is equivalent to `null`, and a truthy `conversation_id` confirms acceptance even when `data.status` is absent or unrecognized, as required by the task contract.
