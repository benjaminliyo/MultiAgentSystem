# session-start-load-profile.ps1
#
# Claude Code SessionStart hook. Looks for `.multiagent/project-profile.md`
# in the current working directory. If found, emits its contents on stdout
# so Claude Code can inject them as additional context for the new session.
#
# Exits silently when no profile is present so projects without the
# multiagent workflow installed see no output.
#
# Wired via `claude-code/settings.example.json`. Opt-in.

$ErrorActionPreference = "Stop"

$profilePath = Join-Path (Get-Location) ".multiagent/project-profile.md"
if (-not (Test-Path -LiteralPath $profilePath)) {
    exit 0
}

$content = Get-Content -LiteralPath $profilePath -Raw -Encoding UTF8
if ([string]::IsNullOrWhiteSpace($content)) {
    exit 0
}

Write-Output "Multiagent project profile loaded from .multiagent/project-profile.md:"
Write-Output ""
Write-Output $content
