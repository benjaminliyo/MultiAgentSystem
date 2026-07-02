# Future Plans

## MultiAgentSystem Init Skill

Create a reusable init skill that helps users design and scaffold a multi-agent system fitted to their own workflow and agent platform.

Before building the init skill, create working reference implementations for:

- Codex,
- Claude Code,
- Antigravity.

Use the current Codex-focused MultiAgentSystem as the canonical behavioral reference. Let each platform implementation adapt the mechanics to its native agent, session, tool, hook, and instruction model. After all three systems work, compare them and extract the shared core plus platform-specific adapters.

The eventual init skill should help a user choose:

- team structure,
- agent roles,
- authority boundaries,
- communication protocol,
- session strategy,
- permission model,
- task artifacts,
- review loop,
- skill assignments,
- project profile format,
- target agent platform.

The skill should support teams beyond the default PM / Developer / Reviewer shape. Examples:

- PM / Designer / Developer / Reviewer
- Researcher / Architect / Developer / QA
- Security Lead / Developer / Security Reviewer
- Data Analyst / Engineer / Reviewer
- Solo PM-developer-reviewer loop for small projects

The skill should produce platform-appropriate scaffolds, such as:

- role instructions,
- Codex custom-agent TOML files when targeting Codex,
- Claude Code-native configuration or instructions when targeting Claude Code,
- Antigravity-native configuration or instructions when targeting Antigravity,
- launch prompts,
- message templates,
- project profile templates,
- team workflow docs,
- installation instructions.

It should also recommend when to use subagents, when to use separate long-lived sessions, and when to keep everything in one root thread.

This is intentionally a later project. The current MultiAgentSystem is the prototype and source material.

## Deferred: Spawnable Orchestrator For Autonomous Loops

We removed the spawnable orchestrator agent on 2026-06-29 (see `CHANGELOG.md`) because in the interactive PM-led workflow it was redundant — the main thread (PM) already absorbs mechanical routing. The role is **deferred, not abandoned**. We will reintroduce a spawnable orchestrator when we tackle any of these scenarios:

### When we'll need it

1. **Autonomous loops.** A `CronCreate`, `ScheduleWakeup`, or external trigger fires a fresh session with no human in the conversation thread. There is no "main thread = PM" because there is no human to talk to. A spawnable orchestrator becomes the workflow entry point: it loads the project profile, decides what work to drive (from a queue, a watched file, or a task DB), and spawns PM-as-a-child-agent to handle product judgment.
2. **Deep nesting limits.** A scenario where PM (as a child agent) cannot spawn workers because the platform enforces nesting depth. The main thread spawns the orchestrator once and delegates all routing.
3. **Multi-PM concurrent runs.** Several PMs are active in parallel (different projects, different clients) and need a higher-level coordinator to assign and rate-limit work between them.

### Implementation outline (for future us)

- Restore `claude-code/agents/multiagent-orchestrator.md` and update `codex-agents/multiagent-orchestrator.toml` to remove the deprecation header.
- Scope the orchestrator strictly to **mechanical** responsibilities: workflow entry, run-folder creation, spawning PM-as-child, escalation catch-and-respawn, run closeout, exit reporting back to whatever fired the session. **Do not** give the orchestrator product judgment — that is still PM's exclusive authority.
- Add a `launch/start-autonomous-loop.md` or equivalent that documents the cron/trigger entry pattern.
- Decide how the orchestrator persists its summary back to the trigger source (file, webhook, push notification).
- Reconsider `scripts/multiagent_files.py` `CANONICAL_AGENT_FILES`: orchestrator becomes mandatory in the autonomous-loop install profile, optional in the interactive install profile.

### What to keep in mind

The orchestrator should **never re-acquire judgment work** (tier selection, scope decisions, requirement clarification). The 2026-06-29 decision was that those belong to PM. The autonomous-loop orchestrator is a workflow driver, not a coordinator-with-opinions. If we find ourselves writing "the orchestrator decides X" instructions, that's a signal we're regrowing the redundancy and should push the decision back to PM-as-child.
