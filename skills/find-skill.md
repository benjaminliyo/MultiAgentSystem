# find-skill — Required Search-And-Install Capability

**This file is not a runnable skill artifact.** It documents the *capability* the tier-2 flow in `docs/skills-framework.md` depends on. Any concrete installed skill that fulfills the capability counts. Do not look for a `~/.claude/skills/find-skill/SKILL.md` in this repo — installing one that satisfies the capability is up to the user.

## Purpose

Tier 2 in the skills framework asks the worker (Developer, Developer-Strong, Reviewer, Reviewer-Strong) to notice mid-work that no installed skill covers the current subproblem, then find a candidate that would. That noticing is the easy part. Turning "I need something better here" into a concrete `skill_need` message with an installable candidate name is the hard part.

The search-and-install capability solves the hard part. Without it, the tier-2 flow still runs — but the worker's `skill_need` message just names the *gap* rather than a specific candidate skill, and PM/Client have to hunt for the skill themselves.

## Required Capability

A concrete skill fulfills this capability when it can do all of the following:

1. **Search.** Take a natural-language query (e.g., "markdown table generation for wide comparison tables") and return a ranked list of candidate skills from a skill registry (Anthropic, OpenAI, community, or whichever registry the platform uses).
2. **Return install commands.** For each candidate, return the exact command or manifest fragment needed to install it locally.
3. **Install on approval.** Given an approved candidate, install it to the current runtime's skill directory without further intervention.

A skill that only searches (but can't install) still helps tier 2 — the worker can hand the install command to PM/Client for approval and manual install. A skill that only installs (but can't search) doesn't help tier 2 unless combined with another search source, because the worker still needs to know what to install.

## Concrete Skills That Satisfy It

| Platform     | Concrete skill                                                                 | Status       |
|--------------|--------------------------------------------------------------------------------|--------------|
| Codex        | `skill-installer` (ships with standard Codex skill catalog)                    | Recommended. |
| Claude Code  | No default ships in-box. Check `~/.claude/skills/` for anything with search + install semantics. Community options may exist. | Optional; degrade gracefully if none installed. |
| Antigravity  | No default ships in-box. Check the Antigravity/Gemini skills path (`~/.gemini/config/skills/` or equivalent). | Optional; degrade gracefully if none installed. |

If a platform later ships a default, or if you install a community skill that satisfies the capability, add it to the row. The framework doesn't care about the artifact name.

## Trigger Conditions

A worker should invoke the search-and-install capability when:

- The task packet's `## Suggested Skills` tier-2 subsection lists an anticipated niche need for this task.
- Mid-work, the worker has tried the current subproblem once or twice with only installed skills + built-in knowledge and produced output the worker is genuinely not confident about (e.g., doc formatting the client would probably reject).
- The Reviewer flags a systematic gap (like "the tables in the docs are wrong three times over") that a specialized skill would clearly address.

Do not invoke the capability for:

- One-off surface issues fixable inline with a targeted edit.
- Tasks already covered by an installed baseline skill.
- Skills the worker just wants to try — the install budget exists to prevent this.

## Sample `skill_need` Message

When the search-and-install capability is installed and returns a candidate, the worker sends PM a message like:

```md
type: skill_need
from: developer   (or developer-strong / reviewer / reviewer-strong)
to: pm

title: Tier-2 skill request: markdown-table skill for parity-table row alignment

body:
  trigger: Mid-work on the README parity table; internal edits keep drifting column widths across markdown parsers.
  candidate: <concrete skill name returned by the search-and-install capability>
  install_command: <exact install string returned by the capability>
  why_it_helps: <one or two lines — what the candidate does that installed skills don't>
  budget_check: This is install N of <budget> for this run.
  fallback_if_denied: Continue best-effort with hand-formatting and disclose the residual risk in the report.
```

When the capability is **not** installed, the message body drops `candidate` and `install_command` and instead names the gap plainly:

```md
title: Tier-2 gap: no installed skill for markdown-table alignment; no search-and-install capability available to find one

body:
  trigger: <same as above>
  candidate: unknown — no skill-search-and-install capability installed on this platform.
  gap_description: <what the ideal skill would do>
  fallback: Continue best-effort; recommend the client install a search-and-install capability post-run if this gap recurs.
```

Either shape is acceptable. PM logs the message and either approves the install (subject to the per-run install budget in `docs/skills-framework.md`) or forwards to the Client.

## Graceful Degradation

The tier-2 flow must never hard-block. If no skill-search-and-install capability is installed:

1. The worker still notices the niche gap in the same way.
2. The worker sends the second `skill_need` shape above (no candidate, plain gap description).
3. PM logs it; the Client sees it at closeout.
4. The worker continues the task with best-effort output and documents the residual risk in the implementation or review report.

The purpose is to make missing capability *visible* in the run history, so the Client can decide whether to install a search-and-install capability going forward. It is not a stop-work condition.

## Not In Scope

This file does not author a runnable skill. It does not define an install command. It does not spec a specific artifact name. It documents a capability contract; installing a concrete skill that satisfies the contract is a user or client decision, and the tier-2 flow must run whether or not one is installed.
