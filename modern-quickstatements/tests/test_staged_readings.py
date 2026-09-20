"""Readings this repo has staged but Wikidata has not landed yet (2026-09-19).

The English-label worklists carry a ``kana`` field read off WIKIDATA, so a
reading sitting in ``nta_kana.txt`` waiting its turn on the daily drip is
invisible to them: Stage 1 saw no kana, emitted nothing, and the item fell
through to Stage 2 or the LLM.

Measured over the real worklists: **296 shrines and 1,116 temples**. That is the
bottleneck ``ATOMIC_FILES`` already names in its own comment — "the ~18,065-item
English-label residual is blocked on READINGS, not on the romanization rule" —
and the readings were in the repo the whole time.

⛔ The two rules this file exists to hold down:

  * **Registry-sourced readings only.** The other two staged P1814 files are
    DERIVED FROM THE ENGLISH LABEL, so feeding them back in would derive a label
    from a reading derived from a label.
  * **Both stages must see the same top-up.** Stage 2 selects the items Stage 1
    could not handle, and decides that by asking whether the item has kana.
"""

import io
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import staged_readings  # noqa: E402
import generate_kana_en_labels as stage1_shrine  # noqa: E402
import generate_temple_en_labels as stage1_temple  # noqa: E402
import generate_identical_name_en_labels as stage2  # noqa: E402
import select_shrines_to_translate as select  # noqa: E402


# --------------------------------------------------------------------------
# ⛔ Circularity: only the registry-sourced file
# --------------------------------------------------------------------------
def test_only_the_registry_sourced_file_is_read():
    """`derived_name_in_kana.txt` and `katakana_reading_add.txt` are derived FROM
    the English label. Reading a label back out of them would be circular."""
    assert staged_readings.SOURCES == ("nta_kana.txt",)
    assert "derived_name_in_kana.txt" not in staged_readings.SOURCES
    assert "katakana_reading_add.txt" not in staged_readings.SOURCES


def test_the_excluded_files_really_are_label_derived():
    """Pinning the reason, not just the exclusion: both are populated only for
    items that ALREADY carry an en label, which is why today's overlap with a
    missing-en-label worklist is zero."""
    import submit_daily_batch as s
    src = io.open(os.path.join(HERE, "submit_daily_batch.py"),
                  encoding="utf-8").read()
    assert "derived_name_in_kana.txt" in s.ATOMIC_FILES
    for name, phrase in (("derived_name_in_kana.txt", "an en label"),
                         ("katakana_reading_add.txt", "English label")):
        i = src.index(name)
        assert phrase in src[i:i + 2000], name


def test_zero_overlap_with_the_worklists_today(worklist_qids):
    """The measured property the exclusion rests on. If this ever fails, the
    populations have shifted and the circularity is live."""
    derived = staged_readings.load(sources=("derived_name_in_kana.txt",))
    assert not (set(derived) & worklist_qids), (
        "an item with no en label now has a label-derived reading staged"
    )


@pytest.fixture(scope="module")
def worklist_qids():
    out = set()
    for name in ("shrines_missing_en_label.json", "temples_missing_en_label.json"):
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        with io.open(path, encoding="utf-8") as fh:
            for it in json.load(fh).get("items", []):
                if not (it.get("kana") or "").strip():
                    out.add(it["qid"])
    return out


# --------------------------------------------------------------------------
# fill()
# --------------------------------------------------------------------------
def test_fill_only_touches_empty_kana():
    items = [{"qid": "Q1", "kana": ""}, {"qid": "Q2", "kana": "すでにある"},
             {"qid": "Q3"}, {"qid": "Q4", "kana": "  "}]
    n = staged_readings.fill(items, staged={"Q1": "いち", "Q2": "に",
                                            "Q3": "さん", "Q4": "よん"})
    assert n == 3
    assert items[0]["kana"] == "いち"
    assert items[1]["kana"] == "すでにある", "a live Wikidata reading wins"
    assert items[2]["kana"] == "さん"
    assert items[3]["kana"] == "よん"


def test_fill_leaves_unknown_items_alone():
    items = [{"qid": "Q9", "kana": ""}]
    assert staged_readings.fill(items, staged={}) == 0
    assert items[0]["kana"] == ""


def test_load_parses_the_real_file():
    staged = staged_readings.load()
    assert len(staged) > 1000, "nta_kana.txt should carry over a thousand readings"
    assert all(q.startswith("Q") for q in staged)
    assert all(v and '"' not in v for v in staged.values())


# --------------------------------------------------------------------------
# ⛔ Both stages, or the two of them emit a competing label for one QID
# --------------------------------------------------------------------------
def test_stage1_applies_the_top_up():
    for mod in (stage1_shrine, stage1_temple):
        src = io.open(mod.__file__, encoding="utf-8").read()
        assert "staged_readings.fill" in src, mod.__name__


def test_stage2_applies_the_same_top_up():
    """⛔ Topping up in Stage 1 alone would leave these items looking kana-less
    to Stage 2, so BOTH would emit an Len line for the same QID into two
    different atomic files, and whichever the drip ran second would silently
    overwrite the first."""
    src = io.open(stage2.__file__, encoding="utf-8").read()
    assert "staged_readings.fill" in src


def test_stage2_hands_the_topped_up_items_to_stage1():
    """Against the real worklists: Stage 2's target list must shed exactly the
    items the top-up gave kana to."""
    for worklist in ("shrines_missing_en_label.json",
                     "temples_missing_en_label.json"):
        path = os.path.join(HERE, worklist)
        if not os.path.exists(path):
            continue
        with io.open(path, encoding="utf-8") as fh:
            items = json.load(fh).get("items", [])
        raw = [i for i in items
               if not (i.get("kana") or "").strip() and i.get("ja")]
        after = stage2.load_targets(path)
        filled = staged_readings.fill(
            [dict(i) for i in items if not (i.get("kana") or "").strip()])
        assert len(raw) - len(after) == filled, worklist


# --------------------------------------------------------------------------
# ⭐ The output-side drift guard the pipeline never had
# --------------------------------------------------------------------------
EN_LABEL_FILES = [
    "kana_en_labels.txt", "temple_en_labels.txt", "tenjinsha_en_labels.txt",
    "identical_name_en_labels.txt", "temple_identical_name_en_labels.txt",
    "en_labels.txt", "en_labels_sonnet.txt",
]

# ⚠ One grandfathered pair, 2026-09-19. `en_labels.txt` gives Q65268013
# "Nenbutsu-ji (Sakai)" from its shintowiki page title while Stage 2 gives
# "Nenbutsu-ji Temple". Which is right depends on whether another Nenbutsu-ji
# already holds the bare label on live Wikidata, and that is one API call's worth
# of judgement for one item — recorded here so it is visible rather than silent.
KNOWN_COLLISIONS = {"Q65268013"}


def _en_lines():
    import re
    pat = re.compile(r'^(Q\d+)\|Len\|')
    owners = {}
    for name in EN_LABEL_FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        for line in io.open(path, encoding="utf-8"):
            m = pat.match(line.strip())
            if m:
                owners.setdefault(m.group(1), set()).add(name)
    return owners


def test_one_en_label_line_per_item():
    """⭐ `select_shrines_to_translate.EXCLUDE_FILES` enforces one label per item
    on the INPUT side and nothing ever checked the OUTPUT side. Two Len lines for
    one QID in two atomic files means the drip writes both and the later one
    wins, arbitrarily — 959 of them appeared the moment Stage 1 could reach the
    items Stage 2 had already claimed."""
    clashes = {q: sorted(v) for q, v in _en_lines().items()
               if len(v) > 1 and q not in KNOWN_COLLISIONS}
    assert not clashes, f"{len(clashes)} items carry two en labels: {list(clashes.items())[:5]}"


def test_the_exclusion_list_still_covers_every_en_label_file():
    """The input-side guard and the output-side guard must watch the same set."""
    assert set(EN_LABEL_FILES) - {"tenjinsha_en_labels.txt"} <= set(select.EXCLUDE_FILES)


def test_a_shared_label_across_items_is_not_a_collision():
    """⚠ 1,355 labels are claimed by more than one QID and that is CORRECT —
    fifteen different Itsukushima Shrines are all `Itsukushima Shrine`. Wikidata
    constrains the (label, description) PAIR, not the label. This test exists so
    a later reader does not mistake that for the defect above."""
    import re
    pat = re.compile(r'^(Q\d+)\|Len\|"([^"]*)"')
    by_label = {}
    for name in EN_LABEL_FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        for line in io.open(path, encoding="utf-8"):
            m = pat.match(line.strip())
            if m:
                by_label.setdefault(m.group(2), set()).add(m.group(1))
    shared = [k for k, v in by_label.items() if len(v) > 1]
    assert shared, "expected shared labels; if this is empty the corpus changed shape"
