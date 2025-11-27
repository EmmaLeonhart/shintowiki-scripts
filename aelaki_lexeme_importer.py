#!/usr/bin/env python3
"""
Mass import English lexemes into aelaki.miraheze.org
Tests import reliability and volume capacity with diverse English words.
"""

import requests
import json
import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

# Aelaki credentials
AELAKI_URL = 'aelaki.miraheze.org'
AELAKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

# English words to import as lexemes
ENGLISH_WORDS = [
    'apple',
    'book',
    'cat',
    'dog',
    'tree',
    'water',
    'fire',
    'house',
    'person',
    'mountain',
    'river',
    'sun',
    'moon',
    'star',
    'bird',
    'fish',
    'flower',
    'stone',
    'bread',
    'milk',
    'love',
    'hope',
    'fear',
    'joy',
    'anger',
    'peace',
    'war',
    'friend',
    'family',
    'teacher',
    'student',
    'doctor',
    'patient',
    'road',
    'bridge',
    'city',
    'village',
    'kingdom',
    'sword',
    'shield',
    'helmet',
    'horse',
    'ship',
    'wheel',
    'door',
    'window',
    'table',
    'chair',
    'bed',
    'lamp',
]

def get_csrf_token(session):
    """Get CSRF token from Aelaki."""
    try:
        r = session.get(f'https://{AELAKI_URL}{AELAKI_PATH}api.php', params={
            'action': 'query',
            'meta': 'tokens',
            'type': 'csrf',
            'format': 'json'
        })
        r.raise_for_status()
        data = r.json()
        token = data['query']['tokens']['csrftoken']
        return token
    except Exception as e:
        print(f"Error getting CSRF token: {e}")
        return None

def find_lexeme_by_word(word):
    """Search Wikidata for English lexeme with this word."""
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
            'User-Agent': 'Immanuelle/AelakiLexemeImporter (https://aelaki.miraheze.org; immanuelleproject@gmail.com)'
        }
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get('search') and len(data['search']) > 0:
            return data['search'][0]['id']  # Return the Wikidata LID
        return None
    except Exception as e:
        print(f"    Error searching for {word}: {e}")
        return None

def get_lexeme_data(lid):
    """Fetch lexeme data from Wikidata."""
    try:
        params = {
            'action': 'wbgetentities',
            'ids': lid,
            'format': 'json'
        }
        headers = {
            'User-Agent': 'Immanuelle/AelakiLexemeImporter (https://aelaki.miraheze.org; immanuelleproject@gmail.com)'
        }
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data['entities'].get(lid)
    except Exception as e:
        print(f"    Error fetching {lid}: {e}")
        return None

def create_lexeme_on_aelaki(session, csrf_token, lexeme_data):
    """Create a new lexeme on Aelaki."""
    try:
        # Prepare lexeme data for creation
        edit_data = {
            'type': 'lexeme',
            'language': lexeme_data.get('language', 'en'),
            'lemmas': lexeme_data.get('lemmas', {}),
            'lexicalCategory': lexeme_data.get('lexicalCategory'),
            'senses': lexeme_data.get('senses', []),
            'forms': lexeme_data.get('forms', [])
        }

        # POST to Aelaki to create the lexeme
        r = session.post(f'https://{AELAKI_URL}{AELAKI_PATH}api.php', data={
            'action': 'wbeditentity',
            'new': 'lexeme',
            'data': json.dumps(edit_data),
            'token': csrf_token,
            'format': 'json'
        })
        r.raise_for_status()
        result = r.json()

        if 'entity' in result:
            return result['entity'].get('id')
        elif 'error' in result:
            return f"ERROR: {result['error'].get('info', 'Unknown error')}"
        else:
            return None
    except Exception as e:
        return f"EXCEPTION: {str(e)}"

def main():
    """Main execution."""
    print("="*70)
    print("AELAKI LEXEME MASS IMPORTER")
    print("="*70)
    print()

    try:
        # Login to Aelaki
        print(f"Connecting to {AELAKI_URL}...")
        session = requests.Session()

        # Login via mwclient
        site = mwclient.Site(AELAKI_URL, path=AELAKI_PATH)
        site.login(USERNAME, PASSWORD)

        # Get session cookies from mwclient
        session.cookies.update(site.client.http_session.cookies)

        print(f"Logged in as {USERNAME}\n")

        # Get CSRF token
        csrf_token = get_csrf_token(session)
        if not csrf_token:
            print("[ERROR] Could not get CSRF token")
            return

        print(f"Got CSRF token: {csrf_token[:20]}...\n")
        print(f"Importing {len(ENGLISH_WORDS)} English words as lexemes...\n")

        successful_imports = []
        failed_imports = []

        for i, word in enumerate(ENGLISH_WORDS, 1):
            print(f"{i}/{len(ENGLISH_WORDS)}: Importing '{word}'...", end=" ")

            # Find lexeme on Wikidata
            lid = find_lexeme_by_word(word)
            if not lid:
                print("[SKIP - not found on Wikidata]")
                failed_imports.append((word, "Not found on Wikidata"))
                continue

            # Get lexeme data from Wikidata
            lexeme_data = get_lexeme_data(lid)
            if not lexeme_data:
                print("[SKIP - could not fetch data]")
                failed_imports.append((word, f"Could not fetch {lid}"))
                continue

            # Create lexeme on Aelaki
            result = create_lexeme_on_aelaki(session, csrf_token, lexeme_data)
            if result and not result.startswith('ERROR') and not result.startswith('EXCEPTION'):
                print(f"[OK] {result}")
                successful_imports.append((word, lid, result))
            else:
                print(f"[FAILED] {result}")
                failed_imports.append((word, result or "Unknown error"))

            # Rate limit
            time.sleep(1.5)

        # Summary
        print("\n" + "="*70)
        print(f"IMPORT SUMMARY")
        print("="*70)
        print(f"Successful: {len(successful_imports)}")
        print(f"Failed: {len(failed_imports)}")
        print(f"Total: {len(ENGLISH_WORDS)}")
        print(f"Success Rate: {len(successful_imports)/len(ENGLISH_WORDS)*100:.1f}%")
        print()

        if successful_imports:
            print("SUCCESSFUL IMPORTS:")
            for word, lid, aelaki_id in successful_imports:
                print(f"  {word:15} -> {lid:6} -> {aelaki_id}")
            print()

        if failed_imports:
            print("FAILED IMPORTS:")
            for word, reason in failed_imports:
                print(f"  {word:15} -> {reason}")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
