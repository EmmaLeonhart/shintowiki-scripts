#!/usr/bin/env python3
"""
Clean up interwiki duplicates in [[Category:Merged Shikinaisha autogenerations]]

Rules:
1. If same language code has identical target pages (100% match) - remove duplicates, keep one
2. If same language code has different target pages (conflict) - add [[Category:Pages with contradicting interwikis]]
3. Report progress and issues
"""

import re
import sys
import time
import mwclient

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to wiki
site = mwclient.Site('shinto.miraheze.org', force_login=False)

INTERWIKI_RE = re.compile(r'\[\[([a-z]{2,3}):([^\]]+)\]\]')
CONFLICT_CATEGORY = '[[Category:Pages with contradicting interwikis]]'

def extract_all_interwikis(text):
    """Extract all interwiki links from text.
    Returns: list of (lang_code, page_title) tuples
    """
    matches = INTERWIKI_RE.findall(text)
    return [(lang.lower(), title) for lang, title in matches]

def find_interwiki_issues(interwikis):
    """Analyze interwikis for duplicates and conflicts.
    Returns: (has_duplicates, has_conflicts, clean_interwikis)
    - has_duplicates: list of (lang, titles) with identical duplicates
    - has_conflicts: list of (lang, titles) with conflicting targets
    - clean_interwikis: list of deduplicated (lang, page_title) tuples to keep
    """
    # Group by language
    lang_groups = {}
    for lang, title in interwikis:
        if lang not in lang_groups:
            lang_groups[lang] = []
        lang_groups[lang].append(title)

    has_duplicates = []
    has_conflicts = []
    clean_interwikis = []

    for lang, titles in lang_groups.items():
        # Remove duplicates within this language
        unique_titles = list(set(titles))

        if len(unique_titles) == 1:
            # No conflict - but might have duplicates to clean up
            if len(titles) > 1:
                has_duplicates.append((lang, titles))
            clean_interwikis.append((lang, unique_titles[0]))
        else:
            # Conflicting interwikis for same language
            has_conflicts.append((lang, unique_titles))

    return has_duplicates, has_conflicts, clean_interwikis

def remove_duplicate_interwikis(text, duplicates_to_remove):
    """Remove only the duplicate interwiki links, preserving conflicting ones.

    duplicates_to_remove: list of (lang, title) to remove (keeping first occurrence)
    """
    lines = text.split('\n')
    result_lines = []
    removed_count = {}  # Track how many of each (lang, title) we've seen

    for line in lines:
        # Check if this line is an interwiki link
        match = INTERWIKI_RE.match(line.strip())
        if match:
            lang, title = match.group(1).lower(), match.group(2)
            key = (lang, title)

            # Check if this is a duplicate we should remove
            if key in duplicates_to_remove:
                if key not in removed_count:
                    # Keep the first occurrence
                    removed_count[key] = 1
                    result_lines.append(line)
                else:
                    # Skip duplicate occurrences
                    removed_count[key] += 1
                    continue
            else:
                # Keep all non-duplicate lines (including conflicting ones)
                result_lines.append(line)
        else:
            # Not an interwiki line, keep it
            result_lines.append(line)

    return '\n'.join(result_lines)

def has_category(text, category_name):
    """Check if page has a specific category."""
    return f'[[Category:{category_name}]]' in text

def add_category(text, category_name):
    """Add a category to the page if not already present."""
    category_link = f'[[Category:{category_name}]]'
    if not has_category(text, category_name):
        text = text.rstrip() + '\n' + category_link
    return text

def process_page(page_title, page_text):
    """Process a single page for interwiki issues.
    Returns: (was_modified, has_conflicts, summary, new_text)
    """
    interwikis = extract_all_interwikis(page_text)

    if not interwikis:
        return False, False, "No interwikis found", None

    has_duplicates, has_conflicts, clean_interwikis = find_interwiki_issues(interwikis)

    summary_parts = []
    modified = False

    # Handle duplicates - remove ONLY exact duplicates, preserve conflicts
    if has_duplicates:
        # Build list of (lang, title) pairs to remove (keeping first of each)
        duplicates_to_remove = [(lang, title) for lang, titles in has_duplicates for title in titles]
        summary_parts.append(f"Removed {sum(len(titles) - 1 for _, titles in has_duplicates)} duplicate interwiki link(s)")
        page_text = remove_duplicate_interwikis(page_text, duplicates_to_remove)
        modified = True

    # Handle conflicts - add category but DON'T remove the conflicting interwikis
    if has_conflicts:
        summary_parts.append(f"Found {len(has_conflicts)} conflicting interwiki(s)")
        page_text = add_category(page_text, 'Pages with contradicting interwikis')
        modified = True

    summary = '; '.join(summary_parts) if summary_parts else "No issues"

    return modified, bool(has_conflicts), summary, page_text if modified else None

def main():
    print("Cleaning up interwiki duplicates in [[Category:Merged Shikinaisha autogenerations]]")
    print("=" * 70)

    # Get all pages in category
    category = site.pages['Category:Merged Shikinaisha autogenerations']
    pages = list(category.members())

    print(f"Found {len(pages)} pages in category\n")

    stats = {
        'total': len(pages),
        'processed': 0,
        'modified': 0,
        'with_conflicts': 0,
        'errors': 0,
        'no_interwikis': 0
    }

    for i, page in enumerate(pages, 1):
        page_title = page.name

        try:
            page_text = page.text()
        except Exception as e:
            print(f"{i:3d}. {page_title:50s} [ERROR reading: {str(e)[:40]}]")
            stats['errors'] += 1
            continue

        interwikis = extract_all_interwikis(page_text)

        if not interwikis:
            stats['no_interwikis'] += 1
            continue

        was_modified, has_conflicts, summary, new_text = process_page(page_title, page_text)

        if was_modified:
            stats['modified'] += 1
            if has_conflicts:
                stats['with_conflicts'] += 1
                print(f"{i:3d}. {page_title:50s} [CONFLICT] {summary}")
            else:
                print(f"{i:3d}. {page_title:50s} [CLEANED] {summary}")

            # Save the page
            try:
                page.edit(new_text, summary=f"v24 interwiki cleanup: {summary} 🤖 Generated with Claude Code\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
                time.sleep(3)  # Rate limit - increased to avoid hitting rate limit
            except Exception as e:
                print(f"     ! ERROR saving {page_title}: {e}")
                stats['errors'] += 1
        else:
            if i % 50 == 0:
                print(f"{i:3d}. {page_title:50s} ✓ (no issues)")
            stats['processed'] += 1

        # Rate limiting
        time.sleep(0.5)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total pages:              {stats['total']}")
    print(f"Pages with no interwikis: {stats['no_interwikis']}")
    print(f"Pages modified:           {stats['modified']}")
    print(f"Pages with conflicts:     {stats['with_conflicts']}")
    print(f"Errors:                   {stats['errors']}")
    print(f"Pages already clean:      {stats['processed']}")

if __name__ == '__main__':
    main()
