#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check how Japanese lexemes are stored on Wikidata."""

import requests
import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Check L5108 specifically
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

params = {
    'action': 'wbgetentities',
    'ids': 'L5108',
    'format': 'json'
}

headers = {
    'User-Agent': 'WiktionaryLexemeBot/1.0 (User:Immanuelle) Python/requests'
}

response = requests.get(WIKIDATA_API, params=params, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response text: {response.text[:200]}")
data = response.json()

if 'entities' in data and 'L5108' in data['entities']:
    lexeme = data['entities']['L5108']

    print("Lexeme L5108 details:")
    print("=" * 60)

    # Get lemmas
    if 'lemmas' in lexeme:
        print("\nLemmas:")
        for lang, lemma_data in lexeme['lemmas'].items():
            print(f"  {lang}: {lemma_data['value']}")

    # Get lexical category
    if 'lexicalCategory' in lexeme:
        print(f"\nLexical category: {lexeme['lexicalCategory']}")

    # Get language
    if 'language' in lexeme:
        print(f"Language: {lexeme['language']}")

    # Get forms
    if 'forms' in lexeme:
        print(f"\nForms ({len(lexeme['forms'])} total):")
        for form in lexeme['forms'][:5]:  # Show first 5
            form_id = form['id']
            reps = form.get('representations', {})
            print(f"  {form_id}:")
            for lang, rep_data in reps.items():
                print(f"    {lang}: {rep_data['value']}")

    print("\n" + "=" * 60)
    print("\nFull lemmas data:")
    print(json.dumps(lexeme.get('lemmas', {}), ensure_ascii=False, indent=2))

# Now test SPARQL query
print("\n\nTesting SPARQL queries:")
print("=" * 60)

SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'

# Try searching for 日本 as lemma
queries = [
    ('Kanji lemma', 'SELECT ?lexeme WHERE { ?lexeme dct:language wd:Q148 ; wikibase:lemma "日本"@ja . } LIMIT 5'),
    ('Hiragana lemma', 'SELECT ?lexeme WHERE { ?lexeme dct:language wd:Q148 ; wikibase:lemma "にほん"@ja . } LIMIT 5'),
    ('Katakana lemma', 'SELECT ?lexeme WHERE { ?lexeme dct:language wd:Q148 ; wikibase:lemma "ニホン"@ja . } LIMIT 5'),
]

for name, query in queries:
    print(f"\n{name}:")
    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={'query': query, 'format': 'json'},
            headers={'User-Agent': 'Test', 'Accept': 'application/sparql-results+json'},
            timeout=10
        )
        results = response.json()
        bindings = results.get('results', {}).get('bindings', [])
        if bindings:
            for binding in bindings:
                lexeme_uri = binding['lexeme']['value']
                print(f"  Found: {lexeme_uri.split('/')[-1]}")
        else:
            print("  No results")
    except Exception as e:
        print(f"  Error: {e}")
