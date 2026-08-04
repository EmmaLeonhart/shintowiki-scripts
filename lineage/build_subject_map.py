#!/usr/bin/env python3
"""
build_subject_map.py
====================
Build `lineage/subject_qids.json` — shrine title -> the QID of **that shrine's
own Wikidata item**, or null.

This replaces the root `_title2qid.json`, which was built by asking ja.wikipedia
for `pageprops.wikibase_item` **with redirects followed**. That silently hands a
redirect the QID of the article it lands on. In this data set 25 of 444 titles
are redirects, so 25 shrines were pointed at another shrine's item, and 19 items
were claimed by two or three shrines at once. An article is not a data item:

  * 大河内神社 and 打懸神社 are SECTION redirects into 志等美神社;
  * 川相神社 and 熊淵神社 redirect to 大水神社 (they were physically moved into its
    precinct in Meiji — a shrine move, which jawiki merged into one article);
  * 馬場都々古別神社 has its own item, Q114593121, whose jawiki sitelink is the
    redirect title itself;
  * 神服織機殿神社, 八槻都々古別神社 and 大間国生神社 have their own items with NO
    sitelink at all — invisible to every sitelink-based lookup.

Resolution order per title, stopping at the first hit:
  1. jawiki page is a real ARTICLE  -> its `pageprops.wikibase_item`
  2. an item whose jawiki SITELINK is exactly this title (redirect sitelinks are
     legal on Wikidata and this is how #3 above is found)
  3. an item whose ja LABEL is exactly this title (`wbsearchentities`)
  4. null — the shrine has no item; record it, do not invent one

Step 1 is ja.wikipedia. Steps 2-3 are the one question ja.wikipedia cannot
answer, asked narrowly and throttled, only for titles step 1 could not settle.

Usage: python lineage/build_subject_map.py [--titles-from _agent_input]
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
from shinto_miraheze.user_agent import USER_AGENT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

JA_API = 'https://ja.wikipedia.org/w/api.php'
WD_API = 'https://www.wikidata.org/w/api.php'
OUT = os.path.join(SCRIPT_DIR, 'subject_qids.json')
THROTTLE = 0.5


def get(api, params):
    params = dict(params, format='json', formatversion='2')
    req = urllib.request.Request(
        api + '?' + urllib.parse.urlencode(params),
        headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def article_items(titles):
    """title -> (qid|None, kind). Redirects are NOT followed."""
    out = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = get(JA_API, {'action': 'query', 'prop': 'pageprops|info',
                            'titles': '|'.join(batch)})
        for page in data.get('query', {}).get('pages', []) or []:
            title = page['title']
            if page.get('missing'):
                out[title] = (None, 'missing')
            elif page.get('redirect'):
                out[title] = (None, 'redirect')
            else:
                qid = (page.get('pageprops') or {}).get('wikibase_item')
                out[title] = (qid, 'article' if qid else 'article-no-item')
        time.sleep(THROTTLE)
        print(f'  jawiki {min(i + 50, len(titles))}/{len(titles)}')
    return out


def sitelink_items(titles):
    out = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        data = get(WD_API, {'action': 'wbgetentities', 'sites': 'jawiki',
                            'titles': '|'.join(titles[i:i + 50]),
                            'props': 'sitelinks'})
        for qid, ent in (data.get('entities') or {}).items():
            if qid.startswith('Q'):
                link = (ent.get('sitelinks') or {}).get('jawiki', {}).get('title')
                if link:
                    out[link] = qid
        time.sleep(THROTTLE)
    return out


def label_item(title):
    data = get(WD_API, {'action': 'wbsearchentities', 'language': 'ja',
                        'uselang': 'ja', 'search': title, 'limit': 5,
                        'type': 'item'})
    time.sleep(THROTTLE)
    hits = [h['id'] for h in data.get('search', []) or [] if h.get('label') == title]
    return hits[0] if len(hits) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--titles-from', default=os.path.join(ROOT, '_agent_input'))
    args = ap.parse_args()

    titles = sorted({f[:-4]
                     for d in os.listdir(args.titles_from)
                     if os.path.isdir(os.path.join(args.titles_from, d))
                     for f in os.listdir(os.path.join(args.titles_from, d))
                     if f.endswith('.txt')})
    print(f'{len(titles)} titles')

    kinds = article_items(titles)
    unresolved = [t for t in titles if not kinds.get(t, (None,))[0]]
    print(f'{len(unresolved)} titles are not articles with an item — asking Wikidata')
    sitelinks = sitelink_items(unresolved) if unresolved else {}

    mapping, how = {}, {}
    for t in titles:
        qid, kind = kinds.get(t, (None, 'missing'))
        if qid:
            mapping[t], how[t] = qid, 'article'
            continue
        if t in sitelinks:
            mapping[t], how[t] = sitelinks[t], f'{kind}, own sitelink'
            continue
        by_label = label_item(t)
        if by_label:
            mapping[t], how[t] = by_label, f'{kind}, exact ja label (no sitelink)'
        else:
            mapping[t], how[t] = None, f'{kind}, no item'
            print(f'  NO ITEM: {t} ({kind})')

    json.dump({'map': mapping, 'how': how}, open(OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    have = sum(1 for v in mapping.values() if v)
    dupes = len(mapping) - len({v for v in mapping.values() if v}) - (len(mapping) - have)
    print(f'\n{have}/{len(titles)} have an item; {len(titles) - have} do not; '
          f'{dupes} QIDs still shared')
    print(f'written to {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
