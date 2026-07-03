# Example: `local/role-skill-map.toml`

A worked example of a personal skill-map overlay. Copy the TOML below to
`local/role-skill-map.toml` and edit it to match skills you actually have
installed. Entries merge **additively** over the tracked
`skills/role-skill-map.toml` — they extend the shipped defaults, never
replace them. Candidates that are not installed on a platform are skipped
silently, so the same file works across Codex, Claude Code, and Antigravity.

```toml
schema_version = 1

# [always] entries are added for every role. Good for a personal skill you
# want the whole team to exercise (e.g. a context-maintenance skill you are
# developing and want field-tested on every run).
[always]
categories = ["a context-maintenance / docs-sync skill (personal)"]
candidates = ["my-context-sync-skill"]

# Per-role additions. Keep these to skills the role uses on EVERY task.
[roles.developer]
categories = ["browser/UI verification skills"]
candidates = ["playwright", "screenshot"]

[roles.developer-strong]
categories = ["browser/UI verification skills"]
candidates = ["playwright", "screenshot"]

[roles.reviewer]
categories = [
  "browser/UI verification skills",
  "a security review checklist skill",
]
candidates = ["playwright", "screenshot", "security-best-practices"]

[roles.reviewer-strong]
categories = [
  "browser/UI verification skills",
  "a security review checklist skill",
]
candidates = ["playwright", "screenshot", "security-best-practices"]

# The optional read-only researcher benefits from search/summarize skills,
# never from write-capable ones — it has no write access by design.
[roles.researcher]
categories = ["a code-search / dependency-graph skill"]
candidates = ["ast-grep", "dependency-cruiser"]
```

What deliberately does **not** appear above: design tools, ticket systems,
framework skills (ASP.NET, WinUI, ...), deploy skills, doc-format skills.
Those apply per-task, not per-role — route them through the task packet's
Tier 0 section or tier-2 mid-work discovery instead of preloading them into
every spawn. A long tier-1 list costs context on every task and buries the
skills that always matter.
