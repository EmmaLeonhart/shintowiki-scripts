#!/usr/bin/env python3
"""
parse_onkamui_bunrei.py — maximalist parse of the onkamui Rakuten blog's
総本宮・総本社と分霊社 post (queue: bunrei #11, Emma approved 2026-07-07 on
[[Open questions]]: maximalist -> middle path -> easy path -> give up).

The post is ONE page listing ~44 shrine networks. Per network:
    <network heading line>
    (photo caption lines)
    総本宮 / 総本社
    <rank>：<head shrine name>[　未]        (one or more)
    祭神 ... (skipped)
    分霊社
    <rank line>                             (官幣大社/県社/郷社/村社/社格不明...)
    <prefecture><place>：<branch name>[ / <alt name>]   (branch entries)
    <city>：<branch name>　<commentary>     (photo-post commentary — skipped:
                                             no prefecture prefix)

Value over the suffix-method sources: branches are NAMED, so we capture
branches whose names do not match the network suffix (新舘神社 under 八幡宮,
二俣神社, 西叶神社, 秋保神社 under 諏訪...).

Matching (never guess — Emma's rail):
  * head names resolve via HEAD_QIDS (hand-verified, seeded from the existing
    bunrei SOURCES) — unresolved heads are reported and their networks skipped;
  * branch names match Wikidata ja labels exactly, or as 「name (place)」;
    only UNIQUE matches emit; ambiguous/missing are counted + reported.

Output: bunrei_onkamui.txt — atomic QS lines
    <branch>|P612|<head>|P1013|Q195793|S854|"<post url>"
Report: onkamui_parse_report.txt (networks, match rates, unresolved heads).
"""
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

from shinto_miraheze.ua_for import ua_for

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "bunrei_onkamui.txt")
REPORT = os.path.join(HERE, "onkamui_parse_report.txt")
URL = "https://plaza.rakuten.co.jp/onkamui/diary/202409290000/"
WDQS = "https://query-main.wikidata.org/sparql"
# UA removed 2026-08-19: the request sites now resolve the agent from the URL via
# ua_for(), so this hand-built literal was dead and could only drift. Was: UA = f"shintowiki-bunrei/1.0 (https://shinto.miraheze.org; {contact('wikidata')})"
Q_BUNREI = "Q195793"

PREFS = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]
RANKS = ["官幣大社", "官幣中社", "官幣小社", "国幣大社", "国幣中社", "国幣小社",
         "別格官幣社", "府県社", "県社", "府社", "郷社", "村社", "無格社",
         "社格不明", "別表神社", "神宮"]
RANK_LINE = re.compile("^(" + "|".join(RANKS) + ")$")
HEAD_LINE = re.compile("^(" + "|".join(RANKS) + ")：(.+?)(　未)?$")
BRANCH_LINE = re.compile("^(" + "|".join(PREFS) + ")([^：]{0,14})：(.+)$")

# Head-shrine QIDs. Every entry VERIFIED against Wikidata 2026-07-07 (either
# copied from the existing bunrei SOURCES config or resolved via
# wbsearchentities + ja-label check this session — an earlier from-memory
# draft of this table was 14/17 wrong; do not add unverified QIDs). A network
# whose heads don't all resolve to ONE item is skipped and reported.
HEAD_QIDS = {
    "伊勢神宮": "Q687168",
    "廣田神社": "Q1466105",          # 西宮の官幣大社 (Hyōgo)
    "宇佐神宮": "Q715632",
    "熊野本宮大社": "Q705035", "熊野速玉大社": "Q335618", "熊野那智大社": "Q710359",
    "伏見稲荷大社": "Q714828",
    "多賀大社": "Q402091",
    "愛宕神社": "Q713021",
    "龍田大社": "Q246455",
    "貴船神社": "Q276779",
    "西宮神社": "Q705297",
    "南宮大社": "Q704967",
    "雷電神社": "Q11660224", "板倉雷電神社": "Q11660224",   # 板倉町
    "宗像大社": "Q704962", "厳島神社": "Q191763", "嚴島神社": "Q191763",
    "住吉大社": "Q705949",
    "志賀海神社": "Q11491171",
    "春日大社": "Q714559",
    "鹿島神宮": "Q706499",
    "香取神宮": "Q372380",
    "鹽竈神社": "Q133753", "塩竈神社": "Q133753",
    "白山比咩神社": "Q704702",
    "高鴨神社": "Q11673295",
    "氣比神宮": "Q11129346", "気比神宮": "Q11129346",
    "八坂神社": "Q692714",
    "大神神社": "Q705542",           # 奈良 三輪
    "大杉神社": "Q11435950",
    "金刀比羅宮": "Q94760",
    "氣多大社": "Q11129340", "気多大社": "Q11129340",
    "諏訪大社": "Q218813",
    "加太淡嶋神社": "Q7007362", "淡嶋神社": "Q7007362",
    "大山祇神社": "Q703904",         # 大三島
    "富士山本宮浅間大社": "Q653180", "浅間大社": "Q653180",
    "日吉大社": "Q656451",
    "松尾大社": "Q710302",
    "橿原神宮": "Q710333",
    "太宰府天満宮": "Q710786", "北野天満宮": "Q662176",
    "日光東照宮": "Q696641", "東照宮": "Q696641",
    "太平山三吉神社": "Q11443949", "大平山三吉神社": "Q11443949",  # blog typo
    "三峯神社": "Q11355207",
    "十和田神社": "Q106852429",
    "古峯神社": "Q106697652",        # 鹿沼 (栃木)
    "酒列磯前神社": "Q11644289",
    "大洗磯前神社": "Q11437230",
}


def head_qid(name):
    """Resolve a 総本社 line's shrine name, tolerating parentheticals and
    sub-shrine suffixes (宗像大社 辺津宮 / 賀茂別雷神社（上賀茂神社） / 諏訪大社 上社)."""
    name = name.strip()
    for cand in (name,
                 re.sub(r"[（(].*?[)）]", "", name).strip(),
                 name.split(" ")[0].split("　")[0]):
        if cand in HEAD_QIDS:
            return HEAD_QIDS[cand]
    return None


def fetch(url=URL, cache=None):
    if cache and os.path.exists(cache):
        return open(cache, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(url, headers={"User-Agent": ua_for(url)})
    wd_pace(SPARQL_INTERVAL)
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status == 429:
            raise SystemExit("429 from rakuten — bailing.")
        html = r.read().decode("utf-8", errors="replace")
    if cache:
        open(cache, "w", encoding="utf-8", newline="\n").write(html)
    return html


def to_lines(html):
    start = html.find("神社は主に特定の神格")
    end = html.find("最終更新日", start)
    seg = html[start:end if end > 0 else len(html)]
    seg = re.sub(r"<br\s*/?>", "\n", seg)
    seg = re.sub(r"<script.*?</script>", "", seg, flags=re.S)
    seg = re.sub(r"<[^>]+>", "\n", seg)
    seg = seg.replace("​", "").replace("&nbsp;", " ")
    return [l.strip() for l in seg.split("\n") if l.strip()]


def parse(lines):
    """[{heading, heads:[name], branches:[(pref, place, name)]}]"""
    # section starts = indices of 総本宮/総本社 marker lines; heading = nearest
    # previous line that is not a caption directly attached to the marker.
    marks = [i for i, l in enumerate(lines) if l in ("総本宮", "総本社")]
    sections = []
    for mi, m in enumerate(marks):
        # walk back past captions: heading is the closest previous line that
        # either follows a branch/commentary line or is the very first line
        # after the previous section's content. Take the line 1-4 above the
        # marker that best looks like a heading (no ：, not rank, <= 40 chars).
        heading = None
        for j in range(m - 1, max(m - 5, -1), -1):
            l = lines[j]
            if "：" in l or RANK_LINE.match(l) or l in ("祭神", "分霊社"):
                break
            # skip prose/captions/the post title — keep walking
            if ("。" in l or len(l) > 28 or l == "総本宮・総本社と分霊社"
                    or re.search(r"(する|した|います|です|ます)$", l)):
                continue
            heading = l  # furthest qualifying line wins
        if heading is None:
            continue
        end = marks[mi + 1] if mi + 1 < len(marks) else len(lines)
        # a section may have TWO marker lines (rare); merge by heading
        if sections and sections[-1]["heading"] == heading:
            sec = sections[-1]
        else:
            sec = {"heading": heading, "heads": [], "branches": []}
            sections.append(sec)
        in_bunrei = False
        for l in lines[m + 1:end]:
            # The post's tail sections (磯前神社 onward) list 同名の神社 /
            # 同一の神格を祀る神社 — same-NAME or same-DEITY shrines the author
            # explicitly does NOT claim as bunrei (総本社と明言しているわけでは無い).
            # Those must never become P612 edges.
            if l.startswith("同名の神社") or l.startswith("同一の神格"):
                sec["tainted"] = True
            if l == "分霊社":
                in_bunrei = True
                continue
            hm = HEAD_LINE.match(l)
            if hm and not in_bunrei:
                sec["heads"].append(hm.group(2).strip())
                continue
            bm = BRANCH_LINE.match(l)
            if bm and in_bunrei:
                pref, place, names = bm.groups()
                names = re.split(r"\s*/\s*", names.split("　")[0])
                for n in names:
                    n = n.strip()
                    if n:
                        sec["branches"].append((pref, place, n))
    # drop next-section headings that leaked as caption walks (no heads found)
    return [s for s in sections if s["heads"]]


def all_shrines():
    """[(qid, ja_label, pref_ja_label_or_None)] for every Wikidata Shinto shrine."""
    qy = ('SELECT ?item ?ja ?prefLabel WHERE { '
          '?item wdt:P31 wd:Q845945 ; rdfs:label ?ja . FILTER(LANG(?ja)="ja") '
          'OPTIONAL { ?item wdt:P131* ?pref . ?pref wdt:P31 wd:Q50337 ; '
          'rdfs:label ?prefLabel . FILTER(LANG(?prefLabel)="ja") } }')
    url = WDQS + "?" + urllib.parse.urlencode({"query": qy, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": ua_for(url), "Accept": "application/sparql-results+json"})
    wd_pace(SPARQL_INTERVAL)
    with urllib.request.urlopen(req, timeout=300) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    return [(x["item"]["value"].rsplit("/", 1)[-1], x["ja"]["value"],
             x.get("prefLabel", {}).get("value")) for x in rows]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="local cached HTML instead of fetching")
    args = ap.parse_args()

    lines = to_lines(fetch(cache=args.html) if args.html else fetch())
    sections = parse(lines)
    print(f"{len(sections)} networks parsed")

    # ja-label index carrying prefecture(s) for disambiguation
    by_label = {}
    for qid, ja, pref in all_shrines():
        by_label.setdefault(ja, {}).setdefault(qid, set()).add(pref)
    def match(pref, place, name):
        # exact label, then 「name (place)」 disambiguated label forms;
        # ambiguity resolves if exactly ONE candidate sits in the entry's prefecture
        for cand in (name, f"{name} ({place})", f"{name} ({pref}{place})",
                     f"{name}（{place}）"):
            hits = by_label.get(cand, {})
            if len(hits) == 1:
                return next(iter(hits))
            if len(hits) > 1:
                in_pref = [q for q, prefs in hits.items() if pref in prefs]
                if len(in_pref) == 1:
                    return in_pref[0]
                return "AMBIG"
        return None

    qs, matched, ambig, missing = [], 0, 0, 0
    rep = []
    for sec in sections:
        if sec.get("tainted"):
            rep.append(f"SAME-NAME/SAME-DEITY section {sec['heading']!r} — not bunrei, skipped "
                       f"({len(sec['branches'])} entries incl. any mixed-in 分霊社 lines)")
            continue
        resolved = {q for q in (head_qid(h) for h in sec["heads"]) if q}
        if not resolved:
            rep.append(f"UNRESOLVED HEAD — network {sec['heading']!r}: heads={sec['heads']}")
            continue
        if len(resolved) > 1:
            rep.append(f"MULTI-HEAD network {sec['heading']!r} resolves to {sorted(resolved)} "
                       f"— skipped (branch->which-head is not decidable from the page)")
            continue
        head = next(iter(resolved))
        n_m = n_a = n_x = 0
        for pref, place, name in sec["branches"]:
            q = match(pref, place, name)
            if q == "AMBIG":
                ambig += 1; n_a += 1
            elif q:
                matched += 1; n_m += 1
                if q != head:
                    qs.append(f'{q}|P612|{head}|P1013|{Q_BUNREI}|S854|"{URL}"')
            else:
                missing += 1; n_x += 1
        rep.append(f"{sec['heading']}: head={head} branches={len(sec['branches'])} "
                   f"matched={n_m} ambiguous={n_a} not-on-wikidata={n_x}")

    qs = sorted(set(qs))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(qs) + ("\n" if qs else ""))
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rep) + "\n")
    print(f"branches: matched={matched} ambiguous={ambig} not-on-wikidata={missing}")
    print(f"{len(qs)} QS lines -> {OUT}")
    for r in rep:
        print(" ", r)


if __name__ == "__main__":
    main()
