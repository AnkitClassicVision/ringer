# Lane 39 port onto deployed lane 38

## Result

`ported-bland_gateway.py` starts from the 142,598-byte deployed lane-38 artifact and adds only the three hunks in `lane39-combined.diff`. The normalized hunk comparison returned `0` (identical). No source outside this working directory was modified.

## Deployed lane-38 behavior preserved

- `_order_availability_slots(slots, time_pref="")`, including the `latest`/`last` ordering and the `anchor=HH:MM` reference-point distance ordering.
- `availability_envelope(result, time_pref="")`, including application of `_order_availability_slots` before selecting the first slot.
- `/availability` handler propagation of `body.get("time_pref", "")` into both the primary and alternate-store availability envelopes.
- All other deployed content was preserved byte-for-byte because the port was made by copying the deployed artifact first and changing only `resolve_relative_date`.

## Lane-39 hunks applied

All changes are confined to `resolve_relative_date`:

1. Strip only a trailing 12-hour clock suffix from an extracted datetime before date parsing.
2. Relocate `number_words` above anchor-word handling.
3. Add relative day/week/month offset parsing, including bare forms and `from today`, `from now`, and `out` suffixes.

## Test reconciliation

None. The unmodified lane-39b test tree passed against the deployed-based port, so no files were created under `updated-tests/`.

## Verification commands and output tails

### Exact approved-hunk comparison

Run from this working directory:

```bash
diff -u deployed-lane-38-bland_gateway.py ported-bland_gateway.py > actual-port.diff || true
sed -n '5,$p' lane39-combined.diff | sed -E 's/^(@@ [^@]* @@).*/\1/' > verification/expected-hunks.diff
sed -n '3,$p' actual-port.diff | sed -E 's/^(@@ [^@]* @@).*/\1/' > verification/actual-hunks.diff
cmp -s verification/expected-hunks.diff verification/actual-hunks.diff
echo "normalized_hunks_cmp=$?"
```

Output tail:

```text
normalized_hunks_cmp=0
```

### Full pytest suite

Scratch setup and command:

```bash
cp -a /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGW39b/gw-datetime-tolerance/gw ./scratch-lane39b
cp ported-bland_gateway.py scratch-lane39b/container/bland_gateway.py
cd scratch-lane39b
pytest -q 2>&1 | tee ../pytest-full.log
```

Output tail:

```text
tests/test_bland_gateway.py: 21 warnings
  .../scratch-lane39b/container/bland_gateway.py:760: DeprecationWarning: Parsing dates involving a day of month without a year specified is ambiguous

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
71 passed, 21 warnings, 13 subtests passed in 0.58s
```

The warnings are pre-existing date-parser deprecation warnings, not test failures.

### Standalone proof script

The supplied script resolves `gw/container/bland_gateway.py` relative to itself, so the verified scratch layout was placed at `verification/gw` with the script beside it:

```bash
mkdir -p verification
cp -a scratch-lane39b verification/gw
cp proof_parse.py verification/proof_parse.py
cd verification
python3 proof_parse.py 2>&1 | tee ../proof-parse.log
```

Output tail:

```text
PHRASE=08/06/2026 10:30 am DATE=2026-08-06
PHRASE=2 weeks from today DATE=2026-08-18
PHRASE=two weeks from today DATE=2026-08-18
PHRASE=in 2 weeks DATE=2026-08-18
PHRASE=2 weeks DATE=2026-08-18
PHRASE=10 days from now DATE=2026-08-14
```

An initial invocation from the CWD failed because the proof script hard-codes the sibling directory name `gw`; changing only the scratch layout fixed that harness-path issue.

### Syntax and artifact hashes

```bash
python3 -m py_compile ported-bland_gateway.py
sha256sum deployed-lane-38-bland_gateway.py ported-bland_gateway.py
```

Output:

```text
6e42c2f55ca2e0820bcef4973195290977f8e8be83ed09511f8d463a61c417c3  deployed-lane-38-bland_gateway.py
ba30eda04f3f07986f4c868b20d89c80bc828833177dfdab43606b34b9ffd9f1  ported-bland_gateway.py
```

### Independent port checker

```bash
python3 /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/checks/check_port39.py ported-bland_gateway.py deployed-lane-38-bland_gateway.py /home/ankit114/repos/gw-diag-snap/container/bland_gateway.py 2>&1 | tee check-port39.log
```

Output:

```text
PASS: lane-39 ported onto deployed lane-38 truth (32 lane-38 lines preserved; 71 passed, 21 warnings, 13 subtests passed in 1.88s)
```
