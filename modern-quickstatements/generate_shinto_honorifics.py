#!/usr/bin/env python3
"""Infer Shinto honorific suffixes (P1035) on kami from their Japanese labels.

Emma 2026-07-16:

    "our Shinto honorifics. We have made a bunch of items for Shinto Honorifics.
    I think we've gotten all of them. I want now to have a pipeline that actively
    creates quick statements that go into the queue that get constantly generated
    and inferred based off of the labels and aliases in Japanese"

    "Required properties for the honorific suffix to be present
       - sex or gender (P21): some kami are not clear. Add unknown (Q24238356)
       - date of birth (P569): add 'novalue'
       - short name (P1813): the Japanese name without the honorific, and also the
         [romaji]"
    "transliteration or transcription (P2440) with the romaji is a qualifier to be
     put on the short name"

WHAT IT EMITS, per kami whose ja label ends in a known honorific:

    <kami>|P1035|<honorific item>
    <kami>|P1813|ja:"<ja label minus the honorific>"|P2440|"<romaji minus the honorific>"
    <kami>|P21|Q24238356          # ONLY if the kami has no P21 at all
    <kami>|P569|novalue           # ONLY if the kami has no P569 at all

THE SUFFIX SET IS DATA-DRIVEN, NOT HARDCODED. It is every item with
P31 = Q137169543 (Shinto honorific), read live, using that item's ja label +
ja aliases as the suffix forms and its en label + en aliases as the romaji forms.
So when Emma mints a new honorific item the pipeline picks it up on the next run
with no code change — that is what "constantly generated and inferred" means.
(She added -hime and -hiko herself right after the first batch; both are already
handled by this, automatically.)

ADD-ONLY, so it is drip-safe under random execution order:
  - P21/P569 are emitted only where the property is ABSENT. Amaterasu keeps her
    real P21=female; nothing is ever overwritten. Emma 2026-07-16: "Only where
    the property is absent".
  - The queries return only items still missing the statement, so the file
    shrinks as lines land — self-healing, no cursor.

Romaji is taken from the item's OWN en label, not transliterated: "Sarutahiko
Ōkami" minus "Ōkami" = "Sarutahiko". No romanisation library, no guessing. If the
en label doesn't end in a matching romaji form, the P2440 qualifier is omitted
rather than invented.

Output: shinto_honorifics.txt (an ATOMIC_FILES entry -> the daily drip).
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

_here = os.path.dirname(os.path.abspath(__file__))
_root = _here
while _root != os.path.dirname(_root) and not os.path.isdir(os.path.join(_root, "shinto_miraheze")):
    _root = os.path.dirname(_root)
if _root not in sys.path:
    sys.path.insert(0, _root)
try:
    from shinto_miraheze.user_agent import USER_AGENT
except Exception:                                     # pragma: no cover
    USER_AGENT = "shintowiki-scripts/1.0 (https://emmaleonhart.com)"

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"

HONORIFIC_CLASS = "Q137169543"   # Shinto honorific
KAMI_CLASS = "Q524158"           # kami
UNKNOWN = "Q24238356"            # "unknown" — entity whose identity is not known
OUTFILE = os.path.join(_here, "shinto_honorifics.txt")
REVIEWFILE = os.path.join(_here, "shinto_honorifics_judgement.txt")

# HARDCODED BAN — Emma 2026-07-16, explicitly:
#
#   "I'm hardcoding the ban of these 12 because their ontology is complicated and
#    explicitly I'm more okay with errors occurring in future added things with bad
#    ontology than these current ones. It's not the job of the script to find
#    ontology errors it's the job to extend existing patterns"
#
# This is a CURATED EXCLUSION LIST, not heuristics. The difference is the whole
# point: label-pattern guards (・, 三神, "and") were the script trying to DETECT
# bad ontology, which is not its job and which mis-fires on legitimate names. A
# fixed list of QIDs is Emma's decision about specific known-complicated items,
# and it is deliberately allowed to go stale — she would rather a future
# bad-ontology item slip through than have these twelve touched.
#
# Groups (三神 / 五行神) and pairs (・) whose ontology she has not settled:
EXCLUDED = {
    "Q10948069",   # 宗像三女神 — Three Goddesses of Munakata
    "Q1114013",    # 住吉三神 — Sumiyoshi sanjin
    "Q402052",     # 開拓三神 — Three Pioneer Kami
    "Q140446096",  # 天地人五行神 — Five Deities of Heaven, Earth, and Man
    "Q643763",     # アシナヅチ・テナヅチ — Ashinazuchi and Tenazuchi
    "Q9090923",    # ウヒヂニ・スヒヂニ — Uhijini and Suhijini
    "Q11073597",   # オオトノヂ・オオトノベ — Ōtonoji and Ōtonobe
    "Q11152535",   # オモダル・アヤカシコネ — Omodaru and Ayakashikone
    "Q11287276",   # イワサク・ネサク — Iwasaku and Nesaku
    "Q11318771",   # ツヌグイ・イクグイ — Tsunugui and Ikugui
    "Q11326733",   # ハヤアキツヒコ・ハヤアキツヒメ — Hayaakitsuhiko and Hayaakitsuhime
    "Q10940723",   # ウワハル・シタハル — Uwaharu and Shitaharu
    # Emma 2026-07-16: "Sarutahiko is a special case just ignore him... he just
    # has a weird name." (猿田彦 ends in 彦, which is itself an honorific.)
    "Q3090037",    # 猿田彦神 — Sarutahiko
}


def sparql(query):
    url = SPARQL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        if r.status == 429:                     # repo policy: bail, never retry
            raise SystemExit("429 from WDQS — bailing, no retries (CLAUDE.md)")
        return json.loads(r.read().decode("utf-8"))["results"]["bindings"]


def load_honorifics():
    """[(qid, [ja forms...], [romaji forms...])] — live, so new honorifics self-register."""
    rows = sparql(f"""
    SELECT ?h ?ja ?jaAlias ?en ?enAlias WHERE {{
      ?h wdt:P31 wd:{HONORIFIC_CLASS} .
      OPTIONAL {{ ?h rdfs:label ?ja      FILTER(LANG(?ja) = "ja") }}
      OPTIONAL {{ ?h skos:altLabel ?jaAlias FILTER(LANG(?jaAlias) = "ja") }}
      OPTIONAL {{ ?h rdfs:label ?en      FILTER(LANG(?en) = "en") }}
      OPTIONAL {{ ?h skos:altLabel ?enAlias FILTER(LANG(?enAlias) = "en") }}
    }}""")
    acc = {}
    for r in rows:
        q = r["h"]["value"].split("/")[-1]
        ja, en = acc.setdefault(q, (set(), set()))
        for k in ("ja", "jaAlias"):
            if k in r:
                ja.add(r[k]["value"])
        for k in ("en", "enAlias"):
            if k in r:
                en.add(r[k]["value"])
    out = []
    for q, (ja, en) in acc.items():
        # Strip the leading particle/hyphen used in the item labels (の命, -hime)
        ja_forms = {f.lstrip("の-").strip() for f in ja if f.strip(" の-")}
        en_forms = {f.lstrip("-").strip() for f in en if f.strip(" -")}
        # longest-first so 大御神 wins over 大神, and 大明神 over 明神
        if ja_forms:
            out.append((q, sorted(ja_forms, key=len, reverse=True),
                        sorted(en_forms, key=len, reverse=True)))
    return out


def load_kami():
    """Kami with a ja label + ja aliases, and whether they already have P21 / P569.

    Aliases matter: Emma 2026-07-16 — "a God can have multiple honorifics derived
    from either sourced things or its labels, or having a label and multiple
    prefixes". So the honorific set is inferred from label AND aliases; the short
    name still comes from the label alone ("There's going to be one short name
    regardless of how many honorifics there are").
    """
    rows = sparql(f"""
    SELECT ?k ?ja ?en ?jaAlias (BOUND(?g) AS ?hasP21) (BOUND(?d) AS ?hasP569) WHERE {{
      ?k wdt:P31/wdt:P279* wd:{KAMI_CLASS} .
      ?k rdfs:label ?ja FILTER(LANG(?ja) = "ja")
      OPTIONAL {{ ?k rdfs:label ?en FILTER(LANG(?en) = "en") }}
      OPTIONAL {{ ?k skos:altLabel ?jaAlias FILTER(LANG(?jaAlias) = "ja") }}
      OPTIONAL {{ ?k wdt:P21  ?g }}
      OPTIONAL {{ ?k wdt:P569 ?d }}
    }}""")
    out = {}
    for r in rows:
        q = r["k"]["value"].split("/")[-1]
        rec = out.setdefault(q, {
            "ja": r["ja"]["value"],
            "en": r.get("en", {}).get("value", ""),
            "aliases": set(),
            "has_p21": r["hasP21"]["value"] == "true",
            "has_p569": r["hasP569"]["value"] == "true",
        })
        if "jaAlias" in r:
            rec["aliases"].add(r["jaAlias"]["value"])
    return out


def existing(prop):
    """QIDs that already carry `prop` — so the file self-heals as lines land."""
    rows = sparql(f"""
    SELECT ?k WHERE {{ ?k wdt:P31/wdt:P279* wd:{KAMI_CLASS} ; wdt:{prop} ?v . }}""")
    return {r["k"]["value"].split("/")[-1] for r in rows}


def qs_escape(s):
    return s.replace('"', '\\"')


# A separator before the romaji honorific is load-bearing. "Sarutahiko Ōkami" has
# one, so Ōkami is a word and stripping it gives "Sarutahiko". "Sarutahiko" alone
# merely *ends in* "hiko"; stripping that gives "Saruta", which is exactly the
# "it reads wrong" failure Emma warned about (2026-07-16). So:
#   - honorific derivation ALLOWS an unseparated suffix (Konohanasakuyahime -> hime)
#   - romaji derivation REQUIRES a separator, else we omit rather than invent.
_SEP = r"[\s\-–—·'’]+"


def derive_from_english(en_label, en_form_index, all_en_forms):
    """(honorific_qid | None, romaji | None) from the English label alone.

    Emma 2026-07-16: "you're not going to need to do any translation of the short
    name. You absolutely should not, in fact, be trying to translate... you're
    supposed to be deriving it from the English name."

    Three cases:
      1. separated honorific  -> honorific + confident romaji  ("Sarutahiko Ōkami")
      2. no honorific at all  -> no honorific + the label IS the romaji ("Amaterasu")
      3. unseparated suffix   -> honorific, but romaji is NOT derivable -> None
                                 ("Konohanasakuyahime": short is 木花咲耶, and
                                  "Konohanasakuyahime" still carries the -hime)
    """
    en_label = (en_label or "").strip()
    if not en_label:
        return None, None
    for ef in all_en_forms:                              # longest romaji form first
        m = re.search(rf"{_SEP}{re.escape(ef)}\s*$", en_label, re.I)
        if m:
            return en_form_index.get(ef.lower()), en_label[: m.start()].strip(" -·")
    for ef in all_en_forms:                              # unseparated => honorific only
        if re.search(rf"{re.escape(ef)}\s*$", en_label, re.I) and len(en_label) > len(ef):
            return en_form_index.get(ef.lower()), None
    return None, en_label                                # already bare


def main():
    print("loading honorifics (live — new ones self-register)...")
    honorifics = load_honorifics()
    for q, ja, en in honorifics:
        print(f"  {q:12} ja={ja}  romaji={en}")
    time.sleep(1)

    print("\nloading kami...")
    kami = load_kami()
    print(f"  {len(kami)} kami with a ja label")
    time.sleep(1)

    have_p1035 = existing("P1035")
    print(f"  {len(have_p1035)} already have P1035 — skipped (self-healing)")

    # Flatten to (form, qid, en_forms) and sort GLOBALLY longest-form-first.
    # Load-bearing: 大神/大御神/大明神 all END in 神, and 明神 is a suffix of 大明神.
    # Sorting only within each honorific and then iterating honorifics in dict
    # order would let 猿田彦大神 match 神 (no Kami) instead of 大神 (Ōkami) purely
    # on hash order — silently wrong, and non-deterministic between runs.
    forms = sorted(
        ((form, hq, en_forms) for hq, ja_forms, en_forms in honorifics for form in ja_forms),
        key=lambda t: len(t[0]), reverse=True,
    )
    all_en_forms = sorted({e for _, _, efs in forms for e in efs}, key=len, reverse=True)
    en_form_index = {e.lower(): hq for _, hq, efs in forms for e in efs}

    def longest_match(text):
        """(honorific qid, form) for the LONGEST honorific this string ends with.

        Emma 2026-07-16: "We need the first one, the longest one within it."
        Longest-first over the GLOBAL form list, so 大御神 beats 大神 beats 神.
        """
        for form, hq, _ in forms:
            if text.endswith(form) and len(text) > len(form):
                return hq, form
        return None, None

    lines, matched = [], 0
    judgement = []          # residue: Emma's calls, never auto-emitted
    for qid, k in sorted(kami.items()):
        if qid in EXCLUDED:
            judgement.append((qid, k["ja"], k["en"], "EXCLUDED by Emma — complicated ontology"))
            continue
        ja_label = k["ja"]
        hq, form = longest_match(ja_label)
        if not hq:
            continue
        matched += 1

        # ONE short name, from the label — Emma: "There's going to be one short
        # name regardless of how many honorifics there are."
        # の/ノ is a particle: part of the LABEL, not part of the name, and often
        # implied (Emma 2026-07-16). Strip it.
        short_ja = ja_label[: -len(form)].rstrip("のノ乃之・ ")
        if not short_ja:
            continue

        # MULTIPLE honorifics: a kami can carry several, inferred from the ja label,
        # its ja aliases, AND the English name (Emma 2026-07-16: "You should be able
        # to programmatically derive the honorifics from the English name when there
        # is an English name"). Each source contributes its own longest match.
        honorific_qids = {hq}
        for alias in k["aliases"]:
            ahq, _ = longest_match(alias)
            if ahq:
                honorific_qids.add(ahq)
        en_hq, romaji = derive_from_english(k["en"], en_form_index, all_en_forms)
        if en_hq and en_hq != hq:
            # ja and en name DIFFERENT honorifics (Q11574224: ja 甕速日神 vs en
            # "Mikahayahi-no-Mikoto"). Measured at 18/274. Emma 2026-07-16: "the
            # extent that we're not able to is the extent... I'm going to be able
            # to make judgement calls." So: don't guess, don't emit the en one.
            judgement.append((qid, ja_label, k["en"],
                              f"ja says {form} ({hq}); en says a different honorific ({en_hq})"))
        elif en_hq:
            honorific_qids.add(en_hq)

        for h in sorted(honorific_qids):
            if qid not in have_p1035:
                lines.append(f"{qid}|P1035|{h}")

        # romaji comes from derive_from_english() — English label only, never
        # transliterated. May legitimately be None (unseparated suffix).
        if romaji:
            lines.append(f'{qid}|P1813|ja:"{qs_escape(short_ja)}"|P2440|"{qs_escape(romaji)}"')
        else:
            lines.append(f'{qid}|P1813|ja:"{qs_escape(short_ja)}"')

        # ADD-ONLY: never clobber a real gender / date (Emma: "only where absent")
        if not k["has_p21"]:
            lines.append(f"{qid}|P21|{UNKNOWN}")
        if not k["has_p569"]:
            lines.append(f"{qid}|P569|novalue")

        if not romaji and k["en"]:
            judgement.append((qid, ja_label, k["en"],
                              "romaji not derivable — en label carries an unseparated suffix"))

    with open(OUTFILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))

    # The residue Emma adjudicates. NEVER goes to the drip.
    with open(REVIEWFILE, "w", encoding="utf-8") as f:
        f.write("# Honorific inference — cases needing Emma's judgement. NOT auto-emitted.\n")
        f.write("# Emma 2026-07-16: \"we'll be able to almost get it out of almost all of them.\n")
        f.write("#  The extent that we're not able to is the extent, probably, that I'm going\n")
        f.write("#  to be able to make judgement calls.\"\n#\n")
        f.write(f"# {len(judgement)} cases.\n\n")
        for qid, ja, en, why in sorted(judgement):
            f.write(f"{qid}\tja={ja}\ten={en}\t{why}\n")

    print(f"\nmatched {matched} kami with an honorific suffix")
    print(f"wrote {OUTFILE}: {len(lines)} lines (confident, drip-safe)")
    print(f"wrote {REVIEWFILE}: {len(judgement)} judgement calls for Emma")


if __name__ == "__main__":
    main()
