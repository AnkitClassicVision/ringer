# Sales Ops Daily Sweep Full Automation Plan

Status: implanted plan, internal only until live-send approval.
Date: 2026-07-08
Owner: AI Sales Ops Operator
Human owner for launch approvals: Ankit
Current highest true state: local detection and draft artifacts proven, no sends, no HubSpot writes.

## Alignment

Purpose: turn the sales-ops daily sweep into a Ringer-run swarm operator that finds stale PracticeOS opportunities, sends safe follow-up, and records receipts.
Context: this sits inside the MyBCAT sales operating system and HubSpot, with Ringer as the traceable swarm agent and router, not merely a test harness.
Audience: Ankit, AI Sales Ops Operator, and any future builder or reviewer touching this workflow.
Belief shift: the daily sweep is not a report, it is a staged operator that must graduate from queue to send to autonomous action.
Logic thread: detect stale deals, gather context, write draft, QA gates, send if allowed, log receipts, monitor outcomes.
Constraints: no live sends or HubSpot writes until explicit approval names the cohort, sender, channel, cap, and logging path.

## One-line operating model

Nate prompts define the worker behavior. Ringer routes, swarms, executes, checks, retries, and records the work. Humans approve live writes until the lane graduates.

## Current state

The current sales-ops Ringer run accomplished Level 0 only:

- reads a local HubSpot PracticeOS snapshot
- detects stale or past-SLA opportunities
- creates local draft hooks and one dry-run task payload
- proves no external APIs, no sends, no CRM writes, no HubSpot tasks
- records a Ringer receipt

Current draft locations:

```text
/tmp/ringer-sales-ops-batch1/winback-plays/winback-plays.md
/tmp/ringer-sales-ops-batch1/stuck-and-lost-sweep/stuck-and-lost-sweep.md
/tmp/ringer-sales-ops-batch1/hot-inbound-rapid-response/hubspot-task-payload.json
/home/ankit114/.ringer/artifacts/deliverables/sales-ops-batch1-20260708T184349Z-p323021/
```

## Target fully autonomous lane

Start narrow. Do not make this a general sales agent.

Initial autonomous lane:

- cohort: PracticeOS stale active deals
- channel: email only
- max sends: 3 per day during pilot, then 5 per day after clean receipts
- business days only
- no weekends
- no SMS
- no LinkedIn
- no postcards
- no sequence enrollment
- no deal stage moves
- HubSpot logging required
- stop if any sent email lacks a HubSpot activity receipt

## Level ladder

### Level 0: local proof

What exists now.

Output:

```text
stuck-and-lost-sweep.md
winback-plays.md
hubspot-task-payload.json
Ringer run receipt
```

Allowed action: none outside local files.

### Level 1: approval queue

Build the missing bridge.

Outputs:

```text
send_queue.jsonl
approval_table.md
qa_report.md
```

Each candidate must include deal, contact, email, stale reason, context evidence, draft, QA results, and send or hold recommendation.

Allowed action: local files only.

### Level 2: human-approved sending

Ankit approves specific rows.

Allowed action:

```text
send only approved rows
log each send to HubSpot
write local ledger receipt
```

Pilot cap: 1 to 3 sends.

### Level 3: auto-send with hard gates

AI can send without per-row approval only if every gate passes.

Required gates:

- deal still exists
- deal is still in PracticeOS pipeline
- deal is still stale
- contact exists
- email address exists
- contact is not unsubscribed
- no bounce or suppression signal
- no recent human touch inside the configured cooldown
- no duplicate send inside the configured cooldown
- draft passes writing QA
- daily cap remains available
- HubSpot logging path is available
- sender account is healthy

Anything else becomes `hold_for_review`.

### Level 4: autonomous daily operator

Daily schedule:

```text
scan HubSpot
build send queue
auto-send safe rows inside cap
hold risky rows
log HubSpot activities
write local ledger
send daily summary to Ankit
monitor replies and failures
```

### Level 5: optimization

Only after safe operation:

- compare subject lines
- compare draft styles
- adjust stale thresholds by stage
- detect reply rate by cohort
- suppress low-yield segments
- re-score models by Ringer receipts

## Candidate state machine

```text
candidate_detected
context_gathered
context_qa_passed
copy_drafted
copy_qa_passed
action_qa_passed
approved_to_send
sent
hubspot_logged
closed_with_receipt
```

Hold states:

```text
hold_context_missing
hold_no_email
hold_suppressed
hold_recent_touch
hold_duplicate_risk
hold_copy_failed
hold_sender_unhealthy
hold_hubspot_logging_unavailable
hold_human_review
```

## Send queue schema

Each row in `send_queue.jsonl` should look like this:

```json
{
  "run_id": "sales-ops-daily-sweep-YYYYMMDD",
  "candidate_id": "stable hash of deal_id + action_type + date",
  "deal_id": "...",
  "contact_id": "...",
  "company_id": "...",
  "deal_name": "...",
  "contact_email": "...",
  "stage": "Identified",
  "days_idle": 10,
  "stale_reason": "past 7-day stage SLA",
  "recommended_action": "send_email",
  "draft_subject": "...",
  "draft_body": "...",
  "context_sources": [
    {"source": "hubspot_deal", "id": "...", "checked_at": "..."},
    {"source": "hubspot_contact", "id": "...", "checked_at": "..."},
    {"source": "hubspot_activity", "id": "...", "checked_at": "..."}
  ],
  "context_qa": "pass",
  "writing_qa": "pass",
  "suppression_qa": "pass",
  "recent_touch_qa": "pass",
  "action_qa": "pass",
  "approval_state": "pending_review",
  "status": "ready_for_approval",
  "send_receipt": null,
  "hubspot_receipt": null,
  "hold_reason": null
}
```

After send:

```json
{
  "status": "sent_and_logged",
  "sent_at": "...",
  "sender_account": "...",
  "send_receipt": "provider message id",
  "hubspot_receipt": "HubSpot email or note activity id"
}
```

## Context QA

A row cannot send unless context QA proves:

- live HubSpot deal was read
- live contact was read
- contact email exists
- deal is in the target pipeline
- deal is stale under current stage SLA
- last activity was checked
- recent-touch cooldown passed
- unsubscribe status checked
- bounce or suppression status checked
- reason for outreach is grounded in the record

If any required field is missing, status becomes `hold_context_missing`.

## Writing QA

A draft cannot send if it contains:

- fake familiarity
- unsupported claim
- inaccurate source reason
- generic filler
- just checking in
- touching base
- circling back
- hope you are doing well
- leverage
- seamless
- holistic
- em dash
- too much length
- no specific ask
- wrong voice for Ankit

If it fails, status becomes `hold_copy_failed`.

## Action QA

A send cannot happen unless:

- candidate is in the approved cohort
- channel is allowed
- sender account is selected and healthy
- daily cap is available
- idempotency key has not been used
- HubSpot logging is available
- local ledger write is available
- kill switch is not active

If send succeeds but HubSpot logging fails, stop the lane and alert Ankit.

## Activity recording

The workflow must record activity in three places.

### 1. Local ledger

Path shape:

```text
~/.ringer/sales-ops-ledger/YYYY-MM-DD.jsonl
```

Records every candidate, send, hold, failure, and receipt.

### 2. HubSpot

For sent emails, record either:

- HubSpot native email activity id, or
- HubSpot note linked to deal and contact with send receipt id, or
- HubSpot BCC/activity sync proof if sender account supports it

### 3. Ringer receipt

Each run writes Ringside artifacts and run JSON.

## Daily summary

Daily summary to Ankit:

```text
Scanned: N deals
Candidates: N
Ready for approval: N
Sent: N
Held context missing: N
Held recent touch: N
Held suppression: N
Held copy QA: N
HubSpot logged: N/N
Replies detected: N
Errors: N
Kill switch: on/off
```

## Kill switch

Stop sending immediately if any of these occur:

- send without ledger row
- send without HubSpot receipt
- more than one provider error in a run
- unexpected recipient domain pattern
- duplicate send detected
- unsubscribe or bounce uncertainty
- sender account health check fails
- Ankit says stop

## Implementation units

U1. Live context gatherer
Proof: reads deal, contact, company, activity, subscription or suppression fields without writing.

U2. Queue builder
Proof: writes `send_queue.jsonl`, `approval_table.md`, and `qa_report.md` for 5 candidates.

U3. Context QA checker
Proof: every row has pass or hold reason. No unknown field is treated as pass.

U4. Writing QA checker
Proof: rejects banned phrases, unsupported claims, wrong voice, and missing ask.

U5. Approval processor
Proof: only rows with explicit approval can enter send-ready state during pilot.

U6. Send adapter
Proof: sends to a sandbox or single approved live row and returns provider receipt.

U7. HubSpot logger
Proof: logs sent activity to HubSpot and returns activity receipt.

U8. Ledger and daily summary
Proof: ledger has candidate, action, hold, send, and HubSpot receipt rows. Daily summary matches ledger counts.

U9. Autonomy scheduler
Proof: cron or scheduled job runs in dry-run, then approved pilot, then capped auto-send lane.

## Graduation criteria

### From Level 1 to Level 2

- 5 candidate rows generated
- all context QA fields present
- all hold reasons understandable
- drafts pass writing QA
- Ankit approves exact sender and max sends

### From Level 2 to Level 3

- at least 10 human-approved sends across multiple days
- 100 percent HubSpot logging receipt rate
- 0 wrong-contact sends
- 0 duplicate sends
- 0 suppression misses
- daily ledger matches provider and HubSpot counts

### From Level 3 to Level 4

- at least 30 auto-eligible candidates reviewed in shadow mode
- at least 95 percent agreement with human review
- all disagreements explainable and fixed
- kill switch tested
- daily summary trusted by Ankit

## Stock Ringer implementation note

Use stock Ringer as the swarm agent, router, and trace layer. Do not add a separate automation framework to Ringer for this lane. The automation controls should be ordinary project code plus Ringer orchestration and checks: queue schema, QA scripts, receipt checks, kill switch file, routing policy, retry behavior, model scoreboard, and graduation rules.

## How the first pass should have been requested

The first pass would have reached the right target faster if the ask was framed as a live-capable operator, not a dry-run Ringer proof.

Better first-pass brief:

```text
Build Sales Ops Daily Sweep as a live-capable operator, starting with approval queue.

Scope:
- PracticeOS stale active deals only
- email only
- no SMS, LinkedIn, postcards, sequence enrollment, or stage moves

Outputs:
- send_queue.jsonl
- approval_table.md
- qa_report.md
- local ledger schema
- one sandbox or approved live-send adapter stub

Context requirements:
- read live HubSpot deal, contact, company, and activity
- check unsubscribe, bounce, suppression, recent touch, and duplicate sends
- no unknown field can pass silently

Writing requirements:
- Ankit Direct voice
- no fake familiarity
- no unsupported claims
- no banned sales phrases
- short specific ask

Action requirements:
- do not send until explicit approval
- when approved, max 1 to 3 sends
- capture provider send receipt
- log to HubSpot
- stop if HubSpot logging fails

Proof:
- Ringer lint and run pass
- 5 real queue candidates
- every hold has reason
- every sent row has provider and HubSpot receipt
- daily summary matches ledger
```

## Why the first pass stopped at dry run

The original run had no approved sender account, no allowed-send cohort, no daily cap, no HubSpot logging path, no suppression source, no approval queue schema, and no explicit live-send authorization. Given that, the safe first pass was local proof only.

The missing bridge was Level 1: the approval queue.

## Next build recommendation

Build `sales_ops_send_queue_v1` next.

It should not send yet. It should produce 5 real candidates with full context QA, writing QA, approval table, and ledger-ready rows. After that, Ankit can approve 1 to 3 sends as the first live pilot.
