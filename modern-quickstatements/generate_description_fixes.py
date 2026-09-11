#!/usr/bin/env python3
"""
generate_description_fixes.py
==============================
Give a LABEL to every shrine/temple that carries a description in a language it
has no label in. Label-only — it does not edit descriptions.

## ⭐ The purpose, corrected by Emma 2026-09-11

*"the Ukrainian descriptions are being updated in a bad way that seems to
indicate a lack of understanding of the purpose, descriptions should not be being
edited either way really. The emergency stuff was intended to rapidly apply
labels to things with orphaned descriptions to see how much actual description
changes were needed."*

An **orphan description** — a description in language X on an item with no label
in X — is actively harmful, because Wikidata's uniqueness constraint is on the
(label, description) PAIR, so the description is occupying the slot and costing
the item a label (`docs/description_label_policy.md`). **Supplying the label is
the fix.** The description is then no longer an orphan, and whether it ALSO needs
rewriting is a separate question that can only be answered once the labels are
in — which is what "to see how much actual description changes were needed"
means.

**13,099 orphan descriptions remained on 2026-09-11** (7,216 shrines, 5,883
temples). That is the number this pipeline exists to bring down.

## ⛔ It used to rewrite the description too, and that was the defect

Each unit was a compound `Qxxx|Dxx|"…"||Qxxx|Lxx|"…"` — standardise the
description, then add the label — with the standard form inferred from the corpus
per (class, language). Two things were wrong with it, in increasing order of
importance:

  1. The inference could not match a prefecture label through an inflected or
     differently-cased description, so nine languages fell to a single generic
     modal and **208 prefecture-specific descriptions were flattened into one
     duplicative string** before Emma caught it (DEVLOG 2026-09-10).
  2. More fundamentally, **the description edit was never the point.** It was
     there to unblock the label, and the label lands without it: the
     (label, description) uniqueness check below is what handles the constraint,
     by WITHHOLDING a label that would collide rather than by rewriting the
     description to make room.

So the description is now read for exactly one reason — to form the pair that the
uniqueness check tests — and never written. The template inference, the
prefecture resolution and the downgrade guard are all deleted with the
description half; a guard for a thing that no longer happens is just more code.

Labels come from the shinto-label-generator proposal files (`id_proposed.txt`,
`uk.txt`, …). An item with no proposed label yields nothing and waits for the
label pipelines.

Output: description_label_pairs.txt — bare `Qxxx|Lxx|"…"` label lines (capped
~100/day in direct_daily_edits via FILE_DAILY_CAPS). Colliding labels are
withheld into description_pair_collision_groups.json for the cloud enrichment
pipeline.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "shinto-label-generator"))
from language_registry import COVERED  # noqa: E402
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact

from shinto_miraheze.ua_for import ua_for

# WDQS pacing. Emma, 2026-08-24: "We need to be properly throttling our own actions so that we
# don't get a gazillion 429s with GitHub Actions." This script had `time.sleep(1)` between SPARQL
# calls while the repo's documented floor is 2.5 — so it ran 2.5x faster than its own rule, in
# VALUES batches of 150 across the whole target set, and 429'd itself out of every weekly refresh
# since 2026-08-02. The 429 was reported for weeks as an external blocker; it was ours.
WDQS_THROTTLE = 2.5
_LAST_CALL = 0.0  # monotonic stamp of the last WDQS request; see sparql()


OUT = os.path.join(HERE, "description_label_pairs.txt")
GROUPS = os.path.join(HERE, "description_pair_collision_groups.json")
PROPOSALS_DIR = os.path.join(REPO, "shinto-label-generator", "quickstatements")
WDQS = "https://query-main.wikidata.org/sparql"
# UA removed 2026-08-19: the request sites now resolve the agent from the URL via
# ua_for(), so this hand-built literal was dead and could only drift. Was: UA = f"shintowiki-descfix/1.0 (https://shinto.miraheze.org; {contact('wikidata')})"

# (class QID, extra pattern) — same classes the label pipelines cover
CLASSES = [
    ("Q845945", ""),                                   # Shinto shrine
    ("Q5393308", "?item wdt:P17 wd:Q17 ."),            # Buddhist temple (Japan)
]


def sparql(query, retries=3):
    """Every WDQS call in this script and in generate_description_adds.py goes through here.

    The throttle lives INSIDE this function on purpose. It used to sit at the call sites, which
    meant the VALUES-batch loop was paced and the four other call sites were not paced at all —
    so the script could fire several queries back to back and 429 itself out of the run. Pacing
    the transport rather than the callers is the only version that cannot be forgotten by a new
    caller. Emma, 2026-08-24: "You just want to rate limit within your scripts."
    """
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": ua_for(url), "Accept": "application/sparql-results+json"})
    global _LAST_CALL
    gap = time.monotonic() - _LAST_CALL
    if gap < WDQS_THROTTLE:
        time.sleep(WDQS_THROTTLE - gap)
    _LAST_CALL = time.monotonic()
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                if r.status == 429:
                    raise SystemExit("429 from WDQS — bailing.")
                return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise SystemExit("429 from WDQS — bailing.")
            if attempt == retries - 1:
                raise
            wait = 30 * (attempt + 1)
            print(f"  {e.code} — retrying in {wait}s", flush=True)
            time.sleep(wait)


def langs_with_targets(cls, extra):
    q = f"""
    SELECT ?lang (COUNT(DISTINCT ?item) AS ?n) WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item schema:description ?d .
      BIND(LANG(?d) AS ?lang)
      FILTER NOT EXISTS {{ ?item rdfs:label ?l . FILTER(LANG(?l) = ?lang) }}
    }} GROUP BY ?lang
    """
    return {b["lang"]["value"]: int(b["n"]["value"]) for b in sparql(q)}


def corpus_and_targets(cls, extra, lang):
    """{qid: (desc, has_label, None)} for every item of cls with a desc@lang.

    One cheap query. It used to run a second and third — the 47 prefecture labels
    and then each target's own prefecture in VALUES batches of 150 — to fill a
    description template. With the description half gone there is nothing to fill,
    so those round trips are gone too; the third element stays only so the tuple
    shape does not churn for callers.
    """
    q = f"""
    SELECT ?item ?d ?hasLabel WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
      BIND(EXISTS {{ ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}") }} AS ?hasLabel)
    }}
    """
    out = {}
    for b in sparql(q):
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        out[qid] = (b["d"]["value"], b["hasLabel"]["value"] == "true", None)
    return out


def existing_pairs(cls, extra, lang):
    """{(label, desc)} already on this class's items in this language — the
    EXTERNAL side of the uniqueness rule (docs/description_enrichment_pipeline.md).
    Class-scoped: cross-class collisions are overwhelmingly same-class."""
    q = f"""
    SELECT ?l ?d WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}")
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
    }}
    """
    return {(b["l"]["value"], b["d"]["value"]) for b in sparql(q)}


def load_label_proposals():
    """(qid, lang) -> proposed label, from every shinto-label-generator output."""
    out = {}
    if not os.path.isdir(PROPOSALS_DIR):
        return out
    row = re.compile(r'^(Q\d+)	L([a-z][a-z0-9-]{1,11})	"(.*)"$')
    for fn in os.listdir(PROPOSALS_DIR):
        if not fn.endswith(".txt"):
            continue
        for ln in open(os.path.join(PROPOSALS_DIR, fn), encoding="utf-8"):
            m = row.match(ln.rstrip("\r\n"))
            if m:
                out.setdefault((m.group(1), m.group(2)), m.group(3))
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    proposals = load_label_proposals()
    print(f"{len(proposals)} label proposals loaded from {PROPOSALS_DIR}")
    covered = set(COVERED)
    lines, report, collisions = [], [], []
    for cls, extra in CLASSES:
        counts = langs_with_targets(cls, extra)
        time.sleep(WDQS_THROTTLE)
        for lang in sorted(counts, key=counts.get, reverse=True):
            if lang not in covered or counts[lang] == 0:
                continue
            items = corpus_and_targets(cls, extra, lang)
            time.sleep(WDQS_THROTTLE)
            # The uniqueness rule, which is the ONLY thing the description is
            # consulted for now: the post-edit (label, description) pair must be
            # unique both within our own proposals and against pairs already on
            # Wikidata. A colliding label is WITHHELD into the collision groups
            # for the cloud enrichment pipeline rather than forced.
            taken = existing_pairs(cls, extra, lang)
            units = []   # (qid, label, existing_desc)
            no_proposal = 0
            for qid, (desc, has_label, _pref) in sorted(items.items()):
                if has_label:
                    continue
                label = proposals.get((qid, lang))
                if not label:
                    no_proposal += 1
                    continue
                units.append((qid, label, desc))

            by_pair = defaultdict(list)
            for qid, label, desc in units:
                by_pair[(label, desc)].append(qid)
            withheld = 0
            for qid, label, desc in units:
                pair = (label, desc)
                if len(by_pair[pair]) > 1 or pair in taken:
                    withheld += 1
                    collisions.append({"lang": lang, "class": cls, "label": label,
                                       "proposed": desc, "items": by_pair[pair],
                                       "external": pair in taken})
                    continue
                lesc = label.replace('"', '""')
                lines.append(f'{qid}|L{lang}|"{lesc}"')
            report.append(f"{cls} {lang}: targets={counts[lang]} "
                          f"label-lines={len(units) - withheld} "
                          f"no-proposed-label={no_proposal} label-withheld={withheld}")
            time.sleep(WDQS_THROTTLE)

    for line in report:
        print(f"  {line}")
    lines = sorted(set(lines))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"\n{len(lines)} LABEL lines -> {OUT}")
    with open(GROUPS, "w", encoding="utf-8") as f:
        json.dump(collisions, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{len(collisions)} withheld labels -> {GROUPS}")


if __name__ == "__main__":
    main()
