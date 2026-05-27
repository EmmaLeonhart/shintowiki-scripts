#!/usr/bin/env python3
"""
configure_wikidata_link_grok_categories.py
==========================================
One-shot: install the conditional Grokopedia-categorisation snippet onto
``Template:Wikidata link`` so that pages transcluding the template are
auto-categorised by the state of the template's ``grok`` parameter:

  * ``grok=<slug>``  (set, non-empty) → [[Category:Pages with Grokipedia links]]
  * ``grok=``        (set, empty)     → [[Category:Pages without Grokipedia links]]
  * no ``grok`` param at all          → [[Category:Pages to be checked for Grokipedia]]

The ``grokipedia_link`` orchestrator op writes ``grok=<slug>`` or
``grok=`` onto each mainspace page's wikidata-link template after
probing grokipedia.com; this script wires the template side, so the
categorisation comes for free from MediaWiki's parser-functions.

Idempotent. Looks for the marker comment
``<!-- BEGIN_GROK_AUTO_CATEGORIES -->``; if present, no-ops. If absent,
appends a self-contained ``<includeonly>`` block at the bottom of the
template so the categorisation only fires on transcluding pages (the
template page itself is unaffected).

Standard CLI flags: ``--apply`` (default dry-run), ``--run-tag``. Wiki
auth via ``WIKI_USERNAME`` + ``WIKI_PASSWORD`` env vars.
"""

import argparse
import io
import os
import re
import sys

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USER_AGENT = (
    "ConfigureWikidataLinkGrokCategories/1.0 "
    "(User:EmmaBot; shinto.miraheze.org)"
)
TEMPLATE_TITLE = "Template:Wikidata link"

BEGIN_MARKER = "<!-- BEGIN_GROK_AUTO_CATEGORIES -->"
END_MARKER = "<!-- END_GROK_AUTO_CATEGORIES -->"

# Three-state classification driven by the `grok` parameter. MediaWiki on
# miraheze treats `grok=` (empty) the same as a totally unpassed
# parameter — both make `{{{grok|}}}` resolve to "" — so an empty slot
# CANNOT distinguish "checked, no article" from "not yet checked". The
# orchestrator op therefore writes the literal sentinel ``none`` for the
# missing case. The template logic:
#
#   grok=<slug>   (non-empty, not "none") → "Pages with Grokipedia links"
#   grok=none                              → "Pages without Grokipedia links"
#   grok= (empty) OR no grok param at all  → "Pages to be checked for Grokipedia"
#
# The legacy `grok=` (empty) state is folded into "to be checked"
# alongside fully-absent; the orchestrator op rewrites those to
# `grok=none` on the next visit so they migrate to the correct bucket.
GROK_BLOCK = (
    f"<includeonly>{BEGIN_MARKER}\n"
    "{{#ifeq:{{{grok|}}}|none|"
    "[[Category:Pages without Grokipedia links]]|"
    "{{#if:{{{grok|}}}|"
    "[[Category:Pages with Grokipedia links]]|"
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
    ap.add_argument("--apply", action="store_true", help="actually save the edit")
    ap.add_argument(
        "--max-edits", type=int, default=1,
        help="hard ceiling on saves; this script only ever does 1, flag kept for CI uniformity",
    )
    ap.add_argument("--run-tag", default="manual run")
    args = ap.parse_args()

    username = os.getenv("WIKI_USERNAME", "EmmaBot")
    password = os.getenv("WIKI_PASSWORD", "")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.login(username, password)
    print(f"Logged in as {username}")

    page = site.pages[TEMPLATE_TITLE]
    if not page.exists:
        print(f"FATAL: {TEMPLATE_TITLE} does not exist on the wiki.", file=sys.stderr)
        return 2

    current = page.text()
    print(f"Fetched {TEMPLATE_TITLE} ({len(current)} chars)")

    new_text = _replace_or_append(current, GROK_BLOCK)

    if new_text == current:
        print("Template already carries the current GROK_BLOCK verbatim — no-op.")
        return 0

    action = "replace existing block" if BEGIN_MARKER in current else "append new block"
    summary = (
        f"configure Grokopedia conditional categorisation ({action}; "
        f"grok=<slug>|grok=none|empty-or-absent → 3 tracking categories) "
        f"{args.run_tag}"
    ).strip()

    if not args.apply:
        preview = GROK_BLOCK.replace("\n", "\\n")
        print(f"DRY RUN ({action}): block content =")
        print(f"  {preview}")
        print(f"  summary: {summary}")
        return 0

    page.save(new_text, summary=summary, minor=False, bot=True)
    print(f"EDIT applied to {TEMPLATE_TITLE}: {action}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
