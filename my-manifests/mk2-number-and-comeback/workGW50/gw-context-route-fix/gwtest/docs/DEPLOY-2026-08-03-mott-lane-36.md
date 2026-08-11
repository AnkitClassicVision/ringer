# Deploy record — mott-lane-36 (2026-08-03 ~20:15 ET)

Following-weekday + offer-relative correction fix, shipped same-night after the live
"No the following Thursday" incident (conversation 782f4dce…, resolved 08/06 instead of 08/13).

## What changed (103 diff lines vs production)

1. `resolve_relative_date`: new pattern `(the )?following <weekday>` → the named weekday of the
   next Monday-anchored calendar week (same semantics as "<weekday> next week").
2. `extract_date_from_text`: a recognized multi-token following-weekday span occupies its span
   and beats one-token weekday windows inside it.
3. Correction semantics: a user message matching `^no[,!. ]+(the )?following <weekday>` after an
   agent offer resolves to **the offered date + 7 days** (most recent agent message containing an
   explicit MM/DD/YYYY on the named weekday), falling back to calendar semantics when no offer is
   found. Genuine negations ("no friday works", "no not thursday") are untouched.

## Ship chain (all steps executed-check-verified under Ringer, run mk2-number-and-comeback)

- Patch base extracted byte-exact from ECR layers of `eyecloud-fargate-runner:mott-lane-35`
  (no container runtime on the workstation; pure ECR API).
- Proofs: 12/12 on the correction/following eval corpus; zero behavioral diffs vs production
  outside the intended family across the gw-temporal-check golden sweep; incident-prefix replay
  resolves 08/13/2026.
- Image `mott-lane-36` assembled via ECR API: all base layers digest-identical, one appended
  overlay layer containing only `opt/cvc-booking-gateway/bland_gateway.py`; pushed digest
  `sha256:f7e1aa3e…`; overlay re-extracted and byte-verified against the proven artifact
  BEFORE deploy.
- Task definition `mott-booking-gateway:51` cloned from `:50` (same-day CPU upgrade preserved;
  the stale untracked terraform tfvars pointed at mott-lane-12 and was deliberately bypassed).
- Live verification on production: `the following thursday`→08/13/2026, plain `thursday`→
  08/06/2026 (unchanged), `following friday`→08/14/2026, exact incident correction replay→
  08/13/2026 with no 08/06; `gate_booked` fresh-proven on pathway v92.

## Rollback

```
aws ecs update-service --cluster stack2 --service mott-booking-gateway --task-definition mott-booking-gateway:50
```

Evidence artifacts: `ringer/my-manifests/mk2-number-and-comeback/workGWfix2..4, workGWdeploy`
(proofs, full_delta.diff, deploy and live-verify transcripts).
