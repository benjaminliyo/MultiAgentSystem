# Start Developer Agent

Paste this into a Codex thread when you already have an approved task packet:

```text
Spawn the custom `developer` agent for this project.

Give it:
- `.multiagent/project-profile.md`
- the approved task packet
- any relevant PM notes

The Developer should own technical design and implementation, run relevant verification, maintain affected technical docs, and return an implementation report plus a ready-for-review message. If technical choices change product behavior, scope, cost, privacy, dependency footprint, or acceptance criteria, route back to PM/client.

Let Developer use a skill-installer or skill-search capability when it needs to find missing skills.

Approved task packet:
<paste or reference task packet here>
```
