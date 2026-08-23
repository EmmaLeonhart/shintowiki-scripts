#!/usr/bin/env python3
"""
fetch_articles.py
=================
Write one plain-text file per shrine into `_agent_input/<set>/<title>.txt` — the
input the reading agents consume. The set is a **ja.wikipedia category, direct
members only** (`Category:別表神社`, `Category:神宮125社`); sub-categories are
never descended into (CLAUDE.md).

The original inputs were fetched ad hoc in an interrupted session with no script
committed, which meant the method could not be inspected or repeated. This
reproduces them exactly, including the two header lines the agents see:

    ARTICLE TITLE: 瀧原竝宮
    WIKIDATA: (no item)

    <full plain-text article>

**Full text, not the lead and not a keyword window.** The lineage sentence sits
anywhere in 由緒 / 歴史 / 創建 / 起源 and is usually not phrased with 分霊 or 勧請,
which is why extraction has to be a read rather than a match.

The WIKIDATA header reports the article's own item and is informational; the
authoritative per-shrine item comes from `build_subject_map.py`, which does not
follow redirects.

Usage: python lineage/fetch_articles.py --category 別表神社 --set beppyo_all
"""
import argparse
import io
import json
import os
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
API = 'https://ja.wikipedia.org/w/api.php'
THROTTLE = 0.4


def get(params):
    params = dict(params, format='json', formatversion='2')
    req = urllib.request.Request(
        API + '?' + urllib.parse.urlencode(params),
        headers={'User-Agent': WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def members(category):
    """Direct ns-0 members. cmnamespace=0 — sub-categories are not descended."""
    out, cont = [], {}
    while True:
        data = get(dict({'action': 'query', 'list': 'categorymembers',
                         'cmtitle': f'Category:{category}', 'cmnamespace': '0',
                         'cmlimit': '500'}, **cont))
        out += [m['title'] for m in data['query']['categorymembers']]
        if 'continue' not in data:
            return out
        cont = data['continue']
        time.sleep(THROTTLE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--category', required=True)
    ap.add_argument('--set', dest='setname', required=True)
    args = ap.parse_args()

    outdir = os.path.join(ROOT, '_agent_input', args.setname)
    os.makedirs(outdir, exist_ok=True)
    titles = members(args.category)
    print(f'{len(titles)} direct ns-0 members of Category:{args.category}')

    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        data = get({'action': 'query', 'prop': 'extracts|pageprops',
                    'explaintext': '1', 'titles': '|'.join(batch)})
        for page in data.get('query', {}).get('pages', []) or []:
            text = page.get('extract') or ''
            if not text:
                continue
            qid = (page.get('pageprops') or {}).get('wikibase_item') or '(no item)'
            safe = page['title'].replace('/', '／')
            with open(os.path.join(outdir, safe + '.txt'), 'w',
                      encoding='utf-8', newline='\n') as fh:
                fh.write(f'ARTICLE TITLE: {page["title"]}\nWIKIDATA: {qid}\n\n{text}\n')
        print(f'  {min(i + 20, len(titles))}/{len(titles)}')
        time.sleep(THROTTLE)
    print(f'written to _agent_input/{args.setname}/')


if __name__ == '__main__':
    main()
