#!/usr/bin/env bash
# One-line installer for the MultiAgentSystem.
#
# Usage:
#   ./scripts/install.sh claude-code
#   ./scripts/install.sh antigravity
#   ./scripts/install.sh codex
#   ./scripts/install.sh all
#   ./scripts/install.sh claude-code --no-hooks
#
# Re-run this script after `git pull` to update an existing install.
# Files are overwritten; hook wiring is merged idempotently.
set -euo pipefail

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    PYTHON="python"
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
helper="$script_dir/install.py"

platform="${1:-}"
shift || true

if [[ -z "$platform" ]]; then
    echo "Which platform do you want to install for?"
    echo "  1) claude-code"
    echo "  2) antigravity"
    echo "  3) codex"
    echo "  4) all"
    read -r -p "Enter 1-4: " choice
    case "$choice" in
        1) platform="claude-code" ;;
        2) platform="antigravity" ;;
        3) platform="codex" ;;
        4) platform="all" ;;
        *) echo "Invalid choice: $choice" >&2; exit 1 ;;
    esac
fi

case "$platform" in
    codex|claude-code|antigravity|all) ;;
    *) echo "Unknown platform: $platform" >&2; exit 1 ;;
esac

echo "Running: $PYTHON $helper install --repo-root $repo_root --platform $platform $*"
"$PYTHON" "$helper" install --repo-root "$repo_root" --platform "$platform" "$@"

echo
echo "Install complete. Restart your CLI session so the new agents/skills load."
echo "To update later: re-run './scripts/install.sh $platform'."
