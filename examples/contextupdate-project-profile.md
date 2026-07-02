# Project Profile: ContextUpdate

## Project

Name: ContextUpdate

Purpose: A Codex/agent skill and plugin that detects when reusable-context files have drifted from recent conversation decisions, then proposes explicit edits for user approval.

Primary users: Developers using agent frontends that load reusable instructions, such as Codex, Claude Code, Cursor, Gemini CLI, Kimi, and related tools.

Current maturity: Active plugin/skill project with strict behavior and pressure-scenario tests.

## Important Docs

Agents should read these first:

- `CLAUDE.md`
- `AGENTS.md`
- `README.md`
- `skills/context-update/SKILL.md`
- `skills/context-update/references/detection-workflow.md`
- `skills/context-update/references/discovery-rules.md`
- `skills/context-update/references/report-format.md`

## Source Of Truth

- `CLAUDE.md` is the canonical contributor instruction file for this repo.
- `AGENTS.md` is a shim that points agents to `CLAUDE.md`.
- The context-update skill body and reference files define runtime behavior.
- Tests and pressure-scenario transcripts are the strongest evidence for whether a skill change works.

## Development Commands

Test:

```text
tests/run-skill-tests.sh
```

## Coding Conventions

- Keep the skill body concise.
- Put heavy workflow details in `skills/context-update/references/`.
- Keep `SKILL.md` frontmatter to `name` and `description` only.
- The `description` should say when to use the skill, not summarize the workflow.
- Do not add broad new features without a paired pressure scenario.

## Approval Rules

Decisions requiring client or PM approval:

- changing the consent model,
- adding automatic writes,
- changing watched-file discovery behavior,
- adding a new runtime/front-end target,
- changing pressure-scenario expectations,
- changing plugin layout invariants.

## Review Focus

The Reviewer should pay special attention to:

- no proposed context edit is applied without explicit approval,
- consolidated report appears before any write,
- watched/frozen files follow the documented workflow,
- skill descriptions do not become workflow summaries,
- new rationalizations discovered in tests are recorded.

## Forbidden Or Risky Changes

- Do not auto-apply context updates.
- Do not write files outside the project root by default.
- Do not append chronicle-style updates to instruction files.
- Do not touch frozen files without explicit override flow.
- Do not change hook behavior on one platform without checking cross-platform expectations.

## Common Pitfalls

- Treating "obvious" context drift as permission to edit.
- Making `SKILL.md` too long instead of moving detail into references.
- Forgetting to re-read files immediately before approved writes.
- Updating `AGENTS.md` as if it were independent from `CLAUDE.md`.

## Project-Specific Agent Notes

PM:

- Define behavior in terms of consent, discovery, report shape, and user trust.
- Ask before approving workflow changes that reduce explicit user control.

Developer:

- Follow existing plugin layout.
- Keep edits tightly scoped.
- Run focused pressure scenarios when changing skill behavior.

Reviewer:

- Review like a consent and safety system, not just a documentation update.
- Confirm the implementation cannot silently bypass the report-and-approve flow.

