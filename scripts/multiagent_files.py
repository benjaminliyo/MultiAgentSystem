#!/usr/bin/env python3
"""Deterministic file helper for the PM-led MultiAgentSystem."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback.
    tomllib = None  # type: ignore[assignment]


# Active agents per platform. The `multiagent-orchestrator` role was deprecated
# on 2026-06-29 (see CHANGELOG.md); PM (main thread) absorbed its mechanical
# responsibilities. Old installs may still have the orchestrator TOML on disk —
# that is harmless and not validated here.
CANONICAL_AGENT_FILES = {
    "codex": (
        "pm.toml",
        "developer.toml",
        "developer-strong.toml",
        "reviewer.toml",
        "reviewer-strong.toml",
    ),
    "claude-code": (
        "pm.md",
        "developer.md",
        "developer-strong.md",
        "reviewer.md",
        "reviewer-strong.md",
    ),
    "antigravity": (
        "pm.md",
        "developer.md",
        "developer-strong.md",
        "reviewer.md",
        "reviewer-strong.md",
    ),
}

SUPPORTED_PLATFORMS = tuple(CANONICAL_AGENT_FILES.keys())

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


class MultiAgentFileError(RuntimeError):
    """Raised when the helper cannot safely prepare or validate artifacts."""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "task"


def require_dir(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise MultiAgentFileError(f"{label} is not a directory: {resolved}")
    return resolved


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


def parse_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise MultiAgentFileError("Python tomllib is unavailable; use Python 3.11+ for TOML validation")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise MultiAgentFileError(f"Cannot parse TOML {path}: {exc}") from exc


def skills_for_agent(path: Path) -> list[str]:
    data = parse_toml(path)
    entries = data.get("skills", {}).get("config", [])
    if not isinstance(entries, list):
        return []
    paths: list[str] = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            paths.append(entry["path"])
    return paths


def validate_install(
    repo_root: Path,
    codex_home: Path | None = None,
    platform: str = "codex",
    claude_home: Path | None = None,
    antigravity_home: Path | None = None,
) -> dict[str, Any]:
    if platform not in CANONICAL_AGENT_FILES:
        raise MultiAgentFileError(
            f"Unknown platform: {platform}. Supported: {', '.join(SUPPORTED_PLATFORMS)}"
        )
    if platform == "codex":
        return _validate_install_codex(repo_root, codex_home)
    if platform == "claude-code":
        return _validate_install_claude_code(repo_root, claude_home)
    return _validate_install_antigravity(repo_root, antigravity_home)


def _validate_install_codex(
    repo_root: Path,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    repo = require_dir(repo_root, "Repository root")
    home = (codex_home or (Path.home() / ".codex")).expanduser().resolve()
    missing: list[str] = []
    warnings: list[str] = []

    canonical_agents = repo / "codex-agents"
    installed_agents = home / "agents"
    for name in CANONICAL_AGENT_FILES["codex"]:
        canonical = canonical_agents / name
        installed = installed_agents / name
        if not canonical.exists():
            missing.append(str(canonical))
            continue
        if not installed.exists():
            missing.append(str(installed))
        # Skill assignments in [[skills.config]] are per-machine and populated by
        # the install script from local paths. Role instructions reference skills
        # by category, not concrete name, so this validator no longer requires
        # specific skill names to appear here.
        if tomllib is not None:
            try:
                parse_toml(canonical)
            except MultiAgentFileError as exc:
                missing.append(str(exc))

    canonical_skill = repo / "codex-skill" / "multiagent-workflow" / "SKILL.md"
    installed_skill = home / "skills" / "multiagent-workflow" / "SKILL.md"
    if not canonical_skill.exists():
        missing.append(str(canonical_skill))
    if not installed_skill.exists():
        missing.append(str(installed_skill))

    if tomllib is None:
        warnings.append("tomllib unavailable; TOML validation requires Python 3.11+")

    return {
        "platform": "codex",
        "repo_root": str(repo),
        "codex_home": str(home),
        "complete": not missing,
        "missing": missing,
        "warnings": warnings,
    }


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse minimal YAML frontmatter without requiring PyYAML.

    Supports the small subset used by Claude Code agent and skill files:
    top-level scalar key/value pairs. Returns ({}, original_text) when the
    file does not start with a frontmatter block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, str] = {}
    body_start: int | None = None
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            body_start = index + 1
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    body = "\n".join(lines[body_start:]) if body_start is not None else ""
    return meta, body


def _validate_install_claude_code(
    repo_root: Path,
    claude_home: Path | None = None,
) -> dict[str, Any]:
    repo = require_dir(repo_root, "Repository root")
    home = (claude_home or (Path.home() / ".claude")).expanduser().resolve()
    missing: list[str] = []
    warnings: list[str] = []

    canonical_agents = repo / "claude-code" / "agents"
    installed_agents = home / "agents"
    for name in CANONICAL_AGENT_FILES["claude-code"]:
        canonical = canonical_agents / name
        installed = installed_agents / name
        if not canonical.exists():
            missing.append(str(canonical))
            continue
        if not installed.exists():
            missing.append(str(installed))
        try:
            text = canonical.read_text(encoding="utf-8")
        except OSError as exc:
            missing.append(f"{canonical}: cannot read ({exc})")
            continue
        meta, body = _parse_frontmatter(text)
        if not meta:
            missing.append(f"{canonical}: missing YAML frontmatter")
            continue
        if not meta.get("name"):
            missing.append(f"{canonical}: frontmatter missing 'name'")
        if not meta.get("description"):
            missing.append(f"{canonical}: frontmatter missing 'description'")
        if "context-maintenance" not in body:
            warnings.append(f"{canonical}: body does not mention context-maintenance")

    canonical_skill = repo / "claude-code" / "skill" / "multiagent-workflow" / "SKILL.md"
    installed_skill = home / "skills" / "multiagent-workflow" / "SKILL.md"
    if not canonical_skill.exists():
        missing.append(str(canonical_skill))
    else:
        try:
            skill_text = canonical_skill.read_text(encoding="utf-8")
            skill_meta, _ = _parse_frontmatter(skill_text)
            if not skill_meta.get("name") or not skill_meta.get("description"):
                missing.append(f"{canonical_skill}: skill frontmatter missing name or description")
        except OSError as exc:
            missing.append(f"{canonical_skill}: cannot read ({exc})")
    if not installed_skill.exists():
        missing.append(str(installed_skill))

    return {
        "platform": "claude-code",
        "repo_root": str(repo),
        "claude_home": str(home),
        "complete": not missing,
        "missing": missing,
        "warnings": warnings,
    }


def _validate_install_antigravity(
    repo_root: Path,
    antigravity_home: Path | None = None,
) -> dict[str, Any]:
    repo = require_dir(repo_root, "Repository root")
    home = (antigravity_home or (Path.home() / ".gemini" / "config")).expanduser().resolve()
    missing: list[str] = []
    warnings: list[str] = []

    canonical_agents = repo / "antigravity" / "agents"
    installed_agents = home / "agents"
    for name in CANONICAL_AGENT_FILES["antigravity"]:
        canonical = canonical_agents / name
        installed = installed_agents / name
        if not canonical.exists():
            missing.append(str(canonical))
            continue
        if not installed.exists():
            missing.append(str(installed))
        try:
            text = canonical.read_text(encoding="utf-8")
        except OSError as exc:
            missing.append(f"{canonical}: cannot read ({exc})")
            continue
        meta, body = _parse_frontmatter(text)
        if not meta:
            missing.append(f"{canonical}: missing YAML frontmatter")
            continue
        if not meta.get("name"):
            missing.append(f"{canonical}: frontmatter missing 'name'")
        if not meta.get("description"):
            missing.append(f"{canonical}: frontmatter missing 'description'")
        if "context-maintenance" not in body:
            warnings.append(f"{canonical}: body does not mention context-maintenance")

    canonical_skill = repo / "antigravity" / "skill" / "multiagent-workflow" / "SKILL.md"
    installed_skill = home / "skills" / "multiagent-workflow" / "SKILL.md"
    if not canonical_skill.exists():
        missing.append(str(canonical_skill))
    else:
        try:
            skill_text = canonical_skill.read_text(encoding="utf-8")
            skill_meta, _ = _parse_frontmatter(skill_text)
            if not skill_meta.get("name") or not skill_meta.get("description"):
                missing.append(f"{canonical_skill}: skill frontmatter missing name or description")
        except OSError as exc:
            missing.append(f"{canonical_skill}: cannot read ({exc})")
    if not installed_skill.exists():
        missing.append(str(installed_skill))

    return {
        "platform": "antigravity",
        "repo_root": str(repo),
        "antigravity_home": str(home),
        "complete": not missing,
        "missing": missing,
        "warnings": warnings,
    }


def discover_codex_skills(codex_home: Path) -> list[Path]:
    """Return sorted, deduplicated SKILL.md paths under codex_home.

    Scans <codex_home>/skills and <codex_home>/plugins recursively for any file
    named SKILL.md. Broken symlinks and unreadable directories are skipped
    silently rather than crashing the install.
    """
    roots = (codex_home / "skills", codex_home / "plugins")
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for candidate in root.rglob("SKILL.md"):
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved.is_file():
                seen.add(resolved)
    return sorted(seen)


def _skill_config_blocks(skill_paths: list[Path]) -> str:
    if not skill_paths:
        return ""
    lines = ["", "# Local skill assignments (auto-generated by install-codex).", ""]
    for skill_path in skill_paths:
        posix = skill_path.as_posix()
        lines.append("[[skills.config]]")
        lines.append(f'path = "{posix}"')
        lines.append("enabled = true")
        lines.append("")
    return "\n".join(lines)


def install_codex(
    repo_root: Path,
    codex_home: Path | None = None,
    deploy: bool = True,
) -> dict[str, Any]:
    """Generate codex-agents/*.toml from templates + local skills, optionally deploy.

    Steps:
      1. Discover SKILL.md paths under <codex_home>/skills and /plugins.
      2. For each templates/<role>.toml, copy to codex-agents/<role>.toml with
         [[skills.config]] blocks appended for each discovered skill.
      3. When deploy=True, also copy the generated files to <codex_home>/agents/.
    """
    repo = require_dir(repo_root, "Repository root")
    home = (codex_home or (Path.home() / ".codex")).expanduser().resolve()
    template_dir = repo / "codex-agents" / "templates"
    if not template_dir.is_dir():
        raise MultiAgentFileError(f"Codex template directory missing: {template_dir}")

    target_dir = repo / "codex-agents"
    target_dir.mkdir(parents=True, exist_ok=True)

    skills = discover_codex_skills(home)
    config_blocks = _skill_config_blocks(skills)

    generated: list[str] = []
    deployed: list[str] = []
    warnings: list[str] = []

    if not skills:
        warnings.append(f"No SKILL.md files found under {home}; generated TOMLs have no [[skills.config]] entries.")

    for name in CANONICAL_AGENT_FILES["codex"]:
        template_path = template_dir / name
        if not template_path.exists():
            warnings.append(f"Template missing: {template_path}")
            continue
        template_text = template_path.read_text(encoding="utf-8")
        if not template_text.endswith("\n"):
            template_text += "\n"
        rendered = template_text + config_blocks
        generated_path = target_dir / name
        generated_path.write_text(rendered, encoding="utf-8")
        generated.append(str(generated_path))

        if deploy:
            deploy_dir = home / "agents"
            deploy_dir.mkdir(parents=True, exist_ok=True)
            deploy_path = deploy_dir / name
            deploy_path.write_text(rendered, encoding="utf-8")
            deployed.append(str(deploy_path))

    return {
        "repo_root": str(repo),
        "codex_home": str(home),
        "skill_count": len(skills),
        "generated": generated,
        "deployed": deployed,
        "warnings": warnings,
        "complete": bool(generated) and not any("Template missing" in w for w in warnings),
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

    validate = subparsers.add_parser("validate-install")
    validate.add_argument("--repo-root", required=True)
    validate.add_argument(
        "--platform",
        default="codex",
        choices=SUPPORTED_PLATFORMS,
        help="Which platform install to validate (default: codex).",
    )
    validate.add_argument("--codex-home", default=None, help="Override ~/.codex (codex platform).")
    validate.add_argument("--claude-home", default=None, help="Override ~/.claude (claude-code platform).")
    validate.add_argument("--antigravity-home", default=None, help="Override ~/.gemini/config (antigravity platform).")

    install = subparsers.add_parser(
        "install-codex",
        help="Generate codex-agents/*.toml from templates + locally installed skills.",
    )
    install.add_argument("--repo-root", required=True)
    install.add_argument("--codex-home", default=None, help="Override ~/.codex.")
    install.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Only write codex-agents/*.toml in the repo; do not copy to <codex-home>/agents/.",
    )
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
        elif args.command == "status":
            payload = status_payload(Path(args.run))
        elif args.command == "install-codex":
            payload = install_codex(
                Path(args.repo_root),
                codex_home=Path(args.codex_home) if args.codex_home else None,
                deploy=not args.skip_deploy,
            )
        else:
            payload = validate_install(
                Path(args.repo_root),
                codex_home=Path(args.codex_home) if args.codex_home else None,
                platform=args.platform,
                claude_home=Path(args.claude_home) if args.claude_home else None,
                antigravity_home=Path(args.antigravity_home) if args.antigravity_home else None,
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("complete", True) else 2
    except MultiAgentFileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
