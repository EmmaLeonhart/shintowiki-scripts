"""
generate_katakana_reading_remove.py
===================================
Step 2 of the top-level-katakana `P1814` replacement: the REMOVE generator.
GENERATOR ONLY — writes QuickStatements removal lines into an atomic .txt file
for the single daily submitter. NEVER edits Wikidata; no edit summaries.
(CLAUDE.md "Wikidata editing — ONE path only".)

This is the SEPARATE second script; `generate_katakana_reading_add.py` is step 1.
It emits a removal ONLY for an item where a fresh SPARQL query confirms the
derived hiragana reading is ALREADY on the item. The confirmation is in the
SPARQL, so under the drip's random run order a removal can never be generated
before its add has landed, and the item is never left with no reading at all.

Both scripts derive the hiragana the same way, through
`english_to_kana.kana_for`, so the value confirmed here is by construction the
value step 1 proposed. Nothing is matched loosely: the item must carry that exact
string.

This is a whole-statement removal of a top-level `P1814`, which QuickStatements
expresses correctly. It is NOT the qualifier removal that destroyed four ojp-hani
official names on 2026-09-09 — see `generate_kana_qualifier_remove.py`'s
docstring and `tests/test_qualifier_removal_is_refused.py`.

⚠ The removal takes the katakana statement's references with it. That is correct
here: they are references FOR the katakana value, which is the thing being
retired. Of the four items in scope, three carry one reference each and
`Q135935015` carries none.

Output: katakana_reading_remove.txt
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
import os
import shutil
import sys
import time
import requests

_usys.path.insert(0, _uos.path.dirname(_uos.path.abspath(__file__)))
from english_to_kana import kana_for
from generate_katakana_reading_add import QUERY, collect, is_katakana, qid

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
OUTPUT_FILE = "katakana_reading_remove.txt"


class RateLimitError(Exception):
    """Raised on HTTP 429 — bail, no retries."""


_last = 0.0


def fetch_sparql(query, retries=3):
    global _last
    for attempt in range(1, retries + 1):
        elapsed = time.time() - _last
        if elapsed < 5:
            time.sleep(5 - elapsed)
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
                timeout=120,
            )
        except requests.exceptions.ReadTimeout:
            _last = time.time()
            if attempt < retries:
                time.sleep(10 * attempt)
                continue
            print("SPARQL timed out after retries — exiting gracefully")
            return None
        _last = time.time()
        if r.status_code == 429:
            print("FATAL: 429 Too Many Requests from SPARQL endpoint — bailing")
            raise RateLimitError("429")
        if r.status_code in (503, 504):
            # CLAUDE.md: 503/504 -> back off hard, do not retry tightly.
            if attempt < retries:
                time.sleep(15 * (3 ** (attempt - 1)))
                continue
            print(f"SPARQL returned {r.status_code} after retries — exiting gracefully")
            return None
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def s(text):
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def build_lines(items):
    """(lines, report). A removal is emitted only when the derived hiragana is
    already among the item's P1814 values — i.e. step 1 has landed."""
    lines, report = [], []
    for q in sorted(items):
        rec = items[q]
        katakana = sorted(v for v in rec["values"] if is_katakana(v))
        if not katakana:
            continue
        derived = kana_for(rec["ja"], rec["en"])
        if not derived:
            report.append((q, katakana, None, "no derivation — nothing was ever added"))
            continue
        if derived not in rec["values"]:
            report.append((q, katakana, derived, "add has not landed yet — holding"))
            continue
        for value in katakana:
            lines.append(f"-{q}|P1814|{s(value)}")
        report.append((q, katakana, derived, "remove"))
    return lines, report


def publish_to_site(path):
    """Copy the batch into _site/ for the GitHub Pages browser. The file the daily
    editor reads is the bare-name one in this directory; this is only the published
    copy. Guarded against SameFileError so it is safe if handed the _site path."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()

    print("=== Generate katakana P1814 REMOVE QuickStatements (no direct edits) ===\n")
    rows = fetch_sparql(QUERY)
    if rows is None:
        print("No SPARQL result — leaving the existing file untouched.")
        return
    items = collect(rows)
    lines, report = build_lines(items)

    for q, katakana, derived, verdict in report:
        print(f"  {q:<12} {'/'.join(katakana):<26} derived={derived or '-':<22} [{verdict}]")

    path = args.out if os.path.dirname(args.out) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.out)
    with open(path, "w", encoding="utf-8") as f:
        # Sorted at the writer, per DEVLOG 2026-08-21: WDQS row order is not stable.
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    publish_to_site(path)
    print(f"\nWrote {len(lines)} lines to {path} "
          f"(0 is normal until the adds have landed)")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
