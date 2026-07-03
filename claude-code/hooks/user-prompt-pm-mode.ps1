# user-prompt-pm-mode.ps1
#
# UserPromptSubmit hook (Claude Code; also usable from a Codex project-level
# .codex/hooks.json). Checks for `.multiagent/active-run.json` in the current
# working directory. When a run is active, emits a compact PM-mode reminder so
# the role survives long sessions and context compaction — the role file
# itself is loaded as a tool result, which is the first thing to fade.
#
# Emits nothing (exit 0) when no run is active, so it is safe to wire
# globally. Wired via `claude-code/settings.example.json` or the installer.

$ErrorActionPreference = "Stop"

$activePath = Join-Path (Get-Location) ".multiagent/active-run.json"
if (-not (Test-Path -LiteralPath $activePath)) {
    exit 0
}

try {
    $active = Get-Content -LiteralPath $activePath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    exit 0
}

$runName = $active.run_name
$state = $active.state
$runDir = $active.run_dir

Write-Output "[multiagent] PM mode active - run $runName, state: $state."
Write-Output "You are the PM (team lead). Follow the installed PM role instructions: product judgment plus mechanical routing."
Write-Output "Run folder: $runDir - log inter-agent messages there and update state on every transition (set-state)."
Write-Output "Spawn Developer/Reviewer as subagents; do not implement business code yourself. Deactivate PM mode with /multiagent off."
