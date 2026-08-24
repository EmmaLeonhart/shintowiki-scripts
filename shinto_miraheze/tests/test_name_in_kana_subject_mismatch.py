"""Flag a work-file whose LEAD is about a different shrine from the item.

The dangerous case, found 2026-08-24 across four items answered by hand:

    Q11549618  千住氷川神社      lead is a bare 氷川神社（ひかわじんじゃ）
    Q11557473  南沢氷川神社      lead is a bare 氷川神社（ひかわじんじゃ）
    Q11556511  洲崎濱宮神明神社  lead is about 海山道神社（みやまどじんじゃ）
    Q11391067  坂本神社八幡宮    lead is a bare 八幡神社（はちまんじんじゃ）

It is worse than a missing reading. The lead states one cleanly, in the usual
parenthetical, so an answer copied from it looks well-sourced — and the collector then
attaches S143/S4656, asserting the Japanese Wikipedia article backs a reading of a name
the article never mentions. A wrong unsourced reading is recoverable; a wrong SOURCED
one is what "visibility is worse than data loss" exists for. Nothing in the answer
format makes anyone compare the item's label to the lead's subject, so the builder does
it.

Every case below is real — taken from work-files actually answered this session, not
invented — because the first version of this check got two of them wrong in each
direction: it passed 千住氷川神社 (the lead's name is a substring of the item's, which
plain containment reads as a match) and flagged 利雁/利鴈 and 尾崎/尾﨑, which are one
shrine with a variant kanji.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from build_name_in_kana_queue import (  # noqa: E402
    MISMATCH, lead_subject, subject_mismatch, write_work_file,
)


@pytest.mark.parametrize("ja,lead", [
    ("千住氷川神社", "氷川神社（ひかわじんじゃ）は、東京都足立区千住4丁目にある神社。"),
    ("南沢氷川神社", "氷川神社（ひかわじんじゃ）は、東京都東久留米市南沢にある神社。"),
    ("洲崎濱宮神明神社", "海山道神社（みやまどじんじゃ）は三重県四日市市海山道町にある神社である。"),
    ("坂本神社八幡宮", "八幡神社（はちまんじんじゃ）は、岐阜県中津川市千旦林に鎮座する神社。"),
])
def test_a_lead_about_another_shrine_is_flagged(ja, lead):
    assert subject_mismatch(ja, lead) is not None


@pytest.mark.parametrize("ja,lead,why", [
    ("三芳野神社", "三芳野神社（みよしのじんじゃ）は、埼玉県川越市郭町の神社。",
     "the ordinary case"),
    ("加賀神社 (松江市)", "加賀神社（かかじんじゃ）は、島根県松江市島根町にある神社。",
     "the item's disambiguator is not part of the name"),
    ("利雁神社", "利鴈神社（とかりじんじゃ）は、大阪府羽曳野市尺度にある神社である。",
     "variant kanji 雁/鴈, one shrine"),
    ("尾崎神社", "尾﨑神社（おざきじんじゃ）は、石川県金沢市にある神社。",
     "variant kanji 崎/﨑, one shrine"),
    ("熊野神社 (高島市)", "本項目で扱う滋賀県高島市の熊野神社（くまのじんじゃ）は、式内社である。",
     "the lead's subject is prose containing the name"),
    ("桜山八幡宮", "桜山八幡宮（さくらやまはちまんぐう）（正字は櫻山八幡宮）は、岐阜県高山市にある神社である。",
     "a 正字 note after the reading"),
])
def test_lookalikes_are_not_flagged(ja, lead, why):
    assert subject_mismatch(ja, lead) is None, why


def test_a_kanji_gloss_inside_the_name_is_not_the_reading_paren():
    """舊府神社 is led as 舊府（旧府）神社（ふるふじんじゃ）. Stopping at the FIRST paren gives
    舊府, which reads as a mismatch against 舊府神社 — a false positive on the detector's
    first live tranche. A parenthetical with no kana in it is a spelling gloss sitting
    inside the name, not the reading."""
    lead = "舊府（旧府）神社（ふるふじんじゃ）は、大阪府和泉市にある神社。"
    assert lead_subject(lead) == "舊府神社"
    assert subject_mismatch("舊府神社", lead) is None


def test_a_paren_that_does_carry_kana_is_still_the_reading():
    lead = "花窟神社（花の窟神社、はなのいわやじんじゃ）は三重県熊野市有馬町に所在する神社。"
    assert lead_subject(lead) == "花窟神社"
    assert subject_mismatch("花窟神社", lead) is None


def test_lead_subject_stops_at_the_first_paren():
    assert lead_subject("氷川神社（ひかわじんじゃ）は、東京都…") == "氷川神社"
    assert lead_subject("氷川神社(ひかわ)は…") == "氷川神社"


def test_lead_subject_falls_back_to_ha_when_there_is_no_paren():
    assert lead_subject("安閑神社は、滋賀県高島市にある神社である。") == "安閑神社"


def test_no_lead_and_no_name_are_not_mismatches():
    assert subject_mismatch("三芳野神社", "") is None
    assert subject_mismatch("", "氷川神社（ひかわ）は…") is None


def test_the_warning_lands_in_the_work_file_and_says_not_to_copy(tmp_path, monkeypatch):
    import build_name_in_kana_queue as b
    monkeypatch.setattr(b, "OUT_DIR", str(tmp_path))
    write_work_file("Q1", "千住氷川神社", "Senju Hikawa Shrine", "氷川神社_(足立区千住)",
                    "氷川神社（ひかわじんじゃ）は、東京都足立区千住4丁目にある神社。")
    body = (tmp_path / "Q1.wiki").read_text(encoding="utf-8")
    assert "THE LEAD IS ABOUT A DIFFERENT NAME" in body
    assert "Do NOT copy the lead's reading as KANA" in body
    assert "GUESS" in body and "NO_KANA" in body
    # and it must sit ABOVE the answer marker, or it is decoration
    assert body.index("DIFFERENT NAME") < body.index("<!-- ANSWER:")


def test_an_ordinary_work_file_carries_no_warning(tmp_path, monkeypatch):
    import build_name_in_kana_queue as b
    monkeypatch.setattr(b, "OUT_DIR", str(tmp_path))
    write_work_file("Q2", "三芳野神社", "Miyoshino Shrine", "三芳野神社",
                    "三芳野神社（みよしのじんじゃ）は、埼玉県川越市郭町の神社。")
    assert "DIFFERENT NAME" not in (tmp_path / "Q2.wiki").read_text(encoding="utf-8")


def test_the_warning_text_names_both_names():
    out = MISMATCH.format(ja="千住氷川神社", subject="氷川神社")
    assert "千住氷川神社" in out and "氷川神社" in out
