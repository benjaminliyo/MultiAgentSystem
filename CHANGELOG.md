# Changelog

Append-only decision log for architectural and role-level changes to the MultiAgentSystem. Different from a release changelog — this is the durable record of *what we changed and why*, so future contributors (and future agents on Codex, Claude Code, or other platforms) can understand the current shape of the system without re-deriving the reasoning.

## How To Use This File

- **Reverse chronological.** Newest entries at the top.
- **One entry per decision**, not per file edit. Group related file changes under a single dated decision.
- **Required sections per entry**: `Decision`, `Why`, `Files affected`, `Reversal triggers` (what conditions would make us undo this).
- **Forward-looking work goes in `FUTURE-PLANS.md`**, not here. Cross-link with a `See also:` line if the decision defers something.
- **Don't edit past entries.** If a later decision overrides an earlier one, write a new entry that names the prior entry it supersedes.

## 2026-07-04 — Install scripts tolerate Python 3.8 (backported from a university-server deployment)

### Decision

Make the install/validate tooling run on older Python interpreters instead of hard-requiring 3.11: `scripts/_common.py` falls back to the third-party `tomli` package when the stdlib `tomllib` (3.11+) is missing, and `scripts/install.py` gains a `_removesuffix()` polyfill replacing `str.removesuffix()` (3.9+). Tests use the same polyfill and fallback. Python 3.11+ remains the recommended baseline; on older interpreters without `tomli`, installs still work but TOML validation and Codex skill scoping degrade to warnings, and the warning text now names `pip install tomli` as the remedy.

### Why

A deployment of this repo on a university server (system Python 3.8) failed at install on `str.removesuffix` and lost TOML validation to the missing `tomllib`. The fix was applied on that copy and proven there; this entry backports it so the canonical repo installs anywhere a shared/cluster machine pins an old system Python. Both changes are behavior-identical on modern interpreters: the `tomllib` import still wins on 3.11+, and the polyfill matches `str.removesuffix` semantics.

### Files affected

- `scripts/_common.py` — `tomli` fallback in the `tomllib` import; `parse_toml` error message names the `tomli` remedy.
- `scripts/install.py` — `_removesuffix()` helper replaces three `str.removesuffix()` call sites; two `tomllib unavailable` warnings name the `tomli` remedy.
- `tests/test_multiagent_files.py` — `from __future__ import annotations`, polyfill at nine call sites, `tomli` fallback in the overlay TOML-validity test.
- `README.md` — install prerequisite note updated.

### Reversal triggers

- If the tooling later adopts a genuinely 3.11-only feature (so old-interpreter support is no longer honest), drop the polyfills and restore the hard 3.11+ requirement in the same change.

---

## 2026-07-04 — Thin the workflow skills; routing detail lives only in the PM role

### Decision

Rewrite the three `multiagent-workflow` SKILL.md files (Claude Code, Codex, Antigravity) to cover only launch, entry points (`/multiagent`, `off`, `resume`), platform constraints, troubleshooting, and (Claude Code) the done standard. All routing detail — spawn tiers and escalation respawns, worktree/workspace isolation, parallel spawning, state tracking, worker self-logging, plan-mode gating, closeout, resume mechanics — is stated once, in the PM role file each skill tells the session to adopt, and the skills point at it instead of restating it. `claude-code/commands/multiagent.md` was retitled accordingly: the PM role file is the canonical operating doc for the run; the skill is the launch doc.

### Why

The skills had drifted into near-full duplicates of the PM role's "Routing And Run Management" section (Claude Code skill: 136 lines, ~60 of them routing detail also present in the installed `pm.md`). Because each skill instructs the session to adopt the role file, PM held **both** copies in context at runtime — double the tokens for the same instructions, and two wordings of every rule to keep in sync (the four-file fan-out tax was paid twice on every routing change). `AGENTS.md` already mandated the fix: "PM's 'Routing And Run Management' section in `roles/pm.md` is the single source of truth for routing detail — keep platform docs thin and pointed at it."

What stays in the skills is exactly what must work before or without the role text: root-session adoption instructions (with the role file's path), the Scoped Autonomy preflight wording, `prepare-run` invocation and what PM-mode activation does, entry-point handling, platform launch constraints (Codex model policy and PM Adoption Shape; Antigravity's root-session permission-boundary warning, now surfaced at preflight so the client can relaunch with `--dangerously-skip-permissions` before the run starts), and troubleshooting. Codex kept the exact strings pinned by `test_codex_interactive_workflow_keeps_pm_in_root_session`.

### Files affected

- `claude-code/skill/multiagent-workflow/SKILL.md` — 136 → ~80 lines; cut Plan-Mode Contract, Spawning Developer/Reviewer/Researcher, Parallel Spawning, Worker Self-Logging, Closeout, Resume detail, and Memory sections (all present in `claude-code/agents/pm.md`); merged Slash Command/Deactivation/Resume into an "Entry Points" section.
- `codex-skill/multiagent-workflow/SKILL.md` — 112 → ~95 lines; Launch Flow steps 9–19 and the Researcher paragraph collapsed into one deferral step; adoption step now names `~/.codex/agents/pm.toml` explicitly.
- `antigravity/skill/multiagent-workflow/SKILL.md` — 93 → ~60 lines; cut the approval-gate, spawning, parallel, self-logging, and closeout sections (all in `antigravity/agents/pm.md`); dynamic-registration mechanics deferred to the role with the permission warning moved into the preflight step.
- `claude-code/commands/multiagent.md` — two sentences updated so references match ("the PM role file is the canonical operating doc"; detail pointer now names the role's routing section).

### Reversal triggers

- If a platform's role file stops being reliably loadable at launch (e.g., a runtime that cannot read `~/.claude/agents/` / `~/.codex/agents/` / `~/.gemini/config/agents/` from the session), that platform's skill must become self-contained again.
- If launch-time failures show sessions skipping role adoption and improvising routing, restore an abbreviated routing checklist to the affected skill rather than the full duplicate.

---

## 2026-07-04 — PM gains Client Calibration for non-technical clients

### Decision

Add a "Client Calibration" section to the PM role (`roles/pm.md` and the three embedded platform copies). PM gauges the client's technical fluency from their first messages and, for a non-technical client: treats a proposed solution as a symptom and recovers the underlying problem first (XY-problem handling); elicits constraints novices cannot volunteer (scale, hosting, cost, privacy) in their terms; offers product-level options in consequence terms with a recommended default; explains any technical choice that reaches the client with a consequence-terms reason ("we'll cap each person's daily usage so nobody can accidentally run up the bill"), not mechanisms; states consequences instead of asking "do you understand?"; and gates the task packet behind a plain-language brief — the packet is PM's translation of the approved brief, so the client never approves packet jargon. One new anti-pattern: do not ask the client to approve something they cannot evaluate.

### Why

The existing discovery workflow (restate → clarify → options → confirm) implicitly assumed a client who can answer PM-shaped questions. A non-technical client with a vague idea or a wrong proposed approach cannot state acceptance criteria, weigh tradeoffs phrased in engineering vocabulary, or meaningfully approve a jargon packet — they approve reflexively and product ambiguity survives "approval," defeating the Readiness Standard.

Calibration is deliberately instruction-level: no new agent, mode, or workflow state. `pm_discovery` already permits arbitrarily long discovery, and PM-mode reinjection plus `active-run.json` already make it survivable, so the gap was conversational technique, not machinery. The consequence-terms reason is a soft rule keyed on the existing client boundary (Escalation Rules): it applies only to choices that reach the client anyway, so it adds no narration burden for choices the client never sees. Authority is unchanged — PM proposes, the client decides, and implementation parts (which database, which framework) stay with Developer.

### Files affected

- `roles/pm.md` — new "Client Calibration" section between Workflow and Readiness Standard; new Anti-Patterns line.
- `claude-code/agents/pm.md` — same section and anti-pattern line; "Plan Mode As Client-Approval Gate" now leads the plan content with the plain-language brief for non-technical clients.
- `antigravity/agents/pm.md` — same section with the anti-pattern line folded into its closing paragraph (file has no Anti-Patterns section); same plan-gate lead-with-brief line.
- `codex-agents/templates/pm.toml` — condensed "Client calibration:" block between Workflow and Readiness standard, anti-pattern line folded in.

### Reversal triggers

- If the calibration bullets make PM over-explain to technical clients or drag out discovery, shrink the section to two rules: the plain-language brief gate and the "do not ask the client to approve what they cannot evaluate" anti-pattern.
- If novice-client discovery turns out to need real machinery (a dedicated brief artifact type in `COMMUNICATION-PROTOCOL.md`, a mockup/prototype loop, or a discovery sub-state), write a superseding entry with that design instead of growing the role text further.

---

## 2026-07-04 — Codex interactive workflow adopts PM in the root session

### Decision

Codex's `multiagent-workflow` skill and copy/paste launch prompts now tell the main Codex session to adopt PM's role for the interactive workflow instead of spawning the `pm` custom agent as a separate child subagent. The `pm.toml` file remains installed as role reference and for the future autonomous-loop scenario, but normal interactive routing spawns only Developer, Reviewer, and optional Researcher workers.

### Why

Live Codex testing showed that launching PM as a spawned custom agent makes PM a normal agent thread that can be stopped or closed mid-session. That contradicts the PM-led design: PM mode should persist through long sessions and interruptions until the user explicitly turns the workflow off (`/multiagent off`) or PM runs `close-run`. The existing helper lifecycle already supports the sticky design via `.multiagent/active-run.json`, marker blocks, and project hooks; the regression was in Codex-specific launch wording.

### Files affected

- `codex-skill/multiagent-workflow/SKILL.md` — root-session PM adoption is now the core rule; worker spawning and troubleshooting were rewritten around that contract.
- `launch/start-multiagent.md`, `launch/start-pm-only.md` — copy/paste prompts no longer request a spawned PM child.
- `CODEX-CUSTOM-AGENTS.md`, `codex-agents/INSTALL.md`, `README.md` — Codex setup and troubleshooting now distinguish sticky PM mode from spawned worker agents.
- `tests/test_multiagent_files.py` — added a regression test that rejects the old Codex PM-spawn instructions.

### Reversal triggers

- If Codex adds a durable non-closable "main-thread custom agent" mode that can adopt `pm.toml` directly while retaining root-session routing and PM-mode lifecycle hooks, the interactive workflow can switch to that platform primitive.
- If the autonomous-loop orchestrator is reintroduced, it may spawn PM as a child for non-interactive background runs only; that must remain separate from the interactive root-session PM workflow.

---

## 2026-07-03 — Antigravity root-session interception limits subagent permissionMode

### Decision

Keep the installer's `permissionMode: plan` → `bypassPermissions` transformation, and document two Antigravity platform constraints discovered in live testing instead of reverting it. This entry qualifies (does not reverse) the prior entry "Automated Antigravity subagent permission configuration for Scoped Autonomy" below.

1. **`define_subagent` discards `permissionMode`.** The dynamic-registration tool accepts only `name`, `description`, `system_prompt`, and the `enable_*_tools` flags. Frontmatter permission modes are honored only for agents statically discovered from `~/.gemini/config/agents/` at session start; the self-healing dynamic-registration path silently drops them.
2. **Root-session interception.** Subagent tool calls execute inside the root session's permission boundary. When the root session runs in interactive confirmation mode (the default), it intercepts and prompts for subagent commands regardless of any agent-level permission mode.

Full subagent autonomy on Antigravity therefore additionally requires launching the root session with `agy --dangerously-skip-permissions`. This is documented as a deliberate opt-in, **not** a recommended default: the flag auto-approves every tool call for the entire session, including actions outside the Scoped Autonomy envelope.

### Why

The frontmatter rewrite remains load-bearing on the static discovery path — a statically loaded worker carrying `permissionMode: plan` still behaves like a planner even when the root session bypasses prompts — and it is harmless on the dynamic path, where any mode would be discarded anyway. It also becomes fully effective if a future Antigravity version adds `permissionMode` to `define_subagent` or parent-mode inheritance. Reverting would restore the worker-side plan gate for no safety gain, since canonical files in git still ship `permissionMode: plan`.

### Files affected

- `antigravity/INSTALL.md` — "Permission Configuration & Scoped Autonomy" reworked: root-session constraint, opt-in `--dangerously-skip-permissions` usage with an explicit risk warning.
- `AGENTS.md`, `CLAUDE.md` — Antigravity install notes state the session-level constraint as a documented opt-in, not a recommendation.
- `antigravity/agents/pm.md`, `antigravity/skill/multiagent-workflow/SKILL.md` — self-healing registration notes updated with the root-session constraint so PM can surface it to the client.
- `CHANGELOG.md` — this entry.

### Reversal triggers

- If a future Google Antigravity version honors `permissionMode` for dynamically registered subagents or inherits the parent grant, remove the `--dangerously-skip-permissions` guidance and rely on the installer transformation alone.
- The prior entry's reversal triggers remain in force for the installer transformation itself.

---

## 2026-07-03 — Automated Antigravity subagent permission configuration for Scoped Autonomy

### Decision

1. **Automated subagent permission mode translation.** The installer (`scripts/install.py`) will automatically substitute `permissionMode: plan` with `permissionMode: bypassPermissions` for all Antigravity subagents (`developer`, `developer-strong`, `reviewer`, `reviewer-strong`, `researcher`) during `install_antigravity` (unless the new override flag `--antigravity-subagent-permission-mode plan` is passed). PM (`pm.md`) retains `permissionMode: plan` as the client-approval gate.
2. **Dynamic subagent registration (self-healing) permission alignment.** Updated `antigravity/agents/pm.md` and `antigravity/skill/multiagent-workflow/SKILL.md` to explicitly instruct the PM agent and the workflow skill to register subagents using `bypassPermissions` during dynamic (`define_subagent`) self-healing registration, matching the mode used by installed configuration copies, even if they fall back to canonical repo/workspace copies that still declare `permissionMode: plan`.
3. **Strict substitution checking.** The installer now checks that the target `permissionMode: plan` occurs exactly once in each subagent file before replacement, raising a warning on mismatch to prevent silent installation failures if agent frontmatter files are edited in the future.
4. **Documentation and upgrade guidance.** Added the new design to `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`, and `README.md`. Instructed existing users to re-run the installer.

### Why

The MultiAgentSystem is conceptually designed around Scoped Autonomy, where the client grants permission once at the beginning of a run to the PM, and workers execute tasks autonomously without per-action prompts. However, the canonical templates checked into git must keep `permissionMode: plan` as a repository safety baseline to prevent downloaded repos from immediately executing code. Automated transformation during installation resolves this contradiction, while updating the dynamic self-healing path prevents stale installs or dynamic fallbacks from silently reintroducing the per-action confirmation prompts.

### Files affected

- `scripts/install.py` — `install_dispatch`, `install_antigravity`, CLI parser changes, strict count checks, and returning `switched_permissions`.
- `antigravity/agents/pm.md` — PM self-healing instructions updated under "Routing And Run Management".
- `antigravity/skill/multiagent-workflow/SKILL.md` — workflow skill self-healing instructions updated.
- `antigravity/INSTALL.md` — new "Permission Configuration & Scoped Autonomy" section added with upgrade note.
- `AGENTS.md`, `CLAUDE.md` — documented the transformation under "Canonical vs Installed Copies → Google Antigravity".
- `README.md` — comparison table updated for Antigravity plan-mode gate.
- `CHANGELOG.md` — this entry.

### Reversal triggers

- If a future Google Antigravity version provides built-in parental permission inheritance for subagents, restore `permissionMode: plan` across all worker agents and rely on the native inheritance feature.
- If users prefer prompt confirmation for all subagent tool calls, they can pass `--antigravity-subagent-permission-mode plan` during installation.

---

## 2026-07-03 — Release-readiness pass: runtime state untracked, copyable docs made portable

### Decision

Pre-publication cleanup before the first GitHub release, driven by an external review (Codex) plus a final local audit:

1. **`.multiagent/team-registry.json` is runtime state, not tracked source.** It is generated by `ensure_registry` during `prepare-run` and the tracked copy had already drifted (missing `researcher`). Untracked it and gitignored it together with `.multiagent/active-run.json`; `.multiagent/runs/` was already ignored. Only `project-profile.md` remains a tracked-eligible file under `.multiagent/`.
2. **`.claude/settings.local.json` added to the repo `.gitignore`.** It was previously invisible only via this machine's *global* git ignore, so a clean clone plus `git add .` on another machine would have published local Claude Code permission entries.
3. **Copyable docs no longer hardcode the maintainer's absolute checkout path.** `COMMUNICATION-PROTOCOL.md`, `ORCHESTRATION.md`, and README's validate-install examples now use the `<MULTIAGENT_REPO>` placeholder (the convention `codex-skill` already used) or `--repo-root .`. `claude-code/settings.example.json` keeps absolute example paths deliberately — hooks require absolute paths and the file's `_comment_paths` says to adjust them.
4. **README repo tree now matches a clean checkout.** `codex-agents/` shows `templates/*.toml` as canonical with generated top-level TOMLs marked gitignored; removed the absent `multiagent-orchestrator.toml` and `claude-code/IMPLEMENTATION-PLAN.md`; added the missing `reviewer-strong.md`/`researcher.md` to the `roles\` tree; tree root is now `MultiAgentSystem\`.
5. **Researcher added to two stale role lists.** README's self-logging roles sentence and `skills/find-skill.md`'s tier-2 worker list both omitted Researcher, which self-logs and can send `skill_need` per `roles/researcher.md`.

### Why

First-time users judge a repo by whether the README matches what they cloned and whether examples run without editing someone else's paths. Tracking runtime-generated files guarantees staleness (the registry drift proved it), and relying on a global gitignore for local settings is a per-machine accident, not a repo property.

### Files affected

- `.gitignore` — `.multiagent/team-registry.json`, `.multiagent/active-run.json`, `.claude/settings.local.json`.
- `.multiagent/team-registry.json` — untracked (`git rm --cached`); local copy regenerated with the current six roles.
- `README.md` — repo tree, self-logging roles, validate-install examples.
- `COMMUNICATION-PROTOCOL.md`, `ORCHESTRATION.md` — `<MULTIAGENT_REPO>` placeholder.
- `skills/find-skill.md` — Researcher in the tier-2 worker list.

### Reversal triggers

- If `team-registry.json` becomes user-editable per-project config rather than generated output, track a template for it instead of ignoring it.
- If a shared project-level `.claude/settings.json` is ever added, keep the ignore scoped to `settings.local.json` only (it already is).

---

## 2026-07-03 — Codex researcher permission profile; installed-copy drift validation

### Decision

Follow-up hardening pass on the researcher role (see the entry below) after per-platform verification by the Codex and Antigravity sessions:

1. **Mechanical permission profile for the Codex researcher.** `codex-agents/templates/researcher.toml` now carries `default_permissions = "researcher"` with a filesystem profile (workspace read-only, `.multiagent` write — its run-folder logging surface) and `network.enabled = false`. This turns the researcher's read-only contract from instruction-following into mechanical enforcement on Codex; the prompt stays unchanged as the behavioral contract. Cross-platform status: the researcher's no-write contract was *already* mechanical on the other two platforms through their native surfaces — Claude Code's `tools:` frontmatter omits Edit/Write (and WebFetch/WebSearch), Antigravity's frontmatter sets `enable_write_tools: false` — so Codex was the only platform with no mechanical layer, and this profile closes that. Filesystem granularity (`.multiagent`-only write) and the network toggle remain Codex-only: neither Claude Code nor Antigravity supports per-agent filesystem or network scoping, and on Claude Code the researcher keeps Bash (needed for inspection commands and `append-message`), which stays a shell-level write/network escape hatch covered by the instruction layer. Codex is now the strictest platform. **The Codex profile is deliberately researcher-only:** PM and Developer need write access; Reviewer (both tiers), though no-file-edits by contract, runs verification commands that mutate the workspace (bytecode caches, build/test artifacts), so a *filesystem-level* read-only profile would break its core job. Known caveat, Codex-specific: `network.enabled = false` conflicts with the researcher prompt's repository-history guidance for *remote* context — local `git log`/`blame` works, fetching GitHub PR/issue data does not; the researcher should route that need to PM.

2. **Antigravity reviewer tiers flipped to `enable_write_tools: false`.** Reviewing the cross-platform picture surfaced an inconsistency: Claude Code's reviewer/reviewer-strong already mechanically lack Edit/Write, but the Antigravity counterparts shipped `enable_write_tools: true`, leaving their no-file-edits contract instruction-only. Flipped both to `false`. This is safe where the Codex filesystem profile is not, because Antigravity's toggle gates write *tools* only — terminal commands (test runs, `append-message` logging) are unaffected, which is exactly the granularity the reviewer needs; the Antigravity researcher already runs verified with the same setting.

3. **Codex validate-install now detects drift.** `_validate_install_codex` in `scripts/install.py` parses each installed TOML (flagging malformed files) and flags installed agent files that differ from the generated repo copies (`codex-agents/*.toml`). Previously an installed agent could be stale after a template change (installer not re-run) or hand-edited, and validation still passed.

4. **Docs and tests.** `codex-agents/INSTALL.md` updated to say 6 roles and list `researcher`. `CODEX-CUSTOM-AGENTS.md` documents the researcher profile as the exception to Scoped Autonomy. Regression tests added for the malformed-installed-agent and install-drift cases plus the template permission block; the Codex-fixture builder was extended to emit the researcher permission block, and one assertion was made case-insensitive to match validator output. 62 tests pass; all three platform validators report `complete: true` with no warnings. Codex agents were regenerated and redeployed to `~/.codex` (restart Codex to pick them up).

### Why

The system's standing principle (2026-07-02 entry): anything the workflow *requires* should be mechanical, not instruction-following. The researcher entry below established read-only as a design constraint, but Codex enforced none of it mechanically — the TOML carried only model fields, so the contract was pure prompt text there, while Claude Code (tool list) and Antigravity (`enable_write_tools`) already had a mechanical layer. Each platform now carries the maximum enforcement its config surface supports, and the reviewer flip removes the one remaining cross-platform asymmetry that was free to fix. The drift check closes the matching validation gap: "installed files exist" is a much weaker invariant than "installed files are what the installer would produce today."

### Files affected

- `codex-agents/templates/researcher.toml` — permission profile block.
- `antigravity/agents/reviewer.md`, `antigravity/agents/reviewer-strong.md` — `enable_write_tools` flipped to `false`.
- `scripts/install.py` — installed-TOML parse + drift checks in `_validate_install_codex`.
- `codex-agents/INSTALL.md` — role count and researcher listing.
- `CODEX-CUSTOM-AGENTS.md` — researcher profile documented under "Model And Permission Defaults".
- `tests/test_multiagent_files.py` — new regression tests + fixture updates (62 total).

### Verified

- 62 tests pass; `validate-install` reports `complete: true` with no warnings on all three platforms.
- Live Codex smoke test (2026-07-03): a real sandboxed `researcher` spawn executed the canonical helper from the repo path (outside its declared workspace root — the open question at review time) and wrote + indexed a message under `.multiagent/runs/2026-07-03-codex-researcher-smoke-test/` (MSG-20260703-001). The `.multiagent` write carve-out covers the full logging path and **no extra repo-path read root is needed** in the permission profile. Cleanup state confirmed clean afterwards (no `active-run.json`, no leftover marker blocks).
- Logging is unaffected on the other platforms by construction: Antigravity's `enable_write_tools` gates file-write *tools* only, and `append-message` runs through terminal command execution; Claude Code agents log through Bash, which they all keep.

### Reversal triggers

- If Codex permission profiles gain finer granularity (e.g. allow cache/temp writes under a read root), revisit giving Reviewer a mechanical profile too — the contract already wants it.
- If the Antigravity reviewer turns out to need a write tool for a legitimate deliverable (its logging and test runs go through terminal commands, so none is expected), flip `enable_write_tools` back and record what needed it.
- If `network.enabled = false` blocks legitimate exploration (remote PR/issue context requested often) more than it prevents drift, enable network read-only or scope allowed hosts, and update the caveat in `CODEX-CUSTOM-AGENTS.md`.
- If the byte-for-byte drift comparison starts false-failing because the installer legitimately writes machine-varying content beyond what it writes to the repo copy, relax the check to structural comparison.

---

## 2026-07-03 — Optional read-only Researcher agent; permission-aware context-update overlays

### Decision

1. **New optional `researcher` role.** A read-only exploration specialist PM spawns on demand: during `pm_discovery` on a large or unfamiliar codebase before drafting the task packet, or mid-run when Developer/Reviewer sends the new `exploration_request` message. It maps architecture, locates relevant code, traces flows, and answers PM's focus questions, returning a structured `exploration_report` (new message type) it self-logs like every other worker. Design constraints, deliberately: no Edit/Write tools (its only write surface is run-folder messages via `append-message`); no strong tier (exploration is breadth-and-summarize work — efficient model: sonnet on Claude Code, `gpt-5.4-mini`/`medium` on Codex); no new workflow state (exploration runs inside the current state and may run in parallel with any worker since it is read-only). Named `researcher`, not `explorer`, to avoid collision with Claude Code's built-in `Explore` agent — which the researcher itself uses for fan-out sweeps. PM owns folding findings into `.multiagent/project-profile.md`, since the researcher cannot write.

2. **Permission-aware skill-edit rule.** Canonical read-only roles (reviewer both tiers, researcher) now carry an explicit instruction: when any invoked skill proposes file edits, do not apply them — capture the proposal in the report or a message to PM. The personal context-update overlays in `local/overlays/roles/` were reworked around the same write-permission split: Researcher/Reviewer detect-and-report only; Developer may apply drift fixes caused by its own current change but must notify PM before applying pre-existing/unrelated drift; PM may apply edits only after explicit client approval (typically at closeout). Genericized in `examples/personal-profiles/example-role-overlay.md`.

### Why

Understanding a large project is real work that previously either burned PM's main-thread context or leaked into Developer/Reviewer sessions that need their context for their own jobs. A dedicated read-only role makes exploration cheap, parallel, and durable (the report outlives the session). Read-only also surfaced a gap: skills that propose edits (like context-update) behaved identically for every role even though only Developer and PM can legitimately write — the overlay rework aligns skill behavior with each role's write authority and adds the Developer scope rule (own-change drift vs. old conflicts) so unrelated context edits always get PM/client eyes first.

### Files affected

- New: `roles/researcher.md`, `claude-code/agents/researcher.md`, `codex-agents/templates/researcher.toml`, `antigravity/agents/researcher.md`, `local/overlays/roles/researcher.md` (gitignored).
- `scripts/_common.py` (CANONICAL_AGENT_FILES), `scripts/multiagent_files.py` (DEFAULT_ROLES, VALID_MESSAGE_ROLES, run-summary agent list), `claude-code/hooks/subagent-log.py` (MULTIAGENT_ROLES), `skills/role-skill-map.toml` (`[roles.researcher]`), `tests/test_multiagent_files.py`.
- PM routing (`roles/pm.md` + three platform PM files): "Optional Researcher" section + message list. Worker message lists (`exploration_request`) in developer/reviewer files across platforms.
- `COMMUNICATION-PROTOCOL.md` (envelope, `exploration_request`/`exploration_report`, routing rule), `TEAM-WORKFLOW.md`, `ORCHESTRATION.md`, `README.md`, `CLAUDE.md`/`AGENTS.md`, `CODEX-CUSTOM-AGENTS.md`, both INSTALL.md files, three platform SKILL.md files, `claude-code/commands/multiagent.md`, `launch/start-multiagent.md`, `codex-skill/.../references/paths.md`, `docs/skills-framework.md`, `examples/personal-profiles/`.

### Reversal triggers

- If PM sessions routinely absorb exploration without context pressure (models with much larger effective context), the dedicated role may become overhead — fold it back into PM guidance.
- If the researcher is observed drifting into implementation or review work despite the read-only constraints, tighten or remove the role.
- If a strong-exploration need emerges repeatedly (very large monorepos where the efficient model produces shallow maps), revisit the no-strong-tier decision.

---

## 2026-07-02 — Local skill-map overlay, tier-1 trim, superpowers sub-skills, context-update dogfooding

### Decision

Four related changes to how personal skill setup layers over the shipped defaults:

1. **Local role-skill-map overlay.** New gitignored `local/role-skill-map.toml` merges **additively** over the tracked `skills/role-skill-map.toml` at install time (`load_role_skill_map` in `scripts/install.py`): local entries extend a role's candidates, never remove tracked ones; local-only roles are added whole; a broken local map warns and is skipped without disabling the tracked map. This is the channel for personal skills to reach Codex's hard allowlist and Claude Code's `skills:` frontmatter without entering version control — previously instruction-text overlays existed but had no way to affect skill *assignment*.

2. **Superpowers at sub-skill granularity in the tracked map.** Added `executing-plans` and `receiving-code-review` to both developer tiers and `define-goal` to PM. The map matches by skill directory name, and the Codex installer already scans `~/.codex/plugins/` recursively, so superpowers plugin sub-skills resolve without special-casing. Platforms without superpowers installed skip the candidates silently (Claude Code plans well natively; installing superpowers there is optional).

3. **Tier-1 baseline trimmed to process skills.** The personal local map carries only every-task skills (context-update for all roles; playwright/screenshot for developer; those plus playwright-interactive/security-best-practices for reviewer). Domain skills (figma, notion, framework, deploy, ticket skills) are deliberately excluded from tier 1 — they enter per-task via tier 0 (task packet) or mid-work via tier 2 (skill-installer), per the existing anti-pattern rule against checkbox tier-1 lists.

4. **Context-update dogfooding instruction + genericized examples.** The five `local/overlays/roles/*.md` now name the client's `context-update` skill concretely with a verify-and-report charter (did it trigger/stay quiet correctly, were edits accurate, report under `### context-update feedback`; false negatives additionally via `context_update_observation`). PM aggregates all feedback at closeout. Strong tiers keep the overlay deliberately: they *replace* the default agents on escalation, so dropping them would silently stop dogfooding on escalated work. The live personal inventories formerly shipped as `examples/personal-profiles/` moved to `local/personal-profiles/` (untracked); the examples directory now holds genericized illustrations of the local map + overlay pattern instead of one user's real setup.

### Why

The user's real skill setup was tracked in `examples/` (leaking personal config into the public repo), the tier-1 profiles had grown to 50+ skills per role (burying the always-relevant ones), and there was no version-control-safe way to give personal skills to Codex agents under the hard allowlist. The dogfooding rewrite makes the context-update feedback loop concrete and testable instead of generic "note anything that worked poorly".

### Files affected

- `scripts/install.py` — `merge_role_skill_maps`, `_merge_skill_map_section`, reworked `load_role_skill_map`.
- `tests/test_multiagent_files.py` — local-map merge + broken-local-map tests.
- `skills/role-skill-map.toml` — superpowers sub-skill and define-goal candidates.
- `local/role-skill-map.toml`, `local/overlays/roles/*.md`, `local/personal-profiles/`, `local/README.md` (gitignored).
- `examples/personal-profiles/` — README rewritten; five personal profiles removed; `example-local-role-skill-map.md` + `example-role-overlay.md` added.
- `CLAUDE.md` / `AGENTS.md`, `CODEX-CUSTOM-AGENTS.md`, `docs/skills-framework.md` — local-map documentation.

### Reversal triggers

- If additive-only merge proves too weak (a user needs to *remove* a tracked default per-role), add an explicit exclusion syntax rather than reverting the overlay.
- If the trimmed tier-1 baseline causes repeated tier-2 shopping trips for the same domain skill, promote that skill back into the relevant role's map (tracked or local as appropriate).

---

## 2026-07-02 — Sticky PM mode, resource acquisition (packages + role-skill map), local overlay, durable runs

### Decision

Four related design changes shipped together, all motivated by real-run failures:

1. **Sticky PM role + off switch.** The interactive workflow's PM adopts its role by reading `pm.md` as a tool result — the lowest-priority context tier, which fades over long sessions (workers never had this problem: their role file is their subagent system prompt). Now `prepare-run` *activates PM mode*: it writes `.multiagent/active-run.json` and inserts a `<!-- multiagent:begin/end -->` marker block into the project's context files (CLAUDE.md/AGENTS.md/GEMINI.md — system-prompt priority, survives compaction and fresh sessions). A new `user-prompt-pm-mode` hook reinjects a compact PM reminder with the live workflow state on every prompt while a run is active. New runtime subcommands: `set-state` (updates `run-summary.md` + `active-run.json` on every workflow transition) and `close-run` (terminal state, marker removal, `active-run.json` deletion — deletes context files that held nothing but our marker). `/multiagent off` deactivates; `/multiagent resume` reconstructs an interrupted run from the run folder. Codex gets the same hooks via a rendered project-level `.codex/hooks.json` (`prepare-run --project-hooks codex`); Antigravity wiring is manual via the `antigravity/hooks.json` template.

2. **Resource acquisition: packages + per-role skill scoping.** New "Environment Resolution" rules in the Developer roles: resolve the project's canonical env (project profile first, then `.venv`/conda/uv markers) before concluding a package is missing; verify against that env's interpreter; fix invocation when the package exists; send the new `package_need` message (or install within the run's pre-approved *package envelope*) when truly missing — never silent fallback, never bare `pip install`. PM's preflight now records the resolved env in the project profile and asks the client one package-envelope question. New `skills/role-skill-map.toml` is the editable per-role default skill list: Codex installer enforces it as a hard allowlist per generated TOML (replacing append-everything), Claude Code installer injects matched installed skills into the deployed agents' `skills:` frontmatter (verified: that field *preloads* full content but does not restrict discovery — which tier 2 depends on), Antigravity stays instruction-level.

3. **Personal content moved to a gitignored local overlay.** All context-maintenance skill references and the `context_update_observation` message type were personal setup and are stripped from canonical files. The installer now merges `local/overlays/roles/<role>.md` into the *installed* agent copies (appended to md bodies; inserted into the Codex TOML's `developer_instructions`). The validator check flipped: it used to warn when a canonical body *didn't* mention context-maintenance; it now warns when one *does* (publish cleanliness).

4. **Durable runs (mechanical logging + checkpoints + resume-any-run).** A real run died at a usage limit mid-implementation and lost worker progress; PM→Developer messages hadn't been saved because logging was instruction-following (and the instructions fade — see item 1). New `subagent-log.py` hook (`SubagentStart`/`SubagentStop`, which fire in the main session — main-session `PostToolUse` does not fire for subagent completion) mechanically appends every spawn/finish to `transcripts/subagent-events.jsonl` and the message log (`subagent_start`/`subagent_stop` types). Wired on all three platforms: Claude Code (settings.json), Codex (rendered `.codex/hooks.json` — Codex confirmed the events run `type: "command"` handlers), and Antigravity (rendered `.agents/hooks.json` — Antigravity has no SubagentStart/SubagentStop, so the logger hooks `PreToolUse`/`PostToolUse` with matcher `invoke_subagent`, the tool that spawns subagents; agent types are extracted from `tool_input.Subagents[*].TypeName`). Antigravity's per-turn PM reminder rides on `PreInvocation`, whose confirmed contract requires a flat JSON object on stdout (`additionalContext` is appended to the LLM context; plain text crashes the framework's JSON parser) — hence the JSON-emitting `user-prompt-pm-mode.py` variant alongside the plain-text `.ps1`/`.sh` used on Claude Code/Codex. Whether Antigravity applies the same JSON contract to `Stop` hook output is unconfirmed; documented in `antigravity/INSTALL.md`. Worker roles now require `progress_update` checkpoints at milestones, not just at handoff. `/multiagent resume [run-name]` resumes not only the interrupted run but any previous run: the new `activate-run` subcommand restores `active-run.json` + marker blocks for an existing run folder (closed runs included, with a warning to `set-state` before continuing). Stale "orchestrator" references in platform agent files were fixed to PM while editing.

Also: a consolidation pass on the role files (dedup, orchestrator-removal history reduced to one CHANGELOG pointer per file) so net length stayed roughly flat despite the new sections.

### Why

The client hit all four failure modes in real use (2026-07-02 session): PM forgot its role mid-session when `/multiagent` was invoked without an initial request; an agent silently skipped a plot-rendering step because a package was "missing" (it lived in a non-activated env); personal skill references were about to leak into the public GitHub repo; and a usage-limit death lost all subagent progress. The connecting principle: anything the workflow *requires* should be mechanical (hooks, marker blocks, generated configs), not instruction-following — instructions fade, hooks don't.

### Files affected

- `scripts/multiagent_files.py` — active-run lifecycle, marker upsert/removal, `set-state`, `close-run`, `--project-hooks` rendering.
- `scripts/install.py` — role-skill map loading + Codex per-role filtering, Claude `skills:` injection + `discover_claude_skills`, overlay merge for all three installers, five-hook wiring, `_validate_shared_repo_files`, flipped context-maintenance check.
- `claude-code/hooks/user-prompt-pm-mode.{ps1,sh}`, `claude-code/hooks/subagent-log.py` (new); `claude-code/settings.example.json` (five hook events).
- `codex/hooks.json`, `antigravity/hooks.json` (new templates); `skills/role-skill-map.toml` (new); `templates/messages/package-need-request.md` (new); `templates/messages/context-update-observation.md` moved to `local/overlays/templates/`.
- `roles/*.md`, `claude-code/agents/*.md`, `antigravity/agents/*.md`, `codex-agents/templates/*.toml` — new sections propagated; personal content stripped.
- `claude-code/commands/multiagent.md`, both platform `SKILL.md` files, `codex-skill/.../SKILL.md`, `launch/*.md` — off/resume, activation, preflight, closeout updates.
- `COMMUNICATION-PROTOCOL.md`, `ORCHESTRATION.md`, `TEAM-WORKFLOW.md`, `README.md`, `docs/skills-framework.md`, `CLAUDE.md`/`AGENTS.md`, `.gitignore`.
- `tests/test_multiagent_files.py` — 18 new tests (51 total).

### Reversal triggers

- If per-turn hook reinjection makes sessions noisy or conflicts with a future Claude Code role feature, drop the hook and rely on the marker block alone.
- If Codex's hard allowlist causes recurring "worker lacked a needed skill" failures despite the `[always]` escape hatch, revert `install_codex` to append-everything (one function).
- If a platform ships native per-agent skill restriction on Claude Code, replace the soft `skills:` preload approach with it.
- If the package envelope proves too permissive in practice (unwanted installs), route all `package_need` to the client unconditionally — the message flow already supports it.

## 2026-07-02 — Split scripts/multiagent_files.py into runtime + install modules

### Decision

Split the single `scripts/multiagent_files.py` module into three files by lifecycle:

- `scripts/multiagent_files.py` — **runtime** only. Called by PM/Developer/Reviewer agents during an active run. Exposes `prepare-run`, `append-message`, `status` CLI subcommands and the corresponding functions. Path unchanged so no agent doc, role file, skill doc, or template needs updating.
- `scripts/install.py` — **install-time** only. Called once per machine (via `scripts/install.ps1` / `scripts/install.sh` or directly) to set up a CLI platform and validate the result. Exposes `install --platform <name|all>`, `install-codex`, `install-claude-code`, `install-antigravity`, and `validate-install` CLI subcommands plus their functions.
- `scripts/_common.py` — shared constants (`CANONICAL_AGENT_FILES`, `SUPPORTED_PLATFORMS`) and low-level helpers (`MultiAgentFileError`, `require_dir`, `parse_toml`, `parse_frontmatter`, `copy_file`, `copy_tree`). Imported by both siblings. No CLI.

Both siblings prepend the project root to `sys.path` when invoked directly (via `if __package__ in (None, "")`) so `from scripts._common import ...` works whether the file is run as `python scripts/install.py` or imported as `from scripts import install`.

Shell wrappers `scripts/install.ps1` and `scripts/install.sh` now point at `install.py`.

Tests `tests/test_multiagent_files.py` were updated to import both `install` and `multiagent_files`, referencing install/validate functions through the new module (`install.install_codex(...)`, `install.validate_install(...)`, `install.CANONICAL_AGENT_FILES`, etc.). 33/33 tests still pass with no test logic changes.

Docs updated where they name the CLI path:

- `CLAUDE.md`, `AGENTS.md` — Key Files list now names all four scripts (`multiagent_files.py`, `install.py`, wrapper `.ps1`/`.sh`, `_common.py`); "Verification" section calls `scripts/install.py validate-install ...`; "Shared" section notes all three Python files stay in the repo.
- `README.md` — "Automation Helper" section splits into runtime vs install-time examples, each pointing at the right entry point.
- `codex-agents/INSTALL.md`, `claude-code/INSTALL.md`, `antigravity/INSTALL.md`, `antigravity/skill/multiagent-workflow/SKILL.md` — validator command paths flipped to `scripts/install.py validate-install ...`.

Supersedes the file-layout claims in the earlier 2026-07-02 entry ("One-command installer for Claude Code and Antigravity, plus install/update parity"), which described `install_claude_code`, `install_antigravity`, `install_dispatch`, `validate_install`, and `_wire_claude_hooks` as living in `scripts/multiagent_files.py`. Those functions now live in `scripts/install.py`; their signatures and behavior are unchanged, and no user-facing CLI entry point changes semantics (only their host module).

### Why

`multiagent_files.py` had two distinct lifecycles crammed into one file:

- **Runtime helpers** (`prepare-run`, `append-message`, `status`) called by agents *during* an active workflow. Blast radius of a bug: one run folder inside a project's `.multiagent/`.
- **Install helpers** (`install-*`, `validate-install`) called *once* on a user's machine to set up the CLI. Blast radius of a bug: user's home config (`~/.claude/settings.json`, `~/.codex/`, `~/.gemini/config/`).

Different callers, different write targets, different failure consequences. The earlier one-command-installer entry had just added ~300 lines to that file (hook merging, JSON settings.json manipulation, install dispatch, per-platform installers) — enough that the mixed shape became a smell rather than a coincidence.

Splitting also lets someone read one file and know what its bugs can hurt: runtime bugs can never touch the user's home; install bugs can never touch a project's message log.

The user asked whether the mixed design was correct after seeing the previous session's file layout; the honest answer was "no, they should be separated," and this entry does that separation. The runtime path (`scripts/multiagent_files.py`) is deliberately kept stable so no agent doc, TOML template, skill file, or role instruction needs updating — the runtime contract is unchanged.

### Files affected

- `scripts/_common.py` — new module.
- `scripts/install.py` — new module. Contains `install_codex`, `install_claude_code` + `_wire_claude_hooks`, `install_antigravity`, `install_dispatch`, `validate_install` (+ per-platform validators), `discover_codex_skills`, and the install/validate CLI.
- `scripts/multiagent_files.py` — trimmed to runtime only. Imports `MultiAgentFileError` and `require_dir` from `_common`. CLI now only exposes `prepare-run`, `append-message`, `status`. Adds sys.path shim.
- `scripts/install.ps1`, `scripts/install.sh` — now invoke `scripts/install.py`.
- `tests/test_multiagent_files.py` — imports `install` alongside `multiagent_files`; install/validate references routed to `install.*`. 33 tests still pass.
- `CLAUDE.md`, `AGENTS.md` — Key Files list and Shared section updated; validator command paths updated.
- `README.md` — Automation Helper section restructured into runtime vs install-time.
- `codex-agents/INSTALL.md`, `claude-code/INSTALL.md`, `antigravity/INSTALL.md`, `antigravity/skill/multiagent-workflow/SKILL.md` — validator command paths updated.

### Reversal triggers

- The maintenance overhead of two files exceeds their conceptual separation benefit (e.g. shared constants keep growing until `_common.py` is larger than either sibling). Fold back into one module.
- A future need to share more state at runtime between install and the workflow (e.g. an install-time-generated manifest the workflow reads) makes the boundary artificial. Reconsider.
- Users report the sys.path shim confuses them (e.g. it breaks when packaged into a wheel). Switch to relative imports (`from ._common import ...`) with `if __package__:` guards.

See also: `2026-07-02 — One-command installer for Claude Code and Antigravity, plus install/update parity` (this entry restructures where those installers live but does not change their behavior).

---

## 2026-07-02 — One-command installer for Claude Code and Antigravity, plus install/update parity

### Decision

Extended `scripts/multiagent_files.py` with `install-claude-code`, `install-antigravity`, and a unified `install --platform <name|all>` subcommand that mirror the existing `install-codex` shape. Added thin `scripts/install.ps1` and `scripts/install.sh` wrappers so users invoke `.\scripts\install.ps1 claude-code` (or `codex` / `antigravity` / `all`).

The Claude Code installer also idempotently merges `SessionStart` and `Stop` hook entries into `~/.claude/settings.json`. Existing entries pointing at the same hook script get their command upgraded (so switching shells or moving the repo Just Works); unrelated hooks the user added are preserved. `--no-hooks` skips that step.

The Codex installer now also copies the `multiagent-workflow` skill to `~/.codex/skills/multiagent-workflow/` (previously a manual step in `CODEX-CUSTOM-AGENTS.md`).

Docs restructured:

- New: `codex-agents/INSTALL.md` — short, install-only doc mirroring the other two adapters.
- `CODEX-CUSTOM-AGENTS.md` slimmed to a background reference (communication model, skill configuration, model defaults) with a pointer to the new install doc at the top.
- `claude-code/INSTALL.md` and `antigravity/INSTALL.md` rewritten so the one-line install is the first thing on the page; manual copy commands moved into a "Manual Install (Fallback)" section.
- `README.md` updated: one-command install shown up front; parity table's install-script row flipped from "No (deferred)" to "Yes" for Claude Code and Antigravity.

Legacy `scripts/install-codex-agents.ps1` removed (predates the templated skill-config generation and would produce a broken install now).

Tests added in `tests/test_multiagent_files.py`:

- `test_install_claude_code_copies_agents_skill_command`
- `test_install_claude_code_wires_hooks_into_new_settings`
- `test_install_claude_code_hooks_are_idempotent`
- `test_install_claude_code_preserves_unrelated_hooks`
- `test_install_antigravity_copies_agents_and_skill`
- `test_install_dispatch_all_platforms`

Total test count: 33 (was 27).

### Why

Before this entry, Claude Code and Antigravity users had to run 5–7 copy commands by hand (docs called this out as clear-but-manual), and Codex users had one working `install-codex` subcommand but it was buried under 60+ lines of background in `CODEX-CUSTOM-AGENTS.md` and still needed a separate manual skill copy. There was no documented "how to update" story except "re-run the copy commands"; only Claude Code's doc said this explicitly.

The user asked for a one-step install like Antigravity's (perceived shortest) and an easy way to update. Delivering that meant: real per-platform installer commands, a wrapper users can memorize, idempotent behavior so update = re-run, and docs that put the one-liner first.

Hook wiring was folded into the installer because the manual step ("edit absolute paths in settings.example.json, then merge the `hooks` block into your settings.json by hand") was the most error-prone part of the Claude Code install. Idempotent merging by script-path marker means the installer safely upgrades an old install after `git pull` — including switching between PowerShell and Bash shells if the user moves platforms.

### Files affected

- `scripts/multiagent_files.py` — new `install_claude_code`, `install_antigravity`, `install_dispatch` functions; new `install-claude-code`, `install-antigravity`, `install` subcommands; `_wire_claude_hooks`, `_copy_tree`, `_copy_file` helpers; `install_codex` now also copies the multiagent-workflow skill.
- `scripts/install.ps1` — new one-line wrapper.
- `scripts/install.sh` — new one-line wrapper.
- `scripts/install-codex-agents.ps1` — deleted.
- `codex-agents/INSTALL.md` — new short install doc.
- `CODEX-CUSTOM-AGENTS.md` — slimmed; points to new install doc.
- `claude-code/INSTALL.md` — rewritten around the one-liner.
- `antigravity/INSTALL.md` — rewritten around the one-liner.
- `README.md` — one-command install callout at top of "Choose Your Platform"; parity table updated; Standard Docs section updated.
- `tests/test_multiagent_files.py` — 6 new tests.

### Reversal triggers

- Users report the installer clobbers `settings.json` state we didn't intend to touch (JSON merge produces unexpected structure). Fallback: strip the hook-merging step and go back to "installer copies files; user wires hooks by hand."
- Hook script path becomes a bad uniqueness marker (e.g. Claude Code changes its `hooks` schema so `command` isn't the right field). Adjust `_wire_claude_hooks` accordingly.
- Cross-platform install intent diverges (Codex, Claude Code, Antigravity grow incompatible install shapes). Split the unified `install --platform` back into per-platform subcommands only.

See also: `FUTURE-PLANS.md` no longer lists Claude Code / Antigravity install scripts as deferred — that item is now delivered.

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
