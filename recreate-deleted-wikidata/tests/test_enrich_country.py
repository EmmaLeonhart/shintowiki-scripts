"""Unit tests for the pure country classifier in enrich_country."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import enrich_country as c  # noqa: E402


def test_shrine_gets_japan():
    assert c.country_for("Shinto shrine") == ("Q17", "Japan")


def test_festival_temple_kofun_get_japan():
    assert c.country_for("festival") == ("Q17", "Japan")
    assert c.country_for("Buddhist temple") == ("Q17", "Japan")
    assert c.country_for("kofun") == ("Q17", "Japan")


def test_kami_and_human_and_book_skip_country():
    # A deity / person / text is NOT given P17 from this pass.
    assert c.country_for("kami") == (None, None)
    assert c.country_for("human") == (None, None)
    assert c.country_for("book") == (None, None)


def test_untyped_skips():
    assert c.country_for(None) == (None, None)
    assert c.country_for("") == (None, None)
