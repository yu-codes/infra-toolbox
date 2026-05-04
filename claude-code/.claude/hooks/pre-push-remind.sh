#!/usr/bin/env bash
# Hook: pre-push-remind
# Trigger: before git push
# Reminds developer to run tests and review changes

echo ""
echo "========================================="
echo "  Pre-push checklist:"
echo "  [ ] Tests passing? (pytest / vitest)"
echo "  [ ] No console.log left in JS/Vue files?"
echo "  [ ] No debug prints in Python files?"
echo "  [ ] Branch is up to date with main?"
echo "========================================="
echo ""
echo "Push proceeding — this is a reminder only."
echo ""
