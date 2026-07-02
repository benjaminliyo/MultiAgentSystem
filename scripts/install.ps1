#!/usr/bin/env pwsh
<#
.SYNOPSIS
  One-line installer for the MultiAgentSystem.

.EXAMPLE
  .\scripts\install.ps1 claude-code
  .\scripts\install.ps1 antigravity
  .\scripts\install.ps1 codex
  .\scripts\install.ps1 all
  .\scripts\install.ps1 claude-code -NoHooks

.NOTES
  Re-run this script after `git pull` to update an existing install.
  Files are overwritten; hook wiring is merged idempotently.
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('codex', 'claude-code', 'antigravity', 'all')]
    [string]$Platform,

    [switch]$NoHooks,

    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'

if (-not $Platform) {
    Write-Host "Which platform do you want to install for?"
    Write-Host "  1) claude-code"
    Write-Host "  2) antigravity"
    Write-Host "  3) codex"
    Write-Host "  4) all"
    $choice = Read-Host "Enter 1-4"
    switch ($choice) {
        '1' { $Platform = 'claude-code' }
        '2' { $Platform = 'antigravity' }
        '3' { $Platform = 'codex' }
        '4' { $Platform = 'all' }
        default { throw "Invalid choice: $choice" }
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$helper = Join-Path $PSScriptRoot 'install.py'

$argsList = @('install', '--repo-root', $repoRoot, '--platform', $Platform)
if ($NoHooks) { $argsList += '--no-hooks' }

Write-Host "Running: $Python $($argsList -join ' ')"
& $Python $helper @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Installer failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Install complete. Restart your CLI session so the new agents/skills load."
Write-Host "To update later: re-run '.\scripts\install.ps1 $Platform'."
