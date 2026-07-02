$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot '..\codex-agents'
$target = Join-Path $env:USERPROFILE '.codex\agents'

New-Item -ItemType Directory -Force -Path $target | Out-Null

Get-ChildItem -Path $source -Filter '*.toml' | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination (Join-Path $target $_.Name) -Force
}

Get-ChildItem -Path $target -Filter '*.toml' | Sort-Object Name | Select-Object Name,FullName,Length

