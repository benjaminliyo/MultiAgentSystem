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
| `antigravity/agents/*.md` (6 files)              | `~/.gemini/config/agents/`                             |
| `antigravity/skill/multiagent-workflow/SKILL.md` | `~/.gemini/config/skills/multiagent-workflow/SKILL.md` |

The agents are: `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, and the optional read-only `researcher`. PM is the main-thread agent and absorbs mechanical routing.

If a gitignored `local/overlays/roles/<role>.md` exists, the installer appends its content to the installed agent body — personal additions without touching canonical files.

`scripts/multiagent_files.py` is not copied — the workflow invokes it from this repo path. `git pull` updates it.

## Optional: Hooks

Antigravity supports hooks via a workspace-level `.agents/hooks.json` (or plugin-level `~/.gemini/antigravity-cli/plugins/<plugin>/hooks.json`). Supported events: `PreInvocation`, `PostInvocation`, `PreToolUse`, `PostToolUse`, `Stop` — there is no SubagentStart/SubagentStop, so the subagent auto-logger hooks `PreToolUse`/`PostToolUse` with `matcher: "invoke_subagent"` instead, which fires at the same spawn/finish boundary.

The easy path: let `prepare-run` render it into the target project —

```powershell
python scripts\multiagent_files.py prepare-run --root <project-root> --task "<name>" --project-hooks antigravity
```

This writes `<project>/.agents/hooks.json` from the `antigravity/hooks.json` template with the `{{...}}` placeholders resolved to this machine's absolute commands. Manual alternative: copy the template yourself and substitute:

```text
{{USER_PROMPT_JSON_CMD}} -> python "<repo>/claude-code/hooks/user-prompt-pm-mode.py"
{{SUBAGENT_LOG_CMD}}     -> python "<repo>/claude-code/hooks/subagent-log.py"
{{STOP_CMD}}             -> powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>/claude-code/hooks/stop-warn-unclosed-run.ps1"
```

(Use `bash "<repo>/claude-code/hooks/stop-warn-unclosed-run.sh"` on macOS/Linux.) Check active hooks with the `/hooks` slash command.

**PreInvocation JSON contract.** Antigravity injects PreInvocation hook output into the agent's context only when stdout is a single flat JSON object — the `additionalContext` field is appended to the LLM context, and any plain text on stdout fails the framework's JSON parser and can crash the turn. That is why the PM reminder here uses `user-prompt-pm-mode.py` (always prints exactly one JSON object, `{}` when no run is active) instead of the plain-text `.ps1`/`.sh` variants used on Claude Code and Codex. If you ever swap in your own command, keep debug output on stderr.

Note: the Stop entry runs the plain-text `stop-warn-unclosed-run` script; whether Antigravity applies the same JSON contract to Stop hook output is unconfirmed. If unclosed-run warnings misbehave, remove the Stop entry from `.agents/hooks.json`.

All hooks are silent outside active multiagent runs, and unknown payload shapes degrade to transcript-only records.

## Permission Configuration & Scoped Autonomy

The MultiAgentSystem workflow relies on **Scoped Autonomy**: you grant permission to the PM agent *once* at the beginning of the run. To prevent repetitive confirmation prompts for every script, tool call, or file edit executed by the spawned subagents (`developer`, `reviewer`, etc.):

1. **PM Agent** retains `permissionMode: plan` so it presents the task packet to you for plan-level approval.
2. **Subagents** are automatically switched to `permissionMode: bypassPermissions` when copied by the installer, so they run their tasks without prompting.

### Safety Defaults in Repository
The canonical files in the `antigravity/agents/` folder of this repository are checked in with `permissionMode: plan` as a security baseline. This prevents cloned repository files from running unconfirmed commands on your machine. The installer script `install.py` transforms the copies it deploys.

### Customizing Deployed Permissions
If you prefer to keep prompt-level confirmation for subagents, you can override this behavior during installation by specifying the `--antigravity-subagent-permission-mode` flag:

```bash
# Deploys subagents with "plan" mode (prompts on every command)
python scripts/install.py install --platform antigravity --antigravity-subagent-permission-mode plan
```

### Upgrade Note
If you have an existing installation, you must re-run the installer and start a fresh Antigravity/`agy` session to pick up the permission changes:

```bash
python scripts/install.py install --platform antigravity
```

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
