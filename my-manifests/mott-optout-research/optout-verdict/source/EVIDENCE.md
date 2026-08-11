# Evidence packet: Bland/Twilio opt-out for Mott recall SMS

## Bland API findings (measured 2026-07-27, live account)
- Bland exposes NO opt-out/suppression/DNC/list API. /v1/sms/a2p, /v1/brands, /v1/account all 404. Docs (sms-send, sms-batch, tutorials/messaging/sms, llms.txt) document no STOP/opt-out handling.
- Bland SMS runs on Twilio: docs reference "bring-your-own-Twilio", "Twilio Messaging Service SID", and a message_sid field.
- The two account numbers both have messaging_service_sid = null at the number level: "AI Bot Test" (...8905) and "Emerald Eye Care | Clarkston" (...1012, the Mott recall test sender).
- Account /v1/me is active, balance ~$174.

## Twilio authoritative facts (support.twilio.com, docs.twilio.com/api/errors/21610)
- A STOP/QUIT/CANCEL/UNSUBSCRIBE reply creates a block-list entry on Twilio's side for that recipient against "the Twilio phone number, Channels sender, or Messaging Service" they replied to.
- Any future send to a blocked recipient returns HTTP 400 + Error 21610; the message is NOT sent and NOT charged.
- The block applies at the SENDING PHONE NUMBER level, not only Messaging Service level, so it is enforced even when no Messaging Service is configured.
- Sending resumes only after the recipient replies START.
- As of 2026-03-16 Twilio unifies opt-out across SMS/MMS/RCS on the same sender/Messaging Service.

## Our current gateway/sender state
- The gateway can WRITE opt-outs (POST /sms-suppression works) but has NO READ endpoint (GET /sms-suppression -> 404, confirmed on the deployed image).
- The batch sender does a pre-send bulk suppression READ and FAILS CLOSED on the 404, so it currently refuses to run a campaign.

## Sources
- https://support.twilio.com/hc/en-us/articles/223134027-Twilio-Support-for-Opt-out-Keywords-SMS-STOP-Filtering
- https://www.twilio.com/docs/api/errors/21610
- https://support.twilio.com/hc/en-us/articles/223133627-Error-21610-The-message-From-To-pair-violates-when-sending-SMS
