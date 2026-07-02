# Changelog

Append-only decision log for architectural and role-level changes to the MultiAgentSystem. Different from a release changelog — this is the durable record of *what we changed and why*, so future contributors (and future agents on Codex, Claude Code, or other platforms) can understand the current shape of the system without re-deriving the reasoning.

## How To Use This File

- **Reverse chronological.** Newest entries at the top.
- **One entry per decision**, not per file edit. Group related file changes under a single dated decision.
- **Required sections per entry**: `Decision`, `Why`, `Files affected`, `Reversal triggers` (what conditions would make us undo this).
- **Forward-looking work goes in `FUTURE-PLANS.md`**, not here. Cross-link with a `See also:` line if the decision defers something.
- **Don't edit past entries.** If a later decision overrides an earlier one, write a new entry that names the prior entry it supersedes.

---

## 2026-06-29 — Phase 9: Claude Code validate-install test fixtures

### Decision

Extended `tests/test_multiagent_files.py` with a `_make_claude_code_fixture` helper that builds a complete mock install (`repo/claude-code/agents/*.md`, `repo/claude-code/skill/multiagent-workflow/SKILL.md`, parallel `claude_home/agents/`, `claude_home/skills/multiagent-workflow/`) and 10 new test cases that exercise the Claude Code validator end-to-end.

Tests added:

1. `test_claude_code_validate_install_happy_path` — smoke test: complete fixture validates with `complete: True`, no `missing`, no `warnings`.
2. `test_claude_code_validate_install_missing_canonical_agent` — deleted `claude-code/agents/pm.md` from repo; validator reports it missing.
3. `test_claude_code_validate_install_missing_installed_agent` — deleted `claude_home/agents/developer.md`; validator reports the installed path missing.
4. `test_claude_code_validate_install_missing_canonical_skill` — deleted the canonical SKILL.md; validator reports it.
5. `test_claude_code_validate_install_missing_installed_skill` — deleted the installed SKILL.md; validator reports it.
6. `test_claude_code_validate_install_malformed_frontmatter` — agent file with no `---` frontmatter at all; validator reports "missing YAML frontmatter".
7. `test_claude_code_validate_install_frontmatter_missing_name` — frontmatter present but no `name:` field; validator reports "missing 'name'".
8. `test_claude_code_validate_install_frontmatter_missing_description` — frontmatter present but no `description:` field; validator reports "missing 'description'".
9. `test_claude_code_validate_install_warns_on_missing_context_update_mention` — valid frontmatter, body without `context-update`; validator marks complete but emits a warning (not a hard failure).
10. `test_claude_code_canonical_set_does_not_include_orchestrator` — regression guard: `CANONICAL_AGENT_FILES["claude-code"]` and `["codex"]` must not contain `multiagent-orchestrator.*`. Catches accidental re-introduction after the 2026-06-29 removal.

Total test count: 16 (was 6 before Phase 9).

### Why

`validate-install --platform claude-code` is the only programmatic gate between "install looks right" and "install is broken." Before this entry, only the Codex validator was tested, and a Claude Code validator regression could ship silently. The 10 new tests cover the happy path plus the seven failure modes the validator actually checks for, plus a regression guard against re-adding the deprecated orchestrator to the canonical set.

The fixture helper is small enough to keep inline rather than promoting to its own module; if more tests need it later, extract.

### Files affected

- Edited: `tests/test_multiagent_files.py` — added `_make_claude_code_fixture`, `_validate_claude`, and 10 test methods.

### Verified

All 16 tests pass:

```
$ python -m unittest tests.test_multiagent_files
......
----------------------------------------------------------------------
Ran 16 tests in 0.292s
OK
```

### Reversal triggers

- If the Claude Code validator schema changes (e.g., requires a new frontmatter field), update both the validator and the relevant tests in lockstep. Don't relax the tests to make them pass without re-validating the new requirement.
- If `_make_claude_code_fixture` grows beyond ~50 lines or needs reuse from another test file, extract to `tests/_fixtures.py` (or similar) rather than copy-paste.

### Follow-ups (not done in this entry)

- No automated test for the hooks (`session-start-load-profile.{ps1,sh}` and `stop-warn-unclosed-run.{ps1,sh}`). Manually exercised in Phase 6 only. A `tests/test_hooks.py` that subprocesses the bash variants against a `.multiagent/` fixture would be straightforward; deferred.
- No CI configuration (`.github/workflows/` or similar) runs `python -m unittest` automatically. Adding a tiny CI job would prevent local-only test regressions.

---

## 2026-06-29 — Phase 6: Opt-in Claude Code hooks

### Decision

Added two opt-in Claude Code hooks plus an example settings file:

- `claude-code/hooks/session-start-load-profile.{ps1,sh}` — on `SessionStart`, looks for `<cwd>/.multiagent/project-profile.md` and emits its contents as additional session context. Quality-of-life: PM no longer has to remember to `Read` the profile.
- `claude-code/hooks/stop-warn-unclosed-run.{ps1,sh}` — on `Stop`, scans the most recent `.multiagent/runs/<run>/run-summary.md`. If the `state:` field is anything other than `done`/`closed`/`completed`, prints a warning. Catches the "abandoned a run" failure mode.
- `claude-code/settings.example.json` — illustrative wiring. User copies or merges into `~/.claude/settings.json`. Ships the PowerShell variants by default; comments document the Bash swap and the schema-gotcha warning.

Both PowerShell and Bash variants of each hook ship so users on WSL / Git Bash / macOS / Linux are covered.

Skipped the proposed third "SessionEnd status-summary" hook because the user correctly observed it would just re-display data the workflow already saves to `run-summary.md` and `messages.jsonl` — no failure mode caught.

### Convention added: `state:` terminal values

PM's "Routing And Run Management" section in `roles/pm.md`, `codex-agents/pm.toml`, and `claude-code/agents/pm.md` was extended to require setting `state: done` (or `closed` / `completed`) in `run-summary.md` at closeout. The convention applies on both platforms even though only the Claude Code `stop-warn-unclosed-run` hook reads it today. Without this convention the warning hook would false-positive on every closed run.

### Documentation

`claude-code/INSTALL.md` got:

- A "What Gets Installed" row marking hooks + settings.example as `optional`, with a note that hooks live where the repo is checked out (no copy step needed).
- A full "Optional: Hooks" section covering: wiring via `settings.json`, path adjustments, PowerShell-vs-Bash swap, verification steps for each hook, removal, and the schema-gotcha warning.

### Why

Hooks solve specific failure modes; they're not for skill discovery (the skill description already handles that). The two we shipped each catch a real issue:

- Profile auto-load: PM tool-call savings + "PM forgot to read the profile" prevention.
- Dangling-run warning: catches abandoned runs that would otherwise only be noticed when the user re-opened the run folder.

Keeping them opt-in respects users who don't want shell scripts running on session events.

### Files affected

- New: `claude-code/hooks/session-start-load-profile.ps1`, `.sh`
- New: `claude-code/hooks/stop-warn-unclosed-run.ps1`, `.sh`
- New: `claude-code/settings.example.json`
- Edited: `roles/pm.md`, `codex-agents/pm.toml`, `claude-code/agents/pm.md` (added the `state: done` closeout convention)
- Edited: `claude-code/INSTALL.md` (hooks section + install table update)

### Verified

- Both PowerShell hooks tested against a synthetic `.multiagent/` fixture: profile content was emitted on stdout; warning fired when `state: developer_implementation`; warning suppressed silently when `state: done`. (Bash variants are direct ports of the same logic; their grep/sed equivalents were spot-tested in the same fixture.)
- `settings.example.json` validated as parseable JSON.

### Reversal triggers

- If a Claude Code version changes the `hooks` schema in `settings.json` and the example stops working, update `settings.example.json` and the schema-gotcha note in `INSTALL.md`. Don't silently remove the hooks.
- If users start writing `state:` values that the hook's regex doesn't recognize as terminal, expand the regex rather than complain — make the convention permissive.

### Follow-ups (not done in this entry)

- The `_comment_schema_note` in `settings.example.json` acknowledges we're guessing slightly at the exact `hooks` JSON shape Claude Code expects. If the hooks fail to fire after wiring, that's where to look first.
- No CI test exercises the hooks; they're tested manually. Adding a `tests/test_hooks.py` that runs them against fixtures would be cheap; deferred for now.

---

## 2026-06-29 — Phase 8: Docs and install for the Claude Code adapter

### Decision

Wrote `claude-code/INSTALL.md` (new) and refreshed `README.md` and `AGENTS.md` for dual-platform install.

`claude-code/INSTALL.md`:

- Prerequisites (Claude Code installed, Python 3.11+, repo cloned).
- What gets installed (table: agents → `~/.claude/agents/`, skill → `~/.claude/skills/multiagent-workflow/`, command → `~/.claude/commands/multiagent.md`).
- Side-by-side PowerShell and Bash install commands. Resolved the open question from `claude-code/IMPLEMENTATION-PLAN.md` ("Bash or PowerShell?") in favor of both — the repo lives on Windows but users may install via WSL, Git Bash, or remote shells.
- Restart-session step, `validate-install --platform claude-code` verification, first-run example (`/multiagent fix the broken login redirect`), update procedure, uninstall commands, and Claude-Code-specific troubleshooting.
- Cross-links to `IMPLEMENTATION-PLAN.md`, the skill, PM's role doc, `CHANGELOG.md`, and `FUTURE-PLANS.md`.

`README.md`:

- Added a "Choose Your Platform" table at the top mapping Codex and Claude Code to their install doc + entry-point command.
- Updated the "Recommended Layout" tree to show both `codex-*/` and `claude-code/`, with the deprecation note on `multiagent-orchestrator.toml`.
- Split "First Manual Run" into Codex and Claude Code variants.
- Split "Recognition Troubleshooting" into per-platform sections; the Claude Code section delegates to `claude-code/INSTALL.md` rather than duplicating.
- Updated the `Automation Helper` section to show both `--platform codex` and `--platform claude-code` validation, and to call out worker self-logging.
- Added `CHANGELOG.md`, `FUTURE-PLANS.md`, `AGENTS.md`, and `claude-code/INSTALL.md` to the "Standard Docs" list.

`AGENTS.md`:

- Expanded "Key Files" to list `claude-code/` artifacts, `CHANGELOG.md`, `FUTURE-PLANS.md`, and `scripts/multiagent_files.py`.
- Split "Canonical vs Installed Copies" into Codex and Claude Code subsections with the actual install paths, and added a "Shared" subsection noting that `scripts/multiagent_files.py` is invoked from the repo path (not copied into either install root).
- Rewrote the "Verification" section to lead with `validate-install --platform {codex,claude-code}` rather than the inline Python snippet. The Python snippet is kept as a Codex-specific deeper check on skill-path references. Documented that Claude Code skip the path-list check (auto-discovery instead).
- Updated the launch-behavior maintenance rule to enumerate all three platform-launch surfaces (`launch/start-multiagent.md`, both `SKILL.md` files, the slash command) and reaffirm that `roles/pm.md`'s "Routing And Run Management" is the single source of truth.

### Why

The orchestrator-removal sweep changed the install model (one fewer agent, workers self-log) but `README.md` and `AGENTS.md` still spoke as if Codex were the only platform and `multiagent-orchestrator` were required. A new contributor reading the docs at the top of the tree would get a wrong mental model before reaching the Claude Code adapter.

`claude-code/INSTALL.md` did not exist; users had no install path documented for the platform we just built.

### Files affected

- New: `claude-code/INSTALL.md`
- Edited: `README.md`, `AGENTS.md`

### Reversal triggers

- If we add a third platform (Antigravity), the `README.md` "Choose Your Platform" table and `AGENTS.md` Canonical-vs-Installed split should extend with a third section rather than collapse back into platform-agnostic prose.
- If we ship a top-level `install.py` (Phase 8 optional), `INSTALL.md` should point at it as the recommended path and demote the manual copy commands to "if the script fails."

### Follow-ups (not done in this entry)

- Phase 8 step 4 (optional `install.py` with `--platform {codex,claude-code,both}`) is **not** built. Manual install via `INSTALL.md` is the only path today. Add the script if the manual commands become a friction point.
- Phase 6 (opt-in hooks) and Phase 9 (tests for Claude Code fixtures) are still pending per `IMPLEMENTATION-PLAN.md`.

---

## 2026-06-29 — Phase 5: `/multiagent` slash command

### Decision

Created `claude-code/commands/multiagent.md`. When the user types `/multiagent <task>`, the command body is injected as a user message. The body:

- Delegates to the `multiagent-workflow` skill as the canonical operating doc — no duplication of routing logic.
- Reaffirms the PM-as-main-session contract (confirmed by the user) so a future Claude reading the command body doesn't accidentally spawn a `pm` subagent for the interactive workflow.
- Passes `$ARGUMENTS` through as the initial client request. Empty args → ask the client what they want; do not assume a task.
- Provides quick-reference launch steps and the parallel-spawn / `run_in_background` patterns.
- Includes install fallback (`cp` and `Copy-Item` variants) for the case where the skill or agent files aren't yet copied into `~/.claude/`.
- Explicitly notes that `multiagent-orchestrator` is deliberately absent from the active set.

### Why

Slash command is a UX shortcut, not a second source of truth. Keeping it thin (delegate to skill, pass args, link install steps) means the only place routing/escalation logic lives is `roles/pm.md` + `claude-code/agents/pm.md` + the skill body — three documents that stay in sync rather than four.

The install-fallback section was added because the slash command is the first thing a new user types after `/multiagent`. If the skill isn't installed, the command body itself needs to teach the user how to fix it.

### Files affected

- New: `claude-code/commands/multiagent.md`

### Reversal triggers

If the autonomous-loop scenario in `FUTURE-PLANS.md` is built, the slash command needs a flag or alternate name (`/multiagent-autonomous`?) that triggers the spawn-orchestrator path instead of the adopt-PM path.

### Follow-ups (not done in this entry)

- Phase 8 (`claude-code/INSTALL.md`) should document `cp claude-code/commands/multiagent.md ~/.claude/commands/multiagent.md` (plus the PowerShell `Copy-Item` variant) alongside the agent and skill install steps.

---

## 2026-06-29 — Phase 4: Claude Code multiagent-workflow skill

### Decision

Created `claude-code/skill/multiagent-workflow/SKILL.md` as the Claude Code variant of the workflow-launch skill. Frontmatter declares trigger phrases; body is a thin entry-point that tells the main Claude Code session to **adopt PM's role** by reading `~/.claude/agents/pm.md`, rather than spawning a separate `pm` subagent.

Design choices:

- **Main session = PM** (not "main session spawns PM"). The skill body explicitly instructs the main session to read PM's role doc and operate as PM. The spawnable `pm.md` agent file still exists, but is reserved for the autonomous-loop scenario in `FUTURE-PLANS.md`. This matches the user's stated intent that PM is the highest-authority agent and talks directly to the client.
- **Shorter than the Codex skill** because Claude Code has no "subagent recognition" failure mode the Codex skill has to work around. The Claude Code skill focuses on what's Claude-Code-native: `EnterPlanMode` as the client-approval gate, `TaskCreate` for state-machine visibility, `Agent` tool with `isolation: "worktree"` and `run_in_background: true`, parallel-spawn via multiple `Agent` calls in one turn.
- **Routing logic lives in PM's role doc, not the skill body.** The skill points at PM; PM owns the detail. This avoids duplicating the "Routing And Run Management" section from `roles/pm.md` / `claude-code/agents/pm.md`.
- **Memory pointer** for cross-session client context: `~/.claude/projects/<slug>/memory/`, not `.multiagent/runs/...`.
- **Troubleshooting section** covers the three failure modes specific to Claude Code: missing subagent types (need to copy agent files and restart), `multiagent_files.py` rejecting a role, and the autonomous-loop case where PM is itself a child agent.

### Why

The skill is the entry point for "run the multiagent workflow" on Claude Code. The earlier orchestrator-removal decision made PM the natural workflow driver; the skill needs to make that explicit so a future Claude session reading the skill body doesn't go hunting for a non-existent orchestrator agent.

Keeping the skill body thin (entry point + Claude-Code-native conventions) and delegating routing detail to PM's role doc prevents drift between two long documents.

### Files affected

- New: `claude-code/skill/multiagent-workflow/SKILL.md`

### Reversal triggers

If the autonomous-loop scenario in `FUTURE-PLANS.md` is implemented, this skill will need a companion entry point (or a `mode` parameter) that does spawn a separate orchestrator agent instead of adopting the PM role in the main session. The "Core Model" section explicitly calls this out as an interactive-workflow constraint.

### Follow-ups (not done in this entry)

- Phase 5: `claude-code/commands/multiagent.md` slash command, referenced by this skill but not yet created.
- Phase 8: `claude-code/INSTALL.md` should document the `cp claude-code/agents/*.md ~/.claude/agents/` step and the parallel `cp -r claude-code/skill/multiagent-workflow ~/.claude/skills/` step.
- The Claude Code `validate-install` path checks for `claude-code/skill/multiagent-workflow/SKILL.md` — that now exists, so future runs should pass. No script change needed.

---

## 2026-06-29 — Docs sweep and script fixes for orchestrator removal

### Decision

Apply the orchestrator-removal decision (see entry below) to the docs and tooling that still referenced the old role:

- Replaced "root/orchestrator," "the orchestrator," "PM/root orchestration" with "PM (main thread)" across `ORCHESTRATION.md`, `AGENTS.md`, `README.md`, `TEAM-WORKFLOW.md`, `COMMUNICATION-PROTOCOL.md`, `launch/start-multiagent.md`, `codex-skill/multiagent-workflow/SKILL.md`, `CODEX-CUSTOM-AGENTS.md`, and `skills/skill-catalog.md`.
- Kept `orchestrator` as a valid sender/recipient in `COMMUNICATION-PROTOCOL.md`'s message envelope for forward compatibility with the autonomous-loop scenario in `FUTURE-PLANS.md`, with an explanatory note.
- Dropped `multiagent-orchestrator` from the "expected installed agents" lists in subagent-recognition troubleshooting; noted that old installs may still show it (harmless).
- `scripts/multiagent_files.py`:
  - Added `developer-strong` to `VALID_MESSAGE_ROLES` so strong-tier workers can self-log without the temporary `--from-role developer` fallback flagged in the prior entry.
  - Added `developer-strong` to `DEFAULT_ROLES` so it appears in the team registry that `prepare-run` writes.
  - Removed `orchestrator` from `DEFAULT_ROLES` (it is not an active role) but retained it in `VALID_MESSAGE_ROLES`.
  - Removed `multiagent-orchestrator.{toml,md}` from `CANONICAL_AGENT_FILES` so `validate-install` no longer flags it missing. Old installs that still have the file pass validation.
  - Expanded PM's `artifact_scope` in `DEFAULT_ROLES` to include the run-folder bookkeeping artifacts (`run-summary`, `messages`, `transcripts`, `routing-notes`) that PM now owns.
  - Fixed the `run-summary.md` template's Agent IDs section to list `developer-strong` and drop `orchestrator`.
- `tests/test_multiagent_files.py`:
  - Updated the registry-roles expectation to the new active-role list.
  - Fixed a pre-existing bug where `CANONICAL_AGENT_FILES` was iterated as a tuple after it had been promoted to a dict — now iterates `["codex"]` and passes `platform="codex"` to `validate_install`.
  - Added a test confirming `developer-strong` can self-log via `append-message`.
  - Added a test confirming `orchestrator` is still accepted as a sender for forward compatibility.
- All 6 tests pass.

### Why

The orchestrator-removal decision below changed role responsibilities but left dozens of stale references in the docs. A stale reference is worse than no reference because it teaches the wrong mental model to anyone (human or agent) reading the docs to bootstrap on the system. Sweeping them now while context is fresh is cheaper than letting them rot.

The script changes correct two real bugs the prior entry only flagged:
- `developer-strong` was in `CANONICAL_AGENT_FILES` but not in `VALID_MESSAGE_ROLES`, so a strong-tier worker following the self-logging instruction would fail.
- `CANONICAL_AGENT_FILES` had silently become a dict but the test was still iterating it as a tuple, masking validation regressions.

### Files affected

- Docs: `ORCHESTRATION.md`, `AGENTS.md`, `README.md`, `TEAM-WORKFLOW.md`, `COMMUNICATION-PROTOCOL.md`, `launch/start-multiagent.md`, `codex-skill/multiagent-workflow/SKILL.md`, `CODEX-CUSTOM-AGENTS.md`, `skills/skill-catalog.md`.
- Script: `scripts/multiagent_files.py`.
- Tests: `tests/test_multiagent_files.py`.

### Reversal triggers

Same as the entry below — if we bring back a spawnable orchestrator for autonomous loops, the docs should describe both roles (PM for interactive, orchestrator for autonomous) without conflating them.

### Follow-up cleanup (done in this entry)

- Removed the "temporary `--from-role developer` fallback" note from `roles/developer-strong.md`, `codex-agents/developer-strong.toml`, and `claude-code/agents/developer-strong.md` now that `developer-strong` is a valid message role.

---

## 2026-06-29 — Remove spawnable orchestrator agent; PM absorbs mechanical routing

### Decision

- Delete `claude-code/agents/multiagent-orchestrator.md` (was created but never shipped to `~/.claude/agents/`).
- Deprecate `codex-agents/multiagent-orchestrator.toml` with a header note. File is kept on disk for backward compatibility with any existing Codex install that already references it. Safe to delete after a verified migration cycle.
- Move the orchestrator's mechanical responsibilities (run-folder creation, tier-based spawning, escalation catch-and-respawn, parallel spawning, workflow-state tracking, run closeout) into the PM role's "Routing And Run Management" section in `roles/pm.md`. PM is the natural main-thread agent and already owns the highest authority; mechanical routing is bookkeeping that doesn't need a separate agent.
- Move worker message-logging responsibility into each worker role. Developer, Developer-Strong, Reviewer, and Reviewer-Strong now self-log via `python scripts/multiagent_files.py append-message ...` before returning their handoff. Previously the orchestrator was the central scribe.

### Why

A coordinator role in a human company exists because humans can't see each other's state, forget to forward messages, and need someone to chase them. In an agent workflow with a well-defined protocol (`COMMUNICATION-PROTOCOL.md`) and structured artifacts (`task-packet.md`, `implementation-report.md`, `review-report.md`), those failure modes don't apply:

- Agents don't forget — they're spawned with the packet and return when done.
- Messages don't get lost — they're returned as the agent's output and the parent saves them.
- There's no political friction to mediate.

What remained for the orchestrator was bookkeeping (run folder, message persistence, respawn on escalation, state tracking). Bookkeeping doesn't need its own agent; it needs a script (`scripts/multiagent_files.py`) and a few instructions in PM and the workers.

The judgment calls (which tier to spawn) belong to PM (`Suggested Developer Tier` in the task packet) and Developer (`ESCALATE_TO_STRONG_DEVELOPER` self-escalation), not to a generic coordinator. Asking the orchestrator to "decide" the tier was an unnecessary intermediate authority.

Original design (recorded here so it's not lost): PM is the main thread that talks to the user with the highest permission. Codex originally suggested the orchestrator role, and we created it without verifying it solved a real problem. In practice on Codex it was never spawned — the main Codex thread absorbed the role implicitly. Making that explicit and removing the redundant agent is the cleanup.

### Files affected

- Deleted: `claude-code/agents/multiagent-orchestrator.md`
- Deprecated (header note added): `codex-agents/multiagent-orchestrator.toml`
- Edited (added "Routing And Run Management"):
  - `roles/pm.md`
  - `codex-agents/pm.toml`
  - `claude-code/agents/pm.md`
- Edited (added "Persist Your Own Messages"):
  - `roles/developer.md`, `roles/developer-strong.md`, `roles/reviewer.md`
  - `codex-agents/developer.toml`, `codex-agents/developer-strong.toml`, `codex-agents/reviewer.toml`, `codex-agents/reviewer-strong.toml`
  - `claude-code/agents/developer.md`, `claude-code/agents/developer-strong.md`, `claude-code/agents/reviewer.md`, `claude-code/agents/reviewer-strong.md`
- Edited (open question resolved): `claude-code/IMPLEMENTATION-PLAN.md`

### Reversal triggers

Bring a spawnable orchestrator agent back if any of these become real needs:

- **Fully autonomous loops** (e.g., `CronCreate` / `ScheduleWakeup` fires a session with no human in the chat thread). PM-as-main-thread can't exist there because there's no conversation; a spawnable orchestrator is needed to drive the workflow from a fresh session.
- **Deep agent nesting** where PM (as a child agent) hits platform nesting limits and cannot spawn workers itself. The main thread would then spawn a dedicated orchestrator and delegate routing to it.
- **Multi-PM concurrent runs** where several PMs are active and need a higher-level coordinator to assign work between them.

See `FUTURE-PLANS.md` → "Deferred: Spawnable Orchestrator For Autonomous Loops" for the implementation outline.

### Follow-ups (not done in this entry)

- `ORCHESTRATION.md`, `AGENTS.md`, `README.md`, `TEAM-WORKFLOW.md`, `COMMUNICATION-PROTOCOL.md`, `launch/start-multiagent.md`, `codex-skill/multiagent-workflow/SKILL.md`, `CODEX-CUSTOM-AGENTS.md`, and `skills/skill-catalog.md` still reference the orchestrator. They should be swept in a follow-up edit. Do not edit them silently — preserve the historical mentions in `docs/superpowers/plans/*` and `docs/superpowers/specs/*` as design history.
- `scripts/multiagent_files.py`: `CANONICAL_AGENT_FILES` still includes `multiagent-orchestrator.toml` / `multiagent-orchestrator.md`. Decide whether to remove from the canonical set or keep as optional, and update `validate-install` accordingly.
- `scripts/multiagent_files.py`: `VALID_MESSAGE_ROLES` is missing `developer-strong`. With workers now self-logging, `developer-strong` cannot pass `--from-role developer-strong` through validation. Add it.
- `tests/test_multiagent_files.py`: update fixtures for the canonical-set and valid-role changes above.
