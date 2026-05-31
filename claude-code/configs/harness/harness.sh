#!/bin/bash
# harness.sh - Universal Claude Code Agent harness script
# Usage: ./harness.sh [repo_path] [task] [model] [max_turns] [budget]

set -euo pipefail

REPO_PATH="${1:-.}"
TASK="${2:-Review the codebase and report issues}"
MODEL="${3:-sonnet}"
MAX_TURNS="${4:-20}"
BUDGET="${5:-2.00}"

cd "$REPO_PATH"

echo "🤖 Running Claude Code Agent..."
echo "   Repo: $(pwd)"
echo "   Task: $TASK"
echo "   Model: $MODEL"
echo "   Max turns: $MAX_TURNS"
echo "   Budget: \$$BUDGET"
echo "---"

result=$(claude --bare -p "$TASK" \
  --dangerously-skip-permissions \
  --model "$MODEL" \
  --max-turns "$MAX_TURNS" \
  --max-budget-usd "$BUDGET" \
  --output-format json 2>/dev/null)

echo "$result" | jq -r '.result'
echo ""
echo "=== Summary ==="
echo "Cost: $(echo "$result" | jq -r '.total_cost_usd // "N/A"') USD"
echo "Session: $(echo "$result" | jq -r '.session_id // "N/A"')"
