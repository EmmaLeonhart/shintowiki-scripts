#!/usr/bin/env python3
"""Sample every registered drip file and report how many of its lines are already on Wikidata.

Read-only. Each file contributes at most --per-file random lines; their items are fetched with
batched wbgetentities (50 ids/call, 1s apart), so a full run is a few dozen API reads.

A line counts as LANDED when Wikidata already says what it says:
  * label/description/alias add  -> that exact text is there
  * statement add                -> a statement with that value exists, and every qualifier
                                    on the line is on one such statement
  * S-props must all sit on one reference of that statement (S813 retrieved-date ignored)
  * removal (-Qid or -P)          -> no statement with that value is left

Usage: python check_landed_sample.py [--per-file 20] [--seed 1] [files...]
"""
import argparse
import io
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "site"))
import build_qs_home as b  # noqa: E402

UA = {"User-Agent": "shintowiki-scripts landed-sample check (emma@topazcomputing.com)"}
API = "https://www.wikidata.org/w/api.php"


def parse(raw):
    first = b.COMPOUND.split(raw.split("    #")[0])
    out = []
    for part in first:
        if not part.strip():
            continue
        p = b.to_v1(part).split("\t")
        rm = p[0].startswith("-")
        if rm:
            p[0] = p[0][1:]
        if p[1].startswith("-"):
            rm, p[1] = True, p[1][1:]
        if len(p) >= 3 and re.fullmatch(r"Q\d+", p[0]):
            out.append((rm, p))
    return out


def norm(dv):
    v = dv.get("value")
    if isinstance(v, dict):
        if "id" in v:
            return v["id"]
        if "text" in v:
            return '%s:"%s"' % (v["language"], v["text"])
        if "time" in v:
            return v["time"][:11]
        if "amount" in v:
            return v["amount"].lstrip("+")
        if "latitude" in v:
            return "@%s/%s" % (v["latitude"], v["longitude"])
    return '"%s"' % v


def same(have, want):
    want = want.strip()
    if want.startswith("+") and re.match(r"\+\d{4}-", want):
        return have == want[:11]
    if want in ("somevalue", "novalue"):
        return have == want
    return have == want or have.strip('"') == want.strip('"') or have.lstrip("+") == want.lstrip("+")


def snakval(s):
    return norm(s["datavalue"]) if "datavalue" in s else s["snaktype"]


def landed(ent, rm, p):
    prop, value = p[1], p[2]
    m = re.fullmatch(r"([LDA])([a-z-]+)", prop)
    if m:
        kind = {"L": "labels", "D": "descriptions", "A": "aliases"}[m[1]]
        cur = ent.get(kind, {}).get(m[2])
        txt = value.strip().strip('"')
        has = any(a["value"] == txt for a in cur or []) if kind == "aliases" else bool(cur) and cur["value"] == txt
        return has != rm
    stmts = [c for c in ent.get("claims", {}).get(prop, []) if same(snakval(c["mainsnak"]), value)]
    if rm:
        return not stmts
    quals = [(p[i], p[i + 1]) for i in range(3, len(p) - 1, 2) if p[i].startswith("P")]
    # S813 (retrieved) carries the run date, so it never matches; judge a reference by the rest.
    refs = [("P" + p[i][1:], p[i + 1]) for i in range(3, len(p) - 1, 2)
            if p[i].startswith("S") and p[i] != "S813"]
    for c in stmts:
        cq = c.get("qualifiers", {})
        if not all(any(same(snakval(s), qv) for s in cq.get(qp, [])) for qp, qv in quals):
            continue
        if not refs or any(all(any(same(snakval(s), rv) for s in r["snaks"].get(rp, [])) for rp, rv in refs)
                           for r in c.get("references", [])):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-file", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("files", nargs="*")
    a = ap.parse_args()
    random.seed(a.seed)
    files = a.files or b.atomic_files() + ["sequential_misc.txt"]
    samples = {}
    for fn in files:
        units = []
        for raw in b.read(os.path.join(HERE, fn)):
            if raw.strip() and not raw.lstrip().startswith("#"):
                units.extend(parse(raw))
        if units:
            samples[fn] = random.sample(units, min(a.per_file, len(units)))
    ids = sorted({p[0] for v in samples.values() for _, p in v})
    ents = {}
    for i in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
                                    "props": "claims|labels|descriptions|aliases", "format": "json"})
        req = urllib.request.Request(API + "?" + q, headers=UA)
        try:
            ents.update(json.load(urllib.request.urlopen(req, timeout=60))["entities"])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                sys.exit("429 from Wikidata; stopping")
            raise
        time.sleep(1)
    print("landed/sampled  file")
    for fn, v in samples.items():
        hits = sum(landed(ents.get(p[0], {}), rm, p) for rm, p in v)
        print("%3d/%-3d  %s" % (hits, len(v), fn))


if __name__ == "__main__":
    main()
