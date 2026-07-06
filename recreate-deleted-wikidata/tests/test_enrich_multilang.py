"""Tests for enrich_multilang.generate_labels — label-source precedence + coverage.

Imports the real transliteration engine (translit_common); CI installs its deps
(opencc-python-reimplemented, hanja, pykakasi) — see ci.yml.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import enrich_multilang as em


def test_native_en_ja_and_fandom_precedence():
    romaji, labels = em.generate_labels(
        "Amaterasu", "天照", {"de": "Amaterasu (Göttin)", "ja": "天照"})
    # en/ja are native; fandom-provided langs are tagged 'fandom' and win over translit.
    assert labels["en"] == {"label": "Amaterasu", "source": "native"}
    assert labels["ja"]["source"] in ("native", "fandom")
    assert labels["de"] == {"label": "Amaterasu (Göttin)", "source": "fandom"}


def test_many_languages_generated():
    _, labels = em.generate_labels("Amaterasu Omikami", "天照大神", {})
    # The engine should render into a broad language set (Cyrillic/Greek/Arabic/…).
    assert len(labels) >= 20
    assert "ru" in labels and labels["ru"]["source"] == "translit"
    assert all("label" in v and "source" in v for v in labels.values())


def test_empty_inputs_safe():
    romaji, labels = em.generate_labels("", "", {})
    assert labels == {}  # nothing to render, no crash
