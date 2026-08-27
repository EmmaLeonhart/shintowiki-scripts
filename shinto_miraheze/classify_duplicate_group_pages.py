#!/usr/bin/env python3
"""
classify_duplicate_group_pages.py
=================================
Read-only. For every duplicate-QID group the dedupe planner files as
"two or more real names -- no single canonical", fetch each page and say
whether it is a real ARTICLE or a Wikidata PROPERTY DUMP.

Why this exists
---------------
``pick_canonical`` treats any title without a ``(Qnnn)`` suffix as a real
name. A property dump -- a page that is nothing but ``== instance of (P31) ==``
style sections under an infobox -- has exactly that shape, so it is
indistinguishable from a genuine article to the planner. Every such page turns
a mechanical merge into a decision handed to a human.

Measured 2026-08-27: **12 of the 25** groups in that bucket have exactly one
genuine article; the other side is a dump of 90-174 bytes of prose. They were
not human calls at all.

Prose measurement, and the trap in it
-------------------------------------
Strip the property-dump sections with the repo's own
``git_sync_strip_property_dumps.strip_property_dump``, then remove templates,
categories, files, HTML and headings, and measure what is left.

⚠ Templates MUST be stripped with a repeated innermost-first pass. A single
``re.sub(r"\\{\\{[^{}]*\\}\\}", "", text)`` cannot match a template containing
another one, so the infobox survives and gets counted as prose. That mistake
scored ``Mononobe Shrine (Nagoya)`` at 491 "prose" bytes and called a dump an
article -- the opposite of the answer -- until the balanced version scored it
at 94 against a real article's 1,812.

The separation is wide (90-174 vs 587-11,419), so the 200-byte threshold is not
a fine judgement call; anything near it should be read by a human anyway.

Usage: ``python shinto_miraheze/classify_duplicate_group_pages.py``
No flags, no writes, nothing to apply.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

from shinto_miraheze.user_agent import USER_AGENT
from shinto_miraheze.git_sync_strip_property_dumps import strip_property_dump

if getattr(sys.stdout, "encoding", "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API = "https://shinto.miraheze.org/w/api.php"
READ_THROTTLE = 0.35
QUERY_BATCH = 40
# Wide margin, not a fine line: dumps measured 90-174, articles 587-11,419.
ARTICLE_PROSE_BYTES = 200


def strip_templates(text: str) -> str:
    """Remove {{...}} including nested, innermost-first until stable."""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    return text


def prose_length(text: str) -> int:
    t = strip_property_dump(text)
    t = strip_templates(t)
    t = re.sub(r"\[\[Category:[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[File:[^\]]*\]\]", "", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"^=+.*$", "", t, flags=re.MULTILINE)
    t = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", t)
    return len(re.sub(r"\s+", " ", t).strip())


def fetch_contents(titles):
    out = {}
    for i in range(0, len(titles), QUERY_BATCH):
        batch = titles[i:i + QUERY_BATCH]
        url = API + "?" + urllib.parse.urlencode({
            "action": "query", "titles": "|".join(batch),
            "prop": "revisions", "rvprop": "content", "rvslots": "main",
            "format": "json", "formatversion": "2",
        })
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=90) as fh:
            data = json.load(fh)
        for page in data.get("query", {}).get("pages", []):
            if page.get("missing"):
                out[page["title"]] = None
            else:
                out[page["title"]] = page["revisions"][0]["slots"]["main"]["content"]
        time.sleep(READ_THROTTLE)
    return out


def main():
    from shinto_miraheze.dedupe_duplicate_qids import (
        DUPES_STATE, build_move_plan, load_json, resolve_qid_redirects, title_qid,
    )

    state = load_json(DUPES_STATE)
    by_qid = defaultdict(list)
    for title, qid in state.items():
        by_qid[qid].append(title)
    dup = {q for q, ps in by_qid.items() if len(ps) > 1}
    need = set(dup)
    for q in dup:
        for p in by_qid[q]:
            tq = title_qid(p)
            if tq:
                need.add(tq)

    print(f"Resolving {len(need)} QIDs against Wikidata...")
    resolved = resolve_qid_redirects(need, USER_AGENT)
    _, ambiguous = build_move_plan(state, resolved)
    groups = [g for g in ambiguous if g["reason"].startswith("two or more real names")]
    if not groups:
        print("No groups in the two-or-more-real-names bucket. Nothing to classify.")
        return

    titles = sorted({p for g in groups for p in g["pages"]})
    print(f"{len(groups)} groups, {len(titles)} pages to read")
    content = fetch_contents(titles)

    collapse, still, empty = [], [], []
    for g in groups:
        scored = [(p, prose_length(content[p]))
                  for p in g["pages"] if content.get(p) and not title_qid(p)]
        real = [p for p, n in scored if n >= ARTICLE_PROSE_BYTES]
        if len(real) == 1:
            collapse.append((g["qid"], scored, real[0]))
        elif not real:
            empty.append((g["qid"], scored))
        else:
            still.append((g["qid"], scored))

    print(f"\nONE genuine article (the rest are property dumps): {len(collapse)}")
    for qid, scored, keep in collapse:
        print(f"  {qid:14} KEEP {keep!r}")
        for p, n in scored:
            if p != keep:
                print(f"{'':17} dump {p!r} ({n}b prose)")

    print(f"\nTWO OR MORE genuine articles -- a real human call: {len(still)}")
    for qid, scored in still:
        print(f"  {qid:14} " + ", ".join(f"{p!r}={n}b" for p, n in scored))

    print(f"\nNO genuine article on either side (all stubs): {len(empty)}")
    for qid, scored in empty:
        print(f"  {qid:14} " + ", ".join(f"{p!r}={n}b" for p, n in scored))


if __name__ == "__main__":
    main()
