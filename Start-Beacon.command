#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to run Beacon BOT on macOS."
  exit 1
fi

echo "Starting Beacon BOT from:"
echo "$PROJECT_ROOT"
echo
echo "Beacon BOT will open at http://127.0.0.1:8765"
echo "Keep this window open while Beacon BOT is running."
echo

if command -v open >/dev/null 2>&1; then
  (sleep 2; open "http://127.0.0.1:8765") &
fi

python3 "$PROJECT_ROOT/src/serve_ui.py"
