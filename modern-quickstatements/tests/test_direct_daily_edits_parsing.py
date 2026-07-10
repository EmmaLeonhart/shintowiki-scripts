"""Parsing invariants for the one Wikidata editor.

The load-bearing fact these pin: a registered atomic file whose lines parse to None is
SILENTLY skipped — the executor just drops it. That is how `remove_junk_aliases.txt`
(alias removals the fallback refuses) and the two tab-separated family-relation files
sat dead for weeks. These tests keep the tab format and comment handling working, and
assert that every currently-registered file has at least one executable line.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import direct_daily_edits as d  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────── tab-separated QuickStatements v1 ───────────────────

def test_a_tab_separated_line_parses():
    """QS v1 is canonically tab-separated; recreate-deleted-wikidata emits it."""
    p = d.parse_qs_line("Q140446068\tP40\tQ140446069")
    assert p is not None
    assert p["entity"] == "Q140446068" and p["property"] == "P40"
    assert p["value"]["value"]["id"] == "Q140446069"
    assert not p["is_removal"]


def test_tab_and_pipe_forms_parse_identically():
    tab = d.parse_qs_line("Q1\tP40\tQ2")
    pipe = d.parse_qs_line("Q1|P40|Q2")
    assert tab == pipe


def test_a_pipe_line_is_untouched_by_the_tab_rule():
    """A pipe-form value may legitimately contain a tab; the rule must not fire on it."""
    p = d.parse_qs_line('Q1|P6375|ja:"a\tb"')
    assert p is not None and p["property"] == "P6375"
    assert p["value"]["value"]["text"] == "a\tb"


def test_a_tab_removal_line_parses_as_a_removal():
    p = d.parse_qs_line("-Q1\tP40\tQ2")
    assert p is not None and p["is_removal"]
    assert p["entity"] == "Q1" and p["property"] == "P40"


def test_a_tab_qualifier_line_parses():
    p = d.parse_qs_line('Q1\tP527\tQ2\tP1545\t"7"')
    assert p is not None
    quals = dict(p["qualifiers"])
    assert quals["P1545"]["value"] == "7"


# ─────────────────── comment lines ───────────────────

def test_a_comment_line_is_skipped():
    assert d.parse_qs_line("# Deferred family relations …") is None


def test_a_blank_line_is_skipped():
    assert d.parse_qs_line("   ") is None


# ─────────────────── no registered file is dead ───────────────────

def _executable(p):
    """Would execute_line attempt a real API call for this parsed line?"""
    if p is None:
        return False
    if p.get("term_kind"):
        return not p["is_removal"]          # the fallback refuses term removals
    return True


def test_every_registered_file_has_an_executable_line():
    """A file all of whose lines are None / term-removals never runs — the dead-batch bug."""
    dead = []
    for f in d.ATOMIC_FILES:
        path = os.path.join(HERE, f)
        if not os.path.exists(path):
            continue
        lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
        if not lines:
            continue
        if not any(_executable(d.parse_qs_line(l)) for l in lines):
            dead.append(f)
    assert dead == [], "registered but non-executable: {}".format(dead)


def test_the_two_tab_files_now_execute():
    for f in ("recreation_relations.txt", "durability_backlinks.txt"):
        path = os.path.join(HERE, f)
        if not os.path.exists(path):
            continue
        lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
        parsed = [d.parse_qs_line(l) for l in lines]
        assert any(_executable(p) for p in parsed), f
        # only comment lines are allowed to drop out
        for l, p in zip(lines, parsed):
            assert p is not None or l.startswith("#"), (f, l)
