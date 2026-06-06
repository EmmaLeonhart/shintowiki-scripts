"""Unit test for the shared transient-login retry helper (wiki_login).

Reproduces the cleanup-loop run 27036877968 failure mode: a single spurious
mwclient LoginError on a valid credential. The retry should absorb a transient
failure and re-raise a persistent one.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wiki_login as d  # noqa: E402


class _FakeSite:
    """site.login raises for the first `fail_n` calls, then succeeds."""

    def __init__(self, fail_n, exc=RuntimeError("auth flake")):
        self.fail_n = fail_n
        self.calls = 0
        self.exc = exc

    def login(self, username, password):
        self.calls += 1
        if self.calls <= self.fail_n:
            raise self.exc


def test_login_succeeds_after_transient_failures(monkeypatch):
    monkeypatch.setattr(d.time, "sleep", lambda *_: None)  # no real backoff
    site = _FakeSite(fail_n=2)
    d.login_with_retry(site, "EmmaBot", "pw", attempts=3, base_delay=0)
    assert site.calls == 3  # failed twice, succeeded on the third


def test_login_succeeds_first_try(monkeypatch):
    monkeypatch.setattr(d.time, "sleep", lambda *_: None)
    site = _FakeSite(fail_n=0)
    d.login_with_retry(site, "EmmaBot", "pw", attempts=3, base_delay=0)
    assert site.calls == 1


def test_login_reraises_after_exhausting_attempts(monkeypatch):
    monkeypatch.setattr(d.time, "sleep", lambda *_: None)
    boom = RuntimeError("bad creds")
    site = _FakeSite(fail_n=99, exc=boom)
    with pytest.raises(RuntimeError) as ei:
        d.login_with_retry(site, "EmmaBot", "pw", attempts=3, base_delay=0)
    assert ei.value is boom
    assert site.calls == 3  # tried exactly `attempts` times
