#!/usr/bin/env python3
"""
generate_honzon_quickstatements.py
===================================
Import 本尊 (principal image / main object of veneration) from the jawiki
{{日本の寺院}} temple infobox onto Wikidata as P825 (dedicated to) — the temple
sibling of generate_saijin_quickstatements.py, from
`docs/jawiki_infobox_import_review_2026-07.md`.

HIGH-PRECISION design — no name-matching, no guessing:
  * only deities that are WIKILINKED in the 祭神 field are imported;
  * each link target resolves to its Wikidata item via jawiki's own
    pageprops (wikibase_item), following redirects — jawiki's editorial
    linking is the identification, we never match by string;
  * unlinked plain-text deity names are counted and skipped;
  * (shrine, deity) pairs already on Wikidata are skipped (SPARQL set).

Output: honzon_p825.txt — atomic cited lines
    <shrine>|P825|<deity>|S143|Q177837|S4656|"<jawiki url>"

Usage:
    python generate_honzon_quickstatements.py             # full run
    python generate_honzon_quickstatements.py --limit 200 # sample
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
import json
import os
import re

import sys
import time
import urllib.parse
import urllib.request

from infobox_fields import field_pattern

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
# The class check below asks Wikidata, not jawiki, so _get takes an endpoint.
WD_API = "https://www.wikidata.org/w/api.php"
WDQS = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
TEMPLATE = "Template:日本の寺院"
OUTPUT = os.path.join(HERE, "honzon_p825.txt")

# Same ordered-alternation defect as 祭神: `[^\n|]` halted at the pipe inside the
# first piped wikilink, dropping every later 本尊. See infobox_fields.py.
# ⛔ A honzon is a DEITY. Refuse any resolved target whose Wikidata class says it
# is a heritage designation instead.
#
# Emma, 2026-09-12, first on Q1188622: "a completely invalid thing and we should
# never add it and should universally remove it from all items it is present on."
# Then, when the same error turned up twice more, on whether to keep naming QIDs:
# "Block the whole class instead."
#
# P825 is "dedicated to". Q1188622 is 重要文化財 and Q1139795 is 国宝 — both
# designations the Agency for Cultural Affairs awards to an object, and both
# P31 = Q30634609 heritage designation. "Dedicated to National Treasure" asserts
# nothing.
#
# They get in because this generator takes EVERY wikilink in the 本尊 field, and
# temple infoboxes write the designation beside the deity:
#     |本尊 = [[阿弥陀如来]]（[[重要文化財]]）
#
# MEASURED before choosing the class, over all 118 distinct values this generator
# emits: Q30634609 contains exactly ONE of them, Q1139795, at 23 lines. Nothing
# legitimate is in it. The neighbouring classes were checked and deliberately NOT
# blocked, because each holds real honzon —
#   Q23847174 religious concept : 曼荼羅, 仏舎利, and Bodhisattva itself
#   Q80071     symbol           : 曼荼羅
#   Q838948    work of art      : Q1410999 大曼荼羅, Nichiren's own Gohonzon
#   Q3658341   literary character: 地蔵菩薩, 文殊菩薩, 普賢菩薩 …
#
# ⚠ 秘仏 hibutsu (Q11595955, 53 lines) has NO P31 at all, so no class rule can
# reach it. It is left emitting, and named here so that is a known state.
# The root of the class, reached by P279 ONLY. Two wrong versions came first:
#   * P31 = Q30634609 alone caught 2 of the 4 — Q858308 (日本の文化財) and
#     Q2901860 (有形文化財) carry no P31 at all.
#   * (P31|P279)/P279* to Q2065736 cultural property caught all four AND 42
#     legitimate statements, because "instance of a cultural property" is true of
#     every listed building: Holy Sepulchre (31), its church, Santa Maria sopra
#     Minerva, Portiuncula, the Warsaw Ghetto.
# Subclass-only, rooted at the Japanese designation family, draws it exactly:
#     Q1139795 国宝 -P279-> Q1188622 -P279-> Q2901860 -P279-> Q858308
#
# ⭐ It does NOT reach 秘仏 (Q11595955 -P279-> Q1000809 Buddharupa -P279-> statue),
# 仏像, or Q101659 dolmen — a monument type that subclasses cultural property
# without being a designation. The chain draws the line; a session does not.
INVALID_HONZON_ROOTS = {
    "Q858308",     # Cultural Property of Japan 日本の文化財, and every subclass
}
MAX_CLASS_DEPTH = 6


def refused_classes(qids):
    """{qid} whose P31/P279 ancestry reaches a blocked root.

    Walks upward in batches rather than asking SPARQL, so this script keeps its
    one dependency (the two MediaWiki APIs) and costs a handful of requests.
    """
    # `P279*` includes zero steps, so a target that IS a root counts. The first
    # version only looked at parents and let Q858308 itself through — caught by
    # the nine-case check, not by reading.
    blocked = {q for q in qids if q in INVALID_HONZON_ROOTS}
    seen = set()
    frontier = {q for q in qids if q}
    origin = {q: {q} for q in frontier}          # ancestor -> which targets it came from
    for _ in range(MAX_CLASS_DEPTH):
        frontier = {q for q in frontier if q not in seen}
        if not frontier:
            break
        seen |= frontier
        parents = {}
        batch = sorted(frontier)
        for i in range(0, len(batch), 50):
            d = _get({"action": "wbgetentities", "props": "claims",
                      "ids": "|".join(batch[i:i + 50])}, api=WD_API)
            for qid, ent in (d.get("entities") or {}).items():
                claims = ent.get("claims") or {}
                # P279 ONLY. Adding P31 means "the value is an instance of a
                # cultural property", which is true of every listed building —
                # it swept up Holy Sepulchre, its church, and the Warsaw Ghetto.
                for prop in ("P279",):
                    for c in claims.get(prop, []):
                        v = c["mainsnak"].get("datavalue", {}).get("value", {})
                        if isinstance(v, dict) and v.get("id"):
                            parents.setdefault(qid, set()).add(v["id"])
            time.sleep(0.3)
        nxt = set()
        for qid, ps in parents.items():
            src = origin.get(qid, set())
            for parent in ps:
                if parent in INVALID_HONZON_ROOTS:
                    blocked |= src
                else:
                    origin.setdefault(parent, set()).update(src)
                    nxt.add(parent)
        frontier = nxt
    return blocked


_FIELD_RE = re.compile(field_pattern("本尊"))
_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def _get(params, api=None):
    params = dict(params)
    params["format"] = "json"
    req = urllib.request.Request((api or JA_API) + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def temple_titles():
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


def existing_pairs():
    q = "SELECT ?s ?d WHERE { ?s wdt:P31 wd:Q5393308 ; wdt:P825 ?d . }"
    url = WDQS + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    return {(b["s"]["value"].rsplit("/", 1)[-1], b["d"]["value"].rsplit("/", 1)[-1])
            for b in rows}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have = existing_pairs()
    print(f"{len(have)} existing (temple, honzon) P825 pairs on Wikidata")
    titles = temple_titles()
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} jawiki temple articles")

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
    print(f"{len(shrine_deities)} temples with linked honzon "
          f"(no-field={no_field}, no-QID={no_qid}, fields-with-unlinked-names={unlinked})")

    # pass 2: resolve deity link targets to QIDs
    all_targets = {t for links in shrine_deities.values() for t in links}
    resolved = resolve_links(all_targets)
    print(f"{len(resolved)}/{len(all_targets)} deity link targets resolve to Wikidata items")

    refused = refused_classes(set(resolved.values()))
    print(f"{len(refused)} resolved target(s) refused as a heritage designation")

    lines, dup, invalid = [], 0, 0
    for (title, qid), links in sorted(shrine_deities.items()):
        url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        for t in dict.fromkeys(links):
            d = resolved.get(t)
            if not d:
                continue
            if d in refused:
                invalid += 1
                continue
            if (qid, d) in have:
                dup += 1
                continue
            lines.append(f'{qid}|P825|{d}|S143|Q177837|S4656|"{url}"')
    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P825 lines -> {OUTPUT} (already-present pairs skipped: {dup}, invalid honzon refused: {invalid})")


if __name__ == "__main__":
    main()
