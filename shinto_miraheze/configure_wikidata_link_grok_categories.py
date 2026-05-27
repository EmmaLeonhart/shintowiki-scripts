#!/usr/bin/env python3
"""
configure_wikidata_link_grok_categories.py
==========================================
Install / update the conditional Grokopedia categorisation snippet in
``miraheze_unique/Template%3AWikidata link.wiki`` — the repo-side
source-of-truth for ``Template:Wikidata link`` on shinto.miraheze.org.

The wiki page is mirrored bidirectionally with that repo file by
``sync_miraheze_unique_pages.py`` (run from cleanup-loop.yml). The
conflict policy for ``miraheze_unique/`` is REPO-WINS — so the proper
place to edit the template is the repo file. Editing the live wiki
directly creates a window where the repo is behind, and the next sync
clobbers the wiki edit with the stale repo state (we hit that exact
trap on 2026-05-27, fixed in commit bd4b937d).

This script reads the repo file, applies / refreshes the
``<!-- BEGIN_GROK_AUTO_CATEGORIES -->`` block via the
``_replace_or_append`` helper, and writes back. The workflow then
commits + pushes the file change; the next ``sync_miraheze_unique_pages``
run propagates to the wiki.

State table (template snippet behaviour, after the snippet lands):

  * ``grok=<slug>``  (non-empty, not "none") → emit ``[[got:<slug>]]``
                                               interwiki + "Pages with
                                               Grokipedia links" cat
  * ``grok=none``                             → "Pages without Grokipedia
                                                 links"
  * ``grok=`` (empty) OR no ``grok`` param   → "Pages to be checked for
                                                 Grokipedia"

CLI: ``--apply`` (default dry-run), ``--max-edits`` (kept for CI
uniformity — this script touches one file), ``--run-tag``. No wiki
authentication required.
"""

import argparse
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Repo-relative path of the file we edit. miraheze_unique/ is the
# miraheze-side mirror dir; the title is URL-encoded the way
# sync_miraheze_unique_pages.title_to_filename() encodes it (``:``
# becomes ``%3A``, spaces preserved as-is).
TEMPLATE_FILE = "miraheze_unique/Template%3AWikidata link.wiki"

BEGIN_MARKER = "<!-- BEGIN_GROK_AUTO_CATEGORIES -->"
END_MARKER = "<!-- END_GROK_AUTO_CATEGORIES -->"

# Three-state classification + Grokopedia interwiki rendering. See
# module docstring for the full semantics. MediaWiki on miraheze treats
# ``grok=`` (empty) the same as a totally unpassed parameter, so the
# missing case uses the literal sentinel ``none``.
GROK_BLOCK = (
    f"<includeonly>{BEGIN_MARKER}\n"
    "{{#ifeq:{{{grok|}}}|none|"
    "[[Category:Pages without Grokipedia links]]|"
    "{{#if:{{{grok|}}}|"
    "[[got:{{{grok}}}]][[Category:Pages with Grokipedia links]]|"
    "[[Category:Pages to be checked for Grokipedia]]}}}}\n"
    f"{END_MARKER}</includeonly>"
)


_MARKER_BLOCK_RE = re.compile(
    r"<includeonly>\s*" + re.escape(BEGIN_MARKER) + r".*?"
    + re.escape(END_MARKER) + r"\s*</includeonly>",
    re.DOTALL,
)


def _replace_or_append(text: str, block: str) -> str:
    """If the BEGIN/END marker pair is already in ``text``, splice
    ``block`` in place of the existing marker section (including the
    enclosing ``<includeonly>...</includeonly>`` tags). Otherwise append
    ``block`` at the end. Idempotent against re-runs and supports
    updating the snippet's logic without manual template surgery."""
    if _MARKER_BLOCK_RE.search(text):
        # re.sub interprets backslash sequences in the replacement
        # string — escape any backslashes in the block content.
        safe_block = block.replace("\\", r"\\")
        return _MARKER_BLOCK_RE.sub(safe_block, text, count=1)
    sep = "" if text.endswith("\n") else "\n"
    return f"{text}{sep}{block}\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="actually write the file (default: dry-run)")
    ap.add_argument(
        "--max-edits", type=int, default=1,
        help="hard ceiling on writes; this script only ever does 1, "
             "flag kept for CI uniformity",
    )
    ap.add_argument("--run-tag", default="manual run",
                    help="echoed into the workflow's git-commit message")
    args = ap.parse_args()

    if not os.path.exists(TEMPLATE_FILE):
        print(f"FATAL: {TEMPLATE_FILE} does not exist in the repo.",
              file=sys.stderr)
        return 2

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        current = f.read()
    print(f"Read {TEMPLATE_FILE} ({len(current)} chars)")

    new_text = _replace_or_append(current, GROK_BLOCK)

    if new_text == current:
        print("Repo file already carries the current GROK_BLOCK "
              "verbatim — no-op.")
        return 0

    action = "replace existing block" if BEGIN_MARKER in current else "append new block"
    preview = GROK_BLOCK.replace("\n", "\\n")

    if not args.apply:
        print(f"DRY RUN ({action}): block content =")
        print(f"  {preview}")
        print(f"  run-tag: {args.run_tag}")
        return 0

    with open(TEMPLATE_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print(f"EDIT applied to {TEMPLATE_FILE}: {action}.")
    print("  Next sync_miraheze_unique_pages run will push this to "
          "shinto.miraheze.org.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
