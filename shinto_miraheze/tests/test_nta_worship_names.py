"""Which registry corporations count as a place of worship.

The NTA CSV has no "religious corporation" flag, so the only available test is the
corporation's NAME. That makes the two regexes load-bearing in opposite directions:
too narrow and real shrines never enter the index; too wide and a company's フリガナ
ends up in a file of shrine readings.

Measured on Yamanashi (file 27959): the 神社-only rule found 433 corporations with a
registered furigana, the widened rule 485. Of the 52 added, 34 end in 会 (churches — the
10% population, deliberately excluded), 17 in 社 and 1 in 宮.
"""
import os
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.fetch_nta_religious_readings import is_worship  # noqa: E402


def test_the_obvious_shrines_and_temples():
    for name in ("専徳寺", "船形神社", "金刀比羅神社", "龍華院", "西昌院"):
        assert is_worship(name), name


def test_a_bare_social_or_miya_suffix_is_a_shrine():
    """八幡社 -> ハチマンシャ and 櫻井神明社 -> サクライシンメイシャ are shrines the
    神社-only rule dropped."""
    for name in ("八幡社", "櫻井神明社", "天満宮", "若宮"):
        assert is_worship(name), name


def test_a_corporation_ending_in_sha_is_not_a_shrine():
    """甲州市土地開発公社 is the one that actually slipped through when 社 was added."""
    for name in ("甲州市土地開発公社", "株式会社山梨", "山梨土地開発公社",
                 "日本商工会議所", "山梨県農業協同組合"):
        assert not is_worship(name), name


def test_churches_are_out_of_scope_here():
    """The general religious-building population is the 10% and has its own pipeline.
    Yamanashi alone holds 34 of these with a furigana, so their absence is a decision."""
    for name in ("小笠原純福音教会", "日本基督教団山梨教会", "天理教若神子分教会"):
        assert not is_worship(name), name


def test_an_empty_or_unsuffixed_name_is_not_a_place_of_worship():
    assert not is_worship("")
    assert not is_worship(None)
    assert not is_worship("山梨県")
