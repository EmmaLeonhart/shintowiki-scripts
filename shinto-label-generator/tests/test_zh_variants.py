"""Tests for zh_variants — B3a: emit zh script variants from the simplified base.
Simplified codes reuse the base; traditional codes are OpenCC-converted."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_chinese_quickstatements import zh_variants  # noqa: E402


def test_has_all_variant_codes():
    v = zh_variants("护国神社")
    assert set(v) == {"zh-hans", "zh-cn", "zh-sg", "zh-hant", "zh-tw", "zh-hk"}


def test_simplified_codes_reuse_base():
    v = zh_variants("护国神社")
    assert v["zh-hans"] == "护国神社"
    assert v["zh-cn"] == "护国神社"
    assert v["zh-sg"] == "护国神社"


def test_traditional_codes_are_converted():
    v = zh_variants("护国神社")
    assert v["zh-hant"] == "護國神社"
    assert v["zh-tw"] == "護國神社"
    assert v["zh-hk"] == "護國神社"


def test_already_traditional_chars_unchanged():
    # 神社 is identical in simplified and traditional
    v = zh_variants("神社")
    assert v["zh-hant"] == "神社"
    assert v["zh-hans"] == "神社"
