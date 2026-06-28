#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) not found. Install: https://cli.github.com/"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Log in to GitHub (browser flow — works on phone too):"
  gh auth login -h github.com -p https -w
fi

echo "Pushing to habitual-reset/danu ..."
git push -u origin main

echo ""
echo "Verify these links in your browser:"
echo "  https://github.com/habitual-reset/danu/blob/main/COMPLIANCE.md"
echo "  https://github.com/habitual-reset/danu/blob/main/PRIVACY.md"
echo "  https://github.com/habitual-reset/danu/blob/main/TERMS.md"