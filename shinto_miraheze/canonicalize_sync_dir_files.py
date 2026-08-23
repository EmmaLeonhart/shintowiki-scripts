#!/usr/bin/env python3
"""
canonicalize_sync_dir_files.py
==============================
One-shot local-files canonicalization for the 5 wiki↔repo sync
directories: ``miraheze_unique/``, ``fandom_unique/``, ``git_synced/``,
``need_translation/``, ``duplicated_content/``.

Walks every ``.wiki`` file under each dir, runs the
``canonicalize_template_case`` orchestrator op against the content, and
writes back any changes. Pages whose URL-decoded title starts with
``Template:Infobox `` are skipped to match the op's own guard (these are
the template-definition pages, which legitimately have the lowercase
form pending the case-collision cleanup).

**Why this exists** (2026-05-28 investigation, see DEVLOG): the wiki-side
orchestrator (``canonicalize_template_case``) rewrites lowercase template
references on the wiki. But pages in the 5 sync dirs are driven by their
local ``.wiki`` files — when the orchestrator canonicalizes the wiki
side, the next sync push sees ``repo != wiki``, applies the configured
conflict policy, and (for repo-wins dirs like ``git_synced/``,
``miraheze_unique/``, ``fandom_unique/``) overwrites the wiki back to
the lowercase form. This script fixes the **local files** so the sync
push moves the canonicalization in the right direction.

After this runs and the changes are committed, the next sync cycle will
push the canonical form to the wiki. Single one-shot — no state file
needed; once the files are canonical, the regex is a no-op.

Default mode is dry-run. ``--apply`` writes the files. Standard
``--max-edits`` / ``--run-tag`` flags are accepted for consistency with
the project-wide scaffolding even though no wiki edits happen here
(the tags appear in the commit message that ships these changes).
"""

import argparse
import io
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # Python 3.7+
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.orchestrators.ops.canonicalize_template_case import (  # noqa: E402
    apply as canonicalize_apply,
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SYNC_DIRS = (
    "git_synced",
    "miraheze_unique",
    "fandom_unique",
    "need_translation",
    "duplicated_content",
)


def _title_from_filename(filename: str) -> str:
    """Reverse the sync scripts' filename mapping: a ``.wiki`` filename
    with ``%3A`` etc. URL-encoded special chars back to a page title."""
    name = filename
    if name.endswith(".wiki"):
        name = name[: -len(".wiki")]
    return urllib.parse.unquote(name)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="Write changes (default dry-run).")
    p.add_argument("--max-edits", type=int, default=10000,
                   help="Cap on files edited (default 10000 — effectively all).")
    p.add_argument("--run-tag", required=False, default="",
                   help="Wiki-formatted run tag (accepted for scaffolding consistency; unused here).")
    args = p.parse_args()

    edited = unchanged = skipped = 0
    edits = []  # (relpath, summary) for the edited files

    for sd in SYNC_DIRS:
        dir_path = REPO_ROOT / sd
        if not dir_path.is_dir():
            continue
        for wiki_file in sorted(dir_path.glob("*.wiki")):
            title = _title_from_filename(wiki_file.name)
            # Mirror the op's own guard — don't rewrite the lowercase
            # template-definition pages themselves; those are the pages
            # delete_lowercase_template_collisions.py will eventually
            # delete on the wiki side.
            if title.lower().startswith("template:infobox "):
                skipped += 1
                continue
            try:
                text = wiki_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  ERROR reading {wiki_file}: {e}")
                skipped += 1
                continue
            new_text, summary = canonicalize_apply(title, text)
            if new_text is None or new_text == text:
                unchanged += 1
                continue
            if edited >= args.max_edits:
                print(f"  reached --max-edits ({args.max_edits}); stopping.")
                break
            relpath = wiki_file.relative_to(REPO_ROOT).as_posix()
            edits.append((relpath, summary))
            if args.apply:
                wiki_file.write_text(new_text, encoding="utf-8", newline="\n")
                print(f"  EDITED {relpath}: {summary}")
            else:
                print(f"  [DRY] {relpath}: {summary}")
            edited += 1
        else:
            continue
        break  # broken out by max-edits

    print(f"\n{'=' * 60}")
    print(f"Mode:        {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Edited:      {edited}{'' if args.apply else ' (would-edit count)'}")
    print(f"Unchanged:   {unchanged}")
    print(f"Skipped:     {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
