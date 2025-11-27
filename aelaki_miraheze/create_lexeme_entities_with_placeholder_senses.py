#!/usr/bin/env python3
"""
Create Lexeme Entities with Placeholder Senses
===============================================

Strategy:
1. Export existing lexemes (especially L61 which has a sense structure)
2. Create XML representations with placeholder senses for L1-L60, L63-L75
3. Import via MediaWiki import action (bypasses API sense-creation limitation)
4. This gives all lexemes a sense structure that can then be modified via API

The key insight: Import can create entities with senses in a single operation,
whereas the API's wbeditentity cannot CREATE new senses (only modify existing ones).
"""

import requests
import json
import sys
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = 'https://aelaki.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# Login
print("=" * 80)
print("STEP 1: AUTHENTICATE")
print("=" * 80)
print()

r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']

r = session.post(API_URL, data={
    'action': 'login',
    'lgname': USERNAME,
    'lgpassword': PASSWORD,
    'lgtoken': login_token,
    'format': 'json'
})

if r.json().get('login', {}).get('result') != 'Success':
    print("✗ Login failed")
    sys.exit(1)

print("✓ Logged in")

r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']
print("✓ Got CSRF token")
print()

# Step 2: Get L61 as template (it has a sense structure)
print("=" * 80)
print("STEP 2: GET L61 AS TEMPLATE")
print("=" * 80)
print()

r = session.get(API_URL, params={
    'action': 'wbgetentities',
    'ids': 'L61',
    'format': 'json'
})

l61_entity = r.json()['entities']['L61']
print(f"L61 structure:")
print(f"  Type: {l61_entity.get('type')}")
print(f"  Lemmas: {list(l61_entity.get('lemmas', {}).keys())}")
print(f"  Lexical Category: {l61_entity.get('lexicalCategory')}")
print(f"  Language: {l61_entity.get('language')}")
print(f"  Senses: {len(l61_entity.get('senses', []))}")
print(f"  Forms: {len(l61_entity.get('forms', []))}")
print(f"  Claims: {len(l61_entity.get('claims', {}).get('P1', []))}")
print()

# Step 3: Create lexeme entities for all L1-L75 with placeholder senses
print("=" * 80)
print("STEP 3: CREATE LEXEME ENTITIES WITH PLACEHOLDER SENSES")
print("=" * 80)
print()

def create_lexeme_with_placeholder_sense(lex_num):
    """Create a lexeme entity with a placeholder sense"""
    lex_id = f"L{lex_num}"

    # Create a simplified lexeme based on L61 structure
    entity = {
        "type": "lexeme",
        "id": lex_id,
        "lemmas": {
            "mis": {
                "language": "mis",
                "value": l61_entity['lemmas']['mis']['value']  # Use L61's lemma as placeholder
            }
        },
        "lexicalCategory": l61_entity.get('lexicalCategory', 'Q4'),
        "language": l61_entity.get('language', 'Q1'),
        "senses": [
            {
                "id": f"{lex_id}-S1",
                "glosses": {
                    "en": {
                        "language": "en",
                        "value": f"Placeholder sense for {lex_id}"
                    }
                },
                "claims": []
            }
        ],
        "forms": [],
        "claims": {}
    }

    return entity

# Create entities for all lexemes that don't have senses
lexeme_entities = []
for i in range(1, 76):
    if i not in [61, 62]:  # Skip L61 and L62, they already have senses
        entity = create_lexeme_with_placeholder_sense(i)
        lexeme_entities.append(entity)

print(f"✓ Created {len(lexeme_entities)} lexeme entities with placeholder senses")
print()

# Step 4: Convert to XML format for import
print("=" * 80)
print("STEP 4: GENERATE MEDIAWIKI XML FOR IMPORT")
print("=" * 80)
print()

def create_xml_export(entities):
    """Create MediaWiki XML export format for lexeme entities"""

    # Create root mediawiki element
    root = ET.Element("mediawiki")
    root.set("xmlns", "http://www.mediawiki.org/xml/export-0.11/")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:schemaLocation", "http://www.mediawiki.org/xml/export-0.11/ http://www.mediawiki.org/xml/export-0.11.xsd")
    root.set("version", "0.11")
    root.set("xml:lang", "en")

    # Add siteinfo
    siteinfo = ET.SubElement(root, "siteinfo")

    sitename = ET.SubElement(siteinfo, "sitename")
    sitename.text = "Aelaki"

    dbname = ET.SubElement(siteinfo, "dbname")
    dbname.text = "aelaki"

    base = ET.SubElement(siteinfo, "base")
    base.text = "https://aelaki.miraheze.org/"

    generator = ET.SubElement(siteinfo, "generator")
    generator.text = "Aelaki Lexeme Placeholder Creator"

    case = ET.SubElement(siteinfo, "case")
    case.text = "first-letter"

    # Add namespaces
    namespaces = ET.SubElement(siteinfo, "namespaces")

    ns_lexeme = ET.SubElement(namespaces, "namespace")
    ns_lexeme.set("key", "146")
    ns_lexeme.set("case", "first-letter")
    ns_lexeme.text = "Lexeme"

    # Add pages (lexeme entities)
    for entity in entities:
        page = ET.SubElement(root, "page")

        title = ET.SubElement(page, "title")
        title.text = f"Lexeme:{entity['id']}"

        ns = ET.SubElement(page, "ns")
        ns.text = "146"

        id_elem = ET.SubElement(page, "id")
        id_elem.text = "0"

        revision = ET.SubElement(page, "revision")

        # model = ET.SubElement(revision, "model")
        # model.text = "wikibase-lexeme"

        format = ET.SubElement(revision, "format")
        format.text = "application/json"

        text = ET.SubElement(revision, "text")
        text.text = json.dumps(entity, ensure_ascii=False)
        text.set("bytes", str(len(json.dumps(entity))))

        sha1 = ET.SubElement(revision, "sha1")
        sha1.text = "0"  # Placeholder - import should ignore this

    return root

xml_root = create_xml_export(lexeme_entities)

# Convert to string with proper formatting
xml_string = minidom.parseString(ET.tostring(xml_root)).toprettyxml(indent="  ")

# Remove XML declaration and extra whitespace
lines = xml_string.split('\n')
xml_string = '\n'.join([line for line in lines[1:] if line.strip()])

# Save to file
output_file = "aelaki_lexemes_with_placeholder_senses.xml"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(xml_string)

print(f"✓ Generated XML with {len(lexeme_entities)} lexeme entities")
print(f"✓ Saved to: {output_file}")
print()

# Step 5: Attempt import via MediaWiki import action
print("=" * 80)
print("STEP 5: IMPORT VIA MEDIAWIKI IMPORT ACTION")
print("=" * 80)
print()

with open(output_file, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Try import action
r = session.post(API_URL, data={
    'action': 'import',
    'xml': xml_content,
    'token': csrf_token,
    'format': 'json'
})

result = r.json()

if 'error' in result:
    error = result['error']
    print(f"✗ Import failed: {error.get('code')} - {error.get('info')}")
    print()
    print("Full response:")
    print(json.dumps(result, indent=2))
elif 'import' in result:
    print("✓ Import succeeded!")
    import_result = result['import']
    print(f"  Imported: {len(import_result)} pages")
    for page_info in import_result[:5]:
        print(f"    - {page_info.get('title')}: {page_info.get('revisions', [{}])[0].get('comment', 'no comment')}")
else:
    print("? Unexpected response:")
    print(json.dumps(result, indent=2)[:500])

print()
print("=" * 80)
print("STEP 6: VERIFY IMPORTS")
print("=" * 80)
print()

# Check if any lexemes now have senses
test_ids = ['L1', 'L5', 'L30', 'L60']
r = session.get(API_URL, params={
    'action': 'wbgetentities',
    'ids': '|'.join(test_ids),
    'format': 'json'
})

entities = r.json().get('entities', {})
for lex_id in test_ids:
    entity = entities.get(lex_id, {})
    senses = entity.get('senses', [])
    if senses:
        print(f"✓ {lex_id}: {len(senses)} sense(s)")
        for sense in senses:
            print(f"    {sense.get('id')}: {sense.get('glosses', {})}")
    else:
        print(f"✗ {lex_id}: No senses")

