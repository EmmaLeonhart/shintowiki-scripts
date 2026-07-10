#!/usr/bin/env python3
"""The miscellaneous-edits queue: small, safe, non-urgent Wikidata fixes.

Emma 2026-07-10:

    "I want us to have a miscellaneous edits queue thing for relatively small
    things that we're going to wait on … This file will be in the modern quick
    statements, so it's going to be eventually run, and I think this is just kind
    of a safe thing."

Nothing here is time-critical. Everything waits behind `conflict_gate`, like every
other batch, and then drips at the normal rate. **ADD-only or term-set; never a
removal** — `assert_no_removals()` enforces that on the way out.

## What lives here

**1. Conspicuous single-item errors.**  `STATIC_EDITS`, each with the reason it is
here. A one-line fix that is not worth its own generator belongs in this list.

**2. The Kikuna Shrine restoration.**  On 2026-07-09 `ブルーノ・プラス` emptied
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

# ── 2. Kikuna Shrine restoration ────────────────────────────────────────────
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


def assert_no_removals(lines):
    """The invariant: this queue only ever adds or sets, never deletes."""
    bad = [l for l in lines if l.lstrip().startswith("-")]
    if bad:
        raise RuntimeError("miscellaneous_edits is ADD-only: {!r}".format(bad[:3]))


def build(kikuna_entity):
    """(lines, notes). `kikuna_entity` is None when the target is gone."""
    lines, notes = [], []

    for qid, prop, value, why in STATIC_EDITS:
        lines.append(qs_line(qid, prop, value))
        notes.append("{} {} — {}".format(qid, prop, why))

    if kikuna_entity is None:
        notes.append("{} is gone; a replacement item is a CREATION, not a "
                     "restoration, and is Emma's call".format(KIKUNA_TARGET))
    else:
        missing = missing_statements(kikuna_entity, KIKUNA_STATEMENTS)
        lines.extend(qs_line(KIKUNA_TARGET, p, v) for p, v in missing)
        notes.append("Kikuna: {} of {} statements absent from {}".format(
            len(missing), len(KIKUNA_STATEMENTS), KIKUNA_TARGET))

    assert_no_removals(lines)
    return lines, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    target = entity(KIKUNA_TARGET)
    lines, notes = build(target)

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
