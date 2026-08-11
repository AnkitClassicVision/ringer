# Suppression Read To DynamoDB

## Summary

- Suppression reads now use the `mott-booking-gateway-sms-suppression` DynamoDB table in `us-east-1`.
- A suppression-reader seam keeps production on DynamoDB and tests fully mocked.
- The existing gateway POST suppression write remains unchanged.

## What Changed

| Function | Before | After |
|---|---|---|
| `bulk_suppressions()` | Sent a gateway `GET /sms-suppression` request. | Calls `reader.read_all()`; the default reader scans DynamoDB and projects only `pk`, including pagination. |
| `is_suppressed(phone)` | Sent a gateway `GET /sms-suppression?phone=...` request. | Calls `reader.read_one(phone)`; the default reader performs `GetItem` with `pk` equal to the E.164 phone. |
| `run()` | Passed the HTTP seam into both suppression reads. | Accepts an optional `suppression_reader` and passes it into both reads while retaining the existing HTTP seam for other calls. |

## Seam

`SuppressionReader` defines `read_all() -> set[str]` and `read_one(phone) -> bool`. The module-level default is a `DynamoDBSuppressionReader` that creates its boto3 DynamoDB resource and table lazily, so importing the sender does not contact AWS. Tests inject `FakeSuppressionReader` into `run()` and the two read functions. Separate fake-table tests prove the default reader's paginated scan and listed/unlisted `GetItem` behavior without AWS.

## Fail-Closed

Both suppression functions convert genuine reader exceptions into `Refusal`. Tests prove failures during either the bulk read or immediate pre-send recheck return refusal status and leave `external_actions_taken=0`.

## Assumptions

- The table partition key is the string `pk`, containing a valid E.164 phone.
- Item presence means opted out; item absence means not opted out.
- The table remains small enough for a paginated projected Scan.
- boto3 is available in the production runtime.
