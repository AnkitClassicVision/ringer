# Install And Upgrade Protocol

## Table of contents

- Product relationship
- Official editions
- Detection
- Approval-based installation
- Surface rules
- Cross-harness implant boundary
- Rollback record

## Product relationship

Mission Fit extends Clean My AI Harness without editing its files. The base Cleaner maps and safely changes the visible harness. Mission Fit checks whether the recurring jobs fit that harness and produces evidence-backed recommendations for the Cleaner to apply later.

Installing Mission Fit beside the Cleaner is the upgrade. Do not merge their folders or copy Mission Fit files into an existing Cleaner directory.

The Cross-Harness Skill Implant workflow is separate. It can install one approved skill package into declared local roots, but it does not download or upgrade the official Cleaner. A Cleaner approval never approves a Mission Fit recommendation or an implant plan, and approval of an implant plan never approves Cleaner installation.

## Official editions

- Claude edition: `https://github.com/NateBJones-Projects/clean-my-ai-harness/raw/main/clean-my-ai-harness-claude.zip`
- Codex edition: `https://github.com/NateBJones-Projects/clean-my-ai-harness/raw/main/clean-my-ai-harness-codex.zip`
- Source repository: `https://github.com/NateBJones-Projects/clean-my-ai-harness`

Do not substitute a similarly named package or mirror.

## Detection

Check only known paths and the current project:

- Codex: `~/.codex/skills/clean-my-ai-harness-codex/SKILL.md`
- Shared agent skills: `~/.agents/skills/clean-my-ai-harness-codex/SKILL.md`
- Claude Code: `~/.claude/skills/clean-my-ai-harness-claude/SKILL.md`
- Project-local `.agents/skills/` or `.claude/skills/` under the approved target

The bundled detector reads these exact locations. It does not search the whole home directory.

Treat a visible SKILL.md with the expected frontmatter name as `VERIFIED`. Treat a user-confirmed Claude.ai upload as `USER_REPORTED`. Otherwise use `NOT_FOUND` or `INACCESSIBLE`.

## Approval-based installation

Before an install, show:

1. the official package URL;
2. the destination or upload surface;
3. whether an existing destination will be replaced;
4. the backup or disable path;
5. the required restart or skill-index refresh.

Ask for explicit approval. After approval, install only the named edition. Re-read the installed SKILL.md and report its frontmatter name. Do not begin a mission audit in the same approval step unless the user separately asked for it.

## Surface rules

### Codex

Unzip the Codex edition, copy `clean-my-ai-harness-codex` into `~/.codex/skills/`, and restart Codex. Preserve an existing customized folder by staging the new edition beside a backup and presenting a diff before replacement.

### Claude Code

Place the Claude edition in the configured Claude skills directory, normally `~/.claude/skills/`, then refresh or restart the harness. Do not assume the path when configuration shows another root.

### Claude.ai

The agent cannot upload or enable a skill in the product UI. Tell the user to open Customize > Skills, upload the Claude zip, enable it, and begin a new conversation. Resume only after the user confirms the upload.

## Rollback record

Record:

- prior installation state;
- source URL and edition installed;
- destination or UI action;
- backup location when files changed;
- restart or refresh completed;
- verification result.

Installing Mission Fit never grants approval to change the audited harness.

## Cross-harness implant boundary

For an approved local implant, follow [cross-harness-skill-implant.md](cross-harness-skill-implant.md). Inspect must finish before mutation. The operator approves the exact immutable `plan_hash`, not a description of the plan. The request must seal the exact absolute rollback backup root; apply's `--backup-root` only cross-checks that sealed value. Any change to a source hash, target, collision action, scope exclusion, discovery adapter, backup root, or rollback rule creates a different plan and requires a new inspect and approval.

Keep one canonical package. Use links by default. Declare a copy only for a target that cannot use the canonical link, and require a real non-symlink directory with exact tree parity during every verification. Rollback refuses drift before mutation and compensates a partial multi-target rollback before returning failure. Do not turn this workflow into a repository migration, remote rollout, control plane, scheduled job, framework port, or unrelated skill install.
