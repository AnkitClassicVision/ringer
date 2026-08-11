# Suppression Truth

VERDICT: IMPLEMENTED

## Summary

- The staged gateway registers and handles authenticated `POST /sms-suppression`; the staged Terraform declares its DynamoDB table, injects the table name, and grants the ECS task role `dynamodb:PutItem` on it (source/bland_gateway.py:1593-1601, source/bland_gateway.py:1696-1711, source/main.tf:55, source/main.tf:122-136, source/main.tf:171-185).
- The write is idempotent: the phone is the partition key, `attribute_not_exists(pk)` prevents replacement, and a conditional failure returns success, preserving the first `created_at` (source/bland_gateway.py:754-772).
- The reviewed-state source is an older snapshot dated 2026-07-24 and admits non-health routes were not live-probed; the later status says this route was live-probed on 2026-07-25 at 18:30 ET (source/mott-aws-gateway-reviewed-state.json:3-8, source/GATEWAY-STATUS.md:3-6, source/GATEWAY-STATUS.md:42-48).

## Evidence

`/sms-suppression` is included in the accepted POST-path set, then dispatched to `record_sms_suppression` (source/bland_gateway.py:1593-1601, source/bland_gateway.py:1696-1704). The handler requires authentication: an authenticated consumer lacking this route receives 403, while other failed authentication receives 401 (source/bland_gateway.py:1611-1617). Consumer scope is the exact string `POST /sms-suppression`, unless the credential's final route entry is `*` (source/bland_gateway.py:927-931).

The handler writes one DynamoDB item whose `pk` is the phone and whose other attributes are `reason`, `source`, and UTC `created_at` (source/bland_gateway.py:754-768). Terraform declares a pay-per-request table named `mott-booking-gateway-sms-suppression`, keyed by string `pk`, with 35-day point-in-time recovery (source/main.tf:17-19, source/main.tf:122-135). It injects that table's name as `ECP_SMS_SUPPRESSION_TABLE` (source/main.tf:33-55). The task definition uses the IAM task role to which Terraform attaches a policy allowing `dynamodb:PutItem` on this table (source/main.tf:171-185, source/main.tf:211-224).

No endpoint response includes the submitted phone: success is `{"ok": true}`, validation and storage responses contain only fixed or field-specific error text, and authentication/body-size failures contain no request value (source/bland_gateway.py:1611-1621, source/bland_gateway.py:1696-1711). The only phone use after validation outside the database write is a masked log suffix, not an HTTP response (source/bland_gateway.py:1701-1704).

## The Contract

The request body must be a JSON object containing `phone_e164`, `reason`, and `source`; additional fields are not rejected or persisted (source/bland_gateway.py:730-746, source/bland_gateway.py:760-768, source/bland_gateway.py:1696-1701).

- `phone_e164`: string matching exactly `\+[0-9]{8,15}` (source/bland_gateway.py:738-742).
- `reason`: exactly `stop`, `unsubscribe`, `complaint`, or `manual` (source/bland_gateway.py:712-713, source/bland_gateway.py:743-744).
- `source`: exactly `sms_reply`, `voice`, `manual`, or `import` (source/bland_gateway.py:712-713, source/bland_gateway.py:745-746).

Valid first and repeat submissions return 200 with `{"ok": true}`; a repeat leaves the original item and timestamp intact (source/bland_gateway.py:760-772, source/bland_gateway.py:1701-1704). Missing fields, malformed JSON, a non-object body, or invalid field values return 400 with `{"ok": false, "error": "<validation message>"}` (source/bland_gateway.py:734-746, source/bland_gateway.py:1697-1707). A body over 16 KiB returns 413 `{"error": "body too large"}` (source/bland_gateway.py:38, source/bland_gateway.py:1618-1621). Missing/unusable storage configuration returns 503 with `suppression_store_unconfigured` or `suppression_store_unavailable`; any non-conditional DynamoDB exception returns the latter (source/bland_gateway.py:748-773, source/bland_gateway.py:1708-1711). Unknown paths return 404; wrong scope returns 403; failed authentication returns 401 (source/bland_gateway.py:1593-1617).

## Why The Sources Disagree

Source B is explicitly a 2026-07-24 review snapshot, labels suppression missing, and says non-health routes were not live-probed (source/mott-aws-gateway-reviewed-state.json:3-8, source/mott-aws-gateway-reviewed-state.json:91-97). Source A is later, names running image `mott-lane-10` and task definition 23, and reports the suppression probe results at 2026-07-25 18:30 ET (source/GATEWAY-STATUS.md:3-6, source/GATEWAY-STATUS.md:42-48). Thus the artifacts support “missing in the July 24 snapshot, shipped by the July 25 snapshot.” The staged artifacts do not date or identify the separately reported 404 probe, so they cannot prove when or against which task that 404 occurred.

## What Source Cannot Prove

Terraform selects an ECR image by mutable `var.image_tag`, not by a source hash or immutable digest, so these files cannot prove what code the running task contains (source/main.tf:17-19, source/main.tf:217-240). One decisive live check is an authenticated `POST /sms-suppression` with a valid, controlled test number: 200 proves the running endpoint accepts the route, while 404 proves that deployment lacks it (source/bland_gateway.py:1593-1601, source/bland_gateway.py:1696-1704).

## Assumptions

“Implemented” means the staged application and infrastructure definitions are internally complete, not that the current deployment was independently observed in this audit. The route depends on applying this Terraform and deploying an image containing this staged gateway source (source/main.tf:55, source/main.tf:122-136, source/main.tf:217-240).
