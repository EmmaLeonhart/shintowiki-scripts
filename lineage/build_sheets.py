#!/usr/bin/env python3
"""
build_sheets.py
===============
Write the two CSVs that get uploaded as Google Sheets for Emma to edit by hand:

    lineage/sheets/to_fix.csv    the 32 rows that produced no statement
    lineage/sheets/all_444.csv   every row, with the statement it produced

Shrine names link to ja.wikipedia and every QID links to Wikidata, as
`=HYPERLINK()` formulas — Sheets evaluates them on CSV import, so the columns are
clickable rather than raw ids. Editable columns (`FIX`, `NOTE`) are left empty
on purpose; they are Emma's, not the pipeline's.

Usage: python lineage/build_sheets.py
"""
import csv
import io
import json
import os
import sys
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
OUTDIR = os.path.join(SCRIPT_DIR, 'sheets')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def link(url, label):
    label = (label or '').replace('"', "'")
    return f'=HYPERLINK("{url}","{label}")'


def ja(title):
    # Unencoded UTF-8 in the URL: browsers and Sheets both handle it, and it
    # keeps the CSV a third of the size percent-encoding would make it.
    return link('https://ja.wikipedia.org/wiki/' + title.replace(' ', '_'), title)


def wd(qid, label=None):
    if not qid or not qid.startswith('Q'):
        return ''
    return link(f'https://www.wikidata.org/wiki/{qid}', label or qid)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    subjects = json.load(open(os.path.join(SCRIPT_DIR, 'subject_qids.json'), encoding='utf-8'))
    results = [l.rstrip('\n').split('\t')
               for l in open(os.path.join(SCRIPT_DIR, 'agent_results.tsv'), encoding='utf-8')][1:]
    collisions = {m['title']: m
                  for g in json.load(open(os.path.join(SCRIPT_DIR, '_collisions.json'),
                                          encoding='utf-8'))
                  for m in g['members']}
    emitted = {}
    for line in open(os.path.join(ROOT, 'modern-quickstatements', 'beppyo_p612.txt'),
                     encoding='utf-8'):
        p = line.strip().split('|')
        if len(p) > 2 and p[1] == 'P612':
            emitted[p[0]] = p[2]
    ise = {f[:-4] for f in os.listdir(os.path.join(ROOT, '_agent_input', 'jingu125'))
           if f.endswith('.txt')}
    # Names for the targets we emitted, so a QID column reads as a shrine.
    qid2title = {q: t for t, q in subjects['map'].items() if q}

    fix, allrows = [], []
    for row in results:
        title, cls, source, quote = (row + ['', '', ''])[:4]
        qid = subjects['map'].get(title)
        target = emitted.get(qid) if qid else None
        col = collisions.get(title, {})
        allrows.append([
            'Ise' if title in ise else 'Beppyo', ja(title), wd(qid) if qid else 'NO ITEM',
            cls, source, wd(target, qid2title.get(target, target)) if target else '',
            'ok' if target else 'NEEDS WORK', quote, '', ''])
        if target:
            continue
        if not qid:
            action = 'CREATE ITEM'
            detail = ('redirect → ' + col.get('redirect_target', '')
                      + (('#' + col['redirect_section']) if col.get('redirect_section') else ''))
            want = 'Q135508874' if cls == 'AUTOCHTHONOUS' else ''
        elif cls == 'UNKNOWN':
            action, detail, want = 'NO ORIGIN IN ARTICLE', 'article gives none', ''
        else:
            action, detail, want = 'PICK TARGET', f'cannot resolve: {source}', ''
        fix.append([action, ja(title), wd(qid) if qid else 'NO ITEM', cls,
                    wd(want, 'Q135508874 (autochthonous)') if want else '',
                    source, detail, quote, '', ''])

    order = {'CREATE ITEM': 0, 'PICK TARGET': 1, 'NO ORIGIN IN ARTICLE': 2}
    fix.sort(key=lambda r: (order[r[0]], r[3]))

    with open(os.path.join(OUTDIR, 'to_fix.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['ACTION', 'SHRINE', 'ITEM', 'CLASS', 'P612 VALUE WANTED',
                    'SOURCE NAMED IN ARTICLE', 'WHY IT STOPPED',
                    'EVIDENCE (the sentence)', 'FIX', 'NOTE'])
        w.writerows(fix)

    with open(os.path.join(OUTDIR, 'all_444.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['SET', 'SHRINE', 'ITEM', 'CLASS', 'SOURCE NAMED IN ARTICLE',
                    'P612 STAGED', 'STATUS', 'EVIDENCE (the sentence)', 'FIX', 'NOTE'])
        w.writerows(sorted(allrows, key=lambda r: (r[6] == 'ok', r[0], r[3])))

    print(f'to_fix.csv: {len(fix)} rows | all_444.csv: {len(allrows)} rows')


if __name__ == '__main__':
    main()
