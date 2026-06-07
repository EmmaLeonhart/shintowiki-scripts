#!/usr/bin/env python3
"""
build_wikidata_resolution_csv.py
================================
Part 3a of the "resolve interlanguage links via local agentic RAG" operation
(Emma, 2026-06-07). Read-only against the wiki/Wikidata; writes one CSV.

For every git_synced page in the cohort (carries
[[Category:Pages git synced to resolve interlanguage and interwiki links]]),
it:
  1. Parses the {{wikidata link}} template: current QID slot + (lang, target)
     interlanguage pairs.
  2. Searches Wikidata for the best candidate item — first by each interlanguage
     target IN ITS OWN LANGUAGE (the method that worked best: e.g. search
     "茨城国造" in ja, not the romanised page title), then by the page title in
     English as a fallback. Records match strength (exact-label vs search-hit).
  3. OVERLAP CHECK: for the best candidate QID, fetches its P11250 (Miraheze
     article ID) claim. If P11250 already points at a DIFFERENT shinto page,
     that's a duplicate/merge situation (both pages claim the same item) and the
     row is flagged — those get merged (prefer the "Jingū" title over "...Shrine")
     rather than blindly written.

Output: ``build_wikidata_resolution_csv.out.csv`` next to this script, with
columns: title, current_qid, pairs, best_qid, match_type, wd_label,
wd_description, overlap_p11250, note.

Pacing: ~1.7s between Wikidata calls, 30s backoff + one retry on HTTP 429, then
the row is marked THROTTLED so a re-run can fill it. Never bails the whole run
on a single 429 (this is analysis, not a pipeline edit).
"""

import csv
import io
import os
import re
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WD_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "ShintoWDResolver/1.0 (User:EmmaBot; shinto.miraheze.org)"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
GIT_SYNCED_DIR = os.path.join(REPO_ROOT, "git_synced")
OUT_CSV = os.path.join(SCRIPT_DIR, "build_wikidata_resolution_csv.out.csv")

COHORT_CAT = "Pages git synced to resolve interlanguage and interwiki links"
WD_LINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*((?:\|[^{}]*)*)\}\}", re.IGNORECASE)
THROTTLE = 1.7

S = requests.Session()
S.headers.update({"User-Agent": USER_AGENT})


def filename_to_title(fn):
    import urllib.parse
    return urllib.parse.unquote(fn[:-5] if fn.endswith(".wiki") else fn)


def parse_wd_link(text):
    m = WD_LINK_RE.search(text)
    if not m:
        return None, []
    parts = [p.strip() for p in m.group(1).split("|")[1:]]
    positional = [p for p in parts if "=" not in p]
    qid = positional[0] if positional else ""
    rest = positional[1:]
    pairs = [(rest[i], rest[i + 1]) for i in range(0, len(rest) - 1, 2)]
    return qid, pairs


def _get(params):
    for attempt in range(2):
        time.sleep(THROTTLE)
        r = S.get(WD_API, params=params, timeout=25)
        if r.status_code == 429:
            time.sleep(30)
            continue
        r.raise_for_status()
        return r.json()
    return None  # throttled out


def wd_search(term, lang):
    j = _get({"action": "wbsearchentities", "search": term, "language": lang,
              "uselang": lang, "limit": 5, "format": "json"})
    if j is None:
        return None
    return j.get("search", [])


def wd_p11250(qid):
    """Return the P11250 (Miraheze article ID) string value of a QID, or ''."""
    j = _get({"action": "wbgetentities", "ids": qid, "props": "claims",
              "format": "json"})
    if j is None:
        return None
    try:
        claims = j["entities"][qid]["claims"].get("P11250", [])
        if claims:
            return claims[0]["mainsnak"]["datavalue"]["value"]
    except (KeyError, IndexError, TypeError):
        pass
    return ""


def best_candidate(title, pairs):
    """Search WD, JP/native targets first then English title. Returns
    (qid, match_type, label, desc) or (None, 'throttled', '', '') on 429."""
    terms = [(t, l) for (l, t) in pairs] + [(title, "en")]
    for term, lang in terms:
        slang = lang if 1 <= len(lang) <= 8 else "en"
        hits = wd_search(term, slang)
        if hits is None:
            return None, "throttled", "", ""
        if not hits:
            continue
        top = hits[0]
        label = top.get("label", "")
        exact = label.strip().lower() == term.strip().lower()
        return top["id"], ("exact-label" if exact else "search-hit"), label, top.get("description", "")
    return "", "no-hit", "", ""


def main():
    files = [f for f in sorted(os.listdir(GIT_SYNCED_DIR)) if f.endswith(".wiki")]
    rows = []
    for fn in files:
        path = os.path.join(GIT_SYNCED_DIR, fn)
        text = open(path, encoding="utf-8").read()
        if COHORT_CAT not in text:
            continue
        title = filename_to_title(fn)
        cur_qid, pairs = parse_wd_link(text)
        qid, mtype, label, desc = best_candidate(title, pairs)
        overlap = ""
        if qid and mtype != "throttled":
            p11250 = wd_p11250(qid)
            if p11250 is None:
                mtype = "throttled"
            elif p11250 and p11250 not in (f"shinto:{title}", title):
                overlap = p11250
        rows.append({
            "title": title, "current_qid": cur_qid,
            "pairs": ";".join(f"{l}:{t}" for l, t in pairs),
            "best_qid": qid or "", "match_type": mtype,
            "wd_label": label, "wd_description": desc,
            "overlap_p11250": overlap,
            "note": "MERGE: QID already used by another page" if overlap else "",
        })
        print(f"[{mtype:11}] {title[:36]:36} -> {qid or '-':12} {('OVERLAP '+overlap) if overlap else label[:30]}")

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["title", "current_qid", "pairs",
            "best_qid", "match_type", "wd_label", "wd_description",
            "overlap_p11250", "note"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    c = Counter(r["match_type"] for r in rows)
    print(f"\nrows: {len(rows)}  breakdown: {dict(c)}  overlaps: {sum(1 for r in rows if r['overlap_p11250'])}")
    print(f"CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
