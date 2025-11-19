#!/usr/bin/env python3
"""
Import Wikidata Lexeme L4164
=============================
Fetches L4164 from Wikidata and imports to Aelaki with:
- Correct lemma and language
- All senses with multilingual glosses
- Lexical category mapping (Q1084->Q20, Q24905->Q22)
- P4 link to Wikidata L4164
- P7 with lemma text
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

# Category mapping
CATEGORY_MAPPING = {
    'Q1084': 'Q20',      # noun -> Noun
    'Q24905': 'Q22'      # verb -> Verb
}

def map_category(wd_category):
    """Map Wikidata category to Aelaki category"""
    return CATEGORY_MAPPING.get(wd_category, 'Q9')

print("=" * 80)
print("IMPORT WIKIDATA L4164 TO AELAKI")
print("=" * 80)
print()

print("=" * 80)
print("STEP 1: FETCH L4164 FROM WIKIDATA")
print("=" * 80)
print()

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

r = session.get(WIKIDATA_API, params={
    'action': 'wbgetentities',
    'ids': 'L4164',
    'format': 'json'
})

wd_entity = r.json()['entities']['L4164']

if 'missing' in wd_entity:
    print("✗ L4164 not found on Wikidata")
    sys.exit(1)

lemma_value = wd_entity.get('lemmas', {}).get('en', {}).get('value', '')
if not lemma_value:
    lemmas = wd_entity.get('lemmas', {})
    if lemmas:
        lemma_value = list(lemmas.values())[0].get('value', 'L4164')

wd_category = wd_entity.get('lexicalCategory', 'Q9')
aelaki_category = map_category(wd_category)
senses = wd_entity.get('senses', [])
wd_language = wd_entity.get('language', 'Q1860')

print(f"✓ Fetched L4164 from Wikidata")
print(f"  Lemma: {lemma_value}")
print(f"  Wikidata Language: {wd_language}")
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

print("=" * 80)
print("STEP 4: ADD SENSES")
print("=" * 80)
print()

if senses:
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
            print(f"  S{i}: {gloss_langs}..." if len(glosses) > 6 else f"  S{i}: {gloss_langs}")
    else:
        print(f"✗ Error adding senses: {result.get('error', {}).get('code')}")
else:
    print("⊘ No senses to add")

print()
time.sleep(0.5)

print("=" * 80)
print("STEP 5: ADD P4 AND P7 CLAIMS")
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
                        'value': 'L4164',
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
    print(f"  P4 (Wikidata link): {p4_count} claim -> L4164")
    print(f"  P7 (text): {p7_count} claim -> '{p7_value}'")
else:
    print(f"✗ Error adding claims: {result.get('error', {}).get('code')}")

print()

print("=" * 80)
print("SUCCESS!")
print("=" * 80)
print()

print(f"✓ Imported Wikidata L4164 to Aelaki {new_lex_id}")
print()
print(f"Lexeme Details:")
print(f"  ID: {new_lex_id}")
print(f"  Lemma: {lemma_value}")
print(f"  Language: Q3 (English)")
print(f"  Lexical Category: {aelaki_category}")
print(f"  Senses: {len(senses)}")
print(f"  P4 Link: L4164 (Wikidata)")
print(f"  P7 Text: {lemma_value}")
print()
print(f"View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
