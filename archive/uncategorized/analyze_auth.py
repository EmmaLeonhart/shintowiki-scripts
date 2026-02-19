#!/usr/bin/env python3
"""
Analyze Python files by their authentication URLs to determine target wiki.
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

        # Look for various API URL patterns
        patterns = [
            r"API_URL\s*=\s*['\"]([^'\"]+)['\"]",
            r"API[_\s]*=\s*['\"]([^'\"]+)['\"]",
            r"api_url\s*=\s*['\"]([^'\"]+)['\"]",
            r"api[_\s]*=\s*['\"]([^'\"]+)['\"]",
            r"WIKI_URL\s*=\s*['\"]([^'\"]+)['\"]",
            r"wiki_url\s*=\s*['\"]([^'\"]+)['\"]",
            r"wiki[_\s]*url\s*=\s*['\"]([^'\"]+)['\"]",
            r"requests\.(?:get|post)\(['\"]([^'\"]+)['\"]",
            r"session\.(?:get|post)\(['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                url = match.group(1)
                return url
    except:
        pass
    return None

def categorize_by_auth(filename, filepath):
    """Categorize file based on authentication target."""
    url = get_api_url(filepath)

    if url:
        if 'aelaki' in url.lower():
            return 'aelaki_lexeme', url
        elif 'shinto' in url.lower():
            return 'shinto_miraheze', url
        elif 'evolutionism' in url.lower():
            return 'evolutionism_miraheze', url
        else:
            return 'unknown', url

    return None, None

def main():
    os.chdir(WIKIBOT_DIR)
    py_files = [f for f in os.listdir('.') if f.endswith('.py') and os.path.isfile(f)]

    categorized = {
        'aelaki_lexeme': [],
        'shinto_miraheze': [],
        'evolutionism_miraheze': [],
        'unknown': [],
        'no_auth': []
    }

    print(f"Analyzing {len(py_files)} Python files...\n")
    print(f"{'Category':<25} {'File':<50} {'URL':<50}")
    print("=" * 130)

    for filename in sorted(py_files):
        category, url = categorize_by_auth(filename, filename)

        if category:
            categorized[category].append((filename, url))
            print(f"{category:<25} {filename:<50} {url:<50}")
        else:
            categorized['no_auth'].append(filename)
            print(f"{'no_auth':<25} {filename:<50}")

    print("\n" + "=" * 130)
    print("SUMMARY")
    print("=" * 130)
    for category, items in categorized.items():
        count = len(items)
        print(f"{category:<25} {count:3} files")

if __name__ == '__main__':
    main()
