"""A cloud-fed stage that has lost its driver must be visible from inside the repo.

Stage 4 of the English-label pipeline was absent for 52 days after the 2026-07-27
account move took its routine with it. Nothing in here could see that: the driver
lived outside the repo, and every in-repo symptom looked healthy -- Stages 0-2 kept
committing daily, the worklists kept refreshing, the submitter kept reading the
file. The only evidence was an output that stopped growing.

The check reads git history of the output, which is the one signal that crosses the
boundary. What these tests hold down is the THRESHOLD, because a check that cries
wolf is a check that gets ignored, and both wrong models were tried on the real data:

  * **A flat day count is wrong.** `beppyo_p612` had gone 44 days without growing on
    2026-09-17 and that is normal -- it is ONE work-file, and the drainer takes 5
    random items from ~1,800, so it comes up about once a year. A flat threshold
    reports a healthy stage as dead on every run.
  * **Draw rate alone is also wrong**, and this one actually fired: the first run
    flagged `category_translation` at 16 days. Its collector runs on the 1st of the
    month, so on the 17th its output is necessarily 16 days stale. An answer cannot
    appear faster than the collector that folds it in.
"""
import datetime
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SM = os.path.join(_ROOT, "shinto_miraheze")
if _SM not in sys.path:
    sys.path.insert(0, _SM)

import check_stage_liveness as live  # noqa: E402

_TODAY = datetime.date(2026, 9, 17)


def _fake(monkeypatch, pools, growths):
    monkeypatch.setattr(live, "outstanding", lambda d: pools.get(d, 0))
    monkeypatch.setattr(live, "last_growth", lambda p: growths.get(p))


def _row(rows, stage):
    return next(r for r in rows if r["stage"] == stage)


def test_the_52_day_label_gap_is_reported(monkeypatch):
    """The incident this exists for."""
    _fake(monkeypatch,
          {"en_label": 400},
          {"modern-quickstatements/en_labels_sonnet.txt": "2026-07-27"})
    rows = live.assess(today=_TODAY, total=1812)
    r = _row(rows, "en_label")
    assert r["days"] == 52
    assert r["quiet"], (
        "a 400-item pool silent for 52 days, against ~0.9 days expected between "
        "picks, is the exact shape of the incident and must be reported"
    )


def test_a_one_item_pool_is_not_called_dead_after_44_days(monkeypatch):
    """beppyo_p612 on 2026-09-17. 5 picks/day from ~1,800 means a 1-item pool is
    drawn about once a year; 44 days of silence is nothing."""
    _fake(monkeypatch,
          {"beppyo_p612": 1},
          {"modern-quickstatements/beppyo_p612.txt": "2026-08-04"})
    r = _row(live.assess(today=_TODAY, total=1812), "beppyo_p612")
    assert r["days"] == 44
    assert not r["quiet"], (
        "a flat day threshold reports this healthy stage as dead on every run, "
        "which is how the check becomes noise and stops being read"
    )
    assert r["expected"] > 300


def test_a_monthly_collector_is_not_called_dead_mid_month(monkeypatch):
    """category_translation on 2026-09-17: the collector runs on the 1st, so the
    output is necessarily 16 days stale. This flagged on the first real run."""
    _fake(monkeypatch,
          {"category_translation": 328},
          {"shinto_miraheze/category_moves.csv": "2026-09-01"})
    r = _row(live.assess(today=_TODAY, total=1812), "category_translation")
    assert r["days"] == 16
    assert r["cadence"] == 31
    assert not r["quiet"], (
        "an answer cannot reach the output faster than the collector that folds "
        "it in; a monthly collector owes nothing for 31 days"
    )


def test_an_empty_pool_is_never_called_quiet(monkeypatch):
    """No work waiting means silence proves nothing about the driver."""
    _fake(monkeypatch,
          {"label_typo_review": 0},
          {"modern-quickstatements/label_typo_fixes.txt": "2026-01-01"})
    r = _row(live.assess(today=_TODAY, total=1812), "label_typo_review")
    assert r["pool"] == 0
    assert not r["quiet"]


def test_an_output_that_never_grew_with_work_waiting_is_quiet(monkeypatch):
    _fake(monkeypatch, {"en_label": 400}, {})
    r = _row(live.assess(today=_TODAY, total=1812), "en_label")
    assert r["days"] is None and r["quiet"]


def test_an_empty_queue_flags_nothing(monkeypatch):
    """Guard against a divide-by-zero dressed up as every stage being dead."""
    _fake(monkeypatch, {"en_label": 400}, {})
    rows = live.assess(today=_TODAY, total=0)
    assert not any(r["quiet"] for r in rows)


def test_it_reports_and_never_gates():
    """A quiet cloud routine must not stop the rest of the pipeline.

    Run as a subprocess rather than calling main(): main() rebinds sys.stdout to a
    UTF-8 wrapper (Windows is cp1252), which defeats capsys. The exit code is the
    thing under test, and that only means anything from the real CLI anyway.
    """
    import subprocess
    r = subprocess.run(
        [sys.executable, os.path.join(_SM, "check_stage_liveness.py")],
        capture_output=True, text=True, encoding="utf-8", cwd=_ROOT,
    )
    assert r.returncode == 0, (
        f"the liveness check must never gate; it exited {r.returncode}.\n"
        f"{r.stdout}\n{r.stderr}"
    )
    assert "cloud-fed stages look quiet" in r.stdout


def test_every_collector_output_has_a_liveness_entry():
    """A new cloud-fed stage must not be able to arrive unwatched -- that is the
    whole failure mode, one stage nobody was watching."""
    covered = {rel for _, rel, _, _ in live.PAIRS}
    missing = []
    for name in sorted(os.listdir(_SM)):
        if not name.startswith("collect_") or not name.endswith(".py"):
            continue
        text = open(os.path.join(_SM, name), encoding="utf-8").read()
        for marker in ("name_in_kana.txt", "ronsha_ranking_qualifiers.txt",
                       "beppyo_p612.txt", "label_typo_fixes.txt",
                       "description_enrichment_en.txt", "en_labels_sonnet.txt",
                       "category_moves.csv"):
            if marker in text and not any(c.endswith(marker) for c in covered):
                missing.append((name, marker))
    assert not missing, f"collector outputs with no liveness entry: {missing}"


@pytest.mark.parametrize("stage,_rel,_what,cadence", live.PAIRS)
def test_every_pair_names_a_real_output_and_a_sane_cadence(stage, _rel, _what, cadence):
    assert cadence >= 1
    # The work-file directory may legitimately be absent (pool drained to zero),
    # but the output path must be one the repo actually knows about.
    assert _rel.startswith(("modern-quickstatements/", "shinto_miraheze/"))
