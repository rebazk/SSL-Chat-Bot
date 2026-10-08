#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_QUESTION="What is the Sustainable Solutions Lab, and what does it focus on?"

if ! command -v pwsh >/dev/null 2>&1; then
  echo "PowerShell 7 (pwsh) is required to run this project on macOS."
  exit 1
fi

run_refresh() {
  if command -v python3 >/dev/null 2>&1; then
    python3 "$PROJECT_ROOT/src/refresh_webpages.py"
  else
    pwsh -NoProfile -File "$PROJECT_ROOT/src/Refresh-Webpages.ps1"
  fi
}

usage() {
  cat <<'EOF'
Usage:
  ./run-mac.sh refresh
  ./run-mac.sh build
  ./run-mac.sh ask "What is the Sustainable Solutions Lab, and what does it focus on?"
  ./run-mac.sh demo
  ./run-mac.sh ui
  ./run-mac.sh beacon
  ./run-mac.sh all
EOF
}

command="${1:-all}"

case "$command" in
  refresh)
    run_refresh
    ;;
  build)
    pwsh -NoProfile -File "$PROJECT_ROOT/src/Build-Corpus.ps1"
    ;;
  ask)
    shift || true
    question="${*:-$DEFAULT_QUESTION}"
    pwsh -NoProfile -File "$PROJECT_ROOT/src/Ask-SSL.ps1" -Question "$question"
    ;;
  demo)
    pwsh -NoProfile -File "$PROJECT_ROOT/src/Run-Demo.ps1"
    ;;
  ui)
    if command -v python3 >/dev/null 2>&1; then
      python3 "$PROJECT_ROOT/src/serve_ui.py"
    else
      echo "python3 is required to run the Beacon BOT UI prototype."
      exit 1
    fi
    ;;
  beacon)
    if command -v python3 >/dev/null 2>&1; then
      if command -v open >/dev/null 2>&1; then
        (sleep 2; open "http://127.0.0.1:8765") &
      fi
      python3 "$PROJECT_ROOT/src/serve_ui.py"
    else
      echo "python3 is required to run the Beacon BOT UI prototype."
      exit 1
    fi
    ;;
  all)
    run_refresh
    pwsh -NoProfile -File "$PROJECT_ROOT/src/Build-Corpus.ps1"
    pwsh -NoProfile -File "$PROJECT_ROOT/src/Ask-SSL.ps1" -Question "$DEFAULT_QUESTION"
    pwsh -NoProfile -File "$PROJECT_ROOT/src/Run-Demo.ps1"
    ;;
  *)
    usage
    exit 1
    ;;
esac
