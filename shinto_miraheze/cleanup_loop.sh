#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Running cleanup loop from: $ROOT_DIR"

python3 shinto_miraheze/normalize_category_pages.py --apply
python3 shinto_miraheze/migrate_talk_pages.py --apply
python3 shinto_miraheze/tag_shikinaisha_talk_pages.py --apply
python3 shinto_miraheze/remove_crud_categories.py
python3 shinto_miraheze/fix_erroneous_qid_category_links.py --apply
