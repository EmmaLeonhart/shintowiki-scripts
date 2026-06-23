"""Tests for temple Stage 2 (identical-name reuse for Japanese temples).

Drives the shared `run()` with the temple worklist/triples/output and a stubbed
SPARQL so no network is needed. Same reuse principle as shrines.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_identical_name_en_labels as core  # noqa: E402
import generate_temple_identical_name_en_labels as tmpl  # noqa: E402


def test_temple_module_uses_temple_class_and_paths():
    assert core.TEMPLE_TRIPLES == "wdt:P31 wd:Q5393308 ; wdt:P17 wd:Q17"
    assert tmpl.OUTPUT_FILE.endswith("temple_identical_name_en_labels.txt")
    assert tmpl.TEMPLE_WORKLIST.endswith("temples_missing_en_label.json")


def test_run_reuses_same_name_temple_label(tmp_path, monkeypatch):
    # Two temples share the ja name 妙法寺; one (the candidate) already has an en
    # label on Wikidata, so the no-en target should reuse it.
    worklist = tmp_path / "temples_missing_en_label.json"
    worklist.write_text(json.dumps({"items": [
        {"qid": "Q1", "ja": "妙法寺", "kana": ""},   # target: no kana, no en
    ]}), encoding="utf-8")
    out = tmp_path / "temple_identical_name_en_labels.txt"

    # Stub the SPARQL batch: 妙法寺 -> "Myoho-ji Temple" on some other temple.
    def fake_fetch(chunk, retries=3, instance_triples=core.SHRINE_TRIPLES):
        assert instance_triples == core.TEMPLE_TRIPLES  # temple-scoped candidates
        return [{"ja": {"value": "妙法寺"}, "en": {"value": "Myoho-ji Temple"}}]
    monkeypatch.setattr(core, "fetch_batch", fake_fetch)

    core.run(worklist=str(worklist), output_file=str(out),
             instance_triples=core.TEMPLE_TRIPLES, kind="temples")

    assert out.read_text(encoding="utf-8").strip() == 'Q1|Len|"Myoho-ji Temple"'


def test_run_skips_kana_targets(tmp_path, monkeypatch):
    # kana-bearing temples are Stage 1's job -> Stage 2 has no targets -> empty out.
    worklist = tmp_path / "temples_missing_en_label.json"
    worklist.write_text(json.dumps({"items": [
        {"qid": "Q9", "ja": "金閣寺", "kana": "きんかくじ"},
    ]}), encoding="utf-8")
    out = tmp_path / "temple_identical_name_en_labels.txt"
    monkeypatch.setattr(core, "fetch_batch", lambda *a, **k: [])

    core.run(worklist=str(worklist), output_file=str(out),
             instance_triples=core.TEMPLE_TRIPLES, kind="temples")
    assert out.read_text(encoding="utf-8") == ""
