"""The daily editor could not encode a time value (2026-07-09).

`parse_qs_value` had no case for QS v1 time syntax (`+1580-00-00T00:00:00Z/9`), so a
time fell through to `{"type": "unknown"}` and `value_to_api_json` POSTed it as a bare
JSON *string*. `wbcreateclaim` cannot decode a string for a time datatype.

Two registered ATOMIC_FILES entries are entirely time-valued — `souken_p571.txt`
(4,119 lines) and `kofun_imports.txt` (870) — and `direct_daily_edits` is the only
path either has (neither is in `submit_daily_batch`'s list). Neither could ever have
landed. Nothing was lost, because the last successful direct-daily-edits run predates
both files; the defect was latent.

These tests pin the encoding, and pin that an unrecognised value token now raises
instead of being POSTed as garbage.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import direct_daily_edits as dde  # noqa: E402

GREGORIAN = "http://www.wikidata.org/entity/Q1985727"


# ------------------------------------------------------------ parsing

def test_year_precision_time_is_parsed():
    v = dde.parse_qs_value("+1580-00-00T00:00:00Z/9")
    assert v["type"] == "time"
    assert v["value"]["time"] == "+1580-00-00T00:00:00Z"
    assert v["value"]["precision"] == 9


def test_century_precision_time_is_parsed():
    """kofun_imports.txt uses /7 (century)."""
    v = dde.parse_qs_value("+0401-00-00T00:00:00Z/7")
    assert v["type"] == "time"
    assert v["value"]["precision"] == 7


def test_time_carries_the_quickstatements_calendar_model():
    v = dde.parse_qs_value("+0807-00-00T00:00:00Z/9")
    assert v["value"]["calendarmodel"] == GREGORIAN


def test_time_is_no_longer_unknown():
    """The regression itself."""
    assert dde.parse_qs_value("+0807-00-00T00:00:00Z/9")["type"] != "unknown"


@pytest.mark.parametrize("raw", [
    "+1580-00-00T00:00:00Z",     # no precision suffix
    "1580-00-00T00:00:00Z/9",    # no sign
    "+1580-00-00/9",             # no time part
])
def test_malformed_time_tokens_are_not_silently_accepted(raw):
    assert dde.parse_qs_value(raw)["type"] == "unknown"


# ------------------------------------------------------------ encoding

def test_time_encodes_to_a_json_object_not_a_string():
    v = dde.parse_qs_value("+1580-00-00T00:00:00Z/9")
    encoded = json.loads(dde.value_to_api_json(v))
    assert isinstance(encoded, dict), "a bare string is what wbcreateclaim rejects"
    assert encoded["time"] == "+1580-00-00T00:00:00Z"
    assert encoded["precision"] == 9
    assert encoded["calendarmodel"] == GREGORIAN


def test_unknown_value_raises_rather_than_posting_garbage():
    with pytest.raises(ValueError, match="unencodable"):
        dde.value_to_api_json({"type": "unknown", "value": "???"})


@pytest.mark.parametrize("raw,kind", [
    ("Q42", "entity"),
    ('"hello"', "string"),
    ('ja:"島根県"', "monolingualtext"),
])
def test_existing_value_kinds_are_unaffected(raw, kind):
    v = dde.parse_qs_value(raw)
    assert v["type"] == kind
    assert isinstance(json.loads(dde.value_to_api_json(v)), (dict, str))


# ------------------------------------------------------------ real lines

REAL_LINES = [
    # souken_p571.txt
    'Q100150003|P571|+1580-00-00T00:00:00Z/9|S4656|"https://ja.wikipedia.org/wiki/X"',
    # kofun_imports.txt
    'Q103903111|P571|+0401-00-00T00:00:00Z/7|S4656|"https://ja.wikipedia.org/wiki/Y"',
]


@pytest.mark.parametrize("line", REAL_LINES)
def test_real_registered_lines_now_encode(line):
    parsed = dde.parse_qs_line(line)
    encoded = json.loads(dde.value_to_api_json(parsed["value"]))
    assert isinstance(encoded, dict)
    assert parsed["references"], "the jawiki citation must survive parsing"


def test_den_line_with_qualifier_and_source_round_trips():
    line = ('Q42|P571|+0807-00-00T00:00:00Z/9|P1480|Q18122778|'
            'S4656|"https://ja.wikipedia.org/wiki/X"')
    parsed = dde.parse_qs_line(line)
    assert json.loads(dde.value_to_api_json(parsed["value"]))["precision"] == 9
    (qprop, qval), = parsed["qualifiers"]
    assert qprop == "P1480"
    assert qval["value"]["id"] == "Q18122778"
    (rprop, rval), = parsed["references"]
    assert rprop == "P4656"
    assert rval["value"].startswith("https://ja.wikipedia.org/")
