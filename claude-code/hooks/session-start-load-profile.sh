#!/usr/bin/env bash
# session-start-load-profile.sh
#
# Claude Code SessionStart hook. Looks for ./.multiagent/project-profile.md
# in the current working directory. If found, emits its contents on stdout
# so Claude Code can inject them as additional context for the new session.
#
# Exits silently when no profile is present so projects without the
# multiagent workflow installed see no output.
#
# Wired via claude-code/settings.example.json. Opt-in.

set -euo pipefail

profile="./.multiagent/project-profile.md"
if [ ! -f "$profile" ]; then
  exit 0
fi

if [ ! -s "$profile" ]; then
  exit 0
fi

printf 'Multiagent project profile loaded from .multiagent/project-profile.md:\n\n'
cat "$profile"
