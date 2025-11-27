#!/usr/bin/env python3
"""
Create English 'cat' Lexeme from Wikidata (v2)
===============================================
1. Query Wikidata for the 'cat' lexeme (L7)
2. Extract its data (lemma, senses, forms, language, etc.)
3. Create it on Aelaki using simple Q items (Q1, Q9, etc.)
"""

import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
AELAKI_API = 'https://aelaki.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

print("=" * 80)
print("STEP 1: FETCH LEXEME L7 FROM WIKIDATA")
print("=" * 80)
print()

# Fetch from Wikidata
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

r = session.get(WIKIDATA_API, params={
    'action': 'wbgetentities',
    'ids': 'L7',
    'format': 'json'
})

wd_entity = r.json()['entities']['L7']

print(f"✓ Fetched L7 from Wikidata")
print()

# Extract key data
lemma_value = wd_entity.get('lemmas', {}).get('en', {}).get('value', 'cat')
senses = wd_entity.get('senses', [])
forms = wd_entity.get('forms', [])

print("=" * 80)
print("EXTRACTED DATA FROM WIKIDATA")
print("=" * 80)
print(f"Lemma: {lemma_value}")
print(f"Senses: {len(senses)}")
print(f"Forms: {len(forms)}")
print()

# Get first sense gloss (in any language, preferring English)
sense_gloss = "A feline mammal"
if senses:
    glosses = senses[0].get('glosses', {})
    if 'en' in glosses:
        sense_gloss = glosses['en'].get('value', sense_gloss)
    elif glosses:
        sense_gloss = list(glosses.values())[0].get('value', sense_gloss)
    print(f"First sense gloss: {sense_gloss}")

print()
print("=" * 80)
print("STEP 2: AUTHENTICATE WITH AELAKI")
print("=" * 80)
print()

# Authenticate with Aelaki
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

print("=" * 80)
print("STEP 3: CREATE NEW LEXEME ON AELAKI")
print("=" * 80)
print()

# Build the lexeme data for Aelaki
# Use Q1 for language (from existing lexemes) and Q9 for lexical category
aelaki_lexeme_data = {
    'type': 'lexeme',
    'lemmas': {
        'en': {
            'language': 'en',
            'value': lemma_value
        }
    },
    'language': 'Q1',  # Use existing Q1
    'lexicalCategory': 'Q9',  # Use existing Q9
    'senses': [
        {
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': sense_gloss
                }
            },
            'claims': []
        }
    ],
    'forms': [
        {
            'representations': {
                'en': {
                    'language': 'en',
                    'value': lemma_value
                }
            },
            'grammaticalFeatures': [],
            'claims': []
        }
    ]
}

print("Creating lexeme with data:")
print(json.dumps(aelaki_lexeme_data, indent=2, ensure_ascii=False))
print()

# Create the lexeme
r = aelaki_session.post(AELAKI_API, data={
    'action': 'wbeditentity',
    'new': 'lexeme',
    'data': json.dumps(aelaki_lexeme_data),
    'token': csrf_token,
    'format': 'json'
})

result = r.json()

if 'error' in result:
    print(f"✗ Error creating lexeme: {result['error'].get('code')}")
    print(f"  {result['error'].get('info')}")
elif 'entity' in result:
    entity = result['entity']
    new_lex_id = entity.get('id', 'UNKNOWN')
    print(f"✓ Successfully created new lexeme: {new_lex_id}")
    print()
    print(f"New lexeme details:")
    print(f"  Lemmas: {entity.get('lemmas', {})}")
    print(f"  Language: {entity.get('language', '')}")
    print(f"  Lexical Category: {entity.get('lexicalCategory', '')}")
    print(f"  Senses: {len(entity.get('senses', []))}")
    print(f"  Forms: {len(entity.get('forms', []))}")
    print()
    print(f"✓ View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
else:
    print(f"? Unexpected response: {str(result)[:200]}")
