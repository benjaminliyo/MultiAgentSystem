# Task Packet: <short name>

## Status

Draft / Client-approved

## Goal

What outcome should this task produce?

## Background

Why does this matter? What context should the Developer and Reviewer know?

## Required Behavior

List the user-visible or externally observable behavior that must exist.

- 

## Non-Goals

List what is intentionally out of scope.

- 

## Constraints

List constraints that affect the solution.

- 

## Acceptance Criteria

Each item should be specific enough for the Reviewer to verify.

- 

## Verification Plan

How the Reviewer verifies each acceptance criterion **by executing it** — concrete commands, scripts, or user-journey steps. Criteria that describe user-visible behavior must map to an executable check (shipped tests, an E2E smoke script, or explicit steps through the running app). If the check does not exist yet, list building it here as a required deliverable of this task.

- 

## Questions Resolved

Record client decisions that shaped the task.

- 

## Approved Assumptions

Record assumptions the PM is allowed to hand off with.

- 

## Technical Decisions Delegated To Developer

List implementation choices the Developer owns.

- 

## Suggested Skills

Three-tier hint to help the assigned worker draw on the right skills. See `docs/skills-framework.md` for the model.

### Tier 0 (install requests)

Skills the client must approve to install before implementation starts. Leave empty if none anticipated. Each entry counts against the per-run install budget (default 3; see `docs/skills-framework.md`).

- 

### Tier 1 (baseline skills the assigned role should draw on)

Baseline skills PM expects the assigned Developer or Reviewer to draw on if installed. Reference by category (e.g., "a plan-writing skill"), not by concrete artifact name. Workers self-check at task start; missing baselines surface as a `skill_need`.

- 

### Tier 2 (niche needs, if any)

Anticipated mid-work niche needs. Usually empty — tier 2 is discovered during work. Populate only if PM already knows a niche capability will be required.

- 

## Suggested Developer Tier

One of `routine`, `strong`, or `unsure`. PM uses this as its first-pass tier choice when spawning Developer. The Developer may self-escalate via `ESCALATE_TO_STRONG_DEVELOPER`.

- tier: 
- rationale: 

Pick `strong` when the task likely matches any of these triggers: large diff scope, security or auth or data-loss or migration or concurrency work, unfamiliar domain or novel algorithm, prior failed implementation loop, or low PM confidence in implementation risk. Pick `routine` otherwise. Pick `unsure` only when the triggers cannot be assessed from PM-level information.

## PM Notes For Reviewer

Highlight risk areas or expectations the Reviewer should pay attention to.

- 

