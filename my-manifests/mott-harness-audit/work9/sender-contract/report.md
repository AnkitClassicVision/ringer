# Sender Contract Fix

## Summary

- Replaced the rejected Bland `/v1/sms/create` request with the measured `/v1/sms/send` contract.
- Added each practice's sender line to `ClientProfile`; Mott uses `+15095611012`, while CVC refuses because its line is not configured.
- Kept both suppression reads fail-closed and made their 404 refusal identify the missing gateway capability.

## What Changed

| Function | Defect | Fix |
|---|---|---|
| `send_one` | Posted rejected field names to `/v1/sms/create`, then retained rejected `pathway_id` and `pathway_version` fields after changing routes. | Posts to `/v1/sms/send` with the measured accepted key set: `user_number`, profile-sourced `agent_number`, `new_conversation`, `start_node_id`, and `request_data`. Omits `agent_message`, `pathway_id`, and `pathway_version`. |
| `send_one` | Had no practice-owned sender-line contract. | Refuses before transport use when the resolved profile has no valid E.164 `agent_number`. |
| `send_one` | A lost `store` value dead-ends Mott's first pathway node. | Preserves `campaign`, `store`, `recall_patient_id`, and `recall_cell` in `request_data` when supplied, along with the existing recall token. |
| `bulk_suppressions` | Its GET cannot succeed because the gateway has no suppression read handler. | Preserves the fatal refusal and names the missing read endpoint in the error. |
| `is_suppressed` | Its immediate GET recheck has the same unavailable contract. | Preserves the fatal refusal and names the missing read endpoint in the error. |
| `FakeHttp` | Ignored authentication and accepted the obsolete send route. | Checks gateway versus Bland auth modes and recognizes only `/v1/sms/send` for sends. |

## Suppression, Left Broken On Purpose

The sender still issues two authenticated GET requests: one bulk suppression read and one per-recipient recheck. The gateway's `/sms-suppression` route supports POST only, so both reads receive 404 in production. The batch therefore still refuses before sending. This is intentional: skipping or weakening suppression would permit messages without a working opt-out check.

Closing this requires a gateway suppression read contract, implemented and deployed for both the bulk list and the single-number recheck, with authenticated responses matching the sender's validated response shapes. Until those GET handlers exist, the sender is correctly blocked.

## Tests Added

- `test_mott_send_uses_exact_measured_contract_and_required_request_data`: catches the wrong URL, rejected or extra payload keys including `pathway_id` and `pathway_version`, missing `start_node_id`, missing `store`, and accidental `agent_message`.
- `test_mott_agent_number_comes_from_profile_not_send_function_literal`: catches a literal Mott number embedded in `send_one`.
- `test_profile_without_agent_number_refuses_without_transport_call`: catches fallback or attempted sending for an unconfigured practice.
- `test_bulk_suppression_404_names_missing_read_endpoint`: catches an opaque bulk-read refusal.
- `test_suppression_recheck_404_names_missing_read_endpoint`: catches an opaque immediate-recheck refusal.
- Existing fake-transport coverage now checks the auth selector and rejects the obsolete send URL.

## Assumptions

- `new_conversation` must be `true` for each recall batch send.
- Bland success responses retain the accepted `ok`, `success`, or queued-status shapes already validated by the sender.
- CVC remains intentionally unable to send until its own E.164 SMS line is configured.
