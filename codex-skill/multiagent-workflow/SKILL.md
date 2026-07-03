---
name: multiagent-workflow
description: Run or troubleshoot the user's PM-led MultiAgentSystem workflow in Codex. Use when the user says "run/start/use the multiagent workflow/system", "start with the PM agent", asks why PM/developer/reviewer agents are not recognized, or wants Codex to coordinate PM, Developer, and Reviewer custom agents across project work.
---

# Multiagent Workflow

Use this skill to launch or troubleshoot the user's reusable PM-led multi-agent team.

## Core Rule

Do not treat "run the multiagent workflow" as an ordinary repo search task. The workflow is installed globally, not necessarily inside the target project.

First check the current subagent tool metadata. If custom roles are available, spawn the custom PM agent explicitly:

```text
agent_type: "pm"
```

Do not use `default`, `worker`, or a manually prompted generic subagent for the PM phase when `pm` is available.

## Expected Custom Agents

The installed agent names are:

- `pm`
- `developer`
- `developer-strong`
- `reviewer`
- `reviewer-strong`

Note: `multiagent-orchestrator` was deprecated on 2026-06-29 (see `CHANGELOG.md`). PM is the main-thread agent and absorbs mechanical routing. The deprecated TOML may still be present in older installs; that is harmless.

If the agents above are missing from the current subagent tool metadata, tell the user the likely cause is stale Codex session/tool metadata. Recommend restarting Codex or opening a new thread after installation. Do not pretend the workflow is unavailable just because the current project repo has no local multiagent files.

## Launch Flow

1. Spawn the `pm` custom agent. PM is the main-thread workflow agent and absorbs mechanical routing in addition to product judgment.
2. PM asks once for Scoped Autonomy for the run before spawning Developer: workspace/project read-write for PM, Developer, and Reviewer. This covers normal project edits, tests, docs, and `.multiagent/runs/...` artifacts. It does not cover writes outside the workspace, secrets, destructive cleanup outside the approved scope, package installs outside the approved envelope, deployments, external services, account changes, or global configuration changes. As part of the same preflight, PM resolves the project's canonical environment (`.venv`, conda, uv/poetry), records it in `.multiagent/project-profile.md`, and asks the one package question: may workers install missing packages into that resolved environment without per-item approval?
3. Use the balanced automatic model policy unless the user requests another preset: strongest/high-reasoning PM (absorbs routing), strong Developer, efficient Reviewer with escalation triggers.
4. PM creates a durable run folder before spawning Developer for the first time. Prefer the deterministic helper from the canonical MultiAgentSystem repo when it is available:
   ```powershell
   python <MULTIAGENT_REPO>/scripts/multiagent_files.py prepare-run --root <project-root> --task "<short task name>" --project-hooks codex
   ```
   Besides the run folder, this activates PM mode: it writes `.multiagent/active-run.json`, inserts a marker block into the project's context files (AGENTS.md/CLAUDE.md) so the PM role survives long sessions and interruptions, and renders the project-level `.codex/hooks.json` (Codex asks the user to trust it once; the hooks reinject the PM reminder each turn, mechanically log every subagent start/stop to the run folder, and warn about unclosed runs).
   The run folder includes:
   - `.multiagent/runs/YYYY-MM-DD-short-task-name/run-summary.md`
   - `.multiagent/runs/YYYY-MM-DD-short-task-name/messages.jsonl`
   - `.multiagent/runs/YYYY-MM-DD-short-task-name/messages/`
   - `.multiagent/runs/YYYY-MM-DD-short-task-name/transcripts/`
   - `.multiagent/team-registry.json`
5. Save the client request summary and Scoped Autonomy decision as the first message in `messages/` and index it in `messages.jsonl`. Prefer:
   ```powershell
   python <MULTIAGENT_REPO>/scripts/multiagent_files.py append-message --run <run-dir> --from-role client --to-role pm --type decision_record --title "Client request and scoped autonomy" --body "<summary>"
   ```
6. Spawn `pm` first for new requests.
7. Give PM the project path, user request, project rules, and any `.multiagent/project-profile.md` if present.
8. Ask PM to return one of:
   - `READY_WITH_TASK_PACKET`
   - `NEEDS_CLIENT_CLARIFICATION`
   - `BLOCKED`
9. Each agent self-logs its own messages to `messages/` and `messages.jsonl` before returning. PM additionally logs task assignments, escalation events, and closeouts.
10. If PM returns a ready task packet, spawn `developer` with that packet. Spawn `developer-strong` instead when the task is large or cross-module, security/auth/data-loss/migration/concurrency-related, in an unfamiliar domain, uses a novel algorithm, follows a prior failed implementation loop, or when PM marked `Suggested Developer Tier: strong` in the task packet.
11. If the default `developer` returns `ESCALATE_TO_STRONG_DEVELOPER`, stop that agent, save the escalation as a message with type `escalation_request` and sub-type `to_strong_developer`, then respawn the same task on `developer-strong` with the original task packet plus the escalation reason attached.
12. When Developer reports ready for review, spawn `reviewer` for routine reviews.
13. Spawn `reviewer-strong` instead when the diff is large, security-sensitive, data-loss-prone, concurrency-heavy, migration-related, dependency-risky, authentication/authorization-related, or when a previous efficient review failed or requested escalation.
14. Route Reviewer failures back to Developer and copy PM.
15. Route Reviewer PASS back to PM for client closeout.
16. Save raw inter-agent replies or transcript excerpts in `transcripts/` when the Codex runtime exposes them. This is best-effort; structured files in `messages/` plus the `messages.jsonl` index are the required record.
17. Record agent IDs and closure status in `run-summary.md` when available.
18. On every workflow-state transition, PM runs `python <MULTIAGENT_REPO>/scripts/multiagent_files.py set-state --run <run-dir> --state <state>` so `run-summary.md` and `active-run.json` stay current.
19. Close task-scoped Developer and Reviewer agents only after their final inter-agent output has been saved or the failed save has been recorded in `run-summary.md`.
20. At closeout (Reviewer PASS + client closeout delivered), PM runs `python <MULTIAGENT_REPO>/scripts/multiagent_files.py close-run --root <project-root>` to deactivate PM mode: terminal state set, marker blocks removed, `active-run.json` deleted.

Do not archive unrelated private user-agent conversation unless it is explicitly routed as workflow input or a client decision.

## Deactivation And Resume

- **Turn off**: when the user asks to stop the multiagent workflow, run `close-run` (step 20 above) and confirm PM mode is off.
- **Resume**: after an interruption — or when the user names a previous run — pick the target run (named `.multiagent/runs/<run-name>/`, else `.multiagent/active-run.json`, else the newest run folder). If PM mode is not active for it, run `python <MULTIAGENT_REPO>/scripts/multiagent_files.py activate-run --root <project-root> --run <run-dir>` to restore `active-run.json` and the marker blocks (works on closed runs; `set-state` to reopen one deliberately). Then read `run-summary.md` and the tail of `messages.jsonl`, re-adopt the PM flow, report the reconstructed state to the user, and continue from the recorded state instead of restarting. The marker block in the project's context files tells a fresh session a run is active — offer to resume proactively.

## PM Prompt Shape

When spawning PM, include:

```text
You are the PM agent for the PM-led MultiAgentSystem workflow.

Project: <absolute project path>
Client request: <user request>

Start the PM phase only. Read project instructions and profile if available. Clarify the product goal, identify open questions, and produce a PM kickoff report or task packet.

Self-log your inter-agent output to `.multiagent/runs/.../messages/` via `python scripts/multiagent_files.py append-message` before returning. Make the report structured and suitable for durable handoff.

Return exactly:
STATUS: READY_WITH_TASK_PACKET | NEEDS_CLIENT_CLARIFICATION | BLOCKED
REPORT:
...
```

## Troubleshooting

If Codex does not recognize the workflow:

- Verify `~/.codex/agents/pm.toml` exists.
- Verify the current subagent tool lists `pm`, `developer`, `developer-strong`, `reviewer`, and `reviewer-strong`. (`multiagent-orchestrator` was deprecated 2026-06-29; it may still appear in old installs.)
- If files exist but roles are absent, restart Codex or open a new thread.
- If roles exist but the model still uses a generic agent, make the prompt more explicit: "Spawn the custom `pm` agent using `agent_type: pm`."
- If roles exist but spawning `pm` fails with `spawn_agent could not resolve the child model for service tier validation`, do not fall back to pretending a generic agent is PM. Test whether a built-in role such as `default` can spawn. If built-in spawning works, report this as a custom-agent model/service-tier validation failure and recommend restarting Codex or opening a fresh thread with a supported Codex model selected.

## References

Read `references/paths.md` only when you need exact installed paths or doc locations.
