#!/usr/bin/env python3
"""
generate_bunrei_quickstatements.py
==================================
Derive shrine bunrei (分霊) lineage — branch shrine -> its network's head shrine
(総本社) — and emit QuickStatements for Wikidata. There is NO downloadable dataset
of the per-branch edge (confirmed: gov/academic/LOD/commercial/community all have
node data only). The network->head mapping IS documented; the authoritative source
used here is jinja-kikou.net's 分霊分社一覧表, cited on every statement.

Method: jinja-kikou gives (network -> head shrine). Each Wikidata Shinto shrine is
classified into a network by its Japanese label suffix (a shrine named 〇〇八幡神社
is a Hachiman-network shrine), and gets:
    <branch> P612 <head shrine>            # mother house
             P1013 Q195793  (qualifier)    # criterion used = Bunrei
             S854 "<jinja-kikou url>"       # reference URL

CAVEAT (honest): P612 here is the network HEAD (総本社), not necessarily the
immediate parent a branch was directly kanjō'd from — the immediate parent is not
published anywhere machine-readable. Only unambiguous single-head networks with a
distinctive label suffix are included; two-/three-headed networks are handled with
the conventional 総本社. Run LOCALLY; writes bunrei.txt into this directory (an
atomic file the daily direct_daily_edits pipeline drains). QS skips existing.

Usage: python generate_bunrei_quickstatements.py [--stats]
"""

import argparse
import io
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WDQS = "https://query-main.wikidata.org/sparql"   # query.wikidata.org is 429-outaged
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
OUTPUT = os.path.join(HERE, "bunrei.txt")

Q_BUNREI = "Q195793"
SOURCE_URL = "http://jinja-kikou.net/bunreibunsya.html"

# (head shrine QID, [ja label suffixes]) per network — heads resolved from Wikidata,
# network->head from jinja-kikou's 分霊分社一覧表. Longest/most-specific suffixes first.
NETWORKS = [
    ("Q715632", ["八幡神社", "八幡宮", "八幡社"]),        # Hachiman -> 宇佐神宮
    ("Q714828", ["稲荷神社", "稲荷社"]),                   # Inari -> 伏見稲荷大社
    ("Q218813", ["諏訪神社", "諏訪社"]),                   # Suwa -> 諏訪大社
    ("Q714559", ["春日神社"]),                             # Kasuga -> 春日大社
    ("Q705949", ["住吉神社"]),                             # Sumiyoshi -> 住吉大社
    ("Q704702", ["白山神社"]),                             # Hakusan -> 白山比咩神社
    ("Q656451", ["日枝神社", "日吉神社"]),                 # Hie/Sanno -> 日吉大社
    ("Q692714", ["八坂神社", "祇園神社"]),                 # Yasaka/Gion -> 八坂神社
    ("Q94760",  ["金刀比羅神社", "金比羅神社", "琴平神社", "金刀比羅宮"]),  # Konpira -> 金刀比羅宮
    ("Q500413", ["秋葉神社"]),                             # Akiba -> 秋葉山本宮秋葉神社
    ("Q372380", ["香取神社"]),                             # Katori -> 香取神宮
    ("Q706499", ["鹿島神社"]),                             # Kashima -> 鹿島神宮
    ("Q191763", ["厳島神社", "嚴島神社"]),                 # Itsukushima -> 厳島神社
    ("Q704962", ["宗像神社"]),                             # Munakata -> 宗像大社
    ("Q703633", ["氷川神社"]),                             # Hikawa -> 氷川神社 (武蔵一宮)
    ("Q653180", ["浅間神社"]),                             # Sengen/Asama -> 富士山本宮浅間大社
    ("Q402091", ["多賀神社"]),                             # Taga -> 多賀大社
    ("Q710302", ["松尾神社"]),                             # Matsuo -> 松尾大社
    ("Q482065", ["熱田神社"]),                             # Atsuta -> 熱田神宮
    ("Q710786", ["天満宮", "天満神社", "天神社", "菅原神社"]),  # Tenjin -> 太宰府天満宮 (conventional 総本社)
    ("Q705035", ["熊野神社"]),                             # Kumano -> 熊野本宮大社 (primary of the 三山)
    ("Q713021", ["愛宕神社"]),                             # Atago -> 愛宕神社 (京都)
]
HEAD_QIDS = {n[0] for n in NETWORKS}


def all_shrines():
    """[(qid, ja_label)] for every Wikidata Shinto shrine (P31=Q845945) with a ja label."""
    qy = ('SELECT ?item ?ja WHERE { ?item wdt:P31 wd:Q845945 ; rdfs:label ?ja . '
          'FILTER(LANG(?ja)="ja") }')
    url = WDQS + "?" + urllib.parse.urlencode({"query": qy, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        rows = json.load(r)["results"]["bindings"]
    return [(x["item"]["value"].rsplit("/", 1)[-1], x["ja"]["value"]) for x in rows]


def head_for(ja_label):
    for head_qid, suffixes in NETWORKS:
        if any(ja_label.endswith(s) for s in suffixes):
            return head_qid
    return None


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true", help="Print counts, write nothing.")
    args = ap.parse_args()

    shrines = all_shrines()
    lines, per_head = [], {}
    for qid, ja in shrines:
        if qid in HEAD_QIDS:          # never make a head its own branch
            continue
        head = head_for(ja)
        if not head:
            continue
        lines.append(f'{qid}|P612|{head}|P1013|{Q_BUNREI}|S854|"{SOURCE_URL}"')
        per_head[head] = per_head.get(head, 0) + 1

    print(f"shrines scanned: {len(shrines)} ; bunrei edges: {len(lines)}")
    for head, n in sorted(per_head.items(), key=lambda x: -x[1]):
        print(f"  {n:5d} -> {head}")
    if args.stats:
        return
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        if lines:
            f.write("\n")
    print(f"Wrote {os.path.basename(OUTPUT)} ({len(lines)} statements)")


if __name__ == "__main__":
    main()
