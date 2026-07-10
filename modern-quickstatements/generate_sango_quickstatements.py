#!/usr/bin/env python3
"""
generate_sango_quickstatements.py
=================================
Import 山号 (sangō — the "mountain name" prefixed to a Japanese Buddhist temple's
formal name, e.g. 醫王山 in 醫王山薬師寺) from the jawiki `{{日本の寺院}}` infobox.

Emma 2026-07-10, choosing the model:

    "official name (P1448) with a qualifier object of statement has role (P3831)
    sangō (Q11058522). Simple thing."

    <temple>|P1448|ja:"<sangō>"|P3831|Q11058522|S4656|"<jawiki url>"

`Q11058522` was verified live: *sangō / 山号 — "a part of name of Buddhist temples
(in Japan)"*. `P1448` is monolingualtext, so the plain-text values fit without the
value needing its own item — which matters, because only ~7% of 山号 values are
wikilinked. Zero items on Wikidata currently carry `P1448` with this role, so every
line is new.

WHY THE PARSER IS FUSSY
-----------------------
山号 is filled on **92%** of temple articles, so every noise pattern is hit
thousands of times. Sampled from live jawiki:

    紫雲山                                     clean
    無量山{{sfn|江戸名所図会|1927|p=6}}            citation template
    瑞鹿山（ずいろくさん）                          parenthetical reading
    [[荒陵山]]（あらはかさん、こうりょうざん）          wikilink + reading
    [[大山 (神奈川県)|雨降山]]（あぶりさん）           PIPED wikilink: the display text is the sangō
    練月山<ref name="練馬の寺院">…</ref>          ref tag

So: strip citations, take a wikilink's *display* text, drop parenthetical readings,
and accept only a single run of kanji. Anything with a separator (、／/) after
cleaning names more than one thing and is refused rather than guessed at.

ADD-only. Items are not skipped by a "already has P1448" check, because a temple's
`P1448` is normally its *full* formal name (醫王山薬師寺); the sangō is a second,
role-qualified statement. The refusal is on the role: an item already carrying
`P1448` with `P3831 = Q11058522` is skipped.

Output: `sango_p1448.txt`, registered in `ATOMIC_FILES`.

    python generate_sango_quickstatements.py [--out FILE] [--limit N]
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request

from infobox_fields import field_pattern
from generate_souken_quickstatements import (
    embedded_titles,
    fetch_batch,
    strip_citations,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "sango_p1448.txt"
OUTPUT = os.path.join(HERE, OUTPUT_FILE)

WDQS = "https://query-main.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

TEMPLATE = "Template:日本の寺院"
SANGO = "Q11058522"        # sangō — "a part of name of Buddhist temples (in Japan)"
P_OFFICIAL_NAME = "P1448"  # monolingualtext
P_ROLE = "P3831"

_FIELD_RE = re.compile(field_pattern("山号"))

# [[Target|Display]] -> Display ; [[Target]] -> Target. The DISPLAY side is the
# sangō: 四天王寺 writes [[大山 (神奈川県)|雨降山]], where 大山 is the mountain article
# and 雨降山 is the temple's sangō.
_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]+)\]\]")

# A trailing (or embedded) kana reading: 瑞鹿山（ずいろくさん）
_READING = re.compile(r"[（(][^）)]*[）)]")

# `{{読み仮名|谷汲山|たにぐみさん}}` (華厳寺) wraps the sangō rather than annotating it,
# so it is UNWRAPPED to its first argument, not deleted like a citation would be.
_RUBY = re.compile(r"\{\{\s*(?:読み仮名|ruby|Ruby)\s*\|\s*([^|}]+)[^}]*\}\}")

# A line break separates two DIFFERENT sangō and must be seen before tags are
# stripped. 泉涌寺 writes `東山（とうざん）<br/>泉山（せんざん）`, and deleting the tag
# first fused them into "東山泉山". 大乗寺 became "東香山椙樹林金獅峯" the same way.
_BREAK = re.compile(r"<br\s*/?>|\n")

# The sangō itself: one run of kanji (with 々 and ヶ, which occur in place names).
_KANJI_RUN = re.compile(r"^[一-鿿々ヶ]{2,12}$")

# After cleaning, any of these means the field names more than one thing.
_SEPARATORS = re.compile(r"[、,／/・;；]")


def _clean_segment(s):
    s = _LINK.sub(r"\1", s)
    s = _READING.sub("", s)
    s = re.sub(r"<[^>]+>", "", s)      # any surviving tag
    s = s.replace("'''", "").replace("''", "")
    return s.strip()


def parse_sango(field):
    """The single sangō in the field, or None.

    A field naming more than one sangō — by `<br>`, by a separator, or by a
    trailing variant — is refused rather than guessed at. 泉涌寺 really does have
    two (東山 and 泉山); picking one would be inventing a fact.
    """
    if not field:
        return None
    s = strip_citations(field)
    s = _RUBY.sub(r"\1", s)

    segments = [seg for seg in (_clean_segment(p) for p in _BREAK.split(s)) if seg]
    if len(segments) != 1:
        return None

    s = segments[0]
    if not s or _SEPARATORS.search(s):
        return None
    return s if _KANJI_RUN.match(s) else None


def qs_line(qid, sango, url):
    return '{}|{}|ja:"{}"|{}|{}|S4656|"{}"'.format(
        qid, P_OFFICIAL_NAME, sango, P_ROLE, SANGO, url)


def items_with_sango_role():
    """QIDs already carrying P1448 qualified as a sangō — never re-add."""
    q = ("SELECT ?item WHERE { ?item p:%s ?st . ?st pq:%s wd:%s }"
         % (P_OFFICIAL_NAME, P_ROLE, SANGO))
    url = WDQS + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        if r.status == 429:
            raise SystemExit("429 from WDQS — bailing.")
        rows = json.load(r)["results"]["bindings"]
    return {b["item"]["value"].rsplit("/", 1)[-1] for b in rows}


def publish_to_site(path):
    """Mirror the batch into _site/ so the dashboard can link it."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    have = items_with_sango_role()
    print("{} items already carry P1448 with the sangō role".format(len(have)))

    titles = embedded_titles(TEMPLATE)
    if args.limit:
        titles = titles[:args.limit]
    print("{} jawiki temple articles".format(len(titles)))

    lines = []
    clean = no_field = unparsable = no_qid = already = 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            m = _FIELD_RE.search(text or "")
            if not m or not m.group(1).strip():
                no_field += 1
                continue
            sango = parse_sango(m.group(1))
            if sango is None:
                unparsable += 1
                continue
            if not qid:
                no_qid += 1
                continue
            if qid in have:
                already += 1
                continue
            url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(
                title.replace(" ", "_"))
            lines.append(qs_line(qid, sango, url))
            clean += 1
        time.sleep(0.3)

    lines = sorted(set(lines))
    assert all(not l.startswith("-") for l in lines), "sangō import is ADD-only"
    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")
    publish_to_site(path)

    print("clean={}, no-field={}, unparsable={}, no-QID={}, already-had={}".format(
        clean, no_field, unparsable, no_qid, already))
    print("{} sangō lines -> {}".format(len(lines), path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
