"""Submit the daily budget of atomic QuickStatements via the QuickStatements API.

Only submits Phase 1 (P459 qualifiers) and Phase 1.5 (P1027→P459 replacement)
lines, which are atomic operations safe for unattended execution.

Phase 3 migration lines are non-atomic (remove old + add new) and require
manual review, so they are NOT submitted here.

Writes a run report to reports/ after each run.

Expects environment variables:
  QUICKSTATEMENTS_API_KEY  - API token from QuickStatements user page
  QUICKSTATEMENTS_USERNAME - Wikidata username associated with the token
"""

import io
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

QS_API = "https://quickstatements.toolforge.org/api.php"
MAX_LINES_PER_BATCH = 200

ATOMIC_FILES = [
    "modern_shrine_ranking_qualifiers.txt",   # Phase 1: add P459 to existing P13723
    # "replace_p1027_with_p459.txt",          # Phase 1.5: non-atomic (remove + re-add), manual only
    "p958_qualifiers.txt",                    # Add P958 section qualifiers to P13677
]


def read_batch(filepath, max_lines=MAX_LINES_PER_BATCH):
    """Read up to max_lines from a file, return as list of non-empty lines."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
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
            headers={"User-Agent": "ModernQuickstatements/1.0 (daily cron batch)"},
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
        "delay_seconds": 0,
    }

    token = os.environ.get("QUICKSTATEMENTS_API_KEY", "")
    username = os.environ.get("QUICKSTATEMENTS_USERNAME", "")

    if not token or not username:
        report["outcome"] = "error"
        report["error"] = "QUICKSTATEMENTS_API_KEY and QUICKSTATEMENTS_USERNAME must be set"
        print(f"ERROR: {report['error']}")
        write_report(report)
        sys.exit(1)

    # Random delay 1-3600 seconds to avoid predictable timing
    delay = random.randint(1, 3600)
    report["delay_seconds"] = delay
    print(f"Waiting {delay}s before submitting ({delay // 60}m {delay % 60}s)...")
    time.sleep(delay)

    all_ok = True
    any_submitted = False

    for filepath in ATOMIC_FILES:
        lines = read_batch(filepath)
        batch_entry = {
            "file": filepath,
            "lines_available": len(lines),
            "lines_submitted": 0,
            "success": None,
            "message": "",
            "api_response": None,
        }

        if not lines:
            batch_entry["success"] = True
            batch_entry["message"] = "Nothing to submit"
            print(f"{filepath}: nothing to submit")
            report["batches"].append(batch_entry)
            continue

        batch_name = f"auto: {os.path.splitext(filepath)[0]} ({len(lines)} lines)"
        print(f"{filepath}: submitting {len(lines)} lines as '{batch_name}'...")

        success, message, raw = submit_batch(lines, token, username, batch_name)
        batch_entry["lines_submitted"] = len(lines)
        batch_entry["success"] = success
        batch_entry["message"] = message
        batch_entry["api_response"] = raw
        report["batches"].append(batch_entry)

        print(f"  → {message}")

        if success:
            any_submitted = True
        else:
            all_ok = False
            print("Submission failed, giving up on remaining batches.")
            break

        # Small gap between batches
        time.sleep(5)

    if all_ok and any_submitted:
        report["outcome"] = "submitted"
    elif all_ok and not any_submitted:
        report["outcome"] = "nothing_to_do"
    else:
        report["outcome"] = "failed"

    report_path = write_report(report)
    print(f"Done. Outcome: {report['outcome']}")

    # Exit non-zero on failure so the workflow step fails visibly
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
