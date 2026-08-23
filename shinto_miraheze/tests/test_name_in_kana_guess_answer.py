"""`GUESS:` — the answer kind for "guess where no kana can be found", and the one
property that makes it safe: it carries NO source.

Emma, 2026-08-23, choosing the full kana-from-jawiki build: pull the kana from the
article, feed the naming pipeline, and guess where no kana can be found.

A first attempt derived the guess mechanically with pykakasi. Measured against the 342
readings already extracted from articles it was **47.7% exact, 52.3% wrong, and 0%
close** — the failures were different words, not spelling slips (江島 えのしま guessed
えじま, 三吉 みよし guessed さんきち, 一宮 いっく guessed いちのみや). Emma: *"Pykakasi is
horrible don't use it lol"*, and *"This is a settled issue."* It is deleted; the guess
comes from the same work-file/ANSWER path that produced the 342 correct readings.

THE LOAD-BEARING DIFFERENCE between KANA and GUESS is the reference. `S143`/`S4656`
asserts "the Japanese Wikipedia article states this". That is true of a KANA answer and
false of a GUESS — the article gave no reading, which is why a guess was asked for.
Attaching it anyway would put a false claim of provenance on Wikidata, and a
sourced-looking wrong reading is worse than an unsourced one because nothing downstream
can tell it apart.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collect_name_in_kana import acceptable_reading, parse_answer  # noqa: E402


def _wf(answer):
    return ("<!-- ITEM: https://www.wikidata.org/wiki/Q1 -->\n"
            "<!-- JA: 三芳野神社 | EN_LABEL: Miyoshino Shrine | BUCKET: a -->\n"
            "<!-- ARTICLE: https://ja.wikipedia.org/wiki/%E4%B8%89%E8%8A%B3%E9%87%8E -->\n"
            f"<!-- ANSWER: {answer} -->\n<!-- TASK: ... -->\n\n== LEAD ==\n...\n")


def test_guess_is_a_recognised_answer_kind():
    assert parse_answer(_wf("GUESS: みよしのじんじゃ")) == ("GUESS", "みよしのじんじゃ")


def test_guess_is_not_confused_with_kana():
    assert parse_answer(_wf("KANA: みよしのじんじゃ"))[0] == "KANA"


def test_no_kana_still_exists_as_an_answer():
    """Answering NO_KANA is still correct when no reading can be derived either —
    the TASK says so explicitly, because a wrong reading is worse than none."""
    assert parse_answer(_wf("NO_KANA: nothing in the lead or elsewhere"))[0] == "NO_KANA"


def test_a_guess_goes_through_the_same_hiragana_gate():
    """GUESS gets no leniency: the gate that rejects an all-katakana or kanji-bearing
    reading applies identically, because P1814 wants a modern hiragana reading whatever
    produced it."""
    assert acceptable_reading("みよしのじんじゃ")
    assert not acceptable_reading("ミヨシノジンジャ")
    assert not acceptable_reading("三芳野じんじゃ")


def test_the_builder_asks_for_guess_and_warns_against_transliterating():
    """The TASK text is the only thing steering the answer, so its content is pinned.

    The named examples are the measured failure modes of the mechanical attempt — if
    they vanish from the prompt, the same class of error comes back."""
    import build_name_in_kana_queue as b
    assert "GUESS:" in b.TASK
    assert "guess where no kana can be found" in b.TASK
    for irregular in ("江島", "三吉", "一宮"):
        assert irregular in b.TASK, irregular
    assert "character-by-character" in b.TASK


def test_the_task_still_offers_no_kana_as_the_out():
    import build_name_in_kana_queue as b
    assert "NO_KANA" in b.TASK
    assert "wrong reading is worse than none" in b.TASK


def test_pykakasi_is_gone():
    """The mechanical guesser was deleted on Emma's ruling. A later session
    reintroducing it would be re-opening something she closed."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert not os.path.exists(os.path.join(root, "shinto_miraheze",
                                           "guess_name_in_kana.py"))
