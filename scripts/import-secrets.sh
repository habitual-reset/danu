#!/usr/bin/env bash
# Merge secrets from a drop file into .env, then delete the drop file.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "PASTE_KEYS_HERE.txt" ]]; then
  DROP="PASTE_KEYS_HERE.txt"
elif [[ -f ".secrets-drop" ]]; then
  DROP=".secrets-drop"
else
  echo "No secrets file found."
  echo ""
  echo "Easiest: open this file in TextEdit, paste your key, save:"
  echo "  $ROOT/PASTE_KEYS_HERE.txt"
  echo ""
  echo "Then say in chat: import my secrets file"
  echo "Or run this script again."
  exit 1
fi

touch .env
chmod 600 .env 2>/dev/null || true

python3 <<PY
from pathlib import Path

drop = Path("$DROP")
env = Path(".env")

updates: dict[str, str] = {}
for line in drop.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, value = line.partition("=")
    key, value = key.strip(), value.strip()
    if not value or "PASTE_YOUR" in value:
        continue
    updates[key] = value
elif line.startswith("sk-"):
    updates["OPENAI_API_KEY"] = line

if not updates:
    raise SystemExit("No real keys found. Replace PASTE_YOUR_KEY_BELOW with your OpenAI key.")

lines: list[str] = []
seen: set[str] = set()
if env.exists():
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

env.write_text("\n".join(lines) + "\n")
drop.unlink()
print(f"Imported {len(updates)} secret(s) into .env")
print("Imported keys:", ", ".join(updates.keys()))
print("Deleted", "$DROP")
PY