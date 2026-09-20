"""
staged_readings.py — readings this repo has STAGED but Wikidata has not landed yet.

The English-label worklists (``shrines_missing_en_label.json``,
``temples_missing_en_label.json``) carry a ``kana`` field read off Wikidata. A
reading that is sitting in one of our own atomic ``.txt`` files, waiting its turn
on the daily drip, is invisible to them — so Stage 1 sees no kana, emits nothing,
and the item falls through to Stage 2 or to the LLM.

Measured 2026-09-19: **296 shrines and 1,116 temples** in those worklists have an
NTA reading staged in ``nta_kana.txt`` and no kana on Wikidata. That is the exact
bottleneck ``ATOMIC_FILES`` already names —

    "the ~18,065-item English-label residual is blocked on READINGS, not on the
     romanization rule: generate_kana_en_labels.py turns kana into a label with
     no judgement and simply has nothing to turn."

— and the readings were in the repo the whole time.

## ⛔ Only registry-sourced readings, and the reason is circularity

``nta_kana.txt`` is a 宗教法人's legally registered フリガナ from the National Tax
Agency corporate-number registry. It is an external source, and the repo already
treats it as authoritative (Emma, 2026-08-24: an NTA-cited reading is preserved
where an uncited one is corrected).

The other two staged P1814 files are **DERIVED FROM THE ENGLISH LABEL**:

  * ``derived_name_in_kana.txt`` — "every shrine that has a ja label, an en label
    and no P1814 at all"
  * ``katakana_reading_add.txt`` — "derived by english_to_kana.kana_for from the
    English label"

Feeding either back into English-label generation would derive a label from a
reading that was derived from a label. Today it cannot happen — an item in those
files already HAS an en label, so it is not in a missing-en-label worklist, and
the measured overlap is **0 for both**. That is a property of how those files are
built, not a guarantee about how they will be built later, so the exclusion is
explicit rather than incidental.

## Why an unlanded reading is still safe to label from

The two statements are independent and both ADD-ONLY: ``Qx|P1814|"…"`` and
``Qx|Len|"…"``. Neither reads the other, so the random drip order cannot hurt
them — this is not the add-first/remove-later case, which exists because a
removal can fire before its add. The label is correct whether or not the kana
statement has landed yet, because both are derived from the same registered
reading.
"""

import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

# ⛔ One file, on purpose. See the circularity note above before adding another.
SOURCES = ("nta_kana.txt",)

_LINE = re.compile(r'^(Q\d+)\|P1814\|(?:[a-z-]+:)?"?([^"|]+)"?')


def load(sources=SOURCES, base=HERE):
    """{qid: kana} for every staged P1814 line, first occurrence winning."""
    out = {}
    for name in sources:
        path = os.path.join(base, name)
        if not os.path.exists(path):
            continue
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                m = _LINE.match(line.strip())
                if m:
                    out.setdefault(m.group(1), m.group(2).strip())
    return out


def fill(items, staged=None):
    """Fill an empty ``kana`` on each worklist item from the staged readings.

    Mutates ``items`` in place and returns how many were filled. An item that
    already carries kana from Wikidata is left alone — the live statement is
    what the rest of the pipeline is keyed to, and a staged line is at best the
    same value.
    """
    if staged is None:
        staged = load()
    filled = 0
    for item in items:
        if (item.get("kana") or "").strip():
            continue
        kana = staged.get(item.get("qid"))
        if kana:
            item["kana"] = kana
            filled += 1
    return filled
