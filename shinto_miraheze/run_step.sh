#!/usr/bin/env bash
# run_step.sh — Generic wrapper for cleanup loop steps.
#
# Usage: run_step.sh <stage_name> <command...>
#
# 1. Updates User:EmmaBot to show the current stage
# 2. Runs the command
# 3. Updates User:EmmaBot to show the stage is done
#
# Environment variables (set by the workflow):
#   RUN_TAG       — wiki-formatted run tag link
#   STEP_FAILED   — set to "true" on failure (for the calling workflow)

set -uo pipefail

STAGE="$1"
shift

echo ""
echo "========================================"
echo "[${STAGE}]"
echo "========================================"

if [ -z "${RUN_TAG:-}" ]; then
  echo "ERROR: RUN_TAG is not set."
  exit 1
fi

# Mark stage as active on User:EmmaBot
python3 shinto_miraheze/update_bot_userpage_status.py \
  --run-tag "${RUN_TAG}" --stage "${STAGE}"

# Run the actual command
if "$@"; then
  echo ""
  echo "[${STAGE}] ✓ completed"
else
  EXIT_CODE=$?
  echo ""
  echo "[${STAGE}] ✗ failed (exit code ${EXIT_CODE})"
  exit $EXIT_CODE
fi
