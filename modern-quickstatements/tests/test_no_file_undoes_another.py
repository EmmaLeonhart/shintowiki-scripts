"""Two atomic files must not stage the same statement both ways.

The drip samples ATOMIC_FILES at random, so a triple that one file adds and another
removes is a coin toss — and worse than a coin toss, because both generators
re-derive from live Wikidata every build and therefore re-queue whichever side just
lost. That is a permanent oscillation, two edits a cycle.

**It is not hypothetical here.** `direct_daily_edits.execute_line` resolves the claim
with `find_claim(...)` and then, at lines 823-825, **creates it if it is missing**. So

    Q10896675|P1448|ojp-hani:"出雲神社"|P1814|"イツモノカミノヤシロ"

does not merely fail to decorate a deleted statement — it RE-CREATES the ojp-hani
official name that `ronsha_ojp_name_removals.txt` deliberately deleted, stripped of
its references and its P1264.

Measured 2026-09-13: **2,564 (item, property, value) triples were staged both ways**,
1,734 items in that one pair. Sampled 20 of them against live Wikidata — every name
still present, with references and P1264 — so nothing had been damaged yet; the
removals had not reached them. The add generator now skips a name queued for removal,
which took it to 761.

⭐ THE 761 THAT REMAIN ARE DELIBERATE and must not be "fixed". Emma, on collapsed
membership: *"every single membership thing on those items should be removed unless
the membership of the Shikinaisha list is 100% accurate and is 100% what we want. We
remove it and then we add it again."* `list_membership_rebuild.txt` against
`orphan_membership_removals.txt` is that instruction, and `_remove` is ADD-only and
diffed against live state, so it shrinks as it lands either way round.

So this test does not ban collisions. It bans NEW ones: the pairs below are the known
set, and anything outside it is a file quietly undoing another.
"""

import importlib.util
import io
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

# (adding file, removing file) -> why it is intended.
INTENDED = {
    ("list_membership_rebuild.txt", "orphan_membership_removals.txt"):
        "Emma's remove-then-re-add for collapsed membership. The rebuild is ADD-only "
        "and diffed against live state, so it shrinks as it lands whichever order "
        "the drip picks.",
    ("list_membership_rebuild.txt", "multi_ordinal_removals.txt"):
        "Same instruction, the multi-ordinal half of it.",
    ("address_citation_from_article.txt", "miscellaneous_edits.txt"):
        "Hand-written one-offs in miscellaneous_edits that predate the citation "
        "backfill; five triples, measured 2026-09-13.",
}


def _atomic_files():
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_dde_clash", os.path.join(MQ, "direct_daily_edits.py"))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return sorted(mod.ATOMIC_FILES)


def _staged():
    """({triple: [where]} added, {triple: [where]} removed)."""
    adds, removes = {}, {}
    for name in _atomic_files():
        path = os.path.join(MQ, name)
        if not os.path.exists(path):
            continue
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                neg = line.startswith("-")
                parts = (line[1:] if neg else line).split("|")
                if len(parts) < 3 or not re.match(r"^Q\d+$", parts[0]):
                    continue
                (removes if neg else adds).setdefault(
                    tuple(parts[:3]), []).append(name)
    return adds, removes


def test_no_unexpected_pair_of_files_stages_a_triple_both_ways():
    adds, removes = _staged()
    unexpected = collections.Counter()
    for triple in set(adds) & set(removes):
        for a in set(adds[triple]):
            for r in set(removes[triple]):
                if (a, r) not in INTENDED:
                    unexpected[(a, r)] += 1
    assert not unexpected, (
        "these file pairs stage the same statement both ways, and the drip runs them "
        "in random order — the add re-creates what the remove deleted, and both "
        f"generators re-queue next build: {dict(unexpected)}")


def test_the_kana_add_skips_a_name_queued_for_removal():
    """The 1,734-item collision this test was written for. If the skip goes, the
    oscillation comes back."""
    src = open(os.path.join(MQ, "generate_kana_qualifier_add.py"), encoding="utf-8").read()
    assert "def names_queued_for_removal(" in src
    assert src.count("in doomed:") == 2, (
        "both the APPEND and the MOVE pass must consult it; one of them does not")


def test_the_intended_list_is_not_a_dumping_ground():
    """Every entry is an exemption from 'do not undo another file'. If it grows, the
    growth is the thing to look at."""
    assert len(INTENDED) <= 5, f"{len(INTENDED)} intended collision pairs is too many"
    for pair, why in INTENDED.items():
        assert len(why) > 40, f"{pair} is exempted without a real reason"
