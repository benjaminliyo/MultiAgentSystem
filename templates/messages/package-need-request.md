# Package Need Request

```yaml
message_id: MSG-YYYYMMDD-NNN
task_id: TASK-YYYYMMDD-short-name
from:
to: pm
type: package_need
status: sent
priority: normal
created_at: YYYY-MM-DD HH:MM America/Chicago
requires_response: true
```

## Package And Version Constraint

## Resolved Target Environment

How the environment was resolved (e.g. `.venv` at project root, conda env from
`environment.yml`) and the exact check that confirmed the package is truly
missing there (e.g. `<env-python> -m pip show <pkg>` returned nothing).

## Why It Is Needed

## Cost Of Working Without It

What the fallback would be (degraded output, skipped step, slower manual path)
and why that is worse than installing.

## Install Command Targeting That Environment

## Within Pre-Approved Envelope?

Yes/no per the run's Scoped Autonomy package envelope. If yes and PM confirms,
the worker installs; if no, PM forwards to the client.
