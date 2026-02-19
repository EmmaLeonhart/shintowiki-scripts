#!/usr/bin/env python3
"""Shintowiki Translated‑Page Maintenance Bot (Miraheze) – v0.3

Fix: use the **page‑level** `embeddedin` generator instead of the missing
`Site.embeddedin`.

Run:
    python translated_page.py
"""

from __future__ import annotations

import sys
from typing import Optional

try:
    import mwclient  # type: ignore
    import mwparserfromhell as mwph  # type: ignore
except ModuleNotFoundError:
    sys.exit("[FATAL] Missing deps →  pip install mwclient mwparserfromhell")

# hard‑coded creds
USER, PASS = "Immanuelle", "[REDACTED_SECRET_1]"

###############################################################################
# util helpers
###############################################################################

def ja_redirect(title: str) -> bool:
    ja = mwclient.Site("ja.wikipedia.org", scheme="https", path="/w/")
    pg = ja.pages[title]
    try:
        txt = pg.text()
    except mwclient.errors.HTTPStatusError:
        return True
    return pg.redirect or txt.lstrip().lower().startswith("#redirect")


def ensure_cat(txt: str, cat: str) -> str:
    return txt if cat.lower() in txt.lower() else txt.rstrip("\n") + "\n" + cat + "\n"


def prepend_iw(txt: str, iw: str) -> str:
    return txt if iw in txt else f"{iw}\n{txt}"

###############################################################################
# main
###############################################################################

def main() -> None:
    site = mwclient.Site("shinto.miraheze.org", scheme="https", path="/w/")
    site.login(USER, PASS)

    tpl_name = "Template:Translated page"
    removed_cat = "[[Category:Removed translated page templates]]"

    tpl_page = site.pages[tpl_name]

    for page in tpl_page.embeddedin(namespace=0):  # main‑namespace only
        print(f"[•] {page.name}")
        orig = page.text()
        code = mwph.parse(orig)

        # first template
        tp: Optional[mwph.nodes.Template] = None
        for t in code.filter_templates(recursive=False):
            if t.name.strip().lower() == "translated page":
                tp = t
                break
        if not tp:
            print("    – template missing; skip")
            continue

        try:
            lang = tp.get(1).value.strip()
            target = tp.get(2).value.strip()
        except (IndexError, ValueError):
            print("    – bad params; skip")
            continue
        if lang.lower() != "ja" or not target:
            print("    – not ja / blank; skip")
            continue

        if ja_redirect(target):
            print("    – redirect ⇒ drop")
            code.remove(tp)
            new = ensure_cat(str(code), removed_cat)
            summary = "Remove {{translated page}} (ja redirect) + cat"
        else:
            iw = f"[[ja:{target}]]"
            new = prepend_iw(str(code), iw)
            if new == orig:
                print("    – already clean; skip save")
                continue
            summary = "Add interwiki link to ja‑wiki"

        try:
            page.save(new, summary=summary, minor=False)
            print("    ✓ saved")
        except mwclient.errors.EditError as e:
            print(f"    ✗ save failed: {e}")


if __name__ == "__main__":
    main()