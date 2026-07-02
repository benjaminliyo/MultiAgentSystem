# Start Reviewer Agent

Paste this into a Codex thread when implementation is ready for review:

```text
Spawn the custom `reviewer` agent for this project.

Give it:
- `.multiagent/project-profile.md`
- the approved task packet
- the implementation report
- the diff and verification output

The Reviewer should act like a test engineer and code reviewer. It should return PASS only if all acceptance criteria are satisfied with adequate verification. If not, it should return concrete required fixes and route them to Developer or PM/client as appropriate.

Let Reviewer use a skill-installer or skill-search capability when it needs to find missing review, testing, or domain skills. Let Reviewer use a context-maintenance skill (if installed) when its triggers apply.
```
