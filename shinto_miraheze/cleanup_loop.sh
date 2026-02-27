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

python3 shinto_miraheze/update_bot_userpage_status.py
python3 shinto_miraheze/normalize_category_pages.py --apply --max-edits "$EDIT_LIMIT"
python3 shinto_miraheze/migrate_talk_pages.py --apply --max-edits "$EDIT_LIMIT"
python3 shinto_miraheze/tag_shikinaisha_talk_pages.py --apply --max-edits "$EDIT_LIMIT"
python3 shinto_miraheze/remove_crud_categories.py --max-edits "$EDIT_LIMIT"
python3 shinto_miraheze/fix_erroneous_qid_category_links.py --apply --max-edits "$EDIT_LIMIT"
