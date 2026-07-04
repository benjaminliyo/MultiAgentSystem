---
name: multiagent-workflow
description: Run the PM-led multi-agent team for software project work on Google Antigravity and agy. Use when the user says "run/start/use the multiagent workflow/system", invokes "/multiagent", asks to coordinate PM/Developer/Reviewer agents on a project, or asks why the multi-agent subagent types are not recognized.
---

# MultiAgent Workflow (Antigravity)

Launch and drive the user's PM-led multi-agent team on Google Antigravity.

## Core Model

PM is the main-thread agent. When this skill is invoked, the main Antigravity session **adopts PM's role** rather than spawning a separate `pm` subagent — read `~/.gemini/config/agents/pm.md` (or the canonical copy at `antigravity/agents/pm.md`) and follow it as your operating instructions for the rest of the run.

The role file is the single source of truth for run mechanics. Its "Routing And Run Management" section owns dynamic subagent registration, `invoke_subagent` spawn tiers and escalation respawns, workspace isolation, parallel spawning, workflow-state tracking, message persistence, the optional Researcher, closeout, and resume; its "Plan Mode As Client-Approval Gate" section owns approval gating. This skill covers launch, entry points, and troubleshooting only — do not look for routing detail here, and do not re-derive it.

PM owns product judgment AND mechanical routing. The spawnable `pm` agent file exists for the autonomous-loop scenario, not for the interactive workflow this skill handles.

## Launch Sequence

1. **Adopt PM's role.** Read `~/.gemini/config/agents/pm.md` (or the canonical copy). Follow it for the rest of the run.
2. **Scoped Autonomy preflight.** Ask the client once whether the run may use workspace/project read-write access for PM, Developer, and Reviewer, and whether commands inside the workspace may run without per-call confirmation. Also resolve the project's canonical environment (`.venv`, conda, uv/poetry), record it in `.multiagent/project-profile.md`, and ask the one package question (may workers install into that env without per-item approval?). Surface the platform constraint now: subagent tool calls run inside the root session's permission boundary, so fully autonomous subagents require the root session to have been launched with `--dangerously-skip-permissions` — if the client wants that and this session was not launched with it, tell them before the run starts so they can relaunch. Note the decisions; you'll save them in the run-summary.
3. **Create the run folder and activate PM mode.** Run:
   ```powershell
   python scripts/multiagent_files.py prepare-run --root <project-root> --task "<short task name>" --project-hooks antigravity
   ```
   Besides the run folder, this writes `.multiagent/active-run.json`, inserts a PM-mode marker block into the project's context files (GEMINI.md/AGENTS.md/CLAUDE.md) — that keeps the PM role alive through long sessions and interruptions — and renders `<project>/.agents/hooks.json` (PM reminder, subagent auto-logging on `invoke_subagent`, unclosed-run warning). Save the resulting run path; every `append-message` call needs it.
4. **Log the entry messages.** Append the client request summary and the Scoped Autonomy decision via `append-message --from-role client --to-role pm --type decision_record ...`.
5. **Start PM work.** Clarify the client request, draft the task packet, and present it for client approval — the gate. From approval onward, follow the role's "Routing And Run Management": register the subagents dynamically before the first spawn (matching installed permission modes) and run `set-state` on every workflow-state transition.

## Entry Points

- **`/multiagent <task>`** — the task is the initial client request. If no task is given, ask the client what they want to build, fix, or investigate.
- **`/multiagent off`** (or "stop the multiagent workflow") — deactivate PM mode: run `python scripts/multiagent_files.py close-run --root <project-root>` (terminal state set, marker blocks removed, `active-run.json` deleted). Confirm PM mode is off and continue as a normal session.
- **`/multiagent resume [run-name]`** — after an interruption, or when the client names a previous run, resume rather than restart. Follow the "Resume" step in the role's routing section: pick the target run, `activate-run` if PM mode is not active for it (works on closed runs; `set-state` to reopen one deliberately), reconstruct from `run-summary.md` and the tail of `messages.jsonl`, report the reconstructed state to the client, and continue without redoing completed work.

The PM-mode marker block in the project's context files means a fresh session already knows a run is active — offer to resume proactively when you see it.

## Troubleshooting

**Subagent types missing.** If `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, or `researcher` are not available:

1. Verify they are installed in `~/.gemini/config/agents/`.
2. Start a new session.
3. Run the validation command:
   ```powershell
   python scripts/install.py validate-install --platform antigravity
   ```
   If anything is missing, copy the agent and skill files to the configuration directory and retry.
