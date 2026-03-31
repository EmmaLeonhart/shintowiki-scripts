"""Generate an HTML run history page from QuickStatements report JSON files.

Reads all reports/*.json and produces _site/runs.html showing the outcome
of each workflow run (submitted, partial, failed, skipped, nothing_to_do, error).
"""

import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPORTS_DIR = Path("reports")
OUTPUT_PATH = Path("_site/runs.html")

OUTCOME_LABELS = {
    "submitted": ("Submitted", "#4caf50", "#e8f5e9"),
    "partial": ("Partial", "#ff9800", "#fff3e0"),
    "failed": ("Failed", "#e53935", "#ffebee"),
    "skipped": ("Skipped", "#9e9e9e", "#f5f5f5"),
    "nothing_to_do": ("Nothing to do", "#2196f3", "#e3f2fd"),
    "error": ("Error", "#e53935", "#ffebee"),
    "unknown": ("Unknown", "#9e9e9e", "#f5f5f5"),
}


def load_reports():
    """Load all report JSON files, sorted newest first."""
    reports = []
    if not REPORTS_DIR.exists():
        return reports
    for f in REPORTS_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                data["_filename"] = f.name
                reports.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: skipping {f.name}: {e}")
    reports.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return reports


def outcome_badge(outcome):
    """Return an HTML badge span for an outcome."""
    label, color, _ = OUTCOME_LABELS.get(outcome, OUTCOME_LABELS["unknown"])
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.85rem;font-weight:600">{label}</span>'


def batch_rows(batches):
    """Generate table rows for batch details."""
    if not batches:
        return '<tr><td colspan="4" style="color:#999">No batches</td></tr>'
    rows = []
    for b in batches:
        status = "OK" if b.get("success") else "FAIL"
        status_color = "#4caf50" if b.get("success") else "#e53935"
        rows.append(
            f'<tr>'
            f'<td><code>{b.get("file", "?")}</code></td>'
            f'<td>{b.get("lines_submitted", 0)}/{b.get("lines_available", 0)}</td>'
            f'<td style="color:{status_color};font-weight:600">{status}</td>'
            f'<td style="font-size:0.85rem">{b.get("message", "")}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def generate_html(reports):
    """Build the full HTML page."""
    # Summary counts
    counts = {}
    for r in reports:
        outcome = r.get("outcome", "unknown")
        counts[outcome] = counts.get(outcome, 0) + 1

    summary_parts = []
    for outcome, count in sorted(counts.items(), key=lambda x: -x[1]):
        label, color, bg = OUTCOME_LABELS.get(outcome, OUTCOME_LABELS["unknown"])
        summary_parts.append(
            f'<div style="background:{bg};border-left:4px solid {color};padding:0.5rem 1rem;'
            f'border-radius:4px;margin:0.25rem 0">'
            f'<strong style="color:{color}">{count}</strong> {label}</div>'
        )

    run_cards = []
    for r in reports:
        outcome = r.get("outcome", "unknown")
        _, _, bg = OUTCOME_LABELS.get(outcome, OUTCOME_LABELS["unknown"])
        error_line = ""
        if r.get("error"):
            error_line = f'<div style="color:#e53935;margin:0.5rem 0;font-size:0.9rem">Error: {r["error"]}</div>'

        run_cards.append(f'''
        <div style="background:{bg};border-radius:8px;padding:1rem 1.25rem;margin:0.75rem 0">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <strong>{r.get("timestamp", "?")}</strong>
            {outcome_badge(outcome)}
          </div>
          {error_line}
          <table style="width:100%;margin-top:0.5rem;border-collapse:collapse;font-size:0.9rem">
            <thead><tr style="text-align:left;border-bottom:1px solid #ddd">
              <th>File</th><th>Lines</th><th>Status</th><th>Message</th>
            </tr></thead>
            <tbody>{batch_rows(r.get("batches", []))}</tbody>
          </table>
        </div>''')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QuickStatements Run History</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #333; }}
    h1 {{ border-bottom: 2px solid #4caf50; padding-bottom: 0.5rem; }}
    h2 {{ margin-top: 2rem; color: #2e7d32; }}
    table {{ border-collapse: collapse; }}
    th, td {{ padding: 0.3rem 0.75rem; text-align: left; }}
    a {{ color: #0645ad; }}
    .timestamp {{ color: #888; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>QuickStatements Run History</h1>
  <p class="timestamp">Generated {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")} &middot; {len(reports)} runs
    &middot; <a href="index.html">&larr; Dashboard</a>
    &middot; <a href="https://github.com/immanuelle/shintowiki-scripts">GitHub</a></p>

  <h2>Summary</h2>
  {"".join(summary_parts) if summary_parts else "<p>No runs recorded yet.</p>"}

  <h2>Runs</h2>
  {"".join(run_cards) if run_cards else "<p>No runs recorded yet.</p>"}
</body>
</html>'''


def main():
    reports = load_reports()
    print(f"Loaded {len(reports)} reports")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html = generate_html(reports)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
