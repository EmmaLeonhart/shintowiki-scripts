#!/usr/bin/env python3
"""
generate_multilingual_label_fixes.py
====================================
A corrected English label is not the whole fix. Emma 2026-08-04, on
調田坐一事尼古神社: *"queue up new names replacing all of the wrong names on 'hikida
Shrine' not just the english one. It's wrong in French and Indonesian too."*

She is right, and it is not one item. The non-English labels were built FROM the
English ones, so every bad reading was copied outward: 寒川神社 carries
"sanctuaire de Samugawa" and "Kuil Samugawa" beside the en "Samugawa Shrine" this
pipeline has just corrected to Samukawa. Fixing only en leaves the same error
standing in two more languages and makes the item inconsistent with itself.

WHAT THIS DOES. For every `Qxxx|Len|"..."` already staged in
`label_typo_fixes.txt`, it fetches the item's labels in every language, works out
which NAME changed, and rewrites any other-language label built on the old one.

HOW THE NAME IS FOUND, and why not a diff. The generic part of a shrine label
differs per language ("Shrine", "sanctuaire de", "Kuil"), so the only shared
substring is the name itself. Both the old and new English labels are stripped of
their generic words to leave a stem — "Samugawa Shrine" -> Samugawa, "Yasui
Kompira-gū" -> Yasui Kompira — and a foreign label is rewritten only if it
CONTAINS the old stem. Anything else is left alone: a label that does not carry
the bad name has nothing wrong with it.

FRENCH ELISION IS HANDLED. "sanctuaire d'Hikida" cannot become "sanctuaire
d'Tsukudanimasu" — French elides before a vowel sound only. The rewrite switches
d'/d’ to "de " when the incoming stem starts with a consonant, and "de " to "d’"
when it starts with a vowel.

WHAT IT REFUSES:
  * ja and its variants — the Japanese label is the source of truth here and is
    never touched;
  * a language whose label does not contain the old stem;
  * a stem shorter than 3 characters, which would match inside unrelated words;
  * an item whose current en label is no longer the old one (someone has already
    fixed it), because the stem would then be wrong.

Output: modern-quickstatements/multilingual_label_fixes.txt (atomic; each line is
an independent label set, so order does not matter and the drip can take them one
at a time).

Read-only against Wikidata (wbgetentities, 50 ids/request). No SPARQL.

Usage: python shinto_miraheze/generate_multilingual_label_fixes.py [--verbose]
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = os.path.join(ROOT, 'modern-quickstatements', 'label_typo_fixes.txt')
OUT = os.path.join(ROOT, 'modern-quickstatements', 'multilingual_label_fixes.txt')
LOG = os.path.join(SCRIPT_DIR, 'local_answers', '_multilingual_label_fixes.log')
WD_API = 'https://www.wikidata.org/w/api.php'
THROTTLE = 0.5

# Never rewritten: the Japanese label is what everything else is derived FROM.
SKIP_LANGS = {'ja', 'ja-hani', 'ja-hira', 'ja-kana', 'ja-latn'}

# Generic shrine words, stripped from both English labels to leave the name.
# Longest first so "Shrine" does not eat the "-jinja" cases before they match.
GENERIC = [
    ' Grand Shrine', ' Shrine', '-jinja', '-jingū', '-jingu', '-gū', '-gu',
    ' Jinja', ' Jingū', ' Jingu', ' Daijinja', ' Daijingū', ' Daijingu',
    ' Taisha', '-taisha', ' Tenmangū', ' Tenmangu', ' Shinmeisha', '-sha',
]

FR_ELIDE = re.compile(r"\bd[’']\s*", re.I)
FR_DE = re.compile(r"\bde\s+", re.I)
# What French elides before, for THIS corpus. Three things earned their place:
#   * the MACRON vowels — after the macron ruling most corrected stems begin Ō,
#     and without them "d’Oominakami" was being turned into "de Ōminakami";
#   * H is included because the existing French labels already elide before it
#     ("sanctuaire d’Harami"), so treating Japanese h- as mute keeps the house
#     form rather than imposing a different one;
#   * Y is EXCLUDED — it is a consonant sound here, and including it turned
#     "sanctuaire de Yagiri" into "d’Yakiri".
VOWELISH = tuple('AEIOUÀÂÄÉÈÊËÎÏÔÖÙÛÜĀĒĪŌŪH'
                 'aeiouàâäéèêëîïôöùûüāēīōūh')


# Aliases to ADD alongside the label replacements. A replaced label is normally
# a misreading and deserves to disappear — but not always, and 調田坐一事尼古神社 is
# the case that proves it: "hikida" looked like garbage and is not. The item's own
# ja aliases include 疋田神社, read ひきだ, so Hikida is a genuinely attested
# alternative name for this shrine; it was only ever wrong as the PRIMARY label.
# Emma 2026-08-04: "Hikida capitalized should be an alias and the one in the
# different languages should be like that."
#
# This is deliberately a hand-kept list, not a rule. Aliasing every replaced label
# would preserve the misreadings too — Samugawa for 寒川 is simply wrong and must
# not survive as an alias.
ALIASES = {
    'Q22119431': {                      # 調田坐一事尼古神社 / 疋田神社
        'en': 'Hikida Shrine',
        'fr': 'sanctuaire d’Hikida',
        'id': 'Kuil Hikida',
    },
}


def get(params):
    params = dict(params, format='json', formatversion='2')
    req = urllib.request.Request(
        WD_API + '?' + urllib.parse.urlencode(params),
        headers={'User-Agent': WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def split_label(label):
    """(name, generic suffix) for an English shrine label.

    Each generic is tried with AND without its leading separator, because the
    two English labels are not always punctuated the same way: 岡田宮 went from
    "Okagagū" to "Okada-gū", and matching only "-gū" would leave the old side's
    stem as "Okagagū" — so the French label would lose its gū entirely.
    """
    s = (label or '').strip()
    for g in GENERIC:
        for cand in (g, g.lstrip(' -')):
            if len(cand) >= 2 and s.lower().endswith(cand.lower()):
                head = s[: -len(cand)].strip(' -')
                if len(head) >= 3:
                    return head, s[len(s) - len(cand):]
    return s.strip(' -'), ''


def rewrite(label, old, new, old_suffix, new_suffix, lang):
    """`label` with the old name swapped for the new, keeping the phrasing.

    Returns None when the label does not carry the old name at all — the common
    case for a language that translated the name rather than transliterating it.
    """
    m = re.search(re.escape(old), label, re.I)
    if not m:
        return None
    out = label[:m.start()] + new + label[m.end():]

    # The generic part can be wrong too, and the stem swap cannot reach it:
    # "sanctuaire de Yasui Kompira-gu" needs the macron on -gū even though the
    # name either side of it is identical.
    if old_suffix and new_suffix and old_suffix != new_suffix \
            and out.lower().endswith(old_suffix.lower()):
        out = out[: len(out) - len(old_suffix)] + new_suffix

    if lang.startswith('fr'):
        # Only touch the article when the name's vowel class actually FLIPS.
        # Rewriting whenever anything changed is what turned an untouched
        # "sanctuaire de Yasui Kompira" into "d’Yasui Kompira".
        was, now = old[:1] in VOWELISH, new[:1] in VOWELISH
        if was != now:
            head = out[:m.start()]
            if not now and FR_ELIDE.search(head):
                out = FR_ELIDE.sub('de ', head, count=1) + out[m.start():]
            elif now and FR_DE.search(head) and not FR_ELIDE.search(head):
                out = FR_DE.sub('d’', head, count=1) + out[m.start():]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    fixes = {}
    for line in open(SRC, encoding='utf-8'):
        p = line.strip().split('|')
        if len(p) == 3 and p[1] == 'Len':
            fixes[p[0]] = p[2].strip('"')
    print(f'{len(fixes)} staged English label fixes')

    qids = sorted(fixes)
    entities = {}
    for i in range(0, len(qids), 50):
        data = get({'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 50]),
                    'props': 'labels'})
        entities.update(data.get('entities') or {})
        time.sleep(THROTTLE)
        print(f'  fetched {min(i + 50, len(qids))}/{len(qids)}')

    lines, log = [], []
    touched = set()
    for qid in qids:
        ent = entities.get(qid) or {}
        labels = ent.get('labels') or {}
        old_en = (labels.get('en') or {}).get('value')
        new_en = fixes[qid]
        if not old_en:
            log.append(f'{qid}\tSKIP\tno en label on the item')
            continue
        if old_en == new_en:
            log.append(f'{qid}\tSKIP\ten label is already "{new_en}" — the fix has landed')
            continue
        old_stem, old_suffix = split_label(old_en)
        new_stem, new_suffix = split_label(new_en)
        if len(old_stem) < 3:
            log.append(f'{qid}\tSKIP\tstem "{old_stem}" too short to match safely')
            continue
        for lang, val in sorted(labels.items()):
            if lang in SKIP_LANGS or lang == 'en':
                continue
            fixed = rewrite(val['value'], old_stem, new_stem,
                            old_suffix, new_suffix, lang)
            if fixed is None or fixed == val['value']:
                continue
            lines.append(f'{qid}|L{lang}|"{fixed}"')
            log.append(f'{qid}\t{lang}\t{val["value"]}\t->\t{fixed}')
            touched.add(qid)
            if args.verbose:
                print(f'  {qid} {lang}: {val["value"]} -> {fixed}')

    for qid, by_lang in sorted(ALIASES.items()):
        for lang, value in sorted(by_lang.items()):
            lines.append(f'{qid}|A{lang}|"{value}"')
            log.append(f'{qid}\t{lang}\tALIAS ADDED\t->\t{value}')
            touched.add(qid)

    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        for line in lines:
            fh.write(line + '\n')
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(log) + '\n')

    langs = {}
    for line in lines:
        lang = line.split('|')[1][1:]
        langs[lang] = langs.get(lang, 0) + 1
    print(f'\n{len(lines)} label lines over {len(touched)} items -> {OUT}')
    print('  by language: ' + ', '.join(f'{k}={v}' for k, v in sorted(langs.items())))
    print(f'log -> {LOG}')


if __name__ == '__main__':
    main()
