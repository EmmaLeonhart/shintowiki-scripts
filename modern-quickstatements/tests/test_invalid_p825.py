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
ROOT = "Q858308"              # 日本の文化財 — the root of the class she asked for


def test_the_honzon_generator_refuses_the_whole_class():
    """Emma chose a class over a list of QIDs — *Block the whole class instead*."""
    src = open(os.path.join(MQ, "generate_honzon_quickstatements.py"), encoding="utf-8").read()
    assert "INVALID_HONZON_ROOTS" in src, "the class gate is gone"
    assert ROOT in src, f"{ROOT} is no longer the blocked root"
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
    assert "INVALID_VALUE_ROOTS" in src
    assert ROOT in src
    assert "?v wdt:P279* wd:{root}" in src, (
        "the query no longer walks the subclass chain from the value")


def test_the_walk_is_subclass_only():
    """P31 must NOT be in the walk. `(P31|P279)/P279*` means "the value is an
    INSTANCE of a cultural property", which is true of every listed building —
    that version swept up Holy Sepulchre (31 statements), its church, Santa Maria
    sopra Minerva, Portiuncula and the Warsaw Ghetto. Churches genuinely are
    dedicated to the Holy Sepulchre; it would have deleted 42 correct statements."""
    # Match the QUERY, not the prose — both docstrings quote the broken version
    # to explain why it was wrong, and an earlier draft of this test failed on
    # its own explanation.
    rm = open(os.path.join(MQ, "generate_invalid_p825_removals.py"), encoding="utf-8").read()
    query = rm[rm.index("rows = wdqs("):rm.index("return sorted({(b[")]
    assert "wdt:P31" not in query, "the removal query reintroduced the P31 leg"
    assert "?v wdt:P279* wd:{root}" in query

    hz = open(os.path.join(MQ, "generate_honzon_quickstatements.py"), encoding="utf-8").read()
    assert 'for prop in ("P279",):' in hz, "the client-side walk follows P31 again"


def test_the_root_itself_is_blocked():
    """`P279*` includes zero steps. The first client-side walk only inspected
    parents, so Q858308 — which IS the root — was let through."""
    hz = open(os.path.join(MQ, "generate_honzon_quickstatements.py"), encoding="utf-8").read()
    assert "blocked = {q for q in qids if q in INVALID_HONZON_ROOTS}" in hz


def test_classes_holding_real_honzon_are_not_blocked():
    """Measured 2026-09-12 over all 118 values the honzon generator emits. Each of
    these holds a legitimate honzon — 曼荼羅, 仏舎利, Nichiren's own 大曼荼羅,
    地蔵菩薩 — so blocking them would drop real data to catch a designation."""
    src = open(os.path.join(MQ, "generate_invalid_p825_removals.py"), encoding="utf-8").read()
    block = src[src.index("INVALID_VALUE_ROOTS = {"):]
    block = block[:block.index("}")]
    for cls, why in (("Q23847174", "religious concept"), ("Q80071", "symbol"),
                     ("Q838948", "work of art"), ("Q3658341", "literary character"),
                     ("Q2065736", "cultural property — too wide, takes dolmen"),
                     ("Q30634609", "heritage designation — too narrow, misses 2 of 4")):
        assert cls not in block, f"{cls} ({why}) must not be the root"

def test_the_staged_honzon_file_agrees_with_the_shipped_gate():
    """The file and the gate drifted once and it shipped.

    On 2026-09-12 the staged lines were stripped using the narrow P31 rule, the
    rule was then widened to the P279 chain, and the file was never re-stripped —
    so 16 lines the shipped gate refuses (Q858308 ×15, Q2901860 ×1) sat in a file
    the drip samples daily. Stripping and widening are two steps and the second
    one silently invalidates the first.

    This compares the FILE against the gate's own root set rather than a
    hand-written list, so widening the gate again cannot leave the file behind
    without turning this red.
    """
    # `generate_honzon_quickstatements` does `from infobox_fields import ...`,
    # a sibling-module import that only resolves with modern-quickstatements on
    # sys.path. Without this the test passes when pytest is run from that
    # directory and fails from the repo root — which is how CI runs it.
    import importlib.util
    import sys as _sys
    if MQ not in _sys.path:
        _sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_gen_honzon", os.path.join(MQ, "generate_honzon_quickstatements.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    path = os.path.join(MQ, "honzon_p825.txt")
    if not os.path.exists(path):
        import pytest
        pytest.skip("not generated in this checkout")
    staged = set()
    for line in open(path, encoding="utf-8"):
        parts = line.split("|")
        if len(parts) > 2 and parts[2].startswith("Q"):
            staged.add(parts[2])
    roots = mod.INVALID_HONZON_ROOTS & staged
    assert not roots, (
        f"the staged file contains blocked roots the gate refuses: {sorted(roots)} — "
        "re-strip it after widening the gate")


def test_the_removal_generator_actually_runs_in_ci():
    """Its docstring promises it re-derives from live Wikidata each run and goes
    inert once the statements are gone. That promise is false unless something
    runs it — and for the first several commits of its life, nothing did. A
    removal batch that never regenerates keeps re-attempting deletions already
    applied and never notices new ones."""
    wf = os.path.normpath(os.path.join(MQ, "..", ".github", "workflows",
                                       "generate-quickstatements.yml"))
    text = open(wf, encoding="utf-8").read()
    assert "generate_invalid_p825_removals.py" in text, (
        "the removals generator is not wired into generate-quickstatements.yml, so "
        "its file is a frozen snapshot")
    assert "generate_ronsha_role_qualifiers.py" in text, (
        "the ronsha role generator is not wired in either")
