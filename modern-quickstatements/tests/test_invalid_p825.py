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

INVALID = "Q1188622"


def test_the_honzon_generator_refuses_it():
    src = open(os.path.join(MQ, "generate_honzon_quickstatements.py"), encoding="utf-8").read()
    assert "INVALID_HONZON" in src, "the blocklist is gone"
    assert INVALID in src, f"{INVALID} is no longer in the honzon blocklist"
    assert "if d in INVALID_HONZON:" in src, (
        "the blocklist exists but nothing consults it in the emit loop")


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
        assert ln.split("|")[2] == INVALID or ln.split("|")[2] in _declared_values(), (
            f"removes a value nobody ruled invalid: {ln}")


def _declared_values():
    src = open(os.path.join(MQ, "generate_invalid_p825_removals.py"), encoding="utf-8").read()
    block = src[src.index("INVALID_VALUES = {"):]
    block = block[:block.index("}")]
    return set(re.findall(r'"(Q\d+)"', block))


def test_only_values_emma_ruled_on_are_removed():
    """The removal generator must not grow entries on a session's own judgement.
    Q1139795 (National Treasure) and Q11595955 (hibutsu) are the same shape and
    are deliberately absent — she named one QID."""
    assert _declared_values() == {INVALID}, (
        "INVALID_VALUES changed; every entry needs Emma's word, not a session's "
        "reading that something looks wrong")
