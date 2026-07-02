# Skills Framework

Canonical reference for how the multi-agent workflow decides when to install or invoke a skill, who has authority over that decision, and how it degrades when the underlying platform can't help.

The framework is **efficiency + quality**. Without the right niche skill, an agent may iterate many times on a task (e.g., doc formatting, table generation, migration planning) and still not meet the client's expectations. The framework's job is to short-circuit that failure mode by making the "we need a different tool for this" moment visible, cheap to act on, and bounded by a per-run install budget.

## Overview

Three tiers, each with a different actor and a different trigger:

| Tier | What it covers | Trigger | Actor | Approval path |
|------|----------------|---------|-------|---------------|
| 0    | Install requests known at PM planning time | PM shapes the task packet | PM ↔ Client | Client-approved as part of the task packet |
| 1    | Per-role baseline skills the assigned worker should draw on | Task starts; worker self-checks its available skills against the packet's tier-1 list | Worker (Developer / Reviewer, either tier) | Worker sends `skill_need` if a critical baseline is missing; PM decides |
| 2    | Niche needs that surface during work | Worker realizes mid-task that no installed skill matches the current subproblem | Worker | Worker uses a skill-search-and-install capability to find a candidate, then sends `skill_need` to PM, who forwards to Client if the install budget is not spent |

Tier 0 lives in the task packet. Tier 1 is a self-check the worker performs against the packet. Tier 2 is a mid-work self-check the worker performs against reality.

## Tier 0 — Install Request Flow (PM ↔ Client)

PM authors the task packet. The packet's `## Suggested Skills` section (added by this framework — see `templates/task-packet.md`) has three subsections. `### Tier 0 (install requests)` is where PM records any skill that must be installed *before* implementation starts.

Common tier-0 triggers:

- The task is in a domain PM knows will need a specific skill (e.g., "we're touching a Notion export — install a Notion skill first").
- A prior run failed because the assigned worker didn't have the right tool.
- The project profile names a skill for this domain that isn't yet installed.

Authority: PM decides what goes in tier 0. The Client approves the packet as a whole; that approval covers the tier-0 installs listed. If the install budget is exceeded, PM must trim tier 0 or ask the Client for a budget bump before handoff.

## Tier 1 — Per-Role Baseline

Every role has a baseline of skills PM expects it to draw on if they're installed on the machine. For a Developer, that might include a plan-writing skill, a systematic-debugging skill, and a verification-before-completion skill. For a Reviewer, a systematic-debugging skill and a verification-before-completion skill. For PM, a plan-writing/goal-definition skill.

PM populates `### Tier 1 (baseline skills the assigned role should draw on)` in the task packet's `## Suggested Skills` section with the specific baselines the assigned role should use for *this* task.

The worker self-checks at task start:

1. Read the tier-1 list in the task packet.
2. For each entry, check whether a matching installed skill exists.
3. If a *critical* baseline is missing (missing it would materially hurt correctness or verification), send a `skill_need` message to PM.
4. If a baseline is optional and missing, note the gap in the implementation or review report and continue.

PM decides whether to forward the tier-1 `skill_need` to the Client (subject to the per-run install budget) or accept the gap.

## Tier 2 — Mid-Work Niche Self-Check

The worker discovers, part-way through a task, that no installed skill covers the current subproblem. Common examples:

- Doc formatting a client is picky about, that the model keeps drifting on.
- A specific migration/database dialect where an existing skill would give an order-of-magnitude better output.
- A UI library the model doesn't know well.

The worker uses a **skill-search-and-install capability** (see `skills/find-skill.md`) to search the skill registry for a candidate. If a candidate is found, the worker sends a `skill_need` message to PM naming the candidate, the trigger, and why it likely closes the gap. PM decides whether the install budget covers it and either approves directly (if the task packet delegated skill authority) or forwards to the Client.

The worker does **not** install a skill on their own authority. They report the need up.

If no skill-search-and-install capability is installed on the current platform, tier 2 degrades gracefully: the worker reports the gap in a `skill_need` message and continues with best effort. See "Graceful Degradation" below.

## Per-Run Install Budget

Default: **3 skill installs per run**.

Rationale: install churn defeats the framework's efficiency goal. Three installs is enough for one tier-0 install and two tier-2 surprises in a normal run without turning every task into a shopping trip.

Where the number is set:

- Default: **3**, documented in this file.
- Project profile override: a project's `.multiagent/project-profile.md` may set a different number for that project (e.g., 5 for a doc-heavy repo, 1 for a stability-sensitive repo).
- PM references this number in `roles/pm.md`; do not re-define it there. Change this file if the default needs to change globally.

PM tracks cumulative approved installs per run. When the budget is exhausted, further `skill_need` messages must be routed to the Client with a clear "we're out of budget for this run — approve or defer?" question.

## Integration Points

The framework touches two integration surfaces:

- **`templates/task-packet.md`** — has a `## Suggested Skills` section between `## Technical Decisions Delegated To Developer` and `## Suggested Developer Tier`. Three subsections: `### Tier 0 (install requests)`, `### Tier 1 (baseline skills the assigned role should draw on)`, `### Tier 2 (niche needs, if any)`. Tier 2 is usually empty in the packet — it's discovered during work — but PM may pre-populate it when they anticipate a niche need.
- **Role files** — every role (`pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`) has a `### Skill Self-Check` subsection under its `## Skill Discovery` section. PM's version describes tier-0 authority; worker versions describe the tier-1 self-check and the tier-2 mid-work flow. Content is propagated to all three platform adapters (`claude-code/agents/*.md`, `antigravity/agents/*.md`, `codex-agents/templates/*.toml`).

Role files reference skills by **category** (e.g., "a skill-search-and-install capability", "a systematic-debugging skill"). Concrete artifact names live only in this file, in `skills/find-skill.md`, and in `examples/personal-profiles/`.

## Concrete Skills That Satisfy The Search+Install Capability

The framework requires a real installed skill that can (a) search a skill registry for candidates given a natural-language query and (b) install an approved candidate. It does not care which concrete skill fills that role, as long as one does.

| Platform     | Concrete skill that satisfies it today                              | Notes |
|--------------|---------------------------------------------------------------------|-------|
| Codex        | `skill-installer` (ships with the standard Codex skill catalog)     | Recommended default. Handles search + install for the OpenAI skill registry. |
| Claude Code  | *No default ships in-box.* Community skills may satisfy; check `~/.claude/skills/` for anything with search + install semantics. | If none is installed, tier 2 degrades gracefully — see below. Consider installing a community equivalent if tier-2 gaps become common. |
| Antigravity  | *No default ships in-box.* Same as Claude Code: community skills may satisfy; check `~/.gemini/config/skills/` (or the equivalent path). | Same graceful-degradation path. |

If a platform later ships a default that satisfies the capability, add a row here. If a user installs their own concrete skill (any name — the framework doesn't care), it counts. The name `find-skill` in `skills/find-skill.md` refers to the *capability*, not a required artifact.

## Graceful Degradation When The Capability Isn't Installed

Tier 2 must never hard-block. If no skill-search-and-install capability is installed:

1. The worker still notices the mid-work niche gap.
2. The worker sends a `skill_need` message to PM naming the gap (what the current subproblem is, why the installed skills don't cover it, and — if the worker can name one — what kind of skill would help).
3. PM logs the observation, optionally raises it to the Client, and lets the worker continue with best effort.
4. Post-run, the observation is available for the Client to decide whether to install a search-and-install capability going forward.

Tier 1 degradation follows the same pattern: if a baseline skill is missing, the worker reports it and continues with best effort. The framework never turns a missing skill into a stop-work condition — it turns it into a visible, tracked signal.

## Anti-Patterns

- Do not silently install a skill mid-work. Every install must be routed via `skill_need` → PM → Client (subject to budget).
- Do not treat tier 2 as an escape hatch to install a skill for every subproblem. The install budget exists to protect focus; if you're hitting it often, the *packet* probably needs a tier-0 install instead.
- Do not reference concrete skill names in role files. Category references only. Concrete names belong in this file, `skills/find-skill.md`, and personal profiles under `examples/personal-profiles/`.
- Do not hard-block when the search-and-install capability isn't installed. Report and continue.
- Do not re-define the install budget number in role files. The number lives here; role files reference it.
- Do not skip tier 0 just because tier 2 exists. Anticipated installs belong up front so the client can approve them as part of the packet, not one at a time mid-run.
- Do not turn tier-1 self-check into a checkbox exercise. The point is to catch missing capability early, not to list every skill you happen to have installed.
