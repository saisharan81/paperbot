#!/usr/bin/env bash
# Helper to enter the Poetry virtual environment for local CLI usage.
# Adds the Poetry-managed virtualenv bin directory to PATH and exports PYTHONPATH
# so tools like pytest or ruff can be executed without prefacing commands with
# `poetry run`.
set -euo pipefail
VENV_PATH="$(poetry env info --path 2>/dev/null || true)"
if [[ -z "$VENV_PATH" || ! -d "$VENV_PATH" ]]; then
  echo "Poetry virtualenv not found. Run 'poetry install' first." >&2
  return 1 2>/dev/null || exit 1
fi
BIN_DIR="$VENV_PATH/bin"
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) export PATH="$BIN_DIR:$PATH";;
esac
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
if [[ -n "${BASH_SOURCE:-}" ]]; then
  echo "Environment prepared. pytest, ruff, flake8 now available on PATH." >&2
fi
