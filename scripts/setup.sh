#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v uv >/dev/null 2>&1; then
  uv venv .venv --allow-existing
  # shellcheck disable=SC1091
  source .venv/bin/activate
  uv pip install -e ".[dev]"
elif command -v python3 >/dev/null 2>&1; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -e ".[dev]"
else
  echo "error: need uv or python3 on PATH" >&2
  exit 1
fi

episodic init

echo ""
echo "Setup complete. Save a subgraph with:"
echo "  episodic save --id myrepo --source /path/to/corpus"
