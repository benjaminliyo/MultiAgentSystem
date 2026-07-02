# Multiagent Skill Catalog

This catalog records installed skills and how the PM, Developer, Reviewer, and Orchestrator should use them.

## Root Session

Recommended installed skills:

- `multiagent-workflow`: recognition and launch layer for prompts like "Run the multiagent workflow for this project. Start with the PM agent." It instructs the root session to spawn the custom `pm` agent explicitly.
- `openai-docs`: verify Codex custom-agent and subagent behavior.
- `skill-installer`: install future skills.
- `context-update:context-update`: durable decision drift at session wrap-up.

## PM Agent

Recommended installed skills:

- `superpowers:using-superpowers`: skill-discovery discipline.
- `superpowers:brainstorming`: product discovery and design before implementation.
- `superpowers:writing-plans`: transition from approved task packet to implementation planning.
- `openai-docs`: current Codex/OpenAI/API guidance.
- `skill-installer`: search for and install missing skills when PM or the team lacks a capability.
- `github:github`: GitHub issue, PR, and repository context.
- `context-update:context-update`: update durable context when decisions drift.
- `define-goal`: turn fuzzy intent into a concrete objective and success measure.
- `linear`: use Linear issues and projects as product context.
- `notion-knowledge-capture`: turn decisions into structured Notion documentation.
- `notion-meeting-intelligence`: prepare meeting context and materials.
- `notion-research-documentation`: synthesize Notion research into briefs and reports.
- `notion-spec-to-implementation`: use Notion specs as implementation inputs.
- `figma`, `figma-generate-design`, `figma-create-new-file`, `figma-use`: use or create PM-level design context.
- `security-threat-model`: run explicit product/security threat modeling.
- `chatgpt-apps`: shape ChatGPT Apps SDK products.

PM should not use coding/debugging skills to make implementation decisions. Those belong to Developer.

## Developer Agent

Recommended installed skills:

- `superpowers:test-driven-development`: feature and bugfix implementation discipline.
- `superpowers:systematic-debugging`: failed tests, bugs, unexpected behavior.
- `superpowers:writing-plans`: plan from approved requirements.
- `superpowers:executing-plans`: execute written plans with checkpoints.
- `superpowers:using-git-worktrees`: isolated feature work.
- `superpowers:subagent-driven-development`: split independent implementation tasks.
- `superpowers:dispatching-parallel-agents`: independent parallel tasks.
- `superpowers:receiving-code-review`: respond to Reviewer feedback.
- `superpowers:verification-before-completion`: evidence before claiming done.
- `github:github`, `github:gh-address-comments`, `github:gh-fix-ci`, `github:yeet`: GitHub work.
- `openai-docs`: OpenAI/Codex/API implementation questions.
- `skill-installer`: search for and install missing implementation skills when the current catalog is insufficient.
- `plugin-creator`, `skill-creator`: plugin/skill creation tasks.
- `imagegen`, `documents`, `pdf`, `presentations`, `spreadsheets`, `template-creator`: artifact-specific tasks.
- `context-update:context-update`: durable context drift after implementation decisions.
- `aspnet-core`: ASP.NET Core, Blazor, Razor, MVC, APIs, SignalR, auth, deployment, and upgrades.
- `winui-app`: WinUI 3 and Windows App SDK desktop applications.
- `chatgpt-apps`: ChatGPT Apps SDK projects with MCP server and widget UI.
- `cli-creator`: reusable CLI tools and command surfaces.
- `figma`, `figma-code-connect-components`, `figma-create-design-system-rules`, `figma-create-new-file`, `figma-generate-design`, `figma-generate-library`, `figma-implement-design`, `figma-use`: Figma-to-code and design-system work.
- `jupyter-notebook`: notebook artifacts.
- `playwright`, `playwright-interactive`, `screenshot`: browser/UI automation and visual verification.
- `security-best-practices`, `security-threat-model`: explicit security implementation or threat-modeling work.
- `sentry`: production error inspection through Sentry.
- `vercel-deploy`, `netlify-deploy`, `cloudflare-deploy`, `render-deploy`: hosting and deployment tasks.
- `linear`: implementation tasks sourced from tickets. Notion specs should be handled by PM first, then passed to Developer as a task packet.

No dedicated database skill was available in the curated catalog at assignment time. For database work, Developer should use:

- project profile,
- existing repo patterns,
- official framework documentation,
- newly installed project-specific skills when added.

## Reviewer Agent

Recommended installed skills:

- `superpowers:systematic-debugging`: investigate failed verification.
- `superpowers:verification-before-completion`: do not declare review complete without evidence.
- `github:github`, `github:gh-address-comments`, `github:gh-fix-ci`: PR, review-thread, and CI review.
- `openai-docs`: verify Codex/OpenAI/API behavior when relevant.
- `skill-installer`: search for missing review, testing, security, or domain skills.
- `context-update:context-update`: durable decision drift discovered during review.
- `playwright`, `playwright-interactive`, `screenshot`: browser/UI evidence and visual review.
- `security-best-practices`, `security-threat-model`, `security-ownership-map`: explicit security reviews and ownership-risk analysis.
- `sentry`: production-error evidence.
- `aspnet-core`, `winui-app`, `chatgpt-apps`: domain-specific review for those project types.
- `figma`, `figma-implement-design`, `figma-use`: design-fidelity review.

Reviewer should return required fixes instead of silently taking over Developer work.

## Orchestrator

Recommended installed skills:

- `superpowers:dispatching-parallel-agents`: independent parallel routing.
- `superpowers:subagent-driven-development`: multi-agent implementation slices.
- `superpowers:writing-plans`: plan after approved PM task packet.
- `superpowers:using-git-worktrees`: isolation for risky or parallel work.
- `superpowers:verification-before-completion`: completion evidence.
- `github:github`: repository, PR, issue routing context.
- `openai-docs`: current Codex subagent/custom-agent guidance.
- `skill-installer`: search for and install missing skills requested by agents.
- `context-update:context-update`: durable decisions at wrap-up.
- `define-goal`: clarify objective before routing.
- `linear`: route work tied to Linear issues or projects.
- `notion-knowledge-capture`, `notion-meeting-intelligence`, `notion-research-documentation`, `notion-spec-to-implementation`: route work tied to Notion context, specs, and documentation.
- `security-threat-model`, `security-ownership-map`: route explicit security-analysis work.

## Installed In This Pass

Installed from the curated OpenAI skills catalog:

- `aspnet-core`
- `chatgpt-apps`
- `cli-creator`
- `cloudflare-deploy`
- `define-goal`
- `figma`
- `figma-code-connect-components`
- `figma-create-design-system-rules`
- `figma-create-new-file`
- `figma-generate-design`
- `figma-generate-library`
- `figma-implement-design`
- `figma-use`
- `jupyter-notebook`
- `linear`
- `netlify-deploy`
- `notion-knowledge-capture`
- `notion-meeting-intelligence`
- `notion-research-documentation`
- `notion-spec-to-implementation`
- `playwright`
- `playwright-interactive`
- `render-deploy`
- `screenshot`
- `security-best-practices`
- `security-ownership-map`
- `security-threat-model`
- `sentry`
- `vercel-deploy`
- `winui-app`

Skipped because equivalent system/plugin skills were already installed or available:

- `openai-docs`
- `skill-installer`
- `pdf`
- `gh-address-comments`
- `gh-fix-ci`
- `yeet`

Skipped as not core to the reusable PM/Developer/Reviewer workflow:

- `hatch-pet`
- `migrate-to-codex`
- `speech`
- `transcribe`

## ContextUpdate Testing

All agents should use `context-update` when its triggers apply because the skill is developed by the user and this system should help test it in realistic multi-agent work.

Agents should report:

- false positives,
- false negatives,
- confusing reports,
- unexpected proposed edits,
- missed watched files,
- performance issues,
- runtime-specific differences,
- approval-flow problems.

## Future Skill Slots

When you install or create more domain skills, add them here and to the Developer agent profile:

- frontend framework skill, such as React, Next.js, Vue, Svelte, or UI design systems.
- backend framework skill, such as FastAPI, Django, Express, Rails, Laravel, or Spring.
- database skill, such as PostgreSQL, SQLite, Prisma, Drizzle, SQLAlchemy, migrations, or data modeling.
- deployment skill, such as Docker, Kubernetes, Fly.io, AWS, Azure, or GCP.
- testing skill, such as Cypress, Vitest, Jest, pytest, or property testing.
