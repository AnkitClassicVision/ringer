# Suppression Wiring

## Summary

- Added one silent suppression webhook before each opt-out exit.
- Both calls use the existing gateway and stored-secret authorization, send only the contracted fields, and disable retries.
- Both success and failure responses continue to the existing honest office-directed wording, so an attempted call is never presented as proof that storage succeeded.

## Nodes Added

| Node id | What it posts | Exit it guards |
|---|---|---|
| `n_suppress_stop` | `POST /sms-suppression` with `phone_e164: "{{recall_cell}}"`, `reason: "stop"`, and `source: "sms_reply"` | `e_stop` |
| `n_suppress_not_me` | `POST /sms-suppression` with `phone_e164: "{{recall_cell}}"`, `reason: "complaint"`, and `source: "sms_reply"` | `e_not_me` |

## Values Chosen

For a STOP request, `reason: "stop"` is the contract's exact description of the patient's instruction. For a wrong-person or wrong-number reply, `reason: "complaint"` honestly records that the recipient has reported an unwanted or misdirected message; `manual` would incorrectly imply a staff-entered suppression. Both use `source: "sms_reply"` because each decision is triggered by the recipient's inbound SMS. The phone is the existing `{{recall_cell}}` conversation variable already used by identity resolution.

## What Stays Honest

The STOP exit still says: “Understood. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it.”

The wrong-person exit still says: “Sorry about that. If you would like to be taken off our list, please call Mott Optical at (855) 750-6688 and the office can take care of it.”

Neither message claims removal, unsubscription, or protection from future contact. That remains accurate when the endpoint returns 503 or the call otherwise fails after being attempted.

## Assumptions

- `{{recall_cell}}` remains populated with an E.164 phone value when either global opt-out route fires.
- The pathway evaluates webhook response pathways in order; `suppression_ok == true` and `suppression_ok != true` cover successful, failed, and unfilled results.
- Moving each global label from its end node to its new webhook makes the webhook the entry point while preserving the original classification wording.
