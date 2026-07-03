# Personal Skill Setup (Reference Examples)

The files in this directory are **genericized examples** of how to layer a
personal skill setup on top of the shipped defaults. They are illustrations,
not defaults, and none of the skill names in them are guaranteed to exist on
your machine.

Your live personal configuration does **not** belong here (this directory is
tracked). It belongs in the gitignored `local/` directory, which the
installer merges into the installed copies:

| What | Where it lives | What the installer does with it |
|------|----------------|--------------------------------|
| Personal per-role skill additions | `local/role-skill-map.toml` | Merged additively over `skills/role-skill-map.toml` (Codex allowlist entries, Claude Code `skills:` frontmatter) |
| Personal per-role instruction text | `local/overlays/roles/<role>.md` | Appended to the installed agent bodies (inserted into `developer_instructions` for Codex) |

## What's here

- `example-local-role-skill-map.md` — a worked example of a personal
  `local/role-skill-map.toml`, with notes on choosing what belongs in the
  tier-1 baseline versus what should stay tier-0/tier-2.
- `example-role-overlay.md` — a worked example of a personal role overlay
  (`local/overlays/roles/<role>.md`).

## Guidance

Keep the tier-1 baseline lean: only skills the role should draw on for
*every* task (process skills like TDD, debugging, verification, planning —
plus universal verification tools). Domain skills (design tools, ticket
systems, framework-specific or deploy skills) should enter per-task via the
task packet's Tier 0 section, or mid-work via tier-2 discovery. See
`docs/skills-framework.md` for the tier model.
