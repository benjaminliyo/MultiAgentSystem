# Claude Code Install

## One-Command Install

From this repo's root:

```powershell
.\scripts\install.ps1 claude-code
```

```bash
./scripts/install.sh claude-code
```

That's it. Restart Claude Code and `/multiagent <task>` works in any project.

**To update:** re-run the same command after `git pull`. It overwrites installed files and merges hook wiring idempotently — no duplicate entries.

**To skip hook wiring:** add `-NoHooks` (PowerShell) or `--no-hooks` (Bash).

## Prerequisites

- Claude Code installed and configured.
- Python 3.11 or newer on your PATH (the installer and `scripts/multiagent_files.py` both use `tomllib`).
- This repo cloned somewhere on your machine.

## What Gets Installed

| Source (canonical repo)                        | Destination                                      |
|------------------------------------------------|--------------------------------------------------|
| `claude-code/agents/*.md` (6 files)            | `~/.claude/agents/`                              |
| `claude-code/skill/multiagent-workflow/`       | `~/.claude/skills/multiagent-workflow/`          |
| `claude-code/commands/multiagent.md`           | `~/.claude/commands/multiagent.md`               |
| `claude-code/hooks/*` (via settings)           | wired into `~/.claude/settings.json`             |

The installer also consults `skills/role-skill-map.toml`: skills installed under `~/.claude/skills/` that match a role's candidates are written into that installed agent's `skills:` frontmatter (preloaded at spawn). And if a gitignored `local/overlays/roles/<role>.md` exists, its content is appended to the installed agent body — personal additions without touching canonical files.

The agents are: `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, and the optional read-only `researcher`. PM is the main-thread agent and absorbs mechanical routing. See `CHANGELOG.md` (2026-06-29) for why there's no `multiagent-orchestrator`.

The hook wiring (five events, all silent outside active multiagent runs):

- **SessionStart** loads `<cwd>/.multiagent/project-profile.md` if present, so PM sees the project profile automatically.
- **UserPromptSubmit** reinjects a compact PM-mode reminder (role + current workflow state from `.multiagent/active-run.json`) on every prompt while a run is active — this is what keeps the PM role from fading over long sessions.
- **SubagentStart / SubagentStop** mechanically log every worker spawn/finish to the run folder (`transcripts/subagent-events.jsonl` + the message log) via `claude-code/hooks/subagent-log.py`.
- **Stop** warns if a `.multiagent/runs/<run>/run-summary.md` has `state:` not set to done/closed/completed.

The installer picks the `.ps1` variants on Windows and the `.sh` variants elsewhere (`subagent-log.py` runs via `python` everywhere). If you already have a `~/.claude/settings.json`, the installer merges into it: existing entries pointing at the same hook script get their command upgraded; unrelated hooks you added are preserved.

`scripts/multiagent_files.py` stays in the repo (the workflow invokes it by path for run-folder setup and message persistence). `git pull` is enough to update it.

## Verify

```powershell
python scripts\install.py validate-install --repo-root . --platform claude-code
```

```bash
python scripts/install.py validate-install --repo-root . --platform claude-code
```

A clean install reports `"complete": true` and an empty `missing` list.

You can override the install root with `--claude-home <path>` if your Claude Code config lives somewhere other than `~/.claude`.

## First Run

Restart Claude Code, then in any project repo:

```text
/multiagent fix the broken login redirect
```

The main session reads `~/.claude/agents/pm.md`, adopts PM's role, asks for Scoped Autonomy, creates `.multiagent/runs/YYYY-MM-DD-<slug>/`, and starts clarifying the task. PM enters plan mode with the task packet; `ExitPlanMode` is your approval gate. After approval, PM spawns Developer (and later Reviewer) as subagents.

The shorter `/multiagent` with no args asks you what to build instead of assuming a task.

## Manual Install (Fallback)

If Python isn't available or you want to see exactly what the installer does, run the copy commands by hand.

**PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude\agents | Out-Null
New-Item -ItemType Directory -Force -Path $HOME\.claude\skills\multiagent-workflow | Out-Null
New-Item -ItemType Directory -Force -Path $HOME\.claude\commands | Out-Null

Copy-Item claude-code\agents\*.md $HOME\.claude\agents\ -Force
Copy-Item -Recurse -Force claude-code\skill\multiagent-workflow\* $HOME\.claude\skills\multiagent-workflow\
Copy-Item claude-code\commands\multiagent.md $HOME\.claude\commands\multiagent.md -Force
```

**Bash:**

```bash
mkdir -p ~/.claude/agents ~/.claude/skills/multiagent-workflow ~/.claude/commands
cp claude-code/agents/*.md ~/.claude/agents/
cp -r claude-code/skill/multiagent-workflow/* ~/.claude/skills/multiagent-workflow/
cp claude-code/commands/multiagent.md ~/.claude/commands/multiagent.md
```

For hooks: open `claude-code/settings.example.json`, edit the absolute paths to your repo checkout, and merge the `hooks` block into `~/.claude/settings.json`.

## Uninstall

```powershell
Remove-Item $HOME\.claude\agents\pm.md, `
            $HOME\.claude\agents\developer.md, `
            $HOME\.claude\agents\developer-strong.md, `
            $HOME\.claude\agents\reviewer.md, `
            $HOME\.claude\agents\reviewer-strong.md, `
            $HOME\.claude\agents\researcher.md
Remove-Item -Recurse $HOME\.claude\skills\multiagent-workflow
Remove-Item $HOME\.claude\commands\multiagent.md
```

```bash
rm ~/.claude/agents/{pm,developer,developer-strong,reviewer,reviewer-strong,researcher}.md
rm -r ~/.claude/skills/multiagent-workflow
rm ~/.claude/commands/multiagent.md
```

Also remove the hook entries from `~/.claude/settings.json` if you wired them.

`.multiagent/` directories inside your project repos are independent run history; leave or delete them based on whether you want the workflow logs.

## Troubleshooting

**`/multiagent` is not a recognized command.** The command file isn't in `~/.claude/commands/` or the session needs restart. Re-run the installer and restart Claude Code.

**`subagent_type: "pm"` (or other roles) is not available.** Agent files aren't in `~/.claude/agents/` or the session needs restart. Same fix.

**The skill isn't auto-invoked when I say "run the multiagent workflow."** Verify `~/.claude/skills/multiagent-workflow/SKILL.md` exists. Verify its frontmatter (`name` and `description`) is intact — the `description` is what Claude Code uses to decide when to surface the skill. You can also invoke explicitly: "Use the multiagent-workflow skill."

**`python scripts/multiagent_files.py` fails with `ModuleNotFoundError: No module named 'tomllib'`.** You're on Python < 3.11. The installer and validator need 3.11+. Upgrade Python or install from a 3.11+ environment.

**Hooks aren't firing.** Restart Claude Code after any change to `~/.claude/settings.json`. If they still don't fire, your Claude Code version may use a different `hooks` schema than the installer writes — check `claude-code/settings.example.json` against Claude Code's current settings docs and adjust.

**Installer wrote hook paths that don't match my repo.** The installer uses the absolute path of the checkout it was run from. If you move the repo, re-run the installer from the new location.

## Related Docs

- `claude-code/skill/multiagent-workflow/SKILL.md` — what the skill actually does.
- `claude-code/agents/pm.md` — PM's role + routing contract (the workflow's source of truth).
- `CHANGELOG.md` — why the orchestrator agent isn't here.
- `FUTURE-PLANS.md` — when a spawnable orchestrator will come back (autonomous loops).
