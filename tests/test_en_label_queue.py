"""Stage 4 of the English-label pipeline, as a remote-queue category.

Stage 4 was its own claude.ai routine emitting `chore(en-labels): 5 Sonnet-
translated shrine labels` daily until 2026-07-27, the day Emma moved Claude
accounts. Routines do not survive an account move; the remote_queue drainer was
recreated that night and the label routine was not, so Stage 4 was absent for 52
days while Stages 0-2 kept running and nothing looked broken. Emma's call,
2026-09-17: fold labels into the drainer that already works.

What these tests hold down:

  * **The pool stays capped.** The residual is ~18,000 items against ~1,400 for
    every other category combined, so an uncapped build would make labels ~93% of
    the queue and the drainer's 5 random daily picks would be labels almost every
    time. That is a priority change nobody asked for, and it is invisible once it
    happens -- the queue would just quietly stop working anything else.
  * **A bad answer never becomes a QuickStatement.** A QS line is
    `Qxxx|Len|"..."`, so a quote in the payload does not make a bad label, it
    makes a malformed COMMAND, and the daily submitter would carry whatever that
    parsed to out to Wikidata.
  * **A rejected answer keeps its work-file.** Deleting it would also re-queue
    the item, so a bad answer would cycle forever with nothing to look at.
"""
import io
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "shinto_miraheze"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_en_label_queue as builder  # noqa: E402
import collect_en_labels as collector  # noqa: E402


def _work_file(tmpdir, qid, answer="", kind="shrine", ja="test", kana=""):
    path = os.path.join(tmpdir, f"{qid}.wiki")
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        f"<!-- ITEM: https://www.wikidata.org/wiki/{qid} -->\n"
        f"<!-- KIND: {kind} | JA: {ja} | KANA: {kana} -->\n"
        f"<!-- ANSWER: {answer} -->\n<!-- TASK: ... -->\n"
    )
    return path


# --------------------------------------------------------------------------
# Builder
# --------------------------------------------------------------------------

def test_the_pool_is_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "OUTDIR", str(tmp_path))
    written, already = builder.build(pool=7)
    assert already == 0
    assert written == 7, (
        f"builder wrote {written} work-files for a pool of 7. An uncapped build "
        f"puts ~18,000 label items against ~1,400 of everything else and starves "
        f"every other category out of the drainer's 5 daily picks."
    )
    assert len(list(tmp_path.glob("*.wiki"))) == 7


def test_the_pool_tops_up_rather_than_refilling(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "OUTDIR", str(tmp_path))
    builder.build(pool=5)
    # Two get answered and drain away.
    for p in sorted(tmp_path.glob("*.wiki"))[:2]:
        os.remove(p)
    written, already = builder.build(pool=5)
    assert already == 3
    assert written == 2, "the builder must top the pool back up, not rebuild it"
    assert len(list(tmp_path.glob("*.wiki"))) == 5


def test_a_full_pool_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "OUTDIR", str(tmp_path))
    builder.build(pool=4)
    written, already = builder.build(pool=4)
    assert (written, already) == (0, 4)


def test_queued_items_are_never_already_labelled(tmp_path, monkeypatch):
    """The residual only. Re-queueing a QID that already has a staged label
    would emit a second, competing Len for the same item."""
    monkeypatch.setattr(builder, "OUTDIR", str(tmp_path))
    builder.build(pool=25)
    queued = {p.stem for p in tmp_path.glob("*.wiki")}
    import select_shrines_to_translate as sel
    assert queued, "builder produced nothing; the worklists may be missing"
    assert not (queued & sel.excluded_qids()), (
        "builder queued a QID that already has a label staged in one of the "
        "deterministic or pending en-label files"
    )


def test_the_work_file_carries_what_the_worker_needs(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "OUTDIR", str(tmp_path))
    builder.build(pool=3)
    for p in tmp_path.glob("*.wiki"):
        text = io.open(p, encoding="utf-8").read()
        assert "<!-- ANSWER: -->" in text, "no empty ANSWER marker to fill"
        assert "KIND:" in text and "JA:" in text and "KANA:" in text
        assert "LABEL:" in text and "SKIP:" in text, "the two answer forms"
        assert "wikidata.org/wiki/" in text


# --------------------------------------------------------------------------
# Collector
# --------------------------------------------------------------------------

@pytest.fixture
def wired(tmp_path, monkeypatch):
    work = tmp_path / "en_label"
    work.mkdir()
    qs = tmp_path / "en_labels_sonnet.txt"
    qs.write_text("", encoding="utf-8")
    monkeypatch.setattr(collector, "WORKDIR", str(work))
    monkeypatch.setattr(collector, "QS_OUT", str(qs))
    monkeypatch.setattr(collector, "LOG", str(work / "_resolved.log"))
    return work, qs


def test_a_label_becomes_a_quickstatement_and_drains(wired):
    work, qs = wired
    _work_file(str(work), "Q1", "LABEL: Iino Shrine")
    r = collector.collect()
    assert r["labels"] == 1
    assert qs.read_text(encoding="utf-8").strip() == 'Q1|Len|"Iino Shrine"'
    assert not (work / "Q1.wiki").exists(), "an answered work-file must drain"


def test_a_skip_drains_without_a_quickstatement(wired):
    work, qs = wired
    _work_file(str(work), "Q2", "SKIP: reading unsourceable")
    r = collector.collect()
    assert (r["labels"], r["skipped"]) == (0, 1)
    assert qs.read_text(encoding="utf-8").strip() == ""
    assert not (work / "Q2.wiki").exists()
    assert "SKIP" in (work / "_resolved.log").read_text(encoding="utf-8")


def test_an_empty_answer_is_left_alone(wired):
    work, qs = wired
    _work_file(str(work), "Q3", "")
    r = collector.collect()
    assert r["pending"] == 1
    assert (work / "Q3.wiki").exists(), "an unanswered item must stay queued"
    assert qs.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize("bad", [
    'Bad"Quote Shrine',          # a quote closes the QS value early
    "Pipe|Shrine",               # a pipe adds a QS field
    "Multi\nline Shrine",        # a newline ends the QS command
    "",                          # LABEL: with nothing after it
    "x" * 200,                   # absurd length
])
def test_a_label_that_would_break_the_quickstatement_is_rejected(wired, bad):
    work, qs = wired
    _work_file(str(work), "Q4", f"LABEL: {bad}")
    r = collector.collect()
    assert r["labels"] == 0, f"{bad!r} must not reach the QS file"
    assert qs.read_text(encoding="utf-8").strip() == ""
    assert (work / "Q4.wiki").exists(), (
        "a rejected answer must KEEP its work-file -- deleting it also re-queues "
        "the item, so the bad answer would cycle forever unseen"
    )


def test_a_free_text_answer_is_a_skip_not_a_label(wired):
    """Guessing that an unprefixed string was meant as the label is how a
    sentence of reasoning ends up as a Wikidata label."""
    work, qs = wired
    _work_file(str(work), "Q5", "I could not find a reliable reading for this one")
    r = collector.collect()
    assert r["labels"] == 0
    assert qs.read_text(encoding="utf-8").strip() == ""
    assert not (work / "Q5.wiki").exists()


def test_dry_run_changes_nothing(wired):
    work, qs = wired
    _work_file(str(work), "Q6", "LABEL: Iino Shrine")
    collector.collect(dry_run=True)
    assert qs.read_text(encoding="utf-8") == ""
    assert (work / "Q6.wiki").exists()


# --------------------------------------------------------------------------
# Wiring
# --------------------------------------------------------------------------

def test_remote_queue_emits_the_category():
    import remote_queue
    assert hasattr(remote_queue, "EN_LABEL_INSTRUCTION")
    text = io.open(os.path.join(_ROOT, "remote_queue.py"), encoding="utf-8").read()
    assert '_build_section("en_label", EN_LABEL_INSTRUCTION)' in text, (
        "the en_label section is not registered, so the work-files exist but the "
        "drainer never sees them"
    )


def test_the_instruction_names_both_answer_forms_and_forbids_other_edits():
    import remote_queue
    ins = remote_queue.EN_LABEL_INSTRUCTION
    assert "LABEL:" in ins and "SKIP:" in ins
    assert "Temple" in ins and "Shrine" in ins, "the naming conventions"
    assert "do NOT edit any other file" in ins, (
        "the drainer's own prompt says to touch nothing else; the instruction "
        "must say where the answer goes or the worker has a contradiction"
    )


def test_ci_runs_the_collector_and_the_builder():
    wf = os.path.join(_ROOT, ".github", "workflows", "generate-quickstatements.yml")
    text = io.open(wf, encoding="utf-8").read()
    assert "collect_en_labels" in text, "answers would never reach the QS file"
    assert "build_en_label_queue" in text, "the pool would drain and never refill"
    assert "en_label/" in text, "the work-files would never be committed"
    # The collector must run before the builder: collect answers, then top up.
    assert text.index("collect_en_labels") < text.index("build_en_label_queue")


def test_the_output_file_is_actually_submitted():
    """A label that reaches en_labels_sonnet.txt must be in the drip's atomic
    file list, or Stage 4 is rebuilt and still lands nothing."""
    for rel in ("modern-quickstatements/submit_daily_batch.py",
                "modern-quickstatements/direct_daily_edits.py"):
        text = io.open(os.path.join(_ROOT, rel), encoding="utf-8").read()
        assert "en_labels_sonnet.txt" in text, f"{rel} does not submit it"
