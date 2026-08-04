#!/usr/bin/env python3
"""
extract_ise21.py
================
Pull the 21 CREATE-ITEM rows out of `lineage/sheets/to_fix.csv` into a plain
JSON list (`lineage/_ise21.json`) that the reading fetcher and the CREATE-batch
generator both read.

to_fix.csv is written for Google Sheets, so its cells are `=HYPERLINK(url,label)`
formulas; this unwraps them back to bare titles and QIDs.

Usage: python lineage/extract_ise21.py
"""
import csv
import io
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = os.path.join(SCRIPT_DIR, 'sheets', 'to_fix.csv')
OUT = os.path.join(SCRIPT_DIR, '_ise21.json')

HYPERLINK = re.compile(r'^=HYPERLINK\("[^"]*","(.*)"\)$')


def unwrap(cell):
    m = HYPERLINK.match(cell or '')
    return m.group(1) if m else (cell or '')


def main():
    rows = list(csv.reader(open(SRC, encoding='utf-8-sig')))[1:]
    out = []
    for r in rows:
        action, shrine, item, cls, want, source, why, quote = r[:8]
        if action != 'CREATE ITEM':
            continue
        want_qid = ''
        m = re.match(r'^=HYPERLINK\("https://www\.wikidata\.org/wiki/(Q\d+)"', want or '')
        if m:
            want_qid = m.group(1)
        out.append({
            'title': unwrap(shrine),
            'redirect': why.replace('redirect → ', '').strip(),
            'cls': cls,
            'p612': want_qid,
            'source': source,
            'quote': quote,
        })
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(out)} rows -> {OUT}')
    for o in out:
        print(f"  {o['title']:<12} {o['cls']:<14} P612={o['p612'] or '(from source: ' + o['source'][:20] + ')'}")


if __name__ == '__main__':
    main()
