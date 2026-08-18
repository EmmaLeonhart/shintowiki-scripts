"""
Crawl prefectural 神社庁 shrine-detail pages -> jinjacho/crawled_shrines.csv.

WHY THIS EXISTS
---------------
`generate_jinjacho_p973.py` emits P973 (described at URL) for every row of
`jinjacho/shrines_and_websites.csv` — all 88 of them. That CSV is a hand-built
SAMPLE, not a backlog, so re-running the generator adds nothing. Coverage grows
only by resolving MORE shrine -> jinjacho-URL pairs, which is what this does.

`jinjacho/verification_results.csv` already verified which prefectural sites serve
real per-shrine content (verdict OK_SHRINE_CONTENT). Two shapes of site, two paths:

* FAMILIES — the detail URL is a plain incrementing integer, so the id space is swept
  directly (gifu, shiga, saitama), bounded by --max-pages and MISS_TOLERANCE.
* INDEX_FAMILIES — keyed by UUID or name slug, so there is no id to sweep. These were
  once written off as "not enumerable"; every one of them turned out to publish an
  index, which is what is harvested instead (checked 2026-08-03):
    aichi     — the search page's JSON API returns the whole register in ONE POST.
    mie       — WordPress; its `shrine` post type is a single sitemap file.
    kagoshima — WordPress; shrines are ordinary posts across 92 monthly sitemaps,
                filtered by the /shrine-search/ path.
    osaka     — no robots.txt and no sitemap, but a two-level HTML index: one page
                lists ~50 municipality pages, each listing its shrines.
  Aichi aside, the index gives URLs but no fields, so the detail pages are still
  fetched — throttled, --max-pages-capped, and resumable by URL against the CSV.

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
    python crawl_jinjacho_shrines.py --index mie --max-pages 300
    python crawl_jinjacho_shrines.py --index osaka --refresh-index --max-pages 300
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
from shinto_miraheze.ua_contact import contact

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "crawled_shrines.csv")
STATE = os.path.join(HERE, "crawl_state.json")

THROTTLE = 1.5
MISS_TOLERANCE = 60          # consecutive dead ids before a family gives up
TIMEOUT = 30
UA = {"User-Agent": "ShintoWikiJinjacho/1.0 "
                    "(https://github.com/EmmaLeonhart/shintowiki-scripts; "
                    f"{contact('wikidata')})"}

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


# ─────────────────────── index-harvest families ───────────────────────
# Not every site can be swept by id. Aichi keys its detail pages by UUID, which is
# why it sat in the "needs an index harvest" pile — but its search page is backed by
# a JSON API (found in assets/js/search.js: POST /index.php/search/shrine, and the
# page itself sends limit:-1), and one query with a prefecture-wide address term
# returns the WHOLE register in a single response: 3,179 shrines, structured, with
# name/kana/city/addr and the UUID that builds the detail URL.
#
# That is strictly better than scraping — one request instead of thousands, and no
# HTML parsing to get wrong — so it is the preferred path wherever a site offers it.
# The endpoint rejects an empty term ("検索キーワードが指定されていない"), hence the
# "愛知" address query rather than a blank one.
AICHI_API = "https://www.aichi-jinjacho.or.jp/index.php/search/shrine"
AICHI_DETAIL = "https://www.aichi-jinjacho.or.jp/search_detail.html?id=%s"


def harvest_aichi():
    """The whole Aichi register in one POST. Returns CSV-shaped rows."""
    hdr = dict(UA, **{"Content-Type": "application/json",
                      "Referer": "https://www.aichi-jinjacho.or.jp/search.html"})
    r = requests.post(AICHI_API, headers=hdr,
                      data=json.dumps({"addr": "愛知", "limit": -1}), timeout=180)
    r.raise_for_status()
    payload = r.json()
    rows = []
    for rec in payload.get("list", []):
        uuid = (rec.get("id") or "").strip()
        name = (rec.get("name") or "").strip()
        if not uuid or not name:
            continue
        addr = "".join((rec.get("city") or "", rec.get("addr") or "",
                        rec.get("house_num") or "")).strip()
        rows.append({"prefecture": "Aichi", "shrine_name": name,
                     "kana": (rec.get("kana") or "").strip(),
                     "address": addr, "url": AICHI_DETAIL % uuid})
    print(f"[aichi] API reports total_rows={payload.get('total_rows')}, "
          f"{len(rows)} usable rows", flush=True)
    return rows


# ─────────── index-backed families needing per-page fetches (Mie, Kagoshima, Osaka) ───────────
# These two were filed as "name-slug paths, not enumerable" and therefore parked. They
# are both WordPress, and both publish a sitemap that robots.txt points at and permits
# (only wp-admin is disallowed) — so the index does exist, it just isn't an integer
# sequence. Checked 2026-08-03.
#
# Unlike Aichi, the sitemap gives URLs but no fields, so each detail page still has to
# be fetched. That is a REAL crawl and is treated like one: same THROTTLE, and bounded
# by --max-pages per run. It is resumable for free — a URL already in crawled_shrines.csv
# is skipped — so repeated capped runs walk the list without a cursor.
#
# The URL list itself is cached in index_urls.json: rebuilding Kagoshima's costs 93
# requests (its shrines are plain `post`s spread over 92 monthly sitemaps), which is not
# worth re-spending on every resumed chunk. --refresh-index rebuilds it.
INDEX_CACHE = os.path.join(HERE, "index_urls.json")

MIE_SITEMAP = "https://kyoka.mie-jinjacho.or.jp/wp-sitemap.xml"
KAGO_SITEMAP = "https://www.kagojinjacho.or.jp/sitemap.xml"

_LOC_RE = re.compile(r"<loc>(.*?)</loc>", re.S)


def parse_mie(raw):
    """'三重県神社庁教化委員会 » 宇氣比神社（村松町）' + '– うけひじんじゃ –' + 鎮座地 block.

    The trailing （村松町） on the name is the SITE's own disambiguator for shrines
    sharing a name within the prefecture. It is stripped: the label lookup is against
    Wikidata labels, which do not carry it, and disambiguation is the municipality
    gate's job in match_jinjacho_shrines.py — not the name's.
    """
    m = re.search(r"<title>(.*?)</title>", raw, re.S)
    if not m:
        return None
    name = html.unescape(m.group(1)).split("»")[-1].strip()
    name = re.sub(r"[（(][^）)]*[）)]\s*$", "", name).strip()
    if not name or "三重県神社庁" in name or len(name) < 2:
        return None
    t = _text(raw)
    kana = ""
    k = re.search(r"–\s*([ぁ-ゖー]{2,})\s*–", t)
    if k:
        kana = k.group(1)
    addr = ""
    a = re.search(r"鎮座地\s*\n?\s*(?:〒?\s*" + _POSTAL + r")?\s*\n?\s*([^\n]{4,60})", t)
    if a:
        addr = a.group(1).strip()
    return {"shrine_name": name, "kana": kana, "address": addr}


def parse_kagoshima(raw):
    """Explicitly labelled fields: '神社名：照島神社 / 神社名カナ：テルシマジンジャ /
    鎮座地：〒896-0032 いちき串木野市西島平町410'.

    The 鎮座地 label is required rather than a generic address search: every page's
    footer carries the AGENCY's own address (鹿児島市照国町19-20), which a loose
    match would happily read as the shrine's and put every shrine in 鹿児島市.
    """
    t = _text(raw)
    m = re.search(r"神社名\s*[：:]\s*([^\n]{2,40})", t)
    if not m:
        return None
    name = m.group(1).strip()
    if not name or name.startswith("カナ"):
        return None
    kana = ""
    k = re.search(r"神社名カナ\s*[：:]\s*([ァ-ヶー]{2,})", t)
    if k:
        kana = k.group(1)
    addr = ""
    a = re.search(r"鎮座地\s*[：:]\s*(?:〒?\s*" + _POSTAL + r")?\s*([^\n]{4,60})", t)
    if a:
        addr = a.group(1).strip()
    return {"shrine_name": name, "kana": kana, "address": addr}


def _sitemap_locs(url):
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return _LOC_RE.findall(r.text)


def _load_index_cache():
    if os.path.exists(INDEX_CACHE):
        try:
            with open(INDEX_CACHE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}


def _save_index_cache(key, urls):
    cache = _load_index_cache()
    cache[key] = urls
    tmp = INDEX_CACHE + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, INDEX_CACHE)


def _collect_mie_urls(throttle):
    urls = []
    for sub in _sitemap_locs(MIE_SITEMAP):
        if "posts-shrine" not in sub:
            continue
        time.sleep(throttle)
        urls += [u for u in _sitemap_locs(sub) if "/shrine/" in u]
    return sorted(set(urls))


def _collect_kagoshima_urls(throttle):
    """Kagoshima's shrines are ordinary `post`s, so the shrine pages are mixed in
    with news items across 90-odd monthly sitemaps; /shrine-search/ is the filter."""
    urls = []
    for sub in _sitemap_locs(KAGO_SITEMAP):
        if "sitemap-pt-post" not in sub:
            continue
        time.sleep(throttle)
        urls += [u for u in _sitemap_locs(sub) if "/shrine-search/" in u]
    return sorted(set(urls))


# Osaka has no robots.txt and no sitemap, but it does publish a two-level HTML index:
# funai_jinja/index.html lists ~50 municipality pages (dai<N>shibu/<muni>/<muni>.html),
# and each of those lists its shrines as numeric-prefixed siblings (01020kusasajinja.html).
# Directory listings are 403, so the link graph is the only way in — which is fine, it is
# the site's own navigation.
OSAKA_INDEX = "https://www.osaka-jinjacho.jp/funai_jinja/index.html"
_OSAKA_MUNI_RE = re.compile(r'href="(dai\d+shibu/[^"/]+/[^"/]+\.html)"')
_OSAKA_SHRINE_RE = re.compile(r'href="(\d{4,6}[^"/]*\.html)"')


def parse_osaka(raw):
    """'コード：01020 / 久佐々神社（くささじんじゃ） / 鎮座地 〒563-0341 豊能郡能勢町宿野274-1'.

    Same footer trap as Kagoshima — every page ends with the agency's own address in
    大阪市中央区 — so the address is taken from the 鎮座地 label, never by a loose search.
    """
    t = _text(raw)
    # Anchored on コード： deliberately. A municipality LISTING page (hirakata.html)
    # also opens with a shrine name in kana parens, and a looser pattern reads it as
    # a record — one with no 鎮座地, which is exactly the shape that reaches the
    # matcher as an unaddressed row. Detail pages are the ones carrying the code.
    m = re.search(r"コード\s*[：:]\s*\d+\s*\n?\s*([^\n（(]{2,30})\s*[（(]([ぁ-ゖー]{2,})[）)]", t)
    if not m:
        return None
    addr = ""
    a = re.search(r"鎮座地\s*\n?\s*(?:〒?\s*" + _POSTAL + r")?\s*\n?\s*([^\n]{4,60})", t)
    if a:
        addr = a.group(1).strip()
    return {"shrine_name": m.group(1).strip(), "kana": m.group(2).strip(),
            "address": addr}


def _collect_osaka_urls(throttle):
    base = "https://www.osaka-jinjacho.jp/funai_jinja/"
    r = requests.get(OSAKA_INDEX, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    munis = sorted(set(_OSAKA_MUNI_RE.findall(r.text)))
    urls = []
    for rel in munis:
        time.sleep(throttle)
        try:
            p = requests.get(base + rel, headers=UA, timeout=TIMEOUT)
            p.encoding = p.apparent_encoding or p.encoding
        except Exception as e:
            print(f"  [osaka] {type(e).__name__} on {rel}", flush=True)
            continue
        if p.status_code != 200:
            continue
        prefix = base + rel.rsplit("/", 1)[0] + "/"
        urls += [prefix + s for s in _OSAKA_SHRINE_RE.findall(p.text)]
    print(f"[osaka] {len(munis)} municipality pages -> {len(set(urls))} shrine pages",
          flush=True)
    return sorted(set(urls))


CRAWLED_INDEX_FAMILIES = {
    "mie": {"prefecture": "Mie", "collect": _collect_mie_urls, "parser": parse_mie},
    "kagoshima": {"prefecture": "Kagoshima", "collect": _collect_kagoshima_urls,
                  "parser": parse_kagoshima},
    "osaka": {"prefecture": "Osaka", "collect": _collect_osaka_urls,
              "parser": parse_osaka},
}


def harvest_indexed_family(key, seen, limit, throttle, refresh=False, sink=None):
    """Fetch up to `limit` not-yet-crawled detail pages for a sitemap-backed family.

    Rows are handed to `sink` in batches of 25 for the same reason the id sweep
    flushes: a long run that dies at the end must not throw away everything it
    fetched. Resume is by URL (already-crawled URLs are skipped), so a flushed
    batch is permanently done.
    """
    fam = CRAWLED_INDEX_FAMILIES[key]
    cache = _load_index_cache()
    urls = cache.get(key)
    if refresh or not urls:
        print(f"[{key}] building the URL index from the sitemap...", flush=True)
        urls = fam["collect"](throttle)
        _save_index_cache(key, urls)
    todo = [u for u in urls if u not in seen]
    print(f"[{key}] {len(urls)} indexed, {len(urls) - len(todo)} already crawled, "
          f"fetching up to {limit} of the remaining {len(todo)}", flush=True)
    rows, misses = [], 0
    for u in todo[:limit]:
        time.sleep(throttle)
        try:
            r = requests.get(u, headers=UA, timeout=TIMEOUT)
        except Exception as e:
            print(f"  [{key}] {type(e).__name__} on {u[:70]}", flush=True)
            misses += 1
            continue
        if r.status_code != 200:
            misses += 1
            continue
        r.encoding = r.apparent_encoding or r.encoding
        rec = fam["parser"](r.text)
        if not rec:
            misses += 1
            continue
        rec.update(prefecture=fam["prefecture"], url=u)
        rows.append(rec)
        if sink and len(rows) >= 25:
            sink(rows)
            rows = []
    if misses:
        print(f"  [{key}] {misses} pages fetched but not parsed as a shrine record "
              f"(they stay in the index and are retried next run)", flush=True)
    return rows


def harvest_mie(seen, limit, throttle, refresh=False, sink=None):
    return harvest_indexed_family("mie", seen, limit, throttle, refresh, sink)


def harvest_kagoshima(seen, limit, throttle, refresh=False, sink=None):
    return harvest_indexed_family("kagoshima", seen, limit, throttle, refresh, sink)


def harvest_osaka(seen, limit, throttle, refresh=False, sink=None):
    return harvest_indexed_family("osaka", seen, limit, throttle, refresh, sink)


def _harvest_aichi_indexed(seen, limit, throttle, refresh=False, sink=None):
    """Aichi needs no budget: the whole register arrives in one POST."""
    return harvest_aichi()


INDEX_FAMILIES = {"aichi": _harvest_aichi_indexed,
                  "mie": harvest_mie,
                  "kagoshima": harvest_kagoshima,
                  "osaka": harvest_osaka}


def run_index_family(key, limit=200, throttle=THROTTLE, refresh=False):
    seen = load_seen()
    total = 0

    def sink(chunk):
        nonlocal total
        fresh = [r for r in chunk if r["url"] not in seen]
        if fresh:
            append_rows(fresh)
            seen.update(r["url"] for r in fresh)
            total += len(fresh)

    sink(INDEX_FAMILIES[key](seen, limit, throttle, refresh, sink))
    print(f"[{key}] +{total} new shrines (rest already present)", flush=True)
    return total


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
    ap.add_argument("--index", action="append", choices=sorted(INDEX_FAMILIES),
                    help="harvest an index-backed family (aichi: one API call; "
                         "mie/kagoshima: sitemap index + a --max-pages-capped fetch)")
    ap.add_argument("--refresh-index", action="store_true",
                    help="rebuild the cached sitemap URL list before harvesting")
    ap.add_argument("--list", action="store_true", help="show families and exit")
    args = ap.parse_args()

    if args.index:
        total = sum(run_index_family(k, args.max_pages, max(args.throttle, 0.5),
                                     args.refresh_index)
                    for k in args.index)
        print(f"\ntotal +{total} shrines -> {OUT_CSV}")
        if not (args.family or args.all):
            return

    if args.list:
        state = load_state()
        for k, f in sorted(FAMILIES.items()):
            print(f"{k:10} {f['prefecture']:10} ids {f['start']}-{f['stop']} "
                  f"next={state.get(k, f['start'])}")
        cache = _load_index_cache()
        seen = load_seen()
        for k in sorted(INDEX_FAMILIES):
            if k in CRAWLED_INDEX_FAMILIES:
                urls = cache.get(k, [])
                done = sum(1 for u in urls if u in seen)
                print(f"{k:10} {CRAWLED_INDEX_FAMILIES[k]['prefecture']:10} sitemap "
                      f"{done}/{len(urls) or '?'} crawled")
            else:
                print(f"{k:10} {'Aichi':10} single-request API index")
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
