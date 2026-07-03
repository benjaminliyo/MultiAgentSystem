# Codex Custom Agents

> **Install:** see [`codex-agents/INSTALL.md`](codex-agents/INSTALL.md) for the one-command installer.
>
> This file is the deeper reference for how Codex custom agents are used in this system — communication model, skill configuration, model and permission defaults. Read it if you're changing the templates or debugging behavior; skip it if you just want to install.

This layer turns the reusable Markdown roles into Codex custom agents.

Codex custom agents are standalone TOML files. Personal agents live in:

```text
~/.codex/agents/
```

Project-scoped agents can live in:

```text
<project>/.codex/agents/
```

This system uses personal agents so they are available across projects.

The global `multiagent-workflow` skill is the recognition layer for short prompts such as:

```text
Run the multiagent workflow for this project. Start with the PM agent.
```

Without that skill or the full launch prompt, a root Codex session may search the target repo for multiagent docs instead of spawning the custom `pm` role.

## Installed Agents

- `pm`: Product manager, team lead, and main-thread agent. Clarifies client intent, assigns work, tracks progress, produces task packets and closeouts, AND owns mechanical routing (run-folder creation, escalation respawning).
- `developer`: Software developer agent. Owns technical design, implementation, tests, bug fixes, and technical docs. Self-logs its own inter-agent messages.
- `developer-strong`: Strong-tier developer for high-risk implementation. Self-logs its own messages.
- `reviewer`: Efficient test engineer and reviewer agent for routine implementation reviews.
- `reviewer-strong`: Strong reviewer agent for risky diffs, failed review loops, or escalations from the efficient reviewer.
- `multiagent-orchestrator`: **REMOVED 2026-06-29.** See `CHANGELOG.md` for the reasoning. Will be revived for autonomous-loop scenarios per `FUTURE-PLANS.md`.

## Recommended Use

Spawn the `pm` custom agent. PM is the main-thread workflow agent and absorbs mechanical routing. After restarting Codex or opening a new thread, ask it to run the multiagent workflow:

```text
Run the multiagent workflow for this project. Start with the PM agent.
```

The main thread should spawn the `pm` agent first, which then spawns workers by name:

```text
pm           # main thread
developer
developer-strong
reviewer
reviewer-strong
```

If the subagent tool metadata does not list these roles, restart Codex or open a new thread. The custom TOML files are loaded as session/tool configuration, so stale sessions may not see newly installed agents.

It should pass structured artifacts between them instead of asking you to copy messages by hand.

## Agent Communication Model

Agents should communicate through PM and shared artifacts:

```text
PM -> task-packet.md
Developer -> technical-plan.md + implementation-report.md
Reviewer -> review-report.md
```

This is intentionally not uncontrolled peer-to-peer chat. PM keeps the workflow traceable, closes completed agents, and routes failures to the right owner.

Use `COMMUNICATION-PROTOCOL.md` for message structure and `TEAM-WORKFLOW.md` for the operating model.

## Skill Configuration

Shipped canonical templates live at `codex-agents/templates/*.toml`. These templates contain the role instructions and skill *categories* (e.g. "a plan-writing skill," "a systematic-debugging skill"), but no concrete `[[skills.config]]` path entries — those depend on which skills each user has installed locally.

The installer (`.\scripts\install.ps1 codex` or `./scripts/install.sh codex`) scans `~/.codex/skills/` and `~/.codex/plugins/` for `SKILL.md` files and appends a `[[skills.config]]` block per skill to each generated `codex-agents/<role>.toml` before copying to `~/.codex/agents/<role>.toml`.

The generated `codex-agents/*.toml` files are gitignored so personal paths never enter version control.

For a working reference of one user's real skill setup, see `examples/personal-profiles/`. Do not copy those skill lists blindly — the names refer to specific installations that vary per user.

If a Developer task needs a domain skill that no template lists (databases, embedded, LaTeX, scientific compute, etc.), the Developer should use a skill-installer or skill-search capability to find and request installation via a `skill_need` message routed through PM.

All agents should have a skill-installer or skill-search capability available for this purpose.

## Model And Permission Defaults

Use Scoped Autonomy as the normal run-level permission pattern: PM asks once for workspace/project read-write access for PM and spawned agents, then escalates only for access outside that envelope.

Use a balanced automatic model policy by default. PM uses `gpt-5.5` with `xhigh` reasoning — strongest model because PM now combines product judgment with mechanical routing. Developer remains on `gpt-5.5` with `high` reasoning because it owns technical design and implementation. Reviewer uses `gpt-5.4-mini` with `medium` reasoning by default. Reviewer escalations use `reviewer-strong`, which runs `gpt-5.5` with `high` reasoning for large or risky diffs, security/data-loss concerns, or failed review loops. There is no separate orchestrator model — see `CHANGELOG.md` (2026-06-29).

The root session should also have the `multiagent-workflow` skill installed at:

```text
~/.codex/skills/multiagent-workflow
```

(The installer copies this automatically.)

## After Editing

Restart Codex or open a new thread after adding or changing files under `~/.codex/agents` or `~/.codex/skills`.
