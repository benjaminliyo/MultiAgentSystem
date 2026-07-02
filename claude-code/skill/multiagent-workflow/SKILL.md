---
name: multiagent-workflow
description: Run the PM-led multi-agent team for software project work on Claude Code. Use when the user says "run/start/use the multiagent workflow/system", invokes "/multiagent", asks to coordinate PM/Developer/Reviewer agents on a project, or asks why the multi-agent subagent types are not recognized.
---

# MultiAgent Workflow (Claude Code)

Launch and drive the user's PM-led multi-agent team on Claude Code.

## Core Model

PM is the main-thread agent. When this skill is invoked, the main Claude Code session **adopts PM's role** rather than spawning a separate `pm` subagent — read `~/.claude/agents/pm.md` (or the canonical copy at `claude-code/agents/pm.md`) and follow its "Mission", "Authority", "Workflow", and "Routing And Run Management" sections as your operating instructions for the rest of the run.

PM owns product judgment AND mechanical routing. The earlier dedicated `multiagent-orchestrator` agent was removed on 2026-06-29 (see `CHANGELOG.md`); do not look for it. The spawnable `pm` agent file exists for the autonomous-loop scenario in `FUTURE-PLANS.md`, not for the interactive workflow this skill handles.

## Launch Sequence

1. **Adopt PM's role.** Read `~/.claude/agents/pm.md` (or the canonical copy). Follow it for the rest of the run.
2. **Scoped Autonomy preflight.** Ask the client once whether the run may use workspace/project read-write access for PM, Developer, and Reviewer, and whether commands inside the workspace may run without per-call confirmation. Note the decision; you'll save it in the run-summary.
3. **Create the run folder.**
   ```bash
   python scripts/multiagent_files.py prepare-run \
     --root <project-root> \
     --task "<short task name>"
   ```
   Save the resulting run path; every `append-message` call needs it.
4. **Log the entry messages.** Append the client request summary and the Scoped Autonomy decision via `append-message --from-role client --to-role pm --type decision_record ...`.
5. **Mirror the state machine.** Use `TaskCreate` to create one task per workflow state: `pm_discovery`, `awaiting_client_approval`, `developer_implementation`, `reviewer_checking`, `developer_fixing`, `pm_closeout`. Update `in_progress` / `completed` as routing moves through states. Tier escalations and failed reviews are self-loops.
6. **Start PM work.** Clarify the client request, draft the task packet, and use `EnterPlanMode` to present it for approval.

## Plan-Mode Contract

`EnterPlanMode` is PM's client-approval gate. The plan body is the task packet. `ExitPlanMode` is the approval signal — only after the client exits plan mode do you spawn Developer.

Do not skip plan mode. Do not edit business code while drafting the packet — plan mode prevents tool side effects and gives the client a single, explicit approval gate.

## Spawning Developer

Use the PM's `Suggested Developer Tier` as the first-pass choice:

- `routine` → `Agent(subagent_type: "developer", ...)`.
- `strong` → `Agent(subagent_type: "developer-strong", ...)`.

Pass the run directory in the spawn prompt so the worker knows where to self-log. Use `isolation: "worktree"` for changes touching multiple files or any migration.

If the default `developer` returns `ESCALATE_TO_STRONG_DEVELOPER`, save the escalation as a message with type `escalation_request`, then respawn the same task on `developer-strong` with the original packet plus the escalation reason and any prior work attached.

For slow Developer work (long builds, full test suites), spawn with `run_in_background: true` and continue routing.

## Spawning Reviewer

Default to `Agent(subagent_type: "reviewer", ...)`. Use `Agent(subagent_type: "reviewer-strong", ...)` directly for large/security-sensitive/data-loss-prone/concurrency-heavy/migration-related/dependency-risky/auth-related diffs, or after a failed review loop.

If the default reviewer returns `ESCALATE_TO_STRONG_REVIEWER`, respawn on `reviewer-strong` with the escalation reason attached.

## Parallel Spawning

When the next Developer slice is independent of the current Reviewer pass (non-overlapping files, no shared state), spawn both in the same assistant turn with two `Agent` calls — they run in parallel. The same applies to independent Developer slices that touch non-overlapping files (use separate worktrees).

Do not parallelize when the next slice depends on the current Reviewer's verdict, or on file changes still being staged.

## Worker Self-Logging

Workers (Developer, Developer-Strong, Reviewer, Reviewer-Strong) self-log their own inter-agent messages via `python scripts/multiagent_files.py append-message --from-role <role> ...`. You do not log on their behalf. Always pass the run directory when spawning them so they can write to it.

If a worker reports a save failure, record it in `run-summary.md` and decide whether to retry the spawn or surface the issue to the client.

## Closeout

When Reviewer returns PASS:

1. Draft the client-facing closeout (concise: what was built, what was verified, residual risks).
2. Log the closeout message.
3. Mark the run complete in `run-summary.md` with final agent IDs.
4. Mark the final `TaskCreate` task `completed`.
5. Close idle worker agents if the runtime allows it.
6. If a context-maintenance skill is installed, consider running it when durable project decisions surfaced during the run.

## Memory For Cross-Session Client Context

Persistent client preferences — quality bar, communication style, tech-stack defaults, do-not-do rules — belong in the Claude Code auto-memory system at `~/.claude/projects/<slug>/memory/`, not in the per-run folder under `.multiagent/runs/...`. Use memory for state that should survive across runs and sessions; use the run folder for run-specific artifacts.

## Slash Command

`/multiagent <task>` is a shortcut that loads this skill with the task as initial input. See `claude-code/commands/multiagent.md` (Phase 5). The two paths are equivalent — the slash command is a UX convenience.

## Troubleshooting

**Subagent types missing.** If `pm`, `developer`, `developer-strong`, `reviewer`, or `reviewer-strong` are not available as `subagent_type` options:

1. The user needs to install the agent files. From the canonical repo:
   ```bash
   cp claude-code/agents/*.md ~/.claude/agents/
   ```
   (Or `Copy-Item claude-code\agents\*.md $HOME\.claude\agents\` on PowerShell.)
2. Restart the Claude Code session (or open a new one) after copying — agent files are loaded at session start.
3. Confirm `~/.claude/agents/pm.md` exists and starts with valid YAML frontmatter.

**`multiagent_files.py` rejects a role.** If `append-message` returns "Unknown from-role" or "Unknown to-role", check `VALID_MESSAGE_ROLES` in `scripts/multiagent_files.py`. The active roles are: `client`, `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`. `orchestrator` is retained for forward-compat with autonomous loops (see `FUTURE-PLANS.md`).

**`multiagent-orchestrator` referenced somewhere.** It was deprecated 2026-06-29. A reference in any current doc or agent file is a bug — fix or flag it. Historical design records live in `docs/private/` (gitignored).

**Subagent depth limit hit while PM is itself a child.** This is the autonomous-loop scenario. The interactive workflow assumes PM = main thread. If PM has been spawned as a child for some reason and cannot spawn grandchildren, fall back to having the spawning parent route on PM's behalf, or surface it as a workflow limitation per `FUTURE-PLANS.md`.

## Done Standard

The workflow is done only when:

- the task packet was client-approved via `ExitPlanMode`,
- implementation satisfies every acceptance criterion,
- relevant verification ran or risk is documented,
- Reviewer returned `PASS`,
- PM has closed out to the client,
- inter-agent messages were saved (or save failures were recorded in `run-summary.md`),
- unresolved risks are documented.
