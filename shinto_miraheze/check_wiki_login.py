#!/usr/bin/env python3
"""Is shinto.miraheze.org reachable for editing, or is the anti-DDoS challenge up?

Emma 2026-07-11: before the work-loop attempts any WIKI item it should check the
login first — when Miraheze serves its "checking your connection" 403 challenge,
mwclient can't even log in, so every wiki edit/sync fails. This is the cheap
pre-check: hit api.php and see whether it answers or 403s.

Exit 0 = reachable (wiki items may proceed). Exit 1 = blocked (skip wiki items this
pass; they are DEFERRED, not failures). Read-only Wikidata is unaffected either way.

    python check_wiki_login.py        # prints OK / BLOCKED, sets exit code
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import io
import sys
import urllib.error
import urllib.request

API = "https://shinto.miraheze.org/w/api.php?action=query&meta=siteinfo&format=json"
UA = USER_AGENT


def wiki_reachable():
    """(ok: bool, detail: str). ok=False on the 403 anti-DDoS challenge."""
    req = urllib.request.Request(API, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            # a JSON siteinfo body means the API answered normally
            if r.status == 200 and b"query" in r.read(4096):
                return True, "api.php answered (siteinfo)"
            return False, f"unexpected status {r.status}"
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False, "403 anti-DDoS challenge (checking-your-connection) — wiki editing blocked"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"unreachable: {e}"


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ok, detail = wiki_reachable()
    print(("OK — " if ok else "BLOCKED — ") + detail)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
