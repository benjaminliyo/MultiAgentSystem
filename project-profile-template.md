# Project Profile

Use this file to adapt the general multi-agent workflow to a specific project.

## Project

Name:

Purpose:

Primary users:

Current maturity:

## Important Docs

List the files agents should read first.

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`

## Source Of Truth

Describe which files or systems override others when they disagree.

Example:

- Current client-approved task packet overrides old planning notes.
- Project instructions override generic agent defaults.
- Tests and source code are the behavioral source of truth for existing features.

## Development Commands

Install:

```text
TODO
```

Test:

```text
TODO
```

Lint:

```text
TODO
```

Build:

```text
TODO
```

## Coding Conventions

- Follow existing local patterns before introducing new abstractions.
- Keep changes scoped to the approved task.
- Do not reformat unrelated files.
- Do not revert user changes unless explicitly requested.

## Approval Rules

Decisions requiring client or PM approval:

- product behavior changes
- new user-facing workflows
- dependency additions with meaningful maintenance cost
- hosted services or external accounts
- privacy, security, or data retention changes
- changes to acceptance criteria

## Agent Permission Profile

Default run mode:

- Scoped Autonomy / Custom:

PM:

- Read: project/workspace
- Write: planning, task, and process docs

Developer:

- Read: project/workspace
- Write: implementation files, tests, and technical docs inside workspace

Reviewer:

- Read: project/workspace
- Write: review reports and test artifacts; code edits only when explicitly assigned

Escalation required for:

- writes outside workspace
- secrets or denied files
- destructive cleanup outside approved scope
- network/package-install access
- deployments or hosted services
- external accounts
- global Codex or machine configuration

## Model And Usage Profile

Default preset:

- Balanced:

PM model policy:

- `gpt-5.5` with `xhigh` reasoning for product ambiguity, planning, and delegation.

Developer model policy:

- `gpt-5.5` with `high` reasoning for technical design and implementation.

Reviewer model policy:

- `gpt-5.4-mini` with `medium` reasoning by default.
- Escalate to `reviewer-strong` (`gpt-5.5` with `high` reasoning) for risky diffs, security/data-loss concerns, large changes, low-confidence reviews, or failed review loops.

Orchestrator model policy:

- `gpt-5.4-mini` with `low` reasoning for routing and artifact management.

## Communication Storage

Run artifacts path:

```text
.multiagent/runs/YYYY-MM-DD-short-task-name/
```

Message log path:

```text
.multiagent/runs/YYYY-MM-DD-short-task-name/messages/
```

## Review Focus

The Reviewer should pay special attention to:

- acceptance criteria coverage
- test coverage
- regression risk
- consistency with project conventions
- documentation updates when behavior changes

## Forbidden Or Risky Changes

- TODO

## Common Pitfalls

- TODO

## Project-Specific Agent Notes

PM:

- TODO

Developer:

- TODO

Reviewer:

- TODO
