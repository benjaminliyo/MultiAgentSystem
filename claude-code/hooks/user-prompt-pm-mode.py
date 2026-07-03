#!/usr/bin/env python3
"""PreInvocation PM-mode reminder for Antigravity (JSON output contract).

Same job as `user-prompt-pm-mode.ps1/.sh` (which emit plain text for Claude
Code's and Codex's UserPromptSubmit): reinject a compact PM-role reminder
every turn while a multiagent run is active, so the role survives long
sessions.

Antigravity's PreInvocation hooks must print a single flat JSON object to
stdout — the framework parses it and appends the `additionalContext` field to
the LLM context. Plain text (or any stray stdout) fails its JSON parser and
can crash the agent's turn, so this script:

  - always prints exactly one JSON object and exits 0,
  - prints `{}` when no run is active or anything goes wrong,
  - never writes debug output to stdout (stderr only, if ever needed).

Wired via the rendered `<project>/.agents/hooks.json`
(`prepare-run --project-hooks antigravity`).
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    try:
        active_path = Path.cwd() / ".multiagent" / "active-run.json"
        if not active_path.exists():
            print("{}")
            return 0
        active = json.loads(active_path.read_text(encoding="utf-8"))
        run_name = str(active.get("run_name", "unknown"))
        state = str(active.get("state", "unknown"))
        run_dir = str(active.get("run_dir", ""))
        reminder = "\n".join(
            [
                f"[multiagent] PM mode active - run {run_name}, state: {state}.",
                "You are the PM (team lead). Follow the installed PM role instructions: "
                "product judgment plus mechanical routing.",
                f"Run folder: {run_dir} - log inter-agent messages there and update state "
                "on every transition (set-state).",
                "Spawn Developer/Reviewer as subagents; do not implement business code "
                "yourself. Deactivate PM mode with /multiagent off.",
            ]
        )
        print(json.dumps({"additionalContext": reminder}, ensure_ascii=False))
    except Exception:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
