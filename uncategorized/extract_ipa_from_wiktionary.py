#!/usr/bin/env python3
"""
Extract IPA Pronunciation from Wiktionary
===========================================
Robust tool to extract English IPA pronunciations from Wiktionary pages
"""

import requests
import re
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_ipa_from_wiktionary(word):
    """
    Extract English IPA pronunciation from Wiktionary page
    Returns IPA string without slashes, or None if not found
    """
    url = f"https://en.wiktionary.org/wiki/{word}"

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    try:
        r = session.get(url, timeout=5)
        if r.status_code != 200:
            print(f"✗ Could not fetch Wiktionary page for '{word}' (HTTP {r.status_code})")
            return None

        html_text = r.text

        # Method 1: Try to find IPA in {{IPA|en|...}} template
        ipa_pattern = r'\{\{IPA\|en\|([^}]+)\}\}'
        match = re.search(ipa_pattern, html_text)
        if match:
            ipa = match.group(1).strip()
            # Remove HTML tags and slashes
            ipa = re.sub(r'<[^>]+>', '', ipa)
            ipa = ipa.strip('/').strip()
            if ipa:
                print(f"✓ Found IPA via {{{{IPA|en|...}}}} template: {ipa}")
                return ipa

        # Method 2: Look for /.../ IPA patterns with stress markers (more likely to be correct)
        # These have higher confidence since they contain IPA-specific stress marks
        stressed_ipa_pattern = r'/([ˈˌɪɛæɔʊɑɒəɜːɚɝaeiouɡkpbtdnmɫwjŋθðʃʒtʃdʒhɹɲlɕ\-]+)/'
        ipa_matches = re.findall(stressed_ipa_pattern, html_text)

        for ipa in ipa_matches:
            ipa_cleaned = ipa.strip()
            # Prioritize those with stress marks
            if ('ˈ' in ipa_cleaned or 'ˌ' in ipa_cleaned) and len(ipa_cleaned) > 2:
                print(f"✓ Found IPA with stress mark: {ipa_cleaned}")
                return ipa_cleaned

        # Method 3: Return first IPA match found (even without stress marks)
        if ipa_matches:
            for ipa in ipa_matches:
                ipa_cleaned = ipa.strip()
                if len(ipa_cleaned) > 2:
                    print(f"✓ Found IPA: {ipa_cleaned}")
                    return ipa_cleaned

        print(f"✗ No IPA pronunciation found for '{word}'")
        return None

    except requests.exceptions.Timeout:
        print(f"✗ Request timeout for '{word}'")
        return None
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection error for '{word}'")
        return None
    except Exception as e:
        print(f"✗ Error fetching IPA for '{word}': {e}")
        return None

# Main
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_ipa_from_wiktionary.py <word>")
        print("Example: python extract_ipa_from_wiktionary.py explore")
        sys.exit(1)

    word = sys.argv[1]
    ipa = extract_ipa_from_wiktionary(word)
    if ipa:
        print(f"\nResult: {ipa}")
    else:
        print(f"\nNo IPA found")
