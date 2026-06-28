#!/usr/bin/env bash
# Merge .secrets-drop into .env, then delete the drop file.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DROP="$ROOT/.secrets-drop"
ENV="$ROOT/.env"

if [[ ! -f "$DROP" ]]; then
  echo "No .secrets-drop file found."
  echo "Create one: cp .secrets-drop.example .secrets-drop"
  echo "Edit in TextEdit, save, then run this script again."
  exit 1
fi

touch "$ENV"
chmod 600 "$ENV" 2>/dev/null || true

python3 <<'PY'
from pathlib import Path

root = Path(__file__).resolve().parent.parent if False else Path(".")
import os
os.chdir("'"$ROOT"'")

drop = Path(".secrets-drop")
env = Path(".env")

updates: dict[str, str] = {}
for line in drop.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, value = line.partition("=")
    key, value = key.strip(), value.strip()
    if value:
        updates[key] = value

if not updates:
    raise SystemExit("No key=value pairs found in .secrets-drop")

existing: dict[str, str] = {}
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            existing[k.strip()] = v

existing.update(updates)

lines: list[str] = []
if env.exists():
    seen = set()
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                lines.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        lines.append(line)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
else:
    lines = [f"{k}={v}" for k, v in existing.items()]

env.write_text("\n".join(lines) + "\n")
drop.unlink()
print(f"Imported {len(updates)} secret(s) into .env and deleted .secrets-drop.")
print("Keys imported:", ", ".join(updates.keys()))
PY