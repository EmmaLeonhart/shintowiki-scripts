"""An item whose article yields no lead still gets a work-file.

It used to get none, on the reasoning — written into the builder's own output — that
"a later run retries them". Measured 2026-08-23: that is a permanent loop, not a retry.

These items sort to the front of the target set and their articles are redirects,
disambiguation pages, or empty, so the extract will never arrive. Three consecutive
tranches printed an identical four:

    Q11391058  八幡社 (岡崎市大高味町字下屋敷)
    Q11391059  八幡社 (岡崎市鍛埜町)
    Q11391060  八幡社 (岡崎市大高味町字寺下)
    Q11396252  刈田嶺神社 (七ヶ宿町)

Each tranche re-fetched and re-skipped them, and the message read like a deferral.

They were answerable the whole time. 刈田嶺神社 is かったみねじんじゃ — its two siblings
Q11396254 and Q11396255 state that reading in their own leads and were answered from
them the same day. 八幡社 is はちまんしゃ. Emma's 2026-08-23 decision is to guess where no
kana can be found; the no-file rule was what put this case out of reach of it.

So the builder now writes a work-file with the LEAD replaced by NO_LEAD, which says
what happened, says it will not change, and points at what is left to derive from.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_name_in_kana_queue as b  # noqa: E402


def test_no_lead_text_says_it_will_not_change():
    """The reason the old behaviour was wrong is that the extract never arrives. If the
    prompt does not say so, the answerer may reasonably defer instead of deriving."""
    assert "NO LEAD AVAILABLE" in b.NO_LEAD
    assert "never change" in b.NO_LEAD


def test_no_lead_text_names_what_to_derive_from():
    for source in ("place", "same name"):
        assert source in b.NO_LEAD, source


def test_no_lead_text_offers_guess_first_and_no_kana_as_the_fallback():
    assert b.NO_LEAD.index("GUESS") < b.NO_LEAD.index("NO_KANA")
    assert "only if you genuinely" in b.NO_LEAD


def test_a_work_file_is_written_for_a_missing_lead(tmp_path, monkeypatch):
    """The behaviour itself, not just the text."""
    monkeypatch.setattr(b, "OUT_DIR", str(tmp_path))
    b.write_work_file("Q1", "八幡社", "Hachiman Shrine", "八幡社", b.NO_LEAD)
    out = tmp_path / "Q1.wiki"
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "NO LEAD AVAILABLE" in body
    assert "<!-- ANSWER: -->" in body
    assert "GUESS:" in body          # the TASK block is present and offers the path


def test_the_builder_does_not_silently_skip_a_missing_lead():
    """Pinned against the source: a `continue` before write_work_file in that branch is
    exactly the regression, and it is invisible in output because the summary line
    still prints a count."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "build_name_in_kana_queue.py"), encoding="utf-8").read()
    branch = src.split("if not lead:", 1)[1].split("write_work_file(qid, ja, en, title, lead)")[0]
    assert "write_work_file(qid, ja, en, title, NO_LEAD)" in branch
    assert "no file written so a later run retries them" not in src
