"""prune_landed_lines removes only lines the drip could not change anything with.

A line is pruned only when its value, every qualifier and every reference are all
on one live statement. Anything else, including anything it cannot compare, is kept.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import prune_landed_lines as P  # noqa: E402

LINE = 'Q1|P612|Q2|P1013|Q195793|S854|"https://example.org/x"'


def st(v, quals=(), refs=()):
    return {"v": v, "quals": set(quals), "refs": set(refs)}


def test_fully_landed_needs_value_qualifier_and_reference():
    p = P.parse(LINE)
    live = {("Q1", "P612"): [st("Q2", [("P1013", "Q195793")], [("P854", "https://example.org/x")])]}
    assert P.fully_landed(p, live)


def test_value_without_its_qualifier_is_kept():
    p = P.parse(LINE)
    live = {("Q1", "P612"): [st("Q2", [], [("P854", "https://example.org/x")])]}
    assert not P.fully_landed(p, live)


def test_value_without_its_reference_is_kept():
    p = P.parse(LINE)
    live = {("Q1", "P612"): [st("Q2", [("P1013", "Q195793")], [])]}
    assert not P.fully_landed(p, live)


def test_qualifier_and_reference_must_be_on_the_same_statement():
    p = P.parse(LINE)
    live = {("Q1", "P612"): [st("Q2", [("P1013", "Q195793")]), st("Q2", [], [("P854", "https://example.org/x")])]}
    assert not P.fully_landed(p, live)


def test_label_line():
    p = P.parse('Q5|Len|"Kamo Shrine"')
    assert P.fully_landed(p, {("Q5", "Len"): "Kamo Shrine"})
    assert not P.fully_landed(p, {("Q5", "Len"): "Kamo Jinja"})


def test_uncomparable_and_removal_lines_are_not_parsed():
    assert P.parse("Q1|P571|+1200-00-00T00:00:00Z/9") is None
    assert P.parse("-Q1|P31|Q2") is None
    assert P.parse("# comment") is None


def test_apply_removes_only_listed_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "HERE", str(tmp_path))
    monkeypatch.setattr(P, "STATE", str(tmp_path / "landed_lines.json"))
    (tmp_path / "reisai.txt").write_text("a\nb\nc\n", encoding="utf-8")
    (tmp_path / "landed_lines.json").write_text(json.dumps({"reisai.txt": ["b"]}), encoding="utf-8")
    P.apply()
    assert (tmp_path / "reisai.txt").read_text(encoding="utf-8") == "a\nc\n"


def test_every_static_file_is_a_real_drip_file():
    os.environ.setdefault("WIKIDATA_EMAIL", "test@example.org")
    os.environ.setdefault("MIRAHEZE_EMAIL", "test@example.org")
    import direct_daily_edits as d
    for fn in P.STATIC_FILES:
        assert fn in d.ATOMIC_FILES, fn
