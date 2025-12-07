#!/usr/bin/env python3
"""generate_shikinaisha_pages_v25_with_redirects.py
================================================
V25: Handles both regular Shikinaisha pages and Wikidata redirects
- For regular Wikidata items: generates full page content
- For Wikidata redirects: creates a redirect page (#redirect[[Q_TARGET]])
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

# ═══ SHARED HELPER FUNCTIONS ═══

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

def check_wikidata_redirect(qid):
    """Check if a Wikidata QID is a redirect and return target QID if so"""
    try:
        url = f'https://www.wikidata.org/w/api.php'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        params = {
            'action': 'wbgetentities',
            'ids': qid,
            'format': 'json'
        }
        resp = requests.get(url, params=params, timeout=10, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if 'entities' in data and qid in data['entities']:
            entity = data['entities'][qid]
            # Check if it's a redirect
            if 'redirects' in entity:
                return entity['redirects'].get('to')
        return None
    except Exception as e:
        print(f"     ! Error checking redirect for {qid}: {e}")
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
    """Get heading text for a property in format: EN_LABEL (PID)"""
    if property_id in PROPERTY_LABELS:
        label = PROPERTY_LABELS[property_id]
        return f"{label} ({property_id})"
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
    final_content = "<!--generated by generate_shikinaisha_pages_v25_with_redirects.py-->\n" + "\n".join(content_parts)
    return final_content

def format_redirect_page(target_qid):
    """Generate a redirect page that points to another Wikidata item"""
    return f"#redirect[[{target_qid}]]"

# ═══ MAIN PROCESS ═══

def main():
    print("Generating standardized Shikinaisha pages (V25 - With Wikidata redirects)\n")
    print("=" * 60)

    category = site.pages['Category:Wikidata generated shikinaisha pages']
    all_members = list(category.members())
    members = [m for m in all_members if m.namespace == 0]

    print(f"Found {len(members)} mainspace pages\n")

    processed_count = 0
    error_count = 0
    redirect_count = 0

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

        try:
            print(f"{i:4d}. {page_name:50s} ({qid})", end="", flush=True)

            # Check if this is a Wikidata redirect
            target_qid = check_wikidata_redirect(qid)

            if target_qid:
                # This is a redirect - create a redirect page
                redirect_content = format_redirect_page(target_qid)
                page.edit(redirect_content, summary=f"v25: Wikidata redirect to {target_qid}")
                print(f" ... → {target_qid} (redirect)")
                redirect_count += 1
            else:
                # Regular page - generate full content
                # Fetch Wikidata
                entity = get_wikidata_entity(qid)
                if not entity:
                    print(f" ... ! Error fetching entity")
                    error_count += 1
                    continue

                # Generate content
                new_content = format_page_content(page_name, qid, entity)

                # Edit the page
                page.edit(new_content, summary="v25: Standardize page format")
                print(f" ... ✓ Edited")
                processed_count += 1

            # Rate limiting
            time.sleep(1.5)

        except Exception as e:
            print(f"\n   ! ERROR: {e}")
            error_count += 1
            time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Processed (full pages): {processed_count}")
    print(f"  Redirects created: {redirect_count}")
    print(f"  Errors: {error_count}")

if __name__ == "__main__":
    main()
