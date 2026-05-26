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

# Sentinel default for {{{grok|...}}}: returned by the parameter
# expansion only when grok is COMPLETELY UNSET. If grok is passed as
# `grok=` (empty), the expansion returns "" — NOT the sentinel. That
# lets the outer #ifeq distinguish the three states cleanly:
#   no grok param        → expansion == sentinel → "to be checked"
#   grok= (empty)        → expansion == ""       → inner #if false → "without"
#   grok=<value>         → expansion == value    → inner #if true  → "with"
_GROK_SENTINEL = "__GROK_UNSET__"

GROK_BLOCK = (
    f"<includeonly>{BEGIN_MARKER}\n"
    "{{#ifeq:{{{grok|" + _GROK_SENTINEL + "}}}|" + _GROK_SENTINEL + "|"
    "[[Category:Pages to be checked for Grokipedia]]|"
    "{{#if:{{{grok|}}}|"
    "[[Category:Pages with Grokipedia links]]|"
    "[[Category:Pages without Grokipedia links]]}}}}\n"
    f"{END_MARKER}</includeonly>"
)


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

    if BEGIN_MARKER in current:
        print(f"Marker {BEGIN_MARKER!r} already present — no-op.")
        return 0

    sep = "" if current.endswith("\n") else "\n"
    new_text = f"{current}{sep}{GROK_BLOCK}\n"

    if not new_text or new_text == current:
        print("Would-be edit produced no change; aborting.")
        return 1

    summary = (
        "configure Grokopedia conditional categorisation "
        f"(grok=*|grok=|absent → 3 tracking categories) {args.run_tag}"
    ).strip()

    if not args.apply:
        preview = GROK_BLOCK.replace("\n", "\\n")
        print("DRY RUN: would append the following block at end of template:")
        print(f"  {preview}")
        print(f"  summary: {summary}")
        return 0

    page.save(new_text, summary=summary, minor=False, bot=True)
    print(f"EDIT applied to {TEMPLATE_TITLE}: appended Grokopedia categorisation block.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
