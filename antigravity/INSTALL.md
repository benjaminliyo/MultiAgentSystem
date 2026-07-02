# Antigravity & agy Install

Install the PM-led multi-agent workflow into your user-level Google Antigravity config (`~/.gemini/config/`). After install, `/multiagent <task>` or the trigger phrase `"run the multiagent workflow"` in any Antigravity or `agy` session launches the workflow.

## What Gets Installed

| Source (canonical repo)                        | Destination                                      | Required? |
|------------------------------------------------|--------------------------------------------------|-----------|
| `antigravity/agents/*.md` (5 files)            | `~/.gemini/config/agents/`                       | yes       |
| `antigravity/skill/multiagent-workflow/SKILL.md` | `~/.gemini/config/skills/multiagent-workflow/SKILL.md` | yes |

The agents are: `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`. PM is the main-thread agent and absorbs mechanical routing.

The repo also contains `scripts/multiagent_files.py`, which the workflow calls for run-folder setup and message persistence. It is **not** copied into `~/.gemini/config/`; the workflow invokes it from the canonical repo path. Make sure Python 3.11+ is on your PATH.

## Prerequisites

- Antigravity / `agy` CLI installed and configured.
- Python 3.11 or newer (needed by `scripts/multiagent_files.py` because it uses `tomllib` internally for Codex-compat validation, but is called for JSONL logging as well).
- This repo cloned somewhere on your machine. The default examples below assume `D:\Projects\MultiAgentSystem` (Windows). Adjust paths as needed.

## Install — PowerShell (Windows)

From the canonical repo root:

```powershell
# Make sure target directories exist.
New-Item -ItemType Directory -Force -Path $HOME\.gemini\config\agents | Out-Null
New-Item -ItemType Directory -Force -Path $HOME\.gemini\config\skills\multiagent-workflow | Out-Null

# Copy agents.
Copy-Item antigravity\agents\*.md $HOME\.gemini\config\agents\ -Force

# Copy skill.
Copy-Item antigravity\skill\multiagent-workflow\SKILL.md $HOME\.gemini\config\skills\multiagent-workflow\SKILL.md -Force
```

## Install — Bash (WSL, Git Bash, macOS, Linux)

From the canonical repo root:

```bash
mkdir -p ~/.gemini/config/agents ~/.gemini/config/skills/multiagent-workflow

cp antigravity/agents/*.md ~/.gemini/config/agents/
cp antigravity/skill/multiagent-workflow/SKILL.md ~/.gemini/config/skills/multiagent-workflow/SKILL.md
```

If you're on Git Bash on Windows and `~` resolves to a Cygwin-style home, prefer `$HOME` explicitly: `$HOME/.gemini/...`.

## Restart Your Session

Agent files and skills are loaded at session start. After copying, **start a new Antigravity/agy session** before invoking `/multiagent`.

## Verify The Install

From the canonical repo root:

```powershell
python scripts\multiagent_files.py validate-install --repo-root . --platform antigravity
```

```bash
python scripts/multiagent_files.py validate-install --repo-root . --platform antigravity
```

A clean install reports `complete: True` and an empty `missing` list. If anything is missing, the output tells you which path is absent — copy that file and re-run.

You can override the install root with `--antigravity-home <path>` if your config lives somewhere other than `~/.gemini/config`.

## First Run

In an Antigravity/agy session inside any project repo:

- Type `/multiagent <task>` or use trigger: `"run the multiagent workflow for this project."`
- The root session reads `~/.gemini/config/agents/pm.md`, adopts PM's role, asks for Scoped Autonomy, creates the run folder under `.multiagent/runs/`, and drafts the task packet.
- Once approved, PM spawns Developer and Reviewer subagents (automatically using `define_subagent` if they are not already globally defined, enabling a self-healing and zero-restart setup!).

## Troubleshooting

**Subagent types missing or not recognized.**
1. The user needs to install the agent files. Re-run the copy commands above.
2. Start a new session.
3. Confirm `~/.gemini/config/agents/pm.md` exists and contains valid YAML frontmatter.
4. Verify using `validate-install` command above.
