# Refusal Battery

## Summary

- Eight distinct fail-closed guards are exercised with synthetic poisoned inputs.
- Every case omits `--approve` and `--max-sends` and is expected to stop before HTTP.
- The first possible HTTP calls are patient enrichment at line 278 or bulk suppression at line 464.

## Guards Proven

| Guard | Poison used | Exact refusal message |
|---|---|---|
| PHI-looking feed header | Added a `diagnosis` column | `feed contains a PHI-looking column name` |
| Approved feed shape allowlist | Omitted `consent_date` | `feed columns do not match an approved phone or patient-ID shape` |
| Feed freshness | Set the feed mtime more than 24 hours old | `feed freshness check failed` |
| Practice resolution | Used an unknown `schema_version` | `unknown manifest schema; no client profile matches` |
| Practice start-node allowlist | Gave Mott `n_not_allowed` | `manifest start node mismatch` |
| Mott voice-source absence | Declared a synthetic voice pathway and version | `manifest declares a voice source this client does not have` |
| Exact manifest key set | Added `unexpected_key` | `invalid release manifest schema` |
| Practice-specific send ledger | Pointed a Mott run at a CVC-schema ledger | `invalid send ledger schema` |

## Rejected As Post-Network

- Positive `--min-days-between` validation is at line 378. In `run()`, it is first reached at line 569, after the bulk-suppression HTTP call at lines 463–466, invoked by line 567.
- All approve-path guards are under `if args.approve` beginning at line 583. They are reached after the same first HTTP call at line 567. This includes the required `--max-sends` guard at line 585, approved-maximum guard at line 587, sending-window guard at line 591, suppression recheck at lines 592–593, ledger reservation, and SMS creation.

## Assumptions

- The battery runs from this task directory, so fixture paths in `cases.json` resolve relative to it.
- The stale fixture's filesystem mtime is part of the fixture and must remain older than the default 24-hour limit.
- Error logging may add `ERROR refused:` around the message; each `expect` is the sender's exact stable refusal substring.
