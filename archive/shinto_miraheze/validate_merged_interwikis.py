#!/usr/bin/env python3
"""
Validate all interwiki links in [[Category:Merged Shikinaisha autogenerations]]
against the linked Wikidata items.

Reports:
- Multiple interwikis for same language (duplicates, conflicts)
- Interwikis that don't match Wikidata sitelinks
- Wikidata items with mismatched/wrong QIDs
"""

import re
import sys
import time
import requests
import mwclient

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to wiki
site = mwclient.Site('shinto.miraheze.org')

WIKIDATA_QID_RE = re.compile(r'{{wikidata link\|([Qq](\d+))}}', re.IGNORECASE)
INTERWIKI_RE = re.compile(r'\[\[([a-z]{2,3}):([^\]]+)\]\]')

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    match = WIKIDATA_QID_RE.search(page_text)
    if match:
        return match.group(1).upper()
    return None

def extract_all_interwikis(page_text):
    """Extract ALL interwiki links from page text (including duplicates).
    Returns: list of (lang_code, page_title) tuples
    """
    matches = INTERWIKI_RE.findall(page_text)
    return [(lang.lower(), title) for lang, title in matches]

def get_wikidata_sitelinks(qid):
    """Query Wikidata for all sitelinks for this QID.
    Returns: dict of {lang_code: page_title}
    """
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        entity = data.get('entities', {}).get(qid, {})
        sitelinks = entity.get('sitelinks', {})

        result = {}
        for site_key, site_info in sitelinks.items():
            # Convert site key to interwiki code (e.g., "dewiki" -> "de")
            if site_key.endswith('wiki'):
                lang_code = site_key[:-4]
                page_title = site_info.get('title', '')
                if page_title:
                    result[lang_code] = page_title

        return result
    except Exception as e:
        print(f"     ERROR querying Wikidata {qid}: {e}")
        return None

def validate_page(page_title, page_text):
    """Validate a single page's interwikis against its Wikidata item.
    Returns: dict with validation results
    """
    results = {
        'page': page_title,
        'qid': None,
        'interwikis': [],
        'wikidata_sitelinks': {},
        'duplicates': [],
        'mismatches': [],
        'missing_from_wikidata': []
    }

    # Extract QID
    qid = extract_wikidata_qid(page_text)
    if not qid:
        results['error'] = 'NO_WIKIDATA_LINK'
        return results

    results['qid'] = qid

    # Extract all interwikis
    interwikis = extract_all_interwikis(page_text)
    results['interwikis'] = interwikis

    # Get Wikidata sitelinks
    sitelinks = get_wikidata_sitelinks(qid)
    if sitelinks is None:
        results['error'] = f'WIKIDATA_QUERY_FAILED'
        return results

    results['wikidata_sitelinks'] = sitelinks

    # Find duplicates (multiple interwikis for same language)
    lang_groups = {}
    for lang, title in interwikis:
        if lang not in lang_groups:
            lang_groups[lang] = []
        lang_groups[lang].append(title)

    for lang, titles in lang_groups.items():
        if len(titles) > 1:
            results['duplicates'].append({
                'lang': lang,
                'titles': titles
            })

    # Validate each interwiki against Wikidata
    for lang, title in interwikis:
        if lang not in sitelinks:
            results['missing_from_wikidata'].append({
                'lang': lang,
                'wiki_title': title,
                'wikidata_title': None
            })
        elif sitelinks[lang] != title:
            results['mismatches'].append({
                'lang': lang,
                'wiki_title': title,
                'wikidata_title': sitelinks[lang]
            })

    return results

def main():
    print("Validating interwikis in [[Category:Merged Shikinaisha autogenerations]]")
    print("=" * 70)

    # Get all pages in category
    category = site.pages['Category:Merged Shikinaisha autogenerations']
    pages = list(category.members())

    print(f"Found {len(pages)} pages in category\n")

    # Track statistics
    stats = {
        'total': len(pages),
        'no_wikidata': 0,
        'wikidata_error': 0,
        'has_duplicates': 0,
        'has_mismatches': 0,
        'has_missing': 0,
        'clean': 0
    }

    issues = []

    for i, page in enumerate(pages, 1):
        page_title = page.name

        try:
            page_text = page.text()
        except Exception as e:
            print(f"{i:4d}. {page_title:50s} [ERROR reading page: {e}]")
            continue

        results = validate_page(page_title, page_text)

        # Categorize results
        if 'error' in results:
            if results['error'] == 'NO_WIKIDATA_LINK':
                stats['no_wikidata'] += 1
                print(f"{i:4d}. {page_title:50s} [NO WIKIDATA LINK]")
            else:
                stats['wikidata_error'] += 1
                print(f"{i:4d}. {page_title:50s} [WIKIDATA ERROR: {results['error']}]")
            continue

        # Check for issues
        has_issues = False
        issue_codes = []

        if results['duplicates']:
            stats['has_duplicates'] += 1
            has_issues = True
            issue_codes.append('DUP')

        if results['mismatches']:
            stats['has_mismatches'] += 1
            has_issues = True
            issue_codes.append('MISMATCH')

        if results['missing_from_wikidata']:
            stats['has_missing'] += 1
            has_issues = True
            issue_codes.append('MISSING')

        if has_issues:
            issue_str = ','.join(issue_codes)
            print(f"{i:4d}. {page_title:50s} [{issue_str}] {results['qid']}")
            issues.append(results)
        else:
            stats['clean'] += 1
            if i % 50 == 0:
                print(f"{i:4d}. {page_title:50s} ✓")

        # Rate limiting
        time.sleep(0.3)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total pages:              {stats['total']}")
    print(f"No Wikidata link:         {stats['no_wikidata']}")
    print(f"Wikidata query errors:    {stats['wikidata_error']}")
    print(f"Pages with duplicates:    {stats['has_duplicates']}")
    print(f"Pages with mismatches:    {stats['has_mismatches']}")
    print(f"Pages missing from WD:    {stats['has_missing']}")
    print(f"Clean pages:              {stats['clean']}")

    # Print detailed issues
    print("\n" + "=" * 70)
    print("DETAILED ISSUES")
    print("=" * 70)

    for results in issues:
        page = results['page']
        qid = results['qid']

        print(f"\n{page} ({qid})")
        print("-" * 70)

        if results['duplicates']:
            print("  DUPLICATES (multiple interwikis for same language):")
            for dup in results['duplicates']:
                print(f"    {dup['lang']}:")
                for title in dup['titles']:
                    print(f"      - {title}")

        if results['mismatches']:
            print("  MISMATCHES (page has different title than Wikidata):")
            for mismatch in results['mismatches']:
                print(f"    {mismatch['lang']}:")
                print(f"      Page:     {mismatch['wiki_title']}")
                print(f"      Wikidata: {mismatch['wikidata_title']}")

        if results['missing_from_wikidata']:
            print("  MISSING FROM WIKIDATA (page has interwiki Wikidata doesn't have):")
            for missing in results['missing_from_wikidata']:
                print(f"    {missing['lang']}: {missing['wiki_title']}")

if __name__ == '__main__':
    main()
