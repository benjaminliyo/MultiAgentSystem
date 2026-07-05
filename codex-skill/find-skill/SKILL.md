---
name: find-skill
description: Search for and install agent skills to close a capability gap. Use when a task needs a skill that is not installed (tier-1 baseline missing or tier-2 niche need mid-work), when a task packet's Suggested Skills section lists something unavailable, or when asked to find/install a skill for a specific problem.
---

# find-skill (Codex)

Deterministic search-and-install capability for the multi-agent skills framework (`docs/skills-framework.md` in the MultiAgentSystem repo). This skill turns "I need a capability I don't have" into a concrete, approvable candidate. It does not authorize installs by itself.

The engine and curated registry are bundled in this skill's directory: `find_skill.py` and `registry.toml` next to this file (installed at `~/.codex/skills/find-skill/`). When the canonical MultiAgentSystem repo is present, prefer the repo copies if they are newer; the bundled files are there so the skill still works without the repo checkout.

## Search Order

Work down the layers; stop at the first layer that yields a fitting candidate.

1. **Installed skills.** The gap may already be covered:
   ```bash
   python ~/.codex/skills/find-skill/find_skill.py list-installed --platform codex
   ```
2. **Curated registry** (deterministic; prefer this over recalling skill names):
   ```bash
   python ~/.codex/skills/find-skill/find_skill.py search <query terms>
   ```
3. **Codex native catalog.** Standard Codex installs include the preinstalled `skill-installer` system skill (`~/.codex/skills/.system/skill-installer/SKILL.md`), which searches and installs from the OpenAI skills catalog. Delegate this layer to `skill-installer`; do not reimplement its catalog logic here. If `skill-installer` is absent from the active skills list, record that gap in the `skill_need` message and continue to public search.
4. **Public search, last resort.** The skills.sh index (`npx skills find <query>`, needs Node) or a web search. Treat results as unverified candidates: report them, never install them directly.

## Approval Flow (mandatory)

You are finding a candidate, not deciding an install. Follow the skills framework:

1. Found a candidate -> send a `skill_need` message to PM naming the candidate, the trigger, why it closes the gap, and the install command (message shape: `skills/find-skill.md` in the MultiAgentSystem repo). Outside a multiagent run, ask the user directly instead.
2. PM/client approves (subject to the per-run install budget, default 3) -> install:
   ```bash
   python ~/.codex/skills/find-skill/find_skill.py install <name> --platform codex
   ```
   Registry entries install via shallow git clone; the script refuses names not in the registry. For an approved Codex-catalog candidate, use `skill-installer`. For an approved public candidate, run its install command manually.
3. Codex discovers skill and agent files at session start. After installing or updating skills, tell the user to restart Codex or open a new thread before relying on the new skill.

Never install on your own authority, never exceed the install budget, and never silently skip the gap. If no candidate is found, send the `skill_need` naming the gap plainly and continue with best effort.

## Registry Maintenance

The canonical registry lives at `skills/registry.toml` in the MultiAgentSystem repo (this installed copy is a bundle; re-run the installer after editing). Verify `source_repo` and `source_path` before adding entries. The install command checks that the target contains a `SKILL.md` and aborts if the upstream layout changed.
