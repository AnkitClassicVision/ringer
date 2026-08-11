# Sales Ops Live Operator Kit

Status: local Ringer kit for turning the sales-ops sweep into a live-capable swarm.

This kit is the bridge from prior proof artifacts to a Ringer-run operator.

## What it does now

Level 1 queue mode:

```text
PracticeOS snapshot -> send_queue.jsonl -> approval_table.md -> qa_report.md
```

It does not send email and does not write HubSpot. It produces rows that explain what is ready, what is held, and why.

## Files

```text
policy.json                         Approved lane and hard boundaries
schemas/send_queue.v1.schema.json   Queue contract for row shape and receipts
build_send_queue.py                 Builds candidate rows from the PracticeOS snapshot
qa_send_queue.py                    Executable QA gate for the queue
boundary/live_send_boundary.py      Deny-by-default live action boundary
check_live_boundary.py              Verifies boundary blocks without approval
sales-ops-live-swarm.json           Ringer manifest for Level 1 queue proof
```

## How to run the Level 1 bridge directly

```bash
cd /home/ankit114/repos/ringer
python3 local-sales-ops/live-operator/build_send_queue.py \
  --snapshot /tmp/ringer-sales-ops-input/live_practiceos_snapshot.json \
  --policy local-sales-ops/live-operator/policy.json \
  --out-dir /tmp/sales-ops-send-queue \
  --limit 5

python3 local-sales-ops/live-operator/qa_send_queue.py \
  --queue /tmp/sales-ops-send-queue/send_queue.jsonl \
  --policy local-sales-ops/live-operator/policy.json \
  --min-rows 5
```

## How to run it through Ringer

```bash
cd /home/ankit114/repos/ringer
./ringer.py lint local-sales-ops/live-operator/sales-ops-live-swarm.json
./ringer.py run local-sales-ops/live-operator/sales-ops-live-swarm.json
```

## Graduation

The current policy has:

```text
send_enabled=false
hubspot_write_enabled=false
```

To move to pilot send, choose the sender account and turn on a separate pilot policy. The send adapter must return a provider message receipt and a HubSpot activity receipt before any row counts as complete.

Ringer should act aggressively inside the approved lane, but it must hold rows when checks fail.
