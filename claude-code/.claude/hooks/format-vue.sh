#!/usr/bin/env bash
# Hook: format-vue
# Trigger: after editing a .vue or .ts or .js file
# Requires: prettier (npm install -g prettier)

FILE="$1"

if [[ "$FILE" == *.vue || "$FILE" == *.ts || "$FILE" == *.js ]]; then
  if command -v prettier &>/dev/null; then
    prettier --write "$FILE" --log-level silent
    echo "[hook] Vue/TS formatted: $FILE"
  else
    echo "[hook] prettier not found — skipping format. Install: npm install -g prettier"
  fi
fi
