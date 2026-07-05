---
name: find-skill
description: Search for and install agent skills to close a capability gap. Use when a task needs a skill that is not installed (tier-1 baseline missing or tier-2 niche need mid-work), when a task packet's Suggested Skills section lists something unavailable, or when asked to find/install a skill for a specific problem.
---

# find-skill (Claude Code)

Deterministic search-and-install capability for the multi-agent skills framework (`docs/skills-framework.md` in the MultiAgentSystem repo). This skill turns "I need a capability I don't have" into a concrete, approvable candidate — it does not authorize installs by itself.

The engine and curated registry are bundled in this skill's directory: `find_skill.py` and `registry.toml` next to this file (installed at `~/.claude/skills/find-skill/`).

## Search Order

Work down the layers; stop at the first layer that yields a fitting candidate.

1. **Installed skills.** The gap may already be covered:
   ```bash
   python ~/.claude/skills/find-skill/find_skill.py list-installed --platform claude-code
   ```
2. **Curated registry** (deterministic — prefer this over recalling skill names):
   ```bash
   python ~/.claude/skills/find-skill/find_skill.py search <query terms>
   ```
3. **Platform catalog / known public collections.** Claude Code has no single built-in registry; check the plugin marketplaces the user has configured and the known collections the registry points at (`anthropics/skills`, `obra/superpowers`).
4. **Public search, last resort.** The skills.sh index (`npx skills find <query>`, needs Node) or a web search. Treat results as **unverified candidates**: report them, never install them directly.

## Approval Flow (mandatory)

You are finding a candidate, not deciding an install. Follow the skills framework:

1. Found a candidate → send a `skill_need` message to PM naming the candidate, the trigger, why it closes the gap, and the install command (message shape: `skills/find-skill.md` in the MultiAgentSystem repo). Outside a multiagent run, ask the user directly instead.
2. PM/client approves (subject to the per-run install budget, default 3) → install:
   ```bash
   python ~/.claude/skills/find-skill/find_skill.py install <name> --platform claude-code
   ```
   Registry entries install via shallow git clone; the script refuses names not in the registry — for approved public candidates, run their install command manually.
3. A newly installed skill is discovered at session start; tell the user a restart or new thread may be needed before it activates.

Never install on your own authority, never exceed the install budget, and never silently skip the gap — if no candidate is found, send the `skill_need` naming the gap plainly and continue with best effort.

## Registry Maintenance

The canonical registry lives at `skills/registry.toml` in the MultiAgentSystem repo (this installed copy is a bundle; re-run the installer after editing). Verify `source_repo`/`source_path` before adding entries — the install command checks that the target contains a `SKILL.md` and aborts if the upstream layout changed.
