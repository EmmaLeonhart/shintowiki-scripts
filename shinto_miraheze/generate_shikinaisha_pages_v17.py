#!/usr/bin/env python3
"""generate_shikinaisha_pages_v17.py
================================================
Generate standardized shrine pages for Wikidata-generated Shikinaisha entries
V17: Restore proper established ILL template logic from v13
================================================

This script:
1. Runs immediately (no startup delay)
2. Walks through [[Category:Wikidata generated shikinaisha pages]]
3. For each page with a {{wikidata link|QID}}, fetches Wikidata properties
4. Generates standardized page content with:
   - Proper intro: {{nihongo|'''EN LABEL'''|JA LABEL}} is a [[shinto shrine]] in [[Engishiki Jinmyōchō]]. Located in [[PROVINCE]]
   - Infobox with Wikidata values
   - Sections for each property (P31, P361, P625, P571, etc.)
   - P1448 OMITTED (not shown)
   - P2671 OMITTED (not shown)
   - P11250 IGNORED (filtered out)
   - ILL templates with PROPER established format:
     * Priority 1 param: shintowiki sitelink > enwiki sitelink > English label
     * Positional pairs: |LANG_CODE|WIKIPEDIA_TITLE for each sitelink (en, ja, de, zh, fr, ru)
     * lt=ENGLISH_LABEL (for display text)
     * WD=QID (always capitalized)
   - P625 (Coordinate Location) formatted with {{coord|lat|lon}} template
   - Source references with URLS: <ref>SOURCE: URL</ref>
   - Sub-bullet qualifiers under each claim
   - Wikipedia links (enwiki/simplewiki) properly included
   - Interwiki categories based on sitelinks
   - Province category from P361 (List of Shikinaisha in X)
   - P31 instances as categories
   - Commons category template without "Category:" prefix
   - Wikidata link at bottom
"""

import mwclient
import requests
import sys
import time
import re

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

PROPERTIES_TO_IGNORE = ['P11250']
PROPERTIES_TO_OMIT = ['P1448', 'P2671']

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def get_wikidata_entity(qid):
    """Fetch full entity data from Wikidata."""
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
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
    """Extract value from a property in entity data."""
    if not entity or 'claims' not in entity:
        return None

    claims = entity.get('claims', {})
    prop_claims = claims.get(property_id, [])

    if prop_claims:
        mainsnak = prop_claims[0].get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        return datavalue.get('value')

    return None


def get_all_property_claims(entity):
    """Get all property claims from entity."""
    if not entity or 'claims' not in entity:
        return {}
    return entity.get('claims', {})


def get_label(entity, language='en'):
    """Extract label from entity in specified language."""
    if not entity or 'labels' not in entity:
        return None

    labels = entity.get('labels', {})
    if language in labels:
        return labels[language].get('value')

    return None


def get_sitelinks(entity):
    """Extract sitelinks (interwiki) from entity - returns only titles."""
    sitelinks = {}
    if entity and 'sitelinks' in entity:
        for site_code, site_data in entity['sitelinks'].items():
            sitelinks[site_code] = site_data.get('title', '')
    return sitelinks


def extract_province_from_p361(entity):
    """Extract province name from P361 (part of) property."""
    if not entity or 'claims' not in entity:
        return None, None

    claims = entity.get('claims', {}).get('P361', [])
    if not claims:
        return None, None

    for claim in claims:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        value = datavalue.get('value')

        if isinstance(value, dict) and 'id' in value:
            qid = value['id']
            ref_entity = get_wikidata_entity(qid)
            if ref_entity:
                label = get_label(ref_entity)
                if label and label.startswith('List of Shikinaisha in '):
                    province = label.replace('List of Shikinaisha in ', '')
                    return province, label
    return None, None


def format_wikidata_link(entity, qid):
    """Format a wikidata link using ILL syntax with proper established logic.

    Format: {{ill|FIRST_PARAM|LANG1|TITLE1|LANG2|TITLE2|...|lt=ENGLISH_LABEL|WD=QID}}

    FIRST_PARAM priority:
    1. shintowiki sitelink
    2. enwiki sitelink
    3. English label from Wikidata

    Then positional pairs: |LANG_CODE|WIKIPEDIA_TITLE for each sitelink
    (these are Wikipedia article titles, not labels)
    """
    sitelinks = get_sitelinks(entity)

    # Try to find shinto wiki page first, then English Wikipedia, then English label
    first_link = None
    if 'shintowiki' in sitelinks:
        first_link = sitelinks['shintowiki']
    elif 'enwiki' in sitelinks:
        first_link = sitelinks['enwiki']
    else:
        first_link = get_label(entity, 'en') or qid

    # Get English label for lt= parameter
    en_label = get_label(entity, 'en') or qid

    # Build the ILL link with positional first param
    wd_link = f"{{{{ill|{first_link}|lt={en_label}"

    # Add all language codes and Wikipedia article titles (positional pairs)
    for lang_code in ['enwiki', 'jawiki', 'dewiki', 'zhwiki', 'frwiki', 'ruwiki']:
        if lang_code in sitelinks:
            lang = lang_code.replace('wiki', '')
            title = sitelinks[lang_code]
            wd_link += f"|{lang}|{title}"

    # Add named parameter: WD= (QID)
    wd_link += f"|WD={qid}}}}}"

    return wd_link


def get_property_heading(property_id):
    """Get human-readable heading for a property."""
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{property_id}.json'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=5, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if 'entities' in data and property_id in data['entities']:
            entity = data['entities'][property_id]
            labels = entity.get('labels', {})
            if 'en' in labels:
                label = labels['en'].get('value')
                return f"{label} ({property_id})"
    except Exception:
        pass

    property_labels = {
        'P31': 'Instance of',
        'P361': 'Part of',
        'P1448': 'Official name',
        'P131': 'Located in',
        'P625': 'Coordinate location',
        'P571': 'Inception',
        'P580': 'Start time',
        'P582': 'End time',
        'P585': 'Point in time',
        'P856': 'Official website',
        'P18': 'Image',
        'P825': 'Dedicated to',
        'P1566': 'GeoNames ID',
    }

    label = property_labels.get(property_id, property_id)
    return f"{label} ({property_id})"


def get_source_reference_with_url(claim):
    """Extract source reference from claim references, including URLs in proper format.

    Returns format: "SOURCE_NAME: URL" or just "URL" if no source name available.
    """
    references = claim.get('references', [])
    if not references:
        return None

    for ref in references:
        ref_snaks = ref.get('snaks', {})

        # Check for reference URL (P854)
        url = None
        if 'P854' in ref_snaks:
            for snak in ref_snaks['P854']:
                datavalue = snak.get('datavalue', {})
                url = datavalue.get('value')
                if url:
                    break

        # Check for stated in (P248) - source
        source_label = None
        if 'P248' in ref_snaks:
            for snak in ref_snaks['P248']:
                datavalue = snak.get('datavalue', {})
                if isinstance(datavalue.get('value'), dict):
                    source_qid = datavalue['value'].get('id')
                    if source_qid:
                        source_entity = get_wikidata_entity(source_qid)
                        if source_entity:
                            source_label = get_label(source_entity)
                            break

        # Format: prefer URL with source name, fall back to just URL, fall back to source name only
        if url:
            if source_label:
                return f"{source_label}: {url}"
            else:
                return url
        elif source_label:
            return source_label

    return None


def format_qualifier_value(qualifier_value):
    """Format a qualifier value for display."""
    if isinstance(qualifier_value, dict) and 'id' in qualifier_value:
        qid = qualifier_value['id']
        ref_entity = get_wikidata_entity(qid)
        return format_wikidata_link(ref_entity or {}, qid)

    if isinstance(qualifier_value, str):
        return qualifier_value

    return str(qualifier_value)


def get_qualifiers_text(claim):
    """Extract and format qualifiers from a claim as sub-bullets."""
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
    """Format a single claim value for display."""
    mainsnak = claim.get('mainsnak', {})
    datavalue = mainsnak.get('datavalue', {})
    value = datavalue.get('value')

    if not value:
        return None, [], None

    formatted_value = None

    if property_id == 'P13677' and isinstance(value, str):
        url = f"https://jmapps.ne.jp/kokugakuin/det.html?data_id={value}"
        formatted_value = f"[{url} Kokugakuin Digital Museum Item]"

    elif property_id == 'P625' and isinstance(value, dict):
        lat = value.get('latitude')
        lon = value.get('longitude')
        if lat and lon:
            formatted_value = f"{{{{coord|{lat}|{lon}}}}}"
        else:
            formatted_value = None

    elif isinstance(value, dict) and 'id' in value:
        qid = value['id']
        ref_entity = get_wikidata_entity(qid)
        formatted_value = format_wikidata_link(ref_entity or {}, qid)

    elif isinstance(value, str):
        formatted_value = value

    else:
        formatted_value = str(value)

    qualifiers = get_qualifiers_text(claim)
    source = get_source_reference_with_url(claim)

    return formatted_value, qualifiers, source


def format_page_content(page_name, qid, entity):
    """Generate standardized page content from Wikidata entity."""
    content_parts = []

    # Get basic info
    native_name = get_label(entity, 'ja')
    english_label = get_label(entity, 'en')

    # Extract sitelinks for interwiki handling
    sitelinks = get_sitelinks(entity)
    has_enwiki = 'enwiki' in sitelinks
    has_simplewiki = 'simplewiki' in sitelinks
    has_jawiki = 'jawiki' in sitelinks
    has_zhwiki = 'zhwiki' in sitelinks

    # Extract province from P361
    province_name, list_label = extract_province_from_p361(entity)

    # ADD EXPAND TEMPLATES AT TOP if needed
    if has_jawiki:
        jawiki_title = sitelinks['jawiki']
        content_parts.append(f"{{{{Expand Japanese|{jawiki_title}}}}}")
        content_parts.append("")
    elif has_zhwiki:
        zhwiki_title = sitelinks['zhwiki']
        content_parts.append(f"{{{{Expand Chinese|{zhwiki_title}}}}}")
        content_parts.append("")

    # ADD INFOBOX FIRST
    infobox_parts = ["{{Infobox religious building"]
    infobox_parts.append(f"| name = {page_name}")

    if native_name:
        infobox_parts.append(f"| native_name = {native_name}")

    # Image (P18)
    image = get_property_value(entity, 'P18')
    if image:
        infobox_parts.append(f"| image = {image}")

    infobox_parts.append("| mapframe = yes")
    infobox_parts.append("| mapframe-zoom = 15")
    infobox_parts.append("| mapframe-wikidata = yes")
    infobox_parts.append("| mapframe-point = none")
    infobox_parts.append("| map_type = Japan")
    infobox_parts.append(f"| map_caption = {page_name}")

    # Coordinates (P625) - using coord template
    coords = get_property_value(entity, 'P625')
    if coords and isinstance(coords, dict):
        lat = coords.get('latitude')
        lon = coords.get('longitude')
        if lat and lon:
            infobox_parts.append(f"| coordinates = {{{{coord|{lat}|{lon}}}}}")

    infobox_parts.append("| map_relief = 1")
    infobox_parts.append("| religious_affiliation = [[Shinto]]")

    # Deity (P825)
    deity = get_property_value(entity, 'P825')
    if deity and isinstance(deity, dict):
        deity_qid = deity.get('id')
        if deity_qid:
            deity_entity = get_wikidata_entity(deity_qid)
            deity_link = format_wikidata_link(deity_entity or {}, deity_qid)
            infobox_parts.append(f"| deity = {deity_link}")

    # Established (P571)
    established = get_property_value(entity, 'P571')
    if established:
        infobox_parts.append(f"| established = {established}")

    # Website (P856)
    website = get_property_value(entity, 'P856')
    if website:
        infobox_parts.append(f"| website = {{{{Official website|{website}}}}}")

    infobox_parts.append("}}")

    content_parts.append("\n".join(infobox_parts))
    content_parts.append("")

    # THEN ADD INTRO TEXT
    if native_name:
        intro = f"{{{{nihongo|'''{english_label}'''|{native_name}}}}}"
    else:
        intro = f"'''{english_label}'''"

    intro += " is a [[shinto shrine]] in the [[Engishiki Jinmyōchō]]."

    if province_name:
        intro += f" It is located in [[{province_name}]]."

    content_parts.append(intro)
    content_parts.append("")

    # Add sections for ALL properties (except those in PROPERTIES_TO_IGNORE or PROPERTIES_TO_OMIT)
    all_claims = get_all_property_claims(entity)
    property_order = ['P31', 'P361', 'P1448', 'P131', 'P625', 'P571', 'P580', 'P582', 'P856', 'P18', 'P825']

    # Add ordered properties first
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

    # Add remaining properties
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

    # Categories
    categories = ["[[Category:Wikidata generated shikinaisha pages]]"]

    # Add interwiki categories
    if has_enwiki or has_simplewiki:
        categories.append("[[Category:Autogenerated pages with simplewiki or enwiki interwikis, possibly accidentally overwritten]]")

    if has_jawiki:
        categories.append("[[Category:Autogenerated pages with jawiki interwikis, possibly accidentally overwritten]]")

    # Add categories from P31 (instance of)
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

    # Add province category from P361
    if province_name:
        categories.append(f"[[Category:Shikinaisha in {province_name}]]")

    content_parts.append("\n".join(categories))
    content_parts.append("")

    # Interwiki links at the bottom
    interwiki_parts = []

    # Handle commons (without "Category:" prefix in the template)
    if 'commonswiki' in sitelinks:
        commons_page = sitelinks['commonswiki']
        interwiki_parts.append(f"{{{{commons category|{commons_page}}}}}")

    # Add other interwiki links (including enwiki and simplewiki)
    for lang_code in ['enwiki', 'simplewiki', 'jawiki', 'dewiki', 'zhwiki', 'frwiki', 'ruwiki']:
        if lang_code in sitelinks:
            lang_title = sitelinks[lang_code]
            lang_prefix = lang_code.replace('wiki', '').upper()
            interwiki_parts.append(f"[[{lang_prefix}:{lang_title}]]")

    if interwiki_parts:
        content_parts.append("\n".join(interwiki_parts))
        content_parts.append("")

    # Wikidata link at the very bottom
    content_parts.append(f"{{{{wikidata link|{qid}}}}}")

    # Add version comment at the very beginning
    final_content = "<!--generated by generate_shikinaisha_pages_v17.py-->\n" + "\n".join(content_parts)
    return final_content


def main():
    """Process all pages in [[Category:Wikidata generated shikinaisha pages]]."""

    print("Generating standardized Shikinaisha pages (V17 - Restore proper established ILL logic)\n")
    print("=" * 60)

    # Get the category
    category = site.pages['Category:Wikidata generated shikinaisha pages']

    print(f"\nFetching mainspace pages in [[Category:Wikidata generated shikinaisha pages]]...")
    try:
        all_members = list(category.members())
        members = [page for page in all_members if page.namespace == 0]
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} mainspace pages (filtered from {len(all_members)} total)\n")

    processed_count = 0
    error_count = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{idx}. {page_name}", end="")

            # Get page text
            text = page.text()

            # Extract QID
            qid = extract_wikidata_qid(text)
            if not qid:
                print(f" ... • No QID found")
                continue

            print(f" ({qid})", end="")

            # Fetch Wikidata entity
            entity = get_wikidata_entity(qid)
            if not entity:
                print(f" ... ! Error fetching entity")
                error_count += 1
                continue

            # Generate content
            new_content = format_page_content(page_name, qid, entity)

            # Save the page
            try:
                page.edit(new_content, summary="Bot: V17 - Restore proper established ILL logic with positional Wikipedia article title pairs")
                processed_count += 1
                print(f" ... ✓ Updated")
            except mwclient.errors.EditConflict:
                print(f" ! Edit conflict")
                error_count += 1
            except Exception as e:
                print(f" ! Error saving: {e}")
                error_count += 1

            # Rate limiting
            time.sleep(1.0)

        except Exception as e:
            try:
                print(f"\n   ! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"\n   ! ERROR: {str(e)}")
            error_count += 1

    print(f"\n{'=' * 60}")
    print(f"\nSummary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Processed: {processed_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    main()
