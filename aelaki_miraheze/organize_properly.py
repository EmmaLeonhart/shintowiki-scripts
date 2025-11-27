#!/usr/bin/env python3
"""
Organize Python files into subdirectories based on authentication URLs.
"""

import os
import re
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIBOT_DIR = r'C:\Users\Immanuelle\Documents\Github\q\wikibot'

def get_api_url(filepath):
    """Extract API URL from file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(3000)

        patterns = [
            r"API_URL\s*=\s*['\"]([^'\"]+)['\"]",
            r"API[_\s]*=\s*['\"]([^'\"]+)['\"]",
            r"api_url\s*=\s*['\"]([^'\"]+)['\"]",
            r"api[_\s]*=\s*['\"]([^'\"]+)['\"]",
            r"WIKI_URL\s*=\s*['\"]([^'\"]+)['\"]",
            r"wiki_url\s*=\s*['\"]([^'\"]+)['\"]",
            r"wiki[_\s]*url\s*=\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
    except:
        pass
    return None

def categorize_by_auth(filename, filepath):
    """Categorize file based on authentication target."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Check for any mention of these wikis (primary check)
        if 'aelaki.miraheze.org' in content.lower():
            return 'aelaki_miraheze'
        elif 'evolutionism.miraheze.org' in content.lower():
            return 'evolutionism_miraheze'
        elif 'shinto.miraheze.org' in content.lower():
            return 'shinto_miraheze'
    except:
        pass

    return 'uncategorized'

def main():
    os.chdir(WIKIBOT_DIR)

    # Create directories first
    for dir_name in ['aelaki_miraheze', 'shinto_miraheze', 'evolutionism_miraheze', 'uncategorized']:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    py_files = [f for f in os.listdir('.') if f.endswith('.py') and os.path.isfile(f)]

    categorized = {
        'aelaki_miraheze': [],
        'shinto_miraheze': [],
        'evolutionism_miraheze': [],
        'uncategorized': []
    }

    print(f"Organizing {len(py_files)} Python files...\n")

    for filename in sorted(py_files):
        category = categorize_by_auth(filename, filename)
        categorized[category].append(filename)

    # Move files to their directories
    print("Moving files to directories:\n")

    for category, files in categorized.items():
        if files and category != 'uncategorized':
            print(f"\n{category}/ ({len(files)} files)")
            print("-" * 70)

            for filename in files:
                src = filename
                dst = os.path.join(category, filename)
                try:
                    os.rename(src, dst)
                    print(f"  [OK] {filename}")
                except Exception as e:
                    print(f"  [ERROR] {filename} - {e}")

    # Show uncategorized
    if categorized['uncategorized']:
        print(f"\nuncategorized/ ({len(categorized['uncategorized'])} files)")
        print("-" * 70)
        for filename in categorized['uncategorized'][:10]:
            print(f"  {filename}")
        if len(categorized['uncategorized']) > 10:
            print(f"  ... and {len(categorized['uncategorized']) - 10} more")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for category, items in categorized.items():
        print(f"{category:<30} {len(items):3} files")

if __name__ == '__main__':
    main()
