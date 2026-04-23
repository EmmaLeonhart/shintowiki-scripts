#!/usr/bin/env bash
# commit_state.sh — Commit and push any changed state/log/error files.
#
# Usage: commit_state.sh <chunk_name>

set -uo pipefail

CHUNK_NAME="${1:-unknown}"

echo ""
echo "--- Committing state after: ${CHUNK_NAME} ---"

STATE_FILES="$(find . -name '*.state' -o -name '*.log' -o -name '*.errors' | sort)"
if [ -z "$STATE_FILES" ]; then
  echo "No state files found, skipping commit."
  exit 0
fi

echo "$STATE_FILES" | xargs git add -f
if git diff --cached --quiet; then
  echo "No state changes to commit after ${CHUNK_NAME}."
  exit 0
fi

git commit -m "chore(state): update state after ${CHUNK_NAME} [skip ci]"
echo "State committed after ${CHUNK_NAME}."

# Push immediately so state survives even if a later step fails
git pull --rebase origin "${GITHUB_REF_NAME}" 2>/dev/null || true
git push origin "HEAD:${GITHUB_REF_NAME}" && echo "State pushed after ${CHUNK_NAME}." || echo "WARNING: failed to push state after ${CHUNK_NAME}."
