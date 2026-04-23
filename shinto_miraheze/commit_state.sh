#!/usr/bin/env bash
# commit_state.sh — Commit and push any changed state/log/error files.
#
# Usage: commit_state.sh <chunk_name>
#
# Retries the push on rejection caused by concurrent pushes. The earlier
# version ran `git pull --rebase ... 2>/dev/null || true` followed by a
# single push, and on rejection just printed a warning. That silently
# dropped every orchestrator state commit except one — category /
# template / misc / duplicate_qids state was created on the runner,
# committed locally, push-rejected, and destroyed when the runner
# tore down.

set -uo pipefail

CHUNK_NAME="${1:-unknown}"
MAX_ATTEMPTS=6

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

for attempt in $(seq 1 ${MAX_ATTEMPTS}); do
  git fetch origin "${GITHUB_REF_NAME}"
  if ! git rebase "origin/${GITHUB_REF_NAME}"; then
    echo "WARN: rebase failed on attempt ${attempt}; aborting. State will retry next run."
    git rebase --abort || true
    exit 0
  fi
  if git push origin "HEAD:${GITHUB_REF_NAME}"; then
    echo "State pushed after ${CHUNK_NAME} (attempt ${attempt})."
    exit 0
  fi
  echo "Push rejected on attempt ${attempt}/${MAX_ATTEMPTS}; refetching and retrying..."
  sleep $((attempt * 2))
done

echo "WARNING: failed to push state after ${CHUNK_NAME} after ${MAX_ATTEMPTS} attempts; state will retry next run."
