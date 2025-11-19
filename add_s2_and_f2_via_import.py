#!/usr/bin/env python3
"""
Add S2 (Second Sense) and F2 (Second Form) via MediaWiki Import
================================================================
Since the API won't allow creating new sense/form IDs:
1. Download all lexeme data
2. Inject S2 sense and F2 form into each
3. Generate XML with corrected nextSenseId/nextFormId
4. Import via MediaWiki
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
PASSWORD = '[REDACTED_SECRET_1]'

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

# Export all lexemes
print("Exporting all 75 lexemes...")
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

print(f"✓ Exported {len(all_lexemes)} lexemes")
print()

print("=" * 80)
print("STEP 2: ADD S2 SENSE AND F2 FORM TO EACH LEXEME")
print("=" * 80)
print()

modified_lexemes = {}
for lex_id, lexeme_data in all_lexemes.items():
    modified = dict(lexeme_data)

    # Get current senses and forms
    senses = modified.get('senses', [])
    forms = modified.get('forms', [])

    # Add S2 sense if it doesn't exist
    if not any(s.get('id') == f'{lex_id}-S2' for s in senses):
        s2_sense = {
            'id': f'{lex_id}-S2',
            'glosses': {
                'en': {
                    'language': 'en',
                    'value': f'Second sense for {lex_id}'
                }
            },
            'claims': []
        }
        senses.append(s2_sense)

    # Add F2 form if it doesn't exist
    if not any(f.get('id') == f'{lex_id}-F2' for f in forms):
        f2_form = {
            'id': f'{lex_id}-F2',
            'representations': {
                'mis': {
                    'language': 'mis',
                    'value': f'form2-{lex_id}'
                }
            },
            'grammaticalFeatures': [],
            'claims': []
        }
        forms.append(f2_form)

    modified['senses'] = senses
    modified['forms'] = forms

    # Calculate nextSenseId and nextFormId
    if senses:
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

    if forms:
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

    # Remove fields that cause import issues
    for field in ['pageid', 'ns', 'title', 'lastrevid', 'modified']:
        if field in modified:
            del modified[field]

    modified_lexemes[lex_id] = modified

print(f"✓ Added S2/F2 to {len(modified_lexemes)} lexemes")
print()

print("=" * 80)
print("STEP 3: GENERATE XML FOR IMPORT")
print("=" * 80)
print()

def create_xml_for_import(lexemes):
    """Create MediaWiki XML for import"""
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
    generator.text = "Aelaki S2/F2 Injector"
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

output_file = "aelaki_lexemes_with_s2_f2.xml"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(xml_string)

print(f"✓ Generated XML: {output_file}")
print(f"  File size: {len(xml_string)} bytes")
print()

print("=" * 80)
print("STEP 4: IMPORT VIA MEDIAWIKI")
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
