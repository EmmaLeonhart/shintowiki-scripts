#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wiktionary bot to add Wikidata lexeme templates to Japanese entries.

For each Japanese part of speech section, queries Wikidata for a matching lexeme
and adds {{wikidata lexeme|LXXXX}} template.
"""

import mwclient
import requests
import re
import time
import io
import sys

# Handle Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiktionary credentials
BOT_USERNAME = 'Immanuelle@ImmanuelleWiktionaryTest'
BOT_PASSWORD = 'qi6v2vi4s0p3bvr6d1lium2n2d7l4930'

# Wikidata SPARQL endpoint
SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'

# User agent for API requests
USER_AGENT = 'WiktionaryLexemeBot/1.0 (User:Immanuelle) Python/mwclient'

# Map Wiktionary part of speech headers to Wikidata lexical category QIDs
POS_MAP = {
    'Noun': 'Q1084',
    'Verb': 'Q24905',
    'Adjective': 'Q34698',
    'Adverb': 'Q380057',
    'Pronoun': 'Q36224',
    'Preposition': 'Q4833830',
    'Conjunction': 'Q36484',
    'Interjection': 'Q83034',
    'Proper noun': 'Q147276',
    'Article': 'Q103184',
    'Numeral': 'Q63116',
    'Particle': 'Q184943',
    'Determiner': 'Q576271',
}


def query_wikidata_lexeme(lemma, language_qid='Q5287', pos_qid=None):
    """
    Query Wikidata for a lexeme with matching lemma, language, and part of speech.

    Args:
        lemma: The lemma text to search for
        language_qid: Wikidata QID for the language (default Q5287 = Japanese)
        pos_qid: Wikidata QID for the lexical category/part of speech

    Returns:
        Tuple of (lexeme_id, count) where:
        - lexeme_id: The lexeme ID (e.g., 'L8005') if exactly one found, None otherwise
        - count: Number of matching lexemes found (0, 1, or 2+)
    """
    if not pos_qid:
        return None, 0

    # SPARQL query to find ALL matching lexemes (no LIMIT)
    # Search for kana reading using @ja-hira language tag
    query = f"""
    SELECT ?lexeme WHERE {{
      ?lexeme dct:language wd:{language_qid} ;
              wikibase:lemma "{lemma}"@ja-hira ;
              wikibase:lexicalCategory wd:{pos_qid} .
    }}
    """

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/sparql-results+json'
    }

    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={'query': query, 'format': 'json'},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        bindings = data.get('results', {}).get('bindings', [])

        count = len(bindings)

        # Only return lexeme ID if there's exactly one match
        if count == 1:
            lexeme_uri = bindings[0]['lexeme']['value']
            # Extract lexeme ID from URI (e.g., http://www.wikidata.org/entity/L8005 -> L8005)
            lexeme_id = lexeme_uri.split('/')[-1]
            return lexeme_id, count
        else:
            # Either no matches or duplicates found
            return None, count

    except Exception as e:
        print(f"Error querying Wikidata: {e}")

    return None, 0


def parse_japanese_section(wikitext):
    """
    Parse the wikitext to find Japanese section and its part of speech subsections.

    Returns:
        List of tuples: (pos_header, start_pos, end_pos)
    """
    # Find the Japanese L2 section
    japanese_pattern = r'==\s*Japanese\s*=='
    japanese_match = re.search(japanese_pattern, wikitext)

    if not japanese_match:
        return []

    japanese_start = japanese_match.end()

    # Find the next L2 section (or end of text)
    next_l2_pattern = r'\n==\s*[^=]+\s*=='
    next_l2_match = re.search(next_l2_pattern, wikitext[japanese_start:])

    if next_l2_match:
        japanese_end = japanese_start + next_l2_match.start()
    else:
        japanese_end = len(wikitext)

    japanese_text = wikitext[japanese_start:japanese_end]

    # Find all L3 part of speech headers in Japanese section
    pos_sections = []
    pos_pattern = r'===\s*(' + '|'.join(re.escape(pos) for pos in POS_MAP.keys()) + r')\s*==='

    for match in re.finditer(pos_pattern, japanese_text):
        pos_header = match.group(1)
        pos_start = japanese_start + match.start()
        pos_end_match = re.search(r'\n===', japanese_text[match.end():])

        if pos_end_match:
            pos_end = japanese_start + match.end() + pos_end_match.start()
        else:
            pos_end = japanese_end

        pos_sections.append((pos_header, pos_start, pos_end))

    return pos_sections


def check_lexeme_template_exists(wikitext, start_pos, end_pos):
    """
    Check if {{wikidata lexeme|...}} template already exists in the section.
    """
    section_text = wikitext[start_pos:end_pos]
    return bool(re.search(r'\{\{wikidata lexeme\|L\d+\}\}', section_text))


def extract_kana_reading(wikitext, start_pos, end_pos):
    """
    Extract kana reading from Japanese POS templates like {{ja-pos|proper|にほん}}.

    Args:
        wikitext: Full page wikitext
        start_pos: Start of the POS section
        end_pos: End of the POS section

    Returns:
        Kana reading string if found, None otherwise
    """
    section_text = wikitext[start_pos:end_pos]

    # Look for {{ja-pos|...|kana}} or {{ja-noun|kana}} etc.
    # Pattern matches: {{ja-POSTYPE|optional-params|KANA}}
    kana_pattern = r'\{\{ja-(?:pos|noun|verb|adj|adv|proper|pron)\|[^}]*?\|([ぁ-んァ-ヶー]+)\}\}'

    match = re.search(kana_pattern, section_text)
    if match:
        return match.group(1)

    return None


def insert_lexeme_template(wikitext, pos_header_match, lexeme_id):
    """
    Insert {{wikidata lexeme|LXXXX}} template after the POS header.

    Args:
        wikitext: Full page wikitext
        pos_header_match: The position after the POS header (===Noun===)
        lexeme_id: The lexeme ID (e.g., 'L8005')

    Returns:
        Modified wikitext
    """
    # Find the end of the POS header line
    header_end = wikitext.find('\n', pos_header_match)
    if header_end == -1:
        header_end = len(wikitext)

    # Insert the template on a new line after the header
    template = f"\n{{{{wikidata lexeme|{lexeme_id}}}}}"

    new_wikitext = wikitext[:header_end] + template + wikitext[header_end:]

    return new_wikitext


def process_page(site, page_title):
    """
    Process a single Wiktionary page.

    Args:
        site: mwclient Site object
        page_title: Title of the page to process

    Returns:
        True if edits were made, False otherwise
    """
    print(f"\nProcessing: {page_title}")

    page = site.pages[page_title]

    if not page.exists:
        print(f"  Page does not exist: {page_title}")
        return False

    wikitext = page.text()

    # Parse Japanese section and find POS subsections
    pos_sections = parse_japanese_section(wikitext)

    if not pos_sections:
        print(f"  No Japanese section or recognized POS found")
        return False

    print(f"  Found {len(pos_sections)} POS section(s)")

    # For Japanese, extract kana readings and check for (POS, kana) duplicates
    from collections import Counter

    # First pass: extract kana for each section
    pos_kana_list = []
    for pos_header, start_pos, end_pos in pos_sections:
        kana = extract_kana_reading(wikitext, start_pos, end_pos)
        pos_kana_list.append((pos_header, kana, start_pos, end_pos))

    # Count (POS, kana) combinations
    pos_kana_counts = Counter((pos, kana) for pos, kana, _, _ in pos_kana_list if kana)

    # Skip any (POS, kana) that appears multiple times
    duplicate_pos_kana = {(pos, kana) for (pos, kana), count in pos_kana_counts.items() if count > 1}
    if duplicate_pos_kana:
        dup_strs = [f"{pos}:{kana}" for pos, kana in sorted(duplicate_pos_kana)]
        print(f"  Skipping duplicate POS+kana combinations: {', '.join(dup_strs)}")

    modified_wikitext = wikitext
    edits_made = []
    offset = 0  # Track offset due to insertions

    for pos_header, kana_reading, start_pos, end_pos in pos_kana_list:
        # Adjust positions for previous insertions
        adjusted_start = start_pos + offset
        adjusted_end = end_pos + offset

        # Check if template already exists
        if check_lexeme_template_exists(modified_wikitext, adjusted_start, adjusted_end):
            print(f"    Template already exists, skipping")
            continue

        # Skip if no kana reading found
        if not kana_reading:
            print(f"  {pos_header}: No kana reading found, skipping")
            continue

        # Skip if this (POS, kana) combination appears multiple times
        if (pos_header, kana_reading) in duplicate_pos_kana:
            continue

        print(f"  Checking {pos_header} ({kana_reading})...")

        # Query Wikidata for matching lexeme using kana reading
        pos_qid = POS_MAP.get(pos_header)
        lexeme_id, count = query_wikidata_lexeme(kana_reading, pos_qid=pos_qid)

        if count == 0:
            print(f"    No matching lexeme found on Wikidata")
        elif count > 1:
            print(f"    Found {count} duplicate lexemes on Wikidata - skipping for safety")
        elif lexeme_id:
            print(f"    Found unique lexeme: {lexeme_id}")

            # Find the exact position of the POS header in the modified text
            pos_pattern = f'===\\s*{re.escape(pos_header)}\\s*==='
            match = re.search(pos_pattern, modified_wikitext[adjusted_start:adjusted_end])

            if match:
                insert_pos = adjusted_start + match.end()
                modified_wikitext = insert_lexeme_template(modified_wikitext, insert_pos, lexeme_id)

                # Update offset for next insertions
                template_length = len(f"\n{{{{wikidata lexeme|{lexeme_id}}}}}")
                offset += template_length

                edits_made.append((pos_header, lexeme_id))

        # Rate limit for Wikidata queries
        time.sleep(1)

    # Make the edit if any templates were added
    if edits_made:
        # Construct edit summary
        if len(edits_made) == 1:
            pos_header, lexeme_id = edits_made[0]
            summary = (f'Early testing of a script as per [[Wiktionary:Bots#Process]]. '
                      f'Connected to wikidata lexeme [[d:Lexeme:{lexeme_id}|{lexeme_id}]] '
                      f'as per Japanese, {pos_header.lower()}, title:"{page_title}" combination')
        else:
            lexeme_list = ', '.join(f'[[d:Lexeme:{lid}|{lid}]]' for _, lid in edits_made)
            summary = (f'Early testing of a script as per [[Wiktionary:Bots#Process]]. '
                      f'Connected to wikidata lexemes {lexeme_list}')

        try:
            page.save(modified_wikitext, summary=summary, minor=False)
            print(f"  ✓ Edit saved successfully")
            return True
        except Exception as e:
            print(f"  ✗ Error saving edit: {e}")
            return False
    else:
        print(f"  No edits needed")
        return False


def main():
    """Main function to run the bot."""
    print("Wiktionary Lexeme Bot (Japanese)")
    print("=" * 50)

    # Get page titles from command-line arguments
    if len(sys.argv) < 2:
        print("\nUsage: python wiktionary_lexeme_bot_ja.py <page1> [page2] [page3] ...")
        print("Example: python wiktionary_lexeme_bot_ja.py 日本 東京 京都")
        sys.exit(1)

    page_titles = sys.argv[1:]
    print(f"\nProcessing {len(page_titles)} page(s): {', '.join(page_titles)}")

    # Connect to Wiktionary
    print("\nConnecting to en.wiktionary.org...")
    site = mwclient.Site('en.wiktionary.org', clients_useragent=USER_AGENT)

    # Log in with bot credentials
    print("Logging in...")
    site.login(BOT_USERNAME, BOT_PASSWORD)
    print("✓ Logged in successfully\n")

    for page_title in page_titles:
        process_page(site, page_title)
        # Rate limit between pages
        time.sleep(1.5)

    print("\n" + "=" * 50)
    print("Bot run completed")


if __name__ == '__main__':
    main()
