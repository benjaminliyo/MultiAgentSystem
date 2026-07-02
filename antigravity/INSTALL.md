# Antigravity & agy Install

## One-Command Install

From this repo's root:

```powershell
.\scripts\install.ps1 antigravity
```

```bash
./scripts/install.sh antigravity
```

That's it. Restart Antigravity/`agy`, then `/multiagent <task>` or the trigger phrase `"run the multiagent workflow"` in any session launches the workflow.

**To update:** re-run the same command after `git pull`. Installed files are overwritten in place.

## Prerequisites

- Antigravity / `agy` CLI installed and configured.
- Python 3.11 or newer on your PATH (used by the installer and by `scripts/multiagent_files.py` for run-folder setup and message persistence).
- This repo cloned somewhere on your machine.

## What Gets Installed

| Source (canonical repo)                          | Destination                                            |
|--------------------------------------------------|--------------------------------------------------------|
| `antigravity/agents/*.md` (5 files)              | `~/.gemini/config/agents/`                             |
| `antigravity/skill/multiagent-workflow/SKILL.md` | `~/.gemini/config/skills/multiagent-workflow/SKILL.md` |

The agents are: `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`. PM is the main-thread agent and absorbs mechanical routing.

`scripts/multiagent_files.py` is not copied — the workflow invokes it from this repo path. `git pull` updates it.

## Verify

```powershell
python scripts\install.py validate-install --repo-root . --platform antigravity
```

```bash
python scripts/install.py validate-install --repo-root . --platform antigravity
```

A clean install reports `"complete": true` and an empty `missing` list.

You can override the install root with `--antigravity-home <path>` if your config lives somewhere other than `~/.gemini/config`.

## First Run

Restart Antigravity/`agy`, then in any project repo:

- Type `/multiagent <task>` or use trigger: `"run the multiagent workflow for this project."`
- The root session reads `~/.gemini/config/agents/pm.md`, adopts PM's role, asks for Scoped Autonomy, creates the run folder under `.multiagent/runs/`, and drafts the task packet.
- Once approved, PM spawns Developer and Reviewer subagents (automatically using `define_subagent` if they are not already globally defined, so no restart is required after adding new roles).

## Manual Install (Fallback)

If Python isn't available or you want to see exactly what the installer does:

**PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.gemini\config\agents | Out-Null
New-Item -ItemType Directory -Force -Path $HOME\.gemini\config\skills\multiagent-workflow | Out-Null

Copy-Item antigravity\agents\*.md $HOME\.gemini\config\agents\ -Force
Copy-Item antigravity\skill\multiagent-workflow\SKILL.md $HOME\.gemini\config\skills\multiagent-workflow\SKILL.md -Force
```

**Bash:**

```bash
mkdir -p ~/.gemini/config/agents ~/.gemini/config/skills/multiagent-workflow
cp antigravity/agents/*.md ~/.gemini/config/agents/
cp antigravity/skill/multiagent-workflow/SKILL.md ~/.gemini/config/skills/multiagent-workflow/SKILL.md
```

## Troubleshooting

**Subagent types missing or not recognized.**
1. Re-run the installer.
2. Start a new Antigravity/`agy` session.
3. Confirm `~/.gemini/config/agents/pm.md` exists and contains valid YAML frontmatter.
4. Run the validator command above.

**Skill isn't auto-invoked.** Verify `~/.gemini/config/skills/multiagent-workflow/SKILL.md` exists with intact frontmatter (`name`, `description`). Invoke explicitly: "Use the multiagent-workflow skill."
