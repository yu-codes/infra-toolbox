#!/usr/bin/env bash
# Hook: format-python
# Trigger: after editing a .py file
# Requires: ruff (pip install ruff)

FILE="$1"

if [[ "$FILE" == *.py ]]; then
  if command -v ruff &>/dev/null; then
    ruff format "$FILE" --quiet
    ruff check "$FILE" --fix --quiet
    echo "[hook] Python formatted: $FILE"
  else
    echo "[hook] ruff not found — skipping format. Install: pip install ruff"
  fi
fi
