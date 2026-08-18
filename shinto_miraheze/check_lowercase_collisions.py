"""
check_lowercase_collisions.py
=============================
READ-ONLY local check for Open questions #2: the lowercase
``Template:Infobox <name>`` case-collision twins. For each title in
``LOWERCASE_COLLISION_TITLES`` it reports, on BOTH wikis
(shinto.miraheze.org + shinto.fandom.com), whether the lowercase page still
exists and how many pages transclude it. The deleter
(``delete_lowercase_template_collisions.py``) only removes a twin once its
transclusion count hits zero, so this tells us how close the self-clearing
process is.

Uses a Miraheze-UA-policy-compliant User-Agent (the generic default gets a 403
from the anonymous miraheze API). Read-only: no edits.
"""

import io
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shinto_miraheze.sync_revision_aware import LOWERCASE_COLLISION_TITLES
from shinto_miraheze.ua_contact import contact

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

UA = ("ShintoWikiBot/1.0 (https://github.com/EmmaLeonhart/shintowiki-scripts; "
      f"{contact('wikidata')})")

WIKIS = {
    "miraheze": "https://shinto.miraheze.org/w/api.php",
    "fandom": "https://shinto.fandom.com/api.php",
}


def page_status(session, api, title):
    """Return (exists: bool, transclusion_count: int)."""
    # existence
    r = session.get(api, params={
        "action": "query", "titles": title, "format": "json",
    }, timeout=60)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    exists = not any("missing" in p for p in pages.values())

    # transclusion count (embeddedin), paginate
    count = 0
    cont = {}
    while True:
        params = {
            "action": "query", "list": "embeddedin", "eititle": title,
            "eilimit": "max", "format": "json",
        }
        params.update(cont)
        r = session.get(api, params=params, timeout=60)
        r.raise_for_status()
        d = r.json()
        count += len(d.get("query", {}).get("embeddedin", []))
        if "continue" in d:
            cont = d["continue"]
        else:
            break
    return exists, count


def main():
    session = requests.Session()
    session.headers["User-Agent"] = UA

    print("=== lowercase Template:Infobox collision check (read-only) ===\n")
    titles = sorted(LOWERCASE_COLLISION_TITLES)
    grand_remaining = 0
    for title in titles:
        cells = []
        for label, api in WIKIS.items():
            try:
                exists, count = page_status(session, api, title)
                if exists:
                    grand_remaining += 1
                cells.append(f"{label}: {'EXISTS' if exists else 'gone'} "
                             f"({count} transclusions)")
            except Exception as e:
                cells.append(f"{label}: ERROR {e}")
        print(f"{title}")
        for c in cells:
            print(f"    {c}")
    print()
    print(f"Lowercase twins still existing across both wikis: {grand_remaining} "
          f"(of {len(titles) * 2} possible). When all are gone + 0 transclusions, "
          f"Open questions #2 is resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
