#!/usr/bin/env python
"""
Check if disputed category names already exist on Wikimedia Commons
"""

import sys
import io
import csv
import mwclient

# Fix Windows Unicode encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── CONFIG ─────────────────────────────────────────────────────────
COMMONS_URL = "commons.wikimedia.org"
COMMONS_PATH = "/w/"
CSV_FILE = r"C:\Users\Immanuelle\Downloads\query (2).csv"

# ── MAIN ───────────────────────────────────────────────────────────

def main():
    print("="*70)
    print("CHECKING DISPUTED CATEGORY NAMES ON WIKIMEDIA COMMONS")
    print("="*70)
    print()

    # Load CSV and get unique disputed labels
    print("Loading CSV data...")
    disputed_labels = set()
    disputed_qids = {}

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row['disputedLabel']
            qid = row['disputed'].split('/')[-1]
            disputed_labels.add(label)
            disputed_qids[label] = qid

    print(f"Found {len(disputed_labels)} unique disputed shrine names\n")

    # Connect to Commons (read-only, no login needed)
    print(f"Connecting to {COMMONS_URL}...")
    site = mwclient.Site(COMMONS_URL, path=COMMONS_PATH)
    print("Connected successfully\n")

    # Check each category
    existing = []
    not_existing = []

    print("Checking categories...")
    print("-" * 70)

    for idx, label in enumerate(sorted(disputed_labels), 1):
        page_title = f"Category:{label}"
        page = site.pages[page_title]
        qid = disputed_qids[label]

        if page.exists:
            text = page.text()
            print(f"{idx}. ✗ EXISTS: {label} ({qid})")
            print(f"   Content preview (first 200 chars):")
            print(f"   {text[:200].replace(chr(10), ' ')}")
            print()
            existing.append((label, qid, text))
        else:
            print(f"{idx}. ✓ OK: {label} ({qid}) - does not exist")
            not_existing.append((label, qid))

    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Categories that DO NOT exist (safe to create): {len(not_existing)}")
    print(f"Categories that ALREADY EXIST (collision!): {len(existing)}")
    print()

    if existing:
        print("⚠ EXISTING CATEGORIES (POTENTIAL COLLISION):")
        print("-" * 70)
        for label, qid, text in existing:
            print(f"  • {label} ({qid})")
        print()
        print("Review these before running the bot!")

    if not_existing:
        print(f"\n✓ {len(not_existing)} categories are safe to create")

if __name__ == "__main__":
    main()
