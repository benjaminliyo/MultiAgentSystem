# Orchestration Guide

Use this guide to run the PM-led three-agent system.

The process model is business-like: the human is the Client/CEO, PM is the team lead and main-thread agent, and Developer, Reviewer, and the optional read-only Researcher report to PM. PM owns both product judgment AND mechanical routing — see `CHANGELOG.md` (2026-06-29) for why the earlier dedicated `multiagent-orchestrator` role was removed and `FUTURE-PLANS.md` for the autonomous-loop scenario where it will be reintroduced.

## States

```text
intake
permission_preflight
pm_discovery
awaiting_client_approval
developer_planning
developer_implementation
reviewer_checking
developer_fixing
pm_closeout
blocked
done
```

## Routing Rules

### intake -> permission_preflight

Start here when the client has an idea, request, bug, or project goal.

Inputs:

- client request
- project profile, if available
- relevant project docs, if known

Output:

- one run-level Scoped Autonomy decision

PM (as the main-thread agent) should ask once whether the current run may use workspace/project read-write access for PM, Developer, and Reviewer. This approval is scoped to the active project workspace and normal local workflow artifacts.

Escalate separately for writes outside the workspace, broad machine access, secrets, destructive cleanup outside the approved scope, network/package-install access, deployments, external services, account changes, or global configuration changes.

### permission_preflight -> pm_discovery

PM (as the main-thread agent) creates `.multiagent/runs/YYYY-MM-DD-short-task-name/` with `messages/`, `messages.jsonl`, optional `transcripts/`, and `run-summary.md` before spawning Developer for the first time. Prefer the deterministic helper (`<MULTIAGENT_REPO>` is your local checkout of this repo):

```powershell
python <MULTIAGENT_REPO>\scripts\multiagent_files.py prepare-run --root <project-root> --task "<short task name>"
```

The client request summary becomes the first saved message.

Record the preflight decision and any denied or deferred permissions in `run-summary.md`.

PM owns this phase. PM is normally the main-thread agent; if the runtime forces PM to be a child subagent that cannot spawn other agents, the main session should route messages on PM's behalf (this is the autonomous-loop scenario tracked in `FUTURE-PLANS.md`).

### pm_discovery -> awaiting_client_approval

During `pm_discovery` on a large or unfamiliar project, PM may spawn the optional read-only `researcher` agent with a scoped exploration assignment (scope, focus questions, run directory). The Researcher returns an `exploration_report`; PM folds durable findings into `.multiagent/project-profile.md` and the task packet. Exploration introduces no new workflow state — it runs inside the current state, and because the Researcher is read-only it may also run mid-run in parallel with Developer or Reviewer work when they send an `exploration_request`.

Move here when the PM believes product-level ambiguity is resolved.

Required PM output:

- task packet
- product-level decisions
- assumptions
- non-goals
- acceptance criteria
- technical decisions delegated to Developer

### awaiting_client_approval -> developer_planning

Move here only after the client approves the task packet.

If the client changes scope, return to `pm_discovery`.

### developer_planning -> developer_implementation

The Developer reads the approved task packet and project profile, inspects the codebase, and chooses a technical approach.

The Developer may proceed without client approval when choices are purely technical and remain inside the task packet.

The Developer must escalate if a technical choice affects:

- product behavior
- user experience
- privacy or security expectations
- cost
- dependency footprint
- deployment or hosting model
- long-term maintenance burden
- acceptance criteria

### developer_planning -> developer_planning (tier escalation)

If the default `developer` returns `ESCALATE_TO_STRONG_DEVELOPER` after reading the task packet but before implementing, PM must:

1. Stop the default `developer` agent.
2. Save the escalation message under `messages/` with type `escalation_request` and sub-type `to_strong_developer`.
3. Respawn the same task on `developer-strong`, passing the original task packet plus the escalation body and any prior work as input.
4. Resume `developer_planning` under the new agent.

The PM's `Suggested Developer Tier` field is its own first-pass judgment: PM pre-selects `developer-strong` on first spawn when the packet was marked `strong`, and pre-selects `developer` when it was marked `routine` or `unsure`. Either may self-correct via escalation.

Symmetric to the reviewer/reviewer-strong escalation: tier escalation is mechanical — the trigger (PM's hint or the Developer's self-escalation) carries the judgment; PM only performs the respawn.

### developer_implementation -> reviewer_checking

Move here when the Developer has implemented the task and produced an implementation report.

Required Developer output:

- technical plan or summary
- files changed
- commands run
- tests added or updated
- verification results
- requirement coverage
- unresolved risks

Developer must also send a `ready_for_review` message to PM and Reviewer.

### reviewer_checking -> developer_fixing

Move here when the Reviewer returns `FAIL` due to implementation defects.

The Reviewer must provide concrete required fixes to Developer and copy PM.

### reviewer_checking -> pm_discovery

Move here when the Reviewer finds the task packet itself is incomplete, contradictory, or no longer matches the implementation reality.

Examples:

- acceptance criteria conflict
- product behavior is underspecified
- implementation requires a product tradeoff
- scope has changed

### reviewer_checking -> pm_closeout

Move here only when the Reviewer returns `PASS`.

PM reviews the final implementation report, review report, and outstanding risks.

### pm_closeout -> done

Move here when PM has produced a client-facing closeout and any needed documentation updates are complete. Closeout ends with `close-run` (`python scripts/multiagent_files.py close-run --root <project-root>`), which sets the terminal state, removes the PM-mode marker blocks from the project's context files, and deletes `active-run.json`.

## Artifact Naming

For a single task, keep artifacts together:

```text
.multiagent\
  runs\
    YYYY-MM-DD-short-task-name\
      run-summary.md
      messages.jsonl
      messages\
      transcripts\
      task-packet.md
      technical-plan.md
      implementation-report.md
      review-report.md
```

Each agent is responsible for persisting its own inter-agent messages before returning. PM additionally records its own task packets, escalation events, and closeouts. The `multiagent_files.py` helper appends one message per call and updates `messages.jsonl`:

```powershell
python scripts/multiagent_files.py append-message --run <run-dir> --from-role pm --to-role developer --type task_assignment --title "<title>" --body "<body>"
```

Save raw inter-agent replies or transcript excerpts in `transcripts/` when the runtime exposes them, but treat that as best-effort. PM should not close a task-scoped Developer or Reviewer until that worker has confirmed its final inter-agent output was saved (or the failed save has been recorded in `run-summary.md`).

## Loop Discipline

Keep feedback routed to the right owner:

- Product ambiguity goes to PM/client.
- Technical defects go to Developer.
- Quality and verification gaps go to Developer.
- Scope changes go to PM/client.

The Reviewer should not silently redesign the task. The Developer should not silently change product behavior. The PM should not over-specify implementation details unless they affect product constraints.

## Session Strategy

Recommended default:

- Keep one main-thread PM session open for the active project or feature.
- Spawn Developer and Reviewer as task-scoped agents from the PM session.
- Close Developer and Reviewer when their assigned task is done.
- Keep durable state in `.multiagent/runs/...` artifacts, not only in chat history.

Why: Codex subagents are direct children by default, and default nesting depth prevents deeper recursive delegation. PM as the main thread sidesteps this. If a runtime forces PM to be a child agent that cannot spawn workers, see `FUTURE-PLANS.md` for the autonomous-loop scenario where a dedicated orchestrator would be reintroduced.

Use long-lived Developer or Reviewer sessions only when continuity is worth the cost, such as a large refactor, ongoing QA campaign, or production incident.

## Standard Messages

Use `COMMUNICATION-PROTOCOL.md` and `templates/messages/*.md` for tracked communication.

Required handoff messages:

- PM to Developer: `task_assignment`
- Developer to PM: `progress_update`
- Developer to PM and Reviewer: `ready_for_review`
- Reviewer to PM and Developer: `review_result`
- Reviewer to Developer, copied to PM: `fix_request`
- Developer or Reviewer to PM: `exploration_request`
- Researcher to PM: `exploration_report`
- Any agent to PM: `blocker`, `skill_need`, `package_need`

Use the efficient `reviewer` agent for routine reviews. Use `reviewer-strong` when a review has large-diff, security, data-loss, concurrency, migration, dependency, authentication/authorization, failed-loop, or low-confidence escalation risk.

Use the default `developer` for routine implementation. Use `developer-strong` when the task has large-diff, security, data-loss, concurrency, migration, unfamiliar-domain, novel-algorithm, prior-failed-loop, or low-confidence triggers. PM owns the first-pass tier choice via `Suggested Developer Tier`; the Developer may self-escalate via `ESCALATE_TO_STRONG_DEVELOPER`; PM performs the mechanical respawn.

Required persistence:

- PM creates the run folder at workflow start.
- Each agent (PM and workers) saves its own inter-agent messages in `messages/` and `messages.jsonl` before returning.
- PM records available agent IDs and closure status in `run-summary.md`.
- Any agent may save raw inter-agent transcript excerpts in `transcripts/` when available; this is best-effort.

## Skill And Package Discovery

All agents should have a skill-search-and-install capability available so they can search for missing capabilities when work requires it. Installation decisions should be reported to PM unless the human has already approved them. See `docs/skills-framework.md` for the tier model, the role-skill map, and the package-need flow.

## Permission Guidance

Recommended default:

- PM (main thread): read the full project, write planning and process docs, create run-folder artifacts, route messages, spawn agents, and apply approved agent configuration updates.
- Developer: read the full project, write implementation, tests, and technical docs inside the workspace.
- Reviewer: read the full project, write review reports and test artifacts; code edits only when explicitly assigned.
- Researcher (optional): read the full project; write nothing except its own run-folder messages via the logging helper.

Avoid unrestricted access as the normal baseline. Prefer one Scoped Autonomy approval for workspace/project read-write at run start, then escalate only when a task requires broader filesystem, network, external-app, deployment, secret, or global-configuration permissions.

## Model And Usage Guidance

Use a balanced automatic model policy by default: `gpt-5.5`/`xhigh` PM, `gpt-5.5`/`high` Developer, `gpt-5.5`/`xhigh` `developer-strong`, `gpt-5.4-mini`/`medium` Reviewer with escalation triggers, `gpt-5.5`/`high` `reviewer-strong`, and `gpt-5.4-mini`/`medium` for the optional `researcher` (breadth-and-summarize work; no strong tier). PM runs on the strongest model because it now combines product judgment and mechanical routing. Escalate Developer and Reviewer model strength automatically when risk, ambiguity, or failed loops justify the usage.
