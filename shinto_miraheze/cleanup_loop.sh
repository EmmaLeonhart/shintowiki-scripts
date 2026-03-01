#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Running cleanup loop from: $ROOT_DIR"
EDIT_LIMIT="${WIKI_EDIT_LIMIT:-1000}"

echo "Per-script max edits: $EDIT_LIMIT"

if [ -z "${WIKI_USERNAME:-}" ] || [ -z "${WIKI_PASSWORD:-}" ]; then
  echo "WIKI_USERNAME and WIKI_PASSWORD must be set."
  exit 1
fi

if [[ "${WIKI_USERNAME}" != *"@"* ]]; then
  echo "WIKI_USERNAME must be a bot-password username (example: EmmaBot@EmmaBot)."
  exit 1
fi

RUN_ID="${GITHUB_RUN_ID:-}"
REPO="${GITHUB_REPOSITORY:-Emma-Leonhart/shintowiki-scripts}"
EVENT_NAME="${GITHUB_EVENT_NAME:-local}"

if [ -z "${RUN_ID}" ]; then
  echo "GITHUB_RUN_ID is required to build run-tag; refusing to run."
  exit 1
fi

RUN_PATH="${REPO}/actions/runs/${RUN_ID}"
CAUSE_TEXT="pipeline run"
case "${EVENT_NAME}" in
  push)
    CAUSE_TEXT="commit triggered pipeline"
    ;;
  schedule)
    CAUSE_TEXT="time triggered pipeline"
    ;;
  workflow_dispatch)
    CAUSE_TEXT="manual triggered pipeline"
    ;;
esac

RUN_TAG="[[git:${RUN_PATH}|${CAUSE_TEXT}]]"
echo "Run tag: ${RUN_TAG}"

python3 shinto_miraheze/update_bot_userpage_status.py --run-tag "${RUN_TAG}"
python3 shinto_miraheze/fix_double_redirects.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/move_categories.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/create_japanese_category_qid_redirects.py
python3 shinto_miraheze/delete_unused_categories.py --max-deletes "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/normalize_category_pages.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/migrate_talk_pages.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/tag_shikinaisha_talk_pages.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/remove_crud_categories.py --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/fix_erroneous_qid_category_links.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
python3 shinto_miraheze/remove_legacy_cat_templates.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"
