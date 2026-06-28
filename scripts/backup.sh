#!/usr/bin/env bash
# Commit and push DANU to GitHub if there are changes.
set -euo pipefail

cd "$(dirname "$0")/.."

MSG="${1:-chore: backup $(date +%Y-%m-%d_%H%M)}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Run: source ~/.local/bin/env"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Not logged into GitHub. Run: gh auth login"
  exit 1
fi

if git diff --quiet && git diff --cached --quiet; then
  echo "No changes to backup."
  exit 0
fi

# Safety: refuse to commit .env
if git status --porcelain | grep -qE '^.. \.env$|^A  \.env$'; then
  echo "ERROR: .env is staged. Unstaging for safety."
  git reset HEAD .env 2>/dev/null || true
fi

git add -A
if git diff --cached --quiet; then
  echo "No changes to backup after excluding secrets."
  exit 0
fi

git commit -m "$MSG"
git push origin main
echo "Backed up to GitHub: $(git rev-parse --short HEAD)"