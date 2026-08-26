#!/usr/bin/env python3
"""
generate_french_elision_fixes.py
================================
Fix French shrine labels that write "sanctuaire **de** Ōminakami" where French
requires "sanctuaire **d’**Ōminakami".

Emma 2026-08-04: *"de Ō should be corrected to d'Ō across them with an additional
pipeline thing that makes the quickstatements instantly if it is something that
was universal across french language shrines."*

It is universal, and the corpus was measured before anything was written rather
than assumed (2026-08-04, over the 23,892 French-labelled shrine items):

    de  + a true vowel (A E I O U, incl. Ō Ū …)      0
    d’  + a true vowel                           4,675
    d’  + a consonant                                0
    de  + H                                         25
    d’  + H                                      3,645

So the direction Emma named — "de Ō" — DOES NOT EXIST in the data. Real vowels
are already 100% elided, and there are no reverse errors either. The only live
class is H, where the corpus has decided 3,645 to 25 that Japanese h- takes the
elision: "sanctuaire d’Hachiman" and "sanctuaire de Hachiman" both exist, for the
same name, and the first outnumbers the second by 146 to 1. Those 25 are the
inconsistency, and they are what this fixes.

That measurement is the whole point of the script. Elision before a true vowel is
obligatory French, so it needs no judgement — but H is exactly the case where
French grammar does NOT decide (mute h elides, aspirated h does not, and whether
a Japanese h- is either is not a question French answers). Guessing it would have
been an error in either direction: an earlier draft of this file assumed H elides
and would have been right by luck; assuming the strict grammar would have
"corrected" 3,645 correct labels into wrong ones.

The generator stays general rather than hard-coding H, so the first "de Ōmi…"
that any future label pass introduces is caught the next run — that is the
"instantly" Emma asked for.

ONE QUERY. Filtering happens server-side, so this asks WDQS for the labels that
are already wrong rather than pulling every shrine and sorting locally.
`WDQS_THROTTLE` and the 429-bail from generate_genbu_ids are reused, not
re-implemented. (CLAUDE.md: Wikidata is a destination — this is the narrow kind
of question only it can answer, asked once.)

WHAT IT WILL NOT TOUCH:
  * `de` before a consonant — correct as it stands;
  * `du`, `des`, `de la`, `de l’` — different constructions, not elision sites;
  * a label with no "de " at all.

Output: modern-quickstatements/french_elision_fixes.txt (atomic; each line is an
independent label set).

Usage: python shinto_miraheze/generate_french_elision_fixes.py [--limit N]
"""
import argparse
import io
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
for p in (ROOT, os.path.join(ROOT, 'modern-quickstatements')):
    if p not in sys.path:
        sys.path.insert(0, p)

sys.stdout.reconfigure(encoding='utf-8')

from generate_genbu_ids import _sparql  # noqa: E402  (shared throttle + 429 bail)

OUT = os.path.join(ROOT, 'modern-quickstatements', 'french_elision_fixes.txt')
LOG = os.path.join(SCRIPT_DIR, 'local_answers', '_french_elision.log')

SHRINE = 'Q845945'

# The apostrophe fr.wikipedia uses, and the one already dominant in this corpus.
APOS = '’'

# Vowels that take the elision, including the macron forms the macron ruling
# produces (Ō, Ū, …) and H, which this corpus already elides before.
VOWELS = 'AEIOUÀÂÄÉÈÊËÎÏÔÖÙÛÜĀĒĪŌŪHaeiouàâäéèêëîïôöùûüāēīōūh'

# "de" as a standalone word followed by a vowel. `de la`, `des`, `du` are other
# constructions and must not match, hence the explicit word boundary and the
# negative lookahead on the article forms.
DE_BEFORE_VOWEL = re.compile(r'\bde (?!la\b|le\b|l{})([{}])'.format(APOS, VOWELS))

# A literal leading space rather than `\b`, which SPARQL's XPath-flavoured REGEX
# does not implement.
#
# THE REASON THIS QUERY IS PINNED BY A TEST: the first version read `wd:Q%s` with
# SHRINE already holding "Q845945", so it asked for `wd:QQ845945` — an entity
# that does not exist. WDQS answers that with zero rows and no error, which is
# indistinguishable from "the corpus is clean". A generator whose filter is
# broken looks exactly like a generator with no work to do, so the corpus counts
# in the docstring were taken with a separate hand-written query rather than
# trusting this one's silence.
QUERY = """
SELECT ?item ?fr WHERE {
  ?item wdt:P31 wd:%s ;
        rdfs:label ?fr .
  FILTER(LANG(?fr) = "fr")
  FILTER(REGEX(?fr, " de [%s]"))
}
""" % (SHRINE, VOWELS)


def elide(label):
    """`label` with every `de <vowel>` turned into `d’<vowel>`, or None."""
    fixed = DE_BEFORE_VOWEL.sub(lambda m: f'd{APOS}{m.group(1)}', label)
    return fixed if fixed != label else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, help='cap the number of lines emitted')
    args = ap.parse_args()

    print('querying WDQS for French shrine labels with an unelided "de"')
    rows = _sparql(QUERY)
    print(f'{len(rows)} candidate label(s)')

    lines, log, skipped = [], [], 0
    for row in rows:
        qid = row['item']['value'].rsplit('/', 1)[-1]
        label = row['fr']['value']
        fixed = elide(label)
        if not fixed:
            # The server-side regex is deliberately looser than the local one
            # (it cannot express the de la / du exclusions), so some rows are
            # expected to fall out here.
            skipped += 1
            log.append(f'{qid}\tNO CHANGE\t{label}')
            continue
        lines.append(f'{qid}|Lfr|"{fixed}"')
        log.append(f'{qid}\tFIX\t{label}\t->\t{fixed}')
        if args.limit and len(lines) >= args.limit:
            break

    # Sorted at the writer, per DEVLOG 2026-08-21: the query has no stable ordering, so
    # emitting in result order rewrote the whole file on every build — 6 of 25 lines on
    # 2026-08-26, 3 of 10 before that, identical content each time. Small, but these are
    # label overwrites, and a diff that is always noise is one nobody reads.
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        for line in sorted(set(lines)):
            fh.write(line + '\n')
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(log) + '\n')

    print(f'{len(lines)} fix(es) -> {OUT} ({skipped} row(s) needed no change)')
    print(f'log -> {LOG}')


if __name__ == '__main__':
    main()
