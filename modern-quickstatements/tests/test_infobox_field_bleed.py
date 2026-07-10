"""Infobox field values must end at the next `|`, not at the newline.

Found 2026-07-10 while regenerating souken_p571.txt. 本願寺西山別院 puts its whole
infobox on one line:

    |創建=平安時代|開基=|中興年=[[1314年|1314年（正和3年）]]|正式名=…

`([^\\n]*)` captured everything after `創建=`, so the *restoration* year 1314 was
imported as the temple's founding date. Two more temples had the same defect. They
were caught only because the bled text contained `中興`, which the parser had just
started refusing — a bled parameter carrying a bare year would have leaked silently.

`generate_saijin_quickstatements` and `generate_honzon_quickstatements` had always
bounded the capture correctly. `souken`, `kofun` and `p3225` had not.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_souken_quickstatements as souken  # noqa: E402
import generate_kofun_quickstatements as kofun  # noqa: E402
import generate_p3225_quickstatements as p3225  # noqa: E402
import generate_saijin_quickstatements as saijin  # noqa: E402
import generate_honzon_quickstatements as honzon  # noqa: E402

# The real article text that produced the wrong import.
NISHIYAMA = ("{{日本の寺院|創建年=平安時代|開基=|中興年=[[1314年|1314年（正和3年）]]"
             "|中興=覚如|正式名=本願寺西山別院|別称=西山御坊}}")
KITAYAMA = ("{{日本の寺院|創建年=|開基=|中興年=[[1680年|1680年（延宝8年）]]|中興="
            "|正式名=本願寺北山別院}}")


def _capture(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None


# ─────────────────────── souken ───────────────────────

def test_one_line_infobox_does_not_bleed_the_next_parameter():
    value = _capture(souken.CONFIGS[1][1], NISHIYAMA)
    assert value == "平安時代"
    assert "1314" not in value


def test_the_bled_restoration_year_is_no_longer_importable():
    value = _capture(souken.CONFIGS[1][1], NISHIYAMA)
    assert souken.parse_year(value) is None


def test_an_empty_field_captures_empty_not_the_rest_of_the_infobox():
    value = _capture(souken.CONFIGS[1][1], KITAYAMA)
    assert value == ""
    assert souken.parse_year(value) is None


def test_a_pipe_inside_a_wikilink_is_not_a_boundary():
    """Era links look like [[大同 (日本)|大同]] — the pipe must not end the field."""
    text = "|創建 = [[大同 (日本)|大同]]2年（[[807年]]）\n"
    value = _capture(souken.CONFIGS[0][1], text)
    assert value.strip() == "[[大同 (日本)|大同]]2年（[[807年]]）"
    assert souken.parse_year(value) == 807


def test_a_pipe_inside_a_template_is_not_a_boundary():
    text = "|創建 = [[807年]]{{sfn|Foo|2001|p=9}}\n"
    value = _capture(souken.CONFIGS[0][1], text)
    assert "sfn" in value
    assert souken.parse_year(value) == 807


def test_a_multiline_field_still_stops_at_the_newline():
    text = "|創建 = [[807年]]\n|別名 = [[1997年]]\n"
    value = _capture(souken.CONFIGS[0][1], text)
    assert "1997" not in value
    assert souken.parse_year(value) == 807


def test_br_tags_survive_the_capture():
    """竹林寺's field relies on <br /> to separate founding from 再興."""
    text = "|創建年 = 伝・[[奈良時代]]初期<br />再興：[[平成]]9年（[[1997年]]）\n"
    value = _capture(souken.CONFIGS[1][1], text)
    assert "<br />" in value and "1997" in value


# ─────────────────────── kofun & p3225 ───────────────────────

def test_kofun_shape_field_stops_at_the_pipe():
    text = "{{日本の古墳|形状=前方後円墳|築造時期=[[4世紀]]}}"
    assert _capture(kofun._FIELD_SHAPE.pattern, text) == "前方後円墳"


def test_kofun_period_field_stops_at_the_pipe():
    text = "{{日本の古墳|築造時期=[[4世紀]]|被葬者=誰か}}"
    value = _capture(kofun._FIELD_PERIOD.pattern, text)
    assert value == "[[4世紀]]"
    assert "被葬者" not in value


def test_p3225_field_stops_at_the_pipe():
    text = "{{日本の寺院|法人番号=1234567890123|正式名=某寺}}"
    value = _capture(p3225._FIELD_RE.pattern, text)
    assert value == "1234567890123"


# ───────────── the ordered-alternation bug (saijin / honzon) ─────────────
#
# saijin and honzon DID bound the capture at `|`, but wrote the alternation as
#     ((?:[^\n|]|\[\[…\]\]|\{\{…\}\})*)
# Alternation is ordered, so `[^\n|]` ate `[`, `[`, `天`, `照`… and halted at the
# pipe INSIDE the wikilink; `\[\[…\]\]` never got a chance.

THREE_DEITIES = "|祭神 = [[天照大神|天照大御神]]、[[素戔嗚尊]]、[[大国主|大国主命]]\n"


def test_saijin_no_longer_truncates_at_a_piped_wikilink():
    """It used to capture "[[天照大神", silently dropping two of the three deities."""
    value = _capture(saijin._FIELD_RE.pattern, THREE_DEITIES)
    assert value.strip() == "[[天照大神|天照大御神]]、[[素戔嗚尊]]、[[大国主|大国主命]]"
    assert "素戔嗚尊" in value and "大国主" in value


def test_saijin_still_stops_at_a_bare_pipe():
    text = "|祭神 = [[天照大神|天照大御神]]|創建 = [[807年]]\n"
    assert "807" not in _capture(saijin._FIELD_RE.pattern, text)


def test_honzon_no_longer_truncates_at_a_piped_wikilink():
    text = "|本尊 = [[阿弥陀如来|阿弥陀仏]]、[[観音菩薩]]\n"
    assert "観音菩薩" in _capture(honzon._FIELD_RE.pattern, text)


ALL_PATTERNS = [souken.CONFIGS[0][1], souken.CONFIGS[1][1],
                kofun._FIELD_SHAPE.pattern, kofun._FIELD_PERIOD.pattern,
                p3225._FIELD_RE.pattern,
                saijin._FIELD_RE.pattern, honzon._FIELD_RE.pattern]


@pytest.mark.parametrize("pattern", ALL_PATTERNS)
def test_no_generator_captures_to_the_newline(pattern):
    """If a new generator writes `([^\\n]*)`, this fails."""
    assert r"([^\n]*)" not in pattern, pattern


@pytest.mark.parametrize("pattern", ALL_PATTERNS)
def test_bracketed_alternatives_come_before_the_character_class(pattern):
    """`[^\\n|]` must be LAST, or it wins and halts at the pipe inside a wikilink."""
    body = pattern[pattern.index("((?:"):]
    assert body.index(r"\[\[") < body.index(r"[^\n|]"), pattern


@pytest.mark.parametrize("pattern", ALL_PATTERNS)
def test_every_generator_keeps_a_piped_wikilink_whole(pattern):
    """Behavioural, not just shape: build a field for each and check nothing is lost."""
    name = pattern.split(r"\s*=")[0].replace(r"\|\s*", "")
    name = name.replace("(?:時期|年代)", "時期")
    text = "|{} = [[A (x)|A]]、[[B]]\n".format(name)
    m = re.search(pattern, text)
    assert m is not None, pattern
    assert "[[B]]" in m.group(1), (pattern, m.group(1))
