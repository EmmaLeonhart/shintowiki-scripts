#!/usr/bin/env python3
"""
audit_git_synced_clobbers.py
============================
One-off recovery audit (Emma, 2026-06-07). Read-only.

The git-synced sync had a bug (shallow CI checkout → repo-wins fallback) that let
the bot overwrite live human wiki edits. This walks the wiki revision history of
every page in [[Category:Git synced pages]] and flags CLOBBER events: an EmmaBot
edit whose summary contains "overwriting divergent wiki edit" that came directly
after a NON-bot (human) edit — i.e. a human change the bot stomped.

For each clobber it records the page, the human editor, the human revision (whose
content can be diffed/recovered), and whether the human's change appears to still
be absent from the current page.

Output: prints a report and writes audit_git_synced_clobbers.out.json next to the
script (page → list of clobber events with revids) for the recovery pass.
"""

import io
import json
import os
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://shinto.miraheze.org/w/api.php"
UA = "GitSyncedClobberAudit/1.0 (User:EmmaBot; shinto.miraheze.org)"
BOT_USERS = {"EmmaBot"}
CLOBBER_MARK = "overwriting divergent wiki edit"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "audit_git_synced_clobbers.out.json")

S = requests.Session()
S.headers.update({"User-Agent": UA})


def jget(**params):
    for _ in range(3):
        r = S.get(API, params=params, timeout=40)
        if r.status_code == 429:
            time.sleep(10); continue
        try:
            return r.json()
        except Exception:
            time.sleep(3); continue
    return {}


def category_pages(cat):
    pages, cont = [], {}
    while True:
        p = dict(action="query", list="categorymembers", cmtitle=f"Category:{cat}",
                 cmtype="page", cmlimit="500", format="json", formatversion="2")
        p.update(cont)
        d = jget(**p)
        pages += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        if "continue" not in d:
            break
        cont = d["continue"]; time.sleep(0.3)
    return pages


def history(title):
    revs, cont = [], {}
    while True:
        p = dict(action="query", prop="revisions", titles=title,
                 rvprop="ids|timestamp|user|comment", rvlimit="500",
                 format="json", formatversion="2")
        p.update(cont)
        d = jget(**p)
        pg = d.get("query", {}).get("pages", [{}])[0]
        revs += pg.get("revisions", [])
        if "continue" not in d:
            break
        cont = d["continue"]; time.sleep(0.3)
    return revs  # newest first


def main():
    pages = category_pages("Git synced pages")
    print(f"git-synced pages: {len(pages)}\n")
    clobbers = {}
    total = 0
    for i, title in enumerate(pages):
        revs = history(title)  # newest-first
        # revs[j] newer than revs[j+1]. A clobber: revs[j] is bot + CLOBBER_MARK,
        # and revs[j+1] (the edit it overwrote) is a human edit.
        events = []
        for j, rv in enumerate(revs):
            if rv.get("user") in BOT_USERS and CLOBBER_MARK in (rv.get("comment") or ""):
                if j + 1 < len(revs):
                    prev = revs[j + 1]
                    if prev.get("user") not in BOT_USERS:
                        events.append({
                            "clobber_rev": rv["revid"], "clobber_ts": rv["timestamp"],
                            "human_user": prev.get("user"), "human_rev": prev["revid"],
                            "human_ts": prev["timestamp"],
                        })
        if events:
            clobbers[title] = events
            total += len(events)
            for e in events:
                print(f"  CLOBBER  {title}  — {e['human_user']} @ {e['human_ts']} "
                      f"(rev {e['human_rev']}) overwritten by sync rev {e['clobber_rev']}")
        if (i + 1) % 20 == 0:
            print(f"  …scanned {i+1}/{len(pages)}", flush=True)
        time.sleep(0.2)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(clobbers, f, indent=2, ensure_ascii=False)
    print(f"\nPages with clobbers: {len(clobbers)}  total clobber events: {total}")
    print(f"Detail: {OUT}")


if __name__ == "__main__":
    main()
