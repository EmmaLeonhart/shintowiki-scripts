"""Daily Wikidata-edit reporter (the QuickStatements path is RETIRED).

History: this script used to submit the atomic files through the
QuickStatements toolforge API. That API refuses every batch with
"Problem generating OAuth signature; user needs to have submitted a batch
manually at least once before", and Emma ruled out ever doing the one-time
manual web-UI batch (2026-07-04). The direct Wikidata API editor
(direct_daily_edits.py, 300 lines/day) is therefore the ONLY path — its
ATOMIC_FILES must stay a superset of the list below (drift-guard test:
tests/test_atomic_files_alignment.py).

What this script still does, and why it still runs daily in cleanup-loop:
 1. Writes the dated report under reports/ — cleanup-loop's
    wikidata-daily-fire gate reads the newest report's date to fire the
    edit jobs exactly once per UTC day.
 2. Exits nonzero, so the workflow's qs-failed output stays true and
    direct-daily-edits fires unchanged (no DAG surgery needed).
No network calls; the QS_TOKEN/QS_USERNAME secrets are no longer used.
"""

import io
import json
import os
import sys
from datetime import datetime, timezone

ATOMIC_FILES = [
    "modern_shrine_ranking_qualifiers.txt",   # Phase 1: add P459 to existing P13723
    "p4656_jawiki_references.txt",            # Add P4656 ja.wiki references to modern P13723
    "p958_qualifiers.txt",                    # Add P958 section qualifiers to P13677
    "remove_shikinai_hiteisha.txt",           # Remove P31=Q135026601 (Shikinai Hiteisha)
    "remove_shikinaisha.txt",                 # Remove P31=Q134917286 (Shikinaisha) from Shikinai Ronsha items
    "engishiki_add_references.txt",           # Add Kokugakuin refs to Engishiki/Ritsuryō P13723
    "p11250_miraheze_links.txt",              # Add P11250 (Miraheze article ID) links
    "p6262_fandom_links.txt",                 # Add P6262 (Fandom article ID) links
    "en_labels.txt",                          # Add en labels (Len) for items with a shintowiki page but no en label
    "kana_en_labels.txt",                     # Stage 1: en labels (Len) + aliases (Aen) deterministically built from kana (generate_kana_en_labels.py); no LLM
    "identical_name_en_labels.txt",           # Stage 2: en labels (Len) + aliases (Aen) reused from same-ja-name shrines (generate_identical_name_en_labels.py); no LLM
    "temple_en_labels.txt",                    # Temples Stage 1: en labels (Len) "<Stem>-<suffix> Temple" deterministically built from kana for Japanese Buddhist temples (generate_temple_en_labels.py); no LLM
    "temple_identical_name_en_labels.txt",     # Temples Stage 2: en labels (Len) + aliases (Aen) reused from same-ja-name Japanese temples (generate_temple_identical_name_en_labels.py); no LLM
    "cjk_ja_backfill.txt",                     # C1: copy a CJK (zh) name onto the ja label for shrines lacking one (generate_cjk_ja_backfill.py)
    "en_labels_sonnet.txt",                   # Add en labels (Len) machine-translated by the daily remote Sonnet routine (5/day) from ja label + kana
    "label_proposals_drip.txt",               # 20/day random multilingual labels drip-fed from the shinto-label-generator subtree
    "kana_qualifier_add.txt",                 # Add <kana>カミノヤシロ P1814 qualifier to ojp-hani P1448 official names (bot request 2026-02-26)
    "kana_redundant_remove.txt",              # Remove redundant raw katakana (qualifier/top-level) AFTER the カミノヤシロ qualifier is confirmed present
    "migrate_ritsuryo_funding_remove.txt",    # Remove P31 ritsuryō funding values once P13723 is confirmed
    "migrate_ritsuryo_funding_underspecified_remove.txt",  # Remove P31=Kanpei-sha when more specific funding type present
    "recreation_relations.txt",               # Deferred family relations (P22/P25/P40/P3373) between recreated deleted-items; from recreate-deleted-wikidata/match_new_qids.py
]


def read_batch(filepath):
    """Read all lines from a file, return as list of non-empty lines."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def write_report(report, quiet=False):
    """Write run report to reports/ directory."""
    os.makedirs("reports", exist_ok=True)
    ts = report["timestamp"].replace(":", "-").replace(" ", "_")
    filepath = f"reports/{ts}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    if not quiet:
        print(f"Report written to {filepath}")
    return filepath


def build_report(now=None):
    """The retired-path daily report: per-file pending-line counts, outcome
    qs_retired. Kept as a pure function so tests can run it offline."""
    now = now or datetime.now(timezone.utc)
    report = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "outcome": "qs_retired",
        "note": ("QuickStatements path retired 2026-07-04 (Emma: no manual "
                 "batch ever) — direct_daily_edits.py is the only editor"),
        "batches": [],
    }
    for filepath in ATOMIC_FILES:
        lines = read_batch(filepath)
        report["batches"].append({
            "file": filepath,
            "lines_available": len(lines),
            "lines_submitted": 0,
            "success": False,
            "message": "QS retired — flows via the direct API drip",
        })
    return report


def main():
    report = build_report()
    write_report(report)
    pending = sum(b["lines_available"] for b in report["batches"])
    print(f"QS path retired — {pending} lines pending across "
          f"{len(ATOMIC_FILES)} files, all flowing via direct_daily_edits.py.")
    print("Exiting 1 so cleanup-loop's qs-failed wiring fires the direct path.")
    sys.exit(1)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()
