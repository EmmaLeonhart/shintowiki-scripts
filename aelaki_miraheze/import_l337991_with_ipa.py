#!/usr/bin/env python3
"""
Import Wikidata L337991 to Aelaki with IPA Pronunciation
==========================================================
Imports L337991 (kept) from Wikidata to Aelaki with category mapping and IPA
"""

import requests
import json
import sys
import io
import time
import re

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
AELAKI_API = 'https://aelaki.miraheze.org/w/api.php'
WIKTIONARY_URL = 'https://en.wiktionary.org/wiki/kept'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

# Category mapping
CATEGORY_MAPPING = {
    'Q1084': 'Q20',      # noun -> Noun
    'Q24905': 'Q22',     # verb -> Verb
    'Q34698': 'Q25',     # adjective -> Adjective
    'Q380057': 'Q26'     # adverb -> Adverb
}

def map_category(wd_category):
    """Map Wikidata category to Aelaki category"""
    return CATEGORY_MAPPING.get(wd_category, 'Q9')

def extract_ipa_from_wiktionary(url):
    """Extract English IPA pronunciation from Wiktionary page"""
    print("=" * 80)
    print("STEP 1: FETCH IPA PRONUNCIATION FROM WIKTIONARY")
    print("=" * 80)
    print()

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    try:
        r = session.get(url)
        if r.status_code == 200:
            # Try to find IPA in multiple ways
            html = r.text

            # Try pattern 1: {{IPA|en|...}}
            if '{{IPA|en|' in html:
                start = html.find('{{IPA|en|')
                if start != -1:
                    start += len('{{IPA|en|')
                    end = html.find('}}', start)
                    if end != -1:
                        ipa = html[start:end].strip()
                        # Clean up any extra markup
                        ipa = re.sub(r'<[^>]+>', '', ipa)
                        # Remove slashes if present
                        ipa = ipa.strip('/').strip()
                        if ipa:
                            print(f"✓ Found IPA pronunciation: {ipa}")
                            print()
                            return ipa
    except Exception as e:
        pass

    # Fallback: hardcode common pronunciations if extraction fails
    fallback_ipas = {
        'kept': 'kɛpt',
        'kill': 'kɪl',
        'cat': 'kæt',
        'dog': 'dɔɡ'
    }

    print("⊘ Could not extract IPA from Wiktionary, using common pronunciation")
    ipa = fallback_ipas.get('kept', None)
    if ipa:
        print(f"✓ Using known pronunciation: {ipa}")
        print()
        return ipa

    print("✗ IPA pronunciation not found")
    print()
    return None

print("=" * 80)
print("IMPORT WIKIDATA L337991 WITH IPA TO AELAKI")
print("=" * 80)
print()

# Step 1: Extract IPA from Wiktionary
ipa_pronunciation = extract_ipa_from_wiktionary(WIKTIONARY_URL)

# Step 2: Fetch L337991 from Wikidata
print("=" * 80)
print("STEP 2: FETCH L337991 FROM WIKIDATA")
print("=" * 80)
print()

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

r = session.get(WIKIDATA_API, params={
    'action': 'wbgetentities',
    'ids': 'L337991',
    'format': 'json'
})

wd_entity = r.json()['entities']['L337991']

if 'missing' in wd_entity:
    print("✗ L337991 not found on Wikidata")
    sys.exit(1)

lemma_value = wd_entity.get('lemmas', {}).get('en', {}).get('value', '')
if not lemma_value:
    lemmas = wd_entity.get('lemmas', {})
    if lemmas:
        lemma_value = list(lemmas.values())[0].get('value', 'L337991')

wd_category = wd_entity.get('lexicalCategory', 'Q9')
aelaki_category = map_category(wd_category)
senses = wd_entity.get('senses', [])

print(f"✓ Fetched L337991 from Wikidata")
print(f"  Lemma: {lemma_value}")
print(f"  Wikidata Category: {wd_category}")
print(f"  Mapped to Aelaki Category: {aelaki_category}")
print(f"  Senses: {len(senses)}")
print()

# Step 3: Authenticate with Aelaki
print("=" * 80)
print("STEP 3: AUTHENTICATE WITH AELAKI")
print("=" * 80)
print()

aelaki_session = requests.Session()
aelaki_session.headers.update({'User-Agent': 'Mozilla/5.0'})

r = aelaki_session.get(AELAKI_API, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']

r = aelaki_session.post(AELAKI_API, data={
    'action': 'login',
    'lgname': USERNAME,
    'lgpassword': PASSWORD,
    'lgtoken': login_token,
    'format': 'json'
})

r = aelaki_session.get(AELAKI_API, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']

print("✓ Authenticated with Aelaki")
print()

# Step 4: Create bare lexeme
print("=" * 80)
print("STEP 4: CREATE BARE LEXEME")
print("=" * 80)
print()

aelaki_lexeme_data = {
    'type': 'lexeme',
    'lemmas': {
        'en': {
            'language': 'en',
            'value': lemma_value
        }
    },
    'language': 'Q3',  # English
    'lexicalCategory': aelaki_category
}

r = aelaki_session.post(AELAKI_API, data={
    'action': 'wbeditentity',
    'new': 'lexeme',
    'data': json.dumps(aelaki_lexeme_data),
    'token': csrf_token,
    'format': 'json'
})

result = r.json()

if 'entity' not in result:
    print(f"✗ Failed to create lexeme")
    print(f"  Error: {result.get('error', {}).get('code')}")
    sys.exit(1)

new_lex_id = result['entity']['id']
print(f"✓ Created bare lexeme: {new_lex_id}")
print(f"  Lemma: {lemma_value}")
print(f"  Language: Q3 (English)")
print(f"  Category: {aelaki_category}")
print()

time.sleep(0.5)

# Step 5: Add senses (if any)
if senses:
    print("=" * 80)
    print("STEP 5: ADD SENSES")
    print("=" * 80)
    print()

    senses_to_add = []
    for sense in senses:
        glosses = sense.get('glosses', {})
        sense_obj = {
            'add': '',
            'glosses': glosses
        }
        senses_to_add.append(sense_obj)

    edit_data = {'senses': senses_to_add}

    r = aelaki_session.post(AELAKI_API, data={
        'action': 'wbeditentity',
        'id': new_lex_id,
        'data': json.dumps(edit_data),
        'token': csrf_token,
        'format': 'json'
    })

    result = r.json()

    if 'entity' in result:
        entity = result['entity']
        senses_count = len(entity.get('senses', []))
        print(f"✓ Added {senses_count} senses")
    else:
        print(f"✗ Error adding senses: {result.get('error', {}).get('code')}")

    print()
    time.sleep(0.5)

# Step 6: Add P4, P7, and P5 (IPA) claims
print("=" * 80)
print("STEP 6: ADD P4, P7, AND P5 (IPA) CLAIMS")
print("=" * 80)
print()

claims_to_add = {
    'P4': [
        {
            'mainsnak': {
                'snaktype': 'value',
                'property': 'P4',
                'datavalue': {
                    'value': 'L337991',
                    'type': 'string'
                },
                'datatype': 'string'
            },
            'type': 'statement',
            'rank': 'normal'
        }
    ],
    'P7': [
        {
            'mainsnak': {
                'snaktype': 'value',
                'property': 'P7',
                'datavalue': {
                    'value': lemma_value,
                    'type': 'string'
                },
                'datatype': 'string'
            },
            'type': 'statement',
            'rank': 'normal'
        }
    ]
}

# Add P5 (English IPA pronunciation) if we found the pronunciation
if ipa_pronunciation:
    claims_to_add['P5'] = [
        {
            'mainsnak': {
                'snaktype': 'value',
                'property': 'P5',
                'datavalue': {
                    'value': ipa_pronunciation,
                    'type': 'string'
                },
                'datatype': 'string'
            },
            'type': 'statement',
            'rank': 'normal'
        }
    ]

edit_data = {'claims': claims_to_add}

r = aelaki_session.post(AELAKI_API, data={
    'action': 'wbeditentity',
    'id': new_lex_id,
    'data': json.dumps(edit_data),
    'token': csrf_token,
    'format': 'json'
})

result = r.json()

if 'entity' in result:
    entity = result['entity']
    claims = entity.get('claims', {})
    p4_count = len(claims.get('P4', []))
    p7_count = len(claims.get('P7', []))
    p5_count = len(claims.get('P5', []))
    p5_value = claims.get('P5', [{}])[0].get('mainsnak', {}).get('datavalue', {}).get('value', 'N/A') if p5_count > 0 else 'N/A'

    print(f"✓ Added lexeme-level claims:")
    print(f"  P4 (Wikidata link): {p4_count} claim -> L337991")
    print(f"  P7 (text): {p7_count} claim -> '{lemma_value}'")
    if p5_count > 0:
        print(f"  P5 (English IPA): {p5_count} claim -> '{p5_value}'")
else:
    print(f"✗ Error adding claims: {result.get('error', {}).get('code')}")

print()

print("=" * 80)
print("SUCCESS!")
print("=" * 80)
print()

print(f"✓ Imported Wikidata L337991 to Aelaki {new_lex_id}")
print()
print(f"Lexeme Details:")
print(f"  ID: {new_lex_id}")
print(f"  Lemma: {lemma_value}")
print(f"  Language: Q3 (English)")
print(f"  Lexical Category: {aelaki_category}")
print(f"  Senses: {len(senses)}")
print(f"  P4 Link: L337991 (Wikidata)")
print(f"  P7 Text: {lemma_value}")
if ipa_pronunciation:
    print(f"  P5 (English IPA): {ipa_pronunciation}")
print()
print(f"View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
