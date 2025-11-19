#!/usr/bin/env python3
"""
Create English 'cat' Lexeme from Wikidata (v3)
===============================================
1. Fetch Wikidata L7 lexeme data
2. Copy all senses from Wikidata
3. Create on Aelaki with Q3 (English)
4. Add P4 property linking to Wikidata L7
5. Add P7 (text) with English glosses as claims
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
PASSWORD = '[REDACTED_SECRET_1]'

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

# Extract senses for copying
aelaki_senses = []
for sense in senses:
    # Get glosses in any language, preferring English
    glosses = sense.get('glosses', {})
    sense_data = {
        'glosses': glosses,
        'claims': []
    }

    # If there's an English gloss, also add it as P7 claim
    if 'en' in glosses:
        gloss_text = glosses['en'].get('value', '')
        if gloss_text:
            sense_data['claims'].append({
                'mainsnak': {
                    'snaktype': 'value',
                    'property': 'P7',
                    'datavalue': {
                        'value': gloss_text,
                        'type': 'string'
                    },
                    'datatype': 'string'
                },
                'type': 'statement',
                'rank': 'normal'
            })

    aelaki_senses.append(sense_data)

print(f"Prepared {len(aelaki_senses)} senses for Aelaki")
for i, sense in enumerate(aelaki_senses, 1):
    glosses = sense.get('glosses', {})
    print(f"  S{i}: {list(glosses.keys())}")
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
# Use Q3 for English language
aelaki_lexeme_data = {
    'type': 'lexeme',
    'lemmas': {
        'en': {
            'language': 'en',
            'value': lemma_value
        }
    },
    'language': 'Q3',  # English
    'lexicalCategory': 'Q9',  # Noun
    'senses': aelaki_senses,
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
    ],
    'claims': {
        'P4': [
            {
                'mainsnak': {
                    'snaktype': 'value',
                    'property': 'P4',
                    'datavalue': {
                        'value': 'L7',
                        'type': 'string'
                    },
                    'datatype': 'string'
                },
                'type': 'statement',
                'rank': 'normal'
            }
        ]
    }
}

print("Creating lexeme with data:")
print(f"  Lemma: {lemma_value}")
print(f"  Language: Q3 (English)")
print(f"  Lexical Category: Q9 (Noun)")
print(f"  Senses: {len(aelaki_senses)}")
print(f"  Forms: 1")
print(f"  P4 (Wikidata link): L7")
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
    for i, sense in enumerate(entity.get('senses', []), 1):
        glosses = sense.get('glosses', {})
        claims = sense.get('claims', {})
        p7_count = len(claims.get('P7', []))
        print(f"    S{i}: {list(glosses.keys())} + {p7_count} P7 claims")
    print(f"  Forms: {len(entity.get('forms', []))}")
    print(f"  P4 claim (Wikidata link): {len(entity.get('claims', {}).get('P4', []))} found")
    print()
    print(f"✓ View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
else:
    print(f"? Unexpected response: {str(result)[:200]}")
