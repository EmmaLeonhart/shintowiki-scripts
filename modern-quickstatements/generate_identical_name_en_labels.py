"""
generate_identical_name_en_labels.py — Stage 2 of the English-label pipeline.

For each Shinto shrine that has a ja label but NO kana and NO en label (the
no-kana subset of ``shrines_missing_en_label.json``), reuse the English label
of OTHER shrines that share the identical Japanese name. The dominant reading
becomes the label; an alias is added only when there's exactly one other
distinct reading (see ``reuse_labels.choose_label``). Adds-only — no removals.

Why this design (not a SPARQL self-join):
  A self-join on identical ja-label strings across ~30k shrines takes ~32s for
  60 rows on WDQS and times out at scale. Instead we already hold the en-less
  shrines locally (the worklist), so we POST batched ``VALUES ?ja { ... }``
  queries (GET 431s on large bodies; POST is ~1s per 150 labels) to fetch the
  en labels of same-named shrines, then decide locally.

Candidate en labels are normalized by stripping a trailing parenthetical
disambiguator ("Maruyama Shrine (Oita)" -> "Maruyama Shrine") so a
location-specific label is never reused verbatim on a different shrine.

Output: ``identical_name_en_labels.txt`` (Len + Aen), in
``submit_daily_batch.ATOMIC_FILES``. Regenerated daily by the worklist workflow.

Usage:
    python generate_identical_name_en_labels.py            # write the .txt
    python generate_identical_name_en_labels.py --stats    # query + report only
    python generate_identical_name_en_labels.py --limit 300  # cap targets (smoke)
"""

import argparse
import io
import json
import os
import re
import sys
import time
from collections import Counter

import requests

from reuse_labels import choose_label

HERE = os.path.dirname(os.path.abspath(__file__))
WORKLIST = os.path.join(HERE, "shrines_missing_en_label.json")
OUTPUT_FILE = os.path.join(HERE, "identical_name_en_labels.txt")

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
SHINTO_SHRINE = "Q845945"
BATCH = 150
THROTTLE = 0.5  # gentle pacing between SPARQL POSTs
TRANSIENT_STATUS = (500, 502, 503, 504)

_PAREN_DISAMBIG = re.compile(r"\s*\([^)]*\)\s*$")


class RateLimitError(Exception):
    """HTTP 429 — bail immediately, no retries (repo policy)."""


def normalize_en(label):
    """Strip a trailing parenthetical disambiguator and surrounding space."""
    return _PAREN_DISAMBIG.sub("", label).strip()


def _sparql_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def fetch_batch(ja_labels, retries=3):
    """POST a VALUES query for a batch of ja labels; return (ja, en) rows, or
    None if the endpoint stayed unavailable. Bails on 429."""
    values = " ".join('"%s"@ja' % _sparql_escape(j) for j in ja_labels)
    query = (
        "SELECT ?ja ?en WHERE {\n"
        "  VALUES ?ja { " + values + " }\n"
        "  ?b wdt:P31 wd:" + SHINTO_SHRINE + " ; rdfs:label ?ja ; rdfs:label ?en .\n"
        '  FILTER(LANG(?en)="en")\n'
        "}\n"
    )
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(
                SPARQL_ENDPOINT,
                data={"query": query, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=180,
            )
            if r.status_code == 429:
                print("FATAL: 429 Too Many Requests from SPARQL endpoint — bailing")
                raise RateLimitError("429 Too Many Requests")
            if r.status_code in TRANSIENT_STATUS:
                print(f"SPARQL {r.status_code} transient (attempt {attempt}/{retries})")
                if attempt < retries:
                    time.sleep(10 * attempt)
                    continue
                return None
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except requests.exceptions.ReadTimeout:
            print(f"SPARQL timeout (attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(10 * attempt)
            else:
                return None
        except requests.exceptions.ConnectionError as e:
            print(f"SPARQL connection error (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(10 * attempt)
            else:
                return None


def gather_candidates(ja_labels):
    """Return {ja_label: Counter(normalized_en -> shrine_count)} for the given
    distinct ja labels, or None if a batch could not be fetched."""
    counters = {}
    distinct = sorted(set(ja_labels))
    for i in range(0, len(distinct), BATCH):
        chunk = distinct[i:i + BATCH]
        rows = fetch_batch(chunk)
        if rows is None:
            return None
        for row in rows:
            ja = row["ja"]["value"]
            en = normalize_en(row["en"]["value"])
            if not en:
                continue
            counters.setdefault(ja, Counter())[en] += 1
        time.sleep(THROTTLE)
    return counters


def lines_for_target(qid, ja, counters):
    """QuickStatements lines for one target shrine, or [] if no reuse is possible."""
    counter = counters.get(ja)
    if not counter:
        return []
    chosen = choose_label(dict(counter), qid)
    if chosen is None:
        return []
    label, alias = chosen
    if '"' in label or (alias and '"' in alias):
        return []
    lines = [f'{qid}|Len|"{label}"']
    if alias:
        lines.append(f'{qid}|Aen|"{alias}"')
    return lines


def load_targets():
    if not os.path.exists(WORKLIST):
        return []
    with open(WORKLIST, encoding="utf-8") as f:
        items = json.load(f).get("items", [])
    # no-kana subset: kana-bearing shrines are Stage 1's job
    return [it for it in items if not (it.get("kana") or "").strip() and it.get("ja")]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true", help="Query + report, write nothing.")
    ap.add_argument("--limit", type=int, default=0, help="Cap number of targets (smoke).")
    args = ap.parse_args()

    targets = load_targets()
    if args.limit:
        targets = targets[: args.limit]
    print(f"Stage 2 targets (no-kana, no-en): {len(targets)} shrines, "
          f"{len(set(t['ja'] for t in targets))} distinct ja labels.")

    counters = gather_candidates([t["ja"] for t in targets])
    if counters is None:
        print("SPARQL unavailable — leaving existing output untouched.")
        return

    all_lines = []
    handled = 0
    for t in targets:
        lines = lines_for_target(t["qid"], t["ja"], counters)
        if lines:
            handled += 1
        all_lines.extend(lines)

    label_lines = sum(1 for ln in all_lines if "|Len|" in ln)
    alias_lines = sum(1 for ln in all_lines if "|Aen|" in ln)
    print(f"Reused a same-name en label for {handled}/{len(targets)} targets "
          f"-> {label_lines} labels + {alias_lines} aliases.")

    if args.stats:
        return
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))
        if all_lines:
            f.write("\n")
    print(f"Wrote {os.path.basename(OUTPUT_FILE)}")


if __name__ == "__main__":
    main()
