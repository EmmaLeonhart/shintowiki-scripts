#!/usr/bin/env python3
"""
build_ise_creates.py
====================
Emit the CREATE batch for the 21 神宮125社 shrines that have NO Wikidata item.

Emma 2026-08-04: *"you should just make items for all of the Issei ones … make
them with the English name, English language name, the P31 Shinto Shrine
Japanese language name, and a connection, and then it'll gradually go through
our pipeline as well."*

WHY THEY HAVE NO ITEM. Each is a real shrine of the 125, but on ja.wikipedia it
is a REDIRECT into a neighbouring shrine's article (two are *section* redirects)
— jawiki merged co-located shrines into one page for editorial convenience. No
article means no sitelink, and a sitelink is how nearly everything here finds a
QID. `build_subject_map.py` already asked the other two questions Wikidata can
answer — is there an item whose jawiki sitelink is this redirect title, and is
there an item whose ja label is exactly this name — and both came back empty for
all 21. So they genuinely do not exist; this is not a lookup failure.

WHAT EACH ITEM GETS, and nothing else:
    Lja  the shrine name            (the jawiki title)
    Len  the English name           (kana -> romaji, `kana_english.label_for`)
    P31  Q845945                    Shinto shrine
    P361 Q687168                    伊勢神宮 — the "connection". Every one of the
                                    99 神宮125社 items that DOES exist carries it.
    P1814 the hiragana reading      free here: the reading had to be read out of
                                    the parent article anyway to romanize the
                                    English label, so A0's whole job is done for
                                    these 21 in the same pass.
    P612 <origin> P1013 Q195793     the lineage value the 444-article read
                                    produced — the reason these were held back.

NO DESCRIPTIONS. Emma's standing note on [[Open questions]]: a past run "randomly
decided to add descriptions when I never asked … that broke the deduplication
process". She did not ask, so there are none.

NO SITELINK. A Wikidata sitelink to a redirect title is legal and would be nice,
but it is the one field that can silently steal a link from a neighbouring item.
Left for a deliberate pass.

The P612 value is resolved with the SAME gates as `build_p612_quickstatements.py`
(that module is imported, not copied): disambiguation pages refused, self-
reference refused, and a row that cannot resolve gets its item created WITHOUT a
P612 rather than with a guessed one.

Output: modern-quickstatements/ise_jingu_creates.txt  (create_items.py batch)
Log:    lineage/_ise_creates.log
Read-only against ja.wikipedia; writes only those two files.

Usage: python lineage/build_ise_creates.py
"""
import io
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
for p in (ROOT, os.path.join(ROOT, 'modern-quickstatements')):
    if p not in sys.path:
        sys.path.insert(0, p)

# NOT the usual `sys.stdout = io.TextIOWrapper(...)` rebind. This module imports
# build_p612_quickstatements, which performs that rebind itself at module scope
# (the documented script-template invariant). Two wrappers over one buffer means
# whichever is dropped first closes the buffer under the other — that is a real
# ValueError, not a theoretical one. `reconfigure` mutates the existing stream
# instead of stacking a second wrapper on it.
sys.stdout.reconfigure(encoding='utf-8')

import build_p612_quickstatements as p612          # noqa: E402
from kana_english import label_for                 # noqa: E402

OUT = os.path.join(ROOT, 'modern-quickstatements', 'ise_jingu_creates.txt')
LOG = os.path.join(SCRIPT_DIR, '_ise_creates.log')

SHRINE = 'Q845945'      # Shinto shrine
JINGU = 'Q687168'       # 伊勢神宮 / Ise Grand Shrine
BUNREI = p612.BUNREI    # Q195793, criterion used
JA_URL = 'https://ja.wikipedia.org/wiki/'

# `kana_english.label_for` declines these three, correctly — it only romanizes a
# name whose kana reading ends in the kana of a known shrine-type suffix, and
# none of these do. Emma 2026-08-04 asked for them anyway ("create them, my best
# labels"), so the labels are written out here rather than by loosening the
# generator, which would start guessing for every future name it cannot parse.
#
#   屋乃波比伎神 / 宮比神  are KAMI names, not 神社 — 宮比神 has no shrine building
#                        at all. Rendered with the -no-kami the reading gives.
#   瀧原竝宮              reading is …のみや, not …ぐう, so the 宮 rule refuses it.
#                        Matches its sibling 瀧原宮, which Wikidata already labels
#                        "Takihara-no-miya" (Q11566292).
MANUAL_LABELS = {
    '屋乃波比伎神': 'Yanohahiki-no-kami',
    '宮比神': 'Miyabi-no-kami',
    '瀧原竝宮': 'Takiharanarabi-no-miya',
}

# Not one of the 神宮125社 and not from the redirect set — 磯宮 has no ja.wikipedia
# article at all. Emma asked for it directly on the 分霊 page: "make wikidata for
# 磯宮", because 瀧原宮's origin is 磯宮 and P612 cannot point at a thing that does
# not exist. It belongs in this batch because it is the same kind of object with
# the same gate: the proto-Naikū, where Amaterasu was enshrined on the 五十鈴川
# before the 皇大神宮 was built.
#
# It carries no P612 of its own. Chaining it back to 笠縫邑 would be a second
# inference and the 分霊 page does not make it.
EXTRA_BLOCKS = [{
    'title': '磯宮',
    'en': 'Iso-no-miya',
    'kana': 'いそのみや',
    'source': 'Emma, 分霊 page: "make wikidata for 磯宮"',
}]


def resolve_p612(rows, log):
    """title -> P612 QID, or absent when nothing resolves safely."""
    wanted, sources = {}, {}
    row_redirect = {r['title']: r['redirect'] for r in rows}
    for r in rows:
        if r['p612']:                     # AUTOCHTHONOUS: a fixed value, no lookup
            wanted[r['title']] = r['p612']
            continue
        sources[r['title']] = r['source']

    # Collect every candidate title across the unresolved rows, ask once.
    asks = set()
    per_row = {}
    for title, source in sources.items():
        cands = p612.candidates(source)
        # These 21 are redirects, so we know the real article title they point
        # at — including its half-width disambiguator, which the source prose
        # never carries. "朝熊神社（その御前神）" yields the candidate 朝熊神社,
        # which is not an article; 朝熊神社 (伊勢市) is. Promote the redirect
        # target only when a candidate is that title minus its disambiguator,
        # so this never introduces an unrelated article.
        redirect = row_redirect[title].split('#')[0].strip()
        base = redirect.split(' (')[0]
        if redirect != base and base in cands:
            cands.insert(cands.index(base), redirect)
        head = p612.head_for(source)
        if head:
            cands.append(head)
        per_row[title] = cands
        asks.update(cands)

    resolved = p612.resolve_titles(sorted(asks)) if asks else {}

    for title, cands in per_row.items():
        hit = None
        for c in cands:
            qid = resolved.get(c)
            if not qid:
                continue
            if c == title:                # self-reference: 瀧原竝宮 -> 瀧原竝宮
                log.append(f'{title}: SKIP P612 — candidate {c} is itself')
                continue
            hit = (c, qid)
            break
        if hit:
            wanted[title] = hit[1]
            log.append(f'{title}: P612 = {hit[1]} via "{hit[0]}" '
                       f'(source: {sources[title]})')
        else:
            log.append(f'{title}: NO P612 — nothing in {cands} resolves '
                       f'(source: {sources[title]}); item still created')
    return wanted


def main():
    rows = json.load(open(os.path.join(SCRIPT_DIR, '_ise21.json'), encoding='utf-8'))
    readings = json.load(open(os.path.join(SCRIPT_DIR, '_ise21_readings.json'),
                              encoding='utf-8'))
    log = []
    targets = resolve_p612(rows, log)

    blocks, skipped = [], []
    for r in rows:
        title = r['title']
        kana = (readings.get(title) or {}).get('kana')
        auto = label_for(title, kana) if kana else None
        if auto:
            en_label = auto.label
        elif title in MANUAL_LABELS:
            en_label = MANUAL_LABELS[title]
            log.append(f'{title}: en label "{en_label}" is hand-written '
                       f'(label_for declined; kana={kana or "none"})')
        else:
            # <batch>.state is keyed on the English label, so a block without one
            # is not idempotent — it would be re-created on every run.
            skipped.append(title)
            log.append(f'{title}: SKIPPED — no English label '
                       f'(kana={kana or "none"}; label_for declined, '
                       f'no MANUAL_LABELS entry)')
            continue

        url = JA_URL + title.replace(' ', '_')
        lines = [
            'CREATE',
            f'LAST|Len|"{en_label}"',
            f'LAST|Lja|"{title}"',
            f'LAST|P31|{SHRINE}',
            f'LAST|P361|{JINGU}',
            f'LAST|P1814|"{kana}"|S143|Q177837|S4656|"{url}"',
        ]
        if title in targets:
            lines.append(
                f'LAST|P612|{targets[title]}|P1013|{BUNREI}|S854|"{url}"')
        blocks.append((title, en_label, lines))

    for extra in EXTRA_BLOCKS:
        # No P1814 source URL: there is no jawiki article to cite, which is the
        # whole reason the item has to be made by hand.
        blocks.append((extra['title'], extra['en'], [
            'CREATE',
            f'LAST|Len|"{extra["en"]}"',
            f'LAST|Lja|"{extra["title"]}"',
            f'LAST|P31|{SHRINE}',
            f'LAST|P361|{JINGU}',
            f'LAST|P1814|"{extra["kana"]}"',
        ]))
        log.append(f'{extra["title"]}: extra block — {extra["source"]}')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('# The 21 神宮125社 shrines with no Wikidata item (Emma 2026-08-04:\n'
                 '# "just make them"). Run with:\n'
                 '#     python modern-quickstatements/create_items.py '
                 '--batch ise_jingu_creates.txt [--apply]\n'
                 '# Gate: ise_jingu_gate.py. Generated by lineage/build_ise_creates.py.\n')
        for title, en, lines in blocks:
            fh.write(f'\n# {title} — {en}\n')
            fh.write('\n'.join(lines) + '\n')

    with open(LOG, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(log) + '\n')

    with_p612 = sum(1 for _, _, l in blocks if any('|P612|' in x for x in l))
    print(f'{len(blocks)} CREATE blocks -> {OUT}')
    print(f'  {with_p612} carry a P612; {len(blocks) - with_p612} do not')
    if skipped:
        print(f'  {len(skipped)} skipped (no English label): {", ".join(skipped)}')
    print(f'log -> {LOG}')


if __name__ == '__main__':
    main()
