#!/usr/bin/env python3
"""
investigate_collisions.py
=========================
`_title2qid.json` maps each of the 444 shrine titles to a QID by asking
ja.wikipedia for `pageprops.wikibase_item` **with redirect resolution on**. That
is wrong for any title that is a redirect: it hands back the QID of the article
it lands on, so parent and child end up sharing one subject QID. 19 QIDs are
claimed by 42 of our titles.

An article is not a data item. A redirect can have its own Wikidata item, a
section can be the real subject of one, and an item can exist with no sitelink at
all. This script establishes, per colliding title:

  * is the jawiki title an ARTICLE, a REDIRECT (to what, to which #section), or
    absent — asked with `redirects=0` so nothing is silently followed;
  * does Wikidata hold an item whose jawiki SITELINK is exactly this title
    (`wbgetentities&sites=jawiki`, no redirect resolution);
  * failing that, does an item exist with this exact ja LABEL
    (`wbsearchentities`) — an item with no sitelink is invisible to every
    sitelink-based lookup, which is the case this whole check exists to find.

Wikidata is touched here deliberately and narrowly: two batched sitelink calls
plus one search per unmatched title, ~1s apart. This is the one question
ja.wikipedia cannot answer ("does an item exist"), not a data sweep.

Writes `lineage/_collisions.json` for the report page. Read-only.

Usage: python lineage/investigate_collisions.py
"""
import collections
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

JA_API = 'https://ja.wikipedia.org/w/api.php'
WD_API = 'https://www.wikidata.org/w/api.php'
OUT = os.path.join(SCRIPT_DIR, '_collisions.json')
THROTTLE = 1.0


def get(api, params):
    params = dict(params, format='json', formatversion='2')
    req = urllib.request.Request(
        api + '?' + urllib.parse.urlencode(params),
        headers={'User-Agent': WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def page_kind(titles):
    """title -> ('article'|'redirect'|'missing', target, section)."""
    kind = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        # redirects=0: do NOT follow. The following is the bug being diagnosed.
        data = get(JA_API, {'action': 'query', 'prop': 'info',
                            'titles': '|'.join(batch)})
        for page in data.get('query', {}).get('pages', []) or []:
            if page.get('missing'):
                kind[page['title']] = ('missing', '', '')
            elif page.get('redirect'):
                kind[page['title']] = ('redirect', '', '')
            else:
                kind[page['title']] = ('article', '', '')
        # Resolve where each redirect points, including the #section.
        reds = [t for t in batch if kind.get(t, ('',))[0] == 'redirect']
        if reds:
            d2 = get(JA_API, {'action': 'query', 'redirects': '1',
                              'titles': '|'.join(reds)})
            for e in d2.get('query', {}).get('redirects', []) or []:
                if e['from'] in kind:
                    kind[e['from']] = ('redirect', e['to'], e.get('tofragment', ''))
        time.sleep(THROTTLE)
    return kind


def sitelink_items(titles):
    """title -> QID of the item whose jawiki sitelink is exactly this title."""
    found = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        data = get(WD_API, {'action': 'wbgetentities', 'sites': 'jawiki',
                            'titles': '|'.join(titles[i:i + 50]), 'props': 'sitelinks'})
        for qid, ent in (data.get('entities') or {}).items():
            if qid.startswith('Q'):
                link = (ent.get('sitelinks') or {}).get('jawiki', {}).get('title')
                if link:
                    found[link] = qid
        time.sleep(THROTTLE)
    return found


def label_items(title):
    """Items whose ja label matches this title exactly (no sitelink needed)."""
    data = get(WD_API, {'action': 'wbsearchentities', 'language': 'ja',
                        'uselang': 'ja', 'search': title, 'limit': 5, 'type': 'item'})
    time.sleep(THROTTLE)
    return [{'qid': h['id'], 'label': h.get('label', ''),
             'description': h.get('description', '')}
            for h in data.get('search', []) or []
            if h.get('label') == title]


def main():
    title2qid = json.load(open(os.path.join(ROOT, '_title2qid.json'), encoding='utf-8'))
    results = {r.split('\t')[0]: r.rstrip('\n').split('\t')
               for r in open(os.path.join(SCRIPT_DIR, 'agent_results.tsv'),
                             encoding='utf-8')}

    rev = collections.defaultdict(list)
    for t, q in title2qid.items():
        rev[q].append(t)
    groups = {q: ts for q, ts in rev.items() if len(ts) > 1}
    titles = sorted(t for ts in groups.values() for t in ts)
    print(f'{len(groups)} colliding QIDs over {len(titles)} titles')

    kind = page_kind(titles)
    sitelinks = sitelink_items(titles)
    out = []
    for qid, ts in sorted(groups.items()):
        members = []
        for t in sorted(ts):
            k, target, section = kind.get(t, ('?', '', ''))
            own = sitelinks.get(t)
            by_label = [] if own else label_items(t)
            row = results.get(t, ['', '', '', ''])
            members.append({
                'title': t, 'mapped_qid': title2qid[t], 'page_kind': k,
                'redirect_target': target, 'redirect_section': section,
                'own_item_by_sitelink': own,
                'items_by_exact_ja_label': by_label,
                'agent_class': row[1] if len(row) > 1 else '',
                'agent_source': row[2] if len(row) > 2 else '',
                'agent_quote': row[3] if len(row) > 3 else '',
            })
            print(f'  {t:28s} {k:9s} -> {target or "-"}'
                  f'{"#" + section if section else ""}  own={own or "-"}'
                  f'  label-hits={[h["qid"] for h in by_label] or "-"}')
        out.append({'shared_qid': qid, 'members': members})

    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\nwritten to {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
