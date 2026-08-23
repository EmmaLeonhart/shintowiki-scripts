#!/usr/bin/env python3
"""
resolve_deleted_qid_ills_202607.py
==================================
One-off, date-gated resolution of the 3 current deleted-QID ills (queue #6,
2026-07-07). Policy: a deleted-QID ill gets its `qid=` set to the BEST EXISTING
Wikidata item (researched by hand, NOT recreated). The 3 cases + their resolved
targets:

  Ogawa Shrine, Nawino Shrine : Q702140 (Ōnamuchi-no-Mikoto, deleted) -> Q276944 (Ōkuninushi)
  Takeo Shimokorihiko Shrine  : Q568647 (Taira clan, deleted)         -> Q1079102 (Taira clan)

For each target ill (identified by the deleted QID appearing as a positional or
`qid=`), both the positional and the `qid=` (whether the raw deleted QID or the
`DELETED_QID` placeholder) are rewritten to the resolved QID. The `deleted_qids_in_ill`
op's self-heal then drops the now-stale tracking category on its next sweep.

Date-gated: no-op before RESOLVE_DATE, so it can sit in the daily cleanup loop and
start acting on that date. Idempotent — skips a page once its deleted QID is gone.
Standard flags: --apply / --max-edits / --run-tag.
"""

import argparse
import datetime
import io
import os
import re
import sys
import time

import mwclient
from wiki_login import login_with_retry
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.user_agent import USER_AGENT

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5
# hand-built agent, not the canonical one -- so it never matched the allowlisted string.
# was: UA = ("ShintoWikiBot/1.0 (https://github.com/EmmaLeonhart/shintowiki-scripts; " f"{contact('wikidata')})")
UA = USER_AGENT

RESOLVE_DATE = datetime.date(2026, 7, 7)

# page -> list of (deleted_qid, resolved_qid)
RESOLUTIONS = {
    "Ogawa Shrine": [("Q702140", "Q276944")],
    "Nawino Shrine": [("Q702140", "Q276944")],
    "Takeo Shimokorihiko Shrine": [("Q568647", "Q1079102")],
}

ILL_RE = re.compile(r"\{\{ill\|([^{}]*)\}\}", re.IGNORECASE)


def rewrite_text(text: str, mappings) -> str:
    """Rewrite every ill that references a deleted QID (positional or qid=) to its
    resolved QID. Untouched ills are returned verbatim."""
    def repl(match):
        parts = match.group(1).split("|")
        stripped = [p.strip() for p in parts]
        for deleted, resolved in mappings:
            refs = deleted in stripped or f"qid={deleted}" in [s.lower() for s in stripped] \
                or any(s.lower() == f"qid={deleted}".lower() for s in stripped)
            if not refs:
                continue
            new = []
            for p in parts:
                ps = p.strip()
                if ps == deleted:
                    new.append(resolved)
                elif ps.lower() == f"qid={deleted}".lower():
                    new.append(f"qid={resolved}")
                elif ps.lower() == "qid=deleted_qid":
                    new.append(f"qid={resolved}")
                else:
                    new.append(p)
            return "{{ill|" + "|".join(new) + "}}"
        return match.group(0)
    return ILL_RE.sub(repl, text)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Actually save (default dry-run).")
    ap.add_argument("--max-edits", type=int, default=10)
    ap.add_argument("--run-tag", required=True)
    args = ap.parse_args()

    today = datetime.datetime.now(datetime.timezone.utc).date()
    if today < RESOLVE_DATE:
        print(f"Before RESOLVE_DATE ({RESOLVE_DATE.isoformat()}); no-op (today {today.isoformat()}).")
        return 0

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=UA)
    if not PASSWORD:
        print("No WIKI_PASSWORD — read-only (dry-run only).")
    else:
        login_with_retry(site, USERNAME, PASSWORD)
        print(f"Logged in as {USERNAME}")

    edits = 0
    for title, mappings in RESOLUTIONS.items():
        if edits >= args.max_edits:
            break
        page = site.pages[title]
        if not page.exists:
            print(f"SKIP {title} (missing)")
            continue
        text = page.text()
        new_text = rewrite_text(text, mappings)
        if new_text == text:
            print(f"SKIP {title} (deleted QID already resolved)")
            continue
        targets = ", ".join(f"{d}->{r}" for d, r in mappings)
        if not args.apply:
            print(f"[DRY] {title}: resolve {targets}")
            edits += 1
            continue
        page.save(new_text, summary=f"Bot: resolve deleted-QID ill to best existing "
                                    f"item ({targets}) {args.run_tag}")
        edits += 1
        print(f"EDIT {title}: {targets}")
        time.sleep(THROTTLE)

    print(f"\nDone. Edits: {edits}")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())
