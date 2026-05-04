#!/usr/bin/env bash
# Hook: warn-console-log
# Trigger: after editing a .vue, .ts, or .js file
# Warns if console.log is detected — does NOT auto-remove

FILE="$1"

if [[ "$FILE" == *.vue || "$FILE" == *.ts || "$FILE" == *.js ]]; then
  COUNT=$(grep -c "console\.log" "$FILE" 2>/dev/null || echo 0)
  if [[ "$COUNT" -gt 0 ]]; then
    echo "[warn] $FILE contains $COUNT console.log statement(s). Remove before committing."
  fi
fi
