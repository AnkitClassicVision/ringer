# How to write a Ringer manifest (properly)

A manifest is the to-do list Ringer runs. It is always **written by a person or
an agent before the run** — Ringer never generates it (except the toy `demo`).
This guide is how to write one that passes checks and self-heals, built from
Nate's documented schema (`templates/`, the guide at unlock-ai.natebjones.com)
and the concrete failures from the 2026-07-08/09 sessions.

## The schema (what fields exist)

A manifest is JSON. Two levels: **run-level** and **task-level**.

### Run-level

```jsonc
{
  "run_name": "my-job",          // becomes the run id prefix + library label
  "workdir": "/tmp/ringer-my-job", // where task subdirs + shared files live
  "max_parallel": 4,             // how many workers run at once (see decision rule)
  "tasks": [ ... ]               // the list — see task-level below
}
```

Optional run-level: `"worktrees": true` plus `"repo": "/path"` gives each task
an isolated git worktree (advanced; see README worktree footgun — PASS deletes
the worktree). `"worktree_lfs": "materialize"` is the backward-compatible
default. Set it to `"skip"` for code-only podcast/media manifests so Git LFS
objects are not copied into every worktree.

### Task-level (each item in `tasks`)

| Field | Required | What it does |
|---|---|---|
| `key` | yes | Task name. Becomes the task subdir + the label everywhere. |
| `spec` | yes | The prompt handed to the worker. Where most of the design lives. |
| `check` | yes | Shell command run after the worker exits. Exit 0 = PASS. |
| `engine` | no | Which lane runs it (default `codex`). Pick from `~/.config/ringer/config.toml`. |
| `model` | no | Override the engine's `model_default` for this task. |
| `task_type` | no | Free-form tag (`docs`, `code-feature`, `research`...) so the scoreboard learns. **Always set it.** |
| `expect_files` | no | Files that must exist + be non-empty before the check runs. |
| `timeout_s` | no | Per-task kill timer. Default 900. |
| `engine_args` | no | Extra CLI flags spliced at `{engine_args}` (e.g. `["-c","model_reasoning_effort=low"]`). |
| `verified` | no | One plain-English sentence: what the check proves. Shown on the results page. **Always set it.** |
| `full_access` | no | Worker runs unsandboxed. Needs `allow_full_access=true` in config too. |

## The 6-part spec anatomy

Every spec in Nate's templates follows this shape. Steal it — do not freestyle.

```
1. ROLE        "You are a market scout for X" (one bounded job)
2. INPUTS      exact paths / facts block: "PRODUCT FACTS: ...", "read /abs/path.csv"
3. BOUNDARY    "write only ./report.md", "never modify files outside this task directory"
4. TASK        the transformation, output-first: "write ./report.md, 400-900 words..."
5. OUTPUT CONTRACT  exact filename + machine-parseable format the check targets
6. HARD RULES  "no invented facts", "mark assumptions", "plain language, no hype"
```

The worker must get everything it needs *in the spec*. If a worker needs a fact,
put the fact in the spec. If it needs a file, put the **absolute path** in the
spec. Do not rely on context the worker doesn't have.

## The 4 check rules (this is where most runs die)

The check is more important than the spec. A bad check accepts fake proof; a
good check makes worker mistakes self-healable and design mistakes visible.

**1. Execute, don't just inspect.**
- ❌ `test -s report.md` (worker writes garbage, passes)
- ✅ run the script, count real rows, assert real values
- *Our sales-ops grep-only checks accepted fabricated output. Execution is the
  only evidence Ringer believes.*

**2. Print a clear WHY on failure.**
- ❌ silent `exit 1`
- ✅ `print(f'WHY: expected 40-70 photos, got {len(paths)}'); sys.exit(1)`
- *Ringer's retry feeds the check's stdout back into the next attempt. No WHY =
  the worker re-fails blind. A diff beats `diff -q`; an assert with a message
  beats a bare test.*

**3. Be fast. Checks are capped at ~60 seconds.**
- ❌ a check that *renders* a 10-minute video (our baldev75 round 2 — TIMED OUT)
- ✅ the worker does slow work; the check only *verifies* the output
- *If the artifact takes minutes to produce, the worker must produce it and the
  check must only inspect it (e.g. `ffprobe` on an existing file). Never put the
  slow build inside the check.*

**4. Cross-reference real data a worker cannot invent.**
- ❌ "does the file mention 'deals'?"
- ✅ "are these deal IDs present in the live snapshot?"
- *This is what stops a worker from satisfying the check with made-up content.*

## Cross-task file sharing (the isolation rule)

**Each task runs in its own subdirectory under `workdir`.** A task cannot see
another task's files by default. This bit us in baldev75 round 1: `build-videos`
looked for `stayin_alive_photos.txt`, which lived in a *sibling* task dir.

**If task B needs task A's output:**
- Have A write to the **shared workdir root** (`/tmp/ringer-<job>/file.txt`),
  not A's task-local dir. Use absolute paths in both spec and check.
- Or run serial (`max_parallel: 1`) and have B read from A's known output path.

Never assume a task can see a sibling's files. It cannot.

## Parallel vs serial (the `max_parallel` decision)

- **Parallel** (`max_parallel: 4+`) when tasks are **independent** — each writes
  only its own files, no shared state. This is the swarm's power. Nate's
  `launch-kit` uses 6; `research-with-proof` uses 4.
- **Serial** (`max_parallel: 1`) when tasks **share files or collide** — same
  CSV reads, same output dir, same repo. Parallel here causes races. Our baldev75
  curation tasks hit a transient file error under parallel that vanished serial.

Rule of thumb: if two tasks touch the same file, run serial.

## Lint before every run

```bash
./ringer.py lint my-manifests/recurring/my-job.json
```

Lint catches: checks that cannot fail, silent checks, write collisions, serial
fan-out, underspecified specs, missing `verified`. It is non-blocking (warnings)
but treats them as teachable. **Never skip it.** `run` and `demo` also print
lint warnings after loading the manifest.

## The retry model (what self-heals and what doesn't)

Ringer retries a failed task **once**, with the check's WHY output prepended to
the spec. So:

| Failure type | Self-heals? | Why |
|---|---|---|
| Worker content/code mistake | ✅ Yes | Retry sees the WHY, adapts |
| Check prints a clear WHY | ✅ Yes | Retry has context to fix against |
| Worker can't reach a resource | ⚠️ Maybe | Only if the worker has the tools to fix it |
| **Check itself is buggy** | ❌ No | Worker is fine but can't pass a broken check |
| **Manifest design wrong** (bad graph, missing inputs, cross-task paths) | ❌ No | No retry fixes a structural flaw |
| **Needs adaptive multi-turn judgment** (debugging env, changing approach) | ❌ No | That's orchestrator work |

**Lesson:** write checks and manifests so that *worker* mistakes are the only
kind that can fail. If the scaffolding is wrong, no retry saves you — read the
run, diagnose, re-design as round 2.

## Rounds are expected (Nate ships them)

`templates/launch-kit/` contains `manifest.json`, `manifest-round2.json`, AND
`manifest-round3.json`. **Round 1 exposing flaws is the designed-for case.** The
loop is: run → read failures + the WHY → diagnose (worker vs design) → fix the
manifest → re-run as round 2. Do not expect perfection on round 1; do expect to
read failures fast.

One job = one `run_name`. Retries are rounds under the same name, not
`-v2-retry`-suffixed scattered runs (the sales-ops patch-loop anti-pattern).

## Worked example: what NOT to do (baldev75, 2026-07-08)

Three failures, three different root causes — all above the worker:

1. **Cross-task paths (round 1):** curation wrote to task-local dirs; build task
   couldn't see them. *Fix: write to shared workdir root with absolute paths.*
2. **Slow work in the check (round 2):** check contained the ffmpeg render;
   killed at the 60s cap. *Fix: worker builds, check only runs ffprobe.*
3. **Check-environment CSV error (rounds 1-3):** check couldn't open a CSV the
   worker opened fine. *Diagnosis incomplete; worked around by verifying output
   directly. Lesson: if a check can't reliably reach a resource, move that
   verification out of the check or copy the resource into the task dir first.*

All three were design/scaffolding problems. The workers were correct every time.
The checks did their job by refusing to pass unproven work.

## Minimal task template (copy this)

```json
{
  "key": "task-name",
  "engine": "pi-openrouter",
  "model": "openrouter/qwen/qwen3-coder",
  "task_type": "docs",
  "timeout_s": 900,
  "spec": "You are a <role> for <project>. Work only in your current task directory; write only ./output.md. INPUTS: read /abs/path/to/input. TASK: <transformation, output-first>. OUTPUT CONTRACT: ./output.md must <parseable format>. HARD RULES: no invented facts, mark assumptions, plain language.",
  "check": "python3 - <<'PY'\nfrom pathlib import Path\nimport sys\np=Path('output.md')\nif not p.exists(): print('WHY: output.md missing'); sys.exit(1)\ntext=p.read_text()\nif len(text.split()) < 100: print('WHY: too short'); sys.exit(1)\nif 'required phrase' not in text.lower(): print('WHY: missing required phrase'); sys.exit(1)\nprint('PASS: output.md exists, is substantial, and contains the required content')\nPY",
  "expect_files": ["output.md"],
  "verified": "executing the check proves output.md exists, is substantial, and contains the required content"
}
```

## Engine routing

Pick from `~/.config/ringer/config.toml` and `docs/MODEL-MENU.md`. Route by the
scoreboard (`./ringer.py models --explore`), not vibes:
- use `engine: "pi-openrouter"` with an exact lowercase
  `openrouter/<publisher>/<model>` selector for OpenRouter text models
- historical OpenCode evidence may inform comparisons, but it is not copy-ready
  routing guidance for current OpenRouter tasks
- proven frontier for load-bearing (`codex`)
- `claude-lean` for long specs (full `claude` bloats on context)
- `local` (gemma4:31b) only for single low-stakes / privacy tasks (serial)

## Checklist before every run

- [ ] `task_type` set on every task (so the scoreboard learns)
- [ ] `verified` set on every task (so the results page says what was proved)
- [ ] Each spec has all 6 parts: role, inputs, boundary, task, output contract, hard rules
- [ ] Check executes (not just inspects), prints WHY, is <60s, cross-references real data
- [ ] No cross-task file assumptions — shared outputs go to workdir root
- [ ] `max_parallel` matches independence (serial if shared state)
- [ ] `./ringer.py lint manifest.json` is clean
