"""Tests for resolve_deleted_qid_ills_202607.rewrite_text (queue #6, no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resolve_deleted_qid_ills_202607 import rewrite_text  # noqa: E402

ONAM = [("Q702140", "Q276944")]
TAIRA = [("Q568647", "Q1079102")]


def test_placeholder_form_ogawa():
    src = "{{ill|Q702140|qid=DELETED_QID|lt=Ōanamuchi-no-Mikoto}}"
    assert rewrite_text(src, ONAM) == "{{ill|Q276944|qid=Q276944|lt=Ōanamuchi-no-Mikoto}}"


def test_raw_deleted_qid_form_nawino():
    src = "{{ill|Q702140|qid=Q702140|lt=Ōnamuchi-no-Mikoto}}"
    assert rewrite_text(src, ONAM) == "{{ill|Q276944|qid=Q276944|lt=Ōnamuchi-no-Mikoto}}"


def test_takeo_taira_keeps_other_positionals():
    src = "{{ill|Taira clan|Q568647|Taira clan|qid=DELETED_QID|lt=Taira clan}}"
    assert rewrite_text(src, TAIRA) == "{{ill|Taira clan|Q1079102|Taira clan|qid=Q1079102|lt=Taira clan}}"


def test_unrelated_ill_untouched():
    src = "{{ill|Ehime Prefecture|en|Ehime Prefecture|qid=Q123376|lt=Ehime}}"
    assert rewrite_text(src, ONAM) == src


def test_idempotent_after_resolution():
    once = rewrite_text("{{ill|Q702140|qid=DELETED_QID|lt=x}}", ONAM)
    assert rewrite_text(once, ONAM) == once  # already resolved -> no further change
