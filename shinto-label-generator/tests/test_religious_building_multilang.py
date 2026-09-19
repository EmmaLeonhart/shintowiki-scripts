"""Stage 2: ja/zh/ko labels for religious buildings, composed from morphemes.

What these hold down is mostly the things that were WRONG first, because each was
found by measuring the real 22,548-label corpus rather than by reasoning:

  * **Collisions.** Composing dedication + type alone gave 36 distinct outputs for
    2,392 labels -- 99.6% colliding, 515 Madonna churches all becoming 聖母教会.
    For this population the "name" IS the dedication and hundreds share it, so the
    place is what separates them and `render()` must refuse without one.
  * **Double-rendering.** "San Giovanni Battista" rendered Giovanni AND Battista
    and came out as 聖ヨハネ洗礼者ヨハネ -- John twice.
  * **A fused saint marker.** "Santiago" is Sant+Iago, so no marker token appears
    and the 聖 prefix was dropped.
  * **A leaked disambiguator.** Place labels carry their own: "Freden (Leine)"
    produced フレーデン (ライネ)の聖ラウレンティウス教会.
  * **Category-shaped labels.** ~818 of the corpus name a GROUPING, not a
    building -- "Cultural heritage monuments in X", plural "Synagogues".
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402
import generate_religious_building_multilang as gen  # noqa: E402


# --------------------------------------------------------------------------
# The place is mandatory -- this is the anti-collision rule
# --------------------------------------------------------------------------

@pytest.mark.parametrize("lang", ["ja", "zh", "ko"])
def test_no_place_means_no_label(lang):
    assert m.render("St. Laurentius", "Q16970", lang, place=None) is None, (
        "without a place, hundreds of items share one dedication -- 515 Madonna "
        "churches collapsed onto 聖母教会 when this was allowed"
    )


def test_the_place_disambiguates_two_identical_dedications():
    a = m.render("St. Martin", "Q16970", "ja", place="レーデン")
    b = m.render("St. Martin", "Q16970", "ja", place="ビッセンドルフ")
    assert a and b and a != b


def test_place_goes_first_and_possessive():
    """Emma, 2026-09-17: 'Place first, possessive'."""
    assert m.render("St. Laurentius", "Q16970", "ja",
                    place="レーデン") == "レーデンの聖ラウレンティウス教会"
    assert m.render("St. Laurentius", "Q16970", "zh",
                    place="雷登") == "雷登圣老楞佐教堂"
    assert m.render("St. Laurentius", "Q16970", "ko",
                    place="레덴") == "레덴의 성라우렌시오교회"


def test_a_place_disambiguator_does_not_leak_in():
    got = m.render("St. Laurentius", "Q16970", "ja", place="フレーデン (ライネ)")
    assert got == "フレーデンの聖ラウレンティウス教会", got
    assert "(" not in got and "（" not in got


# --------------------------------------------------------------------------
# Dedication parsing
# --------------------------------------------------------------------------

def test_a_multi_token_saint_is_one_dedicatee():
    got = m.render("San Giovanni Battista", "Q16970", "ja", place="ローマ")
    assert got == "ローマの聖洗礼者ヨハネ教会", got
    assert got.count("ヨハネ") == 1, "John rendered twice"


def test_a_fused_saint_marker_still_gets_the_prefix():
    got = m.render("Igreja de Santiago", "Q16970", "ja", place="リスボン")
    assert got.startswith("リスボンの聖"), got


def test_a_glued_german_compound_is_split():
    got = m.render("St.-Petri-Kirche", "Q16970", "ja", place="レーデン")
    assert got == "レーデンの聖ペトロ教会", got


def test_a_hyphenated_dedication_phrase_is_found():
    """'Notre-Dame' matched nothing until hyphens were normalised; 111 labels."""
    got = m.render("Notre-Dame", "Q16970", "ja", place="パリ")
    assert got == "パリの聖母教会", got


def test_an_unknown_dedicatee_is_refused():
    """⚠ Narrowed 2026-09-19. "Unknown dedicatee -> refuse" was the whole rule
    until Emma's *"No dedication means transliteration"*; what survives of it is
    that the TABLE still does not invent a name, and that a country with no
    reading rule still refuses. Given Italian rules this label is now READ."""
    assert m.dedication("St. Fictitious", "ja") is None
    assert m.render("St. Fictitious", "Q16970", "ja", place="レーデン") is None
    assert m.render("St. Fictitious", "Q16970", "zh", place="レーデン",
                    rules="it") is None


# --------------------------------------------------------------------------
# The type comes from P31, never from the label
# --------------------------------------------------------------------------

def test_the_type_comes_from_p31_not_the_label():
    """Two thirds of the corpus carries no English type word, so the label
    cannot be the source of the type."""
    chapel = m.render("St. Laurentius", "Q108325", "ja", place="レーデン")
    church = m.render("St. Laurentius", "Q16970", "ja", place="レーデン")
    assert chapel.endswith("礼拝堂") and church.endswith("教会")


def test_an_unmapped_p31_is_refused():
    assert m.render("St. Laurentius", "Q99999999", "ja", place="レーデン") is None


def test_a_label_naming_the_wrong_type_does_not_win():
    """Label says Chapel, P31 says church building -- P31 wins."""
    got = m.render("St. Laurentius Chapel", "Q16970", "ja", place="レーデン")
    assert got.endswith("教会"), got


# --------------------------------------------------------------------------
# Category-shaped labels are refused
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", [
    "Cultural heritage monuments in Foo",
    "Synagogues in Nyrsko",
    "Churches in Bavaria",
    "Historic district of Bar",
    "Uspenskoe estate",
])
def test_category_shaped_labels_are_refused(label):
    assert m.is_category_shaped(label), label
    assert m.render(label, "Q16970", "ja", place="レーデン") is None


def test_a_real_building_is_not_mistaken_for_a_category():
    for label in ("St. Laurentius", "San Giovanni Battista", "Notre-Dame"):
        assert not m.is_category_shaped(label), label


# --------------------------------------------------------------------------
# Table sanity
# --------------------------------------------------------------------------

@pytest.mark.parametrize("table", ["TYPES", "NAMES", "DEDICATIONS", "NAME_PHRASES"])
def test_every_table_entry_covers_every_language(table):
    for key, forms in getattr(m, table).items():
        for lang in ("ja", "zh", "ko"):
            assert forms.get(lang), f"{table}[{key!r}] has no {lang}"


def test_markers_and_names_do_not_overlap():
    """A token cannot be both 'saint' and a saint's name, or parsing is
    order-dependent."""
    overlap = set(m.SAINT_MARKERS) & set(m.NAMES)
    assert not overlap, f"token is both a marker and a name: {sorted(overlap)}"


def test_stopwords_and_names_do_not_overlap():
    overlap = set(m.STOPWORDS) & set(m.NAMES)
    assert not overlap, f"token is both a stopword and a name: {sorted(overlap)}"


def test_english_is_not_emitted():
    """Stage 1's English is paused and is not re-derived here."""
    assert m.render("St. Laurentius", "Q16970", "en", place="Freden") is None


# --------------------------------------------------------------------------
# Specificity: a feast beats the Marian title carrying it
# --------------------------------------------------------------------------

def test_every_dedication_is_grouped():
    """A phrase in neither group is unreachable — the lookup walks the two
    groups, not the dict."""
    ungrouped = set(m.DEDICATIONS) - (m.SPECIFIC_DEDICATIONS | m.GENERIC_DEDICATIONS)
    assert not ungrouped, f"dedications in no group: {sorted(ungrouped)}"


def test_the_groups_do_not_overlap():
    both = m.SPECIFIC_DEDICATIONS & m.GENERIC_DEDICATIONS
    assert not both, f"phrase is both specific and generic: {sorted(both)}"


@pytest.mark.parametrize("label,expect", [
    # Sorting by string LENGTH lost the feast in each of these.
    ("Visitazione della Beata Vergine", "聖母訪問"),
    ("Nuestra Señora de la Asunción", "聖母被昇天"),
    ("Our Lady of Sorrows", "悲しみの聖母"),
    ("Nossa Senhora da Conceição", "無原罪の御宿り"),
    # ...and these two are both 10 characters, so the tie was arbitrary.
    ("Exaltation of the Holy Cross", "十字架挙栄"),
])
def test_a_feast_beats_the_marian_title_carrying_it(label, expect):
    got = m.render(label, "Q16970", "ja", place="X")
    assert got == "Xの" + expect + "教会", got


def test_a_bare_title_still_resolves():
    """The generic titles are a fallback, not something the fix removed."""
    assert m.render("Madonna", "Q16970", "ja", place="X") == "Xの聖母教会"


def test_a_plain_holy_cross_is_not_upgraded_to_the_feast():
    """Specificity must not run the other way."""
    assert m.render("Holy Cross Church", "Q16970", "ja",
                    place="X") == "Xの聖十字架教会"


def test_the_feast_table_covers_the_corpus_languages():
    """English-only feast names could not fire on an Italian or Spanish label,
    which is why the specificity fix did nothing until these were added."""
    for phrase in ("visitazione", "asunción", "natividade", "trasfigurazione",
                   "anunciación", "immacolata", "verkündigung"):
        assert phrase in m.DEDICATIONS, f"{phrase} missing"
        assert phrase in m.SPECIFIC_DEDICATIONS, f"{phrase} not marked specific"


def test_a_bare_modifier_is_never_a_dedication():
    """The santissima defect: a modifier matching as a whole dedication swallows
    what it qualifies. 354 labels came out as 至聖教会, 'Most Holy Church'."""
    for modifier in ("santissima", "santissimo"):
        assert modifier not in m.DEDICATIONS, (
            f"{modifier!r} is a modifier, not a dedication; as a bare entry it "
            f"matches before the thing it qualifies"
        )
    assert m.dedication("Chiesa Santissima", "ja") is None
    assert m.render("Chiesa Santissima", "Q16970", "ja", place="X") is None


# --------------------------------------------------------------------------
# Accent folding, and the devotions the drop-audit found
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label,expect", [
    # Accented and unaccented must behave identically. The table listed "fátima"
    # and "asunción" only, so the plain-ASCII spellings in the corpus missed.
    ("Our Lady of Fatima church", "ファティマの聖母"),
    ("Our Lady of Fátima church", "ファティマの聖母"),
    ("Nuestra Senora de la Asuncion", "聖母被昇天"),
    ("Nuestra Señora de la Asunción", "聖母被昇天"),
])
def test_accents_do_not_change_the_match(label, expect):
    got = m.render(label, "Q16970", "ja", place="X")
    assert got == "Xの" + expect + "教会", got


def test_folding_is_for_matching_only():
    """Output keeps its accents; only the comparison is folded."""
    assert m._fold("Asunción") == "Asuncion"
    assert m.render("Madonna di Loreto", "Q16970", "ja",
                    place="レーデン").startswith("レーデンの")


@pytest.mark.parametrize("label,expect", [
    # Each of these was silently dropped while a less specific dedication
    # rendered in its place -- found by auditing the emitted labels against
    # their sources, not by reading the tables.
    ("St. Johannes der Täufer", "洗礼者ヨハネ"),   # was plain 聖ヨハネ
    ("Beata Vergine delle Grazie", "恩寵の聖母"),
    ("Madonna della Neve", "雪の聖母"),
    ("Beata Vergine Addolorata", "悲しみの聖母"),
    ("Madonna di Loreto", "ロレートの聖母"),
    ("Our Lady of the Rosary church", "ロザリオの聖母"),
    ("Maria Königin", "天の元后"),
])
def test_a_devotion_is_not_lost_to_its_carrier(label, expect):
    got = m.render(label, "Q16970", "ja", place="X")
    assert got == "Xの" + expect + "教会", got


def test_the_carrier_alone_still_resolves():
    """Removing a devotion's carrier from the answer must not break the case
    where the carrier is all there is."""
    assert m.render("Madonna", "Q16970", "ja", place="X") == "Xの聖母教会"
    assert m.render("Beata Vergine", "Q16970", "ja", place="X") == "Xの聖母教会"


# --------------------------------------------------------------------------
# A generic title with an unmapped qualifier is refused
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", [
    # Qualifiers that cannot be READ either -- Slavic and German localities,
    # where Romance rules would give a confident wrong answer.
    # (Pero / Cardello / Campiglio were here until the transliterator landed;
    # they are Italian, so they are handled now rather than refused.)
    "Our Lady of Rzhavets",
    "Madonna di Bąkowa",
    "Our Lady of Zgierz",
])
def test_a_generic_title_with_an_unreadable_qualifier_is_refused(label):
    """Emma, 2026-09-18: 'Refuse each one until the table individual qualifier is
    done.' These rendered as a bare 聖母教会 -- true, unique once the place is
    prefixed, and less specific than the source said."""
    assert m.render(label, "Q16970", "ja", place="X") is None, label


@pytest.mark.parametrize("label", ["Madonna", "Beata Vergine", "Notre-Dame",
                                   "Our Lady"])
def test_a_bare_generic_title_still_resolves(label):
    """Nothing is lost when there is no qualifier to lose."""
    assert m.render(label, "Q16970", "ja", place="X") == "Xの聖母教会", label


@pytest.mark.parametrize("label,expect", [
    ("Madonna della Neve", "雪の聖母"),
    ("Our Lady of Sorrows", "悲しみの聖母"),
    ("Beata Vergine delle Grazie", "恩寵の聖母"),
])
def test_a_mapped_qualifier_is_not_refused(label, expect):
    """The rule must not swallow the devotions already in the table."""
    assert m.render(label, "Q16970", "ja", place="X") == "Xの" + expect + "教会"


def test_a_feast_is_unaffected_by_the_rule():
    """A feast subsumes its Marian carrier, so leftover carrier is not a
    qualifier and must not trigger a refusal."""
    assert m.render("Visitazione della Beata Vergine", "Q16970", "ja",
                    place="X") == "Xの聖母訪問教会"
    assert m.render("Nuestra Señora de la Asunción", "Q16970", "ja",
                    place="X") == "Xの聖母被昇天教会"


def test_widening_the_table_turns_a_refusal_into_a_rendering():
    """The other half of Emma's instruction: "refuse each one UNTIL the table
    individual qualifier is done". Vladimir and Carmo were refusal cases when
    this file was written and are mapped now, which is the intended direction."""
    assert m.render("Our Lady of Vladimir", "Q16970", "ja",
                    place="X") == "Xのウラジーミルの生神女教会"
    assert m.render("Nossa Senhora do Carmo", "Q16970", "ja",
                    place="X") == "Xのカルメル山の聖母教会"


@pytest.mark.parametrize("label,expect", [
    # Residue on a SPECIFIC match found these; each was rendering as a different
    # devotion entirely.
    ("Church of the Immaculate Heart of Mary", "聖母の汚れなき御心"),
    ("Church of Nativity of the Lord", "主の降誕"),
    ("Nativity of the Theotokos", "生神女誕生"),
])
def test_a_longer_dedication_beats_the_shorter_one_inside_it(label, expect):
    got = m.render(label, "Q16970", "ja", place="X")
    assert got == "Xの" + expect + "教会", got


def test_the_immaculate_conception_is_not_the_immaculate_heart():
    """They differ by one word and mean different things; `immaculate` matched
    first and 30 labels came out as the Conception."""
    conception = m.render("Immaculate Conception church", "Q16970", "ja", place="X")
    heart = m.render("Immaculate Heart of Mary", "Q16970", "ja", place="X")
    assert conception != heart
    assert conception == "Xの無原罪の御宿り教会"


# --------------------------------------------------------------------------
# English rendering (for replacing the stage-1 labels that reached Wikidata)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label,p31,expect", [
    ("Auferstehungskirche", "Q16970", "Church of the Resurrection"),
    ("Sacro Cuore", "Q16970", "Church of the Sacred Heart"),
    ("Santa Caterina", "Q108325", "Chapel of Saint Catherine"),
    ("Sant'Anna", "Q16970", "Church of Saint Anne"),
    ("San Martino", "Q16970", "Church of Saint Martin"),
    ("Stella Maris", "Q16970", "Church of Our Lady Star of the Sea"),
])
def test_english_renders_from_the_same_tables(label, p31, expect):
    assert morph_en(label, p31) == expect


def morph_en(label, p31):
    return m.render_en(label, p31)


@pytest.mark.parametrize("label,p31", [
    ("Frauenkirche", "Q16970"),          # 聖母 begins with the saint prefix
    ("Heiligen-Geist-Kapelle", "Q16970"),  # 聖霊 does too
    ("Church of Holy Trinity", "Q16970"),  # 至聖三者 contains it
])
def test_a_dedication_beginning_with_the_saint_prefix_still_renders(label, p31):
    """SAINT_PREFIX['ja'] is 聖, and 聖母 / 聖霊 / 聖体 / 聖十字架 legitimately
    begin with it. Stripping it naively reduced them to 母 and 霊 and returned
    None, silently dropping every such dedication from English."""
    assert m.render_en(label, p31) is not None, label


def test_an_apostrophised_saint_marker_is_split():
    """Sant'Anna and Sant'Antonio arrived as one unknown token until the
    apostrophe was split like a hyphen."""
    toks, saw_saint = m.parse_name("Sant'Anna")
    assert saw_saint and toks == ["anna"]


def test_english_refuses_what_the_tables_cannot_render():
    assert m.render_en("St. Fictitious", "Q16970") is None
    assert m.render_en("Cultural heritage monuments in Foo", "Q16970") is None


# --------------------------------------------------------------------------
# Place-name qualifiers: read by rule for ja, refused for zh/ko
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label,expect", [
    ("Madonna del Pero", "ペーロの聖母"),
    ("Madonna del Cardello", "カルデッロの聖母"),
    ("Madonna di Campiglio", "カンピーリョの聖母"),
])
def test_a_romance_place_qualifier_is_read_for_ja(label, expect):
    """Emma, 2026-09-18: handle the place-name qualifiers too. These were the
    refusal cases; a Romance locality can be read into kana by rule.

    ⚠ `rules="it"` is now passed EXPLICITLY. These three are Italian items and
    the generator has always passed `_rules_for("Q38")`; the test was relying on
    `render`'s old `rules="it"` default, which was removed on 2026-09-19 because
    an implicit Italian reading of a German name is exactly the confident-wrong
    failure the country map exists to refuse."""
    assert m.render(label, "Q16970", "ja", place="X",
                    rules="it") == "Xの" + expect + "教会"


@pytest.mark.parametrize("lang", ["zh", "ko"])
@pytest.mark.parametrize("label", ["Madonna del Pero", "Madonna di Campiglio"])
def test_a_place_qualifier_stays_refused_for_zh_and_ko(lang, label):
    """⛔ There is no rule-based route from an Italian village name to Chinese
    characters or hangul. Those are conventions, not derivations, and inventing
    one fabricates a reading."""
    assert m.render(label, "Q16970", lang, place="X") is None


def test_a_non_romance_qualifier_is_refused_in_every_language():
    """The corpus carries Polish and Russian localities too, and reading one
    with Romance rules gives a confident wrong answer."""
    for lang in ("ja", "zh", "ko"):
        assert m.render("Our Lady of Rzhavets", "Q16970", lang, place="X") is None


def test_a_mapped_devotion_is_not_transliterated():
    """The tables win; transliteration is the last resort, not the first."""
    assert m.render("Madonna della Neve", "Q16970", "ja",
                    place="X") == "Xの雪の聖母教会"
    assert m.render("Our Lady of Vladimir", "Q16970", "zh",
                    place="Y") == "Y弗拉基米尔圣母教堂"


def test_a_bare_title_is_untouched_by_the_qualifier_path():
    assert m.render("Madonna", "Q16970", "ja", place="X") == "Xの聖母教会"


def test_the_qualifier_keeps_its_diacritics():
    """⛔ dedication() folds accents before matching, so a qualifier reached the
    transliterator already stripped -- Graças arrived as "gracas" and came out
    グラーカス however good the Portuguese rules were. The residue is mapped back
    to its source spelling first."""
    assert m.render("Nossa Senhora das Graças", "Q16970", "ja",
                    place="X", rules="pt") == "Xのグラーサスの聖母教会"


def test_the_rule_set_reaches_the_qualifier():
    it = m.render("Madonna del Cardello", "Q16970", "ja", place="X", rules="it")
    assert it == "Xのカルデッロの聖母教会"


def test_a_qualifier_from_an_unsupported_language_is_refused():
    """French reads nothing like Italian; refusing beats a plausible-looking
    wrong answer."""
    import romance_katakana as rk
    assert m.render("Notre-Dame de Pitié de Trouville", "Q108325", "ja",
                    place="X", rules=rk.rules_for_country("Q142")) is None


def test_an_invisible_character_never_reaches_the_label():
    """A soft hyphen in a place label reached the output as a real character
    that is invisible in a terminal."""
    got = m.render("Madonna", "Q16970", "ja", place="\u00adラドヴィシュ")
    assert got == "ラドヴィシュの聖母教会"
    assert "\u00ad" not in got


# --------------------------------------------------------------------------
# Coverage widening, 2026-09-18
# --------------------------------------------------------------------------

def test_an_apostrophe_fragment_is_not_a_name():
    """⛔ Fragments the apostrophe split creates. These were the two most frequent
    "unknown names" in the whole corpus -- s 56, d 46 -- and neither is a name.

    Checked at the PARSE level for the French case: stripping `d` is what this
    fixes, and that label still refuses afterwards because `agnane` is a place
    the tables do not know. Asserting a rendering there would have been asserting
    the wrong thing."""
    assert m.render("St. Nicholas's Church", "Q16970", "ja",
                    place="X") == "Xの聖ニコラオス教会"
    tokens, saw_saint = m.parse_name("Chapelle Saint-Pierre d'Agnane")
    assert "d" not in tokens and saw_saint
    assert tokens == ["pierre", "agnane"]


@pytest.mark.parametrize("label,expect", [
    # Compound saints -- both halves render and the name doubles otherwise.
    ("Chapel of St. John of Nepomuk", "聖ネポムクのヨハネ"),
    ("St. Antonius von Padua", "聖パドヴァのアントニオ"),
    ("Chapel of Saint Mary Magdalene", "聖マグダラのマリア"),
])
def test_a_compound_saint_renders_once(label, expect):
    got = m.render(label, "Q16970", "ja", place="X")
    assert got == "Xの" + expect + "教会", got


def test_a_role_word_is_not_a_name():
    """"San Pietro Apostolo" is Peter; apostolo is his role."""
    assert m.render("San Pietro Apostolo", "Q16970", "ja",
                    place="X") == "Xの聖ペトロ教会"
    assert m.render("Saint Athanasius the Athonite church", "Q16970", "ja",
                    place="X") == "Xの聖アタナシオス教会"


@pytest.mark.parametrize("label,expect", [
    ("Santa Croce", "聖十字架"),
    ("Dreifaltigkeitskapelle", "至聖三者"),
    ("Erlöserkirche", "救世主"),
])
def test_the_added_dedications_render(label, expect):
    assert m.render(label, "Q16970", "ja", place="X") == "Xの" + expect + "教会"


def test_a_german_location_compound_names_no_dedication():
    """Wegkapelle is "wayside chapel" -- it says where, not who for.

    ⚠ `Hofkapelle Aichet` is a GERMAN label and `rules_for_country("Q183")` is
    None, so nothing reads it. It passed here before 2026-09-19 only because
    `render` defaulted to Italian; ホーフカペッレ・アイケット would have been a
    confident wrong reading, not a refusal."""
    assert m.render("Wegkapelle", "Q108325", "ja", place="X") is None
    assert m.render("Hofkapelle Aichet", "Q108325", "ja", place="X") is None
    assert m.dedication("Hofkapelle Aichet", "ja") is None


@pytest.mark.parametrize("label,expect", [
    # German compounds carry a genitive: Martin-s-kirche, Peter-s-kirche. The -s
    # is grammar, so listing every saint twice would be the wrong fix.
    ("Martinskirche", "マルティヌス"),
    ("Peterskirche", "ペトロ"),
    ("St. Pauli", "聖パウロ"),
])
def test_a_genitive_compound_resolves_to_the_saint(label, expect):
    assert m.render(label, "Q16970", "ja", place="X") == "Xの" + expect + "教会"


def test_the_genitive_rule_does_not_invent_names():
    """Stripping a suffix must not turn an unknown word into a known one."""
    assert m.name_key("fictitious") is None
    assert m.name_key("martins") == "martin"
    assert m.render("St. Fictitious", "Q16970", "ja", place="X") is None


@pytest.mark.parametrize("label,expect", [
    ("Saint Francis of Assisi church", "聖アッシジのフランチェスコ"),
    ("Sts. Boris and Gleb Church", "ボリスとグレプ"),
    ("Holy Shroud chapel", "聖骸布"),
])
def test_pass_two_additions(label, expect):
    assert m.render(label, "Q16970", "ja", place="X") == "Xの" + expect + "教会"


# ───────── a designation P31 must not hide the building class ─────────

def test_all_p31_statements_are_kept():
    """Wikidata serves the designation first on thousands of these, and keeping only
    the first statement recorded `architectural landmark` and lost `church building`.
    1,749 items were refused for it."""
    ent = {"claims": {"P31": [
        {"mainsnak": {"datavalue": {"value": {"id": "Q2319498"}}}},
        {"mainsnak": {"datavalue": {"value": {"id": "Q16970"}}}},
    ]}}
    assert gen._claim_ids(ent, "P31") == ["Q2319498", "Q16970"]
    assert gen._claim_id(ent, "P31") == "Q2319498"


def test_building_type_skips_past_a_designation():
    meta = {"p31s": ["Q2319498", "Q16970"]}
    assert gen.building_type(meta, m.TYPES) == "Q16970"


def test_building_type_reads_a_legacy_single_p31():
    """A cache written before p31s existed still resolves, so the fix does not force a
    refetch of all 22,542."""
    assert gen.building_type({"p31": "Q16970"}, m.TYPES) == "Q16970"
    assert gen.building_type({"p31": "Q2319498"}, m.TYPES) is None


def test_building_type_is_none_when_no_statement_is_a_type():
    assert gen.building_type({"p31s": ["Q2319498", "Q2065736"]}, m.TYPES) is None
    assert gen.building_type({}, m.TYPES) is None


def test_malformed_snaks_do_not_break_the_walk():
    ent = {"claims": {"P31": [{"mainsnak": {}},
                              {"mainsnak": {"datavalue": {"value": {"id": "Q16970"}}}}]}}
    assert gen._claim_ids(ent, "P31") == ["Q16970"]
