#!/usr/bin/env python
"""
Generate QuickStatements for disputed Shikinaisha P373 (Commons category)
=========================================================================

Reads the CSV and generates QuickStatements to add P373 to disputed shrines
"""

import sys
import io
import csv

# Fix Windows Unicode encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CSV_FILE = r"C:\Users\Immanuelle\Downloads\query (2).csv"
OUTPUT_FILE = "disputed_shrines_p373_quickstatements.txt"

def extract_qid(url):
    """Extract QID from Wikidata URL"""
    return url.split('/')[-1]

def main():
    print("="*70)
    print("GENERATE QUICKSTATEMENTS - DISPUTED SHRINES P373")
    print("="*70)
    print()

    # Load CSV and get unique disputed shrines
    print("Loading CSV data...")
    disputed_shrines = {}

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = extract_qid(row['disputed'])
            label = row['disputedLabel']
            disputed_shrines[qid] = label

    print(f"Found {len(disputed_shrines)} unique disputed shrines\n")

    # Generate QuickStatements
    quickstatements = []
    for qid, label in sorted(disputed_shrines.items()):
        # Format: QID|P373|"Category Name"
        qs_line = f'{qid}|P373|"{label}"'
        quickstatements.append(qs_line)

    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for line in quickstatements:
            f.write(line + '\n')

    print(f"Generated {len(quickstatements)} QuickStatements")
    print(f"Saved to: {OUTPUT_FILE}\n")

    # Display first 10 for preview
    print("Preview (first 10):")
    print("-" * 70)
    for line in quickstatements[:10]:
        print(line)
    if len(quickstatements) > 10:
        print(f"... and {len(quickstatements) - 10} more")
    print()

    print("✓ Done! Use these QuickStatements at:")
    print("  https://quickstatements.toolforge.org/")

if __name__ == "__main__":
    main()
