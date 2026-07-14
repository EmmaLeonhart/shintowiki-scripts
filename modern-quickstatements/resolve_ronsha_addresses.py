#!/usr/bin/env python3
"""Which of a Shikinai Ronsha's several Japanese addresses is the right one?

REPORT ONLY. This script emits no QuickStatements and removes nothing. Emma
2026-07-09: *"Report before editing; do not guess a rule and drip it."*

WHY THE ORIGINAL RULE COULD NOT WORK
-----------------------------------
Emma's method, metabolised from the wiki queue on 2026-07-09:

    "if they have only one database link then check which address is on the
    database page. Keep the one that is and not the one that isn't."

The Kokugakuin 式内社データベース record **has no address field.** Fetched and
checked: its fields are 大分類, 旧郡名, 座数, 官幣・国幣, 社格, 名神大社・大社・小社,
月次祭・新嘗祭の有無, 神階の変遷, テキスト内容, 現社名など（N）, **現社名など（N）緯度経度**,
現社名など（N）リンク, コンテンツ権利区分, 資料ID. No 所在地, no 住所, no 鎮座地.

WHAT IT DOES HAVE IS COORDINATES
--------------------------------
「北緯 34 度 21 分 57.77 秒 東経 136 度 25 分 33.28 秒」. Emma, told this
(2026-07-10): *"Use the coordinates instead."*

So: read the coordinates off the record, reverse-geocode them with the 国土地理院
(GSI) service — an official Japanese government source, no API key, no rate limit
published — and keep the candidate address whose 都道府県 + 市区町村 prefix matches
the place the shrine actually stands.

    coords -> GSI LonLatToAddress -> muniCd -> GSI muni.js -> 三重県 / 大紀町

An item is only resolved when **exactly one** of its addresses matches. Zero
matches, several matches, several sets of coordinates on the record, or anything
else ambiguous is HELD and reported, never guessed.

The Kokugakuin database is CC BY-NC-SA. Only the derived fact — which of the item's
own existing addresses is correct — is used; nothing is copied.

    python resolve_ronsha_addresses.py [--out FILE]
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import argparse
import collections
import io
import json
import os
import re
import sys
import time
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(REPO, "docs", "ronsha_address_resolution_2026-07.md")

UA = USER_AGENT
HEADERS = {"User-Agent": UA}
SPARQL = "https://query-main.wikidata.org/sparql"

RONSHA = "Q135022904"
KOKUGAKUIN = "https://jmapps.ne.jp/kokugakuin/det.html?data_id={}"
GSI_REVERSE = "https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress"
GSI_MUNI = "https://maps.gsi.go.jp/js/muni.js"

# 「北緯 34 度 21 分 57.77 秒 東経 136 度 25 分 33.28 秒」
_COORD = re.compile(
    r"北緯\s*(\d+)\s*度\s*(\d+)\s*分\s*([\d.]+)\s*秒\s*"
    r"東経\s*(\d+)\s*度\s*(\d+)\s*分\s*([\d.]+)\s*秒")
# Any address that opens with a prefecture name at all.
_NAMES_A_PREFECTURE = re.compile(r"^.{2,4}?[都道府県]")
_MUNI_ENTRY = re.compile(r"MUNI_ARRAY\[\s*[\"'](\d+)[\"']\s*\]\s*=\s*'([^']*)'")


def dms_to_decimal(deg, minute, second):
    return int(deg) + int(minute) / 60.0 + float(second) / 3600.0


def visible_text(html):
    """Tags out, whitespace collapsed.

    Load-bearing: the record writes the coordinate as
    `北緯 33 度 36 分 34.56 秒 <br />東経 134 度 22 分 2.05 秒`, so a regex run against
    raw HTML matches nothing at all. The first live run reported "0 coordinate sets"
    for all 33 items because of exactly this.
    """
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&[a-z]+;", " ", html)
    return re.sub(r"[\s　]+", " ", html)


def parse_coords(page_text):
    """Every 緯度経度 on the record, as (lat, lon). Several means several sites."""
    out = []
    for d1, m1, s1, d2, m2, s2 in _COORD.findall(page_text):
        out.append((round(dms_to_decimal(d1, m1, s1), 6),
                    round(dms_to_decimal(d2, m2, s2), 6)))
    # A record often repeats the same coordinate in markup; distinct sites are
    # what matter.
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


# 〒708-0013 津山市二宮601 — a postcode prefix, and no prefecture at all.
_POSTCODE = re.compile(r"^\s*〒?\s*\d{3}[-‐−ー]?\d{4}\s*")
_FULLWIDTH_DIGITS = {ord("０") + i: ord("0") + i for i in range(10)}


def normalise_address(address):
    """Strip a leading 〒postcode and fold fullwidth digits.

    Three of the 67 addresses begin `〒NNN-NNNN`. Because `address_matches` required
    the string to START with the prefecture, every one of them failed to match and
    was DROPPED by a `resolved` verdict — including two that were simply the *same
    place stated more precisely* (`〒950-0075 新潟県新潟市中央区沼垂東１丁目１番１７号`
    beside `新潟県新潟市中央区沼垂東`). Silently discarding the better address is
    exactly the failure this whole report exists to prevent.
    """
    return _POSTCODE.sub("", (address or "")).translate(_FULLWIDTH_DIGITS).strip()


def normalise_municipality(name):
    """`横浜市　西区` -> [`横浜市`, `西区`]; `大紀町` -> [`大紀町`]."""
    return [p for p in re.split(r"[\s　]+", name.strip()) if p]


def address_matches(address, prefecture, municipality):
    """Does this Japanese address sit in that prefecture and municipality?

    An address that names its prefecture must name the RIGHT one. An address that
    omits it (`津山市二宮601`, once its postcode is stripped) is judged on the
    municipality alone.
    """
    address = normalise_address(address)
    if not address:
        return False
    if _NAMES_A_PREFECTURE.match(address) and not address.startswith(prefecture):
        return False
    return all(part in address for part in normalise_municipality(municipality))


def matching_addresses(addresses, prefecture, municipality):
    return [a for a in addresses if address_matches(a, prefecture, municipality)]


def match_matrix(addresses, places):
    """Every address against every coordinate.

    Emma 2026-07-10: *"almost all of them have multiple coordinates, and you're
    supposed to match between all the addresses and all the coordinates."*

    A Kokugakuin entry lists N candidate shrines, `現社名など（１）…（N）`, each with its
    own 緯度経度. So several coordinate sets is the normal case, not a blocker.

    `places` is [(prefecture, municipality), …], one per coordinate.
    Returns [(address_index, place_index), …] for every pair that matches.
    """
    hits = []
    for i, addr in enumerate(addresses):
        for j, place in enumerate(places):
            if place and address_matches(addr, place[0], place[1]):
                hits.append((i, j))
    return hits


def verdict(addresses, places):
    """(kind, kept, dropped).

    kind is one of:
      'resolved'  exactly one address matches any coordinate -> keep it
      'no-match'  NO address matches ANY coordinate. Emma's predicted glitch: the
                  entry's coordinates were taken from an ADJACENT, non-candidate
                  shrine, so nothing on the page corresponds to this item at all.
      'several'   more than one distinct address matches; the entry cannot choose.
    """
    hits = match_matrix(addresses, places)
    matched = sorted({i for i, _ in hits})
    if not matched:
        return "no-match", None, []
    if len(matched) > 1:
        return "several", None, []
    keep = addresses[matched[0]]
    return "resolved", keep, [a for a in addresses if a != keep]


def resolve_address(addresses, prefecture, municipality):
    """(kept, dropped) when exactly one matches; (None, []) otherwise."""
    hits = matching_addresses(addresses, prefecture, municipality)
    if len(hits) != 1:
        return None, []
    return hits[0], [a for a in addresses if a != hits[0]]


# ─────────────────────────── live lookups ───────────────────────────

def sparql(query):
    for attempt in range(4):
        r = requests.get(SPARQL, params={"query": query, "format": "json"},
                         headers=dict(HEADERS, Accept="application/sparql-results+json"),
                         timeout=180)
        if r.status_code == 429:
            raise SystemExit("FATAL: 429 — bailing (429 policy)")
        if r.status_code == 200:
            return r.json()["results"]["bindings"]
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("SPARQL failed")


def candidates():
    """{qid: {'addresses': [...], 'kokugakuin': [...]}} for >1 Japanese address."""
    rows = sparql("""
    SELECT ?item ?addr ?kid WHERE {
      ?item wdt:P31 wd:%s ; wdt:P6375 ?addr .
      FILTER(LANG(?addr) = "ja")
      OPTIONAL { ?item wdt:P13677 ?kid }
    }""" % RONSHA)
    out = {}
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        rec = out.setdefault(qid, {"addresses": set(), "kokugakuin": set()})
        rec["addresses"].add(b["addr"]["value"])
        if "kid" in b:
            rec["kokugakuin"].add(b["kid"]["value"])
    return {q: {"addresses": sorted(v["addresses"]),
                "kokugakuin": sorted(v["kokugakuin"])}
            for q, v in out.items() if len(v["addresses"]) > 1}


def muni_table():
    r = requests.get(GSI_MUNI, headers=HEADERS, timeout=60)
    r.encoding = "utf-8"
    table = {}
    for code, payload in _MUNI_ENTRY.findall(r.text):
        parts = payload.split(",")
        if len(parts) >= 4:
            table[code] = (parts[1], parts[3])      # (prefecture, municipality)
    return table


def kokugakuin_page(data_id):
    r = requests.get(KOKUGAKUIN.format(data_id), headers=HEADERS, timeout=60)
    r.raise_for_status()
    return visible_text(r.text)


GSI_FORWARD = "https://msearch.gsi.go.jp/address-search/AddressSearch"


def haversine_km(lat1, lon1, lat2, lon2):
    from math import asin, cos, radians, sin, sqrt
    dlon, dlat = radians(lon2 - lon1), radians(lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def geocode_address(address):
    """(lat, lon) of a Japanese address via the 国土地理院 address search, or None."""
    r = requests.get(GSI_FORWARD, params={"q": normalise_address(address)},
                     headers=HEADERS, timeout=60)
    r.raise_for_status()
    hits = r.json()
    if not hits:
        return None
    lon, lat = hits[0]["geometry"]["coordinates"]
    return (round(lat, 6), round(lon, 6))


def nearest_coord_km(address_pt, coords):
    """Distance from a geocoded address to the closest coordinate on the entry."""
    if not address_pt or not coords:
        return None
    return min(haversine_km(address_pt[0], address_pt[1], c[0], c[1]) for c in coords)


def reverse_geocode(lat, lon, table):
    r = requests.get(GSI_REVERSE, params={"lat": lat, "lon": lon},
                     headers=HEADERS, timeout=60)
    r.raise_for_status()
    muni = (r.json().get("results") or {}).get("muniCd")
    if not muni:
        return None
    return table.get(str(muni).lstrip("0")) or table.get(str(muni))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--json", help="also dump the raw match matrix here")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    items = candidates()
    print("{} Ronsha carry more than one Japanese address".format(len(items)))
    single = {q: v for q, v in items.items() if len(v["kokugakuin"]) == 1}
    print("{} of them have exactly one Kokugakuin id".format(len(single)))

    table = muni_table()
    print("{} GSI municipality codes".format(len(table)))

    results = []
    for n, (qid, rec) in enumerate(sorted(single.items())):
        if args.limit and n >= args.limit:
            break
        kid = rec["kokugakuin"][0]
        addrs = rec["addresses"]
        try:
            coords = parse_coords(kokugakuin_page(kid))
        except Exception as exc:
            results.append((qid, kid, addrs, [], [], "error", "page fetch failed: %s" % exc, []))
            continue
        if not coords:
            results.append((qid, kid, addrs, [], [], "error", "no coordinates on the record", []))
            time.sleep(0.4)
            continue

        # EVERY candidate site on the entry gets reverse-geocoded, not just the first.
        places = []
        for lat, lon in coords:
            try:
                places.append(reverse_geocode(lat, lon, table))
            except Exception:
                places.append(None)
            time.sleep(0.5)

        kind, keep, drop = verdict(addrs, places)

        # Municipality granularity cannot see a coordinate borrowed from an
        # adjacent shrine inside the same municipality. So also geocode each
        # ADDRESS and measure how far it is from the nearest coordinate on the
        # entry. Emma's hypothesis predicts every distance is large.
        dists = []
        for a in addrs:
            try:
                dists.append(nearest_coord_km(geocode_address(a), coords))
            except Exception:
                dists.append(None)
            time.sleep(0.4)

        results.append((qid, kid, addrs, coords, places, kind,
                        keep if keep else drop, dists))
        time.sleep(0.3)

    if args.json:
        io.open(args.json, "w", encoding="utf-8", newline="\n").write(json.dumps(
            [{"qid": q, "kid": k, "addresses": a, "coords": c,
              "places": [list(p) if p else None for p in pl],
              "kind": kind, "matrix": match_matrix(a, pl),
              "km_to_nearest_coord": dd}
             for q, k, a, c, pl, kind, _v, dd in results], ensure_ascii=False, indent=2))
    write_report(args.out, results, len(items), len(single))
    counts = collections.Counter(r[5] for r in results)
    print("")
    for k in ("resolved", "no-match", "several", "error"):
        if counts[k]:
            print("  {:9} {}".format(k, counts[k]))
    print("-> {}".format(args.out))
    return 0


def write_report(path, results, total, single):
    resolved = [r for r in results if r[5] == "resolved"]
    nomatch = [r for r in results if r[5] == "no-match"]
    several = [r for r in results if r[5] == "several"]
    errors = [r for r in results if r[5] == "error"]

    def places_str(places):
        return " ".join("`%s%s`" % (p[0], p[1]) if p else "`?`" for p in places) or "—"

    def addrs_str(addrs, dists=None):
        if not dists:
            return " ".join("`%s`" % a for a in addrs)
        return "<br>".join(
            "`%s` — %s" % (a, "%.2f km" % d if d is not None else "?")
            for a, d in zip(addrs, dists))

    out = [
        "# Shikinai Ronsha — which address is right?",
        "",
        "Generated by `modern-quickstatements/resolve_ronsha_addresses.py`. **Report only:**",
        "no QuickStatements were emitted and nothing was removed.",
        "",
        "## Method",
        "",
        "Emma's original rule was *\"check which address is on the database page.\"* The Kokugakuin",
        "式内社データベース record **has no address field** — only 現社名など（N）, 緯度経度 and a map",
        "link. Emma 2026-07-10: *\"Use the coordinates instead\"*, and then: *\"almost all of them have",
        "multiple coordinates, and you're supposed to match between all the addresses and all the",
        "coordinates.\"*",
        "",
        "An entry lists N candidate shrines, `現社名など（１）…（N）`, each with its own coordinate. So",
        "**every** coordinate is reverse-geocoded (国土地理院 `LonLatToAddress` → `muniCd` → `muni.js`)",
        "and **every** address is tested against **every** coordinate.",
        "",
        "* **resolved** — exactly one address matches some coordinate. Keep it, drop the rest.",
        "* **no-match** — no address matches any coordinate. Emma's predicted glitch: the entry's",
        "  coordinates belong to an *adjacent, non-candidate* shrine, so nothing on the page",
        "  corresponds to this item at all.",
        "* **several** — more than one address matches; the entry cannot choose.",
        "",
        "* Ronsha with more than one Japanese address: **{}**".format(total),
        "* …of which exactly one Kokugakuin id: **{}**".format(single),
        "* resolved **{}** · no-match **{}** · several **{}** · error **{}**".format(
            len(resolved), len(nomatch), len(several), len(errors)),
        "",
        "## no-match — nothing on the entry corresponds to this item",
        "",
        "This is the glitch Emma predicted. The entry's coordinates name places none of the item's",
        "addresses sit in.",
        "",
        "| Item | Kokugakuin | Item's addresses — km to nearest coordinate | Entry's coordinates resolve to |",
        "|---|---|---|---|",
    ]
    for qid, kid, addrs, coords, places, _k, _v, d in nomatch:
        out.append("| [{0}](https://www.wikidata.org/wiki/{0}) | [{1}]({2}) | {3} | {4} |".format(
            qid, kid, KOKUGAKUIN.format(kid), addrs_str(addrs, d), places_str(places)))

    out += ["", "## resolved — exactly one address matches a coordinate", "",
            "| Item | Kokugakuin | Entry resolves to | KEEP | DROP |", "|---|---|---|---|---|"]
    for qid, kid, addrs, coords, places, _k, keep, _d in resolved:
        drop = [a for a in addrs if a != keep]
        out.append("| [{0}](https://www.wikidata.org/wiki/{0}) | [{1}]({2}) | {3} | `{4}` | {5} |".format(
            qid, kid, KOKUGAKUIN.format(kid), places_str(places), keep,
            " ".join("`%s`" % d for d in drop) or "—"))

    out += ["", "## several — more than one address matches", "",
            "Each address is shown with its distance to the *nearest* coordinate on the entry",
            "(address geocoded with the 国土地理院 address search).",
            "",
            "| Item | Kokugakuin | Addresses — km to nearest coordinate | Entry resolves to |",
            "|---|---|---|---|"]
    for qid, kid, addrs, coords, places, _k, _v, d in several:
        out.append("| [{0}](https://www.wikidata.org/wiki/{0}) | [{1}]({2}) | {3} | {4} |".format(
            qid, kid, KOKUGAKUIN.format(kid), addrs_str(addrs, d), places_str(places)))

    if errors:
        out += ["", "## error", "", "| Item | Kokugakuin | Why |", "|---|---|---|"]
        for qid, kid, addrs, coords, places, _k, why, _d in errors:
            out.append("| [{0}](https://www.wikidata.org/wiki/{0}) | [{1}]({2}) | {3} |".format(
                qid, kid, KOKUGAKUIN.format(kid), why))
    out.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out))


if __name__ == "__main__":
    raise SystemExit(main())
