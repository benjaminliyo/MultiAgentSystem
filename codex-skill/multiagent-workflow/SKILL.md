---
name: multiagent-workflow
description: Run or troubleshoot the user's PM-led MultiAgentSystem workflow in Codex. Use when the user says "run/start/use the multiagent workflow/system", "start with/adopt the PM agent", asks why PM/developer/reviewer agents are not recognized, or wants Codex to coordinate PM, Developer, and Reviewer custom agents across project work.
---

# Multiagent Workflow

Use this skill to launch or troubleshoot the user's reusable PM-led multi-agent team.

## Core Rule

Do not treat "run the multiagent workflow" as an ordinary repo search task. The workflow is installed globally, not necessarily inside the target project.

PM is the main-thread agent. When this skill is invoked, the main Codex session adopts PM's role; do not spawn a separate `pm` subagent for the interactive workflow. Read the PM role from `~/.codex/agents/pm.toml` (its `developer_instructions`) and follow it for the rest of the run — it is the single source of truth for run mechanics: tiered Developer/Reviewer spawning and escalation respawns, the optional Researcher, worktree isolation, parallel spawning, workflow-state tracking, message persistence, closeout, and resume. This skill covers launch, entry points, and troubleshooting only. The spawnable `pm` TOML also serves the future autonomous-loop scenario in `FUTURE-PLANS.md`; it is not spawned for the interactive workflow.

The main Codex session owns product judgment and mechanical routing. Spawn `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, and optional `researcher` as workers only after PM-mode setup and client approval. Do not archive unrelated private user-agent conversation unless it is explicitly routed as workflow input or a client decision.

## Expected Custom Agent Files

The installed custom-agent files are:

- `pm`
- `developer`
- `developer-strong`
- `reviewer`
- `reviewer-strong`
- `researcher` (optional, read-only exploration)

Note: `multiagent-orchestrator` was deprecated on 2026-06-29 (see `CHANGELOG.md`). PM is the main-thread agent and absorbs mechanical routing. The deprecated TOML may still be present in older installs; that is harmless.

If the worker roles (`developer`, `developer-strong`, `reviewer`, `reviewer-strong`, or optional `researcher`) are missing from the current subagent tool metadata, tell the user the likely cause is stale Codex session/tool metadata. Recommend restarting Codex or opening a new thread after installation. Do not pretend the workflow is unavailable just because the current project repo has no local multiagent files.

## Launch Flow

1. Adopt PM's role in the main Codex session: read `~/.codex/agents/pm.toml` and follow its Mission, Authority, Workflow, and Routing and run management instructions for the rest of the run.
2. PM asks once for Scoped Autonomy for the run before spawning Developer: workspace/project read-write for PM, Developer, and Reviewer. This covers normal project edits, tests, docs, and `.multiagent/runs/...` artifacts. It does not cover writes outside the workspace, secrets, destructive cleanup outside the approved scope, package installs outside the approved envelope, deployments, external services, account changes, or global configuration changes. As part of the same preflight, PM resolves the project's canonical environment (`.venv`, conda, uv/poetry), records it in `.multiagent/project-profile.md`, and asks the one package question: may workers install missing packages into that resolved environment without per-item approval?
3. Use the balanced automatic model policy unless the user requests another preset: strongest/high-reasoning PM (absorbs routing), strong Developer, efficient Reviewer with escalation triggers.
4. PM creates a durable run folder before spawning Developer for the first time. Prefer the deterministic helper from the canonical MultiAgentSystem repo when it is available:
   ```powershell
   python <MULTIAGENT_REPO>/scripts/multiagent_files.py prepare-run --root <project-root> --task "<short task name>" --project-hooks codex
   ```
   This creates `.multiagent/runs/YYYY-MM-DD-short-task-name/` (`run-summary.md`, `messages.jsonl`, `messages/`, `transcripts/`) and activates PM mode: it writes `.multiagent/active-run.json`, inserts a marker block into the project's context files (AGENTS.md/CLAUDE.md) so the PM role survives long sessions and interruptions, and renders the project-level `.codex/hooks.json` (Codex asks the user to trust it once; the hooks reinject the PM reminder each turn, mechanically log every subagent start/stop to the run folder, and warn about unclosed runs).
5. Save the client request summary and Scoped Autonomy decision as the first message in `messages/` and index it in `messages.jsonl`. Prefer:
   ```powershell
   python <MULTIAGENT_REPO>/scripts/multiagent_files.py append-message --run <run-dir> --from-role client --to-role pm --type decision_record --title "Client request and scoped autonomy" --body "<summary>"
   ```
6. Start PM discovery in the root session with the project path, user request, project rules, and any `.multiagent/project-profile.md` if present. Hold the PM Adoption Shape below; discovery returns `READY_WITH_TASK_PACKET`, `NEEDS_CLIENT_CLARIFICATION`, or `BLOCKED`.
7. From the client-approved task packet onward, follow the PM role's Routing and run management section: tiered spawning and `ESCALATE_TO_STRONG_*` respawns, optional read-only Researcher, `set-state` on every workflow-state transition, worker self-logging to `messages/` and `messages.jsonl` (raw transcripts best-effort in `transcripts/`), agent IDs and closure status in `run-summary.md`, and `close-run` at closeout. Close task-scoped workers only after their final inter-agent output has been saved or the failed save has been recorded in `run-summary.md`.

## Deactivation And Resume

- **Turn off**: when the user asks to stop the multiagent workflow, run `python <MULTIAGENT_REPO>/scripts/multiagent_files.py close-run --root <project-root>` (terminal state set, marker blocks removed, `active-run.json` deleted) and confirm PM mode is off.
- **Resume**: after an interruption — or when the user names a previous run — follow the Resume step in the PM role's Routing and run management section: pick the target run (named `.multiagent/runs/<run-name>/`, else `.multiagent/active-run.json`, else the newest run folder), run `activate-run` if PM mode is not active for it (works on closed runs; `set-state` to reopen one deliberately), reconstruct from `run-summary.md` and the tail of `messages.jsonl`, report the reconstructed state to the user, and continue instead of restarting. The marker block in the project's context files tells a fresh session a run is active — offer to resume proactively.

## PM Adoption Shape

When adopting PM mode in the root session, hold this shape:

```text
You are the PM agent for the PM-led MultiAgentSystem workflow in the main Codex session.

Project: <absolute project path>
Client request: <user request>

Start the PM phase only. Read project instructions and profile if available. Clarify the product goal, identify open questions, and produce a PM kickoff report or task packet.

Self-log your PM outputs to `.multiagent/runs/.../messages/` via `python scripts/multiagent_files.py append-message` before routing them. Make the report structured and suitable for durable handoff.

Return exactly:
STATUS: READY_WITH_TASK_PACKET | NEEDS_CLIENT_CLARIFICATION | BLOCKED
REPORT:
...
```

## Troubleshooting

If Codex does not recognize the workflow:

- Verify `~/.codex/agents/pm.toml` exists.
- Verify the current subagent tool lists `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, and `researcher`. (`multiagent-orchestrator` was deprecated 2026-06-29; it may still appear in old installs.)
- If files exist but roles are absent, restart Codex or open a new thread.
- If roles exist but the model still uses a generic agent or tries to launch PM as a child, make the prompt more explicit: "Use the multiagent-workflow skill. The main Codex session adopts PM's role; do not spawn a separate PM subagent. Spawn only Developer/Reviewer/Researcher workers."
- If worker spawning fails with `spawn_agent could not resolve the child model for service tier validation`, test whether a built-in role such as `default` can spawn. If built-in spawning works, report this as a custom-agent model/service-tier validation failure and recommend restarting Codex or opening a fresh thread with a supported Codex model selected.

## References

Read `references/paths.md` only when you need exact installed paths or doc locations.
