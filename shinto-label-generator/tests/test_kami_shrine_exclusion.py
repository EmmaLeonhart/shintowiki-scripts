"""Regression: a kami that also carries a shrine class on Wikidata must get its
bare transliterated name (from the kami generator), NOT a "X Shrine" affix from
the shrine pipeline.

Emma 2026-07-04 on Q10928586 (座摩神 / Ikasuri no Kami): "just the transliteration
everywhere". Toki Pona is the one language forced off the plain transliteration —
label "jan sewi Ikasuli" (deity classifier), alias "tomo sewi Ikasuli".
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import EXCLUDE_QIDS  # noqa: E402

QID = "Q10928586"
_QS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "quickstatements")
_CATEGORY = {
    "kami_labels.txt", "buddhist_deity_labels.txt", "province_labels.txt",
    "human_labels.txt", "text_labels.txt", "misc_term_labels.txt",
    "shikinaisha_lists.txt", "courtrank_labels.txt", "courtrank_translations.txt",
    "concept_translations.txt", "property_translations.txt", "manual_overrides.txt",
}


def test_kami_excluded_from_shrine_pipeline():
    assert QID in EXCLUDE_QIDS


def test_no_shrine_affixed_label_in_per_language_files():
    """No per-language shrine file (*.txt that isn't a category/override file) may
    carry a label for the excluded kami — those were the affixed 'X Shrine' lines."""
    offenders = []
    for name in os.listdir(_QS):
        if not name.endswith(".txt") or name in _CATEGORY:
            continue
        with open(os.path.join(_QS, name), encoding="utf-8") as f:
            if any(line.startswith(QID + "\t") for line in f):
                offenders.append(name)
    assert not offenders, f"{QID} still labelled in per-language shrine files: {offenders}"


def test_tok_override_label_and_alias_present():
    path = os.path.join(_QS, "manual_overrides.txt")
    body = open(path, encoding="utf-8").read()
    assert f'{QID}\tLtok\t"jan sewi Ikasuli"' in body   # deity classifier = label
    assert f'{QID}\tAtok\t"tomo sewi Ikasuli"' in body  # shrine sense = alias
