"""Obvious gender on the created kami (Emma, 2026-10-08); add first, remove later."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import generate_kami_gender as g  # noqa: E402
import generate_kami_gender_unknown_removals as r  # noqa: E402


def test_obvious_markers_only():
    assert g.obvious_gender("淀比咩命") == g.FEMALE
    assert g.obvious_gender("八劔彦命") == g.MALE
    assert g.obvious_gender("健速須佐之男神") == g.MALE
    assert g.obvious_gender("大石大神") is None          # no marker
    assert g.obvious_gender("姫彦神") is None            # both: ambiguous, left alone


def test_never_changes_a_real_gender():
    items = {"Q1": ("橘姫命", {g.UNKNOWN}), "Q2": ("橘姫命", set()), "Q3": ("橘姫命", {g.MALE})}
    assert g.build_lines(items) == ["Q1|P21|Q6581072", "Q2|P21|Q6581072"]


def test_removal_is_confirmed_and_value_matched():
    q = r.query(["Q1"])
    assert f"?k wdt:P21 wd:{g.UNKNOWN}" in q and "FILTER(?real IN" in q
    assert r.build_lines(["Q1", "Q1"]) == ["-Q1|P21|Q24238356"]


def test_registered():
    src = open(os.path.join(HERE, "direct_daily_edits.py"), encoding="utf-8").read()
    assert '"kami_gender.txt"' in src and '"kami_gender_unknown_removals.txt"' in src
    wf = open(os.path.join(os.path.dirname(HERE), ".github", "workflows", "generate-quickstatements.yml"), encoding="utf-8").read()
    assert "python generate_kami_gender.py" in wf and "python generate_kami_gender_unknown_removals.py" in wf
