"""The suffix-based bunrei generator is time-boxed and must stop cleanly.

Emma 2026-08-03 (queue A0b): keep it ~6 months, then STOP. It is deliberately
"inaccurate but descriptive" — an approximately-right, visible statement invites
human correction and seeds the convention — but it is not perpetual maintenance,
and the per-shrine Opus pass is the accurate layer that replaces it.

The subtle part is HOW it stops. main() opens the output with "w", so a
post-sunset run that simply produced no lines would truncate bunrei.txt and
destroy whatever the daily drip has not yet delivered. The gate therefore has to
fire before the file is opened — and before the SPARQL, since querying for a
result that will be thrown away is pure load on a service we are already told not
to hammer.
"""
import datetime
import importlib.util
import io
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)


def _load():
    spec = importlib.util.spec_from_file_location(
        "generate_bunrei_quickstatements",
        os.path.join(MQ, "generate_bunrei_quickstatements.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load()


def test_sunset_is_the_documented_date():
    assert gen.SUNSET == datetime.date(2027, 2, 1)


def test_gate_is_open_before_the_date_and_closed_after():
    assert not gen.sunset_reached(datetime.date(2027, 1, 31))
    assert gen.sunset_reached(datetime.date(2027, 2, 1))      # inclusive
    assert gen.sunset_reached(datetime.date(2030, 1, 1))


class _Out(io.StringIO):
    """Stands in for sys.stdout AND its .buffer.

    main() does `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)`, which
    under pytest wraps the capture object's buffer and leaves it closed at
    teardown (remote_queue.py documents the same trap). So the wrapper is
    neutralised and stdout replaced with a plain buffer we can read.
    """

    @property
    def buffer(self):
        return self


def _capture(monkeypatch):
    out = _Out()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(gen.io, "TextIOWrapper", lambda buf, **kw: buf)
    return out


def test_after_sunset_main_neither_queries_nor_writes(monkeypatch):
    """The whole point of the gate: no SPARQL, and above all no open(..., 'w')
    on bunrei.txt, which would wipe undelivered statements."""
    out = _capture(monkeypatch)
    monkeypatch.setattr(gen, "sunset_reached", lambda today=None: True)

    def _boom(*a, **k):
        raise AssertionError("all_shrines() must not run after the sunset date")

    monkeypatch.setattr(gen, "all_shrines", _boom)

    opened = []
    real_open = open

    def _tracking_open(path, mode="r", *a, **k):
        if "w" in mode:
            opened.append(path)
        return real_open(path, mode, *a, **k)

    monkeypatch.setattr("builtins.open", _tracking_open)
    monkeypatch.setattr(sys, "argv", ["generate_bunrei_quickstatements.py"])
    gen.main()

    assert opened == [], f"post-sunset run opened for writing: {opened}"
    assert "time-boxed" in out.getvalue()


def test_before_sunset_the_gate_does_not_block(monkeypatch):
    """Guard against the gate being wired backwards — it must let a normal run
    through, and the failure mode of getting this wrong is a silent stop."""
    _capture(monkeypatch)
    monkeypatch.setattr(gen, "sunset_reached", lambda today=None: False)
    called = {}

    def _fake_all_shrines():
        called["yes"] = True
        raise RuntimeError("stop here — we only need to prove the gate passed")

    monkeypatch.setattr(gen, "all_shrines", _fake_all_shrines)
    monkeypatch.setattr(sys, "argv", ["generate_bunrei_quickstatements.py"])
    with pytest.raises(RuntimeError):
        gen.main()
    assert called.get("yes")
