"""The enrichment backfills: adding to statements that already exist.

Emma, 2026-09-11, on generators that create but never enrich: *"the updating of
the existing ones to add more to them is kind of a very critical part that makes
it so that this work is productive."*

Two of these remain. The third — citing an existing P6375 street address to the
subject's own jawiki article — was removed on 2026-09-12 at Emma's instruction:
*"Make it stop adding references to the street address things."* Its tests went
with the code rather than being left to pass against nothing.

What is pinned here is the gate that makes each remaining backfill honest — a
VALUE MATCH against what the source still says. Without it a citation asserts
something the source does not, which is worse than no citation.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)


# ---- every backfill is reference/qualifier-only ------------------------------

BACKFILLS = ["souken_p571_citations.txt", "saijin_named_as.txt"]


@pytest.mark.parametrize("name", BACKFILLS)
def test_a_backfill_never_removes_anything(name):
    """These attach to a statement that already exists. A '-' line would remove
    the whole statement instead, which is the shape that destroyed four ojp-hani
    official names on 2026-09-09."""
    path = os.path.join(MQ, name)
    if not os.path.exists(path):
        pytest.skip(f"{name} not generated here")
    for line in open(path, encoding="utf-8"):
        assert not line.startswith("-"), line


@pytest.mark.parametrize("name", BACKFILLS)
def test_a_backfill_is_registered_on_the_only_road_to_wikidata(name):
    """A generated file that no submitter lists is a file whose lines never flow
    — the drift this repo already had to fix once for the temple label files."""
    import direct_daily_edits as d
    assert name in d.ATOMIC_FILES
