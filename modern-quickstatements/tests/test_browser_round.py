"""Browser rounds must be able to reach 0 lines (Emma, 2026-10-09: "Fix both so it can hit 0")."""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, "site"), HERE]
import build_qs_home  # noqa: E402
import build_browser_round as bbr  # noqa: E402


def test_sequential_unit_sends_only_lines_past_the_cursor(tmp_path, monkeypatch):
    monkeypatch.setattr(build_qs_home, "sequential_lines", lambda: ["Q1|P1|Q2", "Q3|P1|Q4", "Q5|P1|Q6"])
    state = tmp_path / "sequential_misc.state"
    monkeypatch.setattr(build_qs_home, "MQ", str(tmp_path))
    state.write_text(json.dumps({"cursor": 2}), encoding="utf-8")
    assert build_qs_home.sequential_unit() == [["Q5\tP1\tQ6"]]
    state.write_text(json.dumps({"cursor": 3}), encoding="utf-8")
    assert build_qs_home.sequential_unit() == []          # all run: nothing goes out


def test_finished_round_advances_the_cursor_never_backwards(tmp_path, monkeypatch):
    lines = ["Q1|P1|Q2", "Q3|P1|Q4", "Q5|P1|Q6"]
    monkeypatch.setattr(build_qs_home, "sequential_lines", lambda: lines)
    monkeypatch.setattr(build_qs_home, "MQ", str(tmp_path))
    state = tmp_path / "sequential_misc.state"
    state.write_text(json.dumps({"cursor": 1}), encoding="utf-8")
    sent = tmp_path / "sent.json"
    sent.write_text(json.dumps({"through": 3}), encoding="utf-8")
    monkeypatch.setattr(bbr, "SENT", str(sent))
    monkeypatch.setattr(bbr, "STATE", str(state))
    bbr.advance_sequential_cursor()
    assert build_qs_home.sequential_cursor(lines) == 3
    sent.write_text(json.dumps({"through": 1}), encoding="utf-8")
    bbr.advance_sequential_cursor()
    assert build_qs_home.sequential_cursor(lines) == 3    # never backwards


def test_merged_items_are_retargeted(tmp_path, monkeypatch):
    """Emma, 2026-10-09: "the merged ones we retarget"."""
    monkeypatch.setattr(bbr, "REDIRECTS", str(tmp_path / "redirects.json"))
    r = bbr.record_redirects({"Q2": "Q20"})
    units = [
        ["Q2\tP973\t\"https://x\"", 'Q2\tLen\t"Old"'],    # statement moves, label stays out
        ["-Q2\tP361\tQ7"],                                 # removals move too
        ['Q2\tLen\t"Old"'],                                # a unit left empty is dropped
        ["Q1\tP31\tQ5", 'Q3\tLen\t"Taken"'],              # everything else untouched
    ]
    assert bbr.apply_redirects(units, r) == [
        ["Q20\tP973\t\"https://x\""],
        ["-Q20\tP361\tQ7"],
        ["Q1\tP31\tQ5", 'Q3\tLen\t"Taken"'],
    ]
    assert bbr.record_redirects({"Q9": "Q90"}) == {"Q2": "Q20", "Q9": "Q90"}
