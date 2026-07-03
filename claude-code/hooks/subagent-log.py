#!/usr/bin/env python3
"""Subagent spawn/finish logging hook for Claude Code, Codex, and Antigravity.

Makes spawn/result logging mechanical instead of instruction-following:
whenever a subagent starts or stops while a multiagent run is active
(`.multiagent/active-run.json` present in cwd), this hook

  1. appends the full hook payload to `<run>/transcripts/subagent-events.jsonl`,
  2. for known multiagent roles, appends a message record to the run's
     message log via `scripts/multiagent_files.py append_message`
     (start events: pm -> worker `subagent_start`;
      stop events: worker -> pm `subagent_stop`).

Event mapping per runtime:
  - Claude Code / Codex: `SubagentStart` / `SubagentStop` (agent type in
    `agent_type` or `subagent_type`).
  - Antigravity: `PreToolUse` / `PostToolUse` with matcher `invoke_subagent`
    (agent types in `tool_input.Subagents[*].TypeName` or `tool_input.TypeName`).

Role-file self-logging remains the workers' responsibility for semantic
messages (progress updates, reports); this hook is the durability net for
the mechanical spawn/finish boundary so a dead session still leaves a trail.

Hooks must never break the session: every failure path exits 0 silently, and
unknown payload shapes degrade to a transcripts-only record. Wired on Claude
Code via `claude-code/settings.example.json` / the installer, on Codex via
the rendered project-level `.codex/hooks.json`, and on Antigravity via
`antigravity/hooks.json` (manual, see antigravity/INSTALL.md) — always as
`python <repo>/claude-code/hooks/subagent-log.py`.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

MULTIAGENT_ROLES = {"pm", "developer", "developer-strong", "reviewer", "reviewer-strong"}

START_EVENTS = {"SubagentStart", "PreToolUse"}
STOP_EVENTS = {"SubagentStop", "PostToolUse"}


def resolve_agent_types(payload: dict) -> list[str]:
    """Extract subagent type names from any supported runtime's payload."""
    found: list[str] = []

    def add(value: object) -> None:
        name = str(value).strip()
        if name and name not in found:
            found.append(name)

    for key in ("agent_type", "subagent_type"):
        if payload.get(key):
            add(payload[key])

    tool_input = payload.get("tool_input") or payload.get("arguments")
    if isinstance(tool_input, dict):
        for key in ("TypeName", "subagent_type", "agent_type"):
            if tool_input.get(key):
                add(tool_input[key])
        subagents = tool_input.get("Subagents")
        if isinstance(subagents, list):
            for entry in subagents:
                if isinstance(entry, dict) and entry.get("TypeName"):
                    add(entry["TypeName"])
                elif isinstance(entry, str):
                    add(entry)
    return found


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0

    active_path = Path.cwd() / ".multiagent" / "active-run.json"
    if not active_path.exists():
        return 0
    try:
        active = json.loads(active_path.read_text(encoding="utf-8"))
        run_dir = Path(active["run_dir"])
    except (json.JSONDecodeError, KeyError, OSError):
        return 0
    if not run_dir.is_dir():
        return 0

    event = str(payload.get("hook_event_name", "unknown"))
    agent_types = resolve_agent_types(payload)

    record = {
        "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M local"),
        "event": event,
        "agent_types": agent_types,
        "payload": payload,
    }
    try:
        transcripts = run_dir / "transcripts"
        transcripts.mkdir(parents=True, exist_ok=True)
        with (transcripts / "subagent-events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return 0

    if event in START_EVENTS:
        is_start = True
    elif event in STOP_EVENTS:
        is_start = False
    else:
        return 0

    roles = [name for name in agent_types if name in MULTIAGENT_ROLES]
    if not roles:
        return 0

    # Import the runtime helper from this repo checkout (hook lives at
    # <repo>/claude-code/hooks/, helper at <repo>/scripts/).
    repo_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(repo_root))
    try:
        from scripts import multiagent_files
    except ImportError:
        return 0

    for agent_type in roles:
        if is_start:
            from_role, to_role, message_type = "pm", agent_type, "subagent_start"
            title = f"Auto-log: spawned {agent_type}"
        else:
            from_role, to_role, message_type = agent_type, "pm", "subagent_stop"
            title = f"Auto-log: {agent_type} finished"

        try:
            multiagent_files.append_message(
                run_dir=run_dir,
                from_role=from_role,
                to_role=to_role,
                message_type=message_type,
                title=title,
                body=(
                    f"Mechanically logged {event} for `{agent_type}` by the subagent-log hook. "
                    "Full hook payload: transcripts/subagent-events.jsonl"
                ),
                status="sent",
                priority="normal",
            )
        except Exception:
            continue
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
