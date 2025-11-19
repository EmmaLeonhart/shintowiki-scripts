#!/usr/bin/env python3
"""
Create English 'cat' Lexeme from Wikidata (v5)
===============================================
Step 1: Create bare lexeme with lemma
Step 2: Add senses with "add" syntax (WITHOUT P7 on senses)
Step 3: Add P4 link to Wikidata L7
Step 4: Add P7 claim at lexeme level with the lemma text
"""

import requests
import json
import sys
import io
import time

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

lemma_value = wd_entity.get('lemmas', {}).get('en', {}).get('value', 'cat')
senses = wd_entity.get('senses', [])

print(f"✓ Fetched L7 from Wikidata: {lemma_value}")
print(f"  Senses: {len(senses)}")
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
print("STEP 3: CREATE BARE LEXEME")
print("=" * 80)
print()

# Create bare lexeme with just lemma
aelaki_lexeme_data = {
    'type': 'lexeme',
    'lemmas': {
        'en': {
            'language': 'en',
            'value': lemma_value
        }
    },
    'language': 'Q3',  # English
    'lexicalCategory': 'Q9'  # Noun
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
print()

time.sleep(0.5)

print("=" * 80)
print("STEP 4: ADD SENSES WITH 'add' SYNTAX")
print("=" * 80)
print()

# Add senses using "add" syntax (WITHOUT any P7 on senses)
senses_to_add = []
for sense in senses:
    glosses = sense.get('glosses', {})

    sense_obj = {
        'add': '',
        'glosses': glosses
    }

    senses_to_add.append(sense_obj)

print(f"Adding {len(senses_to_add)} senses...")
print()

# Add all senses in one edit
edit_data = {
    'senses': senses_to_add
}

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
    print(f"✓ Added senses: {senses_count} total")

    # Show sense details
    for i, sense in enumerate(entity.get('senses', []), 1):
        glosses = sense.get('glosses', {})
        print(f"  S{i}: {len(glosses)} languages")
else:
    print(f"✗ Error adding senses: {result.get('error', {}).get('code')}")
    print(f"  {result.get('error', {}).get('info')}")

print()
time.sleep(0.5)

print("=" * 80)
print("STEP 5: ADD P4 AND P7 CLAIMS AT LEXEME LEVEL")
print("=" * 80)
print()

# Add P4 (Wikidata link) and P7 (lexeme text) at lexeme level
edit_data = {
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
}

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
    print(f"✓ Added claims at lexeme level:")
    print(f"  P4 (Wikidata link): {p4_count}")
    print(f"  P7 (text): {p7_count}")
else:
    print(f"✗ Error adding claims: {result.get('error', {}).get('code')}")

print()

print("=" * 80)
print("FINAL LEXEME")
print("=" * 80)
print()

# Fetch final state
r = aelaki_session.get(AELAKI_API, params={
    'action': 'wbgetentities',
    'ids': new_lex_id,
    'format': 'json'
})

entity = r.json()['entities'][new_lex_id]
print(f"✓ Lexeme: {new_lex_id}")
print(f"  Lemma: {entity.get('lemmas', {}).get('en', {}).get('value')}")
print(f"  Language: {entity.get('language')}")
print(f"  Category: {entity.get('lexicalCategory')}")
print(f"  Senses: {len(entity.get('senses', []))}")

for i, sense in enumerate(entity.get('senses', []), 1):
    glosses = sense.get('glosses', {})
    gloss_langs = list(glosses.keys())[:5]  # Show first 5 languages
    print(f"    S{i}: {gloss_langs}...")

claims = entity.get('claims', {})
print(f"  Lexeme-level claims:")
print(f"    P4 (Wikidata link): {len(claims.get('P4', []))}")
print(f"    P7 (text): {len(claims.get('P7', []))} - value: '{claims.get('P7', [{}])[0].get('mainsnak', {}).get('datavalue', {}).get('value', 'N/A')}'")
print()
print(f"✓ View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
