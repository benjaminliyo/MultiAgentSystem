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


def _removesuffix(s: str, suffix: str) -> str:
    """str.removesuffix polyfill; needed while installs run on Python 3.8."""
    if suffix and s.endswith(suffix):
        return s[: -len(suffix)]
    return s


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
        else:
            if tomllib is not None:
                try:
                    parse_toml(installed)
                except MultiAgentFileError as exc:
                    missing.append(f"Installed {exc}")
            try:
                canonical_text = canonical.read_text(encoding="utf-8")
                installed_text = installed.read_text(encoding="utf-8")
            except OSError as exc:
                missing.append(f"{installed}: cannot read ({exc})")
            else:
                if installed_text != canonical_text:
                    missing.append(f"{installed} differs from {canonical}")
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

    _validate_shared_repo_files(repo, missing, warnings)

    if tomllib is None:
        warnings.append("tomllib unavailable; TOML validation requires Python 3.11+ or `pip install tomli`")

    return {
        "platform": "codex",
        "repo_root": str(repo),
        "codex_home": str(home),
        "complete": not missing,
        "missing": missing,
        "warnings": warnings,
    }


def _validate_shared_repo_files(repo: Path, missing: list[str], warnings: list[str]) -> None:
    """Parse-check shared repo artifacts when present.

    Skips silently when a directory/file is absent (minimal checkouts and test
    fixtures), but a present-yet-broken file is a hard failure and a partially
    populated hooks dir is a warning.
    """
    map_path = repo / "skills" / "role-skill-map.toml"
    if map_path.exists() and tomllib is not None:
        try:
            parse_toml(map_path)
        except MultiAgentFileError as exc:
            missing.append(str(exc))

    settings_example = repo / "claude-code" / "settings.example.json"
    if settings_example.exists():
        try:
            json.loads(settings_example.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            missing.append(f"{settings_example}: invalid JSON ({exc})")

    hooks_dir = repo / "claude-code" / "hooks"
    if hooks_dir.is_dir():
        expected = [
            "session-start-load-profile.ps1",
            "session-start-load-profile.sh",
            "stop-warn-unclosed-run.ps1",
            "stop-warn-unclosed-run.sh",
            "user-prompt-pm-mode.ps1",
            "user-prompt-pm-mode.sh",
            "user-prompt-pm-mode.py",
            "subagent-log.py",
        ]
        for name in expected:
            if not (hooks_dir / name).exists():
                warnings.append(f"hook script missing: {hooks_dir / name}")

    for template in (repo / "codex" / "hooks.json", repo / "antigravity" / "hooks.json"):
        if template.exists():
            try:
                json.loads(template.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                missing.append(f"{template}: invalid JSON ({exc})")


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
        # Publish-cleanliness: personal context-maintenance content belongs in
        # the gitignored local/ overlay, never in canonical files.
        if "context-maintenance" in body or "context_update_observation" in body:
            warnings.append(f"{canonical}: canonical body mentions context-maintenance (move to local/ overlay)")


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
    _validate_shared_repo_files(repo, missing, warnings)

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
    _validate_shared_repo_files(repo, missing, warnings)

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
# local overlays (local/overlays/roles/<role>.md, gitignored)
# ---------------------------------------------------------------------------


def load_role_overlay(repo_root: Path, role: str) -> str | None:
    """Personal per-role additions merged into installed copies only.

    `local/` is gitignored: canonical files ship clean to GitHub while a
    user's machine-specific role additions (e.g. references to private
    skills) still reach every installed agent.
    """
    path = repo_root / "local" / "overlays" / "roles" / f"{role}.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def append_overlay_markdown(text: str, overlay: str) -> str:
    """Append overlay content to a markdown agent body."""
    return text.rstrip("\n") + "\n\n" + overlay + "\n"


def insert_overlay_codex(toml_text: str, overlay: str) -> str:
    """Insert overlay content at the end of `developer_instructions`.

    The Codex templates hold role instructions in one multi-line TOML string
    (`developer_instructions = \"\"\" ... \"\"\"`); the overlay goes inside it,
    just before the closing quotes. Returns the text unchanged when the
    expected structure is not found (caller warns).
    """
    lines = toml_text.splitlines()
    open_index: int | None = None
    close_index: int | None = None
    for index, line in enumerate(lines):
        if open_index is None:
            if line.strip().startswith("developer_instructions") and line.rstrip().endswith('"""'):
                open_index = index
            continue
        if line.strip() == '"""':
            close_index = index
            break
    if open_index is None or close_index is None:
        return toml_text
    merged = lines[:close_index] + ["", overlay.rstrip()] + lines[close_index:]
    return "\n".join(merged) + ("\n" if toml_text.endswith("\n") else "")


# ---------------------------------------------------------------------------
# role-skill map (skills/role-skill-map.toml)
# ---------------------------------------------------------------------------


def _merge_skill_map_section(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Union one map section (categories + candidates), preserving order."""
    merged: dict[str, Any] = dict(base)
    for key in ("categories", "candidates"):
        seen = list(base.get(key, []))
        for item in extra.get(key, []):
            if item not in seen:
                seen.append(item)
        if seen:
            merged[key] = seen
    return merged


def merge_role_skill_maps(base: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """Overlay local/role-skill-map.toml onto the tracked map, additively.

    Local entries never remove tracked candidates — they only extend them.
    Roles that exist only in the local map are added as-is.
    """
    merged = dict(base)
    if isinstance(local.get("always"), dict):
        merged["always"] = _merge_skill_map_section(
            base.get("always", {}) if isinstance(base.get("always"), dict) else {},
            local["always"],
        )
    local_roles = local.get("roles")
    if isinstance(local_roles, dict):
        base_roles = base.get("roles") if isinstance(base.get("roles"), dict) else {}
        merged_roles = dict(base_roles)
        for role, entry in local_roles.items():
            if not isinstance(entry, dict):
                continue
            base_entry = base_roles.get(role)
            merged_roles[role] = _merge_skill_map_section(
                base_entry if isinstance(base_entry, dict) else {}, entry
            )
        merged["roles"] = merged_roles
    return merged


def load_role_skill_map(repo_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load skills/role-skill-map.toml merged with local/role-skill-map.toml.

    The tracked map is the shipped default; the gitignored local map adds
    personal per-role candidates on top (additive only). Returns
    (map or None, warnings).

    A missing or unparseable map disables scoping (installers fall back to
    their unscoped behavior) — it must never break an install. Missing is
    silent (both maps are optional by design); unparseable warns. A broken
    local map never disables the tracked one.
    """
    if tomllib is None:
        return None, ["tomllib unavailable (Python 3.11+ or `pip install tomli` required); skill scoping disabled"]

    warnings: list[str] = []
    map_path = repo_root / "skills" / "role-skill-map.toml"
    data: dict[str, Any] | None = None
    if map_path.exists():
        try:
            data = parse_toml(map_path)
        except MultiAgentFileError as exc:
            warnings.append(f"{exc}; skill scoping disabled")
            return None, warnings

    local_path = repo_root / "local" / "role-skill-map.toml"
    if local_path.exists():
        try:
            local_data = parse_toml(local_path)
        except MultiAgentFileError as exc:
            warnings.append(f"{exc}; local skill-map overlay skipped")
        else:
            data = merge_role_skill_maps(data or {}, local_data)

    return data, warnings


def role_skill_candidates(skill_map: dict[str, Any], role: str) -> set[str] | None:
    """Lower-cased candidate skill dir names for a role, or None when unmapped.

    Includes the map's [always] candidates so required capabilities (workflow
    recognition, skill search-and-install) survive hard allowlists.
    """
    roles = skill_map.get("roles", {})
    entry = roles.get(role) if isinstance(roles, dict) else None
    if not isinstance(entry, dict):
        return None
    candidates = {str(name).lower() for name in entry.get("candidates", [])}
    always = skill_map.get("always", {})
    if isinstance(always, dict):
        candidates |= {str(name).lower() for name in always.get("candidates", [])}
    return candidates


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
    skill_map, map_warnings = load_role_skill_map(repo)

    generated: list[str] = []
    deployed: list[str] = []
    warnings: list[str] = list(map_warnings)

    if not skills:
        warnings.append(f"No SKILL.md files found under {home}; generated TOMLs have no [[skills.config]] entries.")

    def skills_for_role(role: str) -> list[Path]:
        """Per-role allowlist from the role-skill map; unscoped on fallback."""
        if skill_map is None:
            return skills
        candidates = role_skill_candidates(skill_map, role)
        if candidates is None:
            warnings.append(f"Role '{role}' not in role-skill map; assigning all discovered skills.")
            return skills
        matched = [path for path in skills if path.parent.name.lower() in candidates]
        if not matched and skills:
            warnings.append(
                f"No installed skills matched the map for role '{role}'; "
                "assigning all discovered skills instead."
            )
            return skills
        return matched

    for name in CANONICAL_AGENT_FILES["codex"]:
        template_path = template_dir / name
        if not template_path.exists():
            warnings.append(f"Template missing: {template_path}")
            continue
        role = _removesuffix(name, ".toml")
        template_text = template_path.read_text(encoding="utf-8")
        if not template_text.endswith("\n"):
            template_text += "\n"
        overlay = load_role_overlay(repo, role)
        if overlay is not None:
            merged = insert_overlay_codex(template_text, overlay)
            if merged == template_text:
                warnings.append(
                    f"Overlay for '{role}' not applied: developer_instructions block not found in {name}"
                )
            template_text = merged
        rendered = template_text + _skill_config_blocks(skills_for_role(role))
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


def discover_claude_skills(claude_home: Path) -> set[str]:
    """Names (dir names) of skills installed under <claude_home>/skills/."""
    skills_root = claude_home / "skills"
    if not skills_root.is_dir():
        return set()
    return {
        entry.name
        for entry in skills_root.iterdir()
        if entry.is_dir() and (entry / "SKILL.md").is_file()
    }


def inject_skills_frontmatter(text: str, skill_names: list[str]) -> str:
    """Insert a `skills:` list into agent frontmatter (preload on spawn).

    Canonical agent files ship without `skills:` (concrete names are
    per-machine); this runs at deploy time only. Returns text unchanged when
    there is nothing to inject or no frontmatter to inject into.
    """
    if not skill_names:
        return text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            block = ["skills:"] + [f"  - {name}" for name in skill_names]
            merged = lines[:index] + block + lines[index:]
            return "\n".join(merged) + ("\n" if text.endswith("\n") else "")
    return text


def inject_permission_mode_frontmatter(text: str, mode: str) -> str:
    """Insert a `permissionMode:` line into agent frontmatter.

    Canonical Claude Code agent files ship without `permissionMode` (standard
    prompting); this runs at deploy time only, mirroring the Antigravity
    installer's Scoped Autonomy substitution. Returns text unchanged when the
    frontmatter already declares a mode or there is no frontmatter.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for index in range(1, len(lines)):
        stripped = lines[index].strip()
        if stripped == "---":
            merged = lines[:index] + [f"permissionMode: {mode}"] + lines[index:]
            return "\n".join(merged) + ("\n" if text.endswith("\n") else "")
        if stripped.startswith("permissionMode:"):
            return text
    return text


def install_claude_code(
    repo_root: Path,
    claude_home: Path | None = None,
    install_hooks: bool = True,
    subagent_permission_mode: str = "bypassPermissions",
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
    skills_injected: dict[str, list[str]] = {}
    switched_list: list[str] = []

    # Copy the skill and command before discovering installed skills, so a
    # first install already sees multiagent-workflow for `skills:` injection.
    skill_dst = home / "skills" / "multiagent-workflow"
    installed.extend(copy_tree(source_skill, skill_dst))

    command_dst = home / "commands" / "multiagent.md"
    copy_file(source_command, command_dst)
    installed.append(str(command_dst))

    skill_map, map_warnings = load_role_skill_map(repo)
    warnings.extend(map_warnings)
    available_skills = discover_claude_skills(home)

    for name in CANONICAL_AGENT_FILES["claude-code"]:
        src = source_agents / name
        if not src.exists():
            warnings.append(f"Missing agent file in repo: {src}")
            continue
        role = _removesuffix(name, ".md")
        text = src.read_text(encoding="utf-8")
        # PM runs on the main thread (the session adopts its role), so its
        # permission mode is whatever the user launched the session with.
        if role != "pm" and subagent_permission_mode != "default":
            switched = inject_permission_mode_frontmatter(text, subagent_permission_mode)
            if switched == text:
                warnings.append(
                    f"permissionMode not injected into {name}: frontmatter missing or already sets a mode"
                )
            else:
                text = switched
                switched_list.append(role)
        if skill_map is not None and available_skills:
            candidates = role_skill_candidates(skill_map, role)
            if candidates is not None:
                matched = sorted(
                    skill_name
                    for skill_name in available_skills
                    if skill_name.lower() in candidates
                )
                if matched:
                    text = inject_skills_frontmatter(text, matched)
                    skills_injected[role] = matched
        overlay = load_role_overlay(repo, role)
        if overlay is not None:
            text = append_overlay_markdown(text, overlay)
        dst = home / "agents" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        installed.append(str(dst))

    hooks_result: dict[str, Any] = {"wired": False, "reason": "skipped"}
    if install_hooks:
        hooks_result = _wire_claude_hooks(repo, home)

    return {
        "platform": "claude-code",
        "repo_root": str(repo),
        "claude_home": str(home),
        "installed": installed,
        "skills_injected": skills_injected,
        "switched_permissions": switched_list,
        "hooks": hooks_result,
        "warnings": warnings,
        "complete": bool(installed) and not warnings,
    }


# (event, script base name, kind). `shell` scripts have .ps1/.sh variants
# chosen per host OS; `python` scripts are a single cross-platform file.
CLAUDE_HOOKS = (
    ("SessionStart", "session-start-load-profile", "shell"),
    ("UserPromptSubmit", "user-prompt-pm-mode", "shell"),
    ("SubagentStart", "subagent-log", "python"),
    ("SubagentStop", "subagent-log", "python"),
    ("Stop", "stop-warn-unclosed-run", "shell"),
)


def _wire_claude_hooks(repo: Path, home: Path) -> dict[str, Any]:
    """Idempotently merge the multiagent hook entries into settings.json.

    Chooses PowerShell command strings on Windows, bash on other platforms.
    Existing hook entries that already point at the same script paths are
    left in place (no duplicates). Any unrelated hooks the user has wired
    up are preserved untouched.
    """
    hooks_dir = repo / "claude-code" / "hooks"
    if not hooks_dir.is_dir():
        return {"wired": False, "reason": f"hooks dir missing: {hooks_dir}"}

    is_windows = _platform.system() == "Windows"

    def hook_entry(script_base: str, kind: str) -> tuple[str, str]:
        """Return (script path marker, full command) for one hook script."""
        if kind == "python":
            script = (hooks_dir / f"{script_base}.py").as_posix()
            return script, f'python "{script}"'
        if is_windows:
            script = (hooks_dir / f"{script_base}.ps1").as_posix()
            return script, f'powershell -NoProfile -ExecutionPolicy Bypass -File "{script}"'
        script = (hooks_dir / f"{script_base}.sh").as_posix()
        return script, f'bash "{script}"'

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

    changed = False
    for event, script_base, kind in CLAUDE_HOOKS:
        marker, command = hook_entry(script_base, kind)
        if _add_hook(event, marker, command):
            changed = True

    if changed or not settings_path.exists():
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    return {
        "wired": True,
        "path": str(settings_path),
        "shell": "powershell" if is_windows else "bash",
        "changed": changed,
    }


# ---------------------------------------------------------------------------
# install-antigravity
# ---------------------------------------------------------------------------


def install_antigravity(
    repo_root: Path,
    antigravity_home: Path | None = None,
    subagent_permission_mode: str = "bypassPermissions",
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
    switched_list: list[str] = []

    for name in CANONICAL_AGENT_FILES["antigravity"]:
        src = source_agents / name
        if not src.exists():
            warnings.append(f"Missing agent file in repo: {src}")
            continue
        text = src.read_text(encoding="utf-8")

        role = _removesuffix(name, ".md")
        if role != "pm" and subagent_permission_mode != "plan":
            target = "permissionMode: plan"
            count = text.count(target)
            if count != 1:
                warnings.append(
                    f"Expected exactly one '{target}' in canonical {name} to substitute, found {count}"
                )
            else:
                text = text.replace(target, f"permissionMode: {subagent_permission_mode}", 1)
                switched_list.append(role)

        overlay = load_role_overlay(repo, role)
        if overlay is not None:
            text = append_overlay_markdown(text, overlay)
        dst = home / "agents" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        installed.append(str(dst))

    skill_dst = home / "skills" / "multiagent-workflow"
    installed.extend(copy_tree(source_skill, skill_dst))

    return {
        "platform": "antigravity",
        "repo_root": str(repo),
        "antigravity_home": str(home),
        "installed": installed,
        "switched_permissions": switched_list,
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
    antigravity_subagent_permission_mode: str = "bypassPermissions",
    claude_subagent_permission_mode: str = "bypassPermissions",
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
                    subagent_permission_mode=claude_subagent_permission_mode,
                )
            else:
                result = install_antigravity(
                    repo_root,
                    antigravity_home=antigravity_home,
                    subagent_permission_mode=antigravity_subagent_permission_mode,
                )
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
    install_claude.add_argument(
        "--claude-subagent-permission-mode",
        default="bypassPermissions",
        choices=["bypassPermissions", "acceptEdits", "default"],
        help="Permission mode injected into deployed subagents (default: bypassPermissions; 'default' injects nothing).",
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
    install_ag.add_argument(
        "--antigravity-subagent-permission-mode",
        default="bypassPermissions",
        choices=["bypassPermissions", "plan"],
        help="Permission mode for deployed subagents (default: bypassPermissions).",
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
    install_all.add_argument(
        "--antigravity-subagent-permission-mode",
        default="bypassPermissions",
        choices=["bypassPermissions", "plan"],
        help="Permission mode for deployed subagents (default: bypassPermissions).",
    )
    install_all.add_argument(
        "--claude-subagent-permission-mode",
        default="bypassPermissions",
        choices=["bypassPermissions", "acceptEdits", "default"],
        help="Permission mode injected into deployed Claude Code subagents (default: bypassPermissions; 'default' injects nothing).",
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
                subagent_permission_mode=args.claude_subagent_permission_mode,
            )
        elif args.command == "install-antigravity":
            payload = install_antigravity(
                Path(args.repo_root),
                antigravity_home=Path(args.antigravity_home) if args.antigravity_home else None,
                subagent_permission_mode=args.antigravity_subagent_permission_mode,
            )
        elif args.command == "install":
            payload = install_dispatch(
                Path(args.repo_root),
                platform=args.platform,
                codex_home=Path(args.codex_home) if args.codex_home else None,
                claude_home=Path(args.claude_home) if args.claude_home else None,
                antigravity_home=Path(args.antigravity_home) if args.antigravity_home else None,
                install_hooks=not args.no_hooks,
                antigravity_subagent_permission_mode=args.antigravity_subagent_permission_mode,
                claude_subagent_permission_mode=args.claude_subagent_permission_mode,
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
