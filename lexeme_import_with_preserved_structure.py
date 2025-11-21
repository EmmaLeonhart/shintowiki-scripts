#!/usr/bin/env python3
"""
Lexeme Import with Preserved Structure
========================================
Use the ACTUAL exported lexeme structure from wbgetentities,
just inject dummy senses/forms into it, and keep everything else intact.
Don't remove ANY fields - the import might need them for validation.
"""

import requests
import json
import sys
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = 'https://aelaki.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

print("=" * 80)
print("STEP 1: AUTHENTICATE AND EXPORT ALL LEXEMES")
print("=" * 80)
print()

# Login
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']

r = session.post(API_URL, data={
    'action': 'login',
    'lgname': USERNAME,
    'lgpassword': PASSWORD,
    'lgtoken': login_token,
    'format': 'json'
})

r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']

print("✓ Authenticated")
print()

# Export all lexemes with FULL structure (keep all fields)
print("Exporting all 75 lexemes with full structure...")
lex_ids = [f"L{i}" for i in range(1, 76)]
batch_size = 50

all_lexemes = {}
for batch_start in range(0, len(lex_ids), batch_size):
    batch = lex_ids[batch_start:batch_start + batch_size]
    batch_ids = "|".join(batch)

    r = session.get(API_URL, params={
        'action': 'wbgetentities',
        'ids': batch_ids,
        'format': 'json'
    })

    entities = r.json().get('entities', {})
    all_lexemes.update(entities)

print(f"✓ Exported {len(all_lexemes)} lexemes with full structure")
print()

print("=" * 80)
print("STEP 2: EXTRACT L61/L62 TEMPLATES")
print("=" * 80)
print()

l61_template = all_lexemes.get('L61', {})
l62_template = all_lexemes.get('L62', {})

l61_senses = l61_template.get('senses', [])
l61_forms = l61_template.get('forms', [])

print(f"L61 has {len(l61_senses)} senses, {len(l61_forms)} forms")
print(f"L62 has {len(l62_template.get('senses', []))} senses, {len(l62_template.get('forms', []))} forms")
print()

def create_dummy_sense(lex_id):
    """Create a dummy sense based on L61 structure"""
    return {
        'id': f'{lex_id}-S1',
        'glosses': {
            'en': {
                'language': 'en',
                'value': f'Sense for {lex_id}'
            }
        },
        'claims': []
    }

def create_dummy_form(lex_id):
    """Create a dummy form based on L61 structure"""
    return {
        'id': f'{lex_id}-F1',
        'representations': {
            'mis': {
                'language': 'mis',
                'value': f'form-{lex_id}'
            }
        },
        'grammaticalFeatures': [],
        'claims': []
    }

print("=" * 80)
print("STEP 3: ADD DUMMY SENSES/FORMS TO ALL LEXEMES")
print("=" * 80)
print()

modified_lexemes = {}
for lex_id, lexeme_data in all_lexemes.items():
    # PRESERVE ALL ORIGINAL FIELDS
    modified = dict(lexeme_data)

    # Add dummy sense if it doesn't have one
    if not modified.get('senses'):
        modified['senses'] = [create_dummy_sense(lex_id)]

    # Add nextSenseId if we have senses
    if modified.get('senses'):
        senses = modified['senses']
        max_sense_num = 0
        for sense in senses:
            sense_id = sense.get('id', '')
            if '-' in sense_id:
                num_part = sense_id.split('-')[-1]
                if num_part.startswith('S'):
                    try:
                        num = int(num_part[1:])
                        max_sense_num = max(max_sense_num, num)
                    except:
                        pass
        modified['nextSenseId'] = max_sense_num + 1

    # Add dummy form if it doesn't have one
    if not modified.get('forms'):
        modified['forms'] = [create_dummy_form(lex_id)]

    # Add nextFormId if we have forms
    if modified.get('forms'):
        forms = modified['forms']
        max_form_num = 0
        for form in forms:
            form_id = form.get('id', '')
            if '-' in form_id:
                num_part = form_id.split('-')[-1]
                if num_part.startswith('F'):
                    try:
                        num = int(num_part[1:])
                        max_form_num = max(max_form_num, num)
                    except:
                        pass
        modified['nextFormId'] = max_form_num + 1

    modified_lexemes[lex_id] = modified

print(f"✓ Added dummy senses/forms to {len(modified_lexemes)} lexemes")
print()

print("=" * 80)
print("STEP 4: GENERATE XML WITH FULL STRUCTURE PRESERVED")
print("=" * 80)
print()

def create_xml_for_import(lexemes):
    """Create MediaWiki XML for import with preserved structure"""
    root = ET.Element("mediawiki")
    root.set("xmlns", "http://www.mediawiki.org/xml/export-0.11/")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:schemaLocation", "http://www.mediawiki.org/xml/export-0.11/ http://www.mediawiki.org/xml/export-0.11.xsd")
    root.set("version", "0.11")

    # Siteinfo
    siteinfo = ET.SubElement(root, "siteinfo")
    sitename = ET.SubElement(siteinfo, "sitename")
    sitename.text = "Aelaki"
    dbname = ET.SubElement(siteinfo, "dbname")
    dbname.text = "aelaki"
    base = ET.SubElement(siteinfo, "base")
    base.text = "https://aelaki.miraheze.org/"
    generator = ET.SubElement(siteinfo, "generator")
    generator.text = "Aelaki Lexeme Import with Preserved Structure"
    case = ET.SubElement(siteinfo, "case")
    case.text = "first-letter"

    namespaces = ET.SubElement(siteinfo, "namespaces")
    ns_lexeme = ET.SubElement(namespaces, "namespace")
    ns_lexeme.set("key", "146")
    ns_lexeme.set("case", "first-letter")
    ns_lexeme.text = "Lexeme"

    # Pages
    for lex_id, entity in lexemes.items():
        page = ET.SubElement(root, "page")

        title = ET.SubElement(page, "title")
        title.text = f"Lexeme:{lex_id}"

        ns = ET.SubElement(page, "ns")
        ns.text = "146"

        id_elem = ET.SubElement(page, "id")
        id_elem.text = "0"

        revision = ET.SubElement(page, "revision")

        format = ET.SubElement(revision, "format")
        format.text = "application/json"

        text = ET.SubElement(revision, "text")
        text.text = json.dumps(entity, ensure_ascii=False)
        text.set("bytes", str(len(json.dumps(entity))))

    return root

xml_root = create_xml_for_import(modified_lexemes)
xml_string = minidom.parseString(ET.tostring(xml_root)).toprettyxml(indent="  ")
lines = xml_string.split('\n')
xml_string = '\n'.join([line for line in lines[1:] if line.strip()])

output_file = "aelaki_lexemes_import_preserved_structure.xml"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(xml_string)

print(f"✓ Generated XML: {output_file}")
print(f"  File size: {len(xml_string)} bytes")
print()

print("=" * 80)
print("STEP 5: IMPORT VIA MEDIAWIKI")
print("=" * 80)
print()

with open(output_file, 'rb') as f:
    xml_file = f.read()

files = {
    'xml': (output_file, xml_file, 'application/xml')
}

data = {
    'action': 'import',
    'interwikiprefix': 'local',
    'token': csrf_token,
    'format': 'json'
}

print("Sending import request...")
r = session.post(API_URL, files=files, data=data)

try:
    result = r.json()
    if 'error' in result:
        error = result['error']
        print(f"✗ Import error: {error.get('code')}")
        print(f"  {error.get('info')}")
    elif 'import' in result:
        print(f"✓ Import succeeded!")
        import_result = result['import']
        if isinstance(import_result, list):
            print(f"  {len(import_result)} pages imported")
    else:
        print(f"? Response: {str(result)[:200]}")
except Exception as e:
    print(f"✗ Error parsing response: {str(e)[:100]}")

print()
print("Done!")
