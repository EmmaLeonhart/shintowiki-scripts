#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Running cleanup loop from: $ROOT_DIR"
EDIT_LIMIT="${WIKI_EDIT_LIMIT:-100}"

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

RUN_TAG="[[github:${RUN_PATH}|${CAUSE_TEXT}]]"
echo "Run tag: ${RUN_TAG}"

# Helper: update User:EmmaBot with the current stage name.
# This is a lightweight wiki edit so we can tell from the bot page
# exactly which script is running at any point in time.
declare_stage() {
  python3 shinto_miraheze/update_bot_userpage_status.py --run-tag "${RUN_TAG}" --stage "$1"
}

# ============================================================
# [Bookkeeping: START] — mark workflow ACTIVE
# ============================================================
echo ""
echo "========================================"
echo "[Bookkeeping: START]"
echo "========================================"
python3 shinto_miraheze/update_bot_userpage_status.py --run-tag "${RUN_TAG}" --status active --stage "Bookkeeping: START"

# ============================================================
# [Core Loop] — structural changes that later scripts depend on
# ============================================================
echo ""
echo "========================================"
echo "[Core Loop]"
echo "========================================"

declare_stage "Core Loop: reimport_from_enwiki"
python3 shinto_miraheze/reimport_from_enwiki.py --apply --max-imports 10 --run-tag "${RUN_TAG}"

declare_stage "Core Loop: create_wanted_categories"
python3 shinto_miraheze/create_wanted_categories.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: categorize_uncategorized_categories"
python3 shinto_miraheze/categorize_uncategorized_categories.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: triage_emmabot_categories"
python3 shinto_miraheze/triage_emmabot_categories.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: triage_emmabot_categories_jawiki"
python3 shinto_miraheze/triage_emmabot_categories_jawiki.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: triage_emmabot_categories_secondary"
python3 shinto_miraheze/triage_emmabot_categories_secondary.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: delete_unused_templates"
python3 shinto_miraheze/delete_unused_templates.py --max-deletes "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: fix_double_redirects"
python3 shinto_miraheze/fix_double_redirects.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: generate_p11250_quickstatements"
python3 shinto_miraheze/generate_p11250_quickstatements.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Core Loop: tag_pages_without_wikidata"
python3 shinto_miraheze/tag_pages_without_wikidata.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

# ============================================================
# [Cleanup Loop] — category cleanup + talk pages
# ============================================================
echo ""
echo "========================================"
echo "[Cleanup Loop]"
echo "========================================"

declare_stage "Cleanup Loop: delete_unused_categories"
python3 shinto_miraheze/delete_unused_categories.py --max-deletes "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Cleanup Loop: migrate_talk_pages"
python3 shinto_miraheze/migrate_talk_pages.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Cleanup Loop: delete_orphaned_talk_pages"
python3 shinto_miraheze/delete_orphaned_talk_pages.py --max-deletes "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Cleanup Loop: remove_crud_categories"
python3 shinto_miraheze/remove_crud_categories.py --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

# ============================================================
# [Deprecated] — likely complete, kept as safety net
# These are stateless and run after all stateful work + state commit.
# ============================================================
echo ""
echo "========================================"
echo "[Deprecated]"
echo "========================================"

declare_stage "Deprecated: normalize_category_pages"
python3 shinto_miraheze/normalize_category_pages.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Deprecated: tag_shikinaisha_talk_pages"
python3 shinto_miraheze/tag_shikinaisha_talk_pages.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Deprecated: fix_erroneous_qid_category_links"
python3 shinto_miraheze/fix_erroneous_qid_category_links.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Deprecated: remove_legacy_cat_templates"
python3 shinto_miraheze/remove_legacy_cat_templates.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Deprecated: move_categories"
python3 shinto_miraheze/move_categories.py --apply --max-edits "$EDIT_LIMIT" --run-tag "${RUN_TAG}"

declare_stage "Deprecated: create_japanese_category_qid_redirects"
python3 shinto_miraheze/create_japanese_category_qid_redirects.py

# ============================================================
# [Bookkeeping: END] — mark workflow INACTIVE
# ============================================================
echo ""
echo "========================================"
echo "[Bookkeeping: END]"
echo "========================================"
python3 shinto_miraheze/update_bot_userpage_status.py --run-tag "${RUN_TAG}" --status inactive --stage "Complete"
