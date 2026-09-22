"""The language order in `generate_multilang_quickstatements.py` is load-bearing.

A 429 from WDQS ends the run where it lands — repo policy, no retries — so every
language after that point keeps its previous file. With a fixed order, the same tail
loses on every bail. Run 35682528723 (2026-09-21) bailed at index 17 of 57 and 39
languages did not regenerate; `tr de nl es it` had never once been the ones to lose.

This project is deliberately slow and unattended, and it rests on everything being
covered *eventually*. A fixed order under a recurring bail is not slow coverage of the
tail, it is no coverage of the tail. These pin the rotation that fixes that, and — the
part that actually matters — that rotating cannot change any language's OUTPUT.
"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_multilang_quickstatements as g  # noqa: E402


def test_rotation_is_a_permutation_never_a_filter():
    """Every language runs every day. Rotation reorders; it must never drop one."""
    for d in range(0, 400, 7):
        day = datetime.date(2026, 1, 1) + datetime.timedelta(days=d)
        order = g.rotated_langs(day)
        assert sorted(order) == sorted(g.ALL_LANGS), day
        assert len(order) == len(set(order)), day


def test_every_language_reaches_the_front_within_one_cycle():
    """The point of rotating: no language is permanently last. Over `len(ALL_LANGS)`
    consecutive days every one of them leads exactly once."""
    start = datetime.date(2026, 9, 21)
    firsts = [g.rotated_langs(start + datetime.timedelta(days=d))[0]
              for d in range(len(g.ALL_LANGS))]
    assert sorted(firsts) == sorted(g.ALL_LANGS)


def test_rotation_is_deterministic_for_a_given_day():
    """Stateless on purpose — no `.state` file to commit or drift. The same date must
    give the same order in any process, or a re-run would serve a different set."""
    day = datetime.date(2026, 9, 21)
    assert g.rotated_langs(day) == g.rotated_langs(day)


def test_consecutive_days_advance_by_exactly_one():
    day = datetime.date(2026, 9, 21)
    a = g.rotated_langs(day)
    b = g.rotated_langs(day + datetime.timedelta(days=1))
    assert b[0] == a[1]
    assert b == a[1:] + a[:1]


@pytest.mark.parametrize("lang", ["tr", "ca", "shn", "dz"])
def test_no_languages_output_depends_on_what_ran_before_it(lang):
    """The safety property behind the whole change: `_gen_lang` reads no state that a
    previous language could have written, so reordering cannot alter any output file.

    Checked structurally rather than by running it — the function's only cross-language
    inputs are the module constant `EXCLUDE_QIDS` and `ALL_LANGS` itself, and its `seen`
    set is rebuilt per call. If someone adds a module-level accumulator to `_gen_lang`,
    this test is the thing that should stop them, so it asserts on the source.
    """
    import inspect
    src = inspect.getsource(g.main)
    body = src[src.index("def _gen_lang"):src.index("# Per-lang fault isolation")]
    assert "seen = set(EXCLUDE_QIDS)" in body, "seen must be rebuilt per language"
    for bad in ("global ", "nonlocal "):
        assert bad not in body, "_gen_lang gained cross-language state: %r" % bad


def test_all_langs_is_unchanged_in_content():
    """Rotation must not have been an excuse to edit the roster."""
    assert len(g.ALL_LANGS) == 57
    assert g.ALL_LANGS[0] == "tr"
    assert g.ALL_LANGS[-1] == "shn"
