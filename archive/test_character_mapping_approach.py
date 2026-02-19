import requests
import json
import sys
import io
import re

# Fix Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wikidata SPARQL endpoint
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL query to get all instances of Q845945 with labels
query = """
SELECT ?item ?itemLabel_ja ?itemLabel_zh WHERE {
  ?item wdt:P31 wd:Q845945.

  OPTIONAL { ?item rdfs:label ?itemLabel_ja. FILTER(LANG(?itemLabel_ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?itemLabel_zh. FILTER(LANG(?itemLabel_zh) = "zh") }
}
"""

print("Querying Wikidata...")
response = requests.get(SPARQL_ENDPOINT, params={
    'query': query,
    'format': 'json'
}, headers={'User-Agent': 'WikidataLabelComparisonBot/1.0'})

data = response.json()
results = data['results']['bindings']

# Build character mapping from ja→zh by analyzing existing pairs
print("Building character mapping from existing ja↔zh pairs...")

char_map = {}
items_with_both = []

for result in results:
    ja = result.get('itemLabel_ja', {}).get('value')
    zh = result.get('itemLabel_zh', {}).get('value')

    if ja and zh:
        items_with_both.append({'qid': result['item']['value'].split('/')[-1], 'ja': ja, 'zh': zh})

        # Build character mapping (only if same length and no kana)
        if len(ja) == len(zh) and not re.search(r'[\u3040-\u309F\u30A0-\u30FF]', ja):
            for c_ja, c_zh in zip(ja, zh):
                if c_ja != c_zh:
                    if c_ja not in char_map:
                        char_map[c_ja] = {}
                    if c_zh not in char_map[c_ja]:
                        char_map[c_ja][c_zh] = 0
                    char_map[c_ja][c_zh] += 1

# Finalize mapping by taking most common substitution for each character
final_map = {}
for ja_char, zh_options in char_map.items():
    # Take the most common zh char for this ja char
    final_map[ja_char] = max(zh_options.items(), key=lambda x: x[1])[0]

print(f"Built mapping with {len(final_map)} character substitutions\n")
print("Top 20 mappings:")
sorted_map = sorted(final_map.items(), key=lambda x: sum(char_map[x[0]].values()), reverse=True)
for i, (ja_char, zh_char) in enumerate(sorted_map[:20], 1):
    count = sum(char_map[ja_char].values())
    print(f"  {i}. '{ja_char}' → '{zh_char}' ({count} occurrences)")

print("\n" + "=" * 80)
print("TESTING THE MAPPING APPROACH")
print("=" * 80)

def convert_ja_to_zh(ja_text, char_mapping):
    """Convert Japanese text to Chinese using character mapping."""
    result = ""
    for char in ja_text:
        result += char_mapping.get(char, char)
    return result

def has_kana(text):
    """Check if text contains any kana characters."""
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text))

# Test on all items with both labels
pure_kanji_items = [item for item in items_with_both if not has_kana(item['ja'])]
items_with_kana = [item for item in items_with_both if has_kana(item['ja'])]

print(f"\nTotal items with both ja and zh labels: {len(items_with_both)}")
print(f"  Pure kanji (no kana): {len(pure_kanji_items)}")
print(f"  Contains kana: {len(items_with_kana)}")

# Test conversion on pure kanji items
correct = 0
incorrect = 0
incorrect_examples = []

for item in pure_kanji_items:
    converted = convert_ja_to_zh(item['ja'], final_map)
    if converted == item['zh']:
        correct += 1
    else:
        incorrect += 1
        if len(incorrect_examples) < 20:
            incorrect_examples.append({
                'qid': item['qid'],
                'ja': item['ja'],
                'converted': converted,
                'actual_zh': item['zh']
            })

print(f"\n" + "=" * 80)
print("RESULTS FOR PURE KANJI ITEMS")
print("=" * 80)
print(f"Correct conversions: {correct}/{len(pure_kanji_items)} ({100*correct/len(pure_kanji_items):.1f}%)")
print(f"Incorrect conversions: {incorrect}/{len(pure_kanji_items)} ({100*incorrect/len(pure_kanji_items):.1f}%)")

if incorrect_examples:
    print(f"\nFirst {len(incorrect_examples)} incorrect conversions:")
    for ex in incorrect_examples:
        print(f"\n{ex['qid']}:")
        print(f"  Original (ja):     {ex['ja']}")
        print(f"  Converted:         {ex['converted']}")
        print(f"  Actual (zh):       {ex['actual_zh']}")
        # Show character differences
        diffs = []
        for i, (c1, c2) in enumerate(zip(ex['converted'], ex['actual_zh'])):
            if c1 != c2:
                diffs.append(f"pos {i}: '{c1}' should be '{c2}'")
        if len(ex['converted']) != len(ex['actual_zh']):
            diffs.append(f"length: {len(ex['converted'])} vs {len(ex['actual_zh'])}")
        if diffs:
            print(f"  Differences: {', '.join(diffs)}")

print(f"\n" + "=" * 80)
print("EXAMPLES OF ITEMS WITH KANA (would be skipped)")
print("=" * 80)
for item in items_with_kana[:10]:
    print(f"{item['qid']}: {item['ja']} → {item['zh']}")

print("\nDone!")
