# find-skill Implementation Guide (Codex & Antigravity)

Instructions for implementing the find-skill capability on Codex and Antigravity. The Claude Code implementation is done and is the reference; Codex was implemented on 2026-07-05. This guide records the shared contracts so the remaining platform work behaves identically. Written for the platform's own agent to execute - you know your platform's skill system better than this repo does; where this guide and platform reality disagree, fix the guide too.

## What Already Exists (shared, do not duplicate)

| Piece | Location | Role |
|---|---|---|
| Curated registry | `skills/registry.toml` | Search layer 2. Single source of truth; entries have `name`, `description`, `category`, `keywords`, `source_repo`, `source_path`, `install`, `trust`. |
| Engine | `scripts/find_skill.py` | Deterministic `search` / `list-installed` / `install` (stdlib, Py3.8+, tomllib/tomli). Already knows all three platforms' skill dirs (`~/.claude/skills`, `~/.codex/skills`, `~/.gemini/config/skills`). |
| Capability contract | `skills/find-skill.md` | What "search-and-install capability" must do; `skill_need` message shapes. |
| Framework rules | `docs/skills-framework.md` | Tiers, approval flow, per-run install budget (default 3), graceful degradation. |
| Reference wrapper | `claude-code/skill/find-skill/SKILL.md` | The Claude Code SKILL.md this platform's wrapper should mirror. |

The engine and registry are updated once in this repo and used by all platforms. Do not fork them; if your platform needs a behavior change, change `scripts/find_skill.py` for everyone.

## What To Build Per Platform

A thin skill wrapper plus installer wiring:

1. **Wrapper skill** at the platform's canonical location:
   - Codex: `codex-skill/find-skill/SKILL.md` (done)
   - Antigravity: `antigravity/skill/find-skill/SKILL.md`
   Mirror the Claude Code wrapper's structure: trigger description in frontmatter, the four-layer search order, the mandatory approval flow, registry-maintenance note. Adjust only platform specifics (paths, catalog layer — see below).
2. **Installer wiring** in `scripts/install.py` (`install_codex` / `install_antigravity`): copy the wrapper to the platform skills dir and bundle `scripts/find_skill.py` + `skills/registry.toml` into the installed skill directory, exactly as `install_claude_code` does (search for "find-skill is self-contained" in that function). Extend the platform's `_validate_install_*` the same way `_validate_install_claude_code` iterates all canonical skill dirs.
3. **Role-skill map**: `skills/role-skill-map.toml` already lists `find-skill` in `[always].candidates` — no change needed; once installed it will match. On Codex, verify the generated `[[skills.config]]` blocks pick it up for every role.

## Shared Contracts (must hold on every platform)

- **Search order**: 1) installed skills, 2) curated registry (`find_skill.py search`), 3) platform-native catalog, 4) public search (skills.sh / `npx skills find` / web) — public results are proposed, never auto-installed.
- **Approval flow**: candidate → `skill_need` message to PM → PM/client approval within the install budget → `find_skill.py install <name> --platform <platform>`. The wrapper must state that finding a candidate never authorizes installing it.
- **Degradation**: no candidate found → `skill_need` naming the gap plainly, continue best effort. Never hard-block.
- **Self-containment**: the installed skill dir contains `SKILL.md` + `find_skill.py` + `registry.toml`, so it works on machines without the repo checkout. (When the repo *is* present, prefer the repo copies — they may be newer.)

## Platform Questions To Resolve (and write the answers into your wrapper)

**Codex (resolved 2026-07-05):**
- `skill-installer` is present in the standard Codex system skills at `~/.codex/skills/.system/skill-installer/SKILL.md`; the Codex wrapper uses `find_skill.py` for layers 1-2, delegates layer 3 to `skill-installer`, and keeps layer 4 as propose-only.
- Codex discovers skills at session start. After installing or updating skills, restart Codex or open a new thread before relying on them.

**Antigravity (resolved 2026-07-05):**
- Native catalog/marketplace: None on this platform. The `agy` CLI has `plugin` management but no agent-queryable marketplace. Layer 3 is documented as "None" and falls back to Layer 4.
- Discovery: Skills installed dynamically under `~/.gemini/config/skills/` are discovered on session startup. A fresh session is required before a newly installed skill becomes available.
- Install execution: The installed subagents run under the root session's permission boundary and `find_skill.py install` shells out to `git clone`. In terms of execution flow, workers only propose skills via `skill_need` messages, and the PM main thread executes the install command.

## Acceptance Checklist

- [ ] Wrapper SKILL.md exists canonically and installs to the platform skills dir.
- [ ] Installed skill dir is self-contained (SKILL.md + find_skill.py + registry.toml).
- [ ] `python <skills-dir>/find-skill/find_skill.py search "excel spreadsheet"` returns the `xlsx` entry.
- [ ] `list-installed --platform <platform>` reports the platform's skills and `search_and_install_capability: present`.
- [ ] `install <name> --platform <platform>` refuses non-registry names and prints the approval reminder.
- [ ] `validate-install --platform <platform>` passes and covers the new skill.
- [ ] Platform docs updated: the platform's INSTALL.md, plus the platform row in `docs/skills-framework.md` "Concrete Skills That Satisfy The Search+Install Capability" and `skills/find-skill.md`.
- [ ] `CHANGELOG.md` entry appended.
