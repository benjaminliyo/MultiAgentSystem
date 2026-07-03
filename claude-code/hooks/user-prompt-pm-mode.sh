#!/bin/bash
# user-prompt-pm-mode.sh
#
# UserPromptSubmit hook (Claude Code; also usable from a Codex project-level
# .codex/hooks.json). Checks for `.multiagent/active-run.json` in the current
# working directory. When a run is active, emits a compact PM-mode reminder so
# the role survives long sessions and context compaction.
#
# Emits nothing (exit 0) when no run is active, so it is safe to wire
# globally. Avoids jq: extracts fields with grep/sed so the only dependency
# is a POSIX userland.

active_path=".multiagent/active-run.json"
[ -f "$active_path" ] || exit 0

extract() {
    grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$active_path" 2>/dev/null \
        | head -n 1 \
        | sed 's/.*:[[:space:]]*"\(.*\)"/\1/'
}

run_name="$(extract run_name)"
state="$(extract state)"
run_dir="$(extract run_dir)"
[ -n "$run_name" ] || exit 0

echo "[multiagent] PM mode active - run $run_name, state: $state."
echo "You are the PM (team lead). Follow the installed PM role instructions: product judgment plus mechanical routing."
echo "Run folder: $run_dir - log inter-agent messages there and update state on every transition (set-state)."
echo "Spawn Developer/Reviewer as subagents; do not implement business code yourself. Deactivate PM mode with /multiagent off."
