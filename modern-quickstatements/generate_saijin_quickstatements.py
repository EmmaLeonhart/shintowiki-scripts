#!/usr/bin/env python3
"""
generate_saijin_quickstatements.py
===================================
Import 祭神 (enshrined deities) from the jawiki {{神社}} shrine infobox onto
Wikidata as P825 (dedicated to) — the volume build from
`docs/jawiki_infobox_import_review_2026-07.md`. Independently motivated by the
deity-description test (2026-07-08): 6,841 colliding English-labeled shrines
have no P825 at all.

HIGH-PRECISION design — no name-matching, no guessing:
  * only deities that are WIKILINKED in the 祭神 field are imported;
  * each link target resolves to its Wikidata item via jawiki's own
    pageprops (wikibase_item), following redirects — jawiki's editorial
    linking is the identification, we never match by string;
  * unlinked plain-text deity names are counted and skipped;
  * (shrine, deity) pairs whose statement is ALREADY REFERENCED are skipped.

⛔ **The skip set is `referenced_pairs()`, not `existing_pairs()`.**
`audit_model_adoption.py` measured shrine P825 on 2026-09-15 at **5,630 referenced
of 16,137 statements — 35%** — beside temple P825 at 6,172/6,379 (96.8%) and
P13723 at 16,802/16,995 (98.9%). The temple sibling scores high because we created
nearly all of it, cited, from the 本尊 field; the shrine population is mostly older
imports by other editors that landed bare.

Skipping every pair that merely *exists* made those ~10,500 bare statements
unreachable: this generator would not touch them again, and it is the only thing
that knows which jawiki article the deity was read from. Skipping only the
REFERENCED ones re-emits a bare statement WITH its citation — QuickStatements
matches the existing (item, property, value) and attaches the reference to that
statement rather than duplicating it. Same fix as
`generate_court_rank_quickstatements.py` took on 2026-09-15, and the `c121509e`
shape before it.

Output: saijin_p825.txt — atomic cited lines
    <shrine>|P825|<deity>|S143|Q177837|S4656|"<jawiki url>"

Usage:
    python generate_saijin_quickstatements.py             # full run
    python generate_saijin_quickstatements.py --limit 200 # sample
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import io
import os
import re

import sys
import time
import urllib.parse

import requests

from infobox_fields import field_pattern

# Plain module import, matching the other adopters — test_wdqs_transport.py checks
# for exactly this line as the evidence a file has not grown its own urlopen back.
import wdqs_transport

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
# The SPARQL endpoint and its Accept header moved into wdqs_transport with the
# transport itself. UA stays: the ja.wikipedia calls below still use it.
UA = WIKIDATA_USER_AGENT
TEMPLATE = "Template:神社"
OUTPUT = os.path.join(HERE, "saijin_p825.txt")

# Was `((?:[^\n|]|\[\[…)*)`. Regex alternation is ordered, so `[^\n|]` consumed
# `[[天照大神` character-by-character and then halted at the pipe INSIDE the
# wikilink — `\[\[…\]\]` never got a chance. Given
#     |祭神 = [[天照大神|天照大御神]]、[[素戔嗚尊]]、[[大国主|大国主命]]
# it captured "[[天照大神" and silently dropped two of the three deities.
# Bracketed alternatives must come first. See infobox_fields.py.
_FIELD_RE = re.compile(field_pattern("祭神"))
_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def _get(params):
    """One ja.wikipedia API call, retried three times.

    `requests`, not a raw urlopen, for the same reason
    `generate_court_rank_quickstatements.py` uses it: this file's SPARQL now goes
    through `wdqs_transport`, and `test_wdqs_transport.py` reads a hand-rolled
    urlopen anywhere in an adopter as evidence it has grown its own WDQS transport
    back. Conforming to that convention is the right move; loosening the assertion
    is not. Behaviour is unchanged — same params, same UA, same three attempts.
    """
    params = dict(params)
    params["format"] = "json"
    for attempt in range(3):
        try:
            r = requests.get(JA_API, params=params,
                             headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 429:
                raise SystemExit("429 from ja.wikipedia — bailing.")
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def shrine_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": TEMPLATE,
             "einamespace": 0, "eilimit": "max"}
        if cont:
            p["eicontinue"] = cont
        d = _get(p)
        titles += [e["title"] for e in d.get("query", {}).get("embeddedin", [])]
        cont = d.get("continue", {}).get("eicontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def fetch_batch(titles):
    d = _get({"action": "query", "prop": "revisions|pageprops", "rvprop": "content",
              "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles), "redirects": 1})
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        qid = p.get("pageprops", {}).get("wikibase_item")
        revs = p.get("revisions", [])
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        out.append((p["title"], qid, text))
    return out


def resolve_links(titles):
    """{jawiki title -> wikidata QID} for deity link targets (redirects followed)."""
    out = {}
    titles = sorted(titles)
    for i in range(0, len(titles), 50):
        d = _get({"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                  "titles": "|".join(titles[i:i + 50]), "redirects": 1})
        qy = d.get("query", {})
        remap = {}
        for r in qy.get("normalized", []) + qy.get("redirects", []):
            remap[r["from"]] = r["to"]
        final = {}
        for t in titles[i:i + 50]:
            ft = t
            seen = set()
            while ft in remap and ft not in seen:
                seen.add(ft)
                ft = remap[ft]
            final[t] = ft
        by_title = {p["title"]: p.get("pageprops", {}).get("wikibase_item")
                    for p in qy.get("pages", {}).values() if "missing" not in p}
        for t, ft in final.items():
            if by_title.get(ft):
                out[t] = by_title[ft]
        time.sleep(0.3)
    return out


def _pairs(rows):
    return {(b["s"]["value"].rsplit("/", 1)[-1], b["d"]["value"].rsplit("/", 1)[-1])
            for b in rows}


def existing_pairs():
    """Every (shrine, deity) P825 pair on Wikidata. COUNT ONLY — not the skip set.

    ⚠ The 429 check this used to carry — `if r.status == 429` after a successful
    `urlopen` — was dead code: urllib raises `HTTPError` on a 429 and never returns
    a response to test. The transport bails on it properly.
    """
    return _pairs(wdqs_transport.query(
        "SELECT ?s ?d WHERE { ?s wdt:P31 wd:Q845945 ; wdt:P825 ?d . }"))


def referenced_pairs():
    """(shrine, deity) pairs whose P825 statement ALREADY carries a reference.

    ⛔ THIS IS THE SKIP SET, not `existing_pairs()`. Skipping every pair that
    merely exists is what left shrine P825 at **5,630 referenced of 16,137
    statements (35%)** while the temple sibling, built by the 本尊 generator with
    the same reference shape, sits at 96.8% — measured by
    `audit_model_adoption.py` on 2026-09-15.

    The shrine population is mostly older imports that landed bare, and this
    generator is the only thing that knows which ja.wikipedia article named the
    deity. Skipping on "has the statement" made all ~10,500 of them unreachable
    for good.

    Re-emitting the same statement WITH a reference does not duplicate it:
    QuickStatements matches the existing (item, property, value) and attaches the
    reference to it. Same fix `generate_court_rank_quickstatements.py` took on
    2026-09-15, and the `c121509e` shape before that.
    """
    return _pairs(wdqs_transport.query("""
      SELECT ?s ?d WHERE {
        ?s wdt:P31 wd:Q845945 ; p:P825 ?st .
        ?st ps:P825 ?d .
        ?st prov:wasDerivedFrom ?ref .
      }
    """))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have = existing_pairs()
    referenced = referenced_pairs()
    print(f"{len(have)} existing (shrine, deity) P825 pairs on Wikidata; "
          f"{len(referenced)} referenced, "
          f"{len(have - referenced)} bare and reachable for enrichment")
    titles = shrine_titles()
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} jawiki shrine articles")

    # pass 1: parse fields, collect linked deity targets
    shrine_deities = {}     # (shrine_title, shrine_qid) -> [deity jawiki titles]
    unlinked = no_field = no_qid = 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            m = _FIELD_RE.search(text or "")
            if not m or not m.group(1).strip():
                no_field += 1
                continue
            if not qid:
                no_qid += 1
                continue
            links = [t.strip() for t in _LINK_RE.findall(m.group(1))
                     if t.strip() and not t.startswith(("File:", "ファイル:", "Category:"))]
            plain = _LINK_RE.sub("", m.group(1))
            if re.search(r"[一-龠ぁ-んァ-ヶ]{2,}", plain):
                unlinked += 1   # field also has unlinked names — those are skipped
            if links:
                shrine_deities[(title, qid)] = links
        time.sleep(0.3)
    print(f"{len(shrine_deities)} shrines with linked deities "
          f"(no-field={no_field}, no-QID={no_qid}, fields-with-unlinked-names={unlinked})")

    # pass 2: resolve deity link targets to QIDs
    all_targets = {t for links in shrine_deities.values() for t in links}
    resolved = resolve_links(all_targets)
    print(f"{len(resolved)}/{len(all_targets)} deity link targets resolve to Wikidata items")

    lines, dup = [], 0
    for (title, qid), links in sorted(shrine_deities.items()):
        url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        for t in dict.fromkeys(links):
            d = resolved.get(t)
            if not d:
                continue
            if (qid, d) in referenced:
                dup += 1
                continue
            lines.append(f'{qid}|P825|{d}|S143|Q177837|S4656|"{url}"')
    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P825 lines -> {OUTPUT} (already-REFERENCED pairs skipped: {dup})")


if __name__ == "__main__":
    main()
