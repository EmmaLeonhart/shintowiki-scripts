#!/usr/bin/env python3
"""
Bulk Import English Lexemes from Wikidata to Aelaki
====================================================
Searches Wikidata for English lexemes and imports them to Aelaki with IPA support.

This script:
1. Searches Wikidata for English lexemes matching common words
2. Imports each lexeme to Aelaki with all senses
3. Adds IPA pronunciation from Wiktionary when available
4. Tracks successes and failures

Usage: python bulk_import_english_lexemes.py
"""

import requests
import json
import time
import sys
import mwclient

from ipa_to_illish_converter import english_ipa_to_illish

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
AELAKI_URL = 'aelaki.miraheze.org'
AELAKI_PATH = '/w/'
WIKTIONARY_BASE = 'https://en.wiktionary.org/wiki'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

# Category mapping: Wikidata -> Aelaki
CATEGORY_MAPPING = {
    'Q1084': 'Q20',      # noun -> Noun
    'Q24905': 'Q22',     # verb -> Verb
    'Q34698': 'Q25',     # adjective -> Adjective
    'Q380057': 'Q26'     # adverb -> Adverb
}

# Common English words to import
ENGLISH_WORDS = [
    'run', 'walk', 'jump', 'sit', 'stand', 'lie', 'sleep', 'wake',
    'eat', 'drink', 'think', 'know', 'see', 'hear', 'feel', 'touch',
    'come', 'go', 'stay', 'leave', 'arrive', 'depart', 'begin', 'end',
    'happy', 'sad', 'angry', 'afraid', 'tired', 'hungry', 'thirsty', 'sick',
    'big', 'small', 'long', 'short', 'tall', 'wide', 'narrow', 'thick',
    'hot', 'cold', 'warm', 'cool', 'dry', 'wet', 'clean', 'dirty',
    'fast', 'slow', 'quick', 'soft', 'hard', 'loud', 'quiet', 'bright',
    'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    'red', 'blue', 'green', 'yellow', 'black', 'white', 'gray', 'brown',
]

def map_category(wd_category):
    """Map Wikidata category to Aelaki category"""
    return CATEGORY_MAPPING.get(wd_category, 'Q9')

def extract_ipa_from_wiktionary(lemma):
    """Extract English IPA pronunciation from Wiktionary page"""
    url = f"{WIKTIONARY_BASE}/{lemma}"

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()

        # Look for /.../ IPA pattern in the page
        import re
        ipa_pattern = r'/([^/]+)/'
        matches = re.findall(ipa_pattern, response.text)

        if matches:
            for match in matches:
                # Filter to reasonable IPA (not HTML tags or other noise)
                if any(c in match for c in 'ɪɛæʌɔəaːɡkpbtdnmlfvθðszʃʒtʃdʒjwŋ'):
                    return match
        return None
    except Exception as e:
        return None

def search_wikidata_lexeme(word):
    """Search Wikidata for an English lexeme matching this word"""
    try:
        params = {
            'action': 'wbsearchentities',
            'search': word,
            'type': 'lexeme',
            'language': 'en',
            'limit': 1,
            'format': 'json'
        }
        headers = {
            'User-Agent': 'Immanuelle/BulkLexemeImporter (https://aelaki.miraheze.org; immanuelleproject@gmail.com)'
        }
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get('search') and len(data['search']) > 0:
            return data['search'][0]['id']
        return None
    except Exception as e:
        return None

def get_lexeme_data(lid):
    """Fetch lexeme data from Wikidata"""
    try:
        params = {
            'action': 'wbgetentities',
            'ids': lid,
            'format': 'json'
        }
        headers = {
            'User-Agent': 'Immanuelle/BulkLexemeImporter (https://aelaki.miraheze.org; immanuelleproject@gmail.com)'
        }
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data['entities'].get(lid)
    except Exception as e:
        return None

def authenticate_aelaki():
    """Authenticate with Aelaki using mwclient"""
    try:
        site = mwclient.Site(AELAKI_URL, path=AELAKI_PATH)
        site.login(USERNAME, PASSWORD)
        csrf_token = site.get_token('csrf')
        return site, csrf_token
    except Exception as e:
        print(f"Error authenticating: {e}")
        return None, None

def create_lexeme_on_aelaki(site, csrf_token, lexeme_data):
    """Create a new lexeme on Aelaki"""
    try:
        edit_data = {
            'type': 'lexeme',
            'language': lexeme_data.get('language', 'Q3'),  # English
            'lemmas': lexeme_data.get('lemmas', {}),
            'claims': []
        }

        # Add lexical category if available
        if 'lexicalCategory' in lexeme_data:
            edit_data['lexicalCategory'] = map_category(lexeme_data['lexicalCategory'])

        result = site.api('wbeditentity',
            new='lexeme',
            data=json.dumps(edit_data),
            token=csrf_token)

        if 'entity' in result:
            return result['entity'].get('id')
        else:
            return None
    except Exception as e:
        return None

def add_senses_to_lexeme(site, csrf_token, aelaki_id, lexeme_data):
    """Add senses to a lexeme on Aelaki"""
    try:
        senses = lexeme_data.get('senses', [])
        if not senses:
            return True

        # Prepare sense data
        sense_data = []
        for sense in senses[:5]:  # Limit to 5 senses per lexeme
            sense_obj = {
                'add': '',
                'glosses': sense.get('glosses', {})
            }
            sense_data.append(sense_obj)

        if not sense_data:
            return True

        result = site.api('wbeditentity',
            id=aelaki_id,
            data=json.dumps({'senses': sense_data}),
            token=csrf_token)

        return 'entity' in result
    except Exception as e:
        return False

def add_ipa_claims(site, csrf_token, aelaki_id, ipa, illish_ipa, wikidata_lid):
    """Add IPA pronunciation claims to lexeme"""
    try:
        claims = []

        # P4: Link to Wikidata
        claims.append({
            'mainsnak': {
                'snaktype': 'value',
                'property': 'P4',
                'datavalue': {
                    'value': {
                        'entity-type': 'lexeme',
                        'numeric-id': int(wikidata_lid[1:])
                    },
                    'type': 'wikibase-entityid'
                }
            },
            'type': 'statement',
            'rank': 'normal'
        })

        # P5: English IPA
        if ipa:
            claims.append({
                'mainsnak': {
                    'snaktype': 'value',
                    'property': 'P5',
                    'datavalue': {
                        'value': ipa,
                        'type': 'string'
                    }
                },
                'type': 'statement',
                'rank': 'normal'
            })

        # P6: Illish IPA
        if illish_ipa:
            claims.append({
                'mainsnak': {
                    'snaktype': 'value',
                    'property': 'P6',
                    'datavalue': {
                        'value': illish_ipa,
                        'type': 'string'
                    }
                },
                'type': 'statement',
                'rank': 'normal'
            })

        if not claims:
            return True

        result = site.api('wbeditentity',
            id=aelaki_id,
            data=json.dumps({'claims': claims}),
            token=csrf_token)

        return 'entity' in result
    except Exception as e:
        return False

def main():
    """Main execution"""
    print("="*70)
    print("BULK ENGLISH LEXEME IMPORTER")
    print("="*70)
    print()

    session, csrf_token = authenticate_aelaki()
    if not session or not csrf_token:
        print("[ERROR] Could not authenticate with Aelaki")
        return

    print(f"Authenticated with Aelaki\n")
    print(f"Importing {len(ENGLISH_WORDS)} English words...\n")

    successful = []
    failed = []

    for i, word in enumerate(ENGLISH_WORDS, 1):
        print(f"{i}/{len(ENGLISH_WORDS)}: {word}...", end=" ")

        # Search for lexeme
        lid = search_wikidata_lexeme(word)
        if not lid:
            print("[SKIP - not found on Wikidata]")
            failed.append((word, "Not found on Wikidata"))
            continue

        # Get lexeme data
        lexeme_data = get_lexeme_data(lid)
        if not lexeme_data:
            print("[SKIP - could not fetch]")
            failed.append((word, "Could not fetch from Wikidata"))
            continue

        # Create on Aelaki
        aelaki_id = create_lexeme_on_aelaki(site, csrf_token, lexeme_data)
        if not aelaki_id:
            print("[FAILED - could not create]")
            failed.append((word, "Could not create on Aelaki"))
            continue

        # Add senses
        if not add_senses_to_lexeme(site, csrf_token, aelaki_id, lexeme_data):
            print("[PARTIAL - created but no senses]")
            successful.append((word, lid, aelaki_id, 0))
            continue

        # Get IPA from Wiktionary
        ipa = extract_ipa_from_wiktionary(word)
        illish_ipa = english_ipa_to_illish(ipa) if ipa else None

        # Add IPA claims
        add_ipa_claims(site, csrf_token, aelaki_id, ipa, illish_ipa, lid)

        num_senses = len(lexeme_data.get('senses', []))
        print(f"[OK] {aelaki_id} ({num_senses} senses)")
        successful.append((word, lid, aelaki_id, num_senses))

        # Rate limit
        time.sleep(2)

    # Summary
    print(f"\n{'='*70}")
    print("IMPORT SUMMARY")
    print(f"{'='*70}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total: {len(ENGLISH_WORDS)}")
    print(f"Success Rate: {len(successful)/len(ENGLISH_WORDS)*100:.1f}%")
    print()

    if successful:
        print("SUCCESSFUL IMPORTS:")
        for word, lid, aelaki_id, num_senses in successful:
            print(f"  {word:15} -> {lid:6} -> {aelaki_id:5} ({num_senses} senses)")
        print()

    if failed:
        print("FAILED IMPORTS:")
        for word, reason in failed:
            print(f"  {word:15} -> {reason}")
        print()

if __name__ == '__main__':
    main()
