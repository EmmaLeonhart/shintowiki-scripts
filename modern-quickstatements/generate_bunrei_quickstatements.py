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

TIME-BOXED — STOPS 2027-02-01 (Emma 2026-08-03, queue A0b). This generator is
"inaccurate but descriptive": the suffix -> network-head guess is only
approximately right, and that is the point — being approximately-right and
VISIBLE on Wikidata seeds the convention and invites better-equipped human
editors to correct it. It is not meant to be perpetual maintenance. The accurate
layer is the per-shrine Opus pass (`shinto_miraheze/build_beppyo_p612_queue.py`),
which reads each article and names the actual 勧請元.

The stop is a DATE GATE, not a future commit-then-revert (CLAUDE.md: express the
exception as a rule). After SUNSET the script exits before querying and before
opening the output file — deliberately, because main() opens it with "w", so a
post-sunset run that produced no lines would TRUNCATE bunrei.txt and destroy
whatever the daily drip has not yet delivered.

Usage: python generate_bunrei_quickstatements.py [--stats]
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import datetime
import io
import json
import os
import sys
import urllib.parse

# Emma 2026-08-03: "keep the suffix-based generator but time-box it to ~6 months,
# then STOP." Six months from that instruction.
SUNSET = datetime.date(2027, 2, 1)


def sunset_reached(today=None):
    return (today or datetime.date.today()) >= SUNSET
import urllib.request
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

HERE = os.path.dirname(os.path.abspath(__file__))
WDQS = "https://query-main.wikidata.org/sparql"   # query.wikidata.org is 429-outaged
UA = WIKIDATA_USER_AGENT
Q_BUNREI = "Q195793"

# One config per online source. Each source = (network->head suffix map) + its own
# citation URL + its own output file. Overlapping networks across sources are fine
# (idempotent); a new source's file only needs to carry the networks IT documents,
# especially the ones earlier sources missed. (head shrine QID, [ja label suffixes]).
SOURCES = {
    # jinja-kikou.net 分霊分社一覧表 — the 22 main networks.
    "jinja_kikou": {
        "url": "http://jinja-kikou.net/bunreibunsya.html",
        "out": "bunrei.txt",
        "networks": [
            ("Q715632", ["八幡神社", "八幡宮", "八幡社"]),        # Hachiman -> 宇佐神宮
            ("Q714828", ["稲荷神社", "稲荷社"]),                   # Inari -> 伏見稲荷大社
            ("Q218813", ["諏訪神社", "諏訪社"]),                   # Suwa -> 諏訪大社
            ("Q714559", ["春日神社"]),                             # Kasuga -> 春日大社
            ("Q705949", ["住吉神社"]),                             # Sumiyoshi -> 住吉大社
            ("Q704702", ["白山神社"]),                             # Hakusan -> 白山比咩神社
            ("Q656451", ["日枝神社", "日吉神社"]),                 # Hie/Sanno -> 日吉大社
            ("Q692714", ["八坂神社", "祇園神社"]),                 # Yasaka/Gion -> 八坂神社
            ("Q94760",  ["金刀比羅神社", "金比羅神社", "琴平神社", "金刀比羅宮"]),  # Konpira
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
            ("Q710786", ["天満宮", "天満神社", "天神社", "菅原神社"]),  # Tenjin -> 太宰府天満宮
            ("Q705035", ["熊野神社"]),                             # Kumano -> 熊野本宮大社
            ("Q713021", ["愛宕神社"]),                             # Atago -> 愛宕神社 (京都)
        ],
    },
    # animism.world 総本社まとめ — the networks jinja-kikou missed.
    "animism": {
        "url": "https://animism.world/column/souhonja-matome/",
        "out": "bunrei_animism.txt",
        "networks": [
            ("Q276779", ["貴船神社"]),                             # Kifune -> 貴船神社 (京都)
            ("Q696641", ["東照宮"]),                               # Toshogu -> 日光東照宮
            ("Q11435950", ["大杉神社"]),                           # Osugi -> 大杉神社 (茨城)
            ("Q7007362", ["淡島神社", "淡嶋神社"]),                # Awashima -> 淡嶋神社 (和歌山)
            ("Q3541617", ["猿田彦神社"]),                          # Sarutahiko -> 椿大神社
            ("Q3313076", ["事代主神社"]),                          # Kotoshironushi -> 美保神社
        ],
    },
    # jisha-toranomaki.com 系列社 table (30 networks) — adds Ebisu.
    "toranomaki": {
        "url": "https://jisha-toranomaki.com/jinja-keiretsusha/",
        "out": "bunrei_toranomaki.txt",
        "networks": [
            ("Q705297", ["恵比寿神社", "恵比須神社", "戎神社", "蛭子神社", "えびす神社"]),  # Ebisu -> 西宮神社
        ],
    },
    # ikkojin.jp 系統ランキング (一個人 magazine, Jinja-Honcho survey counts) — adds Shirahige, Otori.
    "ikkojin": {
        "url": "https://ikkojin.jp/article/110/",
        "out": "bunrei_ikkojin.txt",
        "networks": [
            ("Q705303", ["白鬚神社", "白髭神社", "白髯神社"]),      # Shirahige -> 白鬚神社 (滋賀 総本社)
            ("Q705151", ["大鳥神社"]),                             # Otori/Yamato-Takeru -> 大鳥大社
        ],
    },
    # shinwa-otaku.com 総本社まとめ (~57 head->branch mappings) — the niche-network tail.
    # Skipped as unresolvable/ambiguous: 雷電 (Itakura head no QID hit), 由加 (two Okayama
    # candidates), 月讀 / 伊豆山 (ambiguous heads), 鷲->大鳥 (official site makes no claim).
    "shinwa_otaku": {
        "url": "https://shinwa-otaku.com/jinja/sohonsha/",
        "out": "bunrei_shinwa_otaku.txt",
        "networks": [
            ("Q11355207", ["三峯神社", "三峰神社"]),               # Mitsumine -> 三峯神社 (秩父)
            ("Q11443949", ["三吉神社"]),                           # Miyoshi -> 太平山三吉神社 (秋田)
            ("Q11572627", ["久伊豆神社"]),                         # Hisaizu -> 玉敷神社 (埼玉)
            ("Q11620955", ["御歳神社", "大歳神社"]),               # Mitoshi/Otoshi -> 葛城御歳神社
            ("Q11673295", ["鴨神社"]),                             # Kamo(Katsuragi) -> 高鴨神社
            ("Q11491171", ["綿津見神社", "海神社"]),               # Watatsumi -> 志賀海神社
            ("Q133753",   ["鹽竈神社", "塩竈神社", "塩釜神社"]),   # Shiogama -> 鹽竈神社 (宮城)
            ("Q11662833", ["青麻神社", "三光神社"]),               # Aoso/Sanko -> 青麻神社 (仙台)
            ("Q3317296",  ["宮地嶽神社"]),                         # Miyajidake -> 宮地嶽神社 (福津)
            ("Q11620885", ["一言主神社"]),                         # Hitokotonushi -> 葛城一言主神社
            ("Q11575046", ["産泰神社"]),                           # Santai -> 産泰神社 (前橋)
            ("Q11572731", ["玉祖神社"]),                           # Tamanooya -> 玉祖神社 (防府)
            ("Q705154",   ["丹生神社"]),                           # Niu -> 丹生都比売神社
        ],
    },
    # dic.nicovideo.jp 神社の系列 (via archive.org; live page 403s bots) — adds Suitengu, Tsushima.
    "nicovideo": {
        "url": "https://dic.nicovideo.jp/a/%E7%A5%9E%E7%A4%BE%E3%81%AE%E7%B3%BB%E5%88%97",
        "out": "bunrei_nicovideo.txt",
        "networks": [
            ("Q3200625", ["水天宮"]),                              # Suitengu -> 久留米水天宮
            ("Q705136",  ["津島神社", "津嶋神社"]),                # Tsushima -> 津島神社 (愛知)
        ],
    },
}


def all_shrines():
    """[(qid, ja_label)] for every Wikidata Shinto shrine (P31=Q845945) with a ja label."""
    qy = ('SELECT ?item ?ja WHERE { ?item wdt:P31 wd:Q845945 ; rdfs:label ?ja . '
          'FILTER(LANG(?ja)="ja") }')
    url = WDQS + "?" + urllib.parse.urlencode({"query": qy, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/sparql-results+json"})
    wd_pace(SPARQL_INTERVAL)
    with urllib.request.urlopen(req, timeout=180) as r:
        rows = json.load(r)["results"]["bindings"]
    return [(x["item"]["value"].rsplit("/", 1)[-1], x["ja"]["value"]) for x in rows]


def head_for(ja_label, networks):
    for head_qid, suffixes in networks:
        if any(ja_label.endswith(s) for s in suffixes):
            return head_qid
    return None


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", default="jinja_kikou", choices=sorted(SOURCES),
                    help="Which online source to derive from.")
    ap.add_argument("--stats", action="store_true", help="Print counts, write nothing.")
    args = ap.parse_args()

    # Before the SPARQL and before the output file is opened: main() writes with
    # "w", so returning later would truncate bunrei.txt and lose staged lines the
    # drip has not delivered yet.
    if sunset_reached():
        print(f"time-boxed: this suffix-based generator stopped on {SUNSET} "
              f"(queue A0b). The per-shrine Opus pass is the accurate layer. "
              f"Existing output left untouched; nothing regenerated.")
        return

    cfg = SOURCES[args.source]
    networks, url, OUTPUT = cfg["networks"], cfg["url"], os.path.join(HERE, cfg["out"])
    head_qids = {n[0] for n in networks}

    shrines = all_shrines()
    lines, per_head = [], {}
    for qid, ja in shrines:
        if qid in head_qids:          # never make a head its own branch
            continue
        head = head_for(ja, networks)
        if not head:
            continue
        lines.append(f'{qid}|P612|{head}|P1013|{Q_BUNREI}|S854|"{url}"')
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
