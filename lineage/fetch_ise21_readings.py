#!/usr/bin/env python3
"""
fetch_ise21_readings.py
=======================
The 21 神宮125社 shrines that need a Wikidata item are jawiki REDIRECTS into a
neighbouring shrine's article, so there is no lead sentence of their own to read
a kana reading out of. The reading is nearly always in the PARENT article
anyway — either in the section that the redirect points at, or in a table row /
bolded run naming the sub-shrine.

This fetches each parent article once and pulls every `名前（かな）` pairing it can
find for the 21 titles. It writes `lineage/_ise21_readings.json`:

    {"井中神社": {"kana": "いなかじんじゃ", "how": "paren-after-name", "context": "..."}}

`how` is recorded so a human can see WHERE a reading came from; `null` kana means
the parent article does not give one and the English label has to come from
somewhere else (or be left off).

Read-only against ja.wikipedia, throttled. Usage: python lineage/fetch_ise21_readings.py
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from shinto_miraheze.user_agent import USER_AGENT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

JA_API = 'https://ja.wikipedia.org/w/api.php'
OUT = os.path.join(SCRIPT_DIR, '_ise21_readings.json')
THROTTLE = 0.5

KANA = r'[ぁ-ゖァ-ヺー・\s]'


def get(params):
    params = dict(params, format='json', formatversion='2')
    req = urllib.request.Request(
        JA_API + '?' + urllib.parse.urlencode(params),
        headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def wikitext(title):
    data = get({'action': 'query', 'prop': 'revisions', 'rvprop': 'content',
                'rvslots': 'main', 'titles': title, 'redirects': 1})
    pages = data.get('query', {}).get('pages') or []
    if not pages or pages[0].get('missing'):
        return ''
    return pages[0]['revisions'][0]['slots']['main']['content']


def find_reading(name, text):
    """Every way the parent article might spell out this shrine's reading."""
    # The name is nearly always bolded where it is first defined
    # (`'''井中神社'''（いなかじんじゃ）`), so the closing wiki-bold sits BETWEEN the
    # name and its parenthesised reading. Allowing `'*` here is what makes the
    # common case match at all — without it only 6 of the 21 were found.
    stem = re.escape(name) + r"'*"
    bare = (re.escape(name[:-2]) + r"'*") if name.endswith('神社') else None
    pats = [
        # 井中神社（いなかじんじゃ）  /  '''井中神社'''（いなかじんじゃ）
        ("paren-after-name", rf"{stem}\s*[（(]\s*({KANA}+?)\s*[）)]"),
        # {{ruby|井中神社|いなかじんじゃ}}
        ("ruby-template", rf"\{{\{{ruby\|{stem}\|({KANA}+?)\}}\}}"),
        # table row: | 井中神社 || いなかじんじゃ
        ("table-cell", rf"{stem}\s*\|\|\s*({KANA}+?)\s*(?:\|\||\n)"),
    ]
    if bare:
        # 井中（いなか）神社 — the paren sits between stem and 神社
        pats.append(("paren-mid-name", rf"{bare}\s*[（(]\s*({KANA}+?)\s*[）)]\s*神社"))
    for how, pat in pats:
        m = re.search(pat, text)
        if not m:
            continue
        kana = m.group(1).strip()
        if len(kana) < 2:
            continue
        start = max(0, m.start() - 60)
        return {'kana': kana, 'how': how,
                'context': text[start:m.end() + 40].replace('\n', ' ')}
    return {'kana': None, 'how': None, 'context': None}


def main():
    targets = json.load(open(os.path.join(SCRIPT_DIR, '_ise21.json'), encoding='utf-8'))
    cache, out = {}, {}
    for t in targets:
        parent = t['redirect'].split('#')[0].strip()
        if parent not in cache:
            cache[parent] = wikitext(parent)
            time.sleep(THROTTLE)
        r = find_reading(t['title'], cache[parent])
        # A section redirect names the sub-shrine as a heading; the reading may
        # also sit in the shrine's OWN would-be lead further down the section.
        out[t['title']] = dict(r, parent=parent)
        print(f"{t['title']:<12} {r['kana'] or '—':<20} {r['how'] or 'NOT FOUND'}  ({parent})")

    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    found = sum(1 for v in out.values() if v['kana'])
    print(f"\n{found}/{len(out)} readings found -> {OUT}")


if __name__ == '__main__':
    main()
