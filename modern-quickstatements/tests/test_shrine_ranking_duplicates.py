"""Tests for the shrine-ranking duplicate-property review tables (Emma 2026-07-09).

Two things here are load-bearing and were discovered the hard way:

1. WDQS aborts an over-heavy query *mid-stream*, and signals it by gluing a Java
   stack trace onto an already-``200`` response whose JSON body is therefore
   truncated. ``fetch_sparql`` used to call ``r.json()`` and die on the resulting
   ``JSONDecodeError``, taking the whole generator with it. It must now treat a
   truncated body like a 5xx and retry.

2. SPARQL literals legitimately contain raw newlines (some P6375 addresses do),
   which strict JSON rejects. Parsing must use ``strict=False``.

Plus the ``VALUES``-chunking helpers, and the renderers Emma reads.
"""

import json
import re
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_modern_shrine_ranking_qualifiers as g  # noqa: E402


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    """fetch_sparql sleeps 10s between calls; tests must not."""
    monkeypatch.setattr(g.time, "sleep", lambda *_: None)
    monkeypatch.setattr(g, "_last_sparql_time", 0.0)


class _Resp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status
        self.url = "https://query-main.wikidata.org/sparql"

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.exceptions.HTTPError(str(self.status_code))


def _ok_body(bindings):
    return json.dumps({"results": {"bindings": bindings}})


def test_200_returns_bindings(monkeypatch):
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: _Resp(_ok_body([{"x": {"value": "1"}}])))
    assert g.fetch_sparql("q") == [{"x": {"value": "1"}}]


def test_truncated_200_is_retried_then_succeeds(monkeypatch):
    """A mid-stream WDQS abort must not kill the run."""
    truncated = _ok_body([{"x": {"value": "1"}}])[:40] + (
        "\n\tat org.eclipse.jetty.util.thread.QueuedThreadPool.runJob(QueuedThreadPool.java:765)\n"
    )
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        if len(calls) == 1:
            return _Resp(truncated)
        return _Resp(_ok_body([{"x": {"value": "2"}}]))

    monkeypatch.setattr(g.requests, "get", fake_get)
    assert g.fetch_sparql("q") == [{"x": {"value": "2"}}]
    assert len(calls) == 2


def test_truncated_200_raises_after_retries(monkeypatch):
    truncated = '{"results": {"bindings": [{"x'
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: _Resp(truncated))
    with pytest.raises(RuntimeError, match="truncated"):
        g.fetch_sparql("q")


def test_raw_newline_in_literal_parses(monkeypatch):
    """Some P6375 address literals contain a raw newline; strict JSON rejects them."""
    body = '{"results": {"bindings": [{"addr": {"value": "\n"}}]}}'
    with pytest.raises(ValueError):
        json.loads(body)  # strict mode: this is exactly what used to blow up
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: _Resp(body))
    assert g.fetch_sparql("q") == [{"addr": {"value": "\n"}}]


def test_429_still_bails_immediately(monkeypatch):
    """The 429 policy (bail, no retries past the cap) must survive the change."""
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: _Resp("", status=429))
    with pytest.raises(g.RateLimitError):
        g.fetch_sparql("q")


def test_chunks_and_values():
    assert list(g._chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert g._values(["Q1", "Q2"]) == "VALUES ?item { wd:Q1 wd:Q2 }"


def test_mass_query_chunks_the_values_clause(monkeypatch):
    """The whole point: materialise the item set once, feed it back as VALUES."""
    seen = []

    def fake_fetch(query):
        seen.append(query)
        return [{"item": {"value": "http://www.wikidata.org/entity/Q1"}}]

    monkeypatch.setattr(g, "fetch_sparql", fake_fetch)
    monkeypatch.setattr(g, "VALUES_CHUNK", 2)
    rows = g._mass_query(["Q1", "Q2", "Q3"], "?item ?p ?o .", "?item")
    assert len(seen) == 2
    assert "VALUES ?item { wd:Q1 wd:Q2 }" in seen[0]
    assert "VALUES ?item { wd:Q3 }" in seen[1]
    assert len(rows) == 2  # one per chunk, concatenated


KOKUGAKUIN_NODE = {"P248": ["http://www.wikidata.org/entity/Q135159299"], "P13677": ["182064"]}
JAWIKI_NODE = {"P143": ["http://www.wikidata.org/entity/Q177837"]}


def test_format_citation_reads_like_a_wikipedia_footnote():
    cite = g.format_citation(KOKUGAKUIN_NODE)
    assert "<i>Kokugakuin University Shrine Database</i>" in cite
    assert "https://jmapps.ne.jp/kokugakuin/det.html?data_id=182064" in cite
    assert cite.endswith(".")


def test_format_citation_names_jawiki_rather_than_its_qid():
    assert "Japanese Wikipedia" in g.format_citation(JAWIKI_NODE)


def test_format_citation_titles_a_url():
    node = {"P4656": ["https://ja.wikipedia.org/wiki/%E9%99%B8%E5%A5%A5%E5%9B%BD"]}
    assert "陸奥国" in g.format_citation(node)  # percent-decoded for legibility


def test_footnotes_number_and_dedupe():
    """Identical citations share one number, exactly as a named ref does on Wikipedia."""
    fn = g.Footnotes("t")
    a = fn.cite([KOKUGAKUIN_NODE])
    b = fn.cite([KOKUGAKUIN_NODE])   # same source -> same number
    c = fn.cite([JAWIKI_NODE])
    assert "[1]" in a and "[1]" in b and "[2]" in c
    assert 'href="#t-cite-1"' in a
    rendered = fn.render()
    assert rendered.count("<li ") == 2
    assert 'id="t-cite-1"' in rendered and 'id="t-cite-2"' in rendered


def test_footnotes_uncited_shows_a_dash_not_a_marker():
    fn = g.Footnotes("t")
    assert "uncited" in fn.cite([])
    assert fn.render() == ""


def test_footnotes_multiple_refs_on_one_statement():
    fn = g.Footnotes("t")
    markers = fn.cite([KOKUGAKUIN_NODE, JAWIKI_NODE])
    assert "[1]" in markers and "[2]" in markers


def test_p6375_table_gives_each_address_its_own_column():
    labels = {"Q1": {"ja": "高城神社", "en": "Takagi Shrine"}, "Q2": {"en": "Solo Shrine", "ja": None}}
    details = {"Q1": {"st-a": "宮城県A", "st-b": "宮城県B"}, "Q2": {"st-c": "東京都C"}}
    refs = {"st-a": [KOKUGAKUIN_NODE]}
    html = g.render_p6375_table(["Q1", "Q2"], labels, details, refs, {"Q1": [("1", None)]})
    assert "<th>Address 1</th>" in html and "<th>Address 2</th>" in html
    assert html.count("<tr>") == 3            # header + 2 items
    assert 'class="cited"' in html            # the sourced address
    assert 'class="uncited-cell"' in html     # the unsourced one
    assert html.count("td class='empty'") == 1  # Q2 has no second address
    assert "1/2" in html                      # per-item cited flag Emma sorts on
    assert "<ol class=\"references\">" in html


def test_p361_table_shades_conflated_statements():
    """A statement carrying several P155/P156 values is a collapsed list entry."""
    labels = {"Q1": {"ja": "x", "en": "Shrine X"}, "Q2": {"en": "Prev"}, "Q3": {"en": "Prev2"},
              "Q4": {"en": "Next"}, "Q9": {"en": "List of Shikinaisha in Mutsu Province"}}
    details = {
        "Q1": {
            "st-a": {"target": "Q9", "ordinal": "25", "follows": {"Q2", "Q3"}, "followedBy": {"Q4"}},
            "st-b": {"target": "Q9", "ordinal": "26", "follows": {"Q3"}, "followedBy": {"Q4"}},
        }
    }
    html = g.render_p361_table(["Q1"], labels, details, {})
    assert html.count('class="conflated"') == 1
    assert "after <a" in html and "before <a" in html
    assert "List of Shikinaisha in Mutsu Province" in html   # named, not Q9-as-text
    assert "<th>Statement 2</th>" in html


def test_p1448_table_shows_kana_and_entries():
    labels = {"Q1": {"ja": "夷針神社", "en": "Iharino Shrine"}, "Q193292": {"en": "Heian period"}}
    details = {"Q1": {"st-a": {"name": "夷針神社", "kana": {"イハリノ"}, "period": "Q193292"}}}
    html = g.render_p1448_table(["Q1"], labels, details, {}, {"Q1": [("181765", "1")]})
    assert "イハリノ" in html
    assert "Heian period" in html   # the period is named, not shown as Q193292
    assert "data_id=181765" in html
    assert "§1" in html


def _text(html):
    """Visible text only — the QID legitimately appears inside href attributes."""
    return re.sub(r"<[^>]+>", " ", html)


def test_shrine_cell_leads_with_the_english_label():
    """Emma 2026-07-09: QIDs instead of English labels made the table illegible."""
    text = _text(g.shrine_cell("Q59282644", {"Q59282644": {"ja": "高城神社", "en": "Takagi Shrine"}}))
    assert text.index("Takagi Shrine") < text.index("Q59282644")
    assert "高城神社" in text


def test_shrine_cell_falls_back_to_ja_then_qid():
    assert "高城神社" in g.shrine_cell("Q1", {"Q1": {"ja": "高城神社", "en": None}})
    assert "Q1" in g.shrine_cell("Q1", {})


def test_html_escape_applied_to_labels():
    html = g.shrine_cell("Q1", {"Q1": {"ja": "<script>", "en": None}})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_dup_exceptions_hold_out_emmas_reviewed_items():
    """Emma 2026-07-09: Izawa-no-Miya and Izumo-daijingū have correct addresses."""
    assert "Q10885171" in g.DUP_EXCEPTIONS["P6375"]
    assert "Q10896675" in g.DUP_EXCEPTIONS["P6375"]
    assert "Q11379325" in g.DUP_EXCEPTIONS["P6375"]
    # every exception carries a stated reason, so it is never a silent drop
    for prop, items in g.DUP_EXCEPTIONS.items():
        assert prop in g.DUP_PROPS
        for q, reason in items.items():
            assert q.startswith("Q") and reason.strip()


def test_script_pair_is_the_same_address_written_twice():
    """Emma 2026-07-09: two addresses, one Japanese + one romanised => not a conflict."""
    assert g.is_script_pair(["374 Isobe-chō Kaminogō, Mie-ken", "三重県志摩市磯部町上之郷374"])
    assert g.is_script_pair(["三重県志摩市磯部町上之郷374", "374 Isobe-chō Kaminogō, Mie-ken"])


def test_script_pair_rejects_two_japanese_addresses():
    """Two genuinely different Japanese addresses are a real conflict."""
    assert not g.is_script_pair(["埼玉県入間市宮寺", "埼玉県入間郡毛呂山町岩井西5-17-1"])


def test_script_pair_rejects_more_than_two():
    assert not g.is_script_pair(["Kyoto-fu", "京都府亀岡市千歳町出雲無番地", "京都府亀岡市千歳町千歳"])


def test_script_pair_macron_romanisation_is_not_cjk():
    """ō is non-ASCII but not CJK — testing for ASCII would misclassify this."""
    assert g.is_script_pair(["Izumo-daijingū, Kyōto-fu", "京都府亀岡市"])


def test_script_pair_detects_kana_not_just_kanji():
    assert g.is_script_pair(["Hiragana-ken", "ひらがな県"])


def test_still_duplicated_drops_items_the_count_query_lied_about():
    """WDQS moves between the COUNT query and the detail query.

    Emma ran the uncited-address removals in that gap on 2026-07-09 and 40 items
    whose count said 2 came back with one address. A one-address row in a
    duplicates table is meaningless.
    """
    details = {"Q1": {"st-a": "A", "st-b": "B"}, "Q2": {"st-c": "C"}, "Q3": {}}
    assert g.still_duplicated(["Q1", "Q2", "Q3"], details) == ["Q1"]


def test_still_duplicated_preserves_order():
    details = {"Q9": {"a": 1, "b": 2}, "Q1": {"c": 1, "d": 2}}
    assert g.still_duplicated(["Q9", "Q1"], details) == ["Q9", "Q1"]


def test_empty_table_says_nothing_left_rather_than_rendering_an_empty_table():
    """Emma: 'If there's just nothing, then just say there's nothing.'"""
    html = g.render_p6375_table([], {}, {}, {}, {})
    assert "Nothing left here" in html
    assert "<table" not in html


def test_p6375_table_never_renders_a_single_address_row():
    """Guard the exact defect: one address is not a duplicate."""
    labels = {"Q1": {"en": "One Address Shrine"}}
    details = {"Q1": {"st-a": "静岡県熱海市網代172"}}
    kept = g.still_duplicated(["Q1"], details)
    assert kept == []
    assert "Nothing left here" in g.render_p6375_table(kept, labels, details, {}, {})
