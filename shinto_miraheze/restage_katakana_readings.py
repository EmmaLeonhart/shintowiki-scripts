#!/usr/bin/env python3
"""
restage_katakana_readings.py
============================
Recover the mixed-script readings that the old blanket katakana gate threw away.

BACKGROUND. `collect_name_in_kana.py` used to demand pure hiragana for P1814.
That correctly refuses the ancient-reading error (all-katakana values like
アスキ- / カミノヤシロ), but it also refused readings that are legitimately
part-katakana because the shrine's name contains a foreign place-name or
loanword. Those answers were recorded in `name_in_kana/_resolved.log` with the
KATAKANA status and produced no statement at all.

Emma ruled 2026-08-05 that these should be allowed, on the argument that the
cleanup the gate was guarding against only touches items carrying an ojp-hani
P1448 with a confirmed カミノヤシロ qualifier and emits value-matched removals —
so an overseas shrine, which has neither, was never at risk. `acceptable_reading`
now allows any all-kana value containing at least one hiragana character.

Their work-files are already deleted (the collector disposes of what it answers),
so the log is the only remaining record — which is what this reads. The jawiki
article URL for the S4656 reference is fetched fresh from each item's sitelink
rather than dropped, so a restaged line carries the same provenance a normally
collected one would.

Idempotent: an item already present in name_in_kana.txt is skipped, so a second
run is a no-op. One `wbgetentities` call, no SPARQL.

Usage:
    python restage_katakana_readings.py            # report only
    python restage_katakana_readings.py --apply
"""
import argparse
import io
import os
import re
import sys
import urllib.parse

import requests
from shinto_miraheze.ua_contact import contact

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
LOG = os.path.join(REPO_ROOT, "name_in_kana", "_resolved.log")
QS_OUT = os.path.join(REPO_ROOT, "modern-quickstatements", "name_in_kana.txt")
JAWIKI_ITEM = "Q177837"

# Was building the agent from the wiki-side contact rather than the Wikidata one, on a
# Wikidata request. The two agents are separate by design; resolve, never hand-build.
# was: a hand-built agent using the wiki-side contact
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
UA = WIKIDATA_USER_AGENT

sys.path.insert(0, HERE)
from collect_name_in_kana import acceptable_reading, clean_kana  # noqa: E402
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL


def katakana_entries(text):
    """[(qid, reading)] from the log's KATAKANA rows. The note after an em-dash
    is commentary, not part of the reading, so it is cut before cleaning."""
    out = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or parts[1] != "KATAKANA":
            continue
        reading = clean_kana(re.split(r"\s+—\s+|\s+--\s+", parts[2])[0])
        out.append((parts[0], reading))
    return out


def already_staged(path):
    if not os.path.exists(path):
        return set()
    return {m.group(1) for m in
            (re.match(r"^(Q\d+)\|", ln) for ln in open(path, encoding="utf-8")) if m}


def sitelinks(qids):
    """{qid: jawiki article URL}. One request; missing sitelink -> absent."""
    wd_pace(SPARQL_INTERVAL)
    r = requests.get("https://www.wikidata.org/w/api.php", params={
        "action": "wbgetentities", "ids": "|".join(qids),
        "props": "sitelinks", "sitefilter": "jawiki", "format": "json",
    }, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    out = {}
    for qid, ent in r.json().get("entities", {}).items():
        title = ent.get("sitelinks", {}).get("jawiki", {}).get("title")
        if title:
            out[qid] = ("https://ja.wikipedia.org/wiki/"
                        + urllib.parse.quote(title.replace(" ", "_")))
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(LOG):
        print("no _resolved.log; nothing to restage")
        return

    entries = katakana_entries(open(LOG, encoding="utf-8").read())
    staged = already_staged(QS_OUT)

    todo, skipped = [], []
    for qid, reading in entries:
        if qid in staged:
            skipped.append((qid, reading, "already staged"))
        elif not acceptable_reading(reading):
            skipped.append((qid, reading, "still refused by the gate"))
        else:
            todo.append((qid, reading))

    for qid, reading, why in skipped:
        print(f"  SKIP {qid} {reading} — {why}")
    if not todo:
        print("nothing to restage")
        return

    urls = sitelinks([q for q, _ in todo])
    lines = []
    for qid, reading in todo:
        line = f'{qid}|P1814|"{reading}"'
        if qid in urls:
            line += f'|S143|{JAWIKI_ITEM}|S4656|"{urls[qid]}"'
        else:
            print(f"  note: {qid} has no jawiki sitelink — staged without a reference")
        lines.append(line)
        print(f"  {line}")

    if args.apply:
        with open(QS_OUT, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\nappended {len(lines)} line(s) to {QS_OUT}")
    else:
        print(f"\n{len(lines)} line(s) [report only; pass --apply]")


if __name__ == "__main__":
    main()
