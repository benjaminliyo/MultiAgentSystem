#!/usr/bin/env python
"""find_skill.py — deterministic engine behind the find-skill capability.

Search a curated skill registry, list installed skills, and install an
approved candidate into a platform's skills directory. This is the shared
engine; each platform ships a thin SKILL.md wrapper that tells the agent
when to call it (see docs/find-skill-implementation-guide.md).

Design constraints:
- stdlib only, Python 3.8 compatible (tomllib with tomli fallback).
- Deterministic keyword search — weak models must not have to "recall"
  which skills exist.
- `install` never runs without an explicit registry entry and prints a
  reminder that PM/client approval is required first (the skills framework
  routes every install through skill_need -> PM -> client; see
  docs/skills-framework.md).

Commands:
  search <query...>       rank registry entries against a query
  list-installed          show installed skills per platform
  install <name>          clone + copy an approved candidate into a platform
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore

DEFAULT_REGISTRY = Path(__file__).resolve().parent / "registry.toml"
REPO_REGISTRY = Path(__file__).resolve().parent.parent / "skills" / "registry.toml"

PLATFORM_SKILL_DIRS = {
    "claude-code": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".codex" / "skills",
    "antigravity": Path.home() / ".gemini" / "config" / "skills",
}

# Skills that satisfy the search-and-install capability itself; used by the
# skills-inventory check in multiagent_files.py and reported by list-installed.
SEARCH_CAPABILITY_NAMES = {"find-skill", "skill-installer", "find-skills"}


def _fail(message: str, code: int = 1) -> "int":
    print(f"error: {message}", file=sys.stderr)
    return code


def load_registry(path: Path) -> list:
    if tomllib is None:
        raise RuntimeError(
            "tomllib unavailable (Python 3.11+ or `pip install tomli` required)"
        )
    if not path.is_file():
        raise RuntimeError(f"registry not found: {path}")
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return list(data.get("skills", []))


def resolve_registry(arg: str) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    # Installed layout bundles registry.toml next to this script; the canonical
    # repo layout keeps it at skills/registry.toml.
    if DEFAULT_REGISTRY.is_file():
        return DEFAULT_REGISTRY
    return REPO_REGISTRY


def _tokens(text: str) -> list:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def score_entry(entry: dict, query_tokens: list) -> int:
    name_tokens = set(_tokens(entry.get("name", "")))
    keyword_tokens = set()
    for kw in entry.get("keywords", []):
        keyword_tokens.update(_tokens(kw))
    category_tokens = set(_tokens(entry.get("category", "")))
    description_tokens = set(_tokens(entry.get("description", "")))
    score = 0
    for token in query_tokens:
        if token in name_tokens:
            score += 4
        if token in keyword_tokens:
            score += 3
        if token in category_tokens:
            score += 2
        if token in description_tokens:
            score += 1
    return score


def cmd_search(args: argparse.Namespace) -> int:
    registry_path = resolve_registry(args.registry)
    try:
        entries = load_registry(registry_path)
    except RuntimeError as exc:
        return _fail(str(exc))
    query_tokens = _tokens(" ".join(args.query))
    if not query_tokens:
        return _fail("empty query")
    ranked = []
    for entry in entries:
        score = score_entry(entry, query_tokens)
        if score > 0:
            ranked.append((score, entry))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].get("name", "")))
    ranked = ranked[: args.limit]
    if args.json:
        print(json.dumps(
            [dict(entry, score=score) for score, entry in ranked], indent=2
        ))
        return 0
    if not ranked:
        print(
            "No registry match. Next layers: the platform's native catalog "
            "(Codex skill-installer) or public search (https://skills.sh, "
            "`npx skills find <query>`). Propose candidates via skill_need; "
            "never install from public search without PM/client approval."
        )
        return 0
    print(f"registry: {registry_path}")
    for score, entry in ranked:
        print(f"\n{entry.get('name')}  (score {score}, trust: {entry.get('trust', 'unverified')})")
        print(f"  {entry.get('description', '')}")
        print(f"  source:  {entry.get('source_repo', '?')}  [{entry.get('source_path', '?')}]")
        print(f"  install: python {Path(__file__).name} install {entry.get('name')} --platform <platform>")
        if entry.get("install"):
            print(f"           (or: {entry['install']})")
    print(
        "\nReminder: installation requires PM/client approval first "
        "(skill_need -> PM -> client, per-run install budget applies)."
    )
    return 0


def read_frontmatter(skill_md: Path) -> dict:
    meta = {}
    try:
        lines = skill_md.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return meta
    if not lines or lines[0].strip() != "---":
        return meta
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if match:
            meta[match.group(1).lower()] = match.group(2).strip().strip("\"'")
    return meta


def installed_skills(platform: str) -> list:
    root = PLATFORM_SKILL_DIRS[platform]
    found = []
    if not root.is_dir():
        return found
    for entry in sorted(root.iterdir()):
        skill_md = entry / "SKILL.md"
        if entry.is_dir() and skill_md.is_file():
            meta = read_frontmatter(skill_md)
            found.append({
                "name": entry.name,
                "description": meta.get("description", ""),
            })
    return found


def cmd_list_installed(args: argparse.Namespace) -> int:
    platforms = list(PLATFORM_SKILL_DIRS) if args.platform == "all" else [args.platform]
    result = {}
    for platform in platforms:
        skills = installed_skills(platform)
        has_search = any(s["name"] in SEARCH_CAPABILITY_NAMES for s in skills)
        result[platform] = {
            "skills_dir": str(PLATFORM_SKILL_DIRS[platform]),
            "skills": skills,
            "search_and_install_capability": has_search,
        }
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    for platform, info in result.items():
        names = [s["name"] for s in info["skills"]] or ["(none)"]
        cap = "present" if info["search_and_install_capability"] else "MISSING"
        print(f"{platform}: {', '.join(names)}")
        print(f"  search-and-install capability: {cap}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    registry_path = resolve_registry(args.registry)
    try:
        entries = load_registry(registry_path)
    except RuntimeError as exc:
        return _fail(str(exc))
    entry = next((e for e in entries if e.get("name") == args.name), None)
    if entry is None:
        return _fail(
            f"'{args.name}' is not in the registry ({registry_path}). "
            "Only registry entries can be installed by this script; for public "
            "candidates, route the install command through PM/client approval "
            "and run it manually."
        )
    repo = entry.get("source_repo")
    sub_path = entry.get("source_path")
    if not repo or not sub_path:
        hint = entry.get("install", "no install command recorded")
        return _fail(f"entry has no clonable source; use the recorded command: {hint}", 2)

    dest_root = Path(args.dest).expanduser() if args.dest else PLATFORM_SKILL_DIRS[args.platform]
    dest = dest_root / args.name
    if dest.exists() and not args.force:
        return _fail(f"already installed: {dest} (use --force to overwrite)")

    print(
        "Reminder: this install must already be PM/client-approved and within "
        "the per-run install budget (docs/skills-framework.md)."
    )
    tmp = tempfile.mkdtemp(prefix="find-skill-")
    try:
        clone = subprocess.run(
            ["git", "clone", "--depth", "1", repo, tmp],
            capture_output=True, text=True,
        )
        if clone.returncode != 0:
            return _fail(f"git clone failed: {clone.stderr.strip()}")
        src = Path(tmp) / sub_path
        if not (src / "SKILL.md").is_file():
            return _fail(
                f"{sub_path} in {repo} has no SKILL.md — upstream layout changed; "
                "fix source_path in the registry before installing"
            )
        if dest.exists():
            shutil.rmtree(dest)
        dest_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"installed: {dest}")
    print("Restart the session (or open a new thread) so the platform discovers it.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", default="", help="registry.toml path (default: bundled, then repo)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="rank registry entries against a query")
    p_search.add_argument("query", nargs="+")
    p_search.add_argument("--limit", type=int, default=5)
    p_search.add_argument("--json", action="store_true")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser("list-installed", help="show installed skills per platform")
    p_list.add_argument("--platform", choices=["all"] + list(PLATFORM_SKILL_DIRS), default="all")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list_installed)

    p_install = sub.add_parser("install", help="install an approved registry entry")
    p_install.add_argument("name")
    p_install.add_argument("--platform", choices=list(PLATFORM_SKILL_DIRS), required=True)
    p_install.add_argument("--dest", default="", help="override the platform skills dir")
    p_install.add_argument("--force", action="store_true")
    p_install.set_defaults(func=cmd_install)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
