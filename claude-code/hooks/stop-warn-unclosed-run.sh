#!/usr/bin/env bash
# stop-warn-unclosed-run.sh
#
# Claude Code Stop hook. Scans the most recent
# ./.multiagent/runs/<run>/ folder in the current working directory and
# warns if the run is not in a terminal state (done, closed, or
# completed). Catches the "abandoned a run with unfinished workers"
# failure mode.
#
# Exits silently when there is no runs folder, no run, or the latest run
# is already closed.
#
# Wired via claude-code/settings.example.json. Opt-in.

set -euo pipefail

runs_dir="./.multiagent/runs"
if [ ! -d "$runs_dir" ]; then
  exit 0
fi

latest=$(ls -1 "$runs_dir" 2>/dev/null | sort -r | head -n 1 || true)
if [ -z "$latest" ]; then
  exit 0
fi

summary="$runs_dir/$latest/run-summary.md"
if [ ! -f "$summary" ]; then
  exit 0
fi

if grep -Eq "^state:[[:space:]]*(done|closed|completed)\b" "$summary"; then
  exit 0
fi

current_state=$(grep -E "^state:" "$summary" | head -n 1 | sed -E 's/^state:[[:space:]]*//' | awk '{print $1}')
current_state=${current_state:-unknown}

# Send to stderr so it appears as a warning rather than session context.
{
  echo "[multiagent] Open run detected: $latest (state: $current_state)"
  echo "[multiagent] Run-summary path: $summary"
  echo "[multiagent] Resume with PM or close out before abandoning. Set 'state: done' in run-summary.md when finished."
} >&2
