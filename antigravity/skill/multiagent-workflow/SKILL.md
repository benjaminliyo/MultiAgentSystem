---
name: multiagent-workflow
description: Run the PM-led multi-agent team for software project work on Google Antigravity and agy. Use when the user says "run/start/use the multiagent workflow/system", invokes "/multiagent", asks to coordinate PM/Developer/Reviewer agents on a project, or asks why the multi-agent subagent types are not recognized.
---

# MultiAgent Workflow (Antigravity)

Launch and drive the user's PM-led multi-agent team on Google Antigravity.

## Core Model

PM is the main-thread agent. When this skill is invoked, the main Antigravity session **adopts PM's role** rather than spawning a separate `pm` subagent — read `~/.gemini/config/agents/pm.md` (or the canonical copy at `antigravity/agents/pm.md`) and follow its "Mission", "Authority", "Workflow", and "Routing And Run Management" sections as your operating instructions for the rest of the run.

PM owns product judgment AND mechanical routing. The spawnable `pm` agent file exists for the autonomous-loop scenario, not for the interactive workflow this skill handles.

## Launch Sequence

1. **Adopt PM's role.** Read `~/.gemini/config/agents/pm.md` (or the canonical copy). Follow it for the rest of the run.
2. **Scoped Autonomy preflight.** Ask the client once whether the run may use workspace/project read-write access for PM, Developer, and Reviewer, and whether commands inside the workspace may run without per-call confirmation. Also resolve the project's canonical environment (`.venv`, conda, uv/poetry), record it in `.multiagent/project-profile.md`, and ask the one package question (may workers install into that env without per-item approval?). Note the decisions; you'll save them in the run-summary.
3. **Dynamic Subagent Registration (Self-Healing).**
   Check if the subagents `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, and (when needed) `researcher` are defined in the session. If not, or to ensure they are up to date with their instructions, read their definitions from `~/.gemini/config/agents/<role>.md` or `<workspace-root>/.agents/<role>.md` (or `antigravity/agents/<role>.md` in this repo), parse their YAML frontmatter and body, and call `define_subagent` to register them dynamically in the active session.
   **Crucial Permission Handling:** Match the permission mode used by your locally installed configuration copies (which defaults to `bypassPermissions` for subagents to support Scoped Autonomy). If you fall back to the repository canonical files or workspace copies that still set `permissionMode: plan` in frontmatter for these subagents, do not register them with `plan` mode; instead, register them as running with `bypassPermissions` (or match the installed copies' mode) so they do not prompt the user for approvals.
4. **Create the run folder and activate PM mode.** Run:
   ```powershell
   python scripts/multiagent_files.py prepare-run --root <project-root> --task "<short task name>" --project-hooks antigravity
   ```
   Besides the run folder, this writes `.multiagent/active-run.json`, inserts a PM-mode marker block into the project's context files (GEMINI.md/AGENTS.md/CLAUDE.md) — that keeps the PM role alive through long sessions and interruptions — and renders `<project>/.agents/hooks.json` (PM reminder, subagent auto-logging on `invoke_subagent`, unclosed-run warning). Save the resulting run path; every `append-message` call needs it.
5. **Log the entry messages.** Append the client request summary and the Scoped Autonomy decision via `append-message --from-role client --to-role pm --type decision_record ...`.
6. **Track state durably.** On every workflow-state transition, run `python scripts/multiagent_files.py set-state --run <run-dir> --state <state>`.
7. **Start PM work.** Clarify the client request, draft the task packet, and present it for approval.

## Plan-Mode/Approval Gate

Before delegating implementation, present the drafted task packet to the client. The client's approval of the plan is the gate. Only after the client approves do you spawn Developer.
Do not edit business code while drafting the packet — this prevents tool side effects and gives the client a single, explicit approval gate.

## Spawning Developer

Use the PM's `Suggested Developer Tier` as the first-pass choice:

- `routine` -> `invoke_subagent` with `TypeName: "developer"`.
- `strong` -> `invoke_subagent` with `TypeName: "developer-strong"`.

Pass the run directory in the spawn prompt so the worker knows where to self-log.
When the task touches multiple files, migration, or risky refactors, set `"Workspace": "share"` or `"Workspace": "branch"` in `invoke_subagent` to isolate the workspace.

If the default `developer` returns `ESCALATE_TO_STRONG_DEVELOPER`, save the escalation as a message with type `escalation_request`, then respawn the same task on `developer-strong` with the original packet plus the escalation reason and any prior work attached.

## Spawning Reviewer

Default to `invoke_subagent` with `TypeName: "reviewer"`. Use `reviewer-strong` directly for large/security-sensitive/data-loss-prone/concurrency-heavy/migration-related/dependency-risky/auth-related diffs, or after a failed review loop.

If the default reviewer returns `ESCALATE_TO_STRONG_REVIEWER`, respawn on `reviewer-strong` with the escalation reason attached.

## Spawning Researcher (Optional)

`invoke_subagent` with `TypeName: "researcher"` spawns an optional read-only exploration agent — no write access, no strong tier, no new workflow state. Spawn it when understanding the codebase is its own chunk of work: during `pm_discovery` on a large or unfamiliar project before drafting the task packet, or when Developer/Reviewer sends an `exploration_request`. Register it dynamically like the other roles if it is not defined in the session.

Pass a scoped assignment (exploration scope, concrete focus questions, depth hint) and the run directory — it self-logs an `exploration_report`. It cannot write to the project: fold durable findings into `.multiagent/project-profile.md` yourself and attach the report when spawning workers who need it.

## Parallel Spawning

When the next Developer slice is independent of the current Reviewer pass (non-overlapping files, no shared state), spawn both in the same turn by including multiple entries in the `Subagents` array of `invoke_subagent` — they run in parallel.

## Worker Self-Logging

Workers (Developer, Developer-Strong, Reviewer, Reviewer-Strong, Researcher) self-log their own inter-agent messages via `python scripts/multiagent_files.py append-message --from-role <role> ...`. You do not log on their behalf. Always pass the run directory when spawning them so they can write to it.

## Closeout

When Reviewer returns PASS:

1. Draft the client-facing closeout (concise: what was built, what was verified, residual risks).
2. Log the closeout message.
3. Mark the run complete in `run-summary.md` with final agent IDs.
4. Close the run: `python scripts/multiagent_files.py close-run --root <project-root>`. This sets the terminal state, removes the PM-mode marker blocks from the project's context files, and deletes `active-run.json`.

## Deactivation And Resume

- **Turn off** (`/multiagent off` or "stop the multiagent workflow"): run `close-run` as in Closeout step 4, confirm PM mode is off, and continue as a normal session.
- **Resume** (`/multiagent resume [run-name]` or after an interruption): pick the target run (named run folder, else `.multiagent/active-run.json`, else the newest `.multiagent/runs/` folder). If PM mode is not active for it, run `python scripts/multiagent_files.py activate-run --root <project-root> --run <run-dir>` to restore `active-run.json` and the marker blocks (works on closed runs; `set-state` to reopen one deliberately). Then read `run-summary.md` and the tail of `messages.jsonl`, re-adopt PM's role, report the reconstructed state to the client, and continue from the recorded state instead of restarting. The marker block in the project's context files tells a fresh session a run is active — offer to resume proactively.

## Troubleshooting

**Subagent types missing.** If `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, or `researcher` are not available:

1. Verify they are installed in `~/.gemini/config/agents/`.
2. Start a new session.
3. Run the validation command:
   ```powershell
   python scripts/install.py validate-install --platform antigravity
   ```
   If anything is missing, copy the agent and skill files to the configuration directory and retry.
