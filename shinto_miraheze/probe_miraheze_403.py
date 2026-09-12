#!/usr/bin/env python3
"""
probe_miraheze_403.py
=====================
Ask shinto.miraheze.org the same question the weekly edit-test asks, record what
comes back in full, and change NOTHING.

## Why this exists

Emma, 2026-09-12: *"the miraheze wiki is supposed to just get edited like normal
so idk what is going on with it lol."* Neither do we, and that is the problem —
the evidence has been thrown away every time.

`weekly_wiki_edit_test.py` has failed 5 of its 8 runs with `HTTPError: 403` on
mwclient's pre-login site-init call, and each failure locks editing for 8 days.
What it records is the exception's `str()`. What it does not record is the
response: no status line beyond 403, no `cf-ray`, no `server`, no `retry-after`,
no body. Those are exactly the fields that separate

  * a Cloudflare managed challenge (an HTML body, a `cf-ray`, `server: cloudflare`)
  * a UA-policy rejection by the farm (a short text body naming the policy)
  * ordinary rate limiting (`retry-after`)

and without them a 403 is just a number. The workflow made it worse by piping the
script through `|| echo`, so its stdout never reached the log either.

## The one fact this is built to establish

From this machine, right now, BOTH a plain `requests` site-init and a full
`mwclient.Site()` against shinto.miraheze.org return 200 (MediaWiki 1.45.4) with
the canonical `EmmaBot/3.1` User-Agent. The failures happen on GitHub Actions.
The difference not yet tested is **where the request comes from** — Azure
`centralus` runner IPs against a home connection.

So run this on a runner (`workflow_dispatch`) and compare its output with a local
run. Same code, two origins.

## Safety

Read-only and unauthenticated: `action=query&meta=siteinfo|userinfo`, exactly the
call that 403s, plus one page read. It never logs in, never edits, never touches
`wiki_editing_lockout.state`, and does not consult the lockout — a probe that the
lockout silenced could not diagnose the lockout. Four requests, paced.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import io
import json
import sys
import time

import requests

from shinto_miraheze.user_agent import USER_AGENT

API = "https://shinto.miraheze.org/w/api.php"
THROTTLE = 1.0

# Verbatim the parameters mwclient sends when constructing a Site — this is the
# request named in every one of the recorded 403s.
SITEINIT_PARAMS = {
    "action": "query",
    "meta": "siteinfo|userinfo",
    "siprop": "general|namespaces",
    "uiprop": "groups|rights|blockinfo|hasmsg",
    "continue": "",
    "format": "json",
}

# Response headers worth keeping. `cf-ray` and `server` say whether Cloudflare
# answered instead of MediaWiki; `retry-after` says it was rate limiting.
KEEP_HEADERS = ("server", "cf-ray", "cf-cache-status", "retry-after",
                "content-type", "x-served-by", "via")


def describe(resp):
    out = {
        "status": resp.status_code,
        "headers": {k: v for k, v in resp.headers.items() if k.lower() in KEEP_HEADERS},
        "bytes": len(resp.content),
    }
    body = resp.text or ""
    if resp.status_code != 200:
        # The body is the whole point on a failure: a challenge page and a policy
        # rejection look nothing alike.
        out["body_head"] = body[:600]
    else:
        try:
            out["ok_generator"] = resp.json()["query"]["general"]["generator"]
        except Exception:
            out["body_head"] = body[:200]
    return out


def probe(session, label, params):
    try:
        r = session.get(API, params=params, timeout=60)
        return {"probe": label, **describe(r)}
    except Exception as e:
        return {"probe": label, "exception": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output only")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    results = []
    results.append(probe(session, "siteinfo (the call that 403s)", SITEINIT_PARAMS))
    time.sleep(THROTTLE)
    results.append(probe(session, "page read", {
        "action": "query", "prop": "revisions", "titles": "Main Page",
        "rvprop": "timestamp", "format": "json"}))
    time.sleep(THROTTLE)

    # mwclient sends its own suffix on the UA; if the farm's allowlist matches on
    # the exact string, that difference matters and this isolates it.
    mw = requests.Session()
    mw.headers["User-Agent"] = (
        USER_AGENT + " mwclient/0.11.0 (https://github.com/mwclient/mwclient)")
    results.append(probe(mw, "siteinfo with mwclient's UA suffix", SITEINIT_PARAMS))
    time.sleep(THROTTLE)

    # A deliberately generic UA. Miraheze's policy rejects these, so a 403 HERE
    # and a 200 above means the allowlist is working and our UA is fine — it is
    # the control, not a request to be served.
    generic = requests.Session()
    generic.headers["User-Agent"] = "python-requests/2.x"
    results.append(probe(generic, "CONTROL: generic UA, expected to be refused",
                         SITEINIT_PARAMS))

    payload = {"user_agent": USER_AGENT, "results": results}
    if args.json:
        print(json.dumps(payload, indent=1, ensure_ascii=False))
        return

    print(f"User-Agent: {USER_AGENT}\n")
    for r in results:
        print(f"--- {r['probe']}")
        for k, v in r.items():
            if k == "probe":
                continue
            print(f"    {k}: {v}")
        print()

    live = [r for r in results if not r["probe"].startswith("CONTROL")]
    bad = [r for r in live if r.get("status") != 200]
    print("VERDICT:", "all real probes 200 — the wiki is answering us here"
          if not bad else f"{len(bad)} of {len(live)} real probes did NOT return 200")


if __name__ == "__main__":
    main()
