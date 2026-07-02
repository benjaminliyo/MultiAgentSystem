# stop-warn-unclosed-run.ps1
#
# Claude Code Stop hook. Scans the most recent
# `.multiagent/runs/<run>/` folder in the current working directory and
# warns if the run is not in a terminal state (`done`, `closed`, or
# `completed`). Catches the "abandoned a run with unfinished workers"
# failure mode.
#
# Exits silently when there is no runs folder, no run, or the latest run
# is already closed.
#
# Wired via `claude-code/settings.example.json`. Opt-in.

$ErrorActionPreference = "Stop"

$runsDir = Join-Path (Get-Location) ".multiagent/runs"
if (-not (Test-Path -LiteralPath $runsDir)) {
    exit 0
}

$latestRun = Get-ChildItem -LiteralPath $runsDir -Directory -ErrorAction SilentlyContinue |
    Sort-Object -Property Name -Descending |
    Select-Object -First 1
if (-not $latestRun) {
    exit 0
}

$summaryPath = Join-Path $latestRun.FullName "run-summary.md"
if (-not (Test-Path -LiteralPath $summaryPath)) {
    exit 0
}

$content = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8

# Terminal-state check: match a top-level `state:` field set to done/closed/completed.
if ($content -match "(?m)^state:\s*(done|closed|completed)\b") {
    exit 0
}

$stateMatch = [regex]::Match($content, "(?m)^state:\s*(\S+)")
$currentState = if ($stateMatch.Success) { $stateMatch.Groups[1].Value } else { "unknown" }

Write-Warning "[multiagent] Open run detected: $($latestRun.Name) (state: $currentState)"
Write-Warning "[multiagent] Run-summary path: $summaryPath"
Write-Warning "[multiagent] Resume with PM or close out before abandoning. Set 'state: done' in run-summary.md when finished."
