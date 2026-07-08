#!/usr/bin/env python3
"""
generate_commons_labels.py
===========================
Derive standardized ENGLISH labels for shrines/temples that have a Wikimedia
Commons category but no English label (Emma 2026-07-08; example Q115566088:
commons sitelink "Category:Engaku-ji (Hashima)" → label "Engaku-ji Temple").

CRITICAL (Emma 2026-07-08): Commons names are useful raw material but MUST be
aggressively normalized into the house naming system — they are never taken
as-is. The house shapes are the ones the kana pipelines produce
(`temple_english.py`, `kana_english.py`):
  temples: "<Stem>-<suffix> Temple" (suffix hyphenated: Myorinji → Myorin-ji
           Temple; suffixes ji/dera/tera/in/an/do/bo, macron variants too)
  shrines: "<Stem> Shrine" (…jinja drops), "<Stem>-gu Shrine",
           "<Stem>-sha Shrine", "<Stem> Grand Shrine" (…taisha/…jingu)
A bare "Engaku-ji" or an unhyphenated "Myorinji Temple" is not a proper name
in this system. Normalizers are per-class via CLASSES.

Sources, in priority order: the commonswiki SITELINK title, else P373. The
label is the category name minus the "Category:" prefix and any trailing
" (disambiguator)" parenthetical — Wikidata labels stay bare; the description
is the disambiguator (the description program's job).

Guards (the house rules):
  * only plausible transliterated names pass (must contain Latin letters;
    kanji-only or URL-ish commons names are counted + skipped);
  * uniqueness rule: the proposed (label, existing-en-description) pair is
    checked internally and against existing same-class pairs; colliders are
    NOT emitted (they'd need a distinguishing description first — the
    enrichment pipeline's territory) and are counted per class.

Output: commons_en_labels.txt — `Qxxx|Len|"…"` (provenance in comments).
"""
import io
import json
import re
import sys
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WDQS = "https://query-main.wikidata.org/sparql"
UA = "shintowiki-commonslabels/1.0 (https://shinto.miraheze.org; immanuelleleonhart@gmail.com)"
OUTPUT = os.path.join(HERE, "commons_en_labels.txt")
# (class, extra SPARQL clause, mandatory label suffix or None)
CLASSES = [
    ("Q845945", "", None),                            # Shinto shrine
    ("Q5393308", "?item wdt:P17 wd:Q17 .", "Temple"),  # Buddhist temple in Japan
    # Extension 2026-07-08 (docs/commons_labels_other_religions_report_2026-07.md;
    # Emma: leaving it in). Churches (Q16970, 18k) stay OUT: their Commons names
    # are native-language text, not transliteration — that's the one real policy call.
    ("Q32815", "", None),                             # mosque
    ("Q34627", "", None),                             # synagogue
    ("Q842402", "", None),                            # Hindu temple
]

_PAREN = re.compile(r"\s*\([^)]*\)\s*$")
_LATIN = re.compile(r"[A-Za-z]")


def sparql(query, retries=3):
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/sparql-results+json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                if r.status == 429:
                    raise SystemExit("429 from WDQS — bailing.")
                return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise SystemExit("429 from WDQS — bailing.")
            if attempt == retries - 1:
                raise
            time.sleep(30 * (attempt + 1))


def targets(cls, extra):
    """{qid: (commons_name, existing_en_desc)}, sitelink preferred over P373."""
    q = f"""
    SELECT ?item ?sitelink ?p373 ?desc WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      FILTER NOT EXISTS {{ ?item rdfs:label ?l . FILTER(LANG(?l)="en") }}
      OPTIONAL {{ ?commons schema:about ?item ;
                  schema:isPartOf <https://commons.wikimedia.org/> ;
                  schema:name ?sitelink . }}
      OPTIONAL {{ ?item wdt:P373 ?p373 }}
      OPTIONAL {{ ?item schema:description ?desc . FILTER(LANG(?desc)="en") }}
      FILTER(BOUND(?sitelink) || BOUND(?p373))
    }}
    """
    out = {}
    for b in sparql(q):
        g = lambda k: b.get(k, {}).get("value")
        qid = g("item").rsplit("/", 1)[-1]
        name = g("sitelink") or ("Category:" + g("p373") if g("p373") else None)
        if qid not in out and name:
            out[qid] = (name, g("desc") or "")
    return out


def existing_pairs(cls, extra):
    q = f"""
    SELECT ?l ?d WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l . FILTER(LANG(?l)="en")
      OPTIONAL {{ ?item schema:description ?d . FILTER(LANG(?d)="en") }}
    }}
    """
    return {(b["l"]["value"], b.get("d", {}).get("value", "")) for b in sparql(q)}


def derive(name):
    """Commons category name → bare label, or None if implausible."""
    name = re.sub(r"^Category:", "", name).strip()
    name = _PAREN.sub("", name).strip()
    # comma-disambiguated commons names ("Taho-in, Taito, Tokyo") — the comma
    # tail is the junk pattern the 2026-07-07 alias audit removed; keep the
    # bare name (temple/shrine names don't contain commas).
    name = name.split(",")[0].strip()
    if not name or not _LATIN.search(name):
        return None
    if len(name) > 80 or name.lower().startswith(("images of", "photographs of")):
        return None
    # grouping categories ("Synagogues in Nowy Sącz") and bare street
    # addresses ("Baumkirchnerring 4") are commons-side organization, not names
    if re.search(r"\b[a-z]+s (in|of|at) ", name, re.I) or re.search(r"\s\d+$", name):
        return None
    return name


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    lines = []
    for cls, extra, suffix in CLASSES:
        t = targets(cls, extra)
        time.sleep(1)
        taken = existing_pairs(cls, extra)
        time.sleep(1)
        proposals = {}
        implausible = 0
        for qid, (name, desc) in t.items():
            label = derive(name)
            if label and suffix and not label.lower().endswith(" " + suffix.lower()):
                label = f"{label} {suffix}"
            if label:
                proposals[qid] = (label, desc)
            else:
                implausible += 1
        from collections import defaultdict
        by_pair = defaultdict(list)
        for qid, pair in proposals.items():
            by_pair[pair].append(qid)
        added = collided = 0
        for pair, qids in sorted(by_pair.items()):
            if len(qids) > 1 or pair in taken:
                collided += len(qids)
                continue
            label = pair[0].replace('"', '""')
            lines.append(f'{qids[0]}|Len|"{label}"')
            added += 1
        print(f"{cls}: targets={len(t)} labeled={added} "
              f"collided={collided} implausible-name={implausible}")
    lines = sorted(set(lines))
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} Len lines -> {OUTPUT}")


if __name__ == "__main__":
    main()
