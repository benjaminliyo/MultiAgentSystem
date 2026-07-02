# Communication Protocol

This document standardizes messages between the PM, Developer (and Developer-Strong), Reviewer (and Reviewer-Strong), and Client.

The `orchestrator` role still appears as a valid sender/recipient in the envelope below for forward compatibility with the autonomous-loop scenario described in `FUTURE-PLANS.md`. In the current interactive workflow PM (as the main-thread agent) absorbs the orchestrator's mechanical responsibilities — see `CHANGELOG.md` (2026-06-29).

## Message Envelope

Every tracked message should use this structure:

```yaml
message_id: MSG-YYYYMMDD-NNN
task_id: TASK-YYYYMMDD-short-name
from: pm | developer | developer-strong | reviewer | reviewer-strong | orchestrator | client
to: pm | developer | developer-strong | reviewer | reviewer-strong | orchestrator | client
type: task_assignment | progress_update | ready_for_review | review_result | fix_request | blocker | decision_record | skill_need | context_update_observation | closeout | escalation_request
status: draft | sent | acknowledged | blocked | done
priority: low | normal | high | urgent
created_at: YYYY-MM-DD HH:MM TZ
requires_response: true | false
```

The body should be short, concrete, and action-oriented.

## Core Message Types

### Client Request

From Client to PM.

Purpose: state the desired outcome at a high level.

### PM Clarification Question

From PM to Client.

Purpose: resolve product ambiguity before handoff.

### Decision Record

From PM to team, or PM to Client.

Purpose: record an approved product or process decision.

### Task Assignment

From PM to Developer or Reviewer.

Purpose: assign concrete work with goals, inputs, acceptance criteria, and expected output.

### Progress Update

From Developer or Reviewer to PM.

Purpose: report state, completed work, next step, risks, and blockers.

### Ready For Review

From Developer to PM and Reviewer.

Purpose: signal that implementation is complete enough for testing/review.

### Review Result

From Reviewer to PM and Developer.

Purpose: report PASS or FAIL with evidence.

### Fix Request

From Reviewer to Developer, copied to PM.

Purpose: list required fixes after failed review.

### Blocker / Escalation

From any agent to PM.

Purpose: ask for help when product, technical, permission, tool, or external-state issues block progress.

### Skill Need Request

From any agent to PM.

Purpose: request installation or use of a new skill.

### ContextUpdate Observation

From any agent to PM.

Purpose: report useful or problematic behavior from the user's ContextUpdate skill.

### Closeout

From PM to Client.

Purpose: summarize what was done, verification, remaining risks, and next recommended step.

### Escalation Request

From Developer or Reviewer to PM (in the interactive workflow; to Orchestrator in autonomous-loop installs).

Purpose: request that PM respawn the current task on a stronger-tier agent. The sender stops work and PM picks up the routing.

Sub-types:

- `to_strong_developer`: sent by the default `developer` when the task matches strong-tier triggers (large or cross-module scope, security/auth/data-loss/migration/concurrency work, unfamiliar domain or novel algorithm, prior failed implementation loop, low self-assessed confidence). Body must include a reason and any prior work attempted.
- `to_strong_reviewer`: sent by the default `reviewer` when the review needs the stronger reviewer (large diff, security-sensitive, data-loss-prone, concurrency-heavy, migration-related, dependency-risky, authentication/authorization-related, previous failed efficient review, or low confidence). Body must include a reason, risk triggers, and minimum context for the strong reviewer.

PM respawns the task on the strong-tier agent with the original task packet plus the escalation body attached.

## Routing Rules

- Product ambiguity goes to PM and possibly Client.
- Implementation defects go to Developer.
- Test failures go to Developer, copied to PM.
- Review PASS goes to PM.
- Permission or tool blockers go to PM.
- Skill installation requests go to PM.
- ContextUpdate observations go to PM and should be captured in the run folder.
- Tier escalation requests go to PM. PM owns respawning the task on the stronger-tier agent.

## Storage

For every multi-agent workflow run, PM (as the main-thread agent) must create a run folder before spawning Developer for the first time:

```text
.multiagent/runs/YYYY-MM-DD-short-task-name/
  run-summary.md
  messages.jsonl
  messages/
  transcripts/
```

Prefer creating the run folder with:

```powershell
python D:\Projects\MultiAgentSystem\scripts\multiagent_files.py prepare-run --root <project-root> --task "<short task name>"
```

The `messages` folder is mandatory. Store every routed inter-agent message there before routing it onward or closing the sending agent. `messages.jsonl` is the machine-readable index that points to those Markdown artifacts. Use filenames like:

```text
001-client-request.md
002-pm-task-assignment.md
003-developer-progress.md
004-ready-for-review.md
005-review-result.md
```

Prefer appending routed messages with:

```powershell
python D:\Projects\MultiAgentSystem\scripts\multiagent_files.py append-message --run <run-dir> --from-role pm --to-role developer --type task_assignment --title "<title>" --body "<body>"
```

The `transcripts` folder is optional best-effort storage for raw inter-agent replies or transcript excerpts when Codex exposes them. Do not depend on closed subagents remaining readable. Do not archive unrelated private user-agent conversation unless it is explicitly routed as workflow input or a client decision.

If a message cannot be saved, the sending agent must surface the failure to PM, and PM must add an entry to `run-summary.md` explaining what was missing and why.

Artifacts should remain readable without opening agent chat history.
