#!/usr/bin/env python3
"""
generate_description_fixes.py
==============================
Description-without-label cleanup (Emma 2026-07-07, [[Open questions]]).

Problem: shrines/temples carry a description in language X but no label in X
(≈10k items; almost all id + uk). A stale description blocks later label adds:
the label+description pair must be unique, and the description is supposed to
be the deduplicator. Rule: fix the DESCRIPTION first (standardized form), and
only then may label-adding QS touch the item.

Method (data-driven, never invented):
  * per (class, language), the standardized description is inferred from the
    corpus of EXISTING descriptions on that class's items: the modal generic
    form, plus a prefecture template ("… di Prefektur {pref}, Jepang"-style)
    when ≥ PREF_SUPPORT existing descriptions contain the item's own
    prefecture label — i.e. we reuse the community's own standard form.
  * a target item (desc@X, no label@X) gets the prefecture form when its
    prefecture label@X is known, else the generic modal.
  * if the description ALREADY equals the target form, the description edit is
    unneeded but the LABEL is not — the item still has no label, which is why it
    is a target. Such items emit a LABEL-ONLY line.

    ⚠ Fixed 2026-08-21. That branch used to `continue`, dropping the label with
    the unneeded description edit, and it had silently stranded every Indonesian
    target: Emma's own 2025 bot pass had already standardized those descriptions
    to "kuil Shinto di Prefektur {pref}, Jepang", so `new == desc` held for all
    5,024 of them and they were counted "already-standard" and skipped on every
    run since. Ukrainian was never standardized, which is why uk produced 3,513
    pairs and id produced nothing. The report now separates `no-template`,
    `already-standard` and `label-only` so this cannot hide in one counter again.

Each output unit is the full PAIR Emma specified — "change description, then
add label" — as ONE compound line (sub-lines joined by "||", executed
sequentially by direct_daily_edits; the label half is skipped if the
description edit fails). The label comes from the shinto-label-generator
proposal files (id_proposed.txt, uk.txt, …); items with no proposed label
get a desc-only line, and the label pipelines pick them up later.

Output: description_label_pairs.txt — `Qxxx|Dxx|"…"||Qxxx|Lxx|"…"` compound
lines, plus bare `Qxxx|Lxx|"…"` label-only lines where the description is
already correct (capped ~100/day in direct_daily_edits via FILE_DAILY_CAPS).
Every label, in either shape, goes through the same (label, description)
uniqueness check — a label-only line forms a pair the moment it lands.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

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
PREF_SUPPORT = 5      # min corpus descriptions containing the prefecture label
GENERIC_SUPPORT = 3   # min corpus frequency for the generic modal form


def sparql(query, retries=3):
    url = WDQS + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": ua_for(url), "Accept": "application/sparql-results+json"})
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
    """{qid: (desc, has_label, pref_label_or_None)} for every item of cls with desc@lang.

    Split into cheap queries — the single joined query with OPTIONAL wdt:P131*
    504'd on the 5k-item languages (2026-07-07):
      1. items + desc + has-label flag (no prefecture);
      2. the 47 prefecture labels@lang (for template inference by substring);
      3. per-item prefecture ONLY for the label-less targets, in VALUES batches.
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
    time.sleep(1)
    targets = [q_ for q_, (_, has, _p) in out.items() if not has]
    for i in range(0, len(targets), 150):
        batch = " ".join(f"wd:{x}" for x in targets[i:i + 150])
        pq = f"""
        SELECT ?item ?prefLabel WHERE {{
          VALUES ?item {{ {batch} }}
          ?item wdt:P131* ?pref . ?pref wdt:P31 wd:Q50337 ;
                rdfs:label ?prefLabel . FILTER(LANG(?prefLabel) = "{lang}")
        }}
        """
        for b in sparql(pq):
            qid = b["item"]["value"].rsplit("/", 1)[-1]
            d, has, _ = out[qid]
            out[qid] = (d, has, b["prefLabel"]["value"])
        time.sleep(1)
    return out


def pref_labels(lang):
    """The 47 prefecture labels in this language (for template inference)."""
    q = f"""
    SELECT ?prefLabel WHERE {{
      ?pref wdt:P31 wd:Q50337 ; rdfs:label ?prefLabel .
      FILTER(LANG(?prefLabel) = "{lang}")
    }}
    """
    return [b["prefLabel"]["value"] for b in sparql(q)]


def infer_templates(items, prefs):
    """(pref_template_or_None, generic_or_None) from existing descriptions.
    Prefecture detection by substring against the 47 known pref labels@lang —
    no per-item P131 needed for the corpus."""
    prefs = sorted(prefs, key=len, reverse=True)
    pref_forms, generic = Counter(), Counter()
    for desc, _has, _pref in items.values():
        hit = next((p for p in prefs if p and p in desc), None)
        if hit:
            pref_forms[desc.replace(hit, "{pref}")] += 1
        else:
            generic[desc] += 1
    gen = next((d for d, n in generic.most_common(1) if n >= GENERIC_SUPPORT), None)
    # The prefecture template must BEAT the generic modal, not just clear an
    # absolute floor: a handful of polluted legacy descriptions ("kuil Shinto"
    # stamped on Buddhist temples) collapse into one {pref} form and would
    # otherwise outrank a clean 23-strong generic (found 2026-07-07).
    gen_n = generic.most_common(1)[0][1] if gen else 0
    pref_t = next((t for t, n in pref_forms.most_common(1)
                   if n >= PREF_SUPPORT and n >= gen_n), None)
    return pref_t, gen


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
        time.sleep(1)
        for lang in sorted(counts, key=counts.get, reverse=True):
            if lang not in covered or counts[lang] == 0:
                continue
            items = corpus_and_targets(cls, extra, lang)
            time.sleep(1)
            pref_t, gen = infer_templates(items, pref_labels(lang))
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, NO inferable template — skipped")
                continue
            # Build proposals, then apply the uniqueness rule to the LABEL half
            # of each pair: the post-edit (label, desc) must be unique both
            # within our proposals and against existing pairs. Description-only
            # fixes are always safe (an item without a label forms no pair);
            # colliding units are emitted desc-only and their label withheld
            # into the collision groups for the cloud enrichment pipeline.
            time.sleep(1)
            taken = existing_pairs(cls, extra, lang)
            units = []   # (qid, desc_line, label_or_None, new_desc)
            fixed = skipped = already_standard = label_only = 0
            for qid, (desc, has_label, pref) in sorted(items.items()):
                if has_label:
                    continue
                new = (pref_t.replace("{pref}", pref) if (pref_t and pref) else gen)
                if not new:
                    skipped += 1
                    continue
                if new == desc:
                    # The description is ALREADY the standardized form -- but the item
                    # still has no label, which is the entire reason it is a target here.
                    #
                    # This branch used to `continue`, which dropped the LABEL along with
                    # the unneeded description edit. Found 2026-08-21: it had silently
                    # stranded every Indonesian target. Emma's own 2025 bot pass had
                    # already standardized those descriptions to "kuil Shinto di Prefektur
                    # {pref}, Jepang" -- so `new == desc` for all 5,024 of them, and they
                    # were counted as "already-standard" and skipped on every run since.
                    # Ukrainian was never standardized, which is why uk got its 3,513
                    # pairs and id got nothing at all.
                    #
                    # A desc-only "fix" is what is unneeded; the label is not. Emit a
                    # LABEL-ONLY unit, and let it through the identical uniqueness check
                    # below -- once the label lands it forms a (label, description) pair
                    # like any other, so it must be checked like any other.
                    already_standard += 1
                    units.append((qid, None, proposals.get((qid, lang)), desc))
                    continue
                esc = new.replace('"', '""')
                units.append((qid, f'{qid}|D{lang}|"{esc}"',
                              proposals.get((qid, lang)), new))
            by_pair = defaultdict(list)
            for u in units:
                if u[2]:
                    by_pair[(u[2], u[3])].append(u[0])
            withheld = 0
            for qid, desc_line, label, new in units:
                unit = desc_line
                if label:
                    pair = (label, new)
                    if len(by_pair[pair]) > 1 or pair in taken:
                        withheld += 1
                        collisions.append({"lang": lang, "class": cls, "label": label,
                                           "proposed": new, "items": by_pair[pair],
                                           "external": pair in taken})
                        label = None
                parts = []
                if desc_line:
                    parts.append(desc_line)
                if label:
                    lesc = label.replace('"', '""')
                    parts.append(f'{qid}|L{lang}|"{lesc}"')
                if not parts:
                    # Description already standard AND the label withheld as colliding:
                    # genuinely nothing to do for this item on this pass.
                    continue
                lines.append("||".join(parts))
                fixed += 1
                if not desc_line:
                    label_only += 1
            report.append(f"{cls} {lang}: targets={counts[lang]} fix-lines={fixed} "
                          f"(label-only={label_only}) no-template={skipped} "
                          f"already-standard={already_standard} label-withheld={withheld} "
                          f"pref_template={bool(pref_t)}")
    lines = sorted(set(lines))
    with open(GROUPS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(collisions, f, ensure_ascii=False, indent=1)
    print(f"{len(collisions)} withheld-label collision entries -> {GROUPS}")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} description-fix lines -> {OUT}")
    for r in report:
        print(" ", r)


if __name__ == "__main__":
    main()
