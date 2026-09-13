#!/usr/bin/env python3
"""
generate_description_adds.py
=============================
The description MAKER (Emma 2026-07-07, [[Open questions]]): shrines/temples
that HAVE a label in language X but no description in X get the standardized
description — "only after the label exists". Sibling of
generate_description_fixes.py (which handles the inverse desc-without-label
case as desc-then-label pairs) and reuses its machinery: templates inferred
from each language's own existing-description corpus (modal generic +
prefecture form), per-item prefectures fetched in VALUES batches.

Backlog at build time: 40,794 items across 54 covered languages
(fr 23,216 / id 14,197 / zh family ~2,100 / long tail). Languages whose
corpus supports no template are skipped, never guessed.

Output: description_adds.txt — plain `Qxxx|Dxx|"…"` lines (uncapped in the
daily drip; simple single adds, unlike the ordered pairs).
"""
import io
import os
import json
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from generate_description_fixes import (  # noqa: E402
    CLASSES, sparql, existing_pairs)

# ⚠ `pref_labels`, `pref_keys` and `infer_templates` LIVE HERE NOW, below.
#
# They used to be imported from generate_description_fixes, and on 2026-09-11
# commit 47b42aff deleted them from it — correctly, because that script became
# label-only and *"a guard for something that no longer happens is just more code
# to mislead someone later"*. What it did not do was check the other importer.
# This script then died at IMPORT for two days:
#
#     ImportError: cannot import name 'pref_labels' from 'generate_description_fixes'
#
# and nothing said so, because the step is `continue-on-error` with an `|| echo`
# that blames HTTP 429. `description_adds.txt` last regenerated 2026-08-25 and
# went on dripping the whole time.
#
# They are copied here rather than restored there: composing a description is
# this script's job (step 3 of docs/description_label_policy.md, Emma 2026-08-21:
# *"If item has a label and no description, add a programmatically generated fill
# in the blanks description"*), and the label-only script must not regrow them.

PREF_SUPPORT = 5      # min corpus descriptions containing the prefecture label
GENERIC_SUPPORT = 3   # min corpus frequency for the generic modal form


def pref_labels(lang):
    """The 47 prefecture labels in this language (for template inference)."""
    q = f"""
    SELECT ?prefLabel WHERE {{
      ?pref wdt:P31 wd:Q50337 ; rdfs:label ?prefLabel .
      FILTER(LANG(?prefLabel) = "{lang}")
    }}
    """
    return [b["prefLabel"]["value"] for b in sparql(q)]


def pref_keys(prefs):
    """{distinctive place-name -> full prefecture label}, for substring matching.

    ⛔ THE WHOLE PREFECTURE TEMPLATE USED TO FAIL IN ANY INFLECTING LANGUAGE, and
    it failed silently, by falling back to the generic modal.

    Matching used the FULL label as a substring. Ukrainian labels these items
    "Префектура Наґано" (nominative) and writes descriptions "…у префектурі
    Наґано, Японія" (locative), so `"Префектура Наґано" in desc` is False for
    every one of the 47. No prefecture form was ever inferred for uk, every uk
    target fell to the generic `синтоїстське святилище в Японії`, and 216 items
    had a prefecture-specific description REPLACED by that identical string
    before Emma caught it on 2026-09-10. Indonesian's "Prefektur Nagano" does not
    decline, which is exactly why id worked and uk did not, and why the bug
    looked like a uk-only oddity rather than a design fault.

    The fix is to match on the part that does NOT inflect. The generic word
    ("Префектура", "Prefektur", "Prefecture") appears in every one of the 47
    labels and is the part that declines; the Japanese place-name does not appear
    in any other label and does not decline. So the shared tokens are dropped and
    what is left is the key.

    Derived from the label set itself rather than a per-language stopword list,
    so it needs no maintenance as languages are added.
    """
    spans = {p: list(re.finditer(r"\w+", p)) for p in prefs if p}
    if not spans:
        return {}
    freq = Counter(t for ms in spans.values() for t in {m.group() for m in ms})
    # A token in most of the 47 labels is the generic word, not a place name.
    common = {t for t, n in freq.items() if n >= max(2, 0.6 * len(spans))}
    keys = {}
    for label, ms in spans.items():
        # Capitalised AND not shared. The capitalisation test is what removes an
        # elision particle: French labels the item "préfecture d'Okayama", and a
        # frequency test alone leaves the "d" (it is in only the vowel-initial
        # labels, well under the threshold). Joining the surviving tokens with a
        # space then produced the key "d Okayama", which is not a substring of
        # anything, and filling the template with it emitted "bâtiment de d
        # Okayama, Japon". Place-names are capitalised in every language sampled,
        # Ukrainian and Czech included.
        picked = [m for m in ms if m.group() not in common and m.group()[:1].isupper()]
        if not picked:
            # No capitalised survivor: fall back to the frequency test alone, for
            # a language that does not capitalise its place-names.
            picked = [m for m in ms if m.group() not in common]
        if not picked:
            continue
        # Slice the ORIGINAL label between the first and last survivor rather than
        # re-joining tokens, so internal punctuation and spacing are whatever the
        # label really has and the key is always a real substring of it.
        key = label[picked[0].start():picked[-1].end()]
        if key:
            keys.setdefault(key, label)
    return keys


def infer_templates(items, keys):
    """(pref_template_or_None, generic_or_None) from existing descriptions.

    Prefecture detection is by substring against the DISTINCTIVE place-name of
    each of the 47 prefecture labels (see pref_keys) — no per-item P131 needed
    for the corpus. The template therefore keeps whatever inflected form of the
    generic word the description used, and `{pref}` carries the place-name
    alone."""
    ordered = sorted(keys, key=len, reverse=True)
    pref_forms, generic = Counter(), Counter()
    for desc, _has, _pref in items.values():
        hit = next((k for k in ordered if k and k in desc), None)
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


def place_tokens(descs, cls_label=""):
    """Tokens that behave like a PLACE NAME in this corpus.

    ⛔ The reason this exists, measured 2026-09-13 against the staged file. The
    generic is the modal description in the corpus, and in several languages the
    modal one names a city:

        fr  x127  "temple bouddhiste à Kyoto, au Japon"
        es  x 71  "templo budista en Yokohama, Japón"
        pl  x 41  "świątynia buddyjska w Jokohamie w Japonii"
        it  x 41  "tempio buddista a Yokohama, Giappone"
        cs  x 25  "buddhistický chrám v japonském městě Jokohama"
        de  x 15  "Shinto-Schrein in Odawara, Kanagawa, Japan"

    It is then stamped on every target with no resolved prefecture, wherever it
    actually is. Of eight sampled `à Kyoto` items, three are in Tokushima,
    Fukushima and Mie. The class-specificity guard below checks the template says
    WHAT the item is; nothing checked that it does not also say WHERE, falsely.

    A prefecture key catches Kyoto, because Kyoto is one of the 47. It does not
    catch Yokohama, Odawara or Sammu, which are cities — so the vocabulary has to
    come from the corpus itself.

    The test is the one `pref_keys` already uses, turned around: a token shared by
    nearly every DISTINCT description is the frame (the class word, the country,
    the preposition); a capitalised token in only a few of them is a place name.
    Counting DISTINCT strings rather than items is what makes it work — "à Kyoto"
    is one string however many items carry it.

    ⚠ `cls_label` is not optional in practice. GERMAN CAPITALISES EVERY NOUN, so
    "Tempel" and "Schrein" score exactly like a place name and the first version of
    this flagged the perfectly good generic "buddhistischer Tempel in Japan". A word
    that names the CLASS is not a place, and the caller already has the class label
    in this language for the specificity guard below.

    A language that does not capitalise its place-names yields nothing here and is
    left exactly as it is today. That is the same limitation `pref_keys` documents,
    and no worse than the status quo.
    """
    class_words = {w for w in re.split(r"\W+", (cls_label or "").lower()) if w}
    distinct = {d for d in descs if d}
    if len(distinct) < 4:
        return set()
    freq = Counter(t for d in distinct
                   for t in {m.group() for m in re.finditer(r"\w+", d)}
                   if t[:1].isupper())
    cutoff = max(2, 0.5 * len(distinct))
    return {t for t, n in freq.items() if n < cutoff and t.lower() not in class_words}


def names_a_place(text, keys, places):
    """Does this template assert a location more specific than the country?"""
    if not text:
        return None
    for k in keys:
        if k and k in text:
            return k
    for t in re.finditer(r"\w+", text):
        if t.group() in places:
            return t.group()
    return None


# WDQS pacing. Emma, 2026-08-24: "We need to be properly throttling our own actions so that we
# don't get a gazillion 429s with GitHub Actions." This script had `time.sleep(1)` between SPARQL
# calls while the repo's documented floor is 2.5 — so it ran 2.5x faster than its own rule, in
# VALUES batches of 150 across the whole target set, and 429'd itself out of every weekly refresh
# since 2026-08-02. The 429 was reported for weeks as an external blocker; it was ours.
WDQS_THROTTLE = 2.5


OUT = os.path.join(HERE, "description_adds.txt")
GROUPS = os.path.join(HERE, "description_collision_groups.json")


def langs_with_label_no_desc(cls, extra):
    q = f"""
    SELECT ?lang (COUNT(DISTINCT ?item) AS ?n) WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l .
      BIND(LANG(?l) AS ?lang)
      FILTER NOT EXISTS {{ ?item schema:description ?d . FILTER(LANG(?d) = ?lang) }}
    }} GROUP BY ?lang
    """
    return {b["lang"]["value"]: int(b["n"]["value"]) for b in sparql(q)}


def desc_corpus(cls, extra, lang):
    """{qid: (desc, True, None)} — existing descriptions, for template inference."""
    q = f"""
    SELECT ?item ?d WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
    }}
    """
    return {b["item"]["value"].rsplit("/", 1)[-1]: (b["d"]["value"], True, None)
            for b in sparql(q)}


def targets_with_pref(cls, extra, lang):
    """{qid: [label, pref_label_or_None]} for items with label@lang but no desc@lang.

    ⛔ `?item wdt:P17 wd:Q17` — THE TARGET MUST BE IN JAPAN, and this is on the
    TARGETS only, deliberately not on CLASSES and not on the corpus.

    Every generic this script can infer names Japan, because the corpus is
    Japan-shaped: *bangunan kuil di Jepang*, *tempel in Japan*, *буддийский храм в
    Японии*. The Buddhist-temple class already carries this filter; the Shinto-shrine
    class does not, so overseas shrines were getting it. Measured 2026-09-13 over the
    819 staged `di Jepang` lines: **325 are in Japan, 98 are demonstrably not** —
    Taiwan 62, Korea under Japanese rule 10, PRC 7, Manchukuo 3, USA 3, Palau, Thailand,
    San Marino — and 397 carry no P17 at all, so the claim is unverified rather than
    false. The colonial-era shrines are the bulk of it: Changchun, Hsinking, Keijō,
    Karenkō.

    Excluding an item with no P17 costs it a description it might have deserved.
    Including it asserts a country nothing in the data supports. The description is,
    in Emma's words, *"a grammatically right fill in the blanks statement"* — a wrong
    blank is worse than an empty one, and the filter self-heals as P17 is added.

    NOT on `CLASSES`: that tuple is shared with the label pipeline, and a LABEL asserts
    no country, so filtering there would drop legitimate label work for no reason.
    NOT on the corpus: template inference wants every existing description it can see.
    """
    q = f"""
    SELECT ?item ?l WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item wdt:P17 wd:Q17 .
      ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}")
      FILTER NOT EXISTS {{ ?item schema:description ?d . FILTER(LANG(?d) = "{lang}") }}
    }}
    """
    out = {b["item"]["value"].rsplit("/", 1)[-1]: [b["l"]["value"], None] for b in sparql(q)}
    time.sleep(WDQS_THROTTLE)
    qids = sorted(out)
    for i in range(0, len(qids), 150):
        batch = " ".join(f"wd:{x}" for x in qids[i:i + 150])
        pq = f"""
        SELECT ?item ?prefLabel WHERE {{
          VALUES ?item {{ {batch} }}
          ?item wdt:P131* ?pref . ?pref wdt:P31 wd:Q50337 ;
                rdfs:label ?prefLabel . FILTER(LANG(?prefLabel) = "{lang}")
        }}
        """
        for b in sparql(pq):
            out[b["item"]["value"].rsplit("/", 1)[-1]][1] = b["prefLabel"]["value"]
        time.sleep(WDQS_THROTTLE)
    return out


_CLASS_LABELS = {}


def class_label(cls, lang):
    """The class item's own label in this language (cached per class)."""
    if cls not in _CLASS_LABELS:
        import urllib.request
        req = urllib.request.Request(
            f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={cls}"
            f"&props=labels&format=json",
            # was a PLAIN string containing "{contact('wikidata')}" -- the braces shipped
            # verbatim, so this request went out with no contact address at all.
            headers={"User-Agent": WIKIDATA_USER_AGENT})
        _CLASS_LABELS[cls] = json.load(urllib.request.urlopen(req))[
            "entities"][cls].get("labels", {})
    return _CLASS_LABELS[cls].get(lang, {}).get("value")


def existing_pairs(cls, extra, lang):
    """{(label, desc)} already on this class's items in this language — the
    EXTERNAL side of the uniqueness rule (docs/description_enrichment_pipeline.md).
    Scoped to the class: cross-class collisions are overwhelmingly same-class
    (same-named shrines); a full-Wikidata pair sweep is not queryable."""
    q = f"""
    SELECT ?l ?d WHERE {{
      ?item wdt:P31 wd:{cls} . {extra}
      ?item rdfs:label ?l . FILTER(LANG(?l) = "{lang}")
      ?item schema:description ?d . FILTER(LANG(?d) = "{lang}")
    }}
    """
    return {(b["l"]["value"], b["d"]["value"]) for b in sparql(q)}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "shinto-label-generator"))
    from language_registry import COVERED
    covered = set(COVERED)
    lines, report, collisions = [], [], []
    for cls, extra in CLASSES:
        counts = langs_with_label_no_desc(cls, extra)
        time.sleep(WDQS_THROTTLE)
        for lang in sorted(counts, key=counts.get, reverse=True):
            if lang not in covered or counts[lang] == 0:
                continue
            corpus = desc_corpus(cls, extra, lang)
            time.sleep(WDQS_THROTTLE)
            # ⛔ pref_keys() is NOT optional, and this call site did not have it.
            # infer_templates matches the prefecture by SUBSTRING, so passing the
            # full labels straight in is the pre-2026-09-10 behaviour that fails
            # in every inflecting language: Ukrainian labels the item
            # "Префектура Наґано" and writes descriptions "…у префектурі
            # Наґано, Японія", so no label is ever found and every uk target falls
            # to the generic. generate_description_fixes was fixed on 2026-09-10;
            # this sibling passed `prefs` where `keys` was expected and was never
            # updated, so it silently kept the fault.
            keys = pref_keys(pref_labels(lang))
            pref_t, gen = infer_templates(corpus, keys)
            # ⛔ A GENERIC MAY NOT NAME A PLACE. The prefecture template may — it
            # fills {pref} from the item's own P131 — but the generic is stamped on
            # every target with no resolved prefecture, so a place name in it is a
            # claim about items that are somewhere else. See place_tokens() for the
            # six languages this was measured on. Dropping it means the language
            # gets no description rather than a wrong one, which is what this
            # script already does for a language with no inferable template.
            places = place_tokens([d for d, _h, _p in corpus.values()],
                                  class_label(cls, lang))
            named = names_a_place(gen, keys, places)
            if named:
                report.append(f"{cls} {lang}: generic {gen!r} names {named!r} — "
                              f"dropped, it would be stamped on items elsewhere")
                gen = None
            # ⛔ AND THE SAME TEST ON THE PREFECTURE TEMPLATE, with {pref} taken
            # out. infer_templates only substitutes the prefecture key, so any
            # OTHER place in the modal description is baked into the template and
            # then repeated on every item. German was the case: the template came
            # out "Shinto-Schrein in Sammu, Präfektur {pref}, Japan" and 104 of
            # the 112 staged de lines named Sammu, a city in Chiba, for items in
            # 30 different prefectures.
            named = names_a_place((pref_t or "").replace("{pref}", ""), keys, places)
            if named:
                report.append(f"{cls} {lang}: pref template {pref_t!r} also names "
                              f"{named!r} — dropped, it is baked in for every item")
                pref_t = None
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, no place-free "
                              f"template — skipped")
                continue
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, NO inferable template — skipped")
                continue
            # CLASS-SPECIFICITY guard: the template must actually SAY what the
            # item is — it must share a content word (≥4 chars) with the
            # class's own Wikidata label in this language ("sanctuaire shinto"
            # / "kuil Shinto" / "buddhistischer Tempel"). Mass-imported junk
            # like "bâtiment de préfecture de X, Japon" shares none and is
            # dropped (2026-07-07/08: two weaker guards let 7-9k junk fr
            # descriptions through; exact cross-class comparison was not
            # enough because each class infers DIFFERENT junk strings).
            cls_label = class_label(cls, lang)
            def _class_true(t):
                if not (t and cls_label):
                    return False
                words = {w for w in re.split(r"\W+", cls_label.lower()) if len(w) >= 4}
                return any(w in t.lower() for w in words)
            if pref_t and not _class_true(pref_t):
                report.append(f"{cls} {lang}: pref template {pref_t!r} lacks class word ({cls_label!r}) — dropped")
                pref_t = None
            if gen and not _class_true(gen):
                report.append(f"{cls} {lang}: generic {gen!r} lacks class word ({cls_label!r}) — dropped")
                gen = None
            if not (pref_t or gen):
                report.append(f"{cls} {lang}: {counts[lang]} targets, no class-true template — skipped")
                continue
            targets = targets_with_pref(cls, extra, lang)
            time.sleep(WDQS_THROTTLE)
            taken = existing_pairs(cls, extra, lang)
            # The uniqueness rule: proposals checked against each other
            # (internal) and against existing pairs (external); colliders are
            # never emitted — they become collision groups for the cloud
            # enrichment pipeline.
            proposals = {}
            for qid, (label, pref) in targets.items():
                new = (pref_t.replace("{pref}", pref) if (pref_t and pref) else gen)
                if new:
                    proposals[qid] = (label, new)
            by_pair = defaultdict(list)
            for qid, pair in proposals.items():
                by_pair[pair].append(qid)
            added = collided = 0
            for pair, qids in sorted(by_pair.items()):
                label, new = pair
                if len(qids) > 1 or pair in taken:
                    collided += len(qids)
                    collisions.append({"lang": lang, "class": cls, "label": label,
                                       "proposed": new, "items": sorted(qids),
                                       "external": pair in taken})
                    continue
                esc = new.replace('"', '""')
                lines.append(f'{qids[0]}|D{lang}|"{esc}"')
                added += 1
            report.append(f"{cls} {lang}: targets={counts[lang]} add-lines={added} "
                          f"collided={collided} pref_template={bool(pref_t)}")
    lines = sorted(set(lines))
    with open(GROUPS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(collisions, f, ensure_ascii=False, indent=1)
    print(f"{len(collisions)} collision groups -> {GROUPS}")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} description-add lines -> {OUT}")
    for r in report:
        print(" ", r)


if __name__ == "__main__":
    main()
