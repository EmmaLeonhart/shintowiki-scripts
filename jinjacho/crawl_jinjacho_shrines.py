"""
Crawl prefectural 神社庁 shrine-detail pages -> jinjacho/crawled_shrines.csv.

WHY THIS EXISTS
---------------
`generate_jinjacho_p973.py` emits P973 (described at URL) for every row of
`jinjacho/shrines_and_websites.csv` — all 88 of them. That CSV is a hand-built
SAMPLE, not a backlog, so re-running the generator adds nothing. Coverage grows
only by resolving MORE shrine -> jinjacho-URL pairs, which is what this does.

`jinjacho/verification_results.csv` already verified which prefectural sites serve
real per-shrine content (verdict OK_SHRINE_CONTENT). Of those, the ones whose detail
URL is a plain incrementing integer are enumerable without a search form; this script
walks exactly those. Sites keyed by UUID (Aichi) or by a name-slug path (Mie, Osaka,
Kagoshima) are NOT enumerable and are deliberately absent — they need an index
harvest, not an id sweep.

Output columns: prefecture, shrine_name, kana, address, url. Matching names to
Wikidata QIDs is a SEPARATE script (`match_jinjacho_shrines.py`), because a crawl and
an entity-resolution pass fail in different ways and should be re-runnable apart.

POLITENESS
----------
These are small volunteer-run prefectural association sites. THROTTLE defaults to
1.5s between requests and is never removed; a family stops after MISS_TOLERANCE
consecutive misses so a wrong range cannot turn into a thousand pointless requests.
Checked 2026-07-28: yamagata serves `User-agent: * / Disallow:` (crawling allowed)
and the others serve no robots.txt at all. Re-check before widening.

The crawl is RESUMABLE: `crawl_state.json` stores the next id per family, so a run
capped with --max-pages picks up where the last one stopped.

Usage
-----
    python crawl_jinjacho_shrines.py --list
    python crawl_jinjacho_shrines.py --family gifu --max-pages 200
    python crawl_jinjacho_shrines.py --all --max-pages 500
"""

import os
import re
import csv
import sys
import io
import json
import time
import html
import argparse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "crawled_shrines.csv")
STATE = os.path.join(HERE, "crawl_state.json")

THROTTLE = 1.5
MISS_TOLERANCE = 60          # consecutive dead ids before a family gives up
TIMEOUT = 30
UA = {"User-Agent": "ShintoWikiJinjacho/1.0 "
                    "(https://github.com/EmmaLeonhart/shintowiki-scripts; "
                    "immanuelleleonhart@gmail.com)"}

FIELDS = ["prefecture", "shrine_name", "kana", "address", "url"]


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _text(raw):
    """HTML -> collapsed visible text."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</(p|div|tr|td|li|h[1-6])>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = t.replace(" ", " ")
    t = re.sub(r"[ \t　]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


# ─────────────────────── per-family parsers ───────────────────────
# Each returns {"shrine_name", "kana", "address"} or None when the page is not a
# real shrine record (dead id, "not found" placeholder, empty stub).

_POSTAL = r"\d{3}-?\d{4}"


def parse_gifu(raw):
    """'天神神社詳細 / 天神神社 (てんじんじんじゃ) ... 住所 〒501-6112 岐阜県...'"""
    t = _text(raw)
    m = re.search(r"(\S+?)詳細\s*\n?\s*(\S+?)\s*[（(]([ぁ-ゖー\s]+)[)）]", t)
    if not m:
        m2 = re.search(r"^(\S+?)詳細", t)
        if not m2:
            return None
        name, kana = m2.group(1), ""
    else:
        name, kana = m.group(2), m.group(3).strip()
    addr = ""
    a = re.search(r"住所\s*[〒]?\s*(" + _POSTAL + r")?\s*([^\n]{4,60})", t)
    if a:
        addr = (a.group(2) or "").strip()
    if not name or "詳細" in name:
        return None
    return {"shrine_name": name, "kana": kana, "address": addr}


def parse_shiga(raw):
    """'... 鎮座地 滋賀県甲賀市信楽町宮町7 ... 飯道神社 （イヒミチ） 御祭神 ...'"""
    t = _text(raw)
    m = re.search(r"神社紹介\s*\n?\s*(\S+?)\s*[（(]([ァ-ヶー\s]+)[)）]", t)
    if not m:
        m = re.search(r"([^\s>]+(?:神社|神宮|大社|社|宮))\s*[（(]([ァ-ヶー\s]+)[)）]", t)
    if not m:
        return None
    addr = ""
    a = re.search(r"鎮座地\s*([^\n]{4,60})", t)
    if a:
        addr = a.group(1).strip()
    return {"shrine_name": m.group(1), "kana": m.group(2).strip(), "address": addr}


def parse_saitama(raw):
    """Name is the <title>: '埼玉県護國神社 ｜ 埼玉県の神社'."""
    m = re.search(r"<title>(.*?)</title>", raw, re.S)
    if not m:
        return None
    name = html.unescape(m.group(1)).split("｜")[0].split("|")[0].strip()
    if not name or "埼玉県の神社" in name or "見つかり" in name or "404" in name:
        return None
    t = _text(raw)
    addr = ""
    a = re.search(r"(?:所在地|鎮座地|住所)\s*[〒]?\s*(?:" + _POSTAL + r")?\s*([^\n]{4,60})", t)
    if a:
        addr = a.group(1).strip()
    return {"shrine_name": name, "kana": "", "address": addr}


def parse_jinjanet(raw):
    """jinja-net family: '神社名/通称 博西神社 （ふりがな） はかにしじんじゃ ... 鎮座地 ...'"""
    t = _text(raw)
    m = re.search(r"神社名/通称\s*(\S+?)\s", t)
    if not m:
        return None
    name = m.group(1)
    kana = ""
    k = re.search(r"[（(]ふりがな[)）]\s*([ぁ-ゖー]+)", t)
    if k:
        kana = k.group(1)
    addr = ""
    a = re.search(r"鎮座地\s*([^\n]{4,60})", t)
    if a:
        addr = a.group(1).strip()
    if name in ("0", "") or len(name) < 2:
        return None
    return {"shrine_name": name, "kana": kana, "address": addr}


# ─────────────────────── families ───────────────────────
# Only integer-enumerable, OK_SHRINE_CONTENT-verified sites. `start`/`stop` bound the
# sweep; ranges were widened past the known-good sample ids from verification_results.

FAMILIES = {
    # INTERMITTENTLY SLOW HOST — and the earlier note here overstated it. On
    # 2026-07-28 gifu answered in ~22s per request for a stretch (HTTP 200 with correct
    # content, so a load spike rather than a block), which this comment recorded as a
    # fixed ~23.5s/id and a ~17-hour sweep. It is not fixed: later the same evening the
    # cursor moved 376 -> 1091 in the span that rate predicted ~50, i.e. back to
    # roughly the ~1s the other families answer in. Treat the slow spell as weather,
    # not climate. Still worth running in its OWN process: when the spike returns, a
    # shared serial run would starve shiga and saitama behind it.
    "gifu": {
        "prefecture": "Gifu",
        "url": "https://www.gifu-jinjacho.jp/syosai.php?shrno={n}",
        "start": 1, "stop": 2600, "parser": parse_gifu,
    },
    "shiga": {
        "prefecture": "Shiga",
        "url": ("https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/"
                "ycDB_02jinja-pc-detail.html?mode:view=1&view:oid={n}"),
        "start": 1, "stop": 1600, "parser": parse_shiga,
    },
    "saitama": {
        "prefecture": "Saitama",
        # Probed 2026-07-28: 8801 is 404, 9000 is a real record — the id space
        # starts at ~9000, so a lower start just burns the miss tolerance.
        "url": "https://www.saitama-jinjacho.or.jp/shrine/{n}/",
        "start": 9000, "stop": 10600, "parser": parse_saitama,
    },
}


def load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}


def save_cursor(key, n):
    """Persist ONE family's cursor, merging into whatever is on disk.

    Families run as SEPARATE processes (gifu is a ~22s/request host and would
    otherwise starve the fast ones), and they share this file. Writing the whole
    in-memory dict would roll back a sibling's cursor to whatever this process read
    at startup — so re-read, touch only our key, write back.
    """
    state = load_state()
    state[key] = n
    tmp = STATE + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, STATE)


def load_seen():
    """URLs already in the CSV, so a resumed run never duplicates a row."""
    seen = set()
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                seen.add(row["url"])
    return seen


def append_rows(rows):
    """Append in ONE write call.

    Two crawler processes share this file, and a DictWriter emitting row-by-row can
    interleave with the other process mid-row. Serialising to a string first and
    issuing a single append keeps every row intact.
    """
    header = not os.path.exists(OUT_CSV) or os.path.getsize(OUT_CSV) == 0
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    if header:
        w.writeheader()
    for r in rows:
        w.writerow(r)
    with open(OUT_CSV, "a", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())


def crawl_family(key, max_pages, throttle):
    fam = FAMILIES[key]
    seen = load_seen()
    n = load_state().get(key, fam["start"])
    got, misses, fetched, rows = 0, 0, 0, []

    print(f"[{key}] starting at id {n} (stop {fam['stop']}, max {max_pages} pages)",
          flush=True)
    while n <= fam["stop"] and fetched < max_pages and misses < MISS_TOLERANCE:
        url = fam["url"].format(n=n)
        n += 1
        if url in seen:
            continue
        fetched += 1
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
        except Exception as e:
            print(f"  {url} ERR {type(e).__name__}", flush=True)
            misses += 1
            time.sleep(throttle)
            continue
        if r.status_code != 200:
            misses += 1
            time.sleep(throttle)
            continue
        r.encoding = r.apparent_encoding or r.encoding
        rec = fam["parser"](r.text)
        if not rec:
            misses += 1
        else:
            misses = 0
            got += 1
            rec.update({"prefecture": fam["prefecture"], "url": url})
            rows.append(rec)
            if got <= 5 or got % 50 == 0:
                print(f"  {got:5d} {rec['shrine_name']}  {rec['address'][:28]}",
                      flush=True)
        # Flush every 25 records rather than once at the end: a 2,600-page sweep is
        # ~65 minutes, and a crash at minute 60 must not throw away the crawl AND
        # leave the cursor unmoved (which would re-fetch every one of those pages).
        if len(rows) >= 25:
            append_rows(rows)
            rows = []
            save_cursor(key, n)
        time.sleep(throttle)

    if rows:
        append_rows(rows)
    save_cursor(key, n)
    why = ("range end" if n > fam["stop"] else
           "miss tolerance" if misses >= MISS_TOLERANCE else "page cap")
    print(f"[{key}] +{got} shrines from {fetched} fetches; stopped at id {n} ({why})",
          flush=True)
    return got


def main():
    _utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", action="append", choices=sorted(FAMILIES),
                    help="crawl this family (repeatable)")
    ap.add_argument("--all", action="store_true", help="crawl every family")
    ap.add_argument("--max-pages", type=int, default=200,
                    help="per-family fetch cap for this run (default 200)")
    ap.add_argument("--throttle", type=float, default=THROTTLE,
                    help="seconds between requests (default 1.5; do not lower)")
    ap.add_argument("--list", action="store_true", help="show families and exit")
    args = ap.parse_args()

    if args.list:
        state = load_state()
        for k, f in sorted(FAMILIES.items()):
            print(f"{k:10} {f['prefecture']:10} ids {f['start']}-{f['stop']} "
                  f"next={state.get(k, f['start'])}")
        return

    keys = sorted(FAMILIES) if args.all else (args.family or [])
    if not keys:
        print("nothing to do — pass --family <name> or --all (see --list)")
        return

    total = 0
    for k in keys:
        total += crawl_family(k, args.max_pages, max(args.throttle, 0.5))
    print(f"\ntotal +{total} shrines -> {OUT_CSV}")


if __name__ == "__main__":
    main()
