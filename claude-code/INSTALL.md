# Claude Code Install

Install the PM-led multi-agent workflow into your user-level Claude Code config (`~/.claude/`). After install, `/multiagent <task>` in any Claude Code session launches the workflow.

## What Gets Installed

| Source (canonical repo)                        | Destination                                      | Required? |
|------------------------------------------------|--------------------------------------------------|-----------|
| `claude-code/agents/*.md` (5 files)            | `~/.claude/agents/`                              | yes       |
| `claude-code/skill/multiagent-workflow/`       | `~/.claude/skills/multiagent-workflow/`          | yes       |
| `claude-code/commands/multiagent.md`           | `~/.claude/commands/multiagent.md`               | yes       |
| `claude-code/hooks/*.{ps1,sh}` + `settings.example.json` | wired in `~/.claude/settings.json`     | optional  |

The agents are: `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`. There is no `multiagent-orchestrator` — PM is the main-thread agent and absorbs mechanical routing. See `CHANGELOG.md` (2026-06-29) for context.

Hooks are opt-in quality-of-life and live where you check out the repo (no copy step). Wire them via `~/.claude/settings.json` — see the "Optional: Hooks" section below.

The repo also contains `scripts/multiagent_files.py`, which the workflow calls for run-folder setup and message persistence. It is **not** copied into `~/.claude/`; the workflow invokes it from the canonical repo path. Make sure Python 3.11+ is on your PATH.

## Prerequisites

- Claude Code installed and configured.
- Python 3.11 or newer (needed by `scripts/multiagent_files.py` because it uses `tomllib`).
- This repo cloned somewhere on your machine. The default examples below assume `D:\Projects\MultiAgentSystem` (Windows). Adjust paths as needed.

## Install — PowerShell (Windows)

From the canonical repo root:

```powershell
# Make sure target directories exist.
New-Item -ItemType Directory -Force -Path $HOME\.claude\agents | Out-Null
New-Item -ItemType Directory -Force -Path $HOME\.claude\skills\multiagent-workflow | Out-Null
New-Item -ItemType Directory -Force -Path $HOME\.claude\commands | Out-Null

# Copy agents.
Copy-Item claude-code\agents\*.md $HOME\.claude\agents\ -Force

# Copy skill (whole folder, in case references/ is added later).
Copy-Item -Recurse -Force claude-code\skill\multiagent-workflow\* $HOME\.claude\skills\multiagent-workflow\

# Copy slash command.
Copy-Item claude-code\commands\multiagent.md $HOME\.claude\commands\multiagent.md -Force
```

## Install — Bash (WSL, Git Bash, macOS, Linux)

From the canonical repo root:

```bash
mkdir -p ~/.claude/agents ~/.claude/skills/multiagent-workflow ~/.claude/commands

cp claude-code/agents/*.md ~/.claude/agents/
cp -r claude-code/skill/multiagent-workflow/* ~/.claude/skills/multiagent-workflow/
cp claude-code/commands/multiagent.md ~/.claude/commands/multiagent.md
```

If you're on Git Bash on Windows and `~` resolves to a Cygwin-style home, prefer `$HOME` explicitly: `$HOME/.claude/...`.

## Restart Your Claude Code Session

Agent files and slash commands are loaded at session start. After copying, **start a new Claude Code session** (or restart the existing one) before invoking `/multiagent`.

## Verify The Install

From the canonical repo root:

```powershell
python scripts\multiagent_files.py validate-install --repo-root . --platform claude-code
```

```bash
python scripts/multiagent_files.py validate-install --repo-root . --platform claude-code
```

A clean install reports `complete: True` and an empty `missing` list. If anything is missing, the output tells you which path is absent — copy that file and re-run.

You can override the install root with `--claude-home <path>` if your Claude Code config lives somewhere other than `~/.claude`.

## First Run

In a Claude Code session inside any project repo:

```text
/multiagent fix the broken login redirect
```

The main session reads `~/.claude/agents/pm.md`, adopts PM's role, asks for Scoped Autonomy, creates `.multiagent/runs/YYYY-MM-DD-<slug>/`, and starts clarifying the task. PM enters plan mode with the task packet; `ExitPlanMode` is your approval gate. After approval, PM spawns Developer (and later Reviewer) as subagents.

The shorter `/multiagent` with no args asks you what to build instead of assuming a task.

## Optional: Hooks

Two opt-in Claude Code hooks live in `claude-code/hooks/`:

| Hook                           | Event           | What it does                                                                                          |
|--------------------------------|-----------------|-------------------------------------------------------------------------------------------------------|
| `session-start-load-profile`   | `SessionStart`  | If `<cwd>/.multiagent/project-profile.md` exists, emits its contents as session context.              |
| `stop-warn-unclosed-run`       | `Stop`          | Scans the most recent `.multiagent/runs/<run>/run-summary.md`; warns if `state:` is not done/closed/completed. |

Both ship in PowerShell (`.ps1`) and Bash (`.sh`) variants — pick the one your shell speaks.

### Wire them via settings.json

`claude-code/settings.example.json` shows the schema. Copy it as a starting point or merge into your existing `~/.claude/settings.json`:

```powershell
# If you have no ~/.claude/settings.json yet:
Copy-Item claude-code\settings.example.json $HOME\.claude\settings.json
```

```bash
# If you have no ~/.claude/settings.json yet:
cp claude-code/settings.example.json ~/.claude/settings.json
```

If you already have a `~/.claude/settings.json`, open `claude-code/settings.example.json` and merge the `hooks` block into yours by hand. **Do not point Claude Code at the example file directly** — it's a template.

After editing `~/.claude/settings.json`, **restart Claude Code** so the new hook wiring takes effect.

### Adjust the paths

The example wires absolute paths to `D:/Projects/MultiAgentSystem/claude-code/hooks/*.ps1`. If your checkout lives elsewhere, edit the `command` strings to match.

### Pick PowerShell or Bash

The example wires the `.ps1` variants. For WSL / Git Bash / macOS / Linux, replace each `command` with the bash variant:

```json
"command": "bash /path/to/MultiAgentSystem/claude-code/hooks/session-start-load-profile.sh"
```

### Verify hooks fire

For `session-start-load-profile`: in a project repo that has `.multiagent/project-profile.md`, open a new Claude Code session. The profile content should appear as additional session context (you'll see a "SessionStart hook additional context:" line in early-session reminders).

For `stop-warn-unclosed-run`: in a project repo with an open `.multiagent/runs/<run>/` whose `run-summary.md` has `state: developer_implementation` (or anything other than `done`/`closed`/`completed`), let Claude finish a turn. The warning should appear in stderr / Claude's tool output. To silence it, set `state: done` in the run-summary at closeout.

### Remove hooks

Delete the relevant entries from `~/.claude/settings.json` and restart the Claude Code session.

### Schema gotcha

If your Claude Code version uses a different `hooks` schema than the example, the hooks won't fire silently and you won't see an error. Test by triggering the event after wiring; if nothing appears, check Claude Code's current settings docs and adapt.

## Updating

When the canonical repo changes (`git pull`), re-run the copy commands above. They use `-Force` / unconditional `cp` so they overwrite existing installed files. Then restart the Claude Code session.

The script (`scripts/multiagent_files.py`) is invoked from the repo path, so a `git pull` updates it automatically — no copy needed.

## Uninstall

```powershell
Remove-Item $HOME\.claude\agents\pm.md, `
            $HOME\.claude\agents\developer.md, `
            $HOME\.claude\agents\developer-strong.md, `
            $HOME\.claude\agents\reviewer.md, `
            $HOME\.claude\agents\reviewer-strong.md
Remove-Item -Recurse $HOME\.claude\skills\multiagent-workflow
Remove-Item $HOME\.claude\commands\multiagent.md
```

```bash
rm ~/.claude/agents/{pm,developer,developer-strong,reviewer,reviewer-strong}.md
rm -r ~/.claude/skills/multiagent-workflow
rm ~/.claude/commands/multiagent.md
```

`.multiagent/` directories inside your project repos are independent run history; leave or delete them based on whether you want the workflow logs.

## Troubleshooting

**`/multiagent` is not a recognized command.** The command file isn't in `~/.claude/commands/` or the session needs restart. Re-run the copy commands above and restart Claude Code.

**`subagent_type: "pm"` (or other roles) is not available.** Agent files aren't in `~/.claude/agents/` or the session needs restart. Same fix.

**The skill isn't auto-invoked when I say "run the multiagent workflow."** Verify `~/.claude/skills/multiagent-workflow/SKILL.md` exists. Verify its frontmatter (`name` and `description`) is intact — the `description` is what Claude Code uses to decide when to surface the skill. You can also invoke explicitly: "Use the multiagent-workflow skill."

**`python scripts/multiagent_files.py` fails with `ModuleNotFoundError: No module named 'tomllib'`.** You're on Python < 3.11. The `validate-install` and `append-message` commands need 3.11+ for canonical-set validation. Upgrade Python or install from a 3.11+ environment.

**Validation reports `multiagent-orchestrator.md` missing.** It shouldn't — the script no longer expects it. If you see this, your `scripts/multiagent_files.py` is out of date relative to the docs; `git pull` and retry.

## Related Docs

- `claude-code/IMPLEMENTATION-PLAN.md` — the plan that produced this install layout.
- `claude-code/skill/multiagent-workflow/SKILL.md` — what the skill actually does.
- `claude-code/agents/pm.md` — PM's role + routing contract (the workflow's source of truth).
- `CHANGELOG.md` — why the orchestrator agent isn't here.
- `FUTURE-PLANS.md` — when a spawnable orchestrator will come back (autonomous loops).
