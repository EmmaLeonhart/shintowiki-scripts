#!/usr/bin/env python3
"""
fetch_jingu125_kana.py
======================
The 神宮125社 half of A0's bucket (a): which of these shrines' items still have no
top-level P1814, and what their jawiki lead says the reading is.

This does NOT query SPARQL. The 神宮125社 membership and every QID were already
resolved by `build_subject_map.py` from the ja.wikipedia category, and P1814 is
read with `wbgetentities` over the QIDs we already hold — two requests, not a
sweep. (CLAUDE.md: Wikidata is a destination, not a lookup service.)

It writes `lineage/_jingu125_kana.tsv`, one row per item with no P1814:

    QID <tab> title <tab> lead-sentence reading (or blank) <tab> the lead

The reading column is a REGEX candidate, not an answer. A0's design is that an
Opus read of the lead produces the kana, precisely because bold/furigana parsing
is fragile; this file is the input to that read, with the obvious case
pre-filled so the read is a check rather than a transcription. Nothing here
emits a QuickStatement — `collect_name_in_kana.py` does that.

Usage: python lineage/fetch_jingu125_kana.py
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
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

JA_API = 'https://ja.wikipedia.org/w/api.php'
WD_API = 'https://www.wikidata.org/w/api.php'
OUT = os.path.join(SCRIPT_DIR, '_jingu125_kana.tsv')
STAGED = os.path.join(ROOT, 'modern-quickstatements', 'name_in_kana.txt')
THROTTLE = 0.5

HIRAGANA_ONLY = re.compile(r'^[ぁ-ゖー\s]+$')


def get(api, params):
    params = dict(params, format='json', formatversion='2')
    req = urllib.request.Request(
        api + '?' + urllib.parse.urlencode(params),
        headers={'User-Agent': WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def items_missing_p1814(qids):
    """The subset with no top-level P1814, via wbgetentities (50 ids/request)."""
    missing = []
    qids = list(qids)
    for i in range(0, len(qids), 50):
        data = get(WD_API, {'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 50]),
                            'props': 'claims'})
        for qid, ent in (data.get('entities') or {}).items():
            if not (ent.get('claims') or {}).get('P1814'):
                missing.append(qid)
        time.sleep(THROTTLE)
    return missing


def leads(titles, follow_redirects=False):
    """title -> first paragraph of the article's plain text.

    With `follow_redirects` the result is keyed by the title ASKED FOR, not the
    article landed on — the point is to read a redirect's reading out of the
    article that absorbed it (神服織機殿神社 inside 機殿神社), which needs the
    mapping kept.
    """
    out = {}
    titles = list(titles)
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        params = {'action': 'query', 'prop': 'extracts',
                  'exintro': '1', 'explaintext': '1', 'titles': '|'.join(batch)}
        if follow_redirects:
            params['redirects'] = '1'
        data = get(JA_API, params)
        norm = {}
        for key in ('normalized', 'redirects'):
            for entry in data.get('query', {}).get(key, []) or []:
                norm[entry['from']] = entry['to']
        pages = {p['title']: (p.get('extract') or '').strip()
                 for p in data.get('query', {}).get('pages', []) or []
                 if not p.get('missing')}
        for asked in batch:
            seen, cur = set(), asked
            while cur in norm and cur not in seen:
                seen.add(cur)
                cur = norm[cur]
            if cur in pages:
                out[asked] = pages[cur]
        time.sleep(THROTTLE)
        print(f'  leads {min(i + 20, len(titles))}/{len(titles)}')
    return out


def candidate_reading(title, lead, anchored=True):
    """The `名前（かな）` the lead opens with, when it is unambiguously there.

    Deliberately strict on three counts. The parenthetical must be pure
    hiragana — katakana is A0's documented gate, signalling the ancient
    Engishiki reading rather than the modern one P1814 wants. The jawiki
    disambiguator is stripped first, since the lead writes 大山祇神社（…）, never
    大山祇神社 (伊勢市)（…）. And with `anchored`, the name must open the lead.

    That last rule is not fussiness. 機殿神社's article opens
    「神服織機殿神社（かんはとりはたどのじんじゃ）・神麻続機殿神社（…）は…」 — its
    own title is a SUBSTRING of the first name in its own lead, so an unanchored
    search hands the pair-item 神服織機殿神社's reading. 田上大水神社 / 大水神社 and
    河原神社 / 川原神社 are the same shape. Anchoring is what makes the difference
    between the article's subject and something merely named in it.
    """
    bare = re.sub(r'\s*\([^()]*\)$', '', title)
    m = re.search(re.escape(bare) + r'\s*[（(]([^（）()]*)[）)]', lead)
    if not m or (anchored and m.start() != 0):
        return ''
    inner = m.group(1).split('、')[0].split(',')[0].strip()
    return inner if inner and HIRAGANA_ONLY.match(inner) else ''


def main():
    subjects = json.load(open(os.path.join(SCRIPT_DIR, 'subject_qids.json'),
                              encoding='utf-8'))
    ise = sorted({f[:-4] for f in os.listdir(os.path.join(ROOT, '_agent_input', 'jingu125'))
                  if f.endswith('.txt')})
    have = {t: subjects['map'][t] for t in ise if subjects['map'].get(t)}
    print(f'{len(ise)} 神宮125社 articles, {len(have)} with an item')

    staged = set()
    if os.path.exists(STAGED):
        for line in open(STAGED, encoding='utf-8'):
            m = re.match(r'^(Q\d+)\|', line)
            if m:
                staged.add(m.group(1))

    missing = set(items_missing_p1814(have.values()))
    todo = {t: q for t, q in have.items() if q in missing and q not in staged}
    skipped = sum(1 for q in have.values() if q in missing and q in staged)
    print(f'{len(missing)} lack P1814; {skipped} of those already staged locally; '
          f'{len(todo)} to do')

    text = leads(todo)
    # A title with no lead of its own is a redirect whose item has no sitelink
    # (神服織機殿神社 / Q135186223, found by exact ja label). Its reading is in the
    # article that absorbed it, where it is one name among several — so the
    # anchored rule cannot apply and the search is unanchored on purpose.
    absorbed = [t for t in todo if not text.get(t)]
    if absorbed:
        print(f'{len(absorbed)} title(s) with no article of their own: '
              f'{", ".join(absorbed)}')
        text.update(leads(absorbed, follow_redirects=True))

    rows, prefilled = [], 0
    for title, qid in sorted(todo.items(), key=lambda kv: kv[0]):
        lead = text.get(title, '')
        kana = candidate_reading(title, lead, anchored=title not in absorbed)
        prefilled += bool(kana)
        rows.append((qid, title, kana, lead.replace('\t', ' ').replace('\n', ' ')))

    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('qid\ttitle\tcandidate_kana\tlead\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')
    print(f'{len(rows)} rows ({prefilled} with a candidate reading) -> {OUT}')


if __name__ == '__main__':
    main()
