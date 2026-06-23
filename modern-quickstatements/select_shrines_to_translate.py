"""
select_shrines_to_translate.py
==============================
Pick the daily residual for the remote Sonnet translator (Stage 4) to label, as
JSON on stdout. Covers BOTH worklists:

  - Shinto shrines   (``shrines_missing_en_label.json``)
  - Japanese Buddhist temples (``temples_missing_en_label.json``, P31=Q5393308 +
    P17=Q17 — Japan only, so the Japanese -> English naming rules apply)

Up to ``--count`` shrines AND up to ``--count`` temples are returned (so adding
temples never starves the shrine queue), each tagged with ``"kind"``
("shrine"/"temple") so the translator can apply the right convention — temples
use Emma's ``"<Stem>-<suffix> Temple"`` form. The remote routine translates every
item it is handed; no cloud-side change is needed to start covering temples.

No state file — statefulness is purely presence-based: an item is excluded if its
QID already has a line in ANY of the deterministic / pending en-label files, so
the LLM only ever sees the genuine residual:

  - ``en_labels.txt``                — Stage 0, wiki-title lookup
  - ``kana_en_labels.txt``           — Stage 1, deterministic kana (shrines)
  - ``temple_en_labels.txt``         — Stage 1, deterministic kana (temples)
  - ``identical_name_en_labels.txt`` — Stage 2, identical-name reuse
  - ``en_labels_sonnet.txt``         — already LLM-translated, not yet submitted

Once a label lands on Wikidata, the next 24h SPARQL refresh drops the item from
its worklist — a self-draining progressive queue that never re-translates an item
an earlier stage (or a previous LLM run) already handled. New temples added to
Wikidata appear in the next refresh and flow through automatically.

Usage:
    python select_shrines_to_translate.py [--count N]
Output (stdout):
    [{"qid": "Q123", "ja": "四所神社", "kana": "...", "kind": "shrine"},
     {"qid": "Q9", "ja": "金閣寺", "kana": "きんかくじ", "kind": "temple"}, ...]
"""

import argparse
import io
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKLIST = os.path.join(HERE, "shrines_missing_en_label.json")
TEMPLE_WORKLIST = os.path.join(HERE, "temples_missing_en_label.json")
QID_RE = re.compile(r"^(Q\d+)\|", re.MULTILINE)

# Every file that already supplies (or will supply) an en label for a QID; the
# LLM must skip all of these so it only translates the true residual.
EXCLUDE_FILES = [
    "en_labels_sonnet.txt",
    "en_labels.txt",
    "kana_en_labels.txt",
    "temple_en_labels.txt",
    "identical_name_en_labels.txt",
    "temple_identical_name_en_labels.txt",
]


def excluded_qids(files=EXCLUDE_FILES, base=HERE):
    """QIDs already covered by any deterministic/pending en-label file."""
    out = set()
    for name in files:
        path = os.path.join(base, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                out |= set(QID_RE.findall(f.read()))
    return out


def select(items, exclude, count, rng=random):
    """Pick up to ``count`` worklist items whose QID isn't excluded."""
    candidates = [it for it in items if it.get("qid") not in exclude]
    return rng.sample(candidates, min(count, len(candidates))) if candidates else []


def _tagged(items, kind):
    return [{**it, "kind": kind} for it in items]


def select_batches(shrine_items, temple_items, exclude, count, rng=random):
    """Up to ``count`` shrines + up to ``count`` temples, each kind-tagged.

    Separate batches so adding temples never reduces the shrine quota.
    """
    return (_tagged(select(shrine_items, exclude, count, rng), "shrine")
            + _tagged(select(temple_items, exclude, count, rng), "temple"))


def _load_items(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("items", [])


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=5, help="Max per kind (default 5).")
    args = ap.parse_args()

    chosen = select_batches(
        _load_items(WORKLIST),
        _load_items(TEMPLE_WORKLIST),
        excluded_qids(),
        args.count,
    )
    print(json.dumps(chosen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
