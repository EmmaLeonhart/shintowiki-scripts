"""Throwaway: how many stage-1 Commons-derived en labels actually reached Wikidata?

Read API, not SPARQL (WDQS 429'd on 2026-09-17 and the transport bailed). For each
QID in the paused stage-1 file, does the item now carry an en label, and does it
match what stage 1 proposed?
"""
import collections
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'shinto-label-generator'))
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import religious_building_morphemes as morph

API = "https://www.wikidata.org/w/api.php"
SRC = os.path.join(ROOT, 'shinto-label-generator', 'paused',
                   'religious_building_en.txt')
OUT = os.path.join(ROOT, 'shinto-label-generator', 'paused',
                   'stage1_landed.json')

proposed = {}
for line in open(SRC, encoding='utf-8'):
    m = re.match(r'^(Q\d+)\|Len\|"(.+)"$', line.strip())
    if m:
        proposed[m.group(1)] = m.group(2)
qids = sorted(proposed)
print("stage-1 proposals: %d" % len(qids))

landed = {}
if os.path.exists(OUT):
    landed = json.load(open(OUT, encoding='utf-8'))
todo = [q for q in qids if q not in landed]
print("to fetch: %d" % len(todo))

for i in range(0, len(todo), 50):
    url = API + "?" + urllib.parse.urlencode({
        "action": "wbgetentities", "format": "json",
        "ids": "|".join(todo[i:i + 50]), "props": "labels", "languages": "en"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        ents = json.load(r).get("entities", {}) or {}
    for qid, e in ents.items():
        lab = ((e.get("labels") or {}).get("en") or {}).get("value")
        landed[qid] = lab
    time.sleep(1.0)
    if i and i % 5000 == 0:
        json.dump(landed, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)

json.dump(landed, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)

TYPE_RE = re.compile(
    r'\b(church|chapel|cathedral|mosque|synagogue|monastery|abbey|basilica|temple|oratory)\b',
    re.I)

n = has = match = 0
cat_shaped = no_type = 0
for qid, prop in proposed.items():
    if qid not in landed:
        continue
    n += 1
    cur = landed[qid]
    if not cur:
        continue
    has += 1
    if cur.strip() == prop.strip():
        match += 1
        if morph.is_category_shaped(cur):
            cat_shaped += 1
        elif not TYPE_RE.search(cur):
            no_type += 1

print("\nchecked            : %d" % n)
print("now has an en label: %d  %.1f%%" % (has, 100.0 * has / max(n, 1)))
print("matches stage 1    : %d  %.1f%%  <- these are ours" % (match, 100.0 * match / max(n, 1)))
print("\nof the ones that are ours:")
print("  category-shaped  : %d" % cat_shaped)
print("  no English type  : %d" % no_type)
print("  plausible        : %d" % (match - cat_shaped - no_type))
