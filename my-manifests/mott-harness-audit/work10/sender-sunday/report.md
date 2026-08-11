# Sunday Send Block

## Summary

- Approved outbound SMS batches now fail closed on Saturdays and Sundays.
- Dry runs remain available every day because the new gate is approve-only.
- The SMS payload and all downstream send behavior are unchanged.

## Change

In `run()`, the `args.approve` path converts the injected clock value to the
practice timezone named by `TIMEZONE` and raises `Refusal` when
`practice_now.weekday() >= 5`.

## Tests Added

| Test | Proof |
|---|---|
| `test_sunday_approve_refuses_before_sms_send` | Sunday approval refuses, makes no `/v1/sms/send` call, and reports `external_actions_taken=0`. |
| `test_saturday_approve_refuses_before_sms_send` | Saturday approval refuses, makes no `/v1/sms/send` call, and reports `external_actions_taken=0`. |
| `test_weekend_gate_allows_monday_approve_to_send_once` | Monday approval with the same feed makes exactly one send. |

## Assumptions

- Python weekday values 5 and 6 represent Saturday and Sunday.
- `TIMEZONE` remains the authoritative practice-local timezone.
