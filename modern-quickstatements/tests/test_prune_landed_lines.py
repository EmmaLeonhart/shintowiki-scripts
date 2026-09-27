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


def _state(tmp_path, monkeypatch, data):
    monkeypatch.setattr(P, "STATE", str(tmp_path / "landed_lines.json"))
    (tmp_path / "landed_lines.json").write_text(json.dumps(data), encoding="utf-8")


def test_refresh_is_weekly_not_every_run(tmp_path, monkeypatch):
    import datetime as dt
    _state(tmp_path, monkeypatch, {"_refreshed": "2026-09-27"})
    assert not P.refresh_due(dt.date(2026, 9, 28))
    assert P.refresh_due(dt.date(2026, 10, 3))


def test_a_refresh_already_attempted_today_is_not_retried(tmp_path, monkeypatch):
    import datetime as dt
    _state(tmp_path, monkeypatch, {"_refreshed": "2026-09-01", "_attempted": "2026-10-04"})
    assert not P.refresh_due(dt.date(2026, 10, 4))
    assert P.refresh_due(dt.date(2026, 10, 5))


def test_a_refresh_that_bails_still_prunes_with_the_old_list(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "HERE", str(tmp_path))
    _state(tmp_path, monkeypatch, {"reisai.txt": ["b"]})
    (tmp_path / "reisai.txt").write_text("a\nb\n", encoding="utf-8")

    def _bail():
        raise SystemExit(2)                     # what a WDQS 429 does

    monkeypatch.setattr(P, "refresh", _bail)
    monkeypatch.setattr(sys, "argv", ["prune_landed_lines.py", "--refresh"])
    P.main()
    assert (tmp_path / "reisai.txt").read_text(encoding="utf-8") == "a\n"
    assert "_attempted" in json.loads((tmp_path / "landed_lines.json").read_text(encoding="utf-8"))
