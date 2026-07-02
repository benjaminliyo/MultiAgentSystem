# Team Workflow

This document defines the standard operating model for the reusable multi-agent team.

## Organization Model

The system mimics a small software team.

```text
Client / CEO / Boss
  -> PM Agent, team lead
      -> Developer Agent
      -> Reviewer Agent
```

The human is the Client, CEO, or Boss. The PM Agent is the team lead and primary interface to the human. Developer and Reviewer report to the PM.

Runtime note: Codex subagents are usually direct children of the root session. Because default subagent nesting depth is limited, the root session may perform the mechanical routing on behalf of the PM. The process authority still belongs to the PM.

## Role Authority

### Client / CEO / Boss

Owns:

- goals and priorities
- final product decisions
- acceptance of PM-level plans
- approval for scope, cost, privacy, hosting, and quality-bar changes

### PM Agent

Owns:

- understanding the client request
- asking clarifying questions
- preventing misunderstanding and product drift
- product-level design
- client task packets
- project plans and decision records
- assigning work to Developer and Reviewer
- checking agent progress
- deciding whether work is ready to present to the client

PM may edit planning and process documents. PM should not directly implement code except when explicitly asked.

### Developer Agent

Owns:

- technical design
- implementation
- tests that belong with implementation
- bug fixes
- project technical docs, such as README, changelog, setup docs, and developer notes
- implementation reports to PM and Reviewer

Developer must not silently change product behavior or acceptance criteria.

### Reviewer Agent

Owns:

- test planning
- verification
- quality review
- acceptance-criteria coverage
- regression and edge-case review
- reporting pass/fail status to PM

Reviewer behaves like a test engineer and code reviewer. Reviewer should return actionable failures to Developer and report final pass status to PM.

## Standard Lifecycle

1. Client gives PM a request.
2. PM (as the main-thread agent) performs the Scoped Autonomy preflight for the run.
3. PM clarifies the request until product-level ambiguity is resolved.
4. PM writes a client task packet and gets approval when needed.
5. PM assigns an implementation task to Developer.
6. Developer writes a technical plan, implements, tests locally, and sends a ready-for-review message.
7. PM sends the review assignment to Reviewer.
8. Reviewer tests and reviews against the task packet.
9. If review fails, Reviewer sends required fixes to Developer and notifies PM.
10. Developer fixes and resubmits.
11. If review passes, Reviewer reports PASS to PM.
12. PM checks the final result, updates project docs or asks Developer to update them, and reports to the client.
13. Before wrap-up, agents consider whether a context-maintenance skill (if installed) should run.

## Scoped Autonomy Mode

At the start of a multi-agent run, PM (as the main-thread agent) should ask once for the normal project-working permission envelope instead of asking repeatedly mid-conversation.

Default run approval covers workspace/project read-write access, creation of `.multiagent/runs/...` artifacts, edits to implementation files, tests, and project docs, and routine local commands that stay inside the active sandbox.

Default run approval does not cover broad machine access, writes outside the workspace, global Codex configuration changes, secrets, destructive cleanup outside the approved workspace scope, package installs requiring network, deployments, hosted services, or external account changes. Those still require explicit escalation.

## Progress Management

PM should request status when:

- an agent has not reported progress after a meaningful delay,
- an agent reports a blocker,
- a task is near a decision point,
- the client asks for status,
- a handoff artifact is missing or incomplete.

Developer and Reviewer should send concise progress updates for long tasks. They should not wait until the end to reveal blockers.

## Inter-Agent History

PM (as the main-thread agent) creates the run folder at workflow start; each worker self-logs its own messages into it. At the start of each run, create:

```text
.multiagent/runs/YYYY-MM-DD-short-task-name/
  run-summary.md
  messages.jsonl
  messages/
  transcripts/
```

Prefer creating this structure with the deterministic helper:

```powershell
python scripts/multiagent_files.py prepare-run --root <project-root> --task "<short task name>"
```

Save every inter-agent message in `messages/`: PM task assignments and closeouts, Developer progress and ready-for-review messages, Reviewer pass/fail results, fix requests, blockers, skill requests, and ContextUpdate observations. Each agent is responsible for persisting its own messages before returning. Use `messages.jsonl` as the machine-readable index for those Markdown artifacts. The helper can append indexed messages:

```powershell
python scripts/multiagent_files.py append-message --run <run-dir> --from-role pm --to-role developer --type task_assignment --title "<title>" --body "<body>"
```

Record agent IDs and closure status in `run-summary.md` when available.

The `transcripts/` folder is best-effort. Use it only for raw inter-agent replies or transcript excerpts that Codex exposes. The workflow does not require archiving unrelated private user-agent conversation.

Do not close task-scoped Developer or Reviewer agents until their final inter-agent output has been saved, or until `run-summary.md` records why it could not be saved.

## Context Maintenance

When a context-maintenance skill is installed (one that keeps CLAUDE.md, AGENTS.md, project plans, or editor rules in sync with decisions made during work), agents should invoke it whenever its trigger conditions apply.

If the workflow surfaces observations worth improving in such a skill, agents may report:

- false positives,
- false negatives,
- confusing approval flow,
- missing watched files,
- unexpected edits proposed,
- performance issues,
- unclear reports,
- runtime-specific behavior differences.

Agents must still follow the skill's consent model: no context file edits are applied until proposed diffs are visible and explicitly approved.

## Skill Discovery Requirement

All agents must have access to the skill-installer or skill-discovery workflow.

When an agent lacks a capability, it should:

1. Search or list available skills.
2. Decide whether a new skill is actually needed.
3. Report the recommendation to PM if installing the skill changes the system.
4. Install only when allowed by the environment and the user or PM has approved the install path.
5. Update the skill catalog after installation.

## Permission Model

Recommended default:

- PM: read the whole project; write planning, task, and process docs.
- Developer: read the whole project; write implementation files, tests, and technical docs inside the workspace.
- Reviewer: read the whole project; write review reports and test artifacts; code edits only when explicitly asked.
- PM/root session: enough permission to route messages, create artifacts, spawn agents, and copy approved agent configs.

Avoid broad unrestricted access as a default. Use the Scoped Autonomy preflight for normal project work, and escalate only when a task needs permissions beyond that approved run envelope.

## Model And Usage Policy

Use automatic role-based model selection so the user does not choose models for every handoff.

Recommended balanced default:

- PM: strongest available model with higher reasoning for ambiguity, product planning, task packets, and delegation.
- Developer: strong model with medium or high reasoning depending on technical complexity, because Developer owns technical design and implementation.
- Reviewer: efficient model by default, with automatic escalation to a stronger model for risky diffs, security/data-loss concerns, large changes, or failed review loops.

Current balanced custom-agent defaults:

- PM: `gpt-5.5` with `xhigh` reasoning.
- Developer: `gpt-5.5` with `high` reasoning.
- Strong Developer: `gpt-5.5` with `xhigh` reasoning.
- Reviewer: `gpt-5.4-mini` with `medium` reasoning.
- Strong Reviewer: `gpt-5.5` with `high` reasoning.

PM runs on the strongest model because it combines product judgment with mechanical routing. There is no separate orchestrator model in the interactive workflow as of 2026-06-29 (see `CHANGELOG.md`).

Use a max-quality preset only when the task is high-stakes enough to justify premium usage across PM, Developer, and Reviewer.

## Session Strategy

Recommended default:

- Keep one main-thread PM session open for the active project or feature.
- Create Developer and Reviewer agents task-by-task.
- Close Developer and Reviewer agents when their assigned task is complete.
- Keep PM context durable in artifacts, not only in chat.
- Keep inter-agent communication durable in `.multiagent/runs/.../messages/`, not only in Codex thread notifications.

Use long-lived Developer or Reviewer sessions only when continuity is valuable, such as a large refactor, ongoing testing campaign, or production incident. Otherwise, task-scoped agents reduce stale context, token use, and coordination risk.

Do not rely on child agents spawning their own children unless the Codex subagent depth is intentionally configured for that. Prefer root-session routing for reliability.
