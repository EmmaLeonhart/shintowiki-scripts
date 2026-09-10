"""The description-fix drip must never make a description LESS specific.

Emma, 2026-09-10: *"we're actively worsening Ukrainian descriptions why is this?
Turning descriptive ones into generic highly duplicative ones"*. 208 descriptions
across seven languages had a prefecture-specific form replaced by one generic
string, and 3,509 more lines were queued to do the same.

Two independent faults, both pinned here:

  1. **Prefecture detection could not match an inflected or differently-cased
     label.** It substring-tested the full label, so Ukrainian's nominative
     "Префектура Наґано" never matched its own locative description "…у
     префектурі Наґано, Японія", and Dutch's "Prefectuur Nagano" never matched
     "…in de prefectuur Nagano, Japan". Nine languages inferred NO prefecture
     template at all and fell wholesale to the generic modal; fr and de happened
     to match and were fine, which is what made it look like a uk oddity.
  2. **Nothing compared the proposal against what was already there** beyond
     exact equality, so an item carrying the better form was overwritten.

Fixing (1) is what stops this arising; (2) is what holds whatever the inference
does. Both are needed — (1) alone would leave the same hole open for the next
language whose descriptions are worded differently from its labels.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import generate_description_fixes as g  # noqa: E402
import generate_description_restores as r  # noqa: E402


UK_PREFS = ["Префектура Наґано", "Префектура Айті", "Префектура Кіото",
            "Префектура Сідзуока", "Префектура Ямаґучі", "Префектура Акіта"]
NL_PREFS = ["Prefectuur Nagano", "Prefectuur Aichi", "Prefectuur Kioto",
            "Prefectuur Shizuoka", "Prefectuur Yamaguchi", "Prefectuur Akita"]
ID_PREFS = ["Prefektur Nagano", "Prefektur Aichi", "Prefektur Kyoto",
            "Prefektur Shizuoka", "Prefektur Yamaguchi", "Prefektur Akita"]


def test_the_generic_word_is_dropped_and_the_place_name_kept():
    keys = g.pref_keys(UK_PREFS)
    assert set(keys) == {"Наґано", "Айті", "Кіото", "Сідзуока", "Ямаґучі", "Акіта"}
    assert keys["Наґано"] == "Префектура Наґано"


@pytest.mark.parametrize("prefs,desc,expected_template,fill,expected", [
    # Ukrainian: the label is nominative, the description locative. This is the
    # exact pair that failed.
    (UK_PREFS, "Синтоїстське святилище у префектурі Наґано, Японія",
     "Синтоїстське святилище у префектурі {pref}, Японія", "Айті",
     "Синтоїстське святилище у префектурі Айті, Японія"),
    # Dutch: not inflected, but the label capitalises what the description does
    # not — the same substring miss from a different cause.
    (NL_PREFS, "Shinto-schrijn in de prefectuur Nagano, Japan",
     "Shinto-schrijn in de prefectuur {pref}, Japan", "Aichi",
     "Shinto-schrijn in de prefectuur Aichi, Japan"),
    # Indonesian: worked before and must produce the identical string after.
    (ID_PREFS, "kuil Shinto di Prefektur Nagano, Jepang",
     "kuil Shinto di Prefektur {pref}, Jepang", "Aichi",
     "kuil Shinto di Prefektur Aichi, Jepang"),
])
def test_a_prefecture_template_is_inferred(prefs, desc, expected_template, fill, expected):
    keys = g.pref_keys(prefs)
    items = {f"Q{i}": (desc, False, None) for i in range(6)}
    pref_t, _gen = g.infer_templates(items, keys)
    assert pref_t == expected_template
    assert pref_t.replace("{pref}", fill) == expected


def test_the_uk_corpus_no_longer_collapses_to_the_generic():
    """The regression, stated as itself: a corpus that is mostly prefecture forms
    must infer a prefecture template, not fall through to the generic modal."""
    keys = g.pref_keys(UK_PREFS)
    items = {f"Q{i}": ("Синтоїстське святилище у префектурі Наґано, Японія", False, None)
             for i in range(8)}
    items.update({f"Qg{i}": ("синтоїстське святилище в Японії", False, None)
                  for i in range(4)})
    pref_t, gen = g.infer_templates(items, keys)
    assert pref_t is not None, "no prefecture template — every target falls to the generic"
    assert gen == "синтоїстське святилище в Японії"


# ---- the restore side --------------------------------------------------------

def test_a_description_naming_its_prefecture_is_recognised():
    keys = g.pref_keys(UK_PREFS)
    assert r.names_a_prefecture(
        "Синтоїстське святилище у префектурі Наґано, Японія", keys) == "Наґано"
    assert r.names_a_prefecture("синтоїстське святилище в Японії", keys) is None


def _restore(was, now, prefs=UK_PREFS, lang="uk"):
    edits = [("Q1", lang, 111, "2026-09-10T01:10:41Z")]
    lines, report = r.build_lines(
        edits, {("Q1", lang): was}, {"Q1": {lang: now}} if now else {"Q1": {}},
        {lang: g.pref_keys(prefs)})
    return lines, report[0][4]


def test_a_downgraded_description_is_restored_verbatim():
    was = "Синтоїстське святилище у префектурі Наґано, Японія"
    lines, verdict = _restore(was, "синтоїстське святилище в Японії")
    assert verdict == "RESTORE"
    assert lines == [f'Q1|Duk|"{was}"']


def test_an_item_someone_has_already_repaired_is_left_alone():
    """Self-healing, and it must not fight a person: if the current value already
    names the prefecture, there is nothing to put back."""
    lines, verdict = _restore("Синтоїстське святилище у префектурі Наґано, Японія",
                              "Синтоїстське святилище у префектурі Наґано, Японія")
    assert verdict == "already carries its prefecture"
    assert lines == []


def test_an_originally_generic_description_is_not_restored():
    """Replacing a generic description with a generic one lost nothing, so there
    is nothing to undo — the restore must not re-assert an equally poor value."""
    lines, verdict = _restore("синтоїстське святилище в Японії",
                              "синтоїстське святилище в Японії")
    assert verdict == "original named no prefecture"
    assert lines == []


def test_the_restore_and_the_fix_share_one_idea_of_a_prefecture():
    """Two definitions would let the two scripts disagree about an item forever —
    one restoring what the other keeps flattening."""
    assert r.pref_keys is g.pref_keys
