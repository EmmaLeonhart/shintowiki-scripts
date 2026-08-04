#!/usr/bin/env python3
"""
stage_takihara_p612.py
======================
Emit 瀧原宮's P612 line once 磯宮 exists.

Emma on the 分霊 page: 瀧原宮 Q11566292 — *"make wikidata for 磯宮"*. That is the
answer, but it cannot be a single QuickStatement: 磯宮 has no ja.wikipedia article
and no Wikidata item, so there is no QID to point at until the CREATE batch has
run. QuickStatements' `LAST` refers only to the item just created, and the
subject here is an existing item, so the two halves cannot live in one block.

Hence two steps, in this order and never the other way round:

  1. `create_items.py --batch ise_jingu_creates.txt --apply` creates 磯宮 and
     records its QID in `ise_jingu_creates.state`.
  2. this script reads that state and appends the 瀧原宮 line.

Run it any time. Before step 1 it prints what it is waiting for and writes
nothing; after step 1 it is idempotent, because it refuses to append a P612 line
for a subject that already has one.

Usage: python lineage/stage_takihara_p612.py [--apply]
"""
import argparse
import io
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

STATE = os.path.join(ROOT, 'modern-quickstatements', 'ise_jingu_creates.state')
QS_OUT = os.path.join(ROOT, 'modern-quickstatements', 'beppyo_p612.txt')

TAKIHARA = 'Q11566292'          # 瀧原宮
ISO_LABEL = 'Iso-no-miya'       # the key create_items.py records state under
BUNREI = 'Q195793'
URL = 'https://ja.wikipedia.org/wiki/%E7%80%A7%E5%8E%9F%E5%AE%AE'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(STATE):
        print(f'waiting: {os.path.basename(STATE)} does not exist yet — '
              f'run create_items.py --batch ise_jingu_creates.txt --apply first')
        return 0
    created = json.load(open(STATE, encoding='utf-8'))
    iso = created.get(ISO_LABEL)
    if not iso:
        print(f'waiting: 磯宮 ("{ISO_LABEL}") is not in {os.path.basename(STATE)} yet')
        return 0

    for line in open(QS_OUT, encoding='utf-8'):
        if line.startswith(f'{TAKIHARA}|P612|'):
            print(f'already staged: {line.strip()}')
            return 0

    line = f'{TAKIHARA}|P612|{iso}|P1013|{BUNREI}|S854|"{URL}"'
    print(line)
    if not args.apply:
        print('dry run; pass --apply')
        return 0
    with open(QS_OUT, 'a', encoding='utf-8', newline='\n') as fh:
        fh.write(line + '\n')
    print(f'appended -> {QS_OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
