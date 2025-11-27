#!/usr/bin/env python3
"""
Import Wikidata Lexemes with Category Mapping
==============================================
Maps Wikidata lexical categories to Aelaki equivalents:
- Wikidata Q1084 (noun) -> Aelaki Q20 (Noun)
- Wikidata Q24905 (verb) -> Aelaki Q22 (Verb)

Creates lexeme with:
1. Lemma and language (Q3 for English)
2. All senses from Wikidata
3. P4 link to Wikidata lexeme
4. P7 with lemma text at lexeme level
5. Correct lexical category mapping
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

# Category mapping: Wikidata -> Aelaki
CATEGORY_MAPPING = {
    'Q1084': 'Q20',      # noun -> Noun
    'Q24905': 'Q22',     # verb -> Verb
    'Q34698': 'Q25',     # adjective -> Adjective
    'Q380057': 'Q26'     # adverb -> Adverb
}

def map_category(wd_category):
    """Map Wikidata category to Aelaki category"""
    return CATEGORY_MAPPING.get(wd_category, 'Q9')  # Default to Q9 if not found

def import_wikidata_lexeme(wd_lexeme_id, aelaki_session, csrf_token):
    """Import a single Wikidata lexeme to Aelaki"""

    print(f"\n{'='*80}")
    print(f"Importing {wd_lexeme_id}")
    print(f"{'='*80}\n")

    # Fetch from Wikidata
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    r = session.get(WIKIDATA_API, params={
        'action': 'wbgetentities',
        'ids': wd_lexeme_id,
        'format': 'json'
    })

    wd_entity = r.json()['entities'][wd_lexeme_id]

    if 'missing' in wd_entity:
        print(f"✗ {wd_lexeme_id} not found on Wikidata")
        return None

    lemma_value = wd_entity.get('lemmas', {}).get('en', {}).get('value', '')
    if not lemma_value:
        # Try any language
        lemmas = wd_entity.get('lemmas', {})
        if lemmas:
            lemma_value = list(lemmas.values())[0].get('value', wd_lexeme_id)

    wd_category = wd_entity.get('lexicalCategory', 'Q9')
    aelaki_category = map_category(wd_category)
    senses = wd_entity.get('senses', [])

    print(f"✓ Fetched {wd_lexeme_id} from Wikidata")
    print(f"  Lemma: {lemma_value}")
    print(f"  Wikidata Category: {wd_category}")
    print(f"  Mapped to Aelaki: {aelaki_category}")
    print(f"  Senses: {len(senses)}")
    print()

    # Step 1: Create bare lexeme
    aelaki_lexeme_data = {
        'type': 'lexeme',
        'lemmas': {
            'en': {
                'language': 'en',
                'value': lemma_value
            }
        },
        'language': 'Q3',  # English
        'lexicalCategory': aelaki_category  # Mapped category
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
        return None

    new_lex_id = result['entity']['id']
    print(f"✓ Created bare lexeme: {new_lex_id}")
    time.sleep(0.3)

    # Step 2: Add senses using "add" syntax
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
            senses_count = len(result['entity'].get('senses', []))
            print(f"✓ Added {senses_count} senses")
        else:
            print(f"✗ Error adding senses: {result.get('error', {}).get('code')}")

        time.sleep(0.3)

    # Step 3: Add P4 (Wikidata link) and P7 (lemma text)
    edit_data = {
        'claims': {
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
        print(f"✓ Added P4 and P7 claims")
    else:
        print(f"✗ Error adding claims: {result.get('error', {}).get('code')}")

    print(f"\n✓ Success! Lexeme {new_lex_id} created")
    print(f"  View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")

    return new_lex_id

# Main
print("=" * 80)
print("AUTHENTICATE WITH AELAKI")
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

# Import example lexemes with different categories
print("=" * 80)
print("IMPORTING WIKIDATA LEXEMES")
print("=" * 80)

lexemes_to_import = [
    ('L7', 'English cat (noun)'),    # Q1084 = noun
    ('L8', 'English tree (noun)'),   # Q1084 = noun
    ('L3', 'English run (verb)'),    # Q24905 = verb
]

created_lexemes = []
for wd_id, description in lexemes_to_import:
    print(f"\nImporting: {description}")
    result = import_wikidata_lexeme(wd_id, aelaki_session, csrf_token)
    if result:
        created_lexemes.append((wd_id, result, description))
    time.sleep(0.5)

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

if created_lexemes:
    print(f"✓ Successfully imported {len(created_lexemes)} lexemes:\n")
    for wd_id, aelaki_id, description in created_lexemes:
        print(f"  {wd_id} -> {aelaki_id}: {description}")
        print(f"    https://aelaki.miraheze.org/wiki/Lexeme:{aelaki_id}")
else:
    print("✗ No lexemes imported")
