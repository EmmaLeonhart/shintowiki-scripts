#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check Wikidata for cat lexemes."""

import requests
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'

queries = [
    ('Hiragana ねこ', 'SELECT ?lexeme WHERE { ?lexeme dct:language wd:Q148 ; wikibase:lemma "ねこ"@ja ; wikibase:lexicalCategory wd:Q1084 . }'),
    ('Katakana ネコ', 'SELECT ?lexeme WHERE { ?lexeme dct:language wd:Q148 ; wikibase:lemma "ネコ"@ja ; wikibase:lexicalCategory wd:Q1084 . }'),
    ('Kanji 猫', 'SELECT ?lexeme WHERE { ?lexeme dct:language wd:Q148 ; wikibase:lemma "猫"@ja ; wikibase:lexicalCategory wd:Q1084 . }'),
]

for name, query in queries:
    print(f"{name}:")
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
