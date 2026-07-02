# Reviewer Skill Profile

Primary role: requirement coverage, verification review, code review, and pass/fail decision.

Use these installed skills when applicable:

- `superpowers:systematic-debugging`
- `superpowers:verification-before-completion`
- `github:github`
- `github:gh-address-comments`
- `github:gh-fix-ci`
- `openai-docs`
- `skill-installer`
- `context-update:context-update`
- `playwright`
- `playwright-interactive`
- `screenshot`
- `security-best-practices`
- `security-threat-model`
- `security-ownership-map`
- `sentry`

Use `skill-installer` for stack-specific review skills such as ASP.NET Core, WinUI, ChatGPT Apps, or Figma when the task actually needs them.

Avoid:

- expanding scope,
- silently redesigning product behavior,
- turning optional preferences into required fixes,
- taking over implementation unless explicitly asked.

ContextUpdate note:

- Use `context-update` when review reveals durable project decisions and report false positives, false negatives, confusing reports, unexpected proposed edits, performance issues, or runtime-specific problems.
