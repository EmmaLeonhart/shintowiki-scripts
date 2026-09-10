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

UK_GENERIC = "синтоїстське святилище в Японії"
UK_PREF = "Синтоїстське святилище у префектурі {pref}, Японія"
PREF_QIDS = {"Наґано": "Q127513", "Айті": "Q122771", "Кіото": "Q123540",
             "Сідзуока": "Q123376", "Ямаґучі": "Q128186", "Акіта": "Q129045"}


def _corpus():
    """A realistic corpus: several prefecture forms, each on two or more items,
    plus the generic modal on more items than any single prefecture form."""
    rows = []
    for spelling, pref in PREF_QIDS.items():
        for i in range(4):
            rows.append((f"Q{spelling}{i}", UK_PREF.replace("{pref}", spelling), pref))
    rows += [(f"Qg{i}", UK_GENERIC, "Q127513") for i in range(30)]
    return rows


def _run(rows):
    template, gen, spellings = r.infer_corpus_forms(rows)
    return r.build_lines(rows, template, gen, spellings)


def test_the_template_and_the_spelling_both_come_from_the_corpus():
    template, gen, spellings = r.infer_corpus_forms(_corpus())
    assert template == UK_PREF
    assert gen == UK_GENERIC
    assert spellings["Q127513"] == "Наґано"


def test_a_flattened_description_is_given_its_prefecture_back():
    rows = _corpus() + [("Q1", UK_GENERIC, "Q123540")]
    lines, _verdicts = _run(rows)
    assert ("Q1", UK_PREF.replace("{pref}", "Кіото")) in lines


def test_the_corpus_spelling_wins_over_any_other():
    """Wikidata's uk LABEL for 長野県 is `Префектура Нагано`; the 2,322 sibling
    descriptions spell it `Наґано`. Filling from the label would introduce a
    second spelling, so the fill must come from the descriptions."""
    rows = _corpus() + [("Q1", UK_GENERIC, "Q127513")]
    lines, _verdicts = _run(rows)
    assert ("Q1", UK_PREF.replace("{pref}", "Наґано")) in lines
    assert not any("Нагано, " in new for _q, new in lines)


def test_a_description_already_naming_its_prefecture_is_left_alone():
    """Self-healing, and it must not fight a person."""
    rows = _corpus() + [("Q1", UK_PREF.replace("{pref}", "Кіото"), "Q123540")]
    lines, verdicts = _run(rows)
    assert not any(q == "Q1" for q, _ in lines)
    assert verdicts["not the generic form — left alone"] >= 1


def test_real_prose_is_not_standardised():
    """This repairs a flattening; it does not normalise descriptions at large."""
    rows = _corpus() + [("Q1", "стародавнє святилище роду Мононобе", "Q123540")]
    lines, _verdicts = _run(rows)
    assert not any(q == "Q1" for q, _ in lines)


def test_one_line_of_prose_does_not_destroy_the_template():
    """Measured, not hypothetical: a common-affix over ALL non-generic
    descriptions collapsed to nothing because of a single "гора в Японії"."""
    rows = _corpus() + [("Qx", "гора в Японії", "Q123540")]
    template, _gen, _sp = r.infer_corpus_forms(rows)
    assert template == UK_PREF


def test_a_capitalised_variant_of_the_generic_does_not_zero_the_suffix():
    """The other measured failure: one `Синтоїстське святилище в Японії` in the
    bucket ends `в Японії` against the template's `, Японія`, and a single
    mismatch used to zero the common suffix."""
    rows = _corpus() + [("Qv", "Синтоїстське святилище в Японії", "Q123540")]
    template, _gen, _sp = r.infer_corpus_forms(rows)
    assert template == UK_PREF


def test_a_corpus_with_no_prefecture_form_yields_nothing():
    """The Buddhist-temple class in uk is 2,294 copies of the SHRINE generic.
    There is no temple prefecture form, and filling one in from the shrine corpus
    would make a wrong description more confident rather than repair anything."""
    rows = [(f"Qg{i}", UK_GENERIC, "Q127513") for i in range(60)]
    lines, verdicts = _run(rows)
    assert lines == []
    assert verdicts["no prefecture form inferable from this corpus"] == 60


def test_a_spelling_needs_two_items_to_agree():
    """One item agreeing with itself is not corpus evidence."""
    rows = _corpus() + [("Qsolo", UK_PREF.replace("{pref}", "Тіба"), "Q123456")]
    _t, _g, spellings = r.infer_corpus_forms(rows)
    assert "Q123456" not in spellings


def test_it_reads_wikidata_and_never_walks_contributions():
    """Emma, 2026-09-10: "please don't walk contributions whatever that means.
    Walk wikidata." The first version paged usercontribs and read parent
    revisions; the selector is now the item's own state."""
    import ast
    tree = ast.parse(open(r.__file__, encoding="utf-8").read())
    # The module docstring RECORDS that it used to walk contributions, so the
    # scan is over the code with the docstrings removed -- otherwise the
    # explanation of the fix trips the test for the fix.
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)                 and isinstance(node.value.value, str):
            node.value.value = ""
    code = ast.unparse(tree)
    for banned in ("usercontribs", "ucuser", "parentid", "rvprop", "revids"):
        assert banned not in code, f"{banned} is an edit-history walk"


def test_indonesian_is_not_in_the_repair_scope():
    """id's template never failed — its labels are uninflected `Prefektur
    Nagano` — so nothing Indonesian was ever flattened. Including it emitted
    1,737 lines of standardisation nobody asked for."""
    assert "id" not in r.LANGS
