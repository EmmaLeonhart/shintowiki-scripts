#!/usr/bin/env python3
"""
report_blank_wikidata_links.py
==============================
Counts the mainspace pages whose ``{{wikidata link}}`` is BLANK — the template
is there but carries no QID — and splits them by whether anything on the page
could ever resolve it.

Why this exists
---------------
The ADD half of the pipeline is built: the ``wikidata_link`` orchestrator op
appends a blank ``{{wikidata link}}`` to every ns-0/14 page that lacks one. The
FILL half has a hole. ``wikidata_lookup`` resolves the QID out of the template's
own ``(lang, target)`` pairs, so a page with a blank template and **no pairs**
never resolves, on any number of runs. ``Shizensha`` is the case Emma named:
``Q139921367`` carries ``en: Shizensha`` and a jawiki sitelink to 自然社, and the
page has sat with an empty template regardless.

Before building a resolver for that, we need the number. This script is the
measurement, and nothing else.

How it counts, without reading 11,069 page bodies
-------------------------------------------------
``Template:Wikidata link`` emits ``[[da:{{{1}}}]]`` — a Danish interlanguage
link whose target is the QID — and it emits it **only inside** ``{{#if:{{{1|}}}
|…}}``. So the rendered ``da:`` langlink is present exactly when the template
has a QID:

* transcludes the template + has a ``da:`` langlink  -> FILLED
* transcludes the template + no ``da:`` langlink     -> BLANK
* does not transclude it at all                      -> MISSING (the op has
  not reached it yet, or it is out of scope like ``Main Page``)

That is one ``allpages`` sweep asking for both ``templates`` and ``langlinks``,
about 23 requests for the whole mainspace, instead of downloading every body.

Read-only. This script makes NO edit, to this wiki or to Wikidata, so the
shinto.miraheze editing lockout does not gate it.
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
import os
import sys
import time
from collections import defaultdict

import requests

from shinto_miraheze.user_agent import USER_AGENT

API = "https://shinto.miraheze.org/w/api.php"
TEMPLATE = "Template:Wikidata link"

# Read-only API calls, so the 2.5s edit throttle does not apply — but the
# redirect-chain followers in this repo pace reads at 0.3s and so does this.
READ_THROTTLE = 0.3

# The template's QID-only output. See the module docstring: presence of this
# langlink IS the "template has a QID" test.
QID_LANG = "da"

REPORT = os.path.join(_uar, "docs", "blank_wikidata_links.md")


def classify(has_template, has_qid_langlink):
    """The whole test, in one place so it can be pinned by a unit test.

    ``has_qid_langlink`` is the ``da:`` interlanguage link the template emits
    from inside ``{{#if:{{{1|}}}|…}}``. A page cannot carry it without the
    template having a QID, which is what makes this cheaper than reading bodies.
    """
    if not has_template:
        return "missing"
    return "filled" if has_qid_langlink else "blank"


def sweep(namespace, limit=None, verbose=True):
    """{title: ("filled" | "blank" | "missing")} for every non-redirect page.

    One `allpages` generator asking for both props. Continuation merges into the
    accumulator rather than replacing it: a page can come back on one response
    with its templates and on a later one with its langlinks.
    """
    has_template = set()
    has_qid = set()
    seen = set()

    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "allpages",
        "gapnamespace": str(namespace),
        "gaplimit": "500",
        "gapfilterredir": "nonredirects",
        "prop": "templates|langlinks",
        "tlnamespace": "10",
        "tltemplates": TEMPLATE,
        "tllimit": "max",
        "lllang": QID_LANG,
        "lllimit": "max",
    }
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    requests_made = 0

    while True:
        r = session.get(API, params=params, timeout=120)
        r.raise_for_status()
        data = r.json()
        requests_made += 1
        for page in data.get("query", {}).get("pages", []):
            title = page["title"]
            seen.add(title)
            if page.get("templates"):
                has_template.add(title)
            if page.get("langlinks"):
                has_qid.add(title)
        if verbose:
            print(f"  request {requests_made}: {len(seen)} pages seen", flush=True)
        if limit and len(seen) >= limit:
            break
        if "continue" not in data:
            break
        params.update(data["continue"])
        time.sleep(READ_THROTTLE)

    out = {title: classify(title in has_template, title in has_qid)
           for title in sorted(seen)}
    return out, requests_made


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--namespace", type=int, default=0,
                    help="namespace to sweep (default 0; the op also covers 14)")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after roughly this many pages — for a quick look")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="also write the per-page verdicts here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    # Rebound HERE, not at module level: importing this module under pytest with
    # the rebind at the top closes the capture fixture's file and no test runs.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print(f"Sweeping ns={args.namespace} for {TEMPLATE} + {QID_LANG}: langlinks…")
    verdicts, n_requests = sweep(args.namespace, args.limit, verbose=not args.quiet)

    counts = defaultdict(list)
    for title, verdict in verdicts.items():
        counts[verdict].append(title)

    total = len(verdicts)
    print(f"\n{total} non-redirect pages in ns={args.namespace}, {n_requests} API requests")
    for verdict in ("filled", "blank", "missing"):
        titles = counts[verdict]
        pct = (100.0 * len(titles) / total) if total else 0.0
        print(f"  {len(titles):>6}  {pct:5.1f}%  {verdict}")

    lines = [
        "# Blank `{{wikidata link}}` — the measurement",
        "",
        "Generated by `shinto_miraheze/report_blank_wikidata_links.py`. Read-only; no edit was made.",
        "",
        "A page transcluding `Template:Wikidata link` renders a `da:` langlink **only** when the",
        "template has a QID, so the langlink is the filled/blank test — see the script's docstring.",
        "",
        f"Namespace {args.namespace}, {total} non-redirect pages, {n_requests} API requests.",
        "",
        "| verdict | pages | meaning |",
        "|---|---:|---|",
        f"| filled | {len(counts['filled'])} | `{{{{wikidata link\\|Q…}}}}` — done |",
        f"| blank | {len(counts['blank'])} | template present, no QID — the gap |",
        f"| missing | {len(counts['missing'])} | no template at all — the `wikidata_link` op has not reached it |",
        "",
        "## Blank",
        "",
    ]
    lines += [f"* [[{t}]]" for t in counts["blank"]] or ["* *(none)*"]
    lines += ["", "## Missing the template entirely", ""]
    lines += [f"* [[{t}]]" for t in counts["missing"]] or ["* *(none)*"]
    lines.append("")

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with io.open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    print(f"\nwrote {REPORT}")

    if args.json_out:
        with io.open(args.json_out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(verdicts, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
