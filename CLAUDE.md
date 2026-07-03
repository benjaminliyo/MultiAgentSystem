# AGENTS.md

Working instructions for maintaining the reusable MultiAgentSystem.

## Purpose

This folder is the canonical source for a PM-led multi-agent software team. The system models:

```text
Client / CEO / Boss
  -> PM Agent, team lead
      -> Developer Agent
      -> Reviewer Agent
      -> Researcher Agent (optional, read-only)
```

PM is the main-thread agent. PM owns product clarity, task assignment, progress tracking, client closeout, and the mechanical routing that no other agent owns (run-folder creation, escalation respawning, worktree spawning, parallel-spawn dispatch). Developer, Reviewer, and the optional Researcher report to PM and self-log their own inter-agent messages. The earlier dedicated `multiagent-orchestrator` role was removed on 2026-06-29 — see `CHANGELOG.md` for the reasoning and `FUTURE-PLANS.md` for when it will be reintroduced (autonomous-loop scenarios).

## Key Files

- `README.md` - project overview and quick start.
- `CHANGELOG.md` - append-only decision log. Read first when something looks unexpected.
- `FUTURE-PLANS.md` - later ideas (init skill, autonomous-loop orchestrator).
- `TEAM-WORKFLOW.md` - business-style team model, lifecycle, session strategy, and permissions.
- `COMMUNICATION-PROTOCOL.md` - standard message envelope and message types.
- `ORCHESTRATION.md` - routing states and PM-led workflow.
- `CODEX-CUSTOM-AGENTS.md` - how custom Codex agents are installed and recognized.
- `claude-code/INSTALL.md` - how Claude Code agents, skill, and slash command are installed.
- `codex-agents/templates/*.toml` - canonical Codex custom-agent templates. The install script generates `codex-agents/*.toml` with local skill paths substituted in; the generated files are gitignored.
- `codex-skill/multiagent-workflow/` - canonical Codex recognition skill.
- `claude-code/agents/*.md` - canonical Claude Code subagent definitions.
- `claude-code/skill/multiagent-workflow/` - canonical Claude Code workflow skill.
- `claude-code/commands/multiagent.md` - canonical Claude Code `/multiagent` slash command.
- `antigravity/INSTALL.md` - how Antigravity agents and skill are installed.
- `antigravity/agents/*.md` - canonical Antigravity subagent definitions.
- `antigravity/skill/multiagent-workflow/SKILL.md` - canonical Antigravity workflow skill.
- `roles/*.md` - shared role instructions used by all platforms.
- `skills/role-skill-map.toml` - editable per-role skill defaults. Codex installer enforces it as a hard allowlist; Claude Code installer injects matched skills into the installed agents' `skills:` frontmatter (preload); Antigravity is instruction-level only. The gitignored `local/role-skill-map.toml` merges additively on top for personal per-role additions.
- `claude-code/hooks/` - canonical hook scripts shared by all platforms: `session-start-load-profile` (project profile), `user-prompt-pm-mode` (per-turn PM-role reinjection while a run is active; `.ps1`/`.sh` emit plain text for Claude Code/Codex, `.py` emits Antigravity's required `{"additionalContext": ...}` JSON contract), `subagent-log.py` (mechanical spawn/finish logging: SubagentStart/SubagentStop on Claude Code and Codex; PreToolUse/PostToolUse with matcher `invoke_subagent` on Antigravity), `stop-warn-unclosed-run`.
- `codex/hooks.json` / `antigravity/hooks.json` - hook-config templates with different schemas (Codex: Claude-style `{"hooks": {...}}`; Antigravity: named hook groups, events limited to PreInvocation/PostInvocation/PreToolUse/PostToolUse/Stop). `prepare-run --project-hooks codex|antigravity` renders them into `<project>/.codex/hooks.json` / `<project>/.agents/hooks.json`.
- `local/` (gitignored) - personal overlay. `local/overlays/roles/<role>.md` is merged into the **installed** agent copies at install time; `local/role-skill-map.toml` merges additively over the tracked skill map. Canonical files ship clean. See `docs/skills-framework.md` "Local Overlay".
- `examples/personal-profiles/` - genericized examples of a personal skill setup (`local/role-skill-map.toml` + role overlays); illustrations, not defaults, and not anyone's live config.
- `launch/*.md` - copy/paste launch prompts (Codex).
- `templates/` - shared task, report, and message templates.
- `scripts/multiagent_files.py` - runtime helper agents invoke during a run (prepare-run, append-message, status, set-state, close-run, activate-run). `prepare-run` also activates PM mode: writes `.multiagent/active-run.json` and inserts marker blocks (`<!-- multiagent:begin/end -->`) into the project's CLAUDE.md/AGENTS.md/GEMINI.md; `close-run` reverses both; `activate-run` restores PM mode for any existing run (resume, including closed runs).
- `scripts/install.py` - install and validation for every platform (`install --platform <name>`, `validate-install`).
- `scripts/install.ps1` / `scripts/install.sh` - one-line wrappers around `install.py`.
- `scripts/_common.py` - constants and low-level helpers shared by runtime and install.

## Canonical vs Installed Copies

Canonical source lives in this folder. Installed copies live in each platform's user directory.

### Codex

Installed copies live at:

```text
~/.codex/agents/
~/.codex/skills/multiagent-workflow/
```

(On Windows: `$HOME\.codex\agents\` and `$HOME\.codex\skills\multiagent-workflow\`.)

When changing `codex-agents/templates/*.toml`, re-run the Codex install script so the generated `codex-agents/*.toml` and the copies in `~/.codex/agents/` are refreshed.

When changing `codex-skill/multiagent-workflow`, copy it to `~/.codex/skills/multiagent-workflow/`.

After changing installed agents or skills, tell the user to restart Codex or open a new thread.

### Claude Code

Installed copies live at:

```text
~/.claude/agents/
~/.claude/skills/multiagent-workflow/
~/.claude/commands/multiagent.md
```

When changing `claude-code/agents/*.md`, copy the updated `.md` files to `~/.claude/agents/`.

When changing `claude-code/skill/multiagent-workflow/`, copy it to `~/.claude/skills/multiagent-workflow/`.

When changing `claude-code/commands/multiagent.md`, copy it to `~/.claude/commands/multiagent.md`.

After changing installed agents, skill, or commands, tell the user to restart the Claude Code session.

Full step-by-step install commands (both PowerShell and Bash) live in `claude-code/INSTALL.md`.

### Google Antigravity

Installed copies live at:

```text
~/.gemini/config/agents/
~/.gemini/config/skills/multiagent-workflow/
```

When changing `antigravity/agents/*.md`, copy the updated `.md` files to `~/.gemini/config/agents/`.

When changing `antigravity/skill/multiagent-workflow/SKILL.md`, copy it to `~/.gemini/config/skills/multiagent-workflow/SKILL.md`.

After changing installed agents or skills, start a new Antigravity session.

Full step-by-step install commands (both PowerShell and Bash) live in `antigravity/INSTALL.md`.

### Shared

`scripts/multiagent_files.py`, `scripts/install.py`, and `scripts/_common.py` are **not** copied into any platform's install root. All platforms invoke them from the canonical repo path. Update once, used by all.

## Maintenance Rules

- Keep PM as the team lead AND the main-thread agent. Developer and Reviewer report to PM. PM owns mechanical routing in addition to product judgment.
- Do not reintroduce a separate `multiagent-orchestrator` agent for the interactive workflow. The role was removed on 2026-06-29 (see `CHANGELOG.md`). It will come back only for the autonomous-loop scenario described in `FUTURE-PLANS.md`.
- Keep the strong-tier pattern symmetric between Developer and Reviewer. `developer-strong` and `reviewer-strong` are escalation targets, not nicer defaults. PM hints via `Suggested Developer Tier`; the default `developer` may self-escalate via `ESCALATE_TO_STRONG_DEVELOPER`; PM performs the mechanical respawn. Update both sides of the pattern when changing one.
- Keep `researcher` optional, read-only, and single-tier. It is spawned by PM on demand (large/unfamiliar codebase during discovery, or a worker's `exploration_request`), never as a default step, and has no strong variant. Its only write surface is run-folder messages via `append-message`. Do not give it Edit/Write tools or add it to the escalation pattern.
- Keep a skill-installer or skill-search capability assigned to every custom agent so agents can search for missing skills. In `skills/role-skill-map.toml`, that capability lives in `[always]` — never remove it, or tier-2 discovery dies under Codex's hard allowlist.
- Role guidance references skills by *category* ("a systematic-debugging skill"), not by concrete skill name — except in `skills/role-skill-map.toml`, which is exactly the place for concrete candidates. Personal-only content (e.g. the user's context-update skill and its dogfooding feedback loop) belongs in the gitignored `local/` (`local/overlays/roles/` for instruction text, `local/role-skill-map.toml` for skill assignments), never in canonical files; the validator warns on leaks. Genericized concrete-skill examples belong in `examples/personal-profiles/`.
- If behavior changes, update both the shared `roles/*.md` docs and the matching platform-specific files (Codex `.toml` template, Claude Code `.md`, Antigravity `.md`).
- Codex skill assignments: local skill paths belong in the generated `codex-agents/*.toml` (gitignored). Do not edit paths in `codex-agents/templates/*.toml`; edit `skills/role-skill-map.toml` (which skills per role) or the install script logic (how they're applied) instead. Claude Code and Antigravity auto-discover skills from `~/.claude/skills/` and `~/.gemini/config/skills/`; on Claude Code the installer additionally preloads mapped skills via the installed agents' `skills:` frontmatter.
- Keep the PM-mode lifecycle symmetric: whatever `prepare-run` activates (active-run.json, marker blocks, project hooks), `close-run` must deactivate. The marker delimiters `<!-- multiagent:begin/end -->` are load-bearing — hooks and cleanup both key on them.
- Hook scripts live once in `claude-code/hooks/` and are referenced by all platform hook configs. When adding a hook, update `claude-code/settings.example.json`, `_wire_claude_hooks` in `scripts/install.py`, and the `codex/hooks.json` + `antigravity/hooks.json` templates together.
- If launch behavior changes, update `launch/start-multiagent.md` (Codex), `codex-skill/multiagent-workflow/SKILL.md`, `claude-code/skill/multiagent-workflow/SKILL.md`, and `claude-code/commands/multiagent.md`. PM's "Routing And Run Management" section in `roles/pm.md` is the single source of truth for routing detail — keep platform docs thin and pointed at it.
- Do not duplicate large blocks across files unless necessary. Prefer one canonical doc plus references from other files.
- Preserve user edits. Do not revert unrelated changes.

## Verification

The repo helper validates all installs. Run from the canonical repo root:

```powershell
python scripts/install.py validate-install --repo-root . --platform codex
python scripts/install.py validate-install --repo-root . --platform claude-code
python scripts/install.py validate-install --repo-root . --platform antigravity
```

Each command reports `complete: True` and an empty `missing` list when the platform's canonical and installed files line up. Pass `--codex-home <path>`, `--claude-home <path>`, or `--antigravity-home <path>` to point at a non-default install root.

For Codex, after regenerating custom-agent TOML files, additionally confirm the skill-path references resolve on disk:

```powershell
@'
import pathlib, tomllib
root = pathlib.Path("codex-agents")
for path in sorted(root.glob("*.toml")):
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    paths = [entry["path"] for entry in data.get("skills", {}).get("config", [])]
    print(f"OK {path.name}: {len(paths)} skill entries")
    for skill_path in paths:
        if not pathlib.Path(skill_path).exists():
            raise SystemExit(f"Missing skill path in {path.name}: {skill_path}")
'@ | python -
```

For Claude Code, the validator parses each agent's YAML frontmatter and confirms `name` and `description` are present. There is no skill-path list to validate on the Claude Code side — Claude Code auto-discovers skills under `~/.claude/skills/`.

For Antigravity, the validator parses each agent's YAML frontmatter and confirms `name` and `description` are present. Antigravity auto-discovers skills under `~/.gemini/config/skills/`.

The `skill-creator` validator may require PyYAML. If validation fails with `ModuleNotFoundError: No module named 'yaml'`, do a minimal structural check and report the validator dependency issue instead of claiming full validation passed.

## Recognition Troubleshooting

If a project thread does not recognize "Run the multiagent workflow":

### Codex
1. Confirm `~/.codex/skills/multiagent-workflow/SKILL.md` exists.
2. Confirm `~/.codex/agents/pm.toml` exists.
3. Confirm the current subagent tool metadata lists `pm`, `developer`, `developer-strong`, `reviewer`, `reviewer-strong`, and `researcher`.
4. Restart Codex or open a fresh thread after install/update.
5. Use the stronger prompt:
```text
Use the multiagent-workflow skill. Spawn the custom pm agent using agent_type: pm.
```

### Claude Code
1. Confirm `/multiagent` or `pm` subagent type is recognized. If not, verify files in `~/.claude/agents/` and skills in `~/.claude/skills/`.
2. Restart the Claude Code session.

### Antigravity
1. Confirm `/multiagent` or trigger phrase is recognized. If not, verify files in `~/.gemini/config/agents/` and skills in `~/.gemini/config/skills/`.
2. Start a new session.
