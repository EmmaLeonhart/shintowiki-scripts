#!/usr/bin/env python3
"""
fetch_cdo_readings.py
=====================
Agentic-RAG builder for the Min Dong (cdo, Bàng-uâ-cê) reading table used by the
cdo transliterator. Per Emma's directive, cdo is NOT a phonetic transliteration
of the kana — it is the **Min Dong romanization of the same Chinese characters
the zh generator produces**. So the table is keyed on the (traditional) hanzi
that appear in zh labels, and each cdo label is built by looking up every
character's reading.

Why traditional: Min Dong readings on en.wiktionary live on the TRADITIONAL
character page (万 has no ``|md=``; 萬 → ``uâng``). The zh generator emits
simplified (OpenCC t2s), so we convert simplified→traditional (s2t) before the
lookup, with a small hand map for Japanese-shinjitai forms OpenCC leaves alone
(恵→惠, 曽→曾, 気→氣).

The table (``cdo_readings.json``) is grown incrementally: this script fetches
``|md=`` (first variant, pre-slash) for any requested hanzi not already present
and merges them in. Run it with the always-present man'yōgana core (default) or
pass ``--corpus`` to walk the full shrine zh output and cover every character
that actually appears — that walk is what closes the long tail so ``cdoify`` can
emit for real labels.

Gentle on Wiktionary: 0.4s throttle, Miraheze-UA-policy-compliant User-Agent.
No wiki writes. ``--apply`` writes the JSON; default dry-run reports coverage.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from opencc import OpenCC

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import generate_chinese_quickstatements as z  # noqa: E402

TABLE_PATH = os.path.join(SCRIPT_DIR, "cdo_readings.json")
USER_AGENT = "ShintoWikiBot/1.0 (immanuelleleonhart@gmail.com) cdo-readings"
THROTTLE = 0.4

_s2t = OpenCC("s2t")

# Japanese-shinjitai man'yōgana forms OpenCC s2t does NOT convert to the Chinese
# traditional character whose Wiktionary page carries the |md= reading.
_SHINJITAI_TO_TRAD = {"恵": "惠", "曽": "曾", "気": "氣"}


def to_trad(ch: str) -> str:
    """Simplified/shinjitai hanzi → the traditional form the md= reading lives on."""
    if ch in _SHINJITAI_TO_TRAD:
        return _SHINJITAI_TO_TRAD[ch]
    return _s2t.convert(ch)


def manyogana_core() -> list[str]:
    """The fixed man'yōgana inventory the zh generator substitutes kana with —
    always present in any zh (hence cdo) label. Traditional-normalised, deduped."""
    simp = {ch for v in z.KANA_TO_CHINESE.values() for ch in v}
    return sorted({to_trad(c) for c in simp})


def md_reading(ch: str) -> "str | None":
    """First Min Dong (Bàng-uâ-cê) reading for a character from en.wiktionary's
    ``|md=`` field, or None if the page/field is absent. Slash-separated variants
    collapse to the first."""
    url = ("https://en.wiktionary.org/w/api.php?action=query&titles="
           + urllib.parse.quote(ch)
           + "&prop=revisions&rvprop=content&rvslots=main&formatversion=2&format=json")
    try:
        d = json.load(urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=30))
        pg = d["query"]["pages"][0]
        if pg.get("missing"):
            return None
        txt = pg["revisions"][0]["slots"]["main"]["content"]
        m = re.findall(r"\|\s*md\s*=\s*([^|}\n]+)", txt)
        return m[0].split("/")[0].strip() if m else None
    except Exception:
        return None


def load_table() -> dict:
    if os.path.exists(TABLE_PATH):
        with open(TABLE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_table(table: dict) -> None:
    with open(TABLE_PATH, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=1, sort_keys=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write cdo_readings.json.")
    ap.add_argument("--chars", default="",
                    help="Extra characters to look up (in addition to the core).")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    table = load_table()
    want = manyogana_core() + [to_trad(c) for c in args.chars if c.strip()]
    want = sorted(set(want))
    missing = [c for c in want if c not in table]
    print(f"Table: {len(table)} entries | requested: {len(want)} | to fetch: {len(missing)}")

    added = nomd = 0
    for ch in missing:
        r = md_reading(ch)
        if r:
            table[ch] = r
            added += 1
            print(f"  {ch} -> {r}")
        else:
            nomd += 1
            print(f"  {ch} -> (no md= reading on Wiktionary)")
        time.sleep(THROTTLE)

    covered = sum(1 for c in want if c in table)
    print(f"\nFetched {added} new; {nomd} had no reading. "
          f"Core/requested coverage: {covered}/{len(want)}.")
    if args.apply:
        save_table(table)
        print(f"Wrote {TABLE_PATH} ({len(table)} entries).")
    else:
        print("[DRY] pass --apply to write cdo_readings.json")


if __name__ == "__main__":
    main()
