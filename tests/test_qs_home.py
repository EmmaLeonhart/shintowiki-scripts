"""The home page is the QuickStatements batch (Emma 2026-09-28): every drip line and every
not-yet-done creation, shuffled, v1 tab-separated, with blocks that must stay together
kept together."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import build_qs_home as h  # noqa: E402


def test_pipes_become_tabs_but_not_inside_quotes():
    assert h.to_v1('Q1|P1448|ja:"a|b"|P3831|Q2') == 'Q1\tP1448\tja:"a|b"\tP3831\tQ2'
    assert h.to_v1("-Q1|P31|Q2") == "-Q1\tP31\tQ2"
    assert h.to_v1("Q1\tP31\tQ2") == "Q1\tP31\tQ2"


def test_blocks_stay_together_and_done_creations_are_left_out(tmp_path, monkeypatch):
    mq = tmp_path
    (mq / "direct_daily_edits.py").write_text('ATOMIC_FILES = [\n    "a.txt",\n    # "p.txt",\n]\n', encoding="utf-8")
    (mq / "create_items.py").write_text('GATES = {\n    "c.txt": "lockout_gate",\n}\n', encoding="utf-8")
    (mq / "a.txt").write_text('Q1|P31|Q2\nQ3|Den|"d"||Q3|Len|"l"\n', encoding="utf-8")
    (mq / "p.txt").write_text("Q9|P31|Q9\n", encoding="utf-8")
    (mq / "c.txt").write_text('CREATE\nLAST|Lja|"甲"\nLAST|P31|Q524158\nCREATE\nLAST|Lja|"乙"\nLAST|P31|Q524158\n', encoding="utf-8")
    (mq / "c.state").write_text(json.dumps({"甲": "Q100"}), encoding="utf-8")
    monkeypatch.setattr(h, "MQ", str(mq))
    lines, creates = h.build(seed=1)
    assert creates == 1                                   # 甲 is already created
    i = lines.index("CREATE")
    assert lines[i + 1:i + 3] == ['LAST\tLja\t"乙"', "LAST\tP31\tQ524158"]
    j = lines.index('Q3\tDen\t"d"')
    assert lines[j + 1] == 'Q3\tLen\t"l"'                  # description then label, adjacent
    assert "Q9\tP31\tQ9" not in lines                     # paused file excluded
