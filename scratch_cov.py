"""Throwaway: coverage + collision rate of the morpheme renderer over the corpus.

P31 is not fetched yet, so every item is treated as a church building (Q16970) --
the dominant class (246/300 in the sample). That inflates coverage slightly and is
stated, not hidden.
"""
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'shinto-label-generator'))
import religious_building_morphemes as m

SRC = os.path.join(ROOT, 'shinto-label-generator', 'paused',
                   'religious_building_en.txt')

labels = []
for line in open(SRC, encoding='utf-8'):
    mm = re.search(r'\|Len\|"(.+)"\s*$', line.strip())
    if mm:
        labels.append(mm.group(1))

n = len(labels)
cat = sum(1 for l in labels if m.is_category_shaped(l))
rendered = {}
unknown_first = collections.Counter()
for l in labels:
    out = m.render(l, 'Q16970', 'ja')
    if out:
        rendered.setdefault(out, []).append(l)
    elif not m.is_category_shaped(l):
        toks, _ = m.parse_name(l)
        for t in toks:
            if t not in m.NAMES:
                unknown_first[t] += 1
                break

emitted = sum(len(v) for v in rendered.values())
print("labels                    : %d" % n)
print("category-shaped (refused) : %d  %.1f%%" % (cat, 100.0 * cat / n))
print("rendered (all parts known): %d  %.1f%%" % (emitted, 100.0 * emitted / n))
print("distinct outputs          : %d" % len(rendered))
coll = {k: v for k, v in rendered.items() if len(v) > 1}
print("outputs used by >1 item   : %d, covering %d labels  %.1f%% of emitted"
      % (len(coll), sum(len(v) for v in coll.values()),
         100.0 * sum(len(v) for v in coll.values()) / max(emitted, 1)))

print("\n--- worst collisions")
for k, v in sorted(coll.items(), key=lambda kv: -len(kv[1]))[:8]:
    print("   %-16s %4d items, e.g. %s" % (k, len(v), ' | '.join(v[:3])))

print("\n--- top unknown name tokens (what a transliterator would have to take)")
for t, c in unknown_first.most_common(70):
    print("   %-22s %4d" % (t, c))
