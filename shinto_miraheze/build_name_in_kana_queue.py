#!/usr/bin/env python3
"""
build_name_in_kana_queue.py
===========================
Queue item A0 — give shrines a correct MODERN HIRAGANA P1814 (name in kana),
extracted by an LLM from the jawiki lead.

WHY AN LLM STEP. The reading is present in almost every jawiki article's first
sentence, but it is not reliably regex-extractable: it appears as furigana, as a
bolded parenthetical, sometimes with the shrine's 通称 or a 旧称 in the same
parens, sometimes with okurigana splits across ruby markup. A regex that gets it
right on the easy 80% quietly gets it WRONG on the rest, and a wrong P1814
propagates straight into romaji and en labels. So the lead is handed over whole
and the reading is read out of it.

⚠ NOT the kana-QUALIFIER cleanup. `generate_kana_qualifier_add.py` /
`generate_kana_qualifier_remove.py` are Engishiki-only and undo the opposite
error — ancient-Japanese KATAKANA readings that landed in top-level P1814, which
that pair relocates onto the ojp-hani P1448 and strips from top-level. The two
touch the same property on the same items, so:

  * this builder HOLDS every item the cleanup touches — the 601 (of 2,637) that
    carry an ojp-hani P1448, derived by SPARQL — so the new writer can never
    re-introduce what the cleanup is stripping, and so the ordering question gets
    Emma's eyes before that subset runs, as she asked; and
  * the collector's hard gate is: a katakana-only reading is REJECTED. Katakana
    is the signature of exactly that ancient-reading error. P1814 wants modern
    hiragana.

Emma's instruction on gating: do NOT over-gate on confidence — producing kana is
the priority and the LLM path is high-quality. The katakana exclusion is the gate.

Target set (SPARQL, query-main): ?item wdt:P31 wd:Q845945, has a jawiki sitelink,
and has NO top-level P1814. Two buckets, recorded on each work-file:
  (a) HAS an en label — most likely to carry romanization-derived errors. Priority.
  (b) NO en label — the collector's companion step also generates the en label.

Output: one work-file per item in `name_in_kana/`, carrying the jawiki lead and an
`<!-- ANSWER: -->` marker, exactly like category_translation/ and
label_typo_review/. `collect_name_in_kana.py` turns filled answers into
QuickStatements. Read-only: Wikidata + ja.wikipedia only, no Miraheze request, so
it runs through the 403 blackout.

Usage:
    python build_name_in_kana_queue.py --limit 200        # write 200 work-files
    python build_name_in_kana_queue.py --bucket b         # only the no-en-label set
    python build_name_in_kana_queue.py --stats            # count, write nothing
"""
import argparse
import io
import os
import re
import sys
import time
import urllib.parse

import requests
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(REPO_ROOT, "name_in_kana")

SPARQL = "https://query-main.wikidata.org/sparql"
JA_API = "https://ja.wikipedia.org/w/api.php"
# Was building the agent from the wiki-side contact rather than the Wikidata one, on a
# Wikidata request. The two agents are separate by design; resolve, never hand-build.
# was: a hand-built agent using the wiki-side contact
UA = WIKIDATA_USER_AGENT
HDR = {"User-Agent": UA, "Accept": "application/sparql-results+json"}
THROTTLE = 0.4
BATCH = 20                       # titles per ja.wikipedia extracts call

TARGET_QUERY = """
SELECT ?item ?ja ?en ?art (GROUP_CONCAT(DISTINCT ?cls; separator=",") AS ?classes) WHERE {
  ?item wdt:P31 wd:Q845945 .
  ?art schema:about ?item ; schema:isPartOf <https://ja.wikipedia.org/> .
  FILTER NOT EXISTS { ?item wdt:P1814 ?k }
  OPTIONAL { ?item wdt:P31 ?cls }
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja)="ja") }
  OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en)="en") }
}
GROUP BY ?item ?ja ?en ?art
"""

# Written into the LEAD section when the article yields no extract at all. Says what
# happened and what is still available to derive from, so the answer is a considered
# GUESS or NO_KANA rather than a shrug at an empty section.
NO_LEAD = (
    "(NO LEAD AVAILABLE — the jawiki article is a redirect, a disambiguation page, or "
    "empty, so there is no first sentence to read a reading out of. This will never "
    "change on its own.\n"
    "Answer GUESS if you can derive the reading — from the shrine's own name, from the "
    "place it is named for, or from other shrines carrying the same name, several of "
    "which are already answered in this queue. Answer NO_KANA only if you genuinely "
    "cannot.)"
)

TASK = (
    "<!-- TASK: read the LEAD above and give this shrine's reading as MODERN "
    "HIRAGANA, for Wikidata P1814 (name in kana). Fill ANSWER with exactly one of:\n"
    "  KANA: <hiragana>        the LEAD states this reading\n"
    "  GUESS: <hiragana>       the lead states no reading; this is derived (below)\n"
    "  KATAKANA: <katakana>    the lead gives only an ancient/katakana reading\n"
    "  NO_KANA: <reason>       no reading, and none can be derived either\n"
    "GUESS is what to give when the lead carries no reading (Emma, 2026-08-23: "
    "guess where no kana can be found). Derive it from what you can actually see — "
    "the reading of the place-name the shrine is named for, the readings other "
    "shrines of the same name carry, the reading given in the article's infobox, "
    "categories or first sentence of a section. Shrine names take irregular local "
    "readings, so do NOT transliterate character-by-character: 江島 is えのしま not "
    "えじま, 三吉 is みよし not さんきち, 一宮 can be いっく. If you cannot do better "
    "than a character-by-character guess, answer NO_KANA — a wrong reading is worse "
    "than none, and GUESS answers carry no source on Wikidata precisely because the "
    "article does not back them.\n"
    "Rules: give the reading of the SHRINE NAME itself, not a 通称 (common name), "
    "not a 旧称 (former name), and not the reading of the place it stands in. Drop "
    "interpuncts and spaces. A KATAKANA answer is recorded and NOT written to "
    "Wikidata — P1814 wants modern hiragana, and a katakana reading is the "
    "signature of the ancient-reading error a separate cleanup is undoing.\n"
    "When ANSWER is filled this file is done. -->"
)



# Items ブルーノ・プラス REPURPOSED — Emma's standing rule (queue.md A5) is
# "document, don't touch; no contact until we understand the editor". They reach
# this queue legitimately: each is a shrine with a jawiki sitelink and no P1814,
# because the repurposing stripped what was there. Writing a reading to one would
# be editing the husk and would look like a response to that editor.
# Source: docs/bruno_plus_analysis_2026-07.md §3.2 and its damage table.
REPURPOSED = {
    "Q123044569",   # was Kamo Shrine (Odawara) -> repurposed into 大美和神社
    "Q134886554",   # was Chikadono Shrine (Saitama) -> repurposed into 近殿神社
    "Q134736575",   # 見光寺
    "Q140476265",   # created then blanked; junk husk
}


# ---------------------------------------------------------------------------
# Items that are NOT shrines but reach the target set anyway.
#
# MEASURED 2026-08-05, and the finding inverts the original suspicion: our P31
# filter is NOT leaky. Every one of these items genuinely carries
# `P31 = Q845945` on Wikidata, asserted alongside its real class — Q7137401
# 水谷川忠起 is `P31 = Q5` (human) AND `P31 = Q845945`. The defect is upstream
# data, so no tightening of the shrine query can exclude them; the only handle
# is the OTHER class the item carries.
#
# A survey of the whole target set found 135 distinct co-classes and 2,684
# (item, class) pairs. The overwhelming majority are legitimate shrine subtypes
# (Shikinaisha 442, Kokuhei-sha 440, Hachiman shrine 170, …). The exclusions
# below are the tail where the item is definitionally not a nameable shrine, so
# a P1814 shrine-reading attaches to the wrong kind of thing entirely.
#
# DELIBERATELY NOT EXCLUDED — Emma's ruling in queue.md A0: "the two place-ish
# ones were answered (P1814 is not shrine-specific and the readings are plainly
# right)". So a forest (Q5367406 春日山原始林), a mountain, a sea cave, a
# building complex (Q7797685 宮中三殿) and a kofun all stay in: they are named
# places whose reading is a real fact. Only non-places are dropped.
NOT_A_SHRINE = {
    "Q5":         "human",                     # Q7137401 水谷川忠起, a Meiji 春日大社宮司
    "Q4167410":   "Wikimedia disambiguation page",  # names several shrines, not one
    "Q7725634":   "literary work",             # Q11381815 住吉大社神代記, a book
    "Q11487032":  "shikinen-sai (a festival)", # Q3698846 御柱祭
    "Q11489226":  "otaue matsuri (a festival)",  # Q11381803 住吉の御田植
    "Q11590703":  "Jinja-cho (an organization)",  # Q135250101 鹿児島県神社庁
}


def not_a_shrine_reason(classes):
    """Reason this item is not a shrine, or None. Pure — `classes` is an iterable
    of P31 QIDs. Kept separate from the query so it is testable without WDQS."""
    for qid in classes:
        if qid in NOT_A_SHRINE:
            return f"{qid} ({NOT_A_SHRINE[qid]})"
    return None


QS_OUT = os.path.join(REPO_ROOT, "modern-quickstatements", "name_in_kana.txt")
RESOLVED_LOG = os.path.join(OUT_DIR, "_resolved.log")


def already_handled():
    """QIDs already staged or already answered — do NOT queue them again.

    A work-file's absence does not mean the item still needs work: the collector
    DELETES the file once answered. And the SPARQL target set cannot tell the
    difference either, because it asks Wikidata "which shrines lack P1814" and the
    staged lines have not been delivered — the freeze holds them until 2026-08-10.
    So the naive "skip if the file exists" rule re-queues everything already done.

    Caught 2026-08-04: a rebuild recreated 12 work-files for the first hand-done
    batch. Answering them would have written a second, identical P1814 line for
    each. The local staging is the only record of what has been done, so it is
    what gets consulted.
    """
    done = set()
    if os.path.exists(QS_OUT):
        for line in open(QS_OUT, encoding="utf-8"):
            m = re.match(r"^(Q\d+)\|", line)
            if m:
                done.add(m.group(1))
    if os.path.exists(RESOLVED_LOG):
        for line in open(RESOLVED_LOG, encoding="utf-8"):
            if line.startswith("Q"):
                done.add(line.split("\t")[0].strip())
    return done


def _utf8():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def sparql(query):
    for attempt in range(4):
        time.sleep(0.5)
        try:
            r = requests.post(SPARQL, data={"query": query, "format": "json"},
                              headers=HDR, timeout=180)
            if r.status_code == 429:
                raise SystemExit("429 from WDQS — bailing (CLAUDE.md 429 policy).")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [WDQS retry {attempt + 1}] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("WDQS failed")


def targets():
    """[(qid, ja_label, en_label, ja_title)] — shrines with a jawiki article, no P1814.

    Items co-classed as a non-shrine (see NOT_A_SHRINE) are dropped here and
    reported, not silently: they are a Wikidata data defect we route around, and
    a silent drop would look like the query simply missing them.
    """
    out, dropped = [], []
    for b in sparql(TARGET_QUERY):
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        classes = [u.rsplit("/", 1)[-1]
                   for u in b.get("classes", {}).get("value", "").split(",") if u]
        reason = not_a_shrine_reason(classes)
        if reason:
            dropped.append((qid, b.get("ja", {}).get("value", ""), reason))
            continue
        art = b["art"]["value"]
        title = urllib.parse.unquote(art.rsplit("/", 1)[-1]).replace("_", " ")
        out.append((qid, b.get("ja", {}).get("value", ""),
                    b.get("en", {}).get("value", ""), title))
    if dropped:
        print(f"  excluded {len(dropped)} non-shrine item(s) co-classed as such:")
        for qid, ja, reason in sorted(dropped):
            print(f"    {qid:<12} {ja:<20} {reason}")
    out.sort(key=lambda r: int(r[0][1:]))
    return out


def engishiki_cleanup_qids():
    """QIDs the kana-qualifier cleanup also touches. Reported, and held ONLY
    under --hold-engishiki.

    RESOLVED 2026-08-03 (Emma: "probably gating the writer per item?"). The
    collision this guarded against cannot occur, verified in the cleanup's own
    code rather than assumed:

      * generate_kana_qualifier_add.py guards BOTH its branches with
        `is_katakana(...)` and skips anything else, so a modern hiragana
        top-level P1814 can never be seeded into a カミノヤシロ qualifier.
      * generate_kana_qualifier_remove.py emits VALUE-MATCHED removals
        (`-Q135070210|P1814|"アスキ-"`), so it deletes that katakana string, not
        "the item's P1814". A hiragana value is not a target.
      * this builder's own target query requires NOT EXISTS P1814, so an item is
        queued only once it has no top-level reading at all — which for an
        Engishiki item means the cleanup's removal has already landed, and that
        removal is itself held until every ojp-hani name on the item carries its
        qualifier.

    The three together ARE the per-item gate: the two pipelines write disjoint
    values and neither can consume the other's. So the set is no longer withheld
    wholesale — that would have left 601 shrines permanently without a modern
    reading, which is the gap A0 exists to close.

    The cleanup (generate_kana_qualifier_add.py / _remove.py) works on items
    carrying an ojp-hani P1448 official name: it moves the ancient katakana
    reading onto that name as a カミノヤシロ qualifier and strips the top-level
    P1814. Both it and this builder write top-level P1814 on the same items, so
    the two must not run against the same subset unordered — Emma's instruction is
    explicitly to get her eyes on the ordering before the Engishiki subset runs.

    Derived by SPARQL, not by scraping the cleanup script: that script picks its
    targets with a query and holds no QID literals, so a source scrape would have
    matched only incidental constants (Q195793, Q845945) and excluded the wrong
    items while looking like it worked.
    """
    rows = sparql('SELECT DISTINCT ?item WHERE { ?item wdt:P31 wd:Q845945 ; '
                  'p:P1448/ps:P1448 ?nm . FILTER(LANG(?nm)="ojp-hani") }')
    return {b["item"]["value"].rsplit("/", 1)[-1] for b in rows}


def leads(titles):
    """{title -> plain-text lead} via the extracts API, BATCH titles per call."""
    out = {}
    for i in range(0, len(titles), BATCH):
        chunk = titles[i:i + BATCH]
        params = {"action": "query", "format": "json", "prop": "extracts",
                  "exintro": 1, "explaintext": 1, "redirects": 1,
                  "titles": "|".join(chunk), "formatversion": 2}
        time.sleep(THROTTLE)
        try:
            r = requests.get(JA_API, params=params,
                             headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", [])
        except Exception as e:
            print(f"  [jawiki batch {i // BATCH} failed] {e}", flush=True)
            continue
        # `redirects` rewrites titles, so map back through the normalisation the
        # API reports rather than assuming the response order matches the request.
        for p in pages:
            if "extract" in p and p.get("title"):
                out[p["title"]] = p["extract"]
        print(f"  leads {min(i + BATCH, len(titles))}/{len(titles)}", flush=True)
    return out


_KANA = re.compile(r"[ぁ-ゖァ-ヺー]")
_GLOSS = re.compile(r"[（(]([^）)]*)[）)]")


def lead_subject(lead):
    """The name the lead is actually ABOUT.

    Japanese leads open `NAME（よみ）は、…`, so the subject is the text before the
    READING parenthetical — which is not always the first parenthetical.

    `舊府神社` is led as `舊府（旧府）神社（ふるふじんじゃ）は、…`: the first paren is a
    kanji gloss sitting INSIDE the name, and stopping at it yields `舊府`, which then
    looks like a mismatch against `舊府神社`. That was a false positive on the first
    live tranche, and a warning that cries wolf is worse than no warning.

    So: drop parentheticals whose content carries no kana — those are spelling glosses,
    not readings — then stop at the first one that remains.
    """
    head = (lead or "").strip().split("\n", 1)[0]
    head = _GLOSS.sub(lambda m: "" if not _KANA.search(m.group(1)) else m.group(0), head)
    for stop in ("（", "("):
        if stop in head:
            return head.split(stop, 1)[0].strip()
    if "は" in head:
        return head.split("は", 1)[0].strip()
    return head.strip()


# 旧字体 → 新字体, restricted to forms that actually turn up in shrine and place names.
# This is a comparison aid only: it is never written anywhere, and the item's own label is
# left exactly as it is. Deliberately not a general Unicode table — a broad mapping would
# start collapsing characters that distinguish real shrines from each other.
KYUJITAI = {
    "縣": "県", "國": "国", "榮": "栄", "舊": "旧", "齋": "斎", "藝": "芸",
    "澤": "沢", "濱": "浜", "邊": "辺", "邉": "辺", "會": "会", "學": "学",
    "廣": "広", "圓": "円", "惠": "恵", "德": "徳", "樂": "楽", "豐": "豊",
    "眞": "真", "淺": "浅", "賣": "売", "巖": "巌", "鐵": "鉄", "靈": "霊",
    "觀": "観", "應": "応", "醫": "医", "亞": "亜", "壽": "寿", "驛": "駅",
    "齒": "歯", "龍": "竜", "萬": "万", "淵": "渕", "槇": "槙", "禪": "禅",
}


def shinjitai(text):
    """Fold 旧字体 to 新字体 so two spellings of one name compare equal."""
    return "".join(KYUJITAI.get(ch, ch) for ch in text)


def subject_mismatch(ja, lead):
    """The lead is about a DIFFERENT name from the item's — the dangerous case.

    Found 2026-08-24 across three items in one tranche. The article is titled and led
    as a bare 氷川神社 while the item is 千住氷川神社 or 南沢氷川神社; worse, Q11556511
    洲崎濱宮神明神社's lead is about 海山道神社 entirely.

    It matters more than a missing reading. The lead states one cleanly, in the usual
    parenthetical, so an answer taken from it looks well-sourced — and the collector
    then attaches S143/S4656, asserting that the Japanese Wikipedia article backs a
    reading of a name the article never mentions. A wrong unsourced reading is
    recoverable; a wrong SOURCED one is what "visibility is worse than data loss" is
    about.

    Two things are NOT mismatches, and a first cut got both wrong:

    * **Variant kanji.** 利雁神社 is led as 利鴈神社 and 尾崎神社 as 尾﨑神社 — the same
      shrine, one character written differently. Same length, one character apart.
    * **A lead whose subject is longer prose containing the name**, e.g.
      本項目で扱う滋賀県高島市の熊野神社. The item's name is in there.

    And one thing IS a mismatch that plain containment misses: the lead's subject being
    a strict *substring* of the item's name. That is exactly 千住氷川神社 led as a bare
    氷川神社 — the article covers the generic name and the item is a specific shrine, so
    its reading is not the one stated.

    A third non-mismatch, found 2026-08-24 on the eleventh tranche: **旧字体 vs 新字体**.
    The item is 香川縣護國神社 and the lead opens 香川県護国神社 — two characters apart, so
    the one-character variant-kanji tolerance above does not catch it, and widening that
    tolerance to two would start passing genuinely different names. Old and new character
    forms are normalised instead, which is exact rather than approximate.
    """
    subject = lead_subject(lead)
    if not subject or not ja:
        return None
    bare = ja.split("(", 1)[0].split("（", 1)[0].strip()
    bare, subject_cmp = shinjitai(bare), shinjitai(subject)
    if bare == subject_cmp or bare in subject_cmp:
        return None
    if len(bare) == len(subject_cmp) and sum(
            a != b for a, b in zip(bare, subject_cmp)) <= 1:
        return None                      # variant kanji
    return subject


MISMATCH = (
    "<!-- ⚠ THE LEAD IS ABOUT A DIFFERENT NAME: this item is {ja!r} but the lead below "
    "opens on {subject!r}. Do NOT copy the lead's reading as KANA — it would be sourced "
    "to an article that does not name this shrine. Either derive this item's own reading "
    "and answer GUESS, or answer NO_KANA. -->"
)


def write_work_file(qid, ja, en, title, lead):
    bucket = "a" if en else "b"
    path = os.path.join(OUT_DIR, f"{qid}.wiki")
    art = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    subject = subject_mismatch(ja, lead)
    warn = (MISMATCH.format(ja=ja, subject=subject) + "\n") if subject else ""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<!-- ITEM: https://www.wikidata.org/wiki/{qid} -->\n"
                f"<!-- JA: {ja} | EN_LABEL: {en or '(none)'} | BUCKET: {bucket} -->\n"
                f"<!-- ARTICLE: {art} -->\n"
                f"{warn}"
                f"<!-- ANSWER: -->\n"
                f"{TASK}\n\n== LEAD ==\n{lead.strip()}\n")


def main():
    _utf8()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=200,
                    help="max work-files to write this run (default 200)")
    ap.add_argument("--bucket", choices=["a", "b"],
                    help="a = has an en label (priority); b = no en label")
    ap.add_argument("--stats", action="store_true", help="count only, write nothing")
    ap.add_argument("--hold-engishiki", action="store_true",
                    help="withhold the ojp-hani P1448 items (see engishiki_cleanup_qids; "
                         "not needed — the two pipelines write disjoint values)")
    args = ap.parse_args()

    print("querying Wikidata for shrines with a jawiki article and no P1814...",
          flush=True)
    rows = targets()
    engishiki = engishiki_cleanup_qids()
    repurposed = [r for r in rows if r[0] in REPURPOSED]
    rows = [r for r in rows if r[0] not in REPURPOSED]
    if repurposed:
        print(f"excluded {len(repurposed)} ブルーノ・プラス-repurposed husks "
              f"({', '.join(r[0] for r in repurposed)}) — document, don't touch")
    kept = [r for r in rows if not (args.hold_engishiki and r[0] in engishiki)]
    overlap = sum(1 for r in rows if r[0] in engishiki)
    a = [r for r in kept if r[2]]
    b = [r for r in kept if not r[2]]
    print(f"{len(rows)} targets; {overlap} also carry an ojp-hani P1448 "
          + ("(HELD by --hold-engishiki)" if args.hold_engishiki
             else "(queued — the two pipelines write disjoint values)")
          + f"; bucket a (has en label) {len(a)}, bucket b {len(b)}")

    pool = a if args.bucket == "a" else b if args.bucket == "b" else a + b
    if args.stats:
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    done = already_handled()
    todo = [r for r in pool
            if r[0] not in done
            and not os.path.exists(os.path.join(OUT_DIR, f"{r[0]}.wiki"))][:args.limit]
    if done:
        print(f"{len(done)} targets already staged or answered — not re-queued")
    if not todo:
        print("every target in this bucket already has a work-file")
        return
    print(f"downloading {len(todo)} jawiki leads...", flush=True)
    text = leads([r[3] for r in todo])

    written, noext = 0, []
    for qid, ja, en, title in todo:
        lead = text.get(title)
        if not lead:
            # NO LEAD IS NOT A REASON TO SKIP — it is the GUESS case.
            #
            # This used to `continue` with no file written, on the reasoning that "a
            # later run retries them". Measured 2026-08-23: it is not a retry, it is a
            # permanent loop. These items sort to the front of the target set, so every
            # tranche re-fetches and re-skips exactly the same ones — three consecutive
            # tranches named an identical four (Q11391058/59/60 八幡社, Q11396252
            # 刈田嶺神社) — and they can never acquire a lead, because the article is a
            # redirect, a disambiguation page, or empty.
            #
            # They are answerable. 刈田嶺神社 is かったみねじんじゃ, which two sibling items
            # answered from their own leads the same day. Emma's 2026-08-23 decision is
            # to guess where no kana can be found, and this is that case exactly; the
            # no-file rule was what put it out of reach.
            noext.append((qid, title))
            write_work_file(qid, ja, en, title, NO_LEAD)
            written += 1
            continue
        write_work_file(qid, ja, en, title, lead)
        written += 1
    print(f"\n{written} work-files -> {OUT_DIR}")
    if noext:
        print(f"{len(noext)} had NO lead extract (redirect / disambig / empty) — a "
              f"work-file was still written, with the lead marked unavailable, so the "
              f"GUESS path can answer them instead of them recycling every run:")
        for qid, title in noext[:8]:
            print(f"  {qid}  {title}")


if __name__ == "__main__":
    main()
