#!/usr/bin/env python3
"""
stage_jingu125_kana.py
======================
Append the 神宮125社 P1814 lines to `modern-quickstatements/name_in_kana.txt`.

A0 bucket (a), done the local way. The queue note is that the cloud routine
handles only a handful of items per run across 2,252 entries, so local batches
"exactly like bucket (b)" are the faster road; `fetch_jingu125_kana.py` produced
the candidate readings and every one was checked against its own lead before
this ran.

TWO REFUSALS, both deliberate:
  * a row with no candidate reading stages nothing — 機殿神社 is the joint article
    for 神服織機殿神社 and 神麻続機殿神社 and has no reading of its own;
  * a QID already present in the output file, or in `_resolved.log`, stages
    nothing. Until the freeze lifts, local staging is the ONLY record of what has
    been done — the target query cannot see an undelivered line, so "does
    Wikidata still lack P1814" would re-queue everything already staged. This is
    the same `already_handled` rule as `build_name_in_kana_queue.py`, and the
    reason it exists is that a rebuild once re-created 12 finished work-files.

Idempotent: run it twice and the second run appends nothing.

Usage: python lineage/stage_jingu125_kana.py [--apply]
"""
import argparse
import io
import os
import re
import sys
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = os.path.join(SCRIPT_DIR, '_jingu125_kana.tsv')
QS_OUT = os.path.join(ROOT, 'modern-quickstatements', 'name_in_kana.txt')
WORKDIR = os.path.join(ROOT, 'name_in_kana')
RESOLVED_LOG = os.path.join(WORKDIR, '_resolved.log')

JAWIKI = 'Q177837'          # Japanese Wikipedia, for S143 imported-from
HIRAGANA_ONLY = re.compile(r'^[ぁ-ゖー]+$')


def already_staged():
    done = set()
    for path in (QS_OUT, RESOLVED_LOG):
        if not os.path.exists(path):
            continue
        for line in open(path, encoding='utf-8'):
            m = re.match(r'^(Q\d+)[|\t]', line)
            if m:
                done.add(m.group(1))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='append the lines (default: show what would be added)')
    args = ap.parse_args()

    done = already_staged()
    rows = [l.rstrip('\n').split('\t')
            for l in open(SRC, encoding='utf-8')][1:]

    lines, skipped_done, skipped_blank = [], 0, []
    for qid, title, kana, _lead in rows:
        if not kana:
            skipped_blank.append(title)
            continue
        if qid in done:
            skipped_done += 1
            continue
        if not HIRAGANA_ONLY.match(kana):
            # The gate. Katakana signals the ancient Engishiki reading, which is
            # what the kana-qualifier cleanup is stripping OUT of top-level P1814.
            skipped_blank.append(f'{title} (not pure hiragana: {kana})')
            continue
        url = 'https://ja.wikipedia.org/wiki/' + urllib.parse.quote(
            title.replace(' ', '_'), safe='_')
        lines.append(f'{qid}|P1814|"{kana}"|S143|{JAWIKI}|S4656|"{url}"')
        done.add(qid)

    print(f'{len(rows)} rows: {len(lines)} to stage, {skipped_done} already staged, '
          f'{len(skipped_blank)} with no usable reading')
    for s in skipped_blank:
        print(f'  no reading: {s}')

    if not args.apply:
        for line in lines[:5]:
            print(f'  {line}')
        if len(lines) > 5:
            print(f'  … and {len(lines) - 5} more (dry run; pass --apply)')
        return

    with open(QS_OUT, 'a', encoding='utf-8', newline='\n') as fh:
        for line in lines:
            fh.write(line + '\n')
    total = sum(1 for _ in open(QS_OUT, encoding='utf-8'))
    print(f'appended {len(lines)} lines -> {QS_OUT} ({total} total)')

    # Some of these already had a work-file waiting for the cloud routine. Doing
    # the item locally does not stop the routine answering it, and the collector
    # would then write a SECOND identical P1814 line — the exact duplication the
    # builders were fixed for. Retiring the file is what the collector itself
    # does on answering, so it is the right disposal.
    retired = []
    for line in lines:
        qid = line.split('|', 1)[0]
        wf = os.path.join(WORKDIR, f'{qid}.wiki')
        if os.path.exists(wf):
            os.remove(wf)
            retired.append(qid)
    if retired:
        with open(RESOLVED_LOG, 'a', encoding='utf-8', newline='\n') as fh:
            for qid in retired:
                fh.write(f'{qid}\tKANA\tstaged locally from the 神宮125社 pass\n')
        print(f'retired {len(retired)} pending work-file(s): {", ".join(retired)}')


if __name__ == '__main__':
    main()
