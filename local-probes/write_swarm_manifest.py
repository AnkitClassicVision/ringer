from pathlib import Path
import json


def check(script, output, marker, phrases):
    phrase_list = repr(phrases)
    return f"""python3 - <<'PY'
from pathlib import Path
import subprocess, sys
script = Path({script!r})
out = Path({output!r})
required = {phrase_list}
if not script.exists():
    print(f'FAIL: {{script}} missing')
    sys.exit(1)
if script.stat().st_size == 0:
    print(f'FAIL: {{script}} is empty')
    sys.exit(1)
proc = subprocess.run([sys.executable, str(script)], text=True, capture_output=True, timeout=20)
if proc.returncode != 0:
    print(f'FAIL: executing {{script}} returned {{proc.returncode}}')
    print('stdout:', proc.stdout)
    print('stderr:', proc.stderr)
    sys.exit(1)
marker = {marker!r}
if marker not in proc.stdout:
    print('FAIL: expected marker %r in script stdout, got %r' % (marker, proc.stdout))
    sys.exit(1)
if not out.exists():
    print(f'FAIL: {{out}} missing after executing {{script}}')
    sys.exit(1)
text = out.read_text(encoding='utf-8')
missing = [p for p in required if p not in text]
if missing:
    print('FAIL: output file is missing required phrases:', missing)
    print('file excerpt:', text[:1000])
    sys.exit(1)
print(f'PASS: executed {{script}} and verified {{out}} contains required setup guidance')
PY"""

base_rules = (
    "No external writes. Do not read secrets. Work only in the current task directory. "
    "Create both the Python generator script and the markdown artifact before finishing. "
    "The generator script must be executable with python3 and must rewrite the markdown artifact when run."
)

tasks = [
    {
        "key": "lane-inventory",
        "task_type": "docs",
        "engine_args": ["-c", "model_reasoning_effort=low"],
        "spec": base_rules + " Create make_lane_inventory.py and lane-inventory.md. The markdown must explain the current Ringer worker lanes: codex works and passed demo; opencode is configured for OpenRouter but still needs user-owned auth; grok is installed/configured but still needs user-owned OAuth and a qualifying plan. Include sections titled '# Ringer Lane Inventory', '## Working now', '## Ready after sign-in', and '## Proof commands'. The script must print LANE_INVENTORY_OK.",
        "check": check("make_lane_inventory.py", "lane-inventory.md", "LANE_INVENTORY_OK", ["# Ringer Lane Inventory", "## Working now", "codex", "## Ready after sign-in", "opencode", "grok", "## Proof commands"]),
        "expect_files": ["make_lane_inventory.py", "lane-inventory.md"],
        "timeout_s": 900,
        "verified": "executing the generator proves the lane inventory artifact can be regenerated and contains the configured/blocked lane state",
    },
    {
        "key": "manifest-starter",
        "task_type": "docs",
        "engine_args": ["-c", "model_reasoning_effort=low"],
        "spec": base_rules + " Create make_manifest_starter.py and first-real-manifest-guide.md. The markdown must teach how to write a first real Ringer manifest with 2-4 independent tasks, self-contained specs, check commands that print WHY failures happen, expect_files, verified lines, max_parallel, and task_type. Include sections titled '# First Real Ringer Manifest', '## Manifest rules', '## Check design', and '## Copyable skeleton'. The script must print MANIFEST_STARTER_OK.",
        "check": check("make_manifest_starter.py", "first-real-manifest-guide.md", "MANIFEST_STARTER_OK", ["# First Real Ringer Manifest", "## Manifest rules", "2-4 independent tasks", "expect_files", "verified", "## Check design", "WHY", "## Copyable skeleton"]),
        "expect_files": ["make_manifest_starter.py", "first-real-manifest-guide.md"],
        "timeout_s": 900,
        "verified": "executing the generator proves the first-manifest guide can be regenerated and includes the required manifest/check fields",
    },
    {
        "key": "model-scoreboard",
        "task_type": "docs",
        "engine_args": ["-c", "model_reasoning_effort=low"],
        "spec": base_rules + " Create make_model_scoreboard.py and model-scoreboard-cheatsheet.md. The markdown must explain ./ringer.py models, first_try_pass_rate vs pass_rate, task_type slicing, why local history is personal to this machine, and how cheap lanes graduate from untested to probation to proven. Include sections titled '# Ringer Model Scoreboard', '## What it reads', '## How to route', and '## Promotion ladder'. The script must print MODEL_SCOREBOARD_OK.",
        "check": check("make_model_scoreboard.py", "model-scoreboard-cheatsheet.md", "MODEL_SCOREBOARD_OK", ["# Ringer Model Scoreboard", "./ringer.py models", "first_try_pass_rate", "pass_rate", "task_type", "## How to route", "## Promotion ladder", "untested", "probation", "proven"]),
        "expect_files": ["make_model_scoreboard.py", "model-scoreboard-cheatsheet.md"],
        "timeout_s": 900,
        "verified": "executing the generator proves the scoreboard cheat sheet can be regenerated and explains evidence-based routing terms",
    },
]
manifest = {"run_name": "ringer-first-real-work", "workdir": "/tmp/ringer-first-real-work", "max_parallel": 3, "tasks": tasks}
Path("/home/ankit114/repos/ringer/swarm.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("/home/ankit114/repos/ringer/swarm.json written with", len(tasks), "tasks")
