#!/usr/bin/env bash
# Hook: suggest-tmux
# Trigger: before running long-running commands (dev servers, watchers, etc.)
# Suggests tmux if not already inside a tmux session

COMMAND="$*"

LONG_RUNNING_PATTERNS=("uvicorn" "fastapi dev" "npm run dev" "vite" "vitest --watch" "celery" "watchfiles")

for pattern in "${LONG_RUNNING_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -q "$pattern"; then
    if [[ -z "$TMUX" ]]; then
      echo "[hint] '$pattern' is a long-running command."
      echo "       Consider running inside tmux to keep it persistent:"
      echo "       tmux new-session -s dev"
    fi
    break
  fi
done
