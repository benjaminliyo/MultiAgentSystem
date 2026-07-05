#!/usr/bin/env python3
"""Runtime file helper for the PM-led MultiAgentSystem.

Called by agents during an active workflow run to:
  - prepare a run folder under `<project>/.multiagent/runs/`,
  - append inter-agent messages to a run's message log,
  - inspect a run's current file state.

Install and validation logic lives in `install.py`; that split keeps runtime
bugs from touching the user's CLI config and vice versa.
"""

from __future__ import annotations

import argparse
import json
import platform as _platform
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Support both `python scripts/multiagent_files.py ...` and
# `python -m scripts.multiagent_files ...` / import from tests. Direct
# invocation doesn't put the project root on sys.path, which would break
# `from scripts._common import ...`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._common import MultiAgentFileError, require_dir


DEFAULT_ROLES = (
    {
        "role": "pm",
        "reports_to": "client",
        "may_modify_business_code": False,
        "artifact_scope": [
            "task-packet",
            "decision-record",
            "closeout",
            "planning-docs",
            "run-summary",
            "messages",
            "transcripts",
            "routing-notes",
        ],
    },
    {
        "role": "developer",
        "reports_to": "pm",
        "may_modify_business_code": True,
        "artifact_scope": ["implementation", "tests", "technical-docs", "implementation-report"],
    },
    {
        "role": "developer-strong",
        "reports_to": "pm",
        "may_modify_business_code": True,
        "artifact_scope": [
            "implementation",
            "tests",
            "technical-docs",
            "implementation-report",
            "technical-plan",
        ],
    },
    {
        "role": "reviewer",
        "reports_to": "pm",
        "may_modify_business_code": False,
        "artifact_scope": ["review-report", "test-artifacts"],
    },
    {
        "role": "reviewer-strong",
        "reports_to": "pm",
        "may_modify_business_code": False,
        "artifact_scope": ["risk-review-report", "test-artifacts"],
    },
    {
        "role": "researcher",
        "reports_to": "pm",
        "may_modify_business_code": False,
        "artifact_scope": ["exploration-report"],
    },
)

# `orchestrator` is retained as a valid message role for forward compatibility
# with the autonomous-loop scenario described in FUTURE-PLANS.md, and for
# backward compatibility with messages written by old installs.
VALID_MESSAGE_ROLES = {
    "client",
    "pm",
    "developer",
    "developer-strong",
    "reviewer",
    "reviewer-strong",
    "researcher",
    "orchestrator",
}

# Workflow state machine (see roles/pm.md "Routing And Run Management").
# `closed` and `completed` are accepted terminal aliases for `done`.
VALID_RUN_STATES = (
    "intake",
    "pm_discovery",
    "awaiting_client_approval",
    "developer_implementation",
    "reviewer_checking",
    "developer_fixing",
    "pm_closeout",
    "done",
    "closed",
    "completed",
)
TERMINAL_RUN_STATES = {"done", "closed", "completed"}

# Marker block delimiters for the PM-mode section inserted into project
# context files (CLAUDE.md / AGENTS.md / GEMINI.md). These files ride at
# system-prompt priority in every supported harness, which is what keeps
# the PM role from fading in long sessions.
MARKER_BEGIN = "<!-- multiagent:begin -->"
MARKER_END = "<!-- multiagent:end -->"
CONTEXT_FILE_NAMES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "task"


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MultiAgentFileError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise MultiAgentFileError(f"Invalid JSONL at {path}:{line_number}: record must be an object")
        records.append(record)
    return records


def registry_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "team_model": "pm-led",
        "entry_role": "pm",
        "roles": list(DEFAULT_ROLES),
    }


def ensure_registry(root: Path) -> tuple[Path, bool]:
    registry_path = root / ".multiagent" / "team-registry.json"
    if not registry_path.exists():
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry_payload(), indent=2) + "\n", encoding="utf-8")
        return registry_path, True

    try:
        existing = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MultiAgentFileError(f"Cannot parse existing registry: {exc}") from exc
    if not isinstance(existing, dict) or not isinstance(existing.get("roles"), list):
        raise MultiAgentFileError("Existing team-registry.json must contain a 'roles' array")
    return registry_path, False


def run_summary(task: str, run_name: str, created_at: str) -> str:
    return f"""# MultiAgent Run Summary

task: {task}
run: {run_name}
created_at: {created_at}
state: intake

## Scoped Autonomy

Not recorded yet.

## Agent IDs

- pm: not recorded
- developer: not recorded
- developer-strong: not recorded
- reviewer: not recorded
- reviewer-strong: not recorded
- researcher: not recorded (optional)

## Routing Notes

- Run folder prepared by scripts/multiagent_files.py.
"""


def active_run_path(root: Path) -> Path:
    return root / ".multiagent" / "active-run.json"


def read_active_run(root: Path) -> dict[str, Any] | None:
    path = active_run_path(root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MultiAgentFileError(f"Cannot parse {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MultiAgentFileError(f"{path} must contain a JSON object")
    return payload


def write_active_run(root: Path, run_name: str, run_dir: Path, state: str) -> Path:
    path = active_run_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "role": "pm",
        "run_name": run_name,
        "run_dir": str(run_dir),
        "state": state,
        "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M local"),
        "script": str(Path(__file__).resolve()),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def marker_block(run_name: str) -> str:
    script = Path(__file__).resolve().as_posix()
    return f"""{MARKER_BEGIN}
## MultiAgent PM Mode (active)

A PM-led multiagent run is active in this project: `.multiagent/runs/{run_name}/`.

- The main session acts as PM. Follow the installed PM role instructions
  (`~/.claude/agents/pm.md`, `~/.codex/agents/pm.toml`, or
  `~/.gemini/config/agents/pm.md`) for the rest of the session.
- Developer and Reviewer run as spawned subagents; PM owns routing, state
  tracking, and message logging in the run folder.
- Current state lives in `.multiagent/active-run.json` and the run's
  `run-summary.md`. Update it on every transition:
  `python "{script}" set-state --run <run-dir> --state <state>`
- To deactivate PM mode: `/multiagent off`, or
  `python "{script}" close-run --root <project-root>`
{MARKER_END}"""


def upsert_marker_block(path: Path, block: str) -> bool:
    """Insert or replace the marker-delimited block in a context file.

    Returns True when the file changed. Creates the file when missing.
    Everything outside the markers is preserved byte-for-byte.
    """
    if not path.exists():
        path.write_text(block + "\n", encoding="utf-8")
        return True
    text = path.read_text(encoding="utf-8")
    begin = text.find(MARKER_BEGIN)
    end = text.find(MARKER_END)
    if begin != -1 and end != -1 and end >= begin:
        new_text = text[:begin] + block + text[end + len(MARKER_END):]
    elif begin == -1 and end == -1:
        separator = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        new_text = text + separator + block + "\n"
    else:
        raise MultiAgentFileError(
            f"Unbalanced multiagent markers in {path}; fix or remove them manually"
        )
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def remove_marker_block(path: Path) -> bool:
    """Remove the marker-delimited block (and surrounding blank padding)."""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    begin = text.find(MARKER_BEGIN)
    end = text.find(MARKER_END)
    if begin == -1 or end == -1 or end < begin:
        return False
    before = text[:begin].rstrip()
    after = text[end + len(MARKER_END):].lstrip("\n")
    if before and after:
        new_text = before + "\n\n" + after
    elif before:
        new_text = before + "\n"
    else:
        new_text = after
    path.write_text(new_text, encoding="utf-8")
    return True


def context_files(root: Path) -> list[Path]:
    """Project context files to receive the PM-mode marker block.

    Always covers AGENTS.md and CLAUDE.md — creating whichever is missing —
    so a run started on one platform stays visible when the project is
    reopened on the other (Codex reads AGENTS.md, Claude Code reads
    CLAUDE.md). GEMINI.md is included only when it already exists. A file
    created here holds nothing but the marker block, so close-run removes
    it again.
    """
    paths = [root / "AGENTS.md", root / "CLAUDE.md"]
    gemini = root / "GEMINI.md"
    if gemini.exists():
        paths.append(gemini)
    return paths


def activate_run(root: Path, run_name: str, run_dir: Path, state: str) -> dict[str, Any]:
    changed: list[str] = []
    write_active_run(root, run_name, run_dir, state)
    changed.append(str(active_run_path(root).relative_to(root)))
    block = marker_block(run_name)
    for path in context_files(root):
        if upsert_marker_block(path, block):
            changed.append(path.name)
    return {"activated": True, "changed": changed}


def _hook_command(script_base: str) -> str:
    """Absolute command string for a canonical hook script, per host OS."""
    hooks_dir = Path(__file__).resolve().parent.parent / "claude-code" / "hooks"
    if _platform.system() == "Windows":
        script = (hooks_dir / f"{script_base}.ps1").as_posix()
        return f'powershell -NoProfile -ExecutionPolicy Bypass -File "{script}"'
    script = (hooks_dir / f"{script_base}.sh").as_posix()
    return f'bash "{script}"'


# Project-level hook wiring per platform: template in the repo, rendered
# destination inside the target project. Claude Code is absent on purpose —
# its hooks are global (settings.json), wired by the installer.
PROJECT_HOOKS = {
    "codex": {"template": ("codex", "hooks.json"), "destination": (".codex", "hooks.json")},
    "antigravity": {"template": ("antigravity", "hooks.json"), "destination": (".agents", "hooks.json")},
}


def write_project_hooks(root: Path, hooks_platform: str) -> dict[str, Any]:
    """Render a platform's hooks.json template into the target project.

    Codex and Antigravity only support project-level hooks (`.codex/hooks.json`
    and `.agents/hooks.json` respectively), so PM-mode reinjection and subagent
    logging there need this file inside the target project. Codex prompts the
    user to trust it on first use.
    """
    spec = PROJECT_HOOKS.get(hooks_platform)
    if spec is None:
        raise MultiAgentFileError(
            f"Unsupported --project-hooks platform: {hooks_platform} "
            f"(supported: {', '.join(sorted(PROJECT_HOOKS))})"
        )
    repo_root = Path(__file__).resolve().parent.parent
    template_path = repo_root.joinpath(*spec["template"])
    if not template_path.exists():
        raise MultiAgentFileError(f"Hooks template missing: {template_path}")
    destination = root.joinpath(*spec["destination"])
    if destination.exists():
        return {"written": False, "path": str(destination), "note": "already exists; left untouched"}

    def escape(command: str) -> str:
        return json.dumps(command)[1:-1]

    hooks_dir = repo_root / "claude-code" / "hooks"
    subagent_log_cmd = f'python "{(hooks_dir / "subagent-log.py").as_posix()}"'
    # Antigravity's PreInvocation contract requires a flat JSON object on
    # stdout ({"additionalContext": ...}); the .py variant honors it, while
    # the .ps1/.sh variants emit plain text for Claude Code/Codex.
    user_prompt_json_cmd = f'python "{(hooks_dir / "user-prompt-pm-mode.py").as_posix()}"'
    text = template_path.read_text(encoding="utf-8")
    text = text.replace("{{USER_PROMPT_CMD}}", escape(_hook_command("user-prompt-pm-mode")))
    text = text.replace("{{USER_PROMPT_JSON_CMD}}", escape(user_prompt_json_cmd))
    text = text.replace("{{SESSION_START_CMD}}", escape(_hook_command("session-start-load-profile")))
    text = text.replace("{{STOP_CMD}}", escape(_hook_command("stop-warn-unclosed-run")))
    text = text.replace("{{SUBAGENT_LOG_CMD}}", escape(subagent_log_cmd))
    try:
        rendered = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MultiAgentFileError(f"Rendered hooks.json is invalid JSON: {exc}") from exc
    if hooks_platform == "codex":
        # Codex uses Claude-style {"hooks": {...}}, where a top-level string
        # key is safe. Antigravity's schema maps top-level keys to hook-group
        # names, so no comment is injected there.
        rendered["_comment"] = (
            "Generated by multiagent prepare-run from codex/hooks.json in the "
            "MultiAgentSystem repo; commands point at this machine's checkout. "
            "Codex asks the user to trust these hooks on first use."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(rendered, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(destination)}


def prepare_run(
    root: Path,
    task: str,
    date: str | None = None,
    activate: bool = True,
    project_hooks: str | None = None,
) -> dict[str, Any]:
    project_root = require_dir(root, "Project root")
    date_part = date or datetime.now().strftime("%Y-%m-%d")
    run_name = f"{date_part}-{slugify(task)}"
    run_dir = project_root / ".multiagent" / "runs" / run_name
    created: list[str] = []

    for directory in (run_dir, run_dir / "messages", run_dir / "transcripts"):
        if not directory.exists():
            directory.mkdir(parents=True)
            created.append(str(directory.relative_to(project_root)))

    if write_if_missing(run_dir / "messages.jsonl", ""):
        created.append(str((run_dir / "messages.jsonl").relative_to(project_root)))

    summary_created = write_if_missing(
        run_dir / "run-summary.md",
        run_summary(task, run_name, f"{date_part} 00:00 local"),
    )
    if summary_created:
        created.append(str((run_dir / "run-summary.md").relative_to(project_root)))

    registry_path, registry_created = ensure_registry(project_root)
    if registry_created:
        created.append(str(registry_path.relative_to(project_root)))

    activation: dict[str, Any] = {"activated": False, "changed": []}
    if activate:
        activation = activate_run(project_root, run_name, run_dir, "intake")

    hooks_result: dict[str, Any] | None = None
    if project_hooks:
        hooks_result = write_project_hooks(project_root, project_hooks)

    return {
        "project_root": str(project_root),
        "run_dir": str(run_dir),
        "run_name": run_name,
        "created_or_repaired": created,
        "activation": activation,
        "project_hooks": hooks_result,
        "complete": True,
    }


def read_summary_state(run_dir: Path) -> str | None:
    summary = run_dir / "run-summary.md"
    if not summary.exists():
        return None
    match = re.search(r"^state: (.*)$", summary.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() if match else None


def reactivate_run(
    root: Path, run_dir: Path, project_hooks: str | None = None
) -> dict[str, Any]:
    """Re-activate PM mode for an existing run (resume of any previous run).

    Restores `.multiagent/active-run.json` and the context-file marker blocks
    for the given run, using the state recorded in its run-summary.md. Works
    on closed runs too — the caller (PM) should `set-state` to a working state
    when deliberately reopening one. `project_hooks` renders the platform's
    project-level hook wiring, for cross-platform resume of a run whose
    prepare-run happened on a different platform.
    """
    project_root = require_dir(root, "Project root")
    run_path = require_dir(run_dir, "Run directory")
    state = read_summary_state(run_path) or "intake"
    activation = activate_run(project_root, run_path.name, run_path, state)
    hooks_result: dict[str, Any] | None = None
    if project_hooks:
        hooks_result = write_project_hooks(project_root, project_hooks)
    warnings: list[str] = []
    if state in TERMINAL_RUN_STATES:
        warnings.append(
            f"run is in terminal state '{state}'; use set-state to reopen it if you intend to continue work"
        )
    return {
        "project_root": str(project_root),
        "run_dir": str(run_path),
        "run_name": run_path.name,
        "state": state,
        "activation": activation,
        "project_hooks": hooks_result,
        "warnings": warnings,
        "complete": True,
    }


def _update_summary_state(summary_path: Path, state: str) -> bool:
    if not summary_path.exists():
        return False
    text = summary_path.read_text(encoding="utf-8")
    new_text, count = re.subn(r"^state: .*$", f"state: {state}", text, count=1, flags=re.MULTILINE)
    if count == 0 or new_text == text:
        return False
    summary_path.write_text(new_text, encoding="utf-8")
    return True


def set_state(run_dir: Path, state: str) -> dict[str, Any]:
    if state not in VALID_RUN_STATES:
        raise MultiAgentFileError(
            f"Unknown state: {state}. Valid states: {', '.join(VALID_RUN_STATES)}"
        )
    run_path = require_dir(run_dir, "Run directory")
    warnings: list[str] = []

    summary_updated = _update_summary_state(run_path / "run-summary.md", state)
    if not summary_updated and not (run_path / "run-summary.md").exists():
        warnings.append(f"run-summary.md missing in {run_path}")

    # run_dir layout: <project-root>/.multiagent/runs/<run-name>
    if len(run_path.parents) < 3 or run_path.parent.name != "runs":
        warnings.append(f"non-standard run path {run_path}; active-run.json not updated")
        return {
            "run_dir": str(run_path),
            "state": state,
            "summary_updated": summary_updated,
            "warnings": warnings,
            "complete": True,
        }
    project_root = run_path.parents[2]
    active = read_active_run(project_root)
    if active is not None and Path(active.get("run_dir", "")) == run_path:
        active["state"] = state
        active_run_path(project_root).write_text(
            json.dumps(active, indent=2) + "\n", encoding="utf-8"
        )
    elif active is None:
        warnings.append("active-run.json missing; only run-summary.md updated")
    else:
        warnings.append("active-run.json points at a different run; left untouched")

    return {
        "run_dir": str(run_path),
        "state": state,
        "summary_updated": summary_updated,
        "warnings": warnings,
        "complete": True,
    }


def close_run(root: Path, run_dir: Path | None = None) -> dict[str, Any]:
    """Deactivate PM mode: terminal state, strip markers, drop active-run.json."""
    project_root = require_dir(root, "Project root")
    warnings: list[str] = []
    active = read_active_run(project_root)

    target_run: Path | None = run_dir
    if target_run is None and active is not None and active.get("run_dir"):
        target_run = Path(active["run_dir"])
    if target_run is not None and target_run.is_dir():
        if not _update_summary_state(target_run / "run-summary.md", "done"):
            current = ""
            summary = target_run / "run-summary.md"
            if summary.exists():
                match = re.search(r"^state: (.*)$", summary.read_text(encoding="utf-8"), re.MULTILINE)
                current = (match.group(1).strip() if match else "")
            if current not in TERMINAL_RUN_STATES:
                warnings.append(f"could not set terminal state in {target_run / 'run-summary.md'}")
    elif target_run is not None:
        warnings.append(f"run directory missing: {target_run}")
    else:
        warnings.append("no active run recorded; removing markers only")

    removed: list[str] = []
    for name in CONTEXT_FILE_NAMES:
        path = project_root / name
        if remove_marker_block(path):
            removed.append(name)
            # Drop files that held nothing but our marker block (i.e. files
            # activation itself created); files with user content are kept.
            if not path.read_text(encoding="utf-8").strip():
                path.unlink()

    active_path = active_run_path(project_root)
    deactivated = False
    if active_path.exists():
        active_path.unlink()
        deactivated = True

    return {
        "project_root": str(project_root),
        "run_dir": str(target_run) if target_run else None,
        "markers_removed_from": removed,
        "deactivated": deactivated,
        "warnings": warnings,
        "complete": True,
    }


def next_message_number(records: list[dict[str, Any]]) -> int:
    numbers: list[int] = []
    for record in records:
        message_id = str(record.get("message_id", ""))
        match = re.search(r"-(\d{3})$", message_id)
        if match:
            numbers.append(int(match.group(1)))
    return (max(numbers) + 1) if numbers else 1


def message_date_for_id(created_at: str) -> str:
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", created_at)
    if match:
        return "".join(match.groups())
    return datetime.now().strftime("%Y%m%d")


def append_message(
    run_dir: Path,
    from_role: str,
    to_role: str,
    message_type: str,
    title: str,
    body: str,
    status: str,
    priority: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    run_path = require_dir(run_dir, "Run directory")
    messages_dir = require_dir(run_path / "messages", "Messages directory")
    index_path = run_path / "messages.jsonl"
    if not index_path.exists():
        raise MultiAgentFileError(f"Missing message index: {index_path}")
    if from_role not in VALID_MESSAGE_ROLES:
        raise MultiAgentFileError(f"Unknown from-role: {from_role}")
    if to_role not in VALID_MESSAGE_ROLES:
        raise MultiAgentFileError(f"Unknown to-role: {to_role}")

    timestamp = created_at or datetime.now().strftime("%Y-%m-%d %H:%M local")
    records = read_jsonl(index_path)
    number = next_message_number(records)
    message_id = f"MSG-{message_date_for_id(timestamp)}-{number:03d}"
    filename = f"{number:03d}-{slugify(from_role)}-to-{slugify(to_role)}-{slugify(message_type)}.md"
    artifact = f"messages/{filename}"
    message_path = messages_dir / filename
    if message_path.exists():
        raise MultiAgentFileError(f"Refusing to overwrite existing message file: {message_path}")
    if any(record.get("message_id") == message_id for record in records):
        raise MultiAgentFileError(f"Duplicate message_id: {message_id}")

    markdown = f"""---
message_id: {message_id}
from: {from_role}
to: {to_role}
type: {message_type}
status: {status}
priority: {priority}
created_at: {timestamp}
requires_response: false
---

# {title}

{body.rstrip()}
"""
    message_path.write_text(markdown, encoding="utf-8")

    record = {
        "message_id": message_id,
        "from": from_role,
        "to": to_role,
        "type": message_type,
        "status": status,
        "priority": priority,
        "title": title,
        "created_at": timestamp,
        "artifact": artifact,
    }
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def status_payload(run_dir: Path) -> dict[str, Any]:
    run_path = require_dir(run_dir, "Run directory")
    required = [
        run_path / "run-summary.md",
        run_path / "messages",
        run_path / "transcripts",
        run_path / "messages.jsonl",
    ]
    missing = [path.name for path in required if not path.exists()]
    index_path = run_path / "messages.jsonl"
    records = read_jsonl(index_path) if index_path.exists() else []
    registry_path = run_path.parents[1] / "team-registry.json"
    registry_roles: list[str] = []
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MultiAgentFileError(f"Cannot parse team registry: {exc}") from exc
        registry_roles = [
            str(role.get("role"))
            for role in registry.get("roles", [])
            if isinstance(role, dict) and role.get("role")
        ]

    return {
        "run_dir": str(run_path),
        "complete": not missing,
        "missing_files": missing,
        "message_count": len(records),
        "registry_roles": registry_roles,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-run")
    prepare.add_argument("--root", required=True)
    prepare.add_argument("--task", required=True)
    prepare.add_argument("--date", default=None)
    prepare.add_argument(
        "--no-activate",
        action="store_true",
        help="Skip writing active-run.json and the PM-mode marker block into context files.",
    )
    prepare.add_argument(
        "--project-hooks",
        default=None,
        choices=("codex", "antigravity"),
        help="Also render project-level hook wiring (Codex: .codex/hooks.json; Antigravity: .agents/hooks.json).",
    )

    state = subparsers.add_parser(
        "set-state",
        help="Update the workflow state in run-summary.md and active-run.json.",
    )
    state.add_argument("--run", required=True)
    state.add_argument("--state", required=True)

    close = subparsers.add_parser(
        "close-run",
        help="Deactivate PM mode: set terminal state, remove marker blocks, delete active-run.json.",
    )
    close.add_argument("--root", required=True)
    close.add_argument("--run", default=None, help="Run directory override (defaults to active-run.json).")

    reactivate = subparsers.add_parser(
        "activate-run",
        help="Re-activate PM mode for an existing run (resume any previous run, including closed ones).",
    )
    reactivate.add_argument("--root", required=True)
    reactivate.add_argument("--run", required=True, help="Run directory to re-activate.")
    reactivate.add_argument(
        "--project-hooks",
        default=None,
        choices=("codex", "antigravity"),
        help="Also render project-level hook wiring (Codex: .codex/hooks.json; Antigravity: .agents/hooks.json). Useful when resuming on a different platform than the one that ran prepare-run.",
    )

    append = subparsers.add_parser("append-message")
    append.add_argument("--run", required=True)
    append.add_argument("--from-role", required=True)
    append.add_argument("--to-role", required=True)
    append.add_argument("--type", required=True)
    append.add_argument("--title", required=True)
    append.add_argument("--body", default="")
    append.add_argument("--status", default="sent")
    append.add_argument("--priority", default="normal")
    append.add_argument("--created-at", default=None)

    status = subparsers.add_parser("status")
    status.add_argument("--run", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-run":
            payload = prepare_run(
                Path(args.root),
                args.task,
                args.date,
                activate=not args.no_activate,
                project_hooks=args.project_hooks,
            )
        elif args.command == "set-state":
            payload = set_state(Path(args.run), args.state)
        elif args.command == "close-run":
            payload = close_run(
                Path(args.root),
                run_dir=Path(args.run) if args.run else None,
            )
        elif args.command == "activate-run":
            payload = reactivate_run(
                Path(args.root), Path(args.run), project_hooks=args.project_hooks
            )
        elif args.command == "append-message":
            payload = append_message(
                run_dir=Path(args.run),
                from_role=args.from_role,
                to_role=args.to_role,
                message_type=args.type,
                title=args.title,
                body=args.body,
                status=args.status,
                priority=args.priority,
                created_at=args.created_at,
            )
        else:
            payload = status_payload(Path(args.run))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("complete", True) else 2
    except MultiAgentFileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
