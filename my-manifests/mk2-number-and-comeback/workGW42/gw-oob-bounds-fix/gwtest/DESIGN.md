# CVC Booking Gateway — Design (locked by Claude QA, 2026-06-24)

## Goal
A BAA-covered ingress on AWS that receives Bland AI booking webhooks (5 endpoints), runs the EyeCloud CLI appt verbs, returns results. REUSES the live `stack2` EyeCloud stack. Replaces the new-box + ngrok/laptop-tunnel idea. CVC = tenant 1; shaped as a multi-tenant conductor shell.

## Proven facts (rely on these; do NOT re-investigate)
- PerimeterX-from-AWS is SOLVED: `/ecs/stack2-runner` logs `login_navigate -> login_submit -> login_succeeded` daily from an AWS IP, 0 blocks/5d, latest 2026-06-24 02:31 UTC. Runner source: `/mnt/d_drive/repos/practicecanopy/src/booking_attribution/eyecloud/runner/` (browser.py = headless Playwright login + store-select).
- The runner mints its session PER RUN in-process (logs in ~4x/hr; no storage_state/secret/S3 session export). So there is NO shared session to reuse -> the gateway mints its OWN session using the same headless-login approach.

## Locked shape: lean always-on Fargate task on the existing `stack2` cluster
- One always-on Fargate service/task. On start: headless-browser login to EyeCloud (reuse the runner image / login module), select store, keep the session warm; re-login on staleness (sessions die in ~1-3h).
- Serves the 5 endpoints (mirror `/mnt/d_drive/repos/eyecloud_CLI/bland-shim/bland_shim.py` contract): `/patient-search`, `/availability`, `/conflict-check`, `/book`, `/book-new-patient`. Each shells to `eyecloud-pro-pp-cli appt <verb> --agent --reason bland-<verb>`; writes require `--confirm` + TEST_MODE allowlist.
- Inbound: the task has a public IP; TLS + bearer + ModSecurity/OWASP CRS terminate IN-CONTAINER (caddy or nginx+modsecurity). NO managed ALB/CloudFront (budget). Source-restrict to Bland where possible.
- TEST_MODE default ON (ZZTEST-only search, allowlisted writes). `ECP_SHIM_TEST_MODE=0` is the supervised live flip (real-patient writes stay Phase 3/4 gated).

## Cost target (incremental): <= $20/mo
- Fargate 0.25 vCPU / 0.5 GB always-on ~= $9/mo + public IPv4 ~= $3.65/mo = ~$13/mo. If the headless browser needs more RAM, 0.25 vCPU / 1 GB ~= $10.6 + IPv4 = ~$14/mo. Stay <= $20. No ALB/NAT/CloudFront.

## REUSE by Terraform data source — do NOT recreate any of these
- ECS cluster `stack2` (data source). ECR image `eyecloud-fargate-runner` (reuse the image or its login module).
- KMS alias "EyeCloud Pro PHI encryption" (data source) for any encryption.
- WORM audit: Lambda `eyecloud-pro-audit-worm-mirror`, DDB `eyecloud-pro-audit-log`, S3 `eyecloud-audit-worm-533267039664` — REFERENCE only, never recreate.
- Secrets (data sources, never read values in TF): `eyecloud-pro/clients/cvc/db/master-key`, `eyecloud-pro/clients/cvc/proxy-api-key`, the CVC EyeCloud login creds secret used by the runner, the gateway bearer secret.
- IAM: clone the SCOPE of `eyecloud-stack2-task-role` / `eyecloud-stack2-execution-role` for the new task role (least privilege); reference existing where possible.

## Multi-tenant conductor seam (CVC wired first)
- Tenant key derived from the Bland inbound number / pathway id on each request.
- A tenant registry abstraction (even a config map for now) maps tenant -> EMR adapter + creds/session + stores + doctors + appt-types + pathway. CVC/EyeCloud is the first wired entry.
- EMR-adapter interface so a second adapter (e.g. RevolutionEHR API) can be added later. EyeCloud adapter = the CLI verbs.
- Full multi-tenant GA is gated elsewhere on the tenant registry build + ADR-013 (CVC duplicate tenant_id cleanup). Do NOT try to solve those here; just leave the seam.

## Security (carry over)
Bearer required (reject pre-processing); TLS 1.2+; ModSecurity/OWASP CRS; no PHI at rest beyond the live session; audit every call via `--reason` + the existing WORM trail; least-privilege IAM. No secret values in TF/tfvars/code/logs.

## Deploy gate
Terraform `fmt` + `validate` clean. NO apply in scaffolding. Owner reviews `terraform plan` before any apply. Claude QAs first.
