---
name: multiagent-workflow
description: Run the PM-led multi-agent team for software project work on Claude Code. Use when the user says "run/start/use the multiagent workflow/system", invokes "/multiagent", asks to coordinate PM/Developer/Reviewer agents on a project, or asks why the multi-agent subagent types are not recognized.
---

# MultiAgent Workflow (Claude Code)

Launch and drive the user's PM-led multi-agent team on Claude Code.

## Core Model

PM is the main-thread agent. When this skill is invoked, the main Claude Code session **adopts PM's role** rather than spawning a separate `pm` subagent — read `~/.claude/agents/pm.md` (or the canonical copy at `claude-code/agents/pm.md`) and follow it as your operating instructions for the rest of the run.

The role file is the single source of truth for run mechanics. Its "Routing And Run Management" section owns spawn tiers and escalation respawns, worktree isolation, parallel and background spawning, workflow-state tracking, message persistence, the optional Researcher, closeout, and resume; its "Plan Mode As Client-Approval Gate" section owns approval gating. This skill covers launch, entry points, and troubleshooting only — do not look for routing detail here, and do not re-derive it.

PM owns product judgment AND mechanical routing. The earlier dedicated `multiagent-orchestrator` agent was removed on 2026-06-29 (see `CHANGELOG.md`); do not look for it. The spawnable `pm` agent file exists for the autonomous-loop scenario in `FUTURE-PLANS.md`, not for the interactive workflow this skill handles.

## Launch Sequence

1. **Adopt PM's role.** Read `~/.claude/agents/pm.md` (or the canonical copy). Follow it for the rest of the run.
2. **Scoped Autonomy preflight.** Ask the client once whether the run may use workspace/project read-write access for PM, Developer, and Reviewer, and whether commands inside the workspace may run without per-call confirmation. Also resolve the project's canonical environment, record it in `.multiagent/project-profile.md`, and ask the one package question (may workers install into that env without per-item approval?). Note the decisions; you'll save them in the run-summary.
3. **Create the run folder and activate PM mode.**
   ```bash
   python scripts/multiagent_files.py prepare-run \
     --root <project-root> \
     --task "<short task name>"
   ```
   Besides the run folder, this writes `.multiagent/active-run.json` and inserts a PM-mode marker block into the project's context files — that is what keeps the PM role alive through long sessions, compaction, and interruptions (the `user-prompt-pm-mode` hook reads it every turn). Save the resulting run path; every `append-message` call needs it.
4. **Log the entry messages.** Append the client request summary and the Scoped Autonomy decision via `append-message --from-role client --to-role pm --type decision_record ...`.
5. **Mirror the state machine.** Create one `TaskCreate` task per workflow state and run `set-state` on every transition, as the role's routing section describes.
6. **Start PM work.** Clarify the client request, draft the task packet, and present it via `EnterPlanMode` — the client-approval gate. From `ExitPlanMode` onward, follow the role's "Routing And Run Management".

## Entry Points

- **`/multiagent <task>`** — loads this skill with the task as the initial client request (see `claude-code/commands/multiagent.md`). The two paths are equivalent — the slash command is a UX convenience.
- **`/multiagent off`** — deactivate PM mode: run `python scripts/multiagent_files.py close-run --root <project-root>`. This sets the run's terminal state, removes the PM-mode marker blocks from the project's context files, and deletes `.multiagent/active-run.json` — the per-turn PM reminder stops immediately. Confirm the deactivation and continue as a normal session.
- **`/multiagent resume [run-name]`** — after an interruption, or when the client names a previous run, resume rather than restart. Follow the "Resume" step in the role's routing section: pick the target run, `activate-run` if PM mode is not active for it, reconstruct from `run-summary.md` and the tail of `messages.jsonl`, report the reconstructed state to the client, and continue without redoing work the message log shows as completed.

The PM-mode marker block in the project's context files means a fresh session already knows a run is active — offer to resume proactively when you see it.

## Troubleshooting

**Subagent types missing.** If `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, or `researcher` are not available as `subagent_type` options:

1. The user needs to install the agent files. From the canonical repo:
   ```bash
   cp claude-code/agents/*.md ~/.claude/agents/
   ```
   (Or `Copy-Item claude-code\agents\*.md $HOME\.claude\agents\` on PowerShell.)
2. Restart the Claude Code session (or open a new one) after copying — agent files are loaded at session start.
3. Confirm `~/.claude/agents/pm.md` exists and starts with valid YAML frontmatter.

**`multiagent_files.py` rejects a role.** If `append-message` returns "Unknown from-role" or "Unknown to-role", check `VALID_MESSAGE_ROLES` in `scripts/multiagent_files.py`. The active roles are: `client`, `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, `researcher`. `orchestrator` is retained for forward-compat with autonomous loops (see `FUTURE-PLANS.md`).

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
