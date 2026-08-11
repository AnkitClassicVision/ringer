# The real /v1/sms/send success response (measured live)

A SUCCESSFUL send returns HTTP 200 with:
{"data": {"status": "processing", "message": "SMS accepted for delivery...",
          "conversation_id": "9e22e417-...", "message_id": "..."}, "errors": null}

The status is "processing" (or sometimes "queued"), nested under "data", NOT top-level.
The failure field is "errors" (plural, a list or null), NOT "error".

A GENUINE failure returns non-2xx OR errors non-null, e.g.:
{"data": null, "errors": [{"message": "Missing required fields", "error": "MISSING_REQUIRED_FIELDS"}]}

BUG: send_one's current check reads top-level body.get("status")/success/ok and body.get("error"),
so it raises "SMS send response did not confirm success" on EVERY real success. Measured: a real
send created a live conversation (opener delivered) yet the sender reported external_actions_taken=0
and refused. In a campaign loop this miscounts sends and would RE-SEND, double-texting patients.
