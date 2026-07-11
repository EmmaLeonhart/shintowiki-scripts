"""山号 (sangō) import — P1448 + P3831=Q11058522 (Emma 2026-07-10).

山号 is filled on 92% of jawiki temple articles, so every noise pattern below is hit
thousands of times. Each fixture is real text sampled from live jawiki.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_sango_quickstatements as sg  # noqa: E402
import direct_daily_edits as dde  # noqa: E402


# ─────────────────────── real values from jawiki ───────────────────────

@pytest.mark.parametrize("field,expected", [
    ("紫雲山", "紫雲山"),                                        # 中山寺
    ("大内山", "大内山"),                                        # 仁和寺
    ("無量山{{sfn|江戸名所図会|1927|p=6}}", "無量山"),              # 伝通院
    ("瑞鹿山（ずいろくさん）{{sfn|新編鎌倉志|1915|p=69}}", "瑞鹿山"),   # 円覚寺
    ("[[荒陵山]]（あらはかさん、こうりょうざん）", "荒陵山"),            # 四天王寺
    ("[[大山 (神奈川県)|雨降山]]（あぶりさん）{{sfn|新編相模国風土記稿 不動堂}}",
     "雨降山"),                                                # 大山寺 — PIPED link
    ("巨福山（こふくさん）{{efn|[[小袋谷]]と関連}}", "巨福山"),        # 建長寺
    ('練月山<ref name="練馬の寺院">{{Cite book|和書}}</ref>', "練月山"),  # 愛染院
    ("東山（とうざん）", "東山"),                                  # 慈照寺
    ("[[成田山]]", "成田山"),                                     # 新勝寺
    ("多宝富士大日蓮華山", "多宝富士大日蓮華山"),                      # 大石寺 — 9 chars
])
def test_real_jawiki_values_parse(field, expected):
    assert sg.parse_sango(field) == expected


def test_a_piped_wikilink_yields_the_display_text_not_the_target():
    """大山寺's sangō is 雨降山; 大山 (神奈川県) is the mountain's article."""
    assert sg.parse_sango("[[大山 (神奈川県)|雨降山]]") == "雨降山"


def test_a_bare_wikilink_yields_the_target():
    assert sg.parse_sango("[[成田山]]") == "成田山"


# ─────────────────────── refusals ───────────────────────

@pytest.mark.parametrize("field", [
    "",
    None,
    "   ",
    "紫雲山、法雲山",          # two sangō — refuse rather than pick
    "紫雲山/法雲山",
    "紫雲山・法雲山",
    "（ずいろくさん）",         # only a reading
    "しうんざん",             # kana, not a sangō
    "Mount Shiun",           # latin
    "山",                     # single char
    "{{sfn|Foo|2001}}",       # citation only
])
def test_noise_is_refused(field):
    assert sg.parse_sango(field) is None


def test_a_reading_alone_never_becomes_the_value():
    assert sg.parse_sango("（あぶりさん）") is None


def test_an_overlong_run_is_refused():
    assert sg.parse_sango("一" * 13) is None


def test_twelve_kanji_is_accepted():
    assert sg.parse_sango("一" * 12) == "一" * 12


# ─────────────────────── line shape ───────────────────────

def test_line_shape():
    line = sg.qs_line("Q42", "紫雲山", "https://ja.wikipedia.org/wiki/X")
    assert line == ('Q42|P1448|ja:"紫雲山"|P3831|Q11058522|'
                    'S143|Q177837|S4656|"https://ja.wikipedia.org/wiki/X"')


def test_the_role_qid_is_the_verified_one():
    """Q11058522 = sangō, 'a part of name of Buddhist temples (in Japan)'."""
    assert sg.SANGO == "Q11058522"
    assert sg.P_OFFICIAL_NAME == "P1448"
    assert sg.P_ROLE == "P3831"


def test_no_line_is_a_removal():
    assert not sg.qs_line("Q1", "紫雲山", "u").startswith("-")


# ─────────────────────── the daily editor can execute it ───────────────────────

def test_the_daily_editor_parses_the_line():
    line = sg.qs_line("Q42", "紫雲山", "https://ja.wikipedia.org/wiki/X")
    p = dde.parse_qs_line(line)
    assert p["entity"] == "Q42"
    assert p["property"] == "P1448"
    assert p["value"]["type"] == "monolingualtext"
    assert p["value"]["value"] == {"text": "紫雲山", "language": "ja"}
    (qprop, qval), = p["qualifiers"]
    assert qprop == "P3831" and qval["value"]["id"] == "Q11058522"
    refs = dict(p["references"])
    assert refs["P143"]["value"]["id"] == "Q177837"
    assert "P4656" in refs
    assert not p["is_removal"]


def test_a_monolingual_value_encodes_without_raising():
    import json
    line = sg.qs_line("Q42", "紫雲山", "u")
    p = dde.parse_qs_line(line)
    assert json.loads(dde.value_to_api_json(p["value"]))["text"] == "紫雲山"


def test_output_file_is_registered_in_atomic_files():
    assert sg.OUTPUT_FILE in dde.ATOMIC_FILES


# ─────────── the three bugs the 400-article sample exposed ───────────

def test_two_sango_split_by_a_line_break_are_refused_not_fused():
    """泉涌寺: 東山（とうざん）<br/>泉山（せんざん）. Stripping the tag before splitting
    produced "東山泉山" — a sangō that does not exist."""
    assert sg.parse_sango("東山（とうざん）<br/>泉山（せんざん）") is None


def test_three_names_split_by_line_breaks_are_refused():
    """大乗寺 became "東香山椙樹林金獅峯"."""
    field = "東香山（とうこうざん）<br />（林号:）椙樹林<br />金獅峯"
    assert sg.parse_sango(field) is None


def test_sfnp_is_stripped_like_sfn():
    """瀧泉寺: 泰叡山{{Sfnp|江戸名所図会|1927|p=101}} was refused outright."""
    assert sg.parse_sango("泰叡山{{Sfnp|江戸名所図会|1927|p=101}}") == "泰叡山"


def test_harvnb_is_stripped_too():
    assert sg.parse_sango("泰叡山{{Harvnb|Foo|2001}}") == "泰叡山"


def test_yomigana_template_is_unwrapped_not_deleted():
    """華厳寺: {{読み仮名|谷汲山|たにぐみさん}} — the sangō is INSIDE the template."""
    assert sg.parse_sango("{{読み仮名|谷汲山|たにぐみさん}}") == "谷汲山"


def test_a_single_segment_with_a_reading_still_parses():
    assert sg.parse_sango("東山（とうざん）") == "東山"


def test_souken_also_strips_sfnp_now():
    """The citation-template gap was shared: a {{Sfnp}} year could leak into a
    founding date."""
    import generate_souken_quickstatements as souken
    assert souken.parse_year("[[807年]]{{Sfnp|江戸名所図会|1927|p=101}}") == 807
    assert souken.parse_year("[[807年]]{{Harvnb|Foo|1921}}") == 807
