"""Submit atomic QuickStatements via the QuickStatements API.

Submits all atomic operation files (P459 qualifiers, P4656 references,
P958 qualifiers, Shikinai Hiteisha removals). Each file is tried
independently with retries, so one flaky failure doesn't block the rest.

Writes a run report to reports/ after each run.

Expects environment variables:
  QS_TOKEN     - API token from QuickStatements user page
  QS_USERNAME  - Wikidata username for QuickStatements submissions
"""

import io
import json
import os
import sys
import time
from datetime import datetime, timezone
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

QS_API = "https://quickstatements.toolforge.org/api.php"
MAX_RETRIES = 10
RETRY_DELAY = 20  # seconds between retries
# Cap total lines submitted per run. Paired with the once-per-day fire gate
# in cleanup-loop.yml. This is the ONLY thing that edits Wikidata — all
# Wikidata work is generated as QuickStatements lines into the atomic files
# and run through here (no bespoke direct-API editors).
MAX_LINES_TOTAL = 50

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
]


def read_batch(filepath):
    """Read all lines from a file, return as list of non-empty lines."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def submit_batch(lines, token, username, batch_name):
    """Submit a batch of QuickStatements v1 lines to the API.

    Returns (success: bool, message: str, raw_response: dict|None).
    """
    if not lines:
        return True, "No lines to submit", None

    data = "||".join(lines)

    try:
        r = requests.post(
            QS_API,
            data={
                "action": "import",
                "submit": "1",
                "format": "v1",
                "data": data,
                "username": username,
                "token": token,
                "batchname": batch_name,
                "compress": "1",
            },
            headers={"User-Agent": "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"},
            timeout=120,
        )
    except Exception as e:
        return False, f"Request failed: {e}", None

    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:500]}", None

    try:
        result = r.json()
    except Exception:
        return False, f"Non-JSON response: {r.text[:500]}", None

    if "batch_id" in result:
        return True, f"Batch created: #{result['batch_id']}", result
    return False, f"API error: {result}", result


def submit_with_retries(lines, token, username, batch_name):
    """Try submitting a batch up to MAX_RETRIES times."""
    for attempt in range(1, MAX_RETRIES + 1):
        success, message, raw = submit_batch(lines, token, username, batch_name)
        if success:
            return success, message, raw, attempt
        print(f"  Attempt {attempt}/{MAX_RETRIES} failed: {message}")
        if attempt < MAX_RETRIES:
            print(f"  Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
    return False, message, raw, MAX_RETRIES


def write_report(report):
    """Write run report to reports/ directory."""
    os.makedirs("reports", exist_ok=True)
    ts = report["timestamp"].replace(":", "-").replace(" ", "_")
    filepath = f"reports/{ts}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report written to {filepath}")
    return filepath


def main():
    now = datetime.now(timezone.utc)
    report = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "outcome": "unknown",
        "batches": [],
    }

    token = os.environ.get("QS_TOKEN", "")
    username = os.environ.get("QS_USERNAME", "")

    if not token or not username:
        missing = []
        if not token:
            missing.append("QS_TOKEN")
        if not username:
            missing.append("QS_USERNAME")
        report["outcome"] = "skipped"
        report["error"] = f"{', '.join(missing)} not set"
        print(f"SKIPPED: {report['error']}")
        write_report(report)
        return

    any_succeeded = False
    any_failed = False
    total_submitted = 0

    for filepath in ATOMIC_FILES:
        lines = read_batch(filepath)
        batch_entry = {
            "file": filepath,
            "lines_available": len(lines),
            "lines_submitted": 0,
            "success": None,
            "message": "",
            "attempts": 0,
            "api_response": None,
        }

        if not lines:
            batch_entry["success"] = True
            batch_entry["message"] = "Nothing to submit"
            print(f"{filepath}: nothing to submit")
            report["batches"].append(batch_entry)
            continue

        # Cap total lines across all files
        remaining_budget = MAX_LINES_TOTAL - total_submitted
        if remaining_budget <= 0:
            batch_entry["success"] = True
            batch_entry["message"] = f"Skipped (daily cap of {MAX_LINES_TOTAL} reached)"
            print(f"{filepath}: skipped ({MAX_LINES_TOTAL} line cap reached)")
            report["batches"].append(batch_entry)
            continue
        if len(lines) > remaining_budget:
            lines = lines[:remaining_budget]

        batch_name = f"auto: {os.path.splitext(filepath)[0]} ({len(lines)} lines)"
        print(f"{filepath}: submitting {len(lines)} lines as '{batch_name}'...")

        success, message, raw, attempts = submit_with_retries(lines, token, username, batch_name)
        batch_entry["lines_submitted"] = len(lines)
        batch_entry["success"] = success
        batch_entry["message"] = message
        batch_entry["attempts"] = attempts
        batch_entry["api_response"] = raw
        report["batches"].append(batch_entry)

        if success:
            print(f"  OK: {message}" + (f" (attempt {attempts})" if attempts > 1 else ""))
            any_succeeded = True
            total_submitted += len(lines)
        else:
            print(f"  FAILED after {attempts} attempts: {message}")
            any_failed = True
            # Continue to next file instead of giving up

        # Gap between files
        time.sleep(5)

    if any_succeeded and not any_failed:
        report["outcome"] = "submitted"
    elif any_succeeded and any_failed:
        report["outcome"] = "partial"
    elif not any_succeeded and not any_failed:
        report["outcome"] = "nothing_to_do"
    else:
        report["outcome"] = "failed"

    report_path = write_report(report)
    print(f"Done. Outcome: {report['outcome']}")

    # Exit non-zero when ALL batches failed so the workflow can trigger the direct API fallback
    if report["outcome"] == "failed":
        print("WARNING: All batches failed — direct API fallback should run")
        sys.exit(1)


if __name__ == "__main__":
    main()
