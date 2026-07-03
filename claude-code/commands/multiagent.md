---
description: Launch the PM-led multi-agent workflow. Pass the initial client request as arguments (e.g. /multiagent fix the login redirect bug). The main session adopts PM's role; Developer and Reviewer are spawned as subagents.
---

Invoke the `multiagent-workflow` skill. That skill is the canonical operating doc for this workflow — read its body and follow it for the rest of the run.

## Core Contract

- The main Claude Code session **adopts PM's role** by reading `~/.claude/agents/pm.md` (or the canonical copy at `claude-code/agents/pm.md`). Do not spawn a separate `pm` subagent for this interactive run.
- PM owns product judgment AND mechanical routing (run-folder creation, escalation respawning, parallel-spawn, state tracking). The earlier `multiagent-orchestrator` role was removed on 2026-06-29 — see `CHANGELOG.md`.
- Developer and Reviewer are spawned as subagents via the `Agent` tool with `subagent_type: "developer" | "developer-strong" | "reviewer" | "reviewer-strong"`. The optional read-only `researcher` may be spawned for codebase exploration (large/unfamiliar projects, or a worker's `exploration_request`).
- Workers self-log their own inter-agent messages via `scripts/multiagent_files.py append-message`.

## Special Arguments: off / resume

Check the first word of `$ARGUMENTS` before treating it as a task:

- **`/multiagent off`** — deactivate PM mode. Run `python scripts/multiagent_files.py close-run --root <project-root>` (use the canonical repo path for the script). This sets the run's terminal state, removes the PM-mode marker blocks from the project's context files, and deletes `.multiagent/active-run.json`. Confirm to the client that PM mode is off, then behave as a normal session.
- **`/multiagent resume [run-name]`** — resume a run. Without a name, target `.multiagent/active-run.json` (or, if missing, the newest folder under `.multiagent/runs/`); with a name, target `.multiagent/runs/<run-name>/`. If PM mode is not currently active for that run, re-activate it: `python scripts/multiagent_files.py activate-run --root <project-root> --run <run-dir>` (restores `active-run.json` + marker blocks; works on closed runs too — `set-state` to a working state when deliberately reopening one). Then read `run-summary.md` and the tail of `messages.jsonl`, re-adopt PM's role, report the reconstructed state to the client (what was done, what state the run is in, what comes next), and continue from the recorded state. Do not restart work that the message log shows as already completed.

## Initial Client Request

Everything else the user typed after `/multiagent` on the invoking line is the initial client request:

$ARGUMENTS

If `$ARGUMENTS` is empty or just whitespace, do not assume a task. Ask the client what they want to build, fix, or investigate before doing any work.

## Launch Steps (Summary)

The `multiagent-workflow` skill body covers these in detail. Quick reference:

1. Read `~/.claude/agents/pm.md` and adopt PM's role.
2. Run the Scoped Autonomy preflight (one approval for workspace read-write), including the environment/package preflight: resolve the project env, record it in the project profile, and ask the one package-envelope question.
3. Create the run folder and activate PM mode: `python scripts/multiagent_files.py prepare-run --root <project-root> --task "<short task name>"` (writes `active-run.json` + context-file marker blocks; the `user-prompt-pm-mode` hook keeps the role fresh each turn).
4. Log the client request and the Scoped Autonomy decision as the first messages.
5. Create `TaskCreate` tasks for the workflow state machine; run `set-state` on every transition.
6. Clarify the client request, draft the task packet, present via `EnterPlanMode`.
7. After `ExitPlanMode`, spawn Developer at the tier PM selected (`developer` or `developer-strong`). Use `isolation: "worktree"` for multi-file or migration work.
8. On `ESCALATE_TO_STRONG_DEVELOPER`, respawn on `developer-strong` with the escalation reason attached.
9. On ready-for-review, spawn Reviewer (`reviewer` or `reviewer-strong` based on risk). On `ESCALATE_TO_STRONG_REVIEWER`, respawn on `reviewer-strong`.
10. On Reviewer PASS, draft the closeout, close idle agents, then deactivate PM mode: `python scripts/multiagent_files.py close-run --root <project-root>`.

## Parallel And Background Spawning

- When the next Developer slice is independent of the current Reviewer pass, spawn both in the same assistant turn with two `Agent` calls.
- For slow Developer work (long builds, full test suites), spawn with `run_in_background: true`.

## Memory For Cross-Session Client Context

Persistent client preferences belong in `~/.claude/projects/<slug>/memory/`, not `.multiagent/runs/...`. Use memory for things that survive across runs.

## If The Skill Isn't Installed

If `~/.claude/skills/multiagent-workflow/SKILL.md` does not exist, the user hasn't completed the install. Tell them to copy from the canonical repo:

```bash
cp -r claude-code/skill/multiagent-workflow ~/.claude/skills/multiagent-workflow
cp claude-code/agents/*.md ~/.claude/agents/
```

PowerShell equivalent:

```powershell
Copy-Item -Recurse claude-code\skill\multiagent-workflow $HOME\.claude\skills\multiagent-workflow
Copy-Item claude-code\agents\*.md $HOME\.claude\agents\
```

Then restart the Claude Code session so the new agents and skill are loaded.

## If Subagent Types Are Missing

If `subagent_type: "pm" | "developer" | ... | "reviewer-strong"` are not recognized, the agent files weren't copied or the session needs restart. See the install commands above.

`multiagent-orchestrator` is deliberately not in the active set — its absence is correct.
