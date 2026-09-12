#!/usr/bin/env python3
"""
apply_blank_wikidata_links.py
=============================
Writes the QIDs that ``resolve_blank_wikidata_links.py`` proposed into the blank
``{{wikidata link}}`` templates they belong to.

The pair is deliberately two scripts. The resolver reads two wikis and decides;
this one only writes what the resolver already decided, from
``blank_wikidata_link_proposals.state``. Resolving and writing in one pass is how
you end up unable to answer "what would this have done?" without letting it do
it.

What it will and will not touch
-------------------------------
* Only a page named in the state file with a non-null ``qid``.
* Only a ``{{wikidata link}}`` that is **still blank** when re-read at write
  time. The proposal is evidence, not a licence: if the template has acquired a
  QID since — from ``wikidata_lookup``, from a human, from anything — the page is
  skipped and said so. It never overwrites a QID, including a different one.
* Exactly one template per page. Two blank templates on one page is the
  ``multiple_wikidata_links`` op's territory, and picking one of them here would
  be a guess.
* Redirects are skipped; they never carry the template directly.

⛔ It does NOT drop ``[[Category:Git synced pages]]`` or any other trailing
category, because it does not rewrite the page — it replaces the template call
in place and leaves every other byte alone.

Gates
-----
Calls ``wiki_edit_allowed.py`` first, like every other writer here, so a local or
manual run is covered and not just the CI step. A locked run prints ``SKIPPED:``
and exits 0 — nothing was attempted, so nothing broke. (shinto.miraheze has been
locked since 2026-09-06 on a failed weekly edit-test; it re-tests itself and
opens on its own.)

This touches shinto.miraheze only. It makes no Wikidata edit and is not gated by
the Wikidata lockout.

Standard flags: ``--apply`` (default dry-run), ``--max-edits``, ``--run-tag``.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time

import mwclient

from shinto_miraheze.ua_for import ua_for

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

STATE = os.path.join(_uar, "shinto_miraheze", "blank_wikidata_link_proposals.state")

REDIRECT_RE = re.compile(r"^\s*#redirect\b", re.IGNORECASE | re.MULTILINE)

# A BLANK call only: "{{wikidata link}}" with nothing but whitespace inside.
# `{{wikidata link|}}` counts as blank too — an empty first parameter is the same
# absent QID — but `{{wikidata link|Q1}}` and `{{wikidata link|ja|X}}` do not.
BLANK_CALL_RE = re.compile(r"\{\{\s*wikidata\s+link\s*\|?\s*\}\}", re.IGNORECASE)
ANY_CALL_RE = re.compile(r"\{\{\s*wikidata\s+link\s*[|}]", re.IGNORECASE)
QID_RE = re.compile(r"^Q\d+$")


def lockout_blocks_us() -> bool:
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_edit_allowed.py")
    if not os.path.isfile(checker):
        return False
    return subprocess.call([sys.executable, checker]) != 0


def load_proposals(path=STATE):
    """{title: qid} for the entries the resolver actually resolved."""
    if not os.path.isfile(path):
        raise SystemExit(f"{path} not found — run resolve_blank_wikidata_links.py first")
    with io.open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out = {}
    for title, row in data.items():
        qid = (row or {}).get("qid")
        if qid and QID_RE.match(qid):
            out[title] = qid
    return out


def fill(text, qid):
    """(new_text, reason). Replace the one blank call with a filled one.

    Returns (None, why) rather than a changed page whenever the situation is not
    exactly the one the proposal was made about.
    """
    if not ANY_CALL_RE.search(text):
        return None, "page no longer carries {{wikidata link}}"
    blanks = BLANK_CALL_RE.findall(text)
    if not blanks:
        return None, "template already has a QID — not overwriting"
    if len(blanks) > 1:
        return None, f"{len(blanks)} blank templates on the page — ambiguous, left alone"
    return BLANK_CALL_RE.sub("{{wikidata link|" + qid + "}}", text, count=1), "filled"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="Write changes (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Maximum page saves this run (default 50).")
    parser.add_argument("--run-tag", default="",
                        help="Run tag appended to the edit summary for auditing.")
    args = parser.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    if lockout_blocks_us():
        print("SKIPPED: miraheze editing is locked. Nothing attempted.")
        return

    # Imported here, not at module level: `wiki_login` resolves off this
    # directory being sys.path[0], which is true for `python <file>` and not for
    # importing the module. `carry_missing_sections.py` does the same.
    from wiki_login import login_with_retry

    proposals = load_proposals()
    print(f"{len(proposals)} resolved proposal(s) in {os.path.basename(STATE)}")

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=ua_for(WIKI_URL))
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    edits = 0
    skipped = 0
    for title, qid in sorted(proposals.items()):
        if edits >= args.max_edits:
            print("MAX EDITS reached, stopping.")
            break
        try:
            page = site.pages[title]
            text = page.text()
        except Exception as e:
            print(f"  read error {title}: {e}")
            continue
        if not text or REDIRECT_RE.search(text):
            print(f"  skip [[{title}]]: missing or redirect")
            skipped += 1
            continue
        new_text, reason = fill(text, qid)
        if new_text is None:
            print(f"  skip [[{title}]]: {reason}")
            skipped += 1
            continue
        if not args.apply:
            print(f"  [DRY] would set [[{title}]] -> {qid}")
            edits += 1
            continue
        summary = f"Bot: fill {{{{wikidata link}}}} with {qid} {args.run_tag}".strip()
        try:
            page.save(new_text, summary=summary)
            print(f"  SET [[{title}]] -> {qid}")
            edits += 1
        except Exception as e:
            print(f"  ERROR saving {title}: {e}")
        time.sleep(THROTTLE)

    print(f"\nDone. {'would edit' if not args.apply else 'edited'}: {edits} | skipped: {skipped}")


if __name__ == "__main__":
    main()
