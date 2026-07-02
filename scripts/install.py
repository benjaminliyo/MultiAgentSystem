#!/usr/bin/env python3
"""Installer and validator for the PM-led MultiAgentSystem.

One-command setup for each supported CLI platform:

    python scripts/install.py install --platform claude-code --repo-root .
    python scripts/install.py install --platform codex --repo-root .
    python scripts/install.py install --platform antigravity --repo-root .
    python scripts/install.py install --platform all --repo-root .

Also exposes per-platform subcommands (`install-codex`, `install-claude-code`,
`install-antigravity`) and `validate-install`.

Runtime helpers (message logging, run-folder setup) live in
`multiagent_files.py`; this file is intentionally scoped to install-time
concerns so a bug here can only touch the user's CLI config, not any
project's `.multiagent/` state.
"""

from __future__ import annotations

import argparse
import json
import platform as _platform
import sys
from pathlib import Path
from typing import Any

# Support both `python scripts/install.py ...` (direct invocation) and
# `python -m scripts.install ...` / import from tests. When run directly the
# project root isn't on sys.path, so absolute imports of the `scripts` package
# would fail.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts._common import (
    CANONICAL_AGENT_FILES,
    MultiAgentFileError,
    SUPPORTED_PLATFORMS,
    copy_file,
    copy_tree,
    parse_frontmatter,
    parse_toml,
    require_dir,
    tomllib,
)


# ---------------------------------------------------------------------------
# validate-install
# ---------------------------------------------------------------------------


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


def _validate_frontmatter_agents(
    canonical_agents: Path,
    installed_agents: Path,
    platform_key: str,
    missing: list[str],
    warnings: list[str],
) -> None:
    """Shared frontmatter validation used by Claude Code and Antigravity."""
    for name in CANONICAL_AGENT_FILES[platform_key]:
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
        meta, body = parse_frontmatter(text)
        if not meta:
            missing.append(f"{canonical}: missing YAML frontmatter")
            continue
        if not meta.get("name"):
            missing.append(f"{canonical}: frontmatter missing 'name'")
        if not meta.get("description"):
            missing.append(f"{canonical}: frontmatter missing 'description'")
        if "context-maintenance" not in body:
            warnings.append(f"{canonical}: body does not mention context-maintenance")


def _validate_install_claude_code(
    repo_root: Path,
    claude_home: Path | None = None,
) -> dict[str, Any]:
    repo = require_dir(repo_root, "Repository root")
    home = (claude_home or (Path.home() / ".claude")).expanduser().resolve()
    missing: list[str] = []
    warnings: list[str] = []

    _validate_frontmatter_agents(
        repo / "claude-code" / "agents",
        home / "agents",
        "claude-code",
        missing,
        warnings,
    )

    canonical_skill = repo / "claude-code" / "skill" / "multiagent-workflow" / "SKILL.md"
    installed_skill = home / "skills" / "multiagent-workflow" / "SKILL.md"
    if not canonical_skill.exists():
        missing.append(str(canonical_skill))
    else:
        try:
            skill_text = canonical_skill.read_text(encoding="utf-8")
            skill_meta, _ = parse_frontmatter(skill_text)
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

    _validate_frontmatter_agents(
        repo / "antigravity" / "agents",
        home / "agents",
        "antigravity",
        missing,
        warnings,
    )

    canonical_skill = repo / "antigravity" / "skill" / "multiagent-workflow" / "SKILL.md"
    installed_skill = home / "skills" / "multiagent-workflow" / "SKILL.md"
    if not canonical_skill.exists():
        missing.append(str(canonical_skill))
    else:
        try:
            skill_text = canonical_skill.read_text(encoding="utf-8")
            skill_meta, _ = parse_frontmatter(skill_text)
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


# ---------------------------------------------------------------------------
# install-codex
# ---------------------------------------------------------------------------


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
      3. When deploy=True, also copy the generated files to <codex_home>/agents/
         and the recognition skill to <codex_home>/skills/multiagent-workflow/.
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

    # The recognition skill is a required install alongside the agents; without
    # it, "run the multiagent workflow" won't reliably resolve to the pm agent.
    if deploy:
        source_skill = repo / "codex-skill" / "multiagent-workflow"
        if source_skill.is_dir():
            skill_dst = home / "skills" / "multiagent-workflow"
            deployed.extend(copy_tree(source_skill, skill_dst))
        else:
            warnings.append(f"Codex skill source missing: {source_skill}")

    return {
        "repo_root": str(repo),
        "codex_home": str(home),
        "skill_count": len(skills),
        "generated": generated,
        "deployed": deployed,
        "warnings": warnings,
        "complete": bool(generated) and not any("Template missing" in w for w in warnings),
    }


# ---------------------------------------------------------------------------
# install-claude-code
# ---------------------------------------------------------------------------


def install_claude_code(
    repo_root: Path,
    claude_home: Path | None = None,
    install_hooks: bool = True,
) -> dict[str, Any]:
    """Install the multi-agent workflow into ~/.claude/.

    Copies agents, the multiagent-workflow skill, and the /multiagent slash
    command. Optionally merges hook wiring into ~/.claude/settings.json,
    rewriting absolute paths to point at this repo checkout.
    """
    repo = require_dir(repo_root, "Repository root")
    home = (claude_home or (Path.home() / ".claude")).expanduser().resolve()

    source_agents = repo / "claude-code" / "agents"
    source_skill = repo / "claude-code" / "skill" / "multiagent-workflow"
    source_command = repo / "claude-code" / "commands" / "multiagent.md"

    if not source_agents.is_dir():
        raise MultiAgentFileError(f"Missing source: {source_agents}")
    if not source_skill.is_dir():
        raise MultiAgentFileError(f"Missing source: {source_skill}")
    if not source_command.is_file():
        raise MultiAgentFileError(f"Missing source: {source_command}")

    installed: list[str] = []
    warnings: list[str] = []

    for name in CANONICAL_AGENT_FILES["claude-code"]:
        src = source_agents / name
        if not src.exists():
            warnings.append(f"Missing agent file in repo: {src}")
            continue
        dst = home / "agents" / name
        copy_file(src, dst)
        installed.append(str(dst))

    skill_dst = home / "skills" / "multiagent-workflow"
    installed.extend(copy_tree(source_skill, skill_dst))

    command_dst = home / "commands" / "multiagent.md"
    copy_file(source_command, command_dst)
    installed.append(str(command_dst))

    hooks_result: dict[str, Any] = {"wired": False, "reason": "skipped"}
    if install_hooks:
        hooks_result = _wire_claude_hooks(repo, home)

    return {
        "platform": "claude-code",
        "repo_root": str(repo),
        "claude_home": str(home),
        "installed": installed,
        "hooks": hooks_result,
        "warnings": warnings,
        "complete": bool(installed) and not warnings,
    }


def _wire_claude_hooks(repo: Path, home: Path) -> dict[str, Any]:
    """Idempotently merge SessionStart + Stop hook entries into settings.json.

    Chooses PowerShell command strings on Windows, bash on other platforms.
    Existing hook entries that already point at the same script paths are
    left in place (no duplicates). Any unrelated hooks the user has wired
    up are preserved untouched.
    """
    hooks_dir = repo / "claude-code" / "hooks"
    if not hooks_dir.is_dir():
        return {"wired": False, "reason": f"hooks dir missing: {hooks_dir}"}

    is_windows = _platform.system() == "Windows"
    if is_windows:
        session_start_script = (hooks_dir / "session-start-load-profile.ps1").as_posix()
        stop_script = (hooks_dir / "stop-warn-unclosed-run.ps1").as_posix()
        session_start_cmd = (
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "{session_start_script}"'
        )
        stop_cmd = (
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "{stop_script}"'
        )
    else:
        session_start_script = (hooks_dir / "session-start-load-profile.sh").as_posix()
        stop_script = (hooks_dir / "stop-warn-unclosed-run.sh").as_posix()
        session_start_cmd = f'bash "{session_start_script}"'
        stop_cmd = f'bash "{stop_script}"'

    settings_path = home / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {
                "wired": False,
                "reason": f"cannot parse existing settings.json: {exc}",
                "path": str(settings_path),
            }
        if not isinstance(settings, dict):
            return {
                "wired": False,
                "reason": "existing settings.json is not a JSON object",
                "path": str(settings_path),
            }
    else:
        settings = {}

    hooks_block = settings.setdefault("hooks", {})
    if not isinstance(hooks_block, dict):
        return {
            "wired": False,
            "reason": "existing settings.json 'hooks' is not an object",
            "path": str(settings_path),
        }

    def _add_hook(event: str, script_path_marker: str, command: str) -> bool:
        """Add a hook entry if no existing entry points at this script.

        Uses the script path as the uniqueness marker so re-running the
        installer after `git pull` (or with a different shell) upgrades
        the command string rather than appending duplicates.
        """
        entries = hooks_block.setdefault(event, [])
        if not isinstance(entries, list):
            return False
        for group in entries:
            if not isinstance(group, dict):
                continue
            inner = group.get("hooks", [])
            if not isinstance(inner, list):
                continue
            for hook in inner:
                if not isinstance(hook, dict):
                    continue
                existing_cmd = hook.get("command", "")
                if script_path_marker in existing_cmd:
                    if existing_cmd != command:
                        hook["command"] = command
                        return True
                    return False
        entries.append({"hooks": [{"type": "command", "command": command}]})
        return True

    changed_session = _add_hook("SessionStart", session_start_script, session_start_cmd)
    changed_stop = _add_hook("Stop", stop_script, stop_cmd)

    if changed_session or changed_stop or not settings_path.exists():
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    return {
        "wired": True,
        "path": str(settings_path),
        "shell": "powershell" if is_windows else "bash",
        "changed": bool(changed_session or changed_stop),
    }


# ---------------------------------------------------------------------------
# install-antigravity
# ---------------------------------------------------------------------------


def install_antigravity(
    repo_root: Path,
    antigravity_home: Path | None = None,
) -> dict[str, Any]:
    """Install the multi-agent workflow into ~/.gemini/config/."""
    repo = require_dir(repo_root, "Repository root")
    home = (antigravity_home or (Path.home() / ".gemini" / "config")).expanduser().resolve()

    source_agents = repo / "antigravity" / "agents"
    source_skill = repo / "antigravity" / "skill" / "multiagent-workflow"

    if not source_agents.is_dir():
        raise MultiAgentFileError(f"Missing source: {source_agents}")
    if not source_skill.is_dir():
        raise MultiAgentFileError(f"Missing source: {source_skill}")

    installed: list[str] = []
    warnings: list[str] = []

    for name in CANONICAL_AGENT_FILES["antigravity"]:
        src = source_agents / name
        if not src.exists():
            warnings.append(f"Missing agent file in repo: {src}")
            continue
        dst = home / "agents" / name
        copy_file(src, dst)
        installed.append(str(dst))

    skill_dst = home / "skills" / "multiagent-workflow"
    installed.extend(copy_tree(source_skill, skill_dst))

    return {
        "platform": "antigravity",
        "repo_root": str(repo),
        "antigravity_home": str(home),
        "installed": installed,
        "warnings": warnings,
        "complete": bool(installed) and not warnings,
    }


# ---------------------------------------------------------------------------
# install --platform <name|all>
# ---------------------------------------------------------------------------


def install_dispatch(
    repo_root: Path,
    platform: str,
    codex_home: Path | None = None,
    claude_home: Path | None = None,
    antigravity_home: Path | None = None,
    install_hooks: bool = True,
) -> dict[str, Any]:
    """Run one or all platform installers and return a combined payload."""
    if platform not in SUPPORTED_PLATFORMS and platform != "all":
        raise MultiAgentFileError(
            f"Unknown platform: {platform}. Supported: {', '.join(SUPPORTED_PLATFORMS)}, all"
        )

    targets = SUPPORTED_PLATFORMS if platform == "all" else (platform,)
    results: dict[str, Any] = {}
    all_complete = True

    for target in targets:
        try:
            if target == "codex":
                result = install_codex(repo_root, codex_home=codex_home, deploy=True)
            elif target == "claude-code":
                result = install_claude_code(
                    repo_root,
                    claude_home=claude_home,
                    install_hooks=install_hooks,
                )
            else:
                result = install_antigravity(repo_root, antigravity_home=antigravity_home)
        except MultiAgentFileError as exc:
            result = {"platform": target, "error": str(exc), "complete": False}
        results[target] = result
        if not result.get("complete", False):
            all_complete = False

    return {
        "platform": platform,
        "results": results,
        "complete": all_complete,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    install_codex_cmd = subparsers.add_parser(
        "install-codex",
        help="Generate codex-agents/*.toml from templates + locally installed skills.",
    )
    install_codex_cmd.add_argument("--repo-root", required=True)
    install_codex_cmd.add_argument("--codex-home", default=None, help="Override ~/.codex.")
    install_codex_cmd.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Only write codex-agents/*.toml in the repo; do not copy to <codex-home>/agents/.",
    )

    install_claude = subparsers.add_parser(
        "install-claude-code",
        help="Copy agents, skill, and slash command into ~/.claude/ and wire hooks.",
    )
    install_claude.add_argument("--repo-root", required=True)
    install_claude.add_argument("--claude-home", default=None, help="Override ~/.claude.")
    install_claude.add_argument(
        "--no-hooks",
        action="store_true",
        help="Skip merging hook wiring into ~/.claude/settings.json.",
    )

    install_ag = subparsers.add_parser(
        "install-antigravity",
        help="Copy agents and skill into ~/.gemini/config/.",
    )
    install_ag.add_argument("--repo-root", required=True)
    install_ag.add_argument(
        "--antigravity-home",
        default=None,
        help="Override ~/.gemini/config.",
    )

    install_all = subparsers.add_parser(
        "install",
        help="One-command installer. Use --platform to pick codex, claude-code, antigravity, or all.",
    )
    install_all.add_argument("--repo-root", required=True)
    install_all.add_argument(
        "--platform",
        required=True,
        choices=list(SUPPORTED_PLATFORMS) + ["all"],
    )
    install_all.add_argument("--codex-home", default=None, help="Override ~/.codex.")
    install_all.add_argument("--claude-home", default=None, help="Override ~/.claude.")
    install_all.add_argument(
        "--antigravity-home",
        default=None,
        help="Override ~/.gemini/config.",
    )
    install_all.add_argument(
        "--no-hooks",
        action="store_true",
        help="Skip Claude Code hook wiring (applies only to claude-code / all).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "install-codex":
            payload = install_codex(
                Path(args.repo_root),
                codex_home=Path(args.codex_home) if args.codex_home else None,
                deploy=not args.skip_deploy,
            )
        elif args.command == "install-claude-code":
            payload = install_claude_code(
                Path(args.repo_root),
                claude_home=Path(args.claude_home) if args.claude_home else None,
                install_hooks=not args.no_hooks,
            )
        elif args.command == "install-antigravity":
            payload = install_antigravity(
                Path(args.repo_root),
                antigravity_home=Path(args.antigravity_home) if args.antigravity_home else None,
            )
        elif args.command == "install":
            payload = install_dispatch(
                Path(args.repo_root),
                platform=args.platform,
                codex_home=Path(args.codex_home) if args.codex_home else None,
                claude_home=Path(args.claude_home) if args.claude_home else None,
                antigravity_home=Path(args.antigravity_home) if args.antigravity_home else None,
                install_hooks=not args.no_hooks,
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
