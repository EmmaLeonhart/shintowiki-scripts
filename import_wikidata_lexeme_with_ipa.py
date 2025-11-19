#!/usr/bin/env python3
"""
Import any Wikidata Lexeme to Aelaki with IPA Pronunciation
===========================================================
Generic importer for Wikidata lexemes with category mapping and IPA

Usage: python import_wikidata_lexeme_with_ipa.py <WIKIDATA_LEXEME_ID>
Example: python import_wikidata_lexeme_with_ipa.py L4164
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
WIKTIONARY_BASE = 'https://en.wiktionary.org/wiki'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_1]'

# Category mapping: Wikidata -> Aelaki
CATEGORY_MAPPING = {
    'Q1084': 'Q20',      # noun -> Noun
    'Q24905': 'Q22',     # verb -> Verb
    'Q34698': 'Q25',     # adjective -> Adjective
    'Q380057': 'Q26'     # adverb -> Adverb
}

# IPA pronunciations for common words (fallback)
FALLBACK_IPAS = {
    'kill': 'kɪl',
    'kept': 'kɛpt',
    'cat': 'kæt',
    'dog': 'dɔɡ'
}

def map_category(wd_category):
    """Map Wikidata category to Aelaki category"""
    return CATEGORY_MAPPING.get(wd_category, 'Q9')

def extract_ipa_from_wiktionary(lemma):
    """Extract English IPA pronunciation from Wiktionary page"""
    url = f"{WIKTIONARY_BASE}/{lemma}"

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    try:
        r = session.get(url)
        if r.status_code == 200:
            html = r.text

            # Try to find IPA in {{IPA|en|...}}
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
                            return ipa
    except Exception as e:
        pass

    # Fallback to known pronunciations
    if lemma.lower() in FALLBACK_IPAS:
        return FALLBACK_IPAS[lemma.lower()]

    return None

# Check command line arguments
if len(sys.argv) < 2:
    print("Usage: python import_wikidata_lexeme_with_ipa.py <WIKIDATA_LEXEME_ID>")
    print("Example: python import_wikidata_lexeme_with_ipa.py L4164")
    sys.exit(1)

wd_lexeme_id = sys.argv[1].upper()

print("=" * 80)
print(f"IMPORT WIKIDATA {wd_lexeme_id} WITH IPA TO AELAKI")
print("=" * 80)
print()

# Step 1: Fetch lexeme from Wikidata
print("=" * 80)
print(f"STEP 1: FETCH {wd_lexeme_id} FROM WIKIDATA")
print("=" * 80)
print()

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

r = session.get(WIKIDATA_API, params={
    'action': 'wbgetentities',
    'ids': wd_lexeme_id,
    'format': 'json'
})

wd_entity = r.json()['entities'].get(wd_lexeme_id, {})

if 'missing' in wd_entity:
    print(f"✗ {wd_lexeme_id} not found on Wikidata")
    sys.exit(1)

# Extract lexeme information
lemma_value = wd_entity.get('lemmas', {}).get('en', {}).get('value', '')
if not lemma_value:
    lemmas = wd_entity.get('lemmas', {})
    if lemmas:
        lemma_value = list(lemmas.values())[0].get('value', wd_lexeme_id)

wd_category = wd_entity.get('lexicalCategory', 'Q9')
aelaki_category = map_category(wd_category)
senses = wd_entity.get('senses', [])

print(f"✓ Fetched {wd_lexeme_id} from Wikidata")
print(f"  Lemma: {lemma_value}")
print(f"  Wikidata Category: {wd_category}")
print(f"  Mapped to Aelaki Category: {aelaki_category}")
print(f"  Senses: {len(senses)}")
print()

# Step 2: Extract IPA pronunciation
print("=" * 80)
print("STEP 2: FETCH IPA PRONUNCIATION FROM WIKTIONARY")
print("=" * 80)
print()

ipa_pronunciation = extract_ipa_from_wiktionary(lemma_value)
if ipa_pronunciation:
    print(f"✓ Found IPA pronunciation: {ipa_pronunciation}")
else:
    print(f"⊘ IPA pronunciation not found")
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
        for i, sense in enumerate(entity.get('senses', []), 1):
            glosses = sense.get('glosses', {})
            gloss_langs = list(glosses.keys())[:6]
            print(f"  S{i}: {gloss_langs}...") if len(glosses) > 6 else print(f"  S{i}: {gloss_langs}")
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
                    'value': wd_lexeme_id,
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
    print(f"  P4 (Wikidata link): {p4_count} claim -> {wd_lexeme_id}")
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

print(f"✓ Imported Wikidata {wd_lexeme_id} to Aelaki {new_lex_id}")
print()
print(f"Lexeme Details:")
print(f"  ID: {new_lex_id}")
print(f"  Lemma: {lemma_value}")
print(f"  Language: Q3 (English)")
print(f"  Lexical Category: {aelaki_category}")
print(f"  Senses: {len(senses)}")
print(f"  P4 Link: {wd_lexeme_id} (Wikidata)")
print(f"  P7 Text: {lemma_value}")
if ipa_pronunciation:
    print(f"  P5 (English IPA): {ipa_pronunciation}")
print()
print(f"View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
