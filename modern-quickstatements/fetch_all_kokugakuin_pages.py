"""Download every Kokugakuin entry page Wikidata references, once, in id order.

Emma, 2026-08-25: *"you can just sequentially download the web pages the id links to using the id
keys en masse."* Correct, and it is the right shape rather than a convenience.

**What was wrong with fetching on demand.** The reader was pulling a page only when some sweep
happened to need it, which meant the corpus grew in whatever order jobs ran, every new job paid
network cost for pages other jobs had not happened to touch, and the site got hit repeatedly across
sessions. The ids are a **known key set** — 2,846 distinct `P13677` values live on Wikidata — so
there is no reason to discover them lazily. Fetch the set once; every reading job afterwards is a
local parse.

**This is what makes the reading queue tractable.** The 228-section job, the ~66 two-id items, the
13 missing `P1352` rankings and anything later all read the same corpus. With it complete, those
stop being network-bound jobs and become offline ones that can be re-run freely, re-parsed after any
change to the matcher, and audited against the exact bytes.

**Politeness.** One request per id, paced at `PACE` seconds, resumable, and it never re-fetches a
page already on disk. This is a small museum site — the whole point of saving the corpus is that it
gets asked for each page once, ever, rather than once per job that needs it.

**Failures are recorded, not fatal.** A page that errors is logged to `kokugakuin_fetch_errors.json`
and the sweep continues; a re-run retries only those.

Usage:
    python modern-quickstatements/fetch_all_kokugakuin_pages.py
    python modern-quickstatements/fetch_all_kokugakuin_pages.py --limit 200
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "kokugakuin_pages")
IDS = os.path.join(HERE, "kokugakuin_all_ids.json")
ERRORS = os.path.join(HERE, "kokugakuin_fetch_errors.json")
DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id="

# Deliberately gentler than the repo's 0.3s READ_INTERVAL. That figure is for Wikidata,
# which is built for it; this is a museum's catalogue and the sweep is thousands of pages.
PACE = 0.6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--retry-errors", action="store_true",
                    help="re-attempt only the ids in kokugakuin_fetch_errors.json")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    ids = json.load(io.open(IDS, encoding="utf-8"))
    if args.retry_errors and os.path.exists(ERRORS):
        ids = [e["id"] for e in json.load(io.open(ERRORS, encoding="utf-8"))]

    have = {f[:-5] for f in os.listdir(CACHE) if f.endswith(".html")}
    todo = [i for i in ids if i not in have]
    if args.limit:
        todo = todo[:args.limit]

    print("ids referenced by Wikidata: %d" % len(ids))
    print("already on disk:            %d" % len(have & set(ids)))
    print("to fetch this run:          %d  (~%.0f min at %.1fs)"
          % (len(todo), len(todo) * PACE / 60.0, PACE))

    errors, done = [], 0
    for n, kid in enumerate(todo, 1):
        try:
            req = urllib.request.Request(DET + str(kid),
                                         headers={"User-Agent": WIKIDATA_USER_AGENT})
            time.sleep(PACE)
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
            io.open(os.path.join(CACHE, "%s.html" % kid), "w",
                    encoding="utf-8", newline="\n").write(body)
            done += 1
        except Exception as exc:
            errors.append({"id": kid, "error": "%s: %s" % (type(exc).__name__, exc)})
        if n % 100 == 0:
            print("  %d/%d fetched, %d error(s)" % (n, len(todo), len(errors)), flush=True)

    io.open(ERRORS, "w", encoding="utf-8", newline="\n").write(
        json.dumps(errors, ensure_ascii=False, indent=1))
    print("\nfetched %d, %d error(s) -> %s" % (done, len(errors), ERRORS))
    print("corpus now: %d pages"
          % len([f for f in os.listdir(CACHE) if f.endswith(".html")]))


if __name__ == "__main__":
    main()
