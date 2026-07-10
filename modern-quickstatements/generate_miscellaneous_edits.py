#!/usr/bin/env python3
"""The miscellaneous-edits queue: small, safe, non-urgent Wikidata fixes.

Emma 2026-07-10:

    "I want us to have a miscellaneous edits queue thing for relatively small
    things that we're going to wait on … This file will be in the modern quick
    statements, so it's going to be eventually run, and I think this is just kind
    of a safe thing."

Nothing here is time-critical. Everything waits behind `conflict_gate`, like every
other batch, and then drips at the normal rate.

Additions need no justification beyond the note beside them. **A removal must be
named, one line at a time, in `STATIC_REMOVALS`** — `assert_removals_enumerated()`
refuses any `-` line the list does not contain. Nothing in this file may compute a
removal.

## What lives here

**1. Conspicuous single-item errors.**  `STATIC_EDITS`, each with the reason it is
here. A one-line fix that is not worth its own generator belongs in this list.

**2. Wrong addresses on Shikinai Ronsha.**  `STATIC_REMOVALS`, 17 of them, decided
by Emma on 2026-07-10 from `docs/ronsha_address_resolution_2026-07.md`. Each names
the address to drop *and the address to keep*; the generator refuses to emit the
removal unless it can see both of them live on the item, so a shrine can never be
left with no address at all. See `ADDRESS_REMOVALS` below for how each was decided.

**3. The Kikuna Shrine restoration.**  On 2026-07-09 `ブルーノ・プラス` emptied
`Q28069431`, the older community-made Kikuna Shrine item, stripping five `P825`
enshrined deities, the image, the website, both phone numbers, `P17`, `P31` and
`P131`, and then its labels and descriptions. It now holds 0 claims and 0 sitelinks.

Kikuna Shrine has **two** items. `Q134926804` is ours (`Immanuelle`, "New shrine
item (bot)", 2025-06-15); it holds the jawiki `菊名神社` sitelink, coordinates, the
Son-sha rank and social IDs. So the blanking looks like a manual merge into our item
that was never finished with a redirect.

We restore onto **our** item and leave the husk alone. Emma:

    "We are not going to be doing anything with the Kikuna Shrine that they nuked …
    because of the fact that they don't have the one that we made on their
    watchlist. It's not going to appear to be a reversion or anything like that.
    It's just adding more statements. … Kikuna Shrine is one that we kind of got
    lucky on because of the fact that there already is a duplicate."

The lines are **diffed against live state**, so the batch shrinks as values land —
whether we add them or, better, somebody else does. Emma: *"it'll naturally start to
reaccumulate content, because the idea here is we would ideally want other people to
do it."*

The repurposed item `Q123044569` (Kamo Shrine → 大美和神社) is deliberately **not**
here. It is actively edited, actively misleading, and on hold.

    python generate_miscellaneous_edits.py [--out FILE]
"""
import argparse
import io
import json
import os
import shutil
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = "miscellaneous_edits.txt"
OUTPUT = os.path.join(HERE, OUTPUT_FILE)

WD_API = "https://www.wikidata.org/w/api.php"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

# ── 1. one-off fixes ────────────────────────────────────────────────────────
# (qid, property-or-term-code, value, why)
STATIC_EDITS = [
    # Its English label is the *Commons category name*, "Category:Shinmei-gū
    # (Kanagawa-ku, Yokohama)", which leaked in from the commonswiki sitelink.
    # Emma 2026-07-10: "This is a rather conspicuous error."
    ("Q138565446", "Len", '"Shinmei-gū (Kanagawa-ku, Yokohama)"',
     "English label is a Commons category name"),
]

# ── 2. wrong addresses on Shikinai Ronsha ───────────────────────────────────
# `located at street address` (P6375). (qid, address to DROP, address to KEEP, why)
#
# Three kinds, all decided by Emma 2026-07-10:
#
#   a. Seven items where the shrine carries two addresses and only one of them is
#      anywhere near the coordinates the Kokugakuin database gives for the entry.
#      Emma: "resolve them and remove the incorrect address."
#   b. Seven of the eighteen conflations — two shrines' addresses on one item —
#      where the item's *own* coordinates fall in one address's municipality and
#      not the other's. Emma: "Keep the address matching the item's own
#      coordinates." The other eleven are reported, not touched.
#   c. Three same-place addresses written two ways. Emma: "Dedupe the 3."
#
# Every DROP differs from its KEEP as a string, so a value-matched QuickStatements
# removal cannot take the wrong statement.
ADDRESS_REMOVALS = [
    # a. one address is far from the Kokugakuin entry's coordinates
    ("Q106852693", "徳島県那賀郡那賀町和食字町154", "徳島県海部郡海陽町大里",
     "30.3 km from every coordinate on Kokugakuin entry 183216"),
    ("Q11358379", "徳島県名西郡神山町神領", "徳島県徳島市国府町矢野",
     "14.5 km from every coordinate on Kokugakuin entry 183197"),
    ("Q11487151", "静岡県沼津市西浦江梨329", "静岡県伊東市十足",
     "30.1 km from every coordinate on Kokugakuin entry 181631"),
    ("Q11553669", "山梨県南都留郡富士河口湖町河口1", "山梨県笛吹市一宮町一ノ宮",
     "14.8 km from every coordinate on Kokugakuin entry 181673"),
    ("Q48758315", "徳島県海部郡海陽町大里", "徳島県阿南市羽ノ浦町中庄千田池32",
     "46.4 km from every coordinate on Kokugakuin entry 183214"),
    ("Q48758398", "徳島県名西郡石井町高川原桜間281", "徳島県徳島市明神町",
     "9.1 km from every coordinate on Kokugakuin entry 183199"),
    ("Q97311695", "千葉県松戸市小金原5-28-12", "千葉県流山市三輪野山",
     "6.5 km from every coordinate on Kokugakuin entry 181751"),

    # b. conflation resolved by the item's own coordinates
    ("Q11379248", "兵庫県西宮市大社町", "兵庫県宝塚市伊孑志1-4-3",
     "the item's own coordinates are in Takarazuka, not Nishinomiya"),
    ("Q11379327", "大阪府池田市綾羽", "兵庫県尼崎市下坂部4丁目13-26",
     "the item's own coordinates are in Amagasaki, not Ikeda"),
    ("Q11673954", "兵庫県たつの市揖保町中臣", "兵庫県姫路市網干区宮内193",
     "the item's own coordinates are in Himeji, not Tatsuno"),
    ("Q124496744", "愛知県一宮市今伊勢町馬寄", "岐阜県羽島市桑原町八神4665",
     "the item's own coordinates are in Hashima, not Ichinomiya"),
    ("Q124668655", "愛知県江南市宮田町四ツ谷", "〒501-6021 岐阜県各務原市川島笠田町１４６",
     "the item's own coordinates are in Kakamigahara, not Kōnan"),
    ("Q54153265", "茨城県常陸太田市天神林町", "茨城県久慈郡大子町下野宮1626",
     "the item's own coordinates are in Daigo, not Hitachiōta"),
    ("Q66085129", "群馬県吾妻郡東吾妻町箱島", "群馬県渋川市祖母島499",
     "the item's own coordinates are in Shibukawa, not Higashiagatsuma"),

    # c. the same place written twice
    ("Q11464224", "東京都多摩市一ノ宮", "東京都多摩市一の宮一丁目18-8",
     "same place, written without the block number"),
    ("Q11625297", "東京都青梅市根ケ布", "東京都青梅市根ヶ布1-316",
     "same place, written with 大 ケ for small ヶ and no block number"),
    ("Q63148121", "新潟県新潟市中央区沼垂東", "〒950-0075 新潟県新潟市中央区沼垂東１丁目１番１７号",
     "same place, written without the block number"),
]

P_ADDRESS = "P6375"


def removal_line(qid, address):
    return '-{}|{}|ja:"{}"'.format(qid, P_ADDRESS, address)


STATIC_REMOVALS = frozenset(
    removal_line(q, drop) for q, drop, _keep, _why in ADDRESS_REMOVALS)


# ── 3. Kikuna Shrine restoration ────────────────────────────────────────────
KIKUNA_HUSK = "Q28069431"       # emptied 2026-07-09; left alone on purpose
KIKUNA_TARGET = "Q134926804"    # ours; holds the jawiki 菊名神社 sitelink

# Exactly what stood on Q28069431 immediately before the blanking (revision
# 2488056826, 2026-05-06). Read off that revision, never reconstructed from memory.
KIKUNA_STATEMENTS = [
    ("P17", "Q17"),                 # country: Japan
    ("P31", "Q845945"),             # Shinto shrine
    ("P131", "Q1358965"),           # Kōhoku-ku
    ("P18", '"Kikuna Shrine in Yokohama City.jpg"'),
    ("P825", "Q317997"),            # Ōjin
    ("P825", "Q455602"),            # Amaterasu
    ("P825", "Q461258"),            # Yamato Takeru
    ("P825", "Q1781862"),           # Konohanasakuyahime
    ("P825", "Q1073668"),           # Takenouchi no Sukune
    ("P856", '"http://www.kikunajinja.jp/profile/"'),
    ("P1329", '"+81-45-431-9344"'),
    ("P2900", '"+81-45-431-9972"'),
]


def _api(params):
    params = dict(params, format="json")
    req = urllib.request.Request(WD_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def entity(qid):
    """The entity dict, or None if missing / deleted / redirected."""
    ent = _api({"action": "wbgetentities", "ids": qid}).get("entities", {}).get(qid)
    if not ent or "missing" in ent or ent.get("type") == "redirect":
        return None
    return ent


def present_values(claims, prop):
    """Values of `prop`, rendered the way KIKUNA_STATEMENTS writes them."""
    out = set()
    for st in claims.get(prop, []):
        dv = st["mainsnak"].get("datavalue")
        if not dv:
            continue
        if dv["type"] == "wikibase-entityid":
            out.add(dv["value"]["id"])
        elif dv["type"] == "string":
            out.add('"{}"'.format(dv["value"]))
    return out


def missing_statements(ent, wanted):
    claims = ent.get("claims", {})
    return [(p, v) for p, v in wanted if v not in present_values(claims, p)]


def qs_line(qid, prop, value):
    return "{}|{}|{}".format(qid, prop, value)


def address_values(claims):
    """The Japanese street addresses standing on an item right now."""
    out = set()
    for st in claims.get(P_ADDRESS, []):
        dv = st["mainsnak"].get("datavalue")
        if dv and dv["type"] == "monolingualtext" and dv["value"]["language"] == "ja":
            out.add(dv["value"]["text"])
    return out


def address_removal_lines(live_addresses):
    """Removals for the items whose live state still matches what Emma decided on.

    `live_addresses` is {qid: {address, ...}}. A removal is emitted only when the
    item still carries **both** the address to drop and the address to keep. If the
    keep is gone the drop is silently the last address left, and dropping it would
    leave the shrine with none; if the drop is gone the work is already done.
    """
    lines, skipped = [], []
    for qid, drop, keep, _why in ADDRESS_REMOVALS:
        live = live_addresses.get(qid)
        if live is None:
            skipped.append((qid, "item is gone"))
        elif drop not in live:
            skipped.append((qid, "already removed"))
        elif keep not in live:
            skipped.append((qid, "the address to keep, {}, is no longer on the item "
                                 "— refusing to drop the last one".format(keep)))
        else:
            lines.append(removal_line(qid, drop))
    return lines, skipped


def assert_removals_enumerated(lines):
    """The invariant: every deletion is one Emma named. Nothing computes a removal."""
    bad = [l for l in lines
           if l.lstrip().startswith("-") and l not in STATIC_REMOVALS]
    if bad:
        raise RuntimeError(
            "miscellaneous_edits may only remove what STATIC_REMOVALS names: "
            "{!r}".format(bad[:3]))


def build(kikuna_entity, live_addresses=None):
    """(lines, notes). `kikuna_entity` is None when the target is gone."""
    lines, notes = [], []

    for qid, prop, value, why in STATIC_EDITS:
        lines.append(qs_line(qid, prop, value))
        notes.append("{} {} — {}".format(qid, prop, why))

    if live_addresses is not None:
        addr, skipped = address_removal_lines(live_addresses)
        lines.extend(addr)
        notes.append("addresses: {} of {} removals emitted".format(
            len(addr), len(ADDRESS_REMOVALS)))
        for qid, why in skipped:
            notes.append("  {} not removed — {}".format(qid, why))

    if kikuna_entity is None:
        notes.append("{} is gone; a replacement item is a CREATION, not a "
                     "restoration, and is Emma's call".format(KIKUNA_TARGET))
    else:
        missing = missing_statements(kikuna_entity, KIKUNA_STATEMENTS)
        lines.extend(qs_line(KIKUNA_TARGET, p, v) for p, v in missing)
        notes.append("Kikuna: {} of {} statements absent from {}".format(
            len(missing), len(KIKUNA_STATEMENTS), KIKUNA_TARGET))

    assert_removals_enumerated(lines)
    return lines, notes



def publish_to_site(path):
    """Mirror the batch into _site/ so the dashboard can link it."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    live = {}
    for qid in sorted({q for q, _d, _k, _w in ADDRESS_REMOVALS}):
        ent = entity(qid)
        if ent is not None:
            live[qid] = address_values(ent.get("claims", {}))

    target = entity(KIKUNA_TARGET)
    lines, notes = build(target, live)

    husk = entity(KIKUNA_HUSK)
    notes.append("husk {}: {}".format(
        KIKUNA_HUSK,
        "still present with {} claims — left alone on purpose".format(
            len(husk.get("claims", {}))) if husk else "deleted or redirected"))

    path = args.out if os.path.dirname(args.out) else os.path.join(HERE, args.out)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ("\n".join(lines) + "\n") if lines else "")

    for n in notes:
        print("  " + n)
    print("\n{} line(s) -> {}".format(len(lines), path))
    for l in lines:
        print("   " + l)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
