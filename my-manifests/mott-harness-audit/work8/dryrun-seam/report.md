# Dry Run Seam Probe

SEAM: BLOCKED

## Summary

- The approved wrapper did not obtain `MOTT_GATEWAY_TOKEN`; AWS Secrets Manager was unreachable, so the authenticated sender-to-gateway seam was never exercised.
- A secondary credential-free dry-run launched the sender only to verify its refusal/finally path. It refused before any gateway request and printed `external_actions_taken=0`.
- Gateway reachability, HTTP authentication status, Bearer-prefix behavior, synthetic lookup, and suppression-list behavior remain unknown.

## What The Counters Said

| Counter name | Value |
|---|---:|
| external_actions_taken | 0 |

No other counter lines were printed because neither attempt reached the sender's normal counter block.

## Failures Encountered

Approved wrapper attempt:

```text
aws: [ERROR]: Could not connect to the endpoint URL: "https://secretsmanager.us-east-1.amazonaws.com/"
```

```text
subprocess.CalledProcessError: Command '['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'conductor/agents/bland-mott/api-key', '--query', 'SecretString', '--output', 'text']' returned non-zero exit status 255.
```

This means the wrapper exited before obtaining the credential or launching `sms_recall_batch.py`.

Secondary sender-only dry-run:

```text
ERROR refused: gateway authorization is unavailable
```

This means the sender started without `MOTT_GATEWAY_TOKEN`, refused before making a gateway request, and executed its real `finally` block. Its next unedited line was:

```text
external_actions_taken=0
```

The full stdout and stderr from both attempts is preserved in `dryrun_output.txt`. No alternate AWS profile or secret-access route was attempted.

## What This Does Not Prove

- Whether the booking gateway was reachable from the sender runtime.
- Whether authentication would succeed or fail, including the HTTP status.
- Whether the stored token includes the required scheme or needs a `Bearer ` prefix the sender does not add.
- What the patient lookup returns for synthetic patient ID `P900001`.
- Whether the suppression-list call succeeds or matches the sender parser.
- Any normal sender counter values beyond the finally counter.

## Assumptions

- Failure before credential retrieval requires `SEAM: BLOCKED`.
- The synthetic feed used accepted columns `patient_id,consent_source,consent_date` and invented ID `P900001`; it contained no real identifier or phone number.
- `external_actions_taken=0` is authoritative because it was emitted by the sender's own `finally` block.
