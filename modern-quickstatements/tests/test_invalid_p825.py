"""P825 -> Q1188622 must never be emitted, and the removals must stay removals.

Emma, 2026-09-12: "a completely invalid thing and we should never add it and
should universally remove it from all items it is present on."

P825 is "dedicated to" — a deity. Q1188622 is 重要文化財, Important Cultural
Property of Japan: a designation awarded to an object. It reached Wikidata
because `generate_honzon_quickstatements.py` takes every wikilink out of the
jawiki 本尊 field and temple infoboxes write

    |本尊 = [[阿弥陀如来]]（[[重要文化財]]）

so the designation parses as a second honzon. It was the second most-emitted
value in honzon_p825.txt — 100 of 973 lines — and 12 statements had landed.

Two things are pinned: the generator refuses it, and no batch in this directory
adds it back. The second is the one that catches a regression from somewhere
other than the honzon generator.
"""

import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

INVALID = "Q1188622"          # 重要文化財, the one Emma named
HERITAGE_CLASS = "Q30634609"  # the class she then asked for instead


def test_the_honzon_generator_refuses_the_whole_class():
    """Emma chose a class over a list of QIDs — *Block the whole class instead*."""
    src = open(os.path.join(MQ, "generate_honzon_quickstatements.py"), encoding="utf-8").read()
    assert "INVALID_HONZON_CLASSES" in src, "the class gate is gone"
    assert HERITAGE_CLASS in src, f"{HERITAGE_CLASS} is no longer blocked"
    assert "if d in refused:" in src, (
        "the gate exists but nothing consults it in the emit loop")
    assert "def refused_classes(" in src


def test_no_batch_adds_it():
    """An ADD line anywhere in the directory. A removal line ('-Q…') is fine and
    is the whole point of invalid_p825_removals.txt."""
    offenders = []
    for path in glob.glob(os.path.join(MQ, "*.txt")):
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            line = line.strip()
            if line.startswith("-") or not line:
                continue
            if f"|P825|{INVALID}" in line:
                offenders.append(f"{os.path.basename(path)}:{i}")
    assert not offenders, f"these ADD the invalid statement: {offenders[:5]}"


def test_the_removal_batch_is_removal_only():
    path = os.path.join(MQ, "invalid_p825_removals.txt")
    if not os.path.exists(path):
        import pytest
        pytest.skip("not generated in this checkout")
    lines = [ln.strip() for ln in open(path, encoding="utf-8") if ln.strip()]
    for ln in lines:
        assert re.match(r"^-Q\d+\|P825\|Q\d+$", ln), f"not a bare removal line: {ln}"



def test_the_removal_generator_works_by_class_not_by_qid():
    """A QID list would have missed Q1139795, which is exactly what happened
    before she said to block the class: the QID version found 12 statements, the
    class version found 16."""
    src = open(os.path.join(MQ, "generate_invalid_p825_removals.py"), encoding="utf-8").read()
    assert "INVALID_VALUE_CLASSES" in src
    assert HERITAGE_CLASS in src
    assert "?v wdt:P31 wd:{cls}" in src, (
        "the query no longer filters by the VALUE's class")


def test_classes_holding_real_honzon_are_not_blocked():
    """Measured 2026-09-12 over all 118 values the honzon generator emits. Each of
    these holds a legitimate honzon — 曼荼羅, 仏舎利, Nichiren's own 大曼荼羅,
    地蔵菩薩 — so blocking them would drop real data to catch a designation."""
    src = open(os.path.join(MQ, "generate_invalid_p825_removals.py"), encoding="utf-8").read()
    block = src[src.index("INVALID_VALUE_CLASSES = {"):]
    block = block[:block.index("}")]
    for cls, why in (("Q23847174", "religious concept"), ("Q80071", "symbol"),
                     ("Q838948", "work of art"), ("Q3658341", "literary character")):
        assert cls not in block, f"{cls} ({why}) contains real honzon and must not be blocked"
