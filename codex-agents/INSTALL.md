# Codex Install

## One-Command Install

From this repo's root:

```powershell
.\scripts\install.ps1 codex
```

```bash
./scripts/install.sh codex
```

That's it. Restart Codex (or open a new thread), then in any session:

```text
Run the multiagent workflow for this project. Start with the PM agent.
```

**To update:** re-run the same command after `git pull`. Installed files are regenerated in place from templates + your currently installed skills.

## Prerequisites

- Codex CLI installed and configured.
- Python 3.11 or newer on your PATH.
- This repo cloned somewhere on your machine.

## What Gets Installed

| Source (canonical repo)                             | Destination                                    |
|-----------------------------------------------------|------------------------------------------------|
| `codex-agents/templates/*.toml` (6 roles)           | `~/.codex/agents/*.toml` (rendered per user)   |
| `codex-skill/*/`                                    | `~/.codex/skills/<skill-name>/`                |
| `scripts/find_skill.py`, `skills/registry.toml`     | bundled into `~/.codex/skills/find-skill/`     |

The installer:

1. Copies canonical Codex skills from `codex-skill/` into `~/.codex/skills/`.
2. Bundles `find_skill.py` and `registry.toml` into the installed `find-skill` skill so it works without the repo checkout.
3. Scans `~/.codex/skills/` and `~/.codex/plugins/` for `SKILL.md` files.
4. Renders each `codex-agents/templates/<role>.toml` into `codex-agents/<role>.toml` with a `[[skills.config]]` block per discovered skill.
5. Copies the rendered TOMLs to `~/.codex/agents/`.

The rendered `codex-agents/*.toml` files are gitignored so per-user skill paths never enter version control. The upstream templates in `codex-agents/templates/` are the source of truth.

The agents are: `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, and optional read-only `researcher`. PM is the main-thread agent and absorbs mechanical routing. See `CHANGELOG.md` (2026-06-29) for why there's no `multiagent-orchestrator`.

## Verify

```powershell
python scripts\install.py validate-install --repo-root . --platform codex
```

```bash
python scripts/install.py validate-install --repo-root . --platform codex
```

A clean install reports `"complete": true`.

Override the install root with `--codex-home <path>` if your Codex install lives elsewhere.

The bundled find-skill engine can also be smoke-tested after install:

```powershell
python "$HOME\.codex\skills\find-skill\find_skill.py" search "excel spreadsheet"
```

## Flags

- `--codex-home <path>` — override `~/.codex`.
- `--skip-deploy` (only on `install-codex` subcommand) — write to `codex-agents/*.toml` in the repo but do not copy to `~/.codex/agents/`. Useful for previewing rendered output.

## First Run

Restart Codex or open a new thread, then in any project session:

```text
Run the multiagent workflow for this project. Start with the PM agent.
```

The main Codex session adopts PM's role and then spawns workers by name. Do not launch PM as a separate child subagent for the interactive workflow; PM mode stays active until `close-run` or `/multiagent off`.

```text
pm           # main thread
developer
developer-strong
reviewer
reviewer-strong
researcher   # optional, read-only exploration
```

## Troubleshooting

**Subagent types missing or not recognized.** Restart Codex or open a fresh thread. Codex loads custom-agent TOMLs at session start.

**`spawn_agent could not resolve the child model for service tier validation`.** The workflow is recognized but Codex custom-agent startup is failing in its own model/service-tier validation for a worker agent. Confirm a built-in agent (like `default`) can spawn in the same thread. If it can, restart Codex with a supported model selected, then retry the worker handoff. If the error persists while built-in agents work, treat it as a Codex runtime issue rather than a MultiAgentSystem install problem.

**Rendered TOMLs have no `[[skills.config]]` entries.** No `SKILL.md` files were discovered under `~/.codex/skills/` or `~/.codex/plugins/`. The install still works; the roles just won't reference any local skills. Install skills into `~/.codex/skills/` and re-run the installer.

**Tier-2 skill search cannot find the Codex catalog.** The repo `find-skill` wrapper uses the bundled engine for installed skills and the curated registry, then delegates Codex catalog lookup to the standard preinstalled `skill-installer` system skill. Confirm `~/.codex/skills/.system/skill-installer/SKILL.md` exists and restart Codex if it was installed or updated during the current session.

## Related Docs

- `CODEX-CUSTOM-AGENTS.md` — deeper reference: agent communication model, skill configuration, model/permission defaults.
- `codex-skill/multiagent-workflow/SKILL.md` — the recognition skill.
- `codex-skill/find-skill/SKILL.md` - the skill search-and-install wrapper.
- `codex-agents/templates/*.toml` — canonical role templates.
