"""Measure what a kana_redundant_remove line would take with it.

Emma, 2026-09-06 (queue.md): *"I have decided that instead of removing katakana, any improper
name in kana things should have the katakana replaced with hiragana, although wait that might
not work based on citations and qualifiers so look over the presence of them before making a
decision"*.

This is that look. The lines are not P1814 removals -- they remove a whole P1448 (official
name) statement that carries the katakana as a P1814 QUALIFIER:

    -Q111776816|P1448|ojp-hani:"広瀬神社"|P1814|"ヒロセノ"

A QuickStatements statement-removal takes the statement's references and every other
qualifier with it, and a re-add comes back bare. So "replace instead of remove" is only
cheaper if those statements are bare to begin with. This counts, per targeted statement:
references, and qualifiers other than the P1814 being replaced.

Read-only. Throwaway -- delete after the numbers are recorded.
"""
import collections
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "EmmaLeonhart-audit/1.0 (emma@topazcomputing.com)"
SRC = os.path.join(HERE, "kana_redundant_remove.txt")


def targets():
    """[(qid, value, kana)] from the 5-field removal lines."""
    out = []
    for line in io.open(SRC, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = line.split("|")
        if len(f) == 5 and f[1] == "P1448":
            qid = f[0].lstrip("-")
            val = f[2].split(":", 1)[1].strip('"') if ":" in f[2] else f[2].strip('"')
            out.append((qid, val, f[4].strip('"')))
    return out


def fetch(qids):
    ents = {}
    for i in range(0, len(qids), 40):
        chunk = "|".join(qids[i:i + 40])
        url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&ids=" + chunk +
               "&props=claims&format=json")
        out = subprocess.run(["curl", "-s", "-A", UA, url],
                             capture_output=True, text=True).stdout
        ents.update(json.loads(out).get("entities", {}))
    return ents


def main():
    tg = targets()
    qids = sorted({q for q, _, _ in tg})
    print("removal lines targeting a P1448 statement: {}".format(len(tg)))
    print("distinct items: {}".format(len(qids)))
    ents = fetch(qids)

    refs = collections.Counter()
    extra_quals = collections.Counter()
    matched = missing = 0
    qual_props = collections.Counter()

    for qid, val, kana in tg:
        claims = ents.get(qid, {}).get("claims", {}).get("P1448", [])
        hit = None
        for c in claims:
            dv = c["mainsnak"].get("datavalue", {}).get("value", {})
            if isinstance(dv, dict) and dv.get("text") == val:
                hit = c
                break
        if hit is None:
            missing += 1
            continue
        matched += 1
        refs[len(hit.get("references", []))] += 1
        q = hit.get("qualifiers", {})
        others = [p for p in q if p != "P1814"]
        extra_quals[len(others)] += 1
        for p in others:
            qual_props[p] += 1

    print("\nmatched the live statement: {}   not found (already gone/changed): {}".format(
        matched, missing))
    print("\nREFERENCES on the targeted statement:")
    for n, c in sorted(refs.items()):
        print("   {} reference(s): {:>4} statements".format(n, c))
    print("\nQUALIFIERS other than the P1814 being replaced:")
    for n, c in sorted(extra_quals.items()):
        print("   {} other qualifier(s): {:>4} statements".format(n, c))
    if qual_props:
        print("\n   which properties:", dict(qual_props.most_common()))

    lossy = sum(c for n, c in refs.items() if n) + \
        sum(c for n, c in extra_quals.items() if n)
    print("\nSTATEMENTS THAT WOULD LOSE SOMETHING on a remove+readd: {}".format(lossy))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    raise SystemExit(main())
