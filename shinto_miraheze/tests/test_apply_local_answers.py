"""The six queues apply_local_answers.py offers are not one shape, and treating
them as one made three of the six dead.

queue.md A1 names this script as the road for draining a queue locally:
``apply_local_answers.py --queue <q> --answers <tsv> --apply``, then the collector.
It advertised six ``--queue`` choices while implementing exactly one shape — key is
a QID, file is ``<key>.wiki``, marker is ``<!-- ANSWER: -->``. Measured 2026-08-23
by running it:

  * ``category_translation`` is not QID-keyed at all. Files are named after the
    URL-encoded category title and the marker is ``TRANSLATED``. Every row was
    dropped by a ``^Q\\d+$`` filter that ran BEFORE any counter, so a real batch
    printed ``would write 0 answer(s) (0 gone, 0 answered, 0 with no marker)`` —
    which is byte-identical to a correct run on an empty batch. 338 pending files.
  * ``description_enrichment`` uses an ``ANSWERS`` BLOCK, and ``ANSWER:`` does not
    match ``ANSWERS:``. Worse, its work-files are named after the group's FIRST
    member while the answerable members are the OTHER QIDs inside the block, so
    ``<key>.wiki`` finds the wrong file or none. 69 pending files.
  * The four ANSWER/QID queues were fine.

So the tests below pin the three shapes separately, plus the two failures that were
silent rather than loud.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apply_local_answers import (  # noqa: E402
    QUEUES, block_line_re, fill, load_answers, marker_re, safe_filename,
)


# --- the marker names must match what each collector actually looks for --------

def test_every_queue_declares_a_directory_marker_and_key_kind():
    for name, spec in QUEUES.items():
        assert len(spec) == 3, name
        assert spec[2] in ("qid", "member", "category"), name


def test_answer_marker_does_not_also_match_answers():
    """The difference between ANSWER and ANSWERS is the whole description bug."""
    block = "<!-- ANSWERS:\nQ1: \n-->"
    assert marker_re("ANSWER").search(block) is None
    assert marker_re("ANSWERS").search(block) is not None


def test_scalar_marker_round_trips_with_normalised_spacing():
    """`\\s*` after the colon is greedy, so a naive splice emitted
    `<!-- TRANSLATED:  value-->`. Parseable, but not the shape the routine writes."""
    for body in ("<!-- TRANSLATED:  -->", "<!-- TRANSLATED: -->", "<!--TRANSLATED:-->"):
        m = marker_re("TRANSLATED").search(body)
        assert m is not None, body
        assert m.group(2).strip() == ""
        out = body[:m.start()] + fill(m.group(1), "Category:History of Inabe",
                                      m.group(3)) + body[m.end():]
        assert out.endswith("TRANSLATED: Category:History of Inabe -->"), out


def test_the_collector_parses_what_this_script_writes():
    """Pinned against the collector's own regex, not a copy of it."""
    import collect_category_translations as c
    body = "<!-- TRANSLATED:  -->"
    m = marker_re("TRANSLATED").search(body)
    out = fill(m.group(1), "Category:History of Inabe", m.group(3))
    assert c._TRANSLATED_RE.search(out).group(1) == "Category:History of Inabe"


def test_scalar_marker_sees_an_existing_answer():
    m = marker_re("ANSWER").search("<!-- ANSWER: KANA: みしまたいしゃ -->")
    assert m.group(2).strip() == "KANA: みしまたいしゃ"


# --- the ANSWERS block is per-member lines, not one value ---------------------

BLOCK = ("<!-- GROUP: id|Kuil Kaizan -->\n"
         "<!-- ANSWERS:\n"
         "Q97013988: \n"
         "Q97013999: already written\n"
         "-->\n")


def test_block_line_targets_one_member_and_leaves_the_others():
    m = block_line_re("Q97013988").search(BLOCK)
    assert m is not None and m.group(2) == ""
    out = BLOCK[:m.start()] + m.group(1) + "Shinto shrine in Tainan" + BLOCK[m.end():]
    assert "Q97013988: Shinto shrine in Tainan\n" in out
    assert "Q97013999: already written\n" in out


def test_block_line_reports_an_already_filled_member():
    assert block_line_re("Q97013999").search(BLOCK).group(2) == "already written"


def test_block_line_does_not_match_a_qid_that_is_only_a_prefix():
    """Q9701 must not match the Q97013988 line — an off-by-prefix write would put
    one member's description onto another member."""
    assert block_line_re("Q9701").search(BLOCK) is None


# --- the category filename rule must mirror the builder ----------------------

def test_category_filename_matches_the_builder_rule():
    assert (safe_filename("Category:いなべの Municipal History")
            == "Category%3Aいなべの Municipal History.wiki")
    assert safe_filename("Category:A/B") == "Category%3AA%2FB.wiki"


def test_the_builder_and_this_script_agree_on_the_rule():
    """Pinned against the builder itself, not against a copy of its output."""
    import build_category_translation_queue as b
    for name in ("いなべの Municipal History", "A/B", "七福神めぐり"):
        assert safe_filename("Category:" + name) == b._safe_filename(name)


# --- a row that cannot be used is reported, never dropped --------------------

def _tsv(tmp_path, text):
    p = tmp_path / "answers.tsv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_category_rows_are_accepted_for_the_category_queue(tmp_path):
    ok, bad = load_answers(
        _tsv(tmp_path, "Category:X\tCategory:Y\n"), "category")
    assert ok == [("Category:X", "Category:Y")] and bad == []


def test_a_qid_row_in_a_category_batch_is_rejected_loudly(tmp_path):
    ok, bad = load_answers(_tsv(tmp_path, "Q999\tbogus\n"), "category")
    assert ok == []
    assert len(bad) == 1 and bad[0][0] == 1 and "not a 'Category" in bad[0][2]


def test_a_category_row_in_a_qid_batch_is_rejected_loudly(tmp_path):
    ok, bad = load_answers(_tsv(tmp_path, "Category:X\tCategory:Y\n"), "qid")
    assert ok == [] and len(bad) == 1 and "not a QID" in bad[0][2]


def test_a_one_column_row_is_rejected_with_its_line_number(tmp_path):
    ok, bad = load_answers(_tsv(tmp_path, "# note\n\nQ1\tfine\nbroken\n"), "qid")
    assert ok == [("Q1", "fine")]
    assert len(bad) == 1 and bad[0][0] == 4 and "two tab-separated" in bad[0][2]


def test_comments_and_blank_lines_are_not_counted_as_rejections(tmp_path):
    ok, bad = load_answers(_tsv(tmp_path, "# header\n\n  \nQ1\ta\n"), "qid")
    assert ok == [("Q1", "a")] and bad == []
