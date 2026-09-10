"""A QS globe coordinate must encode, and an unencodable value must stop the block.

`create_items.py --batch lost_shrine_creates.txt --apply` created three items on
2026-09-10 and wrote every statement in each block EXCEPT its `P625`, printing

    ERROR: unencodable QS value '@35.838036/139.337402' — parse_qs_value has no case for it

once per block and carrying on. `parse_qs_value` handled entity, monolingual text,
string, novalue/somevalue and time, and had no `@lat/lon` case, so the value fell
through to `{"type": "unknown"}` and `value_to_api_json` refused it — correctly,
since guessing a datatype is worse. The missing half was the case itself.

Nothing caught it because the three items were still created and the run reported
success. That is the shape worth pinning: the encoder knows the type, AND a value
it does not know is loud.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
if MQ not in sys.path:
    sys.path.insert(0, MQ)

import direct_daily_edits as dde  # noqa: E402


@pytest.mark.parametrize("raw,lat,lon", [
    ("@35.838036/139.337402", 35.838036, 139.337402),
    ("@35.27712826106289/139.17583480745927", 35.27712826106289, 139.17583480745927),
    ("@-33.8688/151.2093", -33.8688, 151.2093),
    ("@0/0", 0.0, 0.0),
])
def test_globe_coordinates_parse(raw, lat, lon):
    parsed = dde.parse_qs_value(raw)
    assert parsed["type"] == "globecoordinate"
    assert parsed["value"]["latitude"] == lat
    assert parsed["value"]["longitude"] == lon
    # QuickStatements' own semantics, so the twin of a QS-written statement matches.
    assert parsed["value"]["globe"] == "http://www.wikidata.org/entity/Q2"
    assert parsed["value"]["precision"] == 1e-6


def test_a_globe_coordinate_survives_serialisation():
    """The refusal in value_to_api_json must not also refuse the new type."""
    out = dde.value_to_api_json(dde.parse_qs_value("@35.838036/139.337402"))
    assert '"latitude": 35.838036' in out and '"longitude": 139.337402' in out


@pytest.mark.parametrize("raw", ["@notanumber/1.0", "@1.0", "@/", "@"])
def test_a_malformed_coordinate_is_still_refused(raw):
    """Widening the encoder must not turn it into a guesser."""
    with pytest.raises(ValueError):
        dde.value_to_api_json(dde.parse_qs_value(raw))


def test_every_coordinate_in_a_create_batch_is_encodable():
    """The batch that exposed this: every @lat/lon in it must now round-trip.

    Reads the real file rather than a fixture, so a future CREATE batch carrying a
    coordinate shape the encoder cannot take fails here instead of silently
    creating an item without it.
    """
    for name in sorted(os.listdir(MQ)):
        if not name.endswith(".txt"):
            continue
        for n, line in enumerate(open(os.path.join(MQ, name), encoding="utf-8"), 1):
            for field in line.strip().split("|"):
                if not field.startswith("@"):
                    continue
                parsed = dde.parse_qs_value(field)
                assert parsed["type"] == "globecoordinate", f"{name}:{n} {field}"
