#!/usr/bin/env python3
"""
build_en_label_queue.py
=======================
Stage 4 of the English-label pipeline (docs/english_label_pipeline.md), rebuilt as
a remote-queue category after the dedicated cloud routine was lost.

**Why this exists.** Stage 4 used to be its own claude.ai routine emitting
``chore(en-labels): 5 Sonnet-translated shrine labels`` every day. It stopped on
2026-07-27 -- the day Emma moved Claude accounts. Routines do not survive an
account move (docs/remote_queue_pipeline.md); the remote_queue drainer was
recreated that night and the label routine was not, so Stage 4 was simply absent
for 52 days while Stages 0-2 kept running. Emma's call, 2026-09-17: fold labels
into the drainer that already works rather than recreate a second routine.

So this writes one work-file per residual item into ``en_label/``; ``remote_queue.py``
emits them; the worker fills the ANSWER marker; ``collect_en_labels.py`` folds
answers into ``modern-quickstatements/en_labels_sonnet.txt`` and deletes the file.

**The pool is CAPPED, and that is the point of Emma's choice.** The residual is
~18,000 items against ~1,400 for every other category combined. Queueing it whole
would make labels ~93% of the queue, so the drainer's 5 random picks would be
labels almost every day and every other category would starve. That is a priority
change nobody asked for. ``--pool`` (default 400) keeps labels a normal-sized
category, comparable to name_in_kana (807) and category_translation (328), and
each run tops the pool back up as answers drain it.

Selection reuses ``select_shrines_to_translate.py`` unchanged -- its
``excluded_qids()`` already skips every QID covered by a deterministic or pending
en-label file, so only the genuine residual is ever queued. Shrines and temples
are drawn as separate batches so adding temples never starves shrines.

Idempotent: existing work-files are kept and counted toward the pool.

Usage: python build_en_label_queue.py [--pool N] [--dry-run]
"""

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QS_DIR = os.path.join(ROOT, "modern-quickstatements")
OUTDIR = os.path.join(ROOT, "en_label")

if QS_DIR not in sys.path:
    sys.path.insert(0, QS_DIR)

import select_shrines_to_translate as sel  # noqa: E402

DEFAULT_POOL = 400

TASK = (
    "<!-- TASK: give this item its English Wikidata label (P1448 is NOT involved; "
    "this is the `Len` label).\n"
    "Conventions, which are not negotiable -- match the files this folds into:\n"
    "  shrine: '<Stem> Shrine', e.g. Iino Shrine, Kushikino Shrine.\n"
    "  temple: '<Stem>-<suffix> Temple', suffix romanized from the KANA so the\n"
    "          reading survives -- 誓願寺 せいがんじ -> 'Seigan-ji Temple',\n"
    "          清水寺 きよみずでら -> 'Kiyomizu-dera Temple'. Accepted suffixes:\n"
    "          -ji / -dera / -tera / -in / -an / -do / -bo.\n"
    "  Romanize in MACRON-FREE Hepburn (Kozen-ji, not Kōzen-ji). No parenthetical\n"
    "  disambiguator. No trailing period. Do not invent a reading you cannot source.\n"
    "RESEARCH the reading -- the jawiki article, the official site, the Kokugakuin\n"
    "database. The KANA field above is the authoritative reading when it is filled;\n"
    "when it is empty the reading is exactly what you have to establish, and kanji\n"
    "names have irregular readings, so do not guess from the characters alone.\n"
    "Fill ANSWER with exactly one of:\n"
    "  LABEL: <the English label>       (confident)\n"
    "  SKIP: <short reason>             (reading genuinely unsourceable, or the\n"
    "                                    item is not a shrine/temple at all)\n"
    "Do NOT edit Wikidata yourself and do NOT edit any other file -- a collector\n"
    "turns ANSWER into a QuickStatement later. When ANSWER is filled you are done\n"
    "with this file. -->"
)


def _outstanding():
    """QIDs that already have a work-file waiting for an answer."""
    if not os.path.isdir(OUTDIR):
        return set()
    return {
        name[:-5]
        for name in os.listdir(OUTDIR)
        if name.endswith(".wiki") and name.startswith("Q")
    }


def _write_item(item):
    qid = item["qid"]
    kana = item.get("kana") or ""
    path = os.path.join(OUTDIR, f"{qid}.wiki")
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"<!-- ITEM: https://www.wikidata.org/wiki/{qid} -->\n"
            f"<!-- KIND: {item['kind']} | JA: {item['ja']} | KANA: {kana} -->\n"
            f"<!-- ANSWER: -->\n{TASK}\n"
        )


def build(pool=DEFAULT_POOL, dry_run=False):
    outstanding = _outstanding()
    want = pool - len(outstanding)
    if want <= 0:
        return 0, len(outstanding)

    exclude = sel.excluded_qids() | outstanding
    shrines = sel._load_items(sel.WORKLIST)
    temples = sel._load_items(sel.TEMPLE_WORKLIST)

    # Separate batches, half each, so temples never starve shrines. select_batches
    # takes a PER-KIND count, so ask each kind for half the shortfall -- rounded
    # UP, or the two batches cannot cover an odd `want` and the pool silently
    # settles one short of its target on every run (a pool of 7 filled to 6).
    per_kind = max(1, -(-want // 2))
    chosen = sel.select_batches(shrines, temples, exclude, per_kind)[:want]

    if not dry_run:
        os.makedirs(OUTDIR, exist_ok=True)
        for item in chosen:
            _write_item(item)
    return len(chosen), len(outstanding)


def main():
    # Inside main(): rebinding at module scope replaces an importer's stdout and
    # breaks pytest capture. The wrapper is still needed -- Windows is cp1252.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description="Top up the en_label work-file pool.")
    ap.add_argument("--pool", type=int, default=DEFAULT_POOL,
                    help=f"Target outstanding work-files (default {DEFAULT_POOL}).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be written, write nothing.")
    args = ap.parse_args()

    written, already = build(pool=args.pool, dry_run=args.dry_run)
    verb = "would write" if args.dry_run else "wrote"
    print(f"en_label pool target {args.pool}: {already} already outstanding, "
          f"{verb} {written} new work-files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
