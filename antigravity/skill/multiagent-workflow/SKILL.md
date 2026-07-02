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
2. **Scoped Autonomy preflight.** Ask the client once whether the run may use workspace/project read-write access for PM, Developer, and Reviewer, and whether commands inside the workspace may run without per-call confirmation. Note the decision; you'll save it in the run-summary.
3. **Dynamic Subagent Registration (Self-Healing).**
   Check if the subagents `developer`, `developer-strong`, `reviewer`, and `reviewer-strong` are defined in the session. If not, or to ensure they are up to date with their instructions, read their definitions from `~/.gemini/config/agents/<role>.md` or `<workspace-root>/.agents/<role>.md` (or `antigravity/agents/<role>.md` in this repo), parse their YAML frontmatter and body, and call `define_subagent` to register them dynamically in the active session.
4. **Create the run folder.** Run:
   ```powershell
   python scripts/multiagent_files.py prepare-run --root <project-root> --task "<short task name>"
   ```
   Save the resulting run path; every `append-message` call needs it.
5. **Log the entry messages.** Append the client request summary and the Scoped Autonomy decision via `append-message --from-role client --to-role pm --type decision_record ...`.
6. **Start PM work.** Clarify the client request, draft the task packet, and present it for approval.

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

## Parallel Spawning

When the next Developer slice is independent of the current Reviewer pass (non-overlapping files, no shared state), spawn both in the same turn by including multiple entries in the `Subagents` array of `invoke_subagent` — they run in parallel.

## Worker Self-Logging

Workers (Developer, Developer-Strong, Reviewer, Reviewer-Strong) self-log their own inter-agent messages via `python scripts/multiagent_files.py append-message --from-role <role> ...`. You do not log on their behalf. Always pass the run directory when spawning them so they can write to it.

## Closeout

When Reviewer returns PASS:

1. Draft the client-facing closeout (concise: what was built, what was verified, residual risks).
2. Log the closeout message.
3. Mark the run complete in `run-summary.md` with final agent IDs.
4. Set the top-level `state:` field in `run-summary.md` to `done`.
5. If a context-maintenance skill is installed, consider running it when durable project decisions surfaced during the run.

## Troubleshooting

**Subagent types missing.** If `pm`, `developer`, `developer-strong`, `reviewer`, or `reviewer-strong` are not available:

1. Verify they are installed in `~/.gemini/config/agents/`.
2. Start a new session.
3. Run the validation command:
   ```powershell
   python scripts/multiagent_files.py validate-install --platform antigravity
   ```
   If anything is missing, copy the agent and skill files to the configuration directory and retry.
