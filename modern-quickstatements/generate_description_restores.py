"""
generate_description_restores.py
================================
Put the prefecture back into descriptions that carry only the generic form.

Emma, 2026-09-10: *"we're actively worsening Ukrainian descriptions why is this?
Turning descriptive ones into generic highly duplicative ones"*.

GENERATOR ONLY — writes QuickStatements lines into an atomic .txt file that the
single daily submitter runs. It never edits Wikidata and the lines carry no edit
summaries (CLAUDE.md "Wikidata editing — ONE path only").

## What happened

`generate_description_fixes.py` uses the PREFECTURE form of a description when it
can resolve the item's prefecture and the GENERIC modal otherwise. Prefecture
detection was a case-sensitive substring test against the full prefecture label,
and Ukrainian labels the item `Префектура Наґано` while writing descriptions
`…у префектурі Наґано, Японія`; Dutch labels it `Prefectuur Nagano` and writes
`…in de prefectuur Nagano, Japan`. Neither ever matched, so nine languages
inferred no prefecture template at all and every target in them was given the
generic:

    Q100902082, 2026-09-10T01:10:41Z
      before  Синтоїстське святилище у префектурі Наґано, Японія
      after   синтоїстське святилище в Японії

That is fixed in `generate_description_fixes.pref_keys`, and a rule there now
refuses to replace a description naming the item's prefecture with one that does
not. This script repairs the items already flattened.

## ⭐ It reads WIKIDATA, not our edit history

Emma, 2026-09-10: *"please don't walk contributions whatever that means. Walk
wikidata."*

The first version paged `list=usercontribs` for our bot account, matched
`wbsetdescription-set` comments, and read the parent revision of each to recover
the string that had been there. That makes the repair depend on who made the
edit, on a scan window, and on revision history staying readable — three things
that have nothing to do with whether an item's description is right.

**The state of the item is the whole question.** A shrine whose description is
the bare generic modal, and whose prefecture Wikidata knows, should carry the
prefecture form — whoever flattened it, and whether or not anything flattened it.
So the selector is one SPARQL query per language: items of the class with a
description in that language and a resolvable prefecture. Everything else falls
out client-side.

This also repairs items we never touched, which is not scope creep: the proposed
value is the same value `generate_description_fixes` would propose if the item
were still one of its targets. It stops being a target the moment its label
lands, which is exactly what happened to the items we damaged — they were fixed
and labelled in the same compound line, so the fix generator will never look at
them again.

## The rule

Emit where **the description is exactly the class/language generic modal and the
item's prefecture has a spelling attested in the corpus.**

  * Anything that is not the generic modal is left alone — it either already
    names its prefecture or it is somebody's own prose, and this repairs a
    flattening rather than normalising descriptions at large.
  * An item whose prefecture the corpus never spells is skipped: there is nothing
    to put in the slot that would not be invented.

Self-healing on both sides: as the restores land the items stop matching, and an
item a human repairs stops matching too. It cannot fight a person.

Verified 2026-09-10 against 12 items whose pre-flattening value is in their
revision history: **12 of 12 proposals are byte-identical to the string that was
there**, derived from Wikidata's present state alone.

## ⚠ What this cannot reach

Six languages — nl, it, es, cs, ca, vi — hold **21 flattened items between them**
that will NOT be repaired. Their corpora never had many prefecture-form
descriptions, we flattened most of what there was, and what remains is under
`MIN_PREFECTURES`. There is no template to infer and no honest way to invent one,
so the script says so and emits nothing for them. That is the real cost of
reading state instead of history, and it is 21 items.

Output: description_restores.txt
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

import argparse
import collections
import io
import os
import shutil
import sys
import time

import requests

_usys.path.insert(0, _uos.path.dirname(_uos.path.abspath(__file__)))
from generate_description_fixes import CLASSES  # noqa: E402

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
UA = WIKIDATA_USER_AGENT
OUTPUT_FILE = "description_restores.txt"
WDQS_THROTTLE = 2.5

# Corpus descriptions that carry a prefecture, below which the template is not
# trusted. The Buddhist-temple class clears nothing like this in uk — its
# descriptions are 2,294 copies of the shrine generic — and that is the point.
MIN_PREF_SUPPORT = 20

# How many of the most common non-generic descriptions the template is read from.
TEMPLATE_SAMPLE = 6

# Distinct prefectures that must be spelled in the corpus before the template is
# used to write anything. A template validated by two prefectures is a template
# validated by nothing.
MIN_PREFECTURES = 5

# The languages the flattening actually reached.
#
# ⚠ `id` is deliberately ABSENT although it runs clean. Indonesian's prefecture
# template never failed — its labels are uninflected `Prefektur Nagano`, which is
# why the whole bug looked Ukrainian — so no Indonesian description was ever
# flattened by us. Including it emitted 1,737 lines, and every one of them was
# standardisation work nobody asked for riding in on a repair batch. Add it back
# only on a decision to standardise, not as a side effect of this.
#
# fr and de are kept because they were queried while sizing the damage and cost
# one round trip each to confirm they produce nothing.
LANGS = ["uk", "nl", "it", "es", "cs", "pl", "ru", "ca", "vi", "fr", "de"]

def sparql(query, retries=3):
    """One POSTed query, spaced WDQS_THROTTLE from the last."""
    for attempt in range(1, retries + 1):
        time.sleep(WDQS_THROTTLE)
        try:
            r = requests.post(SPARQL_ENDPOINT,
                              data={"query": query, "format": "json"},
                              headers={"User-Agent": UA,
                                       "Accept": "application/sparql-results+json"},
                              timeout=300)
        except requests.exceptions.ReadTimeout:
            if attempt < retries:
                time.sleep(10 * attempt)
                continue
            print("  SPARQL timed out after retries")
            return None
        if r.status_code == 429:
            raise SystemExit("429 from WDQS — bailing (CLAUDE.md 429 policy).")
        if r.status_code in (500, 502, 503, 504):
            if attempt < retries:
                time.sleep(15 * attempt)
                continue
            print(f"  SPARQL {r.status_code} after retries")
            return None
        r.raise_for_status()
        try:
            return r.json()["results"]["bindings"]
        except ValueError:
            # A 200 carrying truncated JSON: WDQS cutting a large result off
            # mid-stream. It presents as a JSONDecodeError deep in requests, and
            # unhandled it takes the whole run down after several languages have
            # already been queried — so it is retried like any other transport
            # failure rather than crashing.
            if attempt < retries:
                time.sleep(15 * attempt)
                continue
            print("  SPARQL returned truncated JSON after retries")
            return None
    return None


def items_with_descriptions(cls, extra, lang):
    """[(qid, description, prefecture-QID)] — every item of the class carrying a
    description in this language, with the prefecture Wikidata resolves for it.

    The prefecture is carried as its QID, not its label. The label is the wrong
    handle: Wikidata's uk label for 長野県 is `Префектура Нагано` while the
    descriptions on 2,322 shrines spell it `Наґано`, and Aichi is `Айчі` in the
    label and `Айті` in the descriptions. Filling a description slot from the
    label would introduce a second spelling alongside the community's own.
    """
    q = f"""
    SELECT ?item ?d ?pref WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
      ?item wdt:P131* ?pref .
      ?pref wdt:P31 wd:Q50337 .
    }}
    """
    rows = sparql(q)
    if rows is None:
        return None
    out = {}
    for b in rows:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        out.setdefault(qid, (b["d"]["value"],
                             b["pref"]["value"].rsplit("/", 1)[-1]))
    return [(q_, d, p) for q_, (d, p) in sorted(out.items())]


def _common_affixes(strings):
    """(longest common prefix, longest common suffix) across the strings.

    Both are running MINIMA. An earlier version assigned rather than min'd the
    suffix, so the answer came from whichever string happened to be last."""
    first = strings[0]
    pre = len(first)
    for s in strings[1:]:
        i = 0
        while i < min(pre, len(s)) and first[i] == s[i]:
            i += 1
        pre = i
    suf = len(first) - pre
    for s in strings[1:]:
        i = 0
        limit = min(suf, len(s) - pre)
        while i < limit and first[-1 - i] == s[-1 - i]:
            i += 1
        suf = min(suf, i)
    return first[:pre], (first[len(first) - suf:] if suf else "")


def infer_corpus_forms(rows, min_support=MIN_PREF_SUPPORT):
    """(template, generic, {prefecture QID: spelling}) read off the descriptions
    themselves — no prefecture label involved anywhere.

    The generic modal is the single most common description. The template comes
    from the most common of the OTHERS: `Синтоїстське святилище у префектурі
    Айті, Японія` (241 items) and `…Осака, Японія` (237) differ in nothing but
    the slot, so their common prefix and suffix ARE the template.

    Taking a common affix over ALL the non-generic descriptions does not work,
    and both ways of failing were measured here rather than guessed:

      * across the whole corpus, one line of real prose ("гора в Японії", "гора"
        = mountain) drives the common prefix to nothing;
      * bucketing by opening and using the largest bucket still fails, because
        the bucket holds one `Синтоїстське святилище в Японії` — a capitalised
        variant of the generic — whose tail is `в Японії` against the template's
        `, Японія`, and a single mismatch zeroes the common suffix.

    Using the modal few sidesteps both: an outlier is by definition not modal.
    The template is then validated by harvesting against the WHOLE corpus, so a
    wrong guess would show up as almost no spellings resolved.

    Each spelling is the community's own — which is what makes this reproduce
    `Наґано`, on 2,322 sibling shrines, rather than the `Нагано` of Wikidata's
    prefecture LABEL. The item's own P131 says which prefecture it belongs to.

    Returns (None, None, {}) when the corpus does not support it. That is the
    honest answer for the Buddhist-temple class, whose uk descriptions are 2,294
    copies of the SHRINE generic: there is no temple prefecture form to infer,
    and filling one in from the shrine corpus would make a wrong description more
    confident rather than repair anything.
    """
    counts = collections.Counter(d for _q, d, _p in rows)
    if not counts:
        return None, None, {}
    gen = counts.most_common(1)[0][0]
    specific = [(q, d, p) for q, d, p in rows if d != gen]
    if len(specific) < min_support:
        return None, None, {}

    modal = [d for d, n in collections.Counter(
        d for _q, d, _p in specific).most_common(TEMPLATE_SAMPLE) if n >= 2]
    if len(modal) < 2:
        return None, None, {}
    pre, suf = _common_affixes(modal)
    if not pre or not suf:
        return None, None, {}

    spellings = collections.defaultdict(collections.Counter)
    for _q, d, pref in specific:
        if not d.startswith(pre) or not d.endswith(suf) or len(d) <= len(pre) + len(suf):
            continue
        middle = d[len(pre):len(d) - len(suf)]
        # A spelling is one place-name: no punctuation, no clause. Anything else
        # means this description is not the template with its slot filled, it is
        # prose that happens to share an opening and an ending.
        if len(middle) <= 24 and not any(c in middle for c in ",;:()"):
            spellings[pref][middle] += 1
    # Two independent items must agree on a spelling before it is used to write
    # anything: one item agreeing with itself is not corpus evidence.
    resolved = {pref: c.most_common(1)[0][0] for pref, c in spellings.items()
                if c.most_common(1)[0][1] >= 2}
    if len(resolved) < MIN_PREFECTURES:
        return None, None, {}
    return pre + "{pref}" + suf, gen, resolved


def build_lines(rows, template, gen, spellings):
    """([(qid, new_description)], verdicts) for every item whose description is
    exactly the generic modal and whose prefecture has a known spelling."""
    lines, verdicts = [], collections.Counter()
    if not (template and gen and spellings):
        verdicts["no prefecture form inferable from this corpus"] += len(rows)
        return lines, verdicts
    for qid, desc, pref in rows:
        if desc != gen:
            # Either it already names its prefecture or it is somebody's own
            # prose. Either way there is nothing here to repair — this script
            # undoes a flattening, it does not normalise descriptions at large.
            verdicts["not the generic form — left alone"] += 1
            continue
        spelling = spellings.get(pref)
        if not spelling:
            verdicts["prefecture not spelled anywhere in the corpus"] += 1
            continue
        new = template.replace("{pref}", spelling)
        if new == desc:
            verdicts["already correct"] += 1
            continue
        lines.append((qid, new))
        verdicts["RESTORE"] += 1
    return lines, verdicts


def publish_to_site(path):
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--stats", action="store_true", help="report only, write nothing")
    ap.add_argument("--langs", nargs="*", default=LANGS)
    args = ap.parse_args()

    print("=== Restore the prefecture to flattened descriptions ===\n")
    lines, report = [], []
    for cls, extra in CLASSES:
        for lang in args.langs:
            rows = items_with_descriptions(cls, extra, lang)
            if rows is None:
                report.append(f"{cls} {lang}: QUERY FAILED — skipped")
                continue
            if not rows:
                continue
            template, gen, spellings = infer_corpus_forms(rows)
            pairs, verdicts = build_lines(rows, template, gen, spellings)
            for qid, new in pairs:
                esc = new.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{qid}|D{lang}|"{esc}"')
            report.append(
                f"{cls} {lang}: {len(rows)} with a description and a prefecture; "
                + ", ".join(f"{v}={n}" for v, n in verdicts.most_common()))
            if verdicts["RESTORE"]:
                q0, n0 = pairs[0]
                print(f"  {cls} {lang}: {verdicts['RESTORE']} to restore, "
                      f"e.g. {q0} -> {n0!r}")

    for line in report:
        print(f"  {line}")

    if args.stats:
        print(f"\n--stats: {len(lines)} lines would be written")
        return

    path = args.out if os.path.dirname(args.out) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.out)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    publish_to_site(path)
    print(f"\nWrote {len(lines)} lines to {path}")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
