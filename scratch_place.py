"""Throwaway: do the P131 places actually have ja/zh/ko labels?"""
import collections
import json
import os
import random
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

API = "https://www.wikidata.org/w/api.php"
SRC = os.path.join(ROOT, 'shinto-label-generator', 'paused',
                   'religious_building_en.txt')


def get(ids, props, langs=None):
    url = (API + "?action=wbgetentities&format=json&ids=" + "|".join(ids)
           + "&props=" + props)
    if langs:
        url += "&languages=" + langs
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("entities", {})


qids = [m.group(1) for m in
        (re.match(r'^(Q\d+)\|', l.strip()) for l in open(SRC, encoding='utf-8'))
        if m]
random.seed(23)
sample = random.sample(qids, 200)

places = {}
no_p131 = 0
for i in range(0, len(sample), 50):
    ents = get(sample[i:i + 50], "claims")
    for qid, e in ents.items():
        cl = (e.get("claims") or {}).get("P131") or []
        if not cl:
            no_p131 += 1
            continue
        try:
            places[qid] = cl[0]["mainsnak"]["datavalue"]["value"]["id"]
        except Exception:
            no_p131 += 1
    time.sleep(1.0)

print("sampled items        : %d" % len(sample))
print("no P131              : %d  %.1f%%" % (no_p131, 100.0 * no_p131 / len(sample)))
distinct = sorted(set(places.values()))
print("distinct P131 places : %d (for %d items)" % (len(distinct), len(places)))

have = collections.Counter()
for i in range(0, len(distinct), 50):
    ents = get(distinct[i:i + 50], "labels", langs="ja|zh|ko|en")
    for qid, e in ents.items():
        labs = e.get("labels", {}) or {}
        for lg in ("ja", "zh", "ko", "en"):
            if lg in labs:
                have[lg] += 1
        if not any(lg in labs for lg in ("ja", "zh", "ko")):
            have["NONE of ja/zh/ko"] += 1
    time.sleep(1.0)

print("\n--- of %d distinct places, how many carry a label in:" % len(distinct))
for lg in ("ja", "zh", "ko", "en", "NONE of ja/zh/ko"):
    c = have[lg]
    print("   %-18s %4d  %5.1f%%" % (lg, c, 100.0 * c / max(len(distinct), 1)))
