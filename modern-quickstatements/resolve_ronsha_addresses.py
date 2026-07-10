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
import argparse
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

UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
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


def normalise_municipality(name):
    """`横浜市　西区` -> [`横浜市`, `西区`]; `大紀町` -> [`大紀町`]."""
    return [p for p in re.split(r"[\s　]+", name.strip()) if p]


def address_matches(address, prefecture, municipality):
    """Does this Japanese address sit in that prefecture and municipality?"""
    if not address.startswith(prefecture):
        return False
    return all(part in address for part in normalise_municipality(municipality))


def matching_addresses(addresses, prefecture, municipality):
    return [a for a in addresses if address_matches(a, prefecture, municipality)]


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
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    items = candidates()
    print("{} Ronsha carry more than one Japanese address".format(len(items)))
    single = {q: v for q, v in items.items() if len(v["kokugakuin"]) == 1}
    print("{} of them have exactly one Kokugakuin id".format(len(single)))

    table = muni_table()
    print("{} GSI municipality codes".format(len(table)))

    rows, held = [], []
    for n, (qid, rec) in enumerate(sorted(single.items())):
        if args.limit and n >= args.limit:
            break
        kid = rec["kokugakuin"][0]
        try:
            coords = parse_coords(kokugakuin_page(kid))
        except Exception as exc:
            held.append((qid, kid, rec["addresses"], "page fetch failed: %s" % exc))
            continue
        if len(coords) != 1:
            held.append((qid, kid, rec["addresses"],
                         "the Kokugakuin entry lists %d candidate sites "
                         "(現社名など（１）…（%d）), so it cannot say which one this "
                         "Ronsha is" % (len(coords), len(coords))
                         if coords else "no coordinates on the record"))
            time.sleep(0.5)
            continue
        lat, lon = coords[0]
        try:
            place = reverse_geocode(lat, lon, table)
        except Exception as exc:
            held.append((qid, kid, rec["addresses"], "reverse geocode failed: %s" % exc))
            time.sleep(0.5)
            continue
        if not place:
            held.append((qid, kid, rec["addresses"], "coords resolve to no municipality"))
            time.sleep(0.5)
            continue
        pref, muni = place
        keep, drop = resolve_address(rec["addresses"], pref, muni)
        if keep is None:
            n = len(matching_addresses(rec["addresses"], pref, muni))
            why = ("coords say %s%s — %s" % (
                pref, muni,
                "NONE of its addresses is there" if n == 0
                else "%d of its addresses are both there" % n))
            held.append((qid, kid, rec["addresses"], why))
        else:
            rows.append((qid, kid, lat, lon, pref, muni, keep, drop))
        time.sleep(0.6)

    write_report(args.out, rows, held, len(items), len(single))
    print("\nRESOLVED {}   HELD {}   -> {}".format(len(rows), len(held), args.out))
    return 0


def write_report(path, rows, held, total, single):
    out = [
        "# Shikinai Ronsha — which address is right?",
        "",
        "Generated by `modern-quickstatements/resolve_ronsha_addresses.py`. **Report only:**",
        "no QuickStatements were emitted and nothing was removed.",
        "",
        "## Why the original rule could not work",
        "",
        "Emma's rule was *\"check which address is on the database page.\"* The Kokugakuin",
        "式内社データベース record **has no address field** — its fields are 旧郡名, 座数, 官幣・国幣,",
        "社格, 神階の変遷, テキスト内容, 現社名など, 緯度経度 and a map link. What it does carry is",
        "**coordinates**, so (Emma, 2026-07-10) *\"use the coordinates instead\"*: reverse-geocode",
        "them with the 国土地理院 service and keep the address whose 都道府県 + 市区町村 matches.",
        "",
        "An item resolves only when **exactly one** of its addresses matches. Everything else is held.",
        "",
        "* Ronsha with more than one Japanese address: **{}**".format(total),
        "* …of which exactly one Kokugakuin id: **{}**".format(single),
        "* Resolved: **{}**  ·  Held: **{}**".format(len(rows), len(held)),
        "",
        "## Resolved — one address matches the coordinates",
        "",
        "| Item | Kokugakuin | Coordinates | GSI says | KEEP | DROP |",
        "|---|---|---|---|---|---|",
    ]
    for qid, kid, lat, lon, pref, muni, keep, drop in rows:
        out.append("| [{0}](https://www.wikidata.org/wiki/{0}) | [{1}]({2}) | {3}, {4} | {5}{6} | `{7}` | {8} |".format(
            qid, kid, KOKUGAKUIN.format(kid), lat, lon, pref, muni, keep,
            " ".join("`%s`" % d for d in drop) or "—"))
    out += ["", "## Held — needs a human", "",
            "| Item | Kokugakuin | Addresses | Why |", "|---|---|---|---|"]
    for qid, kid, addrs, why in held:
        out.append("| [{0}](https://www.wikidata.org/wiki/{0}) | [{1}]({2}) | {3} | {4} |".format(
            qid, kid, KOKUGAKUIN.format(kid),
            " ".join("`%s`" % a for a in addrs), why))
    out.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out))


if __name__ == "__main__":
    raise SystemExit(main())
