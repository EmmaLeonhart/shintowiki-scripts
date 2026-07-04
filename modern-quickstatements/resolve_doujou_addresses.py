#!/usr/bin/env python3
"""
resolve_doujou_addresses.py
============================
Resolver for the 同上 address bug (queue.md 2026-07-04).

The original Shikinaisha import copied 所在地 cells from the per-district
jawiki list templates verbatim — including 同上 ("same as above"), which
is a table shorthand, not an address. ~51 Wikidata items carry
``P6375 = "同上"@ja`` with no reference.

This script:
 1. Fetches every per-district table template transcluded by a 国-level
    式内社一覧 article (default: 出雲国の式内社一覧).
 2. Walks each table's rows carrying the last real 所在地 downward, so
    every 同上 cell resolves to the nearest preceding real address —
    exactly the semantics the table intends.
 3. Fetches all Wikidata items with P6375="同上"@ja and matches them to
    rows by ja label (exact cell match, 合祀：-prefix tolerated).
 4. Writes ``doujou_resolution.json``: per QID the resolved address and
    the source article URL — the input for the corrective-edit generator
    (which drips ``-Q|P6375`` removals + referenced re-adds through
    direct_daily_edits.py; see queue.md).

Read-only: no wiki writes. Run it, eyeball the JSON, then let the
generator leg consume it.
"""

import io
import json
import re
import sys

import requests

UA = {"User-Agent": "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"}
JA_API = "https://ja.wikipedia.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"

LIST_ARTICLE = "出雲国の式内社一覧"

# A cell is a real address only when it STARTS with one of the 47
# prefectures. A [都道府県] character test alone false-positives on
# shrine names (波夜都武自和気 contains 都).
PREFECTURES = (
    "北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 "
    "埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 "
    "岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 "
    "鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 "
    "佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県"
).split()
PREF_RE = re.compile("^(" + "|".join(PREFECTURES) + ")")

# Hand-resolved items the row matcher can't safely claim automatically
# (kanji-variant / cross-district name collisions). Each verified
# 2026-07-04 against the 意宇郡 table revision current at import time
# (2025-04-29) AND the item's own P131 (all three: Q11073594 意宇郡):
#   Q135040786 同社坐韓国伊大弖神社 — item already carries the correct
#     claim 揖屋2229 beside 同上; override lets the generator emit the
#     phase-2 removal.
#   Q135070085 (論)剣神社 row → 島根県松江市八雲町日吉10.
#   Q135070108 (論)佐久多神社 — both its rows carry 上来待551.
MANUAL_OVERRIDES = {
    "Q135040786": "島根県八束郡東出雲町揖屋2229",
    "Q135070085": "島根県松江市八雲町日吉10",
    "Q135070108": "島根県松江市宍道町上来待551",
}


def normalize_kanji(s: str) -> str:
    """Kanji variants seen between item labels and list rows."""
    return s.replace("劔", "剣").replace("劍", "剣").replace("嶋", "島")


def label_matches_names(label: str, names: list) -> bool:
    """True when a Wikidata ja label denotes one of a row's name cells.
    Tolerates 合祀：/同社 prefixes and kanji variants; allows the label as
    a suffix of the cell (rows often carry a longer ceremonial form) but
    only for labels >3 chars so 剣神社-sized names can't cross-match."""
    bare = label.replace("合祀：", "")
    b = normalize_kanji(bare)
    for n in names:
        n_bare = normalize_kanji(n.replace("同社", "").replace("合祀：", ""))
        if normalize_kanji(label) == normalize_kanji(n) or b == n_bare:
            return True
        if len(b) > 3 and (normalize_kanji(n).endswith(b) or n_bare.endswith(b)):
            return True
    return False


def fetch_wikitext(title: str) -> str:
    r = requests.get(JA_API, params={
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "content", "rvslots": "main",
        "format": "json", "formatversion": 2,
    }, headers=UA, timeout=60)
    r.raise_for_status()
    page = r.json()["query"]["pages"][0]
    if "revisions" not in page:
        return ""
    return page["revisions"][0]["slots"]["main"]["content"]


def strip_markup(cell: str) -> str:
    """Plain text of a table cell: unlink [[a|b]]→b, [[a]]→a, drop
    bold/attrs/refs/comments."""
    cell = re.sub(r"<!--.*?-->", "", cell, flags=re.S)
    cell = re.sub(r"<ref[^>]*>.*?</ref>", "", cell, flags=re.S)
    cell = re.sub(r"<ref[^>]*/>", "", cell)
    cell = re.sub(r"\[\[([^|\]]*)\|([^\]]*)\]\]", r"\2", cell)
    cell = re.sub(r"\[\[([^\]]*)\]\]", r"\1", cell)
    cell = re.sub(r"\[https?://\S+[^\]]*\]", "", cell)
    cell = cell.replace("'''", "").replace("''", "")
    # attribute prefix like `colspan=2 style=...|value`
    if "|" in cell and "=" in cell.split("|", 1)[0]:
        cell = cell.split("|", 1)[1]
    cell = re.sub(r"<[^>]+>", "", cell)
    # A ||| typo (seen in 出雲郡: `|||同上`) leaves a leading pipe on the cell.
    return cell.strip().lstrip("|").strip()


def parse_rows(wikitext: str):
    """Yield per-row lists of stripped cell texts from a district table
    template. Rows are separated by |- ; cells by || or leading |."""
    body = re.sub(r"<noinclude>.*?</noinclude>", "", wikitext, flags=re.S)
    for raw_row in re.split(r"\n\|-", body):
        # split into cells: newline-| or ||
        cells = []
        for chunk in re.split(r"\n\|", raw_row):
            cells.extend(chunk.split("||"))
        cells = [strip_markup(c) for c in cells]
        cells = [c for c in cells if c != ""]
        if cells:
            yield cells


def resolve_district(template_title: str):
    """Return (rows, resolutions): resolutions maps every name cell in a
    同上 row to the address carried down from the nearest real one."""
    text = fetch_wikitext(template_title)
    resolutions = []  # (row_names, resolved_address)
    last_address = None
    last_names: list = []
    for cells in parse_rows(text):
        has_doujou = any(c == "同上" for c in cells)
        real_addr = next((c for c in cells if PREF_RE.match(c)), None)
        if real_addr:
            last_address = real_addr
        names = [c for c in cells if re.search(r"神社|大社|神宮|社$", c)]
        if has_doujou and last_address:
            # rowspan continuation rows carry no name cell of their own —
            # the name spans from the previous row.
            resolutions.append({"names": names or last_names,
                                "address": last_address,
                                "template": template_title})
        if names:
            last_names = names
    return resolutions


def main():
    # In main, not at import: tests import this module under pytest capture.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    list_text = fetch_wikitext(LIST_ARTICLE)
    templates = re.findall(r"\{\{(出雲国[^{}]*?の式内社一覧)\}\}", list_text)
    print(f"District templates: {len(templates)}")

    all_res = []
    for t in templates:
        res = resolve_district(f"Template:{t}")
        print(f"  {t}: {len(res)} 同上 rows resolved")
        all_res.extend(res)

    # Wikidata items with the bug
    q = 'SELECT ?item ?jaLabel WHERE { ?item wdt:P6375 "同上"@ja . ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel)="ja") }'
    r = requests.post(SPARQL, data={"query": q, "format": "json"}, headers=UA, timeout=120)
    r.raise_for_status()
    items = {b["item"]["value"].rsplit("/", 1)[-1]: b["jaLabel"]["value"]
             for b in r.json()["results"]["bindings"]}
    print(f"Wikidata items with P6375=同上@ja: {len(items)}")

    out, unmatched = {}, []
    for qid, label in sorted(items.items()):
        if qid in MANUAL_OVERRIDES:
            out[qid] = {
                "label": label,
                "resolved_address": MANUAL_OVERRIDES[qid],
                "source_article": LIST_ARTICLE,
                "source_template": "MANUAL_OVERRIDES (see comment)",
                "source_url": f"https://ja.wikipedia.org/wiki/{LIST_ARTICLE}",
            }
            continue
        hit = next((r_ for r_ in all_res
                    if label_matches_names(label, r_["names"])), None)
        if hit:
            out[qid] = {
                "label": label,
                "resolved_address": hit["address"],
                "source_article": LIST_ARTICLE,
                "source_template": hit["template"],
                "source_url": f"https://ja.wikipedia.org/wiki/{LIST_ARTICLE}",
            }
        else:
            unmatched.append({"qid": qid, "label": label})

    result = {"resolved": out, "unmatched": unmatched,
              "list_article": LIST_ARTICLE}
    with open("doujou_resolution.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"Resolved {len(out)}/{len(items)}; unmatched {len(unmatched)} -> doujou_resolution.json")
    for u in unmatched[:10]:
        print("  unmatched:", u["qid"], u["label"])


if __name__ == "__main__":
    main()
