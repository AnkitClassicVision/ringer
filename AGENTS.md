# Ringer repo agent notes

## Mott scheduling test constants (owner-approved, Ankit 2026-08-04)

Ankit explicitly approved storing his own test-contact identity here for harness use.

- **Bland agent number (send from):** `+15095611012` — "Emerald Eye Care | Clarkston", the live Mott 509 SMS line.
- **Mott pathway id:** `94abad8b-fbe2-4e67-9c64-d9b586dd2653` (version is whatever the line is bound to — verify with `GET /v1/sms/numbers`, never assume).
- **Ankit's live-person test identity:** Ankit Patel, cell `6157793629`, patient id `4362694474`, store `711`.
- **Rachel dummy (automated harness subject):** patient id `4376662466`, cell `6468942428`, store `711`.
- **Test SMS line (non-production):** `+14158778905` "AI Bot Test" — normally bound to the CVC pathway (`09ed1fbb…`); restore snapshot at `my-manifests/mk2-number-and-comeback/workGLD6/sms-restore-8905.json`.

## Standing harness rules

- Opener sends are **coordinator-only** (never a Ringer worker):
  `checks/send_rachel_sample.py --agent-number +15095611012 --version <bound> [--send]` under
  `secret_exec.py --secret-env BLAND_API_KEY=mybcat/ai/api-keys/bland`. Its preflight fail-closes
  unless the line is bound to the exact version.
- `/v1/sms/update` returns 500 (Bland-side bug, reconfirmed 2026-08-04) — number rebinds and
  version flips happen in the Bland dashboard, by Ankit.
- Automated scripts must never contain the turns `1` or `yes` (they book real appointments).
  A live human test replying `1`/`yes` books a REAL appointment for that patient id — cancel via
  the harness afterward if unwanted.
- Mask digit runs in all printed/logged output (harness convention: last-4 only).
- Manifest `expect_files` entries must be plain FILES — Ringer does not match directories
  (a directory entry fails the run even when the check passes; cost two wasted runs 2026-08-04).
- Mint discipline: validate-then-mint only, mints are unattached, Bland auto-increments the
  version number; only Ankit flips a line.
