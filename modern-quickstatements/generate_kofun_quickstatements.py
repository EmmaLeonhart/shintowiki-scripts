#!/usr/bin/env python3
"""
generate_kofun_quickstatements.py
==================================
Import kofun data from the jawiki {{日本の古墳}} infobox onto Wikidata — the
new-class build from `docs/jawiki_infobox_import_review_2026-07.md`.

Two fields, both conservative:
  * 形状 (mound shape) → an additional **P31 shape-class** statement. The
    review guessed P1419, but the live convention on well-modeled kofun
    (Daisen, Hashihaka, Goshikizuka…) is P31 subclass items (前方後円墳
    Q11268718, 円墳 Q11394747, …) and NO kofun uses P1419 — we follow the
    data. Vocabulary of 10 shape classes, every QID resolved + verified via
    wbsearchentities on 2026-07-08 (never from memory). Fields naming
    multiple different shapes are skipped.
  * 築造時期 / 築造年代 (construction period) → **P571 at century
    precision** for plain 「N世紀」 forms (前半/後半/中頃/末/初頭/頃 tolerated —
    still the same century); ranges, multiple centuries, and explicit years
    are skipped.

Items already carrying a shape-class P31 (resp. any P571) are skipped.
Output: kofun_imports.txt — atomic cited lines (S4656 jawiki URL).
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
WDQS = "https://query-main.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
TEMPLATE = "Template:日本の古墳"
OUTPUT = os.path.join(HERE, "kofun_imports.txt")

# Verified 2026-07-08 via wbsearchentities + label check. Longest names first
# so 前方後円墳 wins over 円墳 as a substring.
SHAPE_QIDS = {
    "帆立貝形古墳": "Q11480883",
    "前方後円墳": "Q11268718",
    "前方後方墳": "Q11397225",
    "双方中円墳": "Q11410445",
    "上円下方墳": "Q11358496",
    "長方形墳": "Q80793203",
    "八角墳": "Q11391751",
    "双円墳": "Q119983533",
    "円墳": "Q11394747",
    "方墳": "Q11504353",
}
_SHAPE_ORDER = sorted(SHAPE_QIDS, key=len, reverse=True)
_FIELD_SHAPE = re.compile(r"\|\s*形状\s*=\s*([^\n]*)")
_FIELD_PERIOD = re.compile(r"\|\s*築造(?:時期|年代)\s*=\s*([^\n]*)")
_CENTURY = re.compile(r"(\d{1,2})世紀")


def _get(params):
    params = dict(params)
    params["format"] = "json"
    req = urllib.request.Request(JA_API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def embedded_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": TEMPLATE,
             "einamespace": 0, "eilimit": "max"}
        if cont:
            p["eicontinue"] = cont
        d = _get(p)
        titles += [e["title"] for e in d.get("query", {}).get("embeddedin", [])]
        cont = d.get("continue", {}).get("eicontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def fetch_batch(titles):
    d = _get({"action": "query", "prop": "revisions|pageprops", "rvprop": "content",
              "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles), "redirects": 1})
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        qid = p.get("pageprops", {}).get("wikibase_item")
        revs = p.get("revisions", [])
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        out.append((p["title"], qid, text))
    return out


def parse_shape(field):
    field = re.sub(r"<!--.*?-->", "", field, flags=re.S)
    hits = {SHAPE_QIDS[s] for s in _SHAPE_ORDER if s in field}
    # substring containment: a 前方後円墳 field also contains 円墳 — resolve by
    # longest-match: keep only shapes whose NAME occurs not merely inside a
    # longer matched name.
    names = []
    rest = field
    for s in _SHAPE_ORDER:
        if s in rest:
            names.append(s)
            rest = rest.replace(s, "")
    qids = {SHAPE_QIDS[s] for s in names}
    return qids.pop() if len(qids) == 1 else None


def parse_century(field):
    field = re.sub(r"<!--.*?-->", "", field, flags=re.S)
    if re.search(r"[〜～\-–]|\d{3,4}年", field):
        return None
    cents = {int(c) for c in _CENTURY.findall(field)}
    if len(cents) != 1:
        return None
    c = cents.pop()
    if not 3 <= c <= 8:      # the kofun period; anything else is suspect
        return None
    return c


def existing_sets():
    shapes = " ".join(f"wd:{q}" for q in SHAPE_QIDS.values())
    q1 = f"SELECT ?item WHERE {{ VALUES ?s {{ {shapes} }} ?item wdt:P31 ?s . }}"
    q2 = "SELECT ?item WHERE { ?item wdt:P31 wd:Q1141225 ; wdt:P571 [] . }"
    out = []
    for q in (q1, q2):
        url = WDQS + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "application/sparql-results+json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status == 429:
                raise SystemExit("429 from WDQS — bailing.")
            rows = json.load(r)["results"]["bindings"]
        out.append({b["item"]["value"].rsplit("/", 1)[-1] for b in rows})
        time.sleep(1)
    return out  # (has_shape, has_p571)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    has_shape, has_date = existing_sets()
    print(f"{len(has_shape)} items already have a shape-class P31; "
          f"{len(has_date)} kofun already have P571")
    titles = embedded_titles()
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} jawiki kofun articles")

    lines = []
    stats = {"shape": 0, "date": 0, "shape_skip": 0, "date_skip": 0, "no_qid": 0}
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            if not qid:
                stats["no_qid"] += 1
                continue
            url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            m = _FIELD_SHAPE.search(text or "")
            if m and m.group(1).strip():
                shape = parse_shape(m.group(1))
                if shape and qid not in has_shape:
                    lines.append(f'{qid}|P31|{shape}|S4656|"{url}"')
                    stats["shape"] += 1
                elif not shape:
                    stats["shape_skip"] += 1
            m = _FIELD_PERIOD.search(text or "")
            if m and m.group(1).strip():
                c = parse_century(m.group(1))
                if c and qid not in has_date:
                    year = (c - 1) * 100 + 1
                    lines.append(f'{qid}|P571|+{year:04d}-00-00T00:00:00Z/7|S4656|"{url}"')
                    stats["date"] += 1
                elif not c:
                    stats["date_skip"] += 1
        time.sleep(0.3)

    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} lines -> {OUTPUT} | {stats}")


if __name__ == "__main__":
    main()
