"""Shared constants and low-level helpers for MultiAgentSystem scripts.

`multiagent_files.py` (runtime) and `install.py` (setup) both import from here.
Nothing in this module writes to the user's home directory or a project's
`.multiagent/` folder — it is pure utilities and the canonical file-name
registry.
"""

from __future__ import annotations

import shutil
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback.
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
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
        "researcher.toml",
    ),
    "claude-code": (
        "pm.md",
        "developer.md",
        "developer-strong.md",
        "reviewer.md",
        "reviewer-strong.md",
        "researcher.md",
    ),
    "antigravity": (
        "pm.md",
        "developer.md",
        "developer-strong.md",
        "reviewer.md",
        "reviewer-strong.md",
        "researcher.md",
    ),
}

SUPPORTED_PLATFORMS = tuple(CANONICAL_AGENT_FILES.keys())


class MultiAgentFileError(RuntimeError):
    """Raised when a helper cannot safely prepare, install, or validate artifacts."""


def require_dir(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise MultiAgentFileError(f"{label} is not a directory: {resolved}")
    return resolved


def parse_toml(path: Path) -> dict:
    if tomllib is None:
        raise MultiAgentFileError(
            "Python tomllib is unavailable; use Python 3.11+ or `pip install tomli` for TOML validation"
        )
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise MultiAgentFileError(f"Cannot parse TOML {path}: {exc}") from exc


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
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


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def copy_tree(src: Path, dst: Path) -> list[str]:
    """Copy all files under src into dst, preserving relative paths.

    Returns the list of destination paths written (as strings).
    """
    written: list[str] = []
    for source_path in sorted(src.rglob("*")):
        if source_path.is_dir():
            continue
        relative = source_path.relative_to(src)
        target = dst / relative
        copy_file(source_path, target)
        written.append(str(target))
    return written
