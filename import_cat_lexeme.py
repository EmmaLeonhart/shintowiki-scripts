#!/usr/bin/env python3
"""
Import Wikidata 'cat' Lexeme (L7) to Aelaki
============================================
Imports L7 with correct category mapping:
- Wikidata Q1084 (noun) -> Aelaki Q20 (Noun)
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
PASSWORD = '[REDACTED_SECRET_2]'

print("=" * 80)
print("IMPORT WIKIDATA L7 (CAT) TO AELAKI")
print("=" * 80)
print()

print("=" * 80)
print("STEP 1: FETCH L7 FROM WIKIDATA")
print("=" * 80)
print()

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

r = session.get(WIKIDATA_API, params={
    'action': 'wbgetentities',
    'ids': 'L7',
    'format': 'json'
})

wd_entity = r.json()['entities']['L7']

lemma_value = wd_entity.get('lemmas', {}).get('en', {}).get('value', 'cat')
wd_category = wd_entity.get('lexicalCategory', 'Q1084')
senses = wd_entity.get('senses', [])

# Map Wikidata category to Aelaki
# Wikidata Q1084 (noun) -> Aelaki Q20 (Noun)
aelaki_category = 'Q20' if wd_category == 'Q1084' else 'Q9'

print(f"✓ Fetched L7 from Wikidata")
print(f"  Lemma: {lemma_value}")
print(f"  Wikidata Category: {wd_category}")
print(f"  Mapped to Aelaki Category: {aelaki_category}")
print(f"  Senses: {len(senses)}")
print()

print("=" * 80)
print("STEP 2: AUTHENTICATE WITH AELAKI")
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

print("=" * 80)
print("STEP 3: CREATE BARE LEXEME")
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
    'lexicalCategory': aelaki_category  # Q20 (Noun)
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
print(f"  Category: {aelaki_category} (Noun)")
print()

time.sleep(0.5)

print("=" * 80)
print("STEP 4: ADD SENSES")
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
        gloss_langs = list(glosses.keys())[:8]
        print(f"  S{i}: {gloss_langs}...")
else:
    print(f"✗ Error adding senses: {result.get('error', {}).get('code')}")

print()
time.sleep(0.5)

print("=" * 80)
print("STEP 5: ADD P4 (WIKIDATA LINK) AND P7 (LEMMA TEXT)")
print("=" * 80)
print()

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
    p7_value = claims.get('P7', [{}])[0].get('mainsnak', {}).get('datavalue', {}).get('value', 'N/A')
    print(f"✓ Added lexeme-level claims:")
    print(f"  P4 (Wikidata link): {p4_count} claim -> L7")
    print(f"  P7 (text): {p7_count} claim -> '{p7_value}'")
else:
    print(f"✗ Error adding claims: {result.get('error', {}).get('code')}")

print()

print("=" * 80)
print("SUCCESS!")
print("=" * 80)
print()

print(f"✓ Imported Wikidata L7 (cat) to Aelaki {new_lex_id}")
print()
print(f"Lexeme Details:")
print(f"  ID: {new_lex_id}")
print(f"  Lemma: {lemma_value}")
print(f"  Language: Q3 (English)")
print(f"  Lexical Category: {aelaki_category} (Noun)")
print(f"  Senses: {len(senses)}")
print(f"  P4 Link: L7 (Wikidata)")
print(f"  P7 Text: {lemma_value}")
print()
print(f"View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
