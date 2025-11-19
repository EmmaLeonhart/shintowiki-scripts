#!/usr/bin/env python3
"""
Create English 'cat' Lexeme from Wikidata
==========================================
1. Query Wikidata for the 'cat' lexeme (L7)
2. Extract its data (lemma, senses, forms, language, etc.)
3. Create it on Aelaki with the same structure as L61
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
print("Wikidata L7 structure:")
print(json.dumps(wd_entity, indent=2, ensure_ascii=False)[:1000])
print()

# Extract key data
lemma = wd_entity.get('lemmas', {})
language = wd_entity.get('language', '')
lexical_category = wd_entity.get('lexicalCategory', '')
senses = wd_entity.get('senses', [])
forms = wd_entity.get('forms', [])

print("=" * 80)
print("EXTRACTED DATA")
print("=" * 80)
print(f"Lemmas: {lemma}")
print(f"Language: {language}")
print(f"Lexical Category: {lexical_category}")
print(f"Senses: {len(senses)}")
print(f"Forms: {len(forms)}")
print()

# Show first sense and form
if senses:
    print(f"First sense (S1):")
    print(json.dumps(senses[0], indent=2, ensure_ascii=False)[:500])
    print()

if forms:
    print(f"First form (F1):")
    print(json.dumps(forms[0], indent=2, ensure_ascii=False)[:500])
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
# Use same structure as L61
aelaki_lexeme_data = {
    'type': 'lexeme',
    'lemmas': lemma,  # Use English lemmas from Wikidata
    'language': language,  # Use same language
    'lexicalCategory': lexical_category,  # Use same category
    'senses': [],
    'forms': []
}

# Add first sense (S1) with a definition
if senses:
    first_sense = senses[0]
    s1 = {
        'glosses': {
            'en': {
                'language': 'en',
                'value': first_sense.get('glosses', {}).get('en', {}).get('value', 'A feline mammal')
            }
        },
        'claims': []
    }
    aelaki_lexeme_data['senses'].append(s1)

# Add first form (F1) with representation
if forms:
    first_form = forms[0]
    f1 = {
        'representations': first_form.get('representations', {
            'en': {
                'language': 'en',
                'value': 'cat'
            }
        }),
        'grammaticalFeatures': first_form.get('grammaticalFeatures', []),
        'claims': []
    }
    aelaki_lexeme_data['forms'].append(f1)

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
    print(f"  Senses: {len(entity.get('senses', []))}")
    print(f"  Forms: {len(entity.get('forms', []))}")
    print()
    print(f"View at: https://aelaki.miraheze.org/wiki/Lexeme:{new_lex_id}")
else:
    print(f"? Unexpected response: {str(result)[:200]}")
