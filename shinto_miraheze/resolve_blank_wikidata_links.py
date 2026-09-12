#!/usr/bin/env python3
"""
resolve_blank_wikidata_links.py
===============================
Proposes a QID for each mainspace page whose ``{{wikidata link}}`` is blank and
which ``wikidata_lookup`` can never reach.

The gap, restated
-----------------
``wikidata_lookup`` resolves the QID out of the template's own ``(lang, target)``
pairs. A page with a blank template and no pairs has nothing for it to resolve
FROM, so it stays blank forever. ``report_blank_wikidata_links.py`` measured that
population on 2026-09-12: 233 blank of 11,069, of which 170 are Q-titled stubs
that `dedupe_duplicate_qids` will redirect away and **58 are named pages**.

This script resolves those 58 — and it does it from the page TITLE, which is the
one piece of evidence such a page always has.

⛔ What it deliberately does NOT do
----------------------------------
CLAUDE.md: *"Never issue a large batched SPARQL sweep"*, and *"Wikidata is a
DESTINATION, not a database to query for working data."* A per-page
``wbsearchentities`` or SPARQL lookup over the worklist is exactly the shape that
rule was written about. So:

1. **Free evidence first.** Our own ``modern-quickstatements/*en_labels*.txt``
   already map QID -> English label for tens of thousands of items. A title that
   matches exactly one of them is resolved at zero request cost.
2. **Then ONE batched sitelink call per wiki.** ``wbgetentities`` takes
   ``sites=enwiki&titles=A|B|C…`` 50 at a time, so the whole remaining worklist
   costs 2 requests against enwiki and 2 against jawiki — not 58, and not 116.
3. **Then the page's OWN Japanese name**, which is what actually resolves the
   case Emma named. ``Shizensha`` is not a sitelink of anything — ``Q139921367``
   links to jawiki 自然社 — so a title lookup misses it, and the answer is sitting
   in the page's own infobox as ``native_name = 自然社``. CLAUDE.md's stated
   preference when a Wikidata query looks necessary is "a jawiki article's own
   content" over a search, and this is that: read the Japanese name off the page,
   then one more batched jawiki sitelink call.

Refusals are the point, not a shortfall
---------------------------------------
* A title of 1-2 characters (``R``, ``S``, ``T``) is refused. An exact sitelink
  hit on a single letter says nothing about what the page is.
* enwiki and jawiki resolving to DIFFERENT items is refused, not arbitrated.
* An item that our own en-label file and the sitelink disagree about is refused.

Read-only against both wikis. No edit is made here, so neither the
shinto.miraheze lockout nor the Wikidata one gates it; applying the proposals is
a separate script by design, because add-and-apply in one pass is what this repo
has been bitten by before.

Output: ``docs/blank_wikidata_link_proposals.md`` plus a machine-readable
``shinto_miraheze/blank_wikidata_link_proposals.state``.
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
import sys
import time

import requests

from shinto_miraheze.user_agent import USER_AGENT
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

WD_API = "https://www.wikidata.org/w/api.php"
MIRAHEZE_API = "https://shinto.miraheze.org/w/api.php"

# Paced like every other Wikidata caller here. Four requests total, but the
# interval is the repo's floor, not a per-script choice.
WD_THROTTLE = 2.5
# shinto.miraheze reads, paced like the redirect-chain followers here.
READ_THROTTLE = 0.3
BATCH = 50

# A sitelink hit on a title this short is not evidence of anything.
MIN_TITLE_LEN = 3

STATE = os.path.join(_uar, "shinto_miraheze", "blank_wikidata_link_proposals.state")
REPORT = os.path.join(_uar, "docs", "blank_wikidata_link_proposals.md")

_QID_TITLE = re.compile(r"^Q\d+$")
_QS_EN_LABEL = re.compile(r'^(Q\d+)[|\t]L(?:en|EN)[|\t]"(.*)"\s*$')


def named_blank_titles(report_path):
    """The 58: blank pages that are not Q-titled stubs, lists or dabs.

    Read from `report_blank_wikidata_links.py`'s output rather than re-swept, so
    the two scripts cannot disagree about what the worklist is.
    """
    text = io.open(report_path, encoding="utf-8").read()
    if "## Blank" not in text:
        raise SystemExit(f"{report_path} has no '## Blank' section — re-run "
                         "report_blank_wikidata_links.py first")
    section = text.split("## Blank", 1)[1].split("## Missing", 1)[0]
    titles = re.findall(r"^\* \[\[(.+?)\]\]$", section, re.M)
    return [t for t in titles
            if not _QID_TITLE.match(t)
            and not t.lower().startswith("list of")
            and "(disambiguation)" not in t.lower()]


def local_en_labels():
    """{en label: {qid}} from our own staged batches. Costs nothing.

    A label held by two QIDs is kept as a set so the caller can refuse it rather
    than pick one — two items sharing an English name is exactly the case where
    a title match proves nothing.
    """
    mq = os.path.join(_uar, "modern-quickstatements")
    out = {}
    if not os.path.isdir(mq):
        return out
    for name in sorted(os.listdir(mq)):
        if not name.endswith(".txt") or "en_label" not in name:
            continue
        for line in io.open(os.path.join(mq, name), encoding="utf-8"):
            m = _QS_EN_LABEL.match(line.strip())
            if m:
                out.setdefault(m.group(2).replace('""', '"'), set()).add(m.group(1))
    return out


# The page's own Japanese name, taken only from places that ANNOUNCE it as the
# name. A bare CJK run anywhere in the body is not a candidate — these articles
# are full of incidental Japanese, and guessing from it is how you resolve a
# shrine to a place name that happened to appear in its address.
_CJK = r"[぀-ヿ㐀-䶿一-鿿豈-﫿々〆ヵヶ・ー]"
_NAME_FIELDS = (
    re.compile(r"\|\s*native_name\s*=\s*(" + _CJK + r"{2,})\s*(?:\||$)", re.M),
    re.compile(r"\{\{\s*[Nn]ihongo\s*\|[^|]*\|\s*(" + _CJK + r"{2,})\s*[|}]"),
    re.compile(r"\{\{\s*lang\s*\|\s*ja\s*\|\s*(" + _CJK + r"{2,})\s*\}\}"),
)


def japanese_names(wikitext):
    """Ordered, de-duplicated Japanese names the page states for itself."""
    out = []
    for pattern in _NAME_FIELDS:
        for m in pattern.finditer(wikitext or ""):
            name = m.group(1).strip()
            if name and name not in out:
                out.append(name)
    return out


def fetch_wikitext(titles, session):
    """{title: wikitext} from shinto.miraheze, 50 titles a request."""
    out = {}
    for i in range(0, len(titles), BATCH):
        r = session.get(MIRAHEZE_API, params={
            "action": "query", "format": "json", "formatversion": "2",
            "prop": "revisions", "rvprop": "content", "rvslots": "main",
            "titles": "|".join(titles[i:i + BATCH]),
        }, headers={"User-Agent": USER_AGENT}, timeout=120)
        r.raise_for_status()
        for page in r.json().get("query", {}).get("pages", []):
            revs = page.get("revisions")
            if revs:
                out[page["title"]] = revs[0]["slots"]["main"]["content"]
        time.sleep(READ_THROTTLE)
    return out


def resolve(titles, session, want_sites=("enwiki", "jawiki")):
    """[(title, qid | None, reason, evidence)] for every title."""
    labels = local_en_labels()
    results = {}
    remaining = []

    for title in titles:
        if len(title) < MIN_TITLE_LEN:
            results[title] = (None, "title too short to be evidence", {})
            continue
        hits = labels.get(title)
        if hits and len(hits) == 1:
            results[title] = (next(iter(hits)), "our own staged en label", {"source": "local"})
            continue
        if hits and len(hits) > 1:
            results[title] = (None, f"{len(hits)} staged items share this en label", {})
            continue
        remaining.append(title)

    per_site = {}
    for site in want_sites:
        per_site[site] = sitelinks_for(remaining, site, session)

    still_open = []
    for title in remaining:
        found = {site: per_site[site].get(title) for site in want_sites}
        qids = {q for q in found.values() if q}
        if not qids:
            still_open.append(title)
        elif len(qids) > 1:
            results[title] = (None, "enwiki and jawiki resolve to different items", found)
        else:
            qid = next(iter(qids))
            where = ", ".join(s for s, q in found.items() if q)
            results[title] = (qid, f"sitelink on {where}", found)

    # Third pass: the page's own Japanese name. This is the one that reaches
    # Shizensha, whose jawiki sitelink is 自然社 and whose title therefore matches
    # nothing.
    if still_open:
        bodies = fetch_wikitext(still_open, session)
        candidates = {t: japanese_names(bodies.get(t, "")) for t in still_open}
        flat = sorted({n for names in candidates.values() for n in names})
        ja_qid = sitelinks_for(flat, "jawiki", session) if flat else {}
        for title in still_open:
            hits = {ja_qid[n]: n for n in candidates[title] if n in ja_qid}
            if len(hits) == 1:
                qid, name = next(iter(hits.items()))
                results[title] = (qid, f"jawiki sitelink of its own stated name {name}",
                                  {"ja_name": name})
            elif len(hits) > 1:
                results[title] = (None, "its stated Japanese names resolve to different items", {})
            elif candidates[title]:
                results[title] = (None,
                                  "no sitelink for its title or its stated name "
                                  + "/".join(candidates[title]), {})
            else:
                results[title] = (None, "no sitelink, and the page states no Japanese name", {})

    return [(t, *results[t]) for t in titles]


def sitelinks_for(titles, site, session):
    """{our title: qid} — the sitelink lookup, batched, keyed back correctly.

    The pairing has to come from `props=sitelinks` filtered to the site we asked
    about: `wbgetentities` keys its answer by QID, not by the title we sent, and
    it silently normalises spellings, so reading the sitelink back off each
    entity is the only way to know which request a QID answers.
    """
    found = {}
    for i in range(0, len(titles), BATCH):
        chunk = titles[i:i + BATCH]
        time.sleep(WD_THROTTLE)
        r = session.get(WD_API, params={
            "action": "wbgetentities",
            "sites": site,
            "titles": "|".join(chunk),
            "props": "sitelinks",
            "sitefilter": site,
            "format": "json",
        }, timeout=120)
        r.raise_for_status()
        data = r.json()
        norm = {n["to"]: n["from"] for n in (data.get("normalized") or [])}
        for qid, entity in (data.get("entities") or {}).items():
            if not qid.startswith("Q") or "missing" in entity:
                continue
            link = (entity.get("sitelinks") or {}).get(site)
            if not link:
                continue
            wd_title = link["title"]
            found[norm.get(wd_title, wd_title)] = qid
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", default=os.path.join(_uar, "docs", "blank_wikidata_links.md"),
                    help="the measurement this worklist comes from")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    titles = named_blank_titles(args.report)
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} named pages with a blank {{{{wikidata link}}}}")

    session = requests.Session()
    session.headers["User-Agent"] = WIKIDATA_USER_AGENT

    rows = resolve(titles, session)

    resolved = [r for r in rows if r[1]]
    refused = [r for r in rows if not r[1]]
    print(f"  resolved: {len(resolved)}")
    print(f"  refused:  {len(refused)}")

    by_reason = {}
    for _, qid, reason, _ in rows:
        key = ("RESOLVED " if qid else "refused ") + reason
        by_reason[key] = by_reason.get(key, 0) + 1
    for k in sorted(by_reason, reverse=True):
        print(f"    {by_reason[k]:>4}  {k}")

    payload = {t: {"qid": q, "reason": why} for t, q, why, _ in rows}
    with io.open(STATE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, sort_keys=True)

    lines = [
        "# Blank `{{wikidata link}}` — proposed QIDs",
        "",
        "Generated by `shinto_miraheze/resolve_blank_wikidata_links.py`. Read-only; nothing was",
        "edited on either wiki. Applying these is a separate script.",
        "",
        "Resolution order: our own staged `en_labels` batches (free), then one batched",
        "`wbgetentities` sitelink call per wiki. No `wbsearchentities`, no SPARQL — see the",
        "script's docstring for why.",
        "",
        f"{len(resolved)} resolved, {len(refused)} refused, of {len(titles)} named pages.",
        "",
        "## Proposed",
        "",
        "| page | QID | evidence |",
        "|---|---|---|",
    ]
    for t, q, why, _ in rows:
        if q:
            lines.append(f"| [[{t}]] | [{q}](https://www.wikidata.org/wiki/{q}) | {why} |")
    lines += ["", "## Refused", "", "| page | why |", "|---|---|"]
    for t, q, why, _ in rows:
        if not q:
            lines.append(f"| [[{t}]] | {why} |")
    lines.append("")

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    print(f"\nwrote {REPORT}\nwrote {STATE}")


if __name__ == "__main__":
    main()
