"""The confirmed-Shikinaisha orphan report (Emma 2026-07-10).

Report only — it emits no QuickStatements, so what is worth pinning is the
classification: the normalisation that finds a modern shrine's 927 entry twin under a
variant spelling, and the ordering of the rules (a real Kokugakuin-id match must beat a
coincidental name match).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import report_orphan_shikinaisha as rep  # noqa: E402


# ─────────────────────── name normalisation ───────────────────────

def test_old_kanji_folds_to_new():
    assert rep.normalise("三國神社") == rep.normalise("三国神社")
    assert rep.normalise("彌彦神社") == rep.normalise("弥彦神社")
    assert rep.normalise("小国神社") == rep.normalise("小國神社")


def test_the_disambiguator_is_dropped():
    assert rep.normalise("坂本神社 (高島市)") == rep.normalise("坂本神社")
    assert rep.normalise("杉山神社 (横浜市西区)") == rep.normalise("杉山神社")


def test_the_no_variants_fold():
    assert rep.normalise("都留彌神社") == rep.normalise("都留弥神社")
    assert rep.normalise("木之本神社") == rep.normalise("木のもと神社".replace("もと", "本"))
    assert rep.normalise("大ヶ原神社") == rep.normalise("大が原神社")


def test_the_shrine_suffix_is_dropped_only_at_the_end():
    assert rep.normalise("三国神社") == "三国"
    assert rep.normalise("神社山神社") == "神社山"


def test_two_genuinely_different_shrines_do_not_collide():
    assert rep.normalise("坂本神社") != rep.normalise("杉山神社")


def test_normalise_survives_an_empty_name():
    assert rep.normalise("") == ""
    assert rep.normalise(None) == ""


# ─────────────────────── classification ───────────────────────

PARTS = {"Qlist": {"Qentry", "Qother"}}
JA = {"Qorphan": "三國神社", "Qentry": "三国神社", "Qother": "杉山神社"}


def test_a_shared_kokugakuin_id_wins_over_everything():
    """An id match is evidence; a name match is a guess. Rank them that way."""
    k = rep.classify("Qorphan", ["Qlist"], PARTS, JA, {"Qorphan": ["1"]}, {"Qorphan"})
    assert k.startswith("twin: shares a Kokugakuin id")


def test_an_exact_label_match_is_found():
    ja = dict(JA, Qorphan="三国神社")
    k = rep.classify("Qorphan", ["Qlist"], PARTS, ja, {}, set())
    assert k == "twin: same ja label as a named entry in the list it claims"


def test_a_normalised_label_match_is_found_and_ranked_below_the_exact_one():
    k = rep.classify("Qorphan", ["Qlist"], PARTS, JA, {}, set())
    assert k == "twin: same normalised ja label as a named entry in the list it claims"


def test_claiming_no_list_is_its_own_class():
    k = rep.classify("Qorphan", [], PARTS, JA, {}, set())
    assert k == "no twin: claims no list at all"


def test_holding_an_unshared_kokugakuin_id_is_its_own_class():
    ja = dict(JA, Qorphan="全然違う神社")
    k = rep.classify("Qorphan", ["Qlist"], PARTS, ja, {"Qorphan": ["9"]}, set())
    assert k == "no twin: holds its own Kokugakuin id, yet no list names it"


def test_the_residue_is_named_plainly():
    ja = dict(JA, Qorphan="全然違う神社")
    k = rep.classify("Qorphan", ["Qlist"], PARTS, ja, {}, set())
    assert k == "no twin: claims a list, has no Kokugakuin id"


def test_an_item_is_never_its_own_twin():
    parts = {"Qlist": {"Qorphan"}}
    k = rep.classify("Qorphan", ["Qlist"], parts, JA, {}, set())
    assert k.startswith("no twin")


def test_a_twin_in_a_list_the_item_does_not_claim_is_not_counted():
    """The evidence is 'the list it claims names this name already', not 'somewhere'."""
    parts = {"Qother_list": {"Qentry"}}
    k = rep.classify("Qorphan", ["Qlist"], parts, JA, {}, set())
    assert k.startswith("no twin")
