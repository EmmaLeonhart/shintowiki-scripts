"""Unit test for fetch_sparql's transient-error handling in
generate_shrines_missing_en_label.

Guards the fix for CI run 27087424162 (2026-06-07), where a transient
``502 Bad Gateway`` from query.wikidata.org hit ``raise_for_status()`` uncaught
and red-marked the daily job. fetch_sparql must now retry transient 5xx and
connection errors (returning None after exhausting retries, so the caller leaves
the existing list untouched), while still bailing immediately on 429.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_shrines_missing_en_label as g  # noqa: E402


class _FakeResp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {"results": {"bindings": [{"x": 1}]}}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.exceptions.HTTPError(f"{self.status_code}")

    def json(self):
        return self._payload


def test_200_returns_bindings(monkeypatch):
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: _FakeResp(200))
    assert g.fetch_sparql("q") == [{"x": 1}]


def test_transient_502_then_success(monkeypatch):
    monkeypatch.setattr(g.time, "sleep", lambda *_: None)
    seq = [_FakeResp(502), _FakeResp(200)]
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: seq.pop(0))
    assert g.fetch_sparql("q", retries=3) == [{"x": 1}]


def test_persistent_502_returns_none(monkeypatch):
    monkeypatch.setattr(g.time, "sleep", lambda *_: None)
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: _FakeResp(502))
    assert g.fetch_sparql("q", retries=3) is None


def test_429_bails_immediately(monkeypatch):
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _FakeResp(429)

    monkeypatch.setattr(g.requests, "get", fake_get)
    with pytest.raises(g.RateLimitError):
        g.fetch_sparql("q", retries=3)
    assert calls["n"] == 1  # no retries on 429


def test_connection_error_then_success(monkeypatch):
    monkeypatch.setattr(g.time, "sleep", lambda *_: None)
    import requests
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.exceptions.ConnectionError("boom")
        return _FakeResp(200)

    monkeypatch.setattr(g.requests, "get", fake_get)
    assert g.fetch_sparql("q", retries=3) == [{"x": 1}]


def test_non_transient_4xx_raises(monkeypatch):
    # A 400 (bad query) is a real error, not transient — it must surface.
    monkeypatch.setattr(g.requests, "get", lambda *a, **k: _FakeResp(400))
    import requests
    with pytest.raises(requests.exceptions.HTTPError):
        g.fetch_sparql("q", retries=3)
