#!/usr/bin/env python3
"""
Organize Python files into subdirectories based on their purpose.
"""

import os
import re
import sys
import io
from pathlib import Path

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIBOT_DIR = r'C:\Users\Immanuelle\Documents\Github\q\wikibot'

# Define categories and their keywords/patterns
CATEGORIES = {
    'aelaki_lexeme': {
        'patterns': [
            r'aelaki\.miraheze\.org',
            r'lexeme',
            r'wbeditentity.*lexeme',
            r'aelaki',
        ],
        'filenames': [
            'add_aelaki',
            'add_dummy_senses',
            'add_s2_and_f2',
            'add_s3_and_f3',
            'add_p1_q10',
            'add_forms',
            'add_senses',
            'bulk_add_s2_and_f2',
            'bulk_create_sense',
            'cleanup_lexemes',
            'comprehensive_lexeme',
            'create_english_cat_lexeme',
            'create_lexeme',
            'import_l',
            'import_wikidata_lexeme',
            'import_cat_lexeme',
            'inspect_l',
            'investigate_lexeme',
            'lexeme_export',
            'lexeme_import',
            'overwrite_senses',
            'spam_sense',
            'test_all_lexeme',
            'test_all_possible_forms',
            'test_all_sense',
            'test_lexeme',
            'test_senses_array',
            'test_wikibase_items',
            'test_lexeme_properties',
        ]
    },
    'shinto_miraheze': {
        'patterns': [
            r"shinto\.miraheze\.org",
            r"WIKI_URL.*=.*['\"]shinto",
            r"shrine",
            r"shikinaisha",
        ],
        'filenames': [
            'generate_shikinaisha',
            'create_blank_shikinaisha',
            'create_shrine_pages',
            'finalize_ashitaka',
            'check_kashima',
            'resolve_wikidata_from_interwiki',
            'categorize_wikidata_links',
            'generate_quickstatements_wikidata_links',
        ]
    },
    'wikidata_editing': {
        'patterns': [
            r'wikidata',
            r'quickstatements',
            r'P\d+',  # Properties like P1, P11250
        ],
        'filenames': [
            'add_wikidata',
            'resolve_wikidata',
            'categorize_wikidata',
            'find_wikidata',
            'find_broken_wikidata',
            'find_duplicate_wikidata',
            'find_qid',
            'find_unclosed',
            'generate_quickstatements',
            'check_wikidata',
            'cleanup_wikidata',
            'consolidate_wikidata',
            'create_qid',
            'create_duplicates_report',
            'delete_correct_qid',
            'merge_duplicate_qid',
            'upload_wikidata',
            'upload_qid',
            'undo_wikidata',
            'extract_',
            'export_translated',
            'find_missing_p11250',
            'find_file_category',
            'add_interwikis_from_wikidata',
            'tag_missing_wikidata',
            'remove_missing_wikidata',
            'add_distinguish',
            'create_contradictions',
            'update_contradictions',
            'enhance_contradictions',
            'fix_contradictions',
            'split_erroneous_history',
            'interwiki_redirect_bot',
            'enwiki_',
        ]
    }
}

def get_file_contents(filepath):
    """Safely read file contents."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(2000)  # Read first 2000 chars to check patterns
    except:
        return ""

def categorize_file(filename, filepath):
    """Determine which category a file belongs to."""
    filename_lower = filename.lower()
    file_contents = get_file_contents(filepath)

    # Check aelaki first (most specific)
    aelaki_patterns = CATEGORIES['aelaki_lexeme']['patterns']
    aelaki_filenames = CATEGORIES['aelaki_lexeme']['filenames']

    for pattern in aelaki_patterns:
        if re.search(pattern, file_contents, re.IGNORECASE):
            return 'aelaki_lexeme'

    for fname_pattern in aelaki_filenames:
        if fname_pattern.lower() in filename_lower:
            return 'aelaki_lexeme'

    # Check shinto/shikinaisha
    shinto_patterns = CATEGORIES['shinto_miraheze']['patterns']
    shinto_filenames = CATEGORIES['shinto_miraheze']['filenames']

    for pattern in shinto_patterns:
        if re.search(pattern, file_contents, re.IGNORECASE):
            return 'shinto_miraheze'

    for fname_pattern in shinto_filenames:
        if fname_pattern.lower() in filename_lower:
            return 'shinto_miraheze'

    # Check wikidata editing
    wikidata_filenames = CATEGORIES['wikidata_editing']['filenames']

    for fname_pattern in wikidata_filenames:
        if fname_pattern.lower() in filename_lower:
            return 'wikidata_editing'

    # Default to utilities
    return 'utilities_and_testing'

def main():
    """Main organization function."""
    os.chdir(WIKIBOT_DIR)

    py_files = [f for f in os.listdir('.') if f.endswith('.py') and os.path.isfile(f)]

    categorized = {
        'aelaki_lexeme': [],
        'shinto_miraheze': [],
        'wikidata_editing': [],
        'utilities_and_testing': []
    }

    print(f"Found {len(py_files)} Python files to organize\n")

    # Categorize all files
    for filename in sorted(py_files):
        category = categorize_file(filename, filename)
        categorized[category].append(filename)
        print(f"{category:30} <- {filename}")

    # Move files to their directories
    print("\n" + "="*70)
    print("Moving files...")
    print("="*70 + "\n")

    for category, files in categorized.items():
        if files:
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

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for category, files in categorized.items():
        print(f"{category:35} {len(files):3} files")

if __name__ == '__main__':
    main()
