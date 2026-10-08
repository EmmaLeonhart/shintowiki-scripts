"""Inochi Shrine (Q141677508): deity create + date-gated labels (Emma, 2026-10-08)."""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import generate_inochi_shrine as g  # noqa: E402

BEFORE = datetime.date(2026, 10, 21)
ON = datetime.date(2026, 10, 22)


def test_deity_block_until_the_shrine_has_p825():
    creates, _ = g.build({}, False, BEFORE)
    assert creates[0] == "CREATE"
    assert 'LAST|Lja|"命之命"' in creates and 'LAST|Len|"Inochi no Mikoto"' in creates
    assert "LAST|P31|Q524158" in creates and "LAST|P21|Q6581097" in creates
    assert "Q141677508|P825|LAST" in creates
    assert g.build({}, True, BEFORE)[0] == []          # created: never again


def test_labels_wait_two_weeks_and_only_when_different():
    assert g.build({"en": "x"}, True, BEFORE)[1] == []
    lines = g.build({"en": "Inochi-jinja", "ja": "命神社"}, True, ON)[1]
    assert lines == ['Q141677508|Len|"Inochi Shrine"']
    assert g.build({"en": "Inochi Shrine", "ja": "命神社"}, True, ON)[1] == []


def test_registered():
    src = open(os.path.join(HERE, "create_items.py"), encoding="utf-8").read()
    assert '"inochi_creates.txt"' in src
    src = open(os.path.join(HERE, "direct_daily_edits.py"), encoding="utf-8").read()
    assert '"inochi_labels.txt"' in src
    wf = os.path.join(os.path.dirname(HERE), ".github", "workflows", "generate-quickstatements.yml")
    assert "python generate_inochi_shrine.py" in open(wf, encoding="utf-8").read()
