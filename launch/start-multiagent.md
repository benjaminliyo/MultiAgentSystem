# Start Multiagent Workflow

Paste this into a Codex project thread after installing the custom agents:

```text
Run the multiagent workflow for this project.

The main Codex session adopts PM's role. Do not spawn a separate `pm` subagent for the interactive workflow. PM is the main-thread agent and owns mechanical routing in addition to product judgment (see CHANGELOG.md 2026-06-29 for why the earlier `multiagent-orchestrator` role was removed).

Before spawning Developer, ask once for Scoped Autonomy for this run: workspace/project read-write for PM, Developer, and Reviewer. Treat that as approval for normal project edits, tests, docs, and `.multiagent/runs/...` artifacts. As part of the same preflight, resolve the project's canonical environment (.venv, conda, uv/poetry), record it in `.multiagent/project-profile.md`, and ask whether workers may install missing packages into that resolved environment without per-item approval (the package envelope). Still ask separately for writes outside the workspace, secrets, destructive cleanup outside the approved scope, package installs outside the envelope, deployments, external services, account changes, or global configuration changes.

Use the balanced automatic model policy unless I say otherwise: `gpt-5.5`/`xhigh` PM, `gpt-5.5`/`high` default Developer, `gpt-5.5`/`xhigh` `developer-strong` for large or cross-module/security/auth/data-loss/migration/concurrency/unfamiliar-domain/novel-algorithm/prior-failed-loop tasks or when the default `developer` returns `ESCALATE_TO_STRONG_DEVELOPER`, `gpt-5.4-mini`/`medium` Reviewer, and `gpt-5.5`/`high` `reviewer-strong` for risky reviews or failed review loops. The developer-strong escalation pattern mirrors the reviewer-strong escalation pattern.

PM creates a durable run folder before spawning Developer for the first time (prefer `python <MULTIAGENT_REPO>/scripts/multiagent_files.py prepare-run --root <project-root> --task "<name>" --project-hooks codex`, which also activates PM mode: `active-run.json`, context-file marker blocks, and project-level hooks):

`.multiagent/runs/YYYY-MM-DD-short-task-name/`

Inside it, keep `run-summary.md`, `messages/`, and `transcripts/`. Each agent self-logs its own inter-agent messages to `messages/` before returning. PM records agent IDs and closure status in `run-summary.md` when available, and runs `set-state` on every workflow transition. Raw inter-agent replies or transcript excerpts go in `transcripts/` when the runtime exposes them. Do not archive unrelated private user-agent conversation unless it is explicitly routed as workflow input or a client decision. At closeout (or when I say to stop the workflow), run `close-run` to deactivate PM mode.

Use this routing model:
- PM clarifies product intent and produces a client-approved task packet.
- PM acts as team lead in the main Codex session, assigns work, tracks progress, and owns client closeout.
- Developer owns technical design, implementation, tests, technical docs, and implementation report.
- Reviewer acts like a test engineer/code reviewer and checks the diff, tests, task packet, and project profile.
- Use `reviewer-strong` instead of `reviewer` when the review is large, security-sensitive, data-loss-prone, concurrency-heavy, migration-related, dependency-risky, authentication/authorization-related, or when a previous efficient review failed or requested escalation.
- Optionally spawn the read-only `researcher` when understanding a large or unfamiliar codebase is its own chunk of work (PM discovery, or a worker's `exploration_request`). It returns an `exploration_report`; PM folds durable findings into the project profile.
- Route Reviewer FAIL findings back to Developer when they are implementation defects.
- Route product ambiguity, scope changes, or acceptance-criteria conflicts back to PM/client.
- Let all agents use skill-installer to search for missing skills when needed.
- PM does not close Developer or Reviewer until that worker confirms its final inter-agent output was saved (or the failed save is recorded in `run-summary.md`).

Use `.multiagent/project-profile.md` if this project has one. If it does not, infer a temporary profile from project docs and ask me before treating it as durable.

Do not ask me to copy messages between agents. Pass structured summaries and artifacts between agents directly when the Codex runtime allows it. Close completed agents when no longer needed.

My request:
<describe the task here>
```
