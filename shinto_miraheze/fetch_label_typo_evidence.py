#!/usr/bin/env python3
"""
fetch_label_typo_evidence.py
============================
For the label_typo_review work-files still pending, fetch the evidence needed to
settle the ones where the English label and the P1814 kana disagree about the
READING itself — 潮江 うしおえ vs "Shioe", 敬満 きょうまん vs "Keiman", 鵜鳥 うねどり
vs "Unotori". Both sides are real readings of the kanji; only the individual
shrine decides. Emma 2026-08-04: research each, then decide.

The evidence is the shrine's OWN ja.wikipedia lead, reached through its Wikidata
item's jawiki sitelink rather than by guessing a title from the ja label — the
labels here include 八幡神社 and 秋葉神社, which name hundreds of shrines each.

Writes `shinto_miraheze/local_answers/_label_typo_evidence.tsv`:

    qid, ja label, kana, en label, jawiki title, the reading its lead gives, the lead

An item with no jawiki sitelink gets an empty title and lead; that is a finding,
not a failure — it means the article cannot settle it and something else has to.

Read-only against Wikidata + ja.wikipedia, batched and throttled. No SPARQL.

Usage: python shinto_miraheze/fetch_label_typo_evidence.py
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
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WORKDIR = os.path.join(ROOT, 'label_typo_review')
OUT = os.path.join(SCRIPT_DIR, 'local_answers', '_label_typo_evidence.tsv')
WD_API = 'https://www.wikidata.org/w/api.php'
JA_API = 'https://ja.wikipedia.org/w/api.php'
THROTTLE = 0.5

META_RE = re.compile(r'<!-- JA: (.*?) \| KANA: (.*?) \| EN_LABEL: (.*?) \| '
                     r'KANA_ROMANIZED: (.*?) -->')
KANA = r'[ぁ-ゖァ-ヺー]'


def get(api, params):
    params = dict(params, format='json', formatversion='2')
    req = urllib.request.Request(
        api + '?' + urllib.parse.urlencode(params),
        headers={'User-Agent': WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def sitelinks(qids):
    out = {}
    qids = list(qids)
    for i in range(0, len(qids), 50):
        data = get(WD_API, {'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 50]),
                            'props': 'sitelinks', 'sitefilter': 'jawiki'})
        for qid, ent in (data.get('entities') or {}).items():
            title = (ent.get('sitelinks') or {}).get('jawiki', {}).get('title')
            if title:
                out[qid] = title
        time.sleep(THROTTLE)
    return out


def leads(titles):
    out = {}
    titles = list(titles)
    for i in range(0, len(titles), 20):
        data = get(JA_API, {'action': 'query', 'prop': 'extracts', 'exintro': '1',
                            'explaintext': '1', 'titles': '|'.join(titles[i:i + 20])})
        for page in data.get('query', {}).get('pages', []) or []:
            if not page.get('missing'):
                out[page['title']] = (page.get('extract') or '').strip()
        time.sleep(THROTTLE)
        print(f'  leads {min(i + 20, len(titles))}/{len(titles)}')
    return out


def lead_reading(title, lead):
    """The reading the lead itself opens with, disambiguator stripped."""
    bare = re.sub(r'\s*\([^()]*\)$', '', title)
    m = re.search(re.escape(bare) + r"'*\s*[（(]([^（）()]*)[）)]", lead)
    if not m or m.start() != 0:
        return ''
    inner = m.group(1).split('、')[0].split(',')[0].strip()
    return inner if re.fullmatch(KANA + r'+', inner or '') else ''


def main():
    rows = []
    for name in sorted(os.listdir(WORKDIR)):
        if not name.endswith('.wiki'):
            continue
        body = open(os.path.join(WORKDIR, name), encoding='utf-8').read()
        m = META_RE.search(body)
        if m:
            rows.append((name[:-5],) + m.groups())
    print(f'{len(rows)} pending work-files')

    links = sitelinks(r[0] for r in rows)
    text = leads(sorted(set(links.values())))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('qid\tja\tkana\ten_label\tjawiki\tlead_reading\tlead\n')
        for qid, ja, kana, en, _rom in rows:
            title = links.get(qid, '')
            lead = text.get(title, '')
            fh.write('\t'.join([
                qid, ja, kana, en, title, lead_reading(title, lead),
                lead.replace('\t', ' ').replace('\n', ' ')[:600]]) + '\n')

    nolink = sum(1 for r in rows if r[0] not in links)
    print(f'{len(rows)} rows -> {OUT} ({nolink} with no jawiki sitelink)')


if __name__ == '__main__':
    main()
