#!/usr/bin/env python3
"""
source_coverage.py
==================
For every shrine the full read gave a LINEAGE (TRANSFER or NETWORK), answer the
question Emma asked 2026-08-04: **does the thing it came from have a Wikidata
item, or not?**

Four outcomes per row, written to `lineage/_source_coverage.tsv`:

    ITEM        the named source resolves to a Wikidata item -> P612 is emittable
    NO_ITEM     ja.wikipedia has an article for it but the article has no item
    NO_ARTICLE  no ja.wikipedia article — the source is prose, a lost shrine, or
                a place with no page ("伊部郷座ヶ岳の素盞嗚尊神霊")
    AMBIGUOUS   resolves only to a disambiguation page, or to the subject itself

**NO_ITEM and NO_ARTICLE are recorded, not discarded** (Emma: "No wikidata item
means still record it — it can be folded in later"). The source string and the
sentence the agent quoted are kept verbatim so the edge can be re-made once an
item exists, without re-reading 444 articles.

Reads ja.wikipedia only, never Wikidata. Usage: python lineage/source_coverage.py
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from lineage.build_p612_quickstatements import (  # noqa: E402
    candidates, head_for, load_results, resolve_titles, API, DAB)
import urllib.parse                              # noqa: E402
import urllib.request                            # noqa: E402
import time                                      # noqa: E402
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

# build_p612_quickstatements already wraps stdout as utf-8 on import; wrapping
# it a second time closes the buffer out from under the first wrapper.
OUT = os.path.join(SCRIPT_DIR, '_source_coverage.tsv')


def article_exists(titles):
    """title -> True if ja.wikipedia has an article (missing pages excluded)."""
    live = set()
    titles = list(titles)
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        params = {'action': 'query', 'format': 'json', 'formatversion': '2',
                  'redirects': '1', 'titles': '|'.join(batch)}
        req = urllib.request.Request(
            API + '?' + urllib.parse.urlencode(params),
            headers={'User-Agent': WIKIDATA_USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        norm = {}
        for key in ('normalized', 'redirects'):
            for e in data.get('query', {}).get(key, []) or []:
                norm[e['from']] = e['to']
        present = {p['title'] for p in data.get('query', {}).get('pages', []) or []
                   if not p.get('missing')}
        for asked in batch:
            cur, seen = asked, set()
            while cur in norm and cur not in seen:
                seen.add(cur)
                cur = norm[cur]
            if cur in present:
                live.add(asked)
        time.sleep(0.3)
    return live


def main():
    title2qid = {t: q for t, q in json.load(open(
        os.path.join(SCRIPT_DIR, 'subject_qids.json'), encoding='utf-8'))['map'].items() if q}
    rows = [r for r in load_results() if r[1] in ('TRANSFER', 'NETWORK')]

    wanted = set()
    for _, _, source in rows:
        wanted.update(candidates(source))
        head = head_for(source)
        if head:
            wanted.add(head)
    print(f'{len(rows)} lineage rows, {len(wanted)} candidate titles')
    resolved = resolve_titles(sorted(wanted))
    unresolved = sorted(wanted - set(resolved))
    live = article_exists(unresolved) if unresolved else set()

    out, tally = [], {}
    for title, cls, source in rows:
        subject = title2qid.get(title)
        verdict, target, via = 'NO_ARTICLE', '', ''
        for cand in candidates(source):
            if cand in resolved:
                verdict, target, via = 'ITEM', resolved[cand], cand
                break
            same = [t for t in title2qid if t == cand or t.startswith(cand + ' (')]
            if len(same) == 1:
                verdict, target, via = 'ITEM', title2qid[same[0]], same[0]
                break
        if verdict == 'ITEM' and target == subject:
            verdict, target, via = 'AMBIGUOUS', '', via + ' (is the subject itself)'
        if verdict == 'NO_ARTICLE' and any(c in DAB for c in candidates(source)):
            verdict = 'AMBIGUOUS'
            via = next(c for c in candidates(source) if c in DAB) + ' (disambiguation page)'
        if verdict == 'NO_ARTICLE':
            head = head_for(source)
            if head and head in resolved:
                verdict, target, via = 'ITEM', resolved[head], f'inferred head: {head}'
            else:
                hit = [c for c in candidates(source) if c in live]
                if hit:
                    verdict, via = 'NO_ITEM', hit[0]
        tally[verdict] = tally.get(verdict, 0) + 1
        out.append('\t'.join([title, subject or '-', cls, verdict, target, via, source]))

    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('shrine\tsubject\tclass\tverdict\ttarget\tvia\tsource\n')
        fh.write('\n'.join(out) + '\n')

    n = len(rows)
    print()
    for k in ('ITEM', 'NO_ITEM', 'NO_ARTICLE', 'AMBIGUOUS'):
        c = tally.get(k, 0)
        print(f'  {k:11s} {c:4d}  {100.0 * c / n:5.1f}%')
    print(f'\nwritten to {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
