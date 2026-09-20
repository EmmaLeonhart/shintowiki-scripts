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

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import io
import json
import os
import re
import sys
import time
from collections import Counter

import requests

import staged_readings
from reuse_labels import choose_label

HERE = os.path.dirname(os.path.abspath(__file__))
WORKLIST = os.path.join(HERE, "shrines_missing_en_label.json")
OUTPUT_FILE = os.path.join(HERE, "identical_name_en_labels.txt")

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
SHINTO_SHRINE = "Q845945"
BATCH = 150

# ⛔ 0.5s HERE WAS A RULE VIOLATION, AND THE 429s WERE ITS PREDICTED RESULT.
# CLAUDE.md: "DO NOT HAMMER WIKIDATA … never issue a large batched SPARQL sweep",
# and `wdqs_transport.WDQS_THROTTLE = 2.5` is the repo's floor, described there as
# "no caller can ask to be FASTER than the floor". This file hand-rolls its own
# transport and paced itself at **0.5s**, five times faster, across ~70 batched
# POSTs per run for shrines and temples together.
#
# `Generate shrines-missing-en-label list` failed 5 of its last 6 runs — 09-16,
# 09-17, 09-18, 09-19, 09-20 — every one of them `RateLimitError: 429` from both
# Stage 2 steps, so `identical_name_en_labels.txt` and
# `temple_identical_name_en_labels.txt` have not regenerated since 09-17 and have
# been re-offering landed lines since.
#
# ⚠ This removes the violation and cuts this generator's request rate fivefold.
# It is NOT a claim that the 429s stop: the endpoint's limit is not published and
# the workflow makes other WDQS calls in the same window. The next runs are the
# measurement. If it still rate-limits, the levers are a slower throttle (the
# transport lets a caller be slower, never faster) or a smaller BATCH.
#
# ⚠ Why the throttle and not a full migration to `wdqs_transport`: that module's
# own docstring says migration "is per-file reading and is NOT uniformly an
# upgrade", and this file's `except ValueError` truncated-body handling is one of
# the cases it cites — WDQS answering 200 and cutting the body mid-row. Swapping
# several hard-won error paths at once, in the only producer of two atomic files,
# to fix a pacing bug is more change than the bug needs.
from wdqs_transport import WDQS_THROTTLE, RETRIES
THROTTLE = max(0.5, WDQS_THROTTLE)
TRANSIENT_STATUS = (500, 502, 503, 504)

_PAREN_DISAMBIG = re.compile(r"\s*\([^)]*\)\s*$")

# SPARQL triples that select the instance class to reuse candidate labels from.
# Shrines (default) reuse from other Shinto shrines; the temple Stage 2 passes the
# Japanese-Buddhist-temple triples so temple labels are reused only from temples.
SHRINE_TRIPLES = "wdt:P31 wd:" + SHINTO_SHRINE
TEMPLE_TRIPLES = "wdt:P31 wd:Q5393308 ; wdt:P17 wd:Q17"


class RateLimitError(Exception):
    """HTTP 429 — bail immediately, no retries (repo policy)."""


def normalize_en(label):
    """Strip a trailing parenthetical disambiguator and surrounding space."""
    return _PAREN_DISAMBIG.sub("", label).strip()



def _backoff(attempt):
    """The repo's documented 5xx backoff: 15s, 45s, 135s (1-based attempt).

    ⛔ This was `10 * attempt` — 10s then 20s — and CLAUDE.md says the opposite in
    two places: *"503/504 -> back off hard, do not retry tightly"*, and the
    `generate_genbu_ids.py` floor is *"WDQS_THROTTLE = 2.5 ... with exponential
    backoff (15/45/135s)"*. `wdqs_transport` implements it as `15 * (3 ** attempt)`
    over `RETRIES = 4`, and its own comment says three attempts make the documented
    third step decoration.

    ⚠ This is what the 2026-09-20 dispatch actually showed, in the log, in order:

        Stage 2 targets (no-kana, no-en): 4082 shrines, 3041 distinct ja labels.
        SPARQL 502 transient (attempt 1/3)
        FATAL: 429 Too Many Requests from SPARQL endpoint - bailing

    The endpoint said "I am struggling", this waited ten seconds, asked again, and
    was told to go away. Raising THROTTLE to the floor earlier the same day did not
    touch that path, because the retry never consulted THROTTLE at all.

    ⚠ Cost, stated because it is not free: a batch that exhausts the backoff now
    spends 195s instead of 30s, against a `timeout-minutes: 20` job that normally
    finishes in ~7m. A run where several batches go transient could hit that
    ceiling. The job already treats a bail as red, so it would be visible.
    """
    return 15 * (3 ** (attempt - 1))

def _sparql_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def fetch_batch(ja_labels, retries=RETRIES, instance_triples=SHRINE_TRIPLES):
    """POST a VALUES query for a batch of ja labels; return (ja, en) rows, or
    None if the endpoint stayed unavailable. Bails on 429."""
    values = " ".join('"%s"@ja' % _sparql_escape(j) for j in ja_labels)
    query = (
        "SELECT ?ja ?en WHERE {\n"
        "  VALUES ?ja { " + values + " }\n"
        "  ?b " + instance_triples + " ; rdfs:label ?ja ; rdfs:label ?en .\n"
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
                    time.sleep(_backoff(attempt))
                    continue
                return None
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except ValueError as e:
            # A TRUNCATED BODY. WDQS answers 200 and then cuts the response short
            # mid-row; `r.json()` then raises requests' JSONDecodeError, which is a
            # ValueError and was caught by nothing here. On 2026-09-13 that ended a
            # forty-minute sweep at its last language with nothing written, because
            # these generators write their .txt only at the end. Purely additive:
            # no previously-succeeding path changes, a previously-fatal one retries.
            print(f"SPARQL short read (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(_backoff(attempt))
            else:
                return None
        except requests.exceptions.ReadTimeout:
            print(f"SPARQL timeout (attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(_backoff(attempt))
            else:
                return None
        except requests.exceptions.ConnectionError as e:
            print(f"SPARQL connection error (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(_backoff(attempt))
            else:
                return None


def gather_candidates(ja_labels, instance_triples=SHRINE_TRIPLES):
    """Return {ja_label: Counter(normalized_en -> count)} for the given distinct
    ja labels, or None if a batch could not be fetched."""
    counters = {}
    distinct = sorted(set(ja_labels))
    for i in range(0, len(distinct), BATCH):
        chunk = distinct[i:i + BATCH]
        rows = fetch_batch(chunk, instance_triples=instance_triples)
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
    # Emma 2026-07-06: use the most-common English label as the decided label and
    # DO NOT add aliases. Reusing other same-named items' labels as aliases dragged
    # in their typos (e.g. "Zebshō-ji Temple") and disambiguators ("…, Hino, Tokyo").
    label, _alias = chosen
    if '"' in label:
        return []
    return [f'{qid}|Len|"{label}"']


def load_targets(worklist=WORKLIST):
    """The no-kana subset — AFTER the staged readings are applied.

    ⛔ The top-up has to happen here too, not only in Stage 1. Stage 2 selects
    the items Stage 1 could not handle, and it decides that by asking whether
    the item has kana. Topping up in Stage 1 alone would leave these items
    looking kana-less here, so BOTH stages would emit an ``Len`` line for the
    same QID into two different atomic files, and whichever the drip ran second
    would silently overwrite the first. There is exactly one such collision in
    the whole output today, and it is not one of ours.
    """
    if not os.path.exists(worklist):
        return []
    with open(worklist, encoding="utf-8") as f:
        items = json.load(f).get("items", [])
    staged_readings.fill(items)
    # no-kana subset: kana-bearing items are Stage 1's job
    return [it for it in items if not (it.get("kana") or "").strip() and it.get("ja")]


def run(worklist=WORKLIST, output_file=OUTPUT_FILE, instance_triples=SHRINE_TRIPLES,
        kind="shrines", stats=False, limit=0):
    """Stage 2 for one instance class. Reuses an en label from another item of the
    same class sharing the identical ja name. Writes ``output_file`` unless stats."""
    targets = load_targets(worklist)
    if limit:
        targets = targets[:limit]
    print(f"Stage 2 targets (no-kana, no-en): {len(targets)} {kind}, "
          f"{len(set(t['ja'] for t in targets))} distinct ja labels.")

    counters = gather_candidates([t["ja"] for t in targets], instance_triples)
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

    if stats:
        return
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))
        if all_lines:
            f.write("\n")
    print(f"Wrote {os.path.basename(output_file)}")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", action="store_true", help="Query + report, write nothing.")
    ap.add_argument("--limit", type=int, default=0, help="Cap number of targets (smoke).")
    args = ap.parse_args()
    run(stats=args.stats, limit=args.limit)


if __name__ == "__main__":
    main()
