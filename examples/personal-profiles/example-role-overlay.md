# Example: `local/overlays/roles/<role>.md`

A worked example of a personal role overlay. The installer appends this text
to the **installed** copy of the matching agent (for Codex it is inserted
into the generated TOML's `developer_instructions`); canonical files ship
clean. One file per role: `local/overlays/roles/developer.md`,
`.../reviewer.md`, etc.

A common use is dogfooding a skill you develop yourself — giving every agent
a standing instruction to use it, watch how it behaves, and report back:

```markdown
## My-Skill Dogfooding (personal)

The `my-context-sync-skill` keeps CLAUDE.md, AGENTS.md, and other
reusable-context files in sync with decisions made during work. I develop
this skill — every run doubles as a field test. If it is not installed on
this platform, note that in your report and skip the rest.

When it is available:

1. Invoke it whenever its trigger conditions apply.
2. Verify it behaved as designed: did it trigger when it should have, stay
   quiet when nothing drifted, propose accurate and minimal edits to the
   right file, and run without errors or confusing output?
3. Report what you observed in your report under a dedicated heading. One
   line if it worked cleanly; full detail for any false positive, false
   negative, bad edit, or performance problem.
```

## Match the overlay to the role's write permissions

When the dogfooded skill *proposes file edits* (like a context-sync skill),
write a different overlay per role, keyed to who may actually write in the
working project:

- **Developer (has write access)** — two lanes: drift caused by its own
  current change may be approved and applied directly (noted in the
  implementation report); pre-existing or unrelated drift must be reported
  to PM and approved before anything is touched. When in doubt, treat a
  proposal as unrelated and notify first.
- **PM (has write access as parent, rarely uses it)** — routes task-related
  drift to Developer; applies anything else itself only after showing the
  client the proposed change and getting explicit approval.
- **Reviewer / Researcher (read-only)** — detect-and-report only: never
  apply a proposed edit; capture the proposal in the report and an
  observation message to PM.

The generic rule ("respect your role's write permissions when a skill
proposes edits") lives in the canonical role files; the overlay carries the
skill-specific instructions for *your* skill.

Anything personal, machine-specific, or client-specific belongs here rather
than in `roles/*.md` or the platform agent files — the validator warns when
personal content leaks into canonical files.
