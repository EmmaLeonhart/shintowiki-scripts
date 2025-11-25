#!/usr/bin/env python3
"""generate_shikinaisha_pages_v24_local_storage.py
================================================
V24: Local XML storage + batch upload approach
Uses the same page generation logic as v24_individual_edits
Generates all XML locally, saves to disk, creates CSV manifest, then uploads

To verify output matches v24_individual_edits.py, compare generated page content
"""

import mwclient
import requests
import sys
import time
import re
import os
import csv
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

PROPERTIES_TO_IGNORE = ['P11250']
PROPERTIES_TO_OMIT = ['P1448', 'P2671']

# Output directories
OUTPUT_DIR = 'output_xml_v24'
MANIFEST_FILE = 'pages_manifest_v24.csv'
PROPERTY_LABELS_CACHE = 'property_labels_cache.csv'

# Load property labels cache
PROPERTY_LABELS = {}
if os.path.exists(PROPERTY_LABELS_CACHE):
    print(f"Loading property labels cache from {PROPERTY_LABELS_CACHE}...")
    try:
        with open(PROPERTY_LABELS_CACHE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                PROPERTY_LABELS[row['property_id']] = row['label']
        print(f"Loaded {len(PROPERTY_LABELS)} cached property labels\n")
    except Exception as e:
        print(f"Warning: Could not load property labels cache: {e}\n")
else:
    print(f"Warning: Property labels cache file not found: {PROPERTY_LABELS_CACHE}")
    print("Run fetch_property_labels.py first to create cache\n")

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API)\n")

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created output directory: {OUTPUT_DIR}\n")

# ═══ SHARED HELPER FUNCTIONS (same as v24_individual_edits) ═══

def get_wikidata_entity(qid):
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if 'entities' in data and qid in data['entities']:
            return data['entities'][qid]
        return None
    except Exception as e:
        print(f"     ! Error fetching {qid}: {e}")
        return None

def get_property_value(entity, property_id):
    if not entity or 'claims' not in entity:
        return None
    claims = entity.get('claims', {})
    prop_claims = claims.get(property_id, [])
    if not prop_claims:
        return None
    claim = prop_claims[0]
    mainsnak = claim.get('mainsnak', {})
    datavalue = mainsnak.get('datavalue', {})
    return datavalue.get('value')

def get_label(entity, lang='en'):
    if not entity:
        return None
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    return None

def get_sitelinks(entity):
    sitelinks = {}
    if entity and 'sitelinks' in entity:
        for site_code, site_data in entity['sitelinks'].items():
            sitelinks[site_code] = site_data.get('title', '')
    return sitelinks

def get_all_property_claims(entity):
    if not entity or 'claims' not in entity:
        return {}
    return entity.get('claims', {})

def extract_province_from_p361(entity):
    p361_claims = entity.get('claims', {}).get('P361', [])
    for claim in p361_claims:
        datavalue = claim.get('mainsnak', {}).get('datavalue', {})
        if isinstance(datavalue.get('value'), dict):
            list_qid = datavalue['value'].get('id')
            if list_qid:
                list_entity = get_wikidata_entity(list_qid)
                list_label = get_label(list_entity)
                if list_label:
                    match = re.match(r'List of Shikinaisha in (.+)$', list_label)
                    if match:
                        province = match.group(1)
                        return province, list_label
    return None, None

def format_wikidata_link(entity, qid):
    sitelinks = get_sitelinks(entity)
    first_link = None
    if 'shintowiki' in sitelinks:
        first_link = sitelinks['shintowiki']
    elif 'enwiki' in sitelinks:
        first_link = sitelinks['enwiki']
    else:
        first_link = get_label(entity, 'en') or qid
    en_label = get_label(entity, 'en') or qid
    wd_link = f"{{{{ill|{first_link}|lt={en_label}"
    for lang_code in sorted(sitelinks.keys()):
        if lang_code != 'commonswiki':
            lang = lang_code.replace('wiki', '')
            title = sitelinks[lang_code]
            wd_link += f"|{lang}|{title}"
    wd_link += f"|WD={qid}}}}}"
    return wd_link

def get_property_heading(property_id):
    """Get heading text for a property in format: EN_LABEL (PID)
    Uses cached property labels to avoid API calls.
    """
    # Check cache first (no API call needed)
    if property_id in PROPERTY_LABELS:
        label = PROPERTY_LABELS[property_id]
        return f"{label} ({property_id})"

    # Fallback if not in cache
    return f"{property_id} ({property_id})"

def get_source_reference_with_url(claim):
    references = claim.get('references', [])
    if not references:
        return None
    for ref in references:
        ref_snaks = ref.get('snaks', {})
        url = None
        if 'P854' in ref_snaks:
            for snak in ref_snaks['P854']:
                datavalue = snak.get('datavalue', {})
                url = datavalue.get('value')
                if url:
                    source_label = None
                    source_qid = None
                    if 'P248' in ref_snaks:
                        for source_snak in ref_snaks['P248']:
                            source_datavalue = source_snak.get('datavalue', {})
                            if isinstance(source_datavalue.get('value'), dict):
                                source_qid = source_datavalue['value'].get('id')
                                if source_qid:
                                    source_entity = get_wikidata_entity(source_qid)
                                    if source_entity:
                                        source_label = get_label(source_entity)
                                        break
                    if source_label and source_qid:
                        return f"{source_label} ({source_qid}) {url}"
                    elif source_label:
                        return f"{source_label} {url}"
                    else:
                        return url
            if url:
                break
        if 'P248' in ref_snaks:
            source_label = None
            source_qid = None
            source_url = None
            for source_snak in ref_snaks['P248']:
                source_datavalue = source_snak.get('datavalue', {})
                if isinstance(source_datavalue.get('value'), dict):
                    source_qid = source_datavalue['value'].get('id')
                    if source_qid:
                        source_entity = get_wikidata_entity(source_qid)
                        if source_entity:
                            source_label = get_label(source_entity)
                            break
            if 'P2699' in ref_snaks:
                for url_snak in ref_snaks['P2699']:
                    datavalue = url_snak.get('datavalue', {})
                    source_url = datavalue.get('value')
                    if source_url:
                        break
            if not source_url and source_qid:
                source_entity = get_wikidata_entity(source_qid)
                if source_entity:
                    source_claims = source_entity.get('claims', {})
                    p2699_claims = source_claims.get('P2699', [])
                    if p2699_claims:
                        source_dataval = p2699_claims[0].get('mainsnak', {}).get('datavalue', {})
                        source_url = source_dataval.get('value')
            if source_url and source_label and source_qid:
                return f"{source_label} ({source_qid}) {source_url}"
            elif source_url and source_label:
                return f"{source_label} {source_url}"
            elif source_url:
                return source_url
            elif source_label:
                return source_label
    return None

def format_qualifier_value(qualifier_value):
    if isinstance(qualifier_value, dict) and 'id' in qualifier_value:
        qid = qualifier_value['id']
        ref_entity = get_wikidata_entity(qid)
        return format_wikidata_link(ref_entity or {}, qid)
    if isinstance(qualifier_value, str):
        return qualifier_value
    return str(qualifier_value)

def get_qualifiers_text(claim):
    qualifiers = claim.get('qualifiers', {})
    qualifier_lines = []
    if not qualifiers:
        return qualifier_lines
    qualifier_labels = {
        'P580': 'Start time',
        'P582': 'End time',
        'P585': 'Point in time',
        'P407': 'Language of work',
        'P1545': 'Series ordinal',
        'P813': 'Retrieved',
        'P854': 'Reference URL',
    }
    for qualifier_id, qualifier_claims in qualifiers.items():
        for qualifier_claim in qualifier_claims:
            qualifier_datavalue = qualifier_claim.get('datavalue', {})
            qualifier_value = qualifier_datavalue.get('value')
            if qualifier_value:
                qual_label = qualifier_labels.get(qualifier_id, qualifier_id)
                formatted_qual_value = format_qualifier_value(qualifier_value)
                qualifier_lines.append(f"** {qual_label}: {formatted_qual_value}")
    return qualifier_lines

def format_claim_value(claim, entity, property_id=None):
    mainsnak = claim.get('mainsnak', {})
    datavalue = mainsnak.get('datavalue', {})
    value = datavalue.get('value')
    if not value:
        return None, [], None
    if isinstance(value, dict) and 'id' in value:
        qid = value['id']
        ref_entity = get_wikidata_entity(qid)
        formatted = format_wikidata_link(ref_entity or {}, qid)
        qualifiers = get_qualifiers_text(claim)
        source = get_source_reference_with_url(claim)
        return formatted, qualifiers, source
    if isinstance(value, str):
        qualifiers = get_qualifiers_text(claim)
        source = get_source_reference_with_url(claim)
        return value, qualifiers, source
    if isinstance(value, dict) and 'latitude' in value and 'longitude' in value:
        lat = value['latitude']
        lon = value['longitude']
        formatted = f"{{{{coord|{lat}|{lon}}}}}"
        qualifiers = get_qualifiers_text(claim)
        source = get_source_reference_with_url(claim)
        return formatted, qualifiers, source
    formatted = str(value)
    qualifiers = get_qualifiers_text(claim)
    source = get_source_reference_with_url(claim)
    return formatted, qualifiers, source

def format_page_content(page_name, qid, entity):
    """Generate standardized page content from Wikidata entity"""
    content_parts = []
    native_name = get_label(entity, 'ja')
    english_label = get_label(entity, 'en')
    sitelinks = get_sitelinks(entity)
    has_jawiki = 'jawiki' in sitelinks
    has_zhwiki = 'zhwiki' in sitelinks
    has_enwiki = 'enwiki' in sitelinks
    has_simplewiki = 'simplewiki' in sitelinks
    province_name, list_label = extract_province_from_p361(entity)

    if has_jawiki:
        jawiki_title = sitelinks['jawiki']
        content_parts.append(f"{{{{Expand Japanese|{jawiki_title}}}}}")
        content_parts.append("")
    elif has_zhwiki:
        zhwiki_title = sitelinks['zhwiki']
        content_parts.append(f"{{{{Expand Chinese|{zhwiki_title}}}}}")
        content_parts.append("")

    infobox_parts = ["{{Infobox religious building"]
    infobox_parts.append(f"| name = {page_name}")
    if native_name:
        infobox_parts.append(f"| native_name = {native_name}")
    image = get_property_value(entity, 'P18')
    if image:
        infobox_parts.append(f"| image = {image}")
    infobox_parts.append("| mapframe = yes")
    infobox_parts.append("| mapframe-zoom = 15")
    infobox_parts.append("| mapframe-wikidata = yes")
    infobox_parts.append("| mapframe-point = none")
    infobox_parts.append("| map_type = Japan")
    infobox_parts.append(f"| map_caption = {page_name}")
    coords = get_property_value(entity, 'P625')
    if coords and isinstance(coords, dict):
        lat = coords.get('latitude')
        lon = coords.get('longitude')
        if lat and lon:
            infobox_parts.append(f"| coordinates = {{{{coord|{lat}|{lon}}}}}")
    infobox_parts.append("| map_relief = 1")
    infobox_parts.append("| religious_affiliation = [[Shinto]]")
    deity = get_property_value(entity, 'P825')
    if deity and isinstance(deity, dict):
        deity_qid = deity.get('id')
        if deity_qid:
            deity_entity = get_wikidata_entity(deity_qid)
            deity_link = format_wikidata_link(deity_entity or {}, deity_qid)
            infobox_parts.append(f"| deity = {deity_link}")
    established = get_property_value(entity, 'P571')
    if established:
        infobox_parts.append(f"| established = {established}")
    website = get_property_value(entity, 'P856')
    if website:
        infobox_parts.append(f"| website = {{{{Official website|{website}}}}}")
    infobox_parts.append("}}")
    content_parts.append("\n".join(infobox_parts))
    content_parts.append("")

    if native_name:
        intro = f"{{{{nihongo|'''{english_label}'''|{native_name}}}}}"
    else:
        intro = f"'''{english_label}'''"
    intro += " is a [[shinto shrine]] in the [[Engishiki Jinmyōchō]]."
    if province_name:
        intro += f" It is located in [[{province_name}]]."
    content_parts.append(intro)
    content_parts.append("")

    all_claims = get_all_property_claims(entity)
    property_order = ['P31', 'P361', 'P1448', 'P131', 'P625', 'P571', 'P580', 'P582', 'P856', 'P18', 'P825']

    for prop_id in property_order:
        if prop_id in all_claims and prop_id not in PROPERTIES_TO_IGNORE and prop_id not in PROPERTIES_TO_OMIT:
            claims = all_claims[prop_id]
            prop_heading = get_property_heading(prop_id)
            content_parts.append(f"== {prop_heading} ==")
            content_parts.append("")
            for claim in claims:
                formatted_value, qualifiers, source = format_claim_value(claim, entity, prop_id)
                if formatted_value:
                    if source:
                        content_parts.append(f"* {formatted_value}<ref>{source}</ref>")
                    else:
                        content_parts.append(f"* {formatted_value}")
                    for qualifier in qualifiers:
                        content_parts.append(qualifier)
            content_parts.append("")

    for prop_id in sorted(all_claims.keys()):
        if prop_id not in property_order and prop_id not in PROPERTIES_TO_IGNORE and prop_id not in PROPERTIES_TO_OMIT:
            claims = all_claims[prop_id]
            prop_heading = get_property_heading(prop_id)
            content_parts.append(f"== {prop_heading} ==")
            content_parts.append("")
            for claim in claims:
                formatted_value, qualifiers, source = format_claim_value(claim, entity, prop_id)
                if formatted_value:
                    if source:
                        content_parts.append(f"* {formatted_value}<ref>{source}</ref>")
                    else:
                        content_parts.append(f"* {formatted_value}")
                    for qualifier in qualifiers:
                        content_parts.append(qualifier)
            content_parts.append("")

    categories = ["[[Category:Wikidata generated shikinaisha pages]]"]
    if has_enwiki or has_simplewiki:
        categories.append("[[Category:Autogenerated pages with simplewiki or enwiki interwikis, possibly accidentally overwritten]]")
    if has_jawiki:
        categories.append("[[Category:Autogenerated pages with jawiki interwikis, possibly accidentally overwritten]]")
    p31_values = entity.get('claims', {}).get('P31', [])
    for claim in p31_values:
        datavalue = claim.get('mainsnak', {}).get('datavalue', {})
        if isinstance(datavalue.get('value'), dict):
            instance_qid = datavalue['value'].get('id')
            if instance_qid:
                instance_entity = get_wikidata_entity(instance_qid)
                instance_label = get_label(instance_entity)
                if instance_label:
                    categories.append(f"[[Category:{instance_label}]]")
    if province_name:
        categories.append(f"[[Category:Shikinaisha in {province_name}]]")
    content_parts.append("\n".join(categories))
    content_parts.append("")

    interwiki_parts = []
    if 'commonswiki' in sitelinks:
        commons_page = sitelinks['commonswiki']
        interwiki_parts.append(f"{{{{commons category|{commons_page}}}}}")
    for lang_code in sorted(sitelinks.keys()):
        if lang_code != 'commonswiki':
            lang_title = sitelinks[lang_code]
            lang_prefix = lang_code.replace('wiki', '').upper()
            interwiki_parts.append(f"[[{lang_prefix}:{lang_title}]]")
    if interwiki_parts:
        content_parts.append("\n".join(interwiki_parts))
        content_parts.append("")

    content_parts.append(f"{{{{wikidata link|{qid}}}}}")
    final_content = "<!--generated by generate_shikinaisha_pages_v24_local_storage.py-->\n" + "\n".join(content_parts)
    return final_content

# ═══ MAIN PROCESS ═══

def generate_xml_from_content(title, content):
    """Convert page content to XML format for import"""
    # Escape XML special characters
    content = content.replace('&', '&amp;')
    content = content.replace('<', '&lt;')
    content = content.replace('>', '&gt;')

    xml = f'  <page>\n'
    xml += f'    <title>{title}</title>\n'
    xml += f'    <revision>\n'
    xml += f'      <text xml:space="preserve">{content}</text>\n'
    xml += f'    </revision>\n'
    xml += f'  </page>\n'
    return xml

def main():
    print("Generating standardized Shikinaisha pages (V24 - Local storage)\n")
    print("=" * 70)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Manifest file: {MANIFEST_FILE}\n")

    # Step 1: Download all pages from category and extract QIDs
    print("Step 1: Downloading all category members and extracting QIDs...")
    category = site.pages['Category:Wikidata generated shikinaisha pages']
    all_members = list(category.members())
    members = [m for m in all_members if m.namespace == 0]
    print(f"Found {len(members)} mainspace pages\n")

    # Step 1b: Extract QIDs and create manifest CSV immediately
    print("Step 1b: Creating manifest CSV with page titles and QIDs...")
    print("-" * 70)

    manifest_rows = []
    page_qid_map = {}
    error_count = 0

    for i, page in enumerate(members, 1):
        page_name = page.name

        try:
            page_text = page.text()
        except Exception as e:
            print(f"{i:4d}. {page_name:50s} [ERROR reading: {str(e)[:40]}]")
            error_count += 1
            continue

        # Extract QID
        match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
        if not match:
            print(f"{i:4d}. {page_name:50s} [NO QID FOUND]")
            error_count += 1
            continue

        qid = match.group(1).upper()
        page_qid_map[page_name] = qid
        manifest_rows.append({
            'page_title': page_name,
            'qid': qid,
            'xml_file': f"{page_name}.xml"
        })

        if i % 100 == 0:
            print(f"{i:4d}. {page_name:50s} ({qid})")

    # Save manifest CSV immediately
    print("\n" + "-" * 70)
    print("Saving manifest CSV...")

    try:
        with open(MANIFEST_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['page_title', 'qid', 'xml_file'])
            writer.writeheader()
            writer.writerows(manifest_rows)
        print(f"Saved manifest to {MANIFEST_FILE} with {len(manifest_rows)} entries\n")
    except Exception as e:
        print(f"ERROR saving manifest: {e}\n")
        return

    # Step 2: Generate content and save to local XML files
    print("Step 2: Generating page content and saving XML files...")
    print("-" * 70)

    processed_count = 0
    xml_files = []

    for i, (page_name, qid) in enumerate(page_qid_map.items(), 1):
        try:
            print(f"{i:4d}. {page_name:50s} ({qid})", end="", flush=True)

            # Fetch Wikidata
            entity = get_wikidata_entity(qid)
            if not entity:
                print(f" ... ! Error fetching entity")
                error_count += 1
                continue

            # Generate content
            new_content = format_page_content(page_name, qid, entity)

            # Save to XML file
            xml_filename = f"{OUTPUT_DIR}/{page_name}.xml"
            xml_content = generate_xml_from_content(page_name, new_content)

            with open(xml_filename, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            xml_files.append(xml_filename)
            print(f" ... ✓ Generated")
            processed_count += 1

        except Exception as e:
            print(f"\n   ! ERROR: {e}")
            error_count += 1
            time.sleep(1)

    # Step 4: Create batch XML files for upload
    print("Step 4: Creating batch XML files for upload...")
    print("-" * 70)

    BATCH_SIZE = 200
    batch_count = (len(xml_files) + BATCH_SIZE - 1) // BATCH_SIZE
    batch_files = []

    for batch_num in range(batch_count):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min((batch_num + 1) * BATCH_SIZE, len(xml_files))
        batch_xml_files = xml_files[start_idx:end_idx]

        # Read and combine XML files
        batch_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mediawiki>\n'

        for xml_file in batch_xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    batch_xml += content
            except Exception as e:
                print(f"ERROR reading {xml_file}: {e}")

        batch_xml += '</mediawiki>\n'

        # Save batch XML
        batch_filename = f"{OUTPUT_DIR}/batch_{batch_num+1:03d}.xml"
        try:
            with open(batch_filename, 'w', encoding='utf-8') as f:
                f.write(batch_xml)
            batch_files.append(batch_filename)
            print(f"Batch {batch_num+1}/{batch_count}: {end_idx - start_idx} pages → {batch_filename}")
        except Exception as e:
            print(f"ERROR writing batch {batch_num+1}: {e}")

    # Step 5: Upload batches
    print("\n" + "-" * 70)
    print("Step 5: Uploading batches...")
    print("-" * 70)

    upload_count = 0
    upload_errors = 0

    for batch_num, batch_file in enumerate(batch_files, 1):
        try:
            print(f"Batch {batch_num}/{len(batch_files)}: {batch_file}", end="", flush=True)

            with open(batch_file, 'r', encoding='utf-8') as f:
                xml_string = f.read()

            # Upload via API
            result = site.api(
                'import',
                xml=xml_string,
                format='json'
            )

            print(f" ... ✓ Uploaded")
            upload_count += 1

            # Rate limiting
            time.sleep(3)

        except Exception as e:
            print(f" ... ! ERROR: {str(e)[:60]}")
            upload_errors += 1
            time.sleep(1)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total pages found: {len(members)}")
    print(f"Content generated: {processed_count}")
    print(f"XML files created: {len(xml_files)}")
    print(f"Manifest entries: {len(manifest_rows)}")
    print(f"Batch files created: {len(batch_files)}")
    print(f"Batches uploaded: {upload_count}")
    print(f"Upload errors: {upload_errors}")
    print(f"Generation errors: {error_count}")
    print("\nAll XML files saved to: " + OUTPUT_DIR)
    print("Manifest saved to: " + MANIFEST_FILE)

if __name__ == "__main__":
    main()
