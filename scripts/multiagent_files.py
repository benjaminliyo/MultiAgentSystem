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
    "orchestrator",
}


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

## Routing Notes

- Run folder prepared by scripts/multiagent_files.py.
"""


def prepare_run(root: Path, task: str, date: str | None = None) -> dict[str, Any]:
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

    return {
        "project_root": str(project_root),
        "run_dir": str(run_dir),
        "run_name": run_name,
        "created_or_repaired": created,
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
            payload = prepare_run(Path(args.root), args.task, args.date)
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
