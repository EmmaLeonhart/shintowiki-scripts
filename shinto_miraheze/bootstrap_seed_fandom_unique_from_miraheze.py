#!/usr/bin/env python3
"""
bootstrap_seed_fandom_unique_from_miraheze.py
==============================================
Idempotent bootstrap: for every ``miraheze_unique/<title>.wiki`` whose
counterpart ``fandom_unique/<title>.wiki`` does NOT exist, copy the
miraheze file to fandom_unique/. This seeds new entries with the
miraheze content as a starting point, which the next
``sync_fandom_unique_pages.py`` run will push to fandom.

Pre-existing files in ``fandom_unique/`` are NEVER overwritten — those
are intentional fandom-side overrides (Portable Infoboxes, the
Wikidata link HTTPS shim, etc.) and must be preserved.

Performs no wiki edits. Pure local file copy.
"""

import io
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
MIRAHEZE_DIR = REPO_ROOT / "miraheze_unique"
FANDOM_DIR = REPO_ROOT / "fandom_unique"


def main():
    # FANDOM_SUNSET_DATE mirrors the canonical constant in
    # shinto_miraheze/orchestrators/ops/fandom_mirror.py. Inlined here
    # because this script runs as `python3 shinto_miraheze/X.py` (the
    # script dir is on sys.path, not the repo root, and there's no
    # shinto_miraheze/__init__.py), so the package import raised
    # ModuleNotFoundError and crashed every run. Keep the two in sync.
    import datetime as _dt
    FANDOM_SUNSET_DATE = _dt.date(2027, 1, 1)
    if _dt.datetime.utcnow().date() >= FANDOM_SUNSET_DATE:
        print(
            f"bootstrap_seed disabled: past FANDOM_SUNSET_DATE "
            f"({FANDOM_SUNSET_DATE.isoformat()}). No new fandom_unique/ "
            f"files will be seeded."
        )
        return 0

    if not MIRAHEZE_DIR.exists():
        print(f"miraheze_unique/ does not exist; nothing to seed.")
        return 0
    FANDOM_DIR.mkdir(parents=True, exist_ok=True)

    miraheze_files = [p for p in MIRAHEZE_DIR.iterdir()
                      if p.is_file() and p.suffix == ".wiki"]
    print(f"miraheze_unique/: {len(miraheze_files)} files")

    seeded = preserved = 0
    for src in miraheze_files:
        dst = FANDOM_DIR / src.name
        if dst.exists():
            preserved += 1
            continue
        shutil.copy2(src, dst)
        seeded += 1
        print(f"SEED  {src.name}")

    print(f"\n{'=' * 60}")
    print(f"Seeded into fandom_unique/:  {seeded}")
    print(f"Preserved (override exists): {preserved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
