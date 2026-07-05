"""Whitespace hygiene for generated labels (2026-07-04 audit).

Source Wikidata en/id labels sometimes carry stray ASCII double-spaces (often left
by parenthetical removal) or web-copy artifacts — non-breaking space U+00A0 and
narrow no-break space U+202F. These leaked verbatim into ~1,900 generated labels.
The extract steps now collapse those to a single ASCII space and strip the ends.

Deliberately NOT normalised: the ideographic space U+3000, which is a legitimate
separator inside CJK compound-shrine labels (甲埜神社　諏訪神社　合殿) — collapsing it
to an ASCII space is a style change, not a fix, so it is left alone.
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_multilang_quickstatements import extract_name, extract_name_from_en  # noqa: E402


# ── Unit: extraction collapses stray whitespace at the source ──

def test_en_extraction_collapses_double_space():
    name, _, _ = extract_name_from_en(
        "Katsuraki Shitori ni Imasu  Ame no Ha Ikazuchi no Mikoto Shrine")
    assert name == "Katsuraki Shitori ni Imasu Ame no Ha Ikazuchi no Mikoto"


def test_en_extraction_paren_removal_leaves_no_double_space():
    # removing "(bar)" would leave "Foo  Shrine" -> must collapse before suffix strip
    assert extract_name_from_en("Foo (bar) Shrine")[0] == "Foo"


def test_id_extraction_collapses_nbsp():
    # a non-breaking space between name parts must become a plain space
    assert extract_name("Kuil Wakamiya Hachiman")[0] == "Wakamiya Hachiman"


# ── File invariant: no committed label/alias carries forbidden whitespace ──
# Forbidden: ASCII double-space, leading/trailing whitespace, U+00A0, U+202F.
# Allowed: single ASCII spaces, and internal U+3000 (CJK).

_QS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "quickstatements")
_FORBIDDEN = ("  ", " ", " ")


def test_no_committed_label_has_forbidden_whitespace():
    bad = []
    for path in glob.glob(os.path.join(_QS, "*.txt")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3 or not parts[1].startswith(("L", "A")):
                    continue
                v = parts[2].strip('"')
                if v != v.strip() or any(tok in v for tok in _FORBIDDEN):
                    bad.append((os.path.basename(path), parts[0], parts[1], repr(v)))
    assert not bad, f"{len(bad)} labels with forbidden whitespace; e.g. {bad[:5]}"
