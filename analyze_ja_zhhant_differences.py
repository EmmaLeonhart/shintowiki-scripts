import requests
import json
import sys
import io

# Fix Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wikidata SPARQL endpoint
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL query to get all instances of Q845945 with labels
query = """
SELECT ?item ?itemLabel_ja ?itemLabel_zh_hant WHERE {
  ?item wdt:P31 wd:Q845945.

  OPTIONAL { ?item rdfs:label ?itemLabel_ja. FILTER(LANG(?itemLabel_ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?itemLabel_zh_hant. FILTER(LANG(?itemLabel_zh_hant) = "zh-hant") }
}
"""

print("Querying Wikidata for instances of Q845945 with ja and zh-hant labels...")
response = requests.get(SPARQL_ENDPOINT, params={
    'query': query,
    'format': 'json'
}, headers={'User-Agent': 'WikidataLabelComparisonBot/1.0'})

data = response.json()
results = data['results']['bindings']

print(f"Found {len(results)} results\n")

# Collect items with both labels
items_with_both = []
matches = 0
differences = []

for result in results:
    ja = result.get('itemLabel_ja', {}).get('value')
    zh_hant = result.get('itemLabel_zh_hant', {}).get('value')

    if ja and zh_hant:
        items_with_both.append({
            'qid': result['item']['value'].split('/')[-1],
            'ja': ja,
            'zh_hant': zh_hant
        })

        if ja == zh_hant:
            matches += 1
        else:
            # Find the character differences
            diff_chars = []
            for i, (c_ja, c_zh) in enumerate(zip(ja, zh_hant)):
                if c_ja != c_zh:
                    diff_chars.append({
                        'position': i,
                        'ja_char': c_ja,
                        'zh_char': c_zh,
                        'ja_unicode': f'U+{ord(c_ja):04X}',
                        'zh_unicode': f'U+{ord(c_zh):04X}'
                    })

            if len(ja) != len(zh_hant) or diff_chars:
                differences.append({
                    'qid': result['item']['value'].split('/')[-1],
                    'ja': ja,
                    'zh_hant': zh_hant,
                    'diff_chars': diff_chars,
                    'length_diff': len(zh_hant) - len(ja)
                })

print("=" * 80)
print("STATISTICS")
print("=" * 80)
print(f"Total items with both ja and zh-hant: {len(items_with_both)}")
print(f"Exact matches: {matches} ({100*matches/len(items_with_both):.1f}%)")
print(f"Differences: {len(differences)} ({100*len(differences)/len(items_with_both):.1f}%)")
print()

# Analyze character differences
print("=" * 80)
print("CHARACTER-LEVEL ANALYSIS")
print("=" * 80)

# Count frequency of character substitutions
char_pairs = {}
for diff in differences:
    for char_diff in diff['diff_chars']:
        pair = (char_diff['ja_char'], char_diff['zh_char'])
        if pair not in char_pairs:
            char_pairs[pair] = {
                'count': 0,
                'ja_unicode': char_diff['ja_unicode'],
                'zh_unicode': char_diff['zh_unicode'],
                'examples': []
            }
        char_pairs[pair]['count'] += 1
        if len(char_pairs[pair]['examples']) < 3:
            char_pairs[pair]['examples'].append(diff['qid'])

print(f"\nMost common character differences:")
print(f"(Sorted by frequency)\n")
sorted_pairs = sorted(char_pairs.items(), key=lambda x: x[1]['count'], reverse=True)

for i, ((ja_char, zh_char), data) in enumerate(sorted_pairs[:30], 1):
    examples_str = ', '.join(data['examples'])
    print(f"{i}. '{ja_char}' (ja) → '{zh_char}' (zh-hant): {data['count']} occurrences")
    print(f"   Unicode: {data['ja_unicode']} → {data['zh_unicode']}")
    print(f"   Examples: {examples_str}")
    print()

# Show full examples
print("=" * 80)
print("FULL EXAMPLES OF DIFFERENCES (first 20)")
print("=" * 80)
for diff in differences[:20]:
    print(f"\n{diff['qid']}:")
    print(f"  ja:      {diff['ja']}")
    print(f"  zh-hant: {diff['zh_hant']}")
    if diff['diff_chars']:
        for char_diff in diff['diff_chars']:
            print(f"    Position {char_diff['position']}: '{char_diff['ja_char']}' ({char_diff['ja_unicode']}) → '{char_diff['zh_char']}' ({char_diff['zh_unicode']})")

print(f"\n... and {len(differences) - 20} more differences")
print("\nDone!")
