# Suppression read: gateway GET -> DynamoDB direct

Table: mott-booking-gateway-sms-suppression, region us-east-1.
Partition key: pk (String) = the E.164 phone number.
Other attributes: reason, source, created_at. Presence of an item = that phone is opted out.
Current items: 3.

The gateway has NO GET /sms-suppression route (returns 404); it only serves POST (write).
So the sender's bulk_suppressions() and is_suppressed() currently fail closed on the 404.

Two independent audits (Codex + Gemini) blocked best-effort skipping of the read, because
this table holds opt-outs the Twilio carrier STOP block does NOT catch: pathway freeform
opt-outs ("take me off"), wrong-number suppressions, and web/phone opt-outs. The sender
must consult this real list, not skip it.

The WRITE path (record_suppression -> POST /sms-suppression) WORKS and must stay unchanged.
