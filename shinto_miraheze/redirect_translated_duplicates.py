#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redirect_translated_duplicates.py
=================================
Redirects a Japanese-TITLED page onto its English-titled twin, for the pairs where
the English page is already a structurally parallel superset — the redirect-only
remainder of Emma's *"redirect the Japanese so qid shit is resolved"*.

This is the counterpart of ``merge_duplicate_pairs.py``. That script runs where the
Japanese-titled page holds MORE and its body has to survive; this one runs where the
English page already holds everything and only the duplicate title is left.

WHY THE PAIR LIST IS COMPUTED, NOT LISTED
-----------------------------------------
The size of this set has been mis-stated four times (44, then 23+9+12, then 33+2),
every time by reusing a figure from a devlog instead of measuring. So there is no
hardcoded list: the pairs are derived from ``orchestrators/duplicate_qids.state``
and every gate is evaluated against the LIVE page text at run time. A pair that
stopped qualifying since the last run is refused on that run.

THE TWO GATES — both must hold, and both are checked live
---------------------------------------------------------
1. **Byte ratio.** The English page must be at least ``MIN_TARGET_RATIO`` times the
   Japanese-titled one. Redirecting onto a smaller page is the mistake this gate
   exists to prevent — it is what would have happened to 健磐龍命 (19,798b onto a
   13,510b page missing its Nihon Shoki, Fudoki and Engishiki sections).

2. **Heading correspondence — NOT heading count.** Heading COUNT was the metric that
   mis-classified this set twice: it says nothing about direction, nor about which
   sections exist. Instead each heading normalises to a CONCEPT CLASS (``Base`` /
   ``Headquarters`` / ``Base of Operations`` / ``本拠`` are one class), and every
   content-bearing heading on the Japanese page must have a heading of the same
   class on the English page. Apparatus headings (notes, references, see also,
   external links) are exempt — they carry no article content.

   **An UNRECOGNISED heading fails the gate.** A heading this map cannot classify is
   an unknown, and an unknown never authorises an edit — the same rule
   ``dedupe_duplicate_qids.py`` follows. A page-specific heading such as ``The Ice
   House of Tsuge`` is not a concept class, so it is resolved in ``PAIR_HEADINGS``
   against the one pair it belongs to rather than widened into ``CLASSES``.

   **An EMPTY heading is exempt, for the same reason apparatus is.** Correspondence is
   about CONTENT, and a heading with no body under it carries none — it is a wrapper
   nesting its subsections (``== Base ==`` over ``=== Territory ===``) or a stub the
   translator left behind. Measured across the held set on 2026-08-28, this was the
   single largest cause of a false refusal: 島津国造 and 熊野国造 were held on an empty
   ``Base``, 上毛野国造 on an empty ``Genealogy``, 伊勢国造 on an empty ``墓``. Nothing
   was actually missing from any of those English pages. Emptiness is judged on the
   SOURCE for the exemption and on the TARGET for what it may vouch for, so an empty
   target heading cannot stand in for a section that was never written.

WHAT IS NOT COPIED, AND WHY (measured 2026-08-28)
-------------------------------------------------
The target page is **not** rewritten, and the source's categories are not
blanket-unioned into it — which is what ``merge_duplicate_pairs.py`` does and would
be wrong here. Across the qualifying pairs the source-only categories are almost
entirely *jawiki* category names carried in by the import (下野国, 栃木県の歴史,
古墳時代の人物) plus maintenance categories describing the SOURCE's own state
(``Need translation``, ``Pages with 500+ untranslated japanese characters``). Neither
belongs on the English article.

What IS carried over is the narrow real case: a source-only category that is
English-named and not a maintenance tag — a genuine classification the target lacks
(菟狭津彦命 carries ``Usa clan``, ``People from Buzen Province`` and three more).
Those are appended to the target; nothing on the target is ever removed.

Idempotence: a source that is already a redirect is refused, so a re-run cannot
double-apply and a re-dispatch is safe.

    python redirect_translated_duplicates.py --plan-only          # read-only, no login
    python redirect_translated_duplicates.py                      # dry-run
    python redirect_translated_duplicates.py --apply --max-edits 5 --run-tag "(run 123)"
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import collections
import io
import json
import os
import re
import subprocess
import sys
import time

if getattr(sys.stdout, "encoding", "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "orchestrators", "duplicate_qids.state")

# The English page must be at least this many times the Japanese-titled one. At 1.0
# the surviving page is simply never the smaller of the two.
MIN_TARGET_RATIO = 1.0

CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")
HEADING_RE = re.compile(r"^==+\s*(.+?)\s*==+\s*$", re.M)
REDIRECT_RE = re.compile(r"^\s*#redirect\b", re.IGNORECASE)
CATEGORY_RE = re.compile(r"\[\[\s*Category\s*:\s*([^\]|]+?)\s*(?:\|[^\]]*)?\]\]", re.IGNORECASE)

# Headings that are apparatus rather than article content. Their absence from the
# English page loses nothing, so they are exempt from the correspondence gate.
APPARATUS = {
    "notes", "note", "footnotes", "footnote", "annotations", "notelist",
    "references", "reference", "citations", "sources", "source", "bibliography",
    "cited works", "further reading", "see also", "related articles",
    "related items", "external links", "external link", "other",
    "jawiki content", "other boilerplate",
    "脚注", "注釈", "出典", "参考文献", "関連項目", "外部リンク",
}

# Concept classes. Two headings correspond when they share a class — this is what
# replaces the heading-COUNT comparison that mis-classified the set twice.
CLASSES = {
    "overview": ["overview", "description", "summary", "概要",
                 "mythical narrative", "mythological background"],
    "name": ["name", "names", "naming", "name variants", "writing", "terminology",
             "spelling variations", "表記"],
    "ancestry": ["ancestry", "ancestors", "ancestor", "origin",
                 "origins and genealogy", "祖先", "出自"],
    "clan": ["clan", "clan lineage", "氏族"],
    "base": ["base", "headquarters", "base of operations", "base territory",
             "domain", "本拠"],
    "territory": ["territory", "governed region", "jurisdiction", "governance",
                  "domain", "支配領域"],
    "shrine": ["tutelary shrine", "tutelary shrines", "tutelary deity",
               "tutelary deities", "clan shrine", "clan shrines", "clan deity",
               "clan deities", "deity", "deities worshipped", "patron deity",
               "shrine", "shrines", "local deities", "enshrining shrine",
               "shrines enshrining him", "shrines dedicated to himuro",
               "related shrine", "related shrines", "associated shrines",
               "related sites", "atsuta shrine", "worship",
               "氏神", "関連神社", "祀る神社"],
    "tomb": ["tombs", "tomb", "burial site", "historic sites", "sites of legend", "墓"],
    "people": ["people", "notable figures", "figures", "famous members", "人物"],
    "descendants": ["descendants", "descendant clans", "related clans",
                    "descendant", "子孫", "後裔氏族"],
    "genealogy": ["genealogy", "family tree", "lineage", "系図", "系譜",
                  "divine genealogy and descendant clans", "神統譜・後裔氏族"],
    "records": ["records", "record", "historical records", "biography", "deeds",
                "記録", "記述", "事跡"],
    "analysis": ["analysis", "examination", "考察"],
    "place names": ["place names", "地名"],
}
# Per-pair heading equivalences — the honest alternative to widening ``CLASSES``.
# A heading that occurs on ONE article and nowhere else is not a concept class, and
# adding it to ``CLASSES`` would overfit a general map to a single page: it would then
# silently match on pages nobody looked at. So the judgement is recorded against the
# pair it was made about, keyed by the Japanese title, and applies to BOTH of that
# pair's pages — the English twin usually carries the same section under its own
# rendering, and it has to be recognised too or it cannot vouch for anything.
#
# Every entry was made by reading the two sections and confirming they hold the same
# material (2026-08-28); the byte counts are from that reading.
PAIR_HEADINGS = {
    # himuro IS an ice house — one translation kept the loanword, the other rendered
    # it. Source 2,046b, target 4,703b, same subject.
    "闘鶏大山主": {"the ice house of tsuge": "himuro",
                "the himuro of tsuge": "himuro"},
    # The same sutra, transliterated on one page (Chishiki-kyō) and translated on the
    # other (Knowledge Sutra). Source 635b, target 645b.
    "針間鴨国造": {"kitadera chishiki-kyō": "kitadera sutra",
                 "kitadera knowledge sutra": "kitadera sutra"},
    # The succession list. The English page carries it at 19,294b under ``Genealogy``
    # against the source's 4,093b, and also names it "Lineage of ...".
    "紀伊国造": {"generations of kii no kuni no miyatsuko": "genealogy",
               "lineage of kii no kuni no miyatsuko": "genealogy"},
    # Translated verbatim on the English page, heading for heading.
    "天道根命": {"降臨と東征": "descent",
               "descent and eastern expedition": "descent",
               "国造職": "kuni no miyatsuko office",
               "the kuni no miyatsuko office": "kuni no miyatsuko office"},
    # The source's ``Base`` (276b — Akashi-gō, and the neighbours north and west) is
    # on the target under ``Territory`` (361b), saying the same thing in the same
    # order. This is NOT a general base==territory equivalence and must not become
    # one: 那須国造 carries Base (943b) and Territory (1,993b) as separate sections,
    # and merging the two classes would silently lose its Territory.
    "明石国造": {"base": "territory"},
    # One temple, named twice. The source's ``Clan Temple`` (63b) is "the clan's temple
    # is Miroku-ji"; the target's ``Associated Temple`` (173b) is the same sentence about
    # the same ja target (弥勒寺跡 (関市)), carrying a QID the source lacks. Read
    # 2026-08-30. This does NOT go in ``CLASSES``: "clan temple" and "associated temple"
    # are how these two pages happen to render one heading, not a concept class the map
    # should start matching on pages nobody has looked at.
    "牟義都国造": {"clan temple": "clan temple",
                "associated temple": "clan temple"},
    # The only pair that is two genuinely DIFFERENT articles rather than two translations
    # of one, so these two headings have no counterpart to be equivalent TO — they are
    # sections that exist on one page and, after the carry, on the other. Each is keyed to
    # itself so the gate can recognise it on both pages rather than refusing it as an
    # unknown. Read 2026-08-30: the Kinai-regime section (2,416b) is the Nihon Shoki
    # descent and the imperial consort line (Yosotahonomihime → Emperor Kōan, Owari
    # Ōamihime → Sujin); the Inaba section (982b) is a separate Owari family in Inaba
    # Province, with its own infobox, the Saji and Hikita branches, and Saji Shigesada's
    # Kamakura appointment. Neither belongs in ``CLASSES``.
    "尾張氏": {"the owari clan from the perspective of the kinai regime": "kinai regime view",
             "owari clan (inaba province)": "inaba branch"},
}

CLASS_OF = collections.defaultdict(set)
for _cls, _names in CLASSES.items():
    for _n in _names:
        CLASS_OF[_n].add(_cls)

# Categories that describe the SOURCE page's own state. Carrying one onto the target
# would assert something false about the target.
MAINTENANCE_CATEGORIES = {"need translation", "translated but not moved"}
MAINTENANCE_CATEGORY_RE = re.compile(
    r"^pages with \d+\+ untranslated japanese characters$", re.IGNORECASE)


def normalize_heading(h):
    h = re.sub(r"''+", "", h).strip().lower()
    h = re.sub(r"\s+", " ", h)
    for _ in range(3):                      # "Tutelary Shrine, etc." -> "tutelary shrine"
        h = re.sub(r"\s*\betc\b\.?$", "", h).strip()
        h = re.sub(r"[,.;:]+$", "", h).strip()
    return h


def heading_classes(h, pair=None):
    """None = apparatus (exempt). Empty set = unrecognised. Otherwise its classes.

    ``pair`` is this pair's ``PAIR_HEADINGS`` entry, consulted before the general map
    so a page-specific heading resolves without ``CLASSES`` growing a page-specific
    entry.
    """
    n = normalize_heading(h)
    if n in APPARATUS:
        return None
    if pair and n in pair:
        return {pair[n]}
    return set(CLASS_OF.get(n, ()))


def sections(text):
    """[(heading, body)] — each heading with the text under it, up to the next one.

    The body is what a heading actually contributes; ``check_pair`` needs it because a
    heading with an empty body contributes nothing at all.
    """
    out, name, start = [], None, 0
    for m in HEADING_RE.finditer(text):
        if name is not None:
            out.append((name, text[start:m.start()]))
        name, start = m.group(1), m.end()
    if name is not None:
        out.append((name, text[start:]))
    return out


def is_maintenance_category(name):
    name = name.strip()
    return name.lower() in MAINTENANCE_CATEGORIES or bool(MAINTENANCE_CATEGORY_RE.match(name))


def carried_categories(source, target):
    """Source-only categories worth carrying over: English-named, non-maintenance."""
    on_target = set(c.strip() for c in CATEGORY_RE.findall(target))
    out = []
    for c in CATEGORY_RE.findall(source):
        c = c.strip()
        if c in on_target or c in out:
            continue
        if CJK_RE.search(c):                # a jawiki category, not the target's
            continue
        if is_maintenance_category(c):      # describes the source, not the target
            continue
        out.append(c)
    return out


def check_pair(source, target, source_title=None):
    """Return (ok, reason, detail). ``ok`` False means refuse — never guess.

    ``source_title`` selects this pair's ``PAIR_HEADINGS`` entry, if it has one.
    """
    if REDIRECT_RE.match(source):
        return False, "source is already a redirect", {}
    if REDIRECT_RE.match(target):
        return False, "target is a redirect, not an article", {}

    s_bytes = len(source.encode("utf-8"))
    t_bytes = len(target.encode("utf-8"))
    if s_bytes and t_bytes < s_bytes * MIN_TARGET_RATIO:
        return False, ("target is %db against source %db — below the %sx gate, so the "
                       "English page is not the superset this redirect assumes"
                       % (t_bytes, s_bytes, MIN_TARGET_RATIO)), {}

    pair = PAIR_HEADINGS.get(source_title or "")

    # Only a target section that HAS a body may vouch for a source section. An empty
    # target heading is a wrapper or a stub, and neither is the content being sought.
    target_classes = set()
    for h, body in sections(target):
        if not body.strip():
            continue
        cls = heading_classes(h, pair)
        if cls:
            target_classes |= cls

    missing, unrecognised = [], []
    for h, body in sections(source):
        cls = heading_classes(h, pair)
        if cls is None:
            continue
        if not body.strip():
            continue                    # carries no content, so its absence loses none
        if not cls:
            unrecognised.append(normalize_heading(h))
        elif not (cls & target_classes):
            missing.append(normalize_heading(h))
    if unrecognised:
        return False, ("unrecognised heading on the source: "
                       + ", ".join(repr(h) for h in unrecognised)), {}
    if missing:
        return False, ("the English page has no counterpart for: "
                       + ", ".join(repr(h) for h in missing)), {}

    ratio = (float(t_bytes) / s_bytes) if s_bytes else 0.0
    return True, "%.2fx, every content heading has a counterpart" % ratio, {
        "ratio": ratio, "source_bytes": s_bytes, "target_bytes": t_bytes,
        "carry": carried_categories(source, target),
    }


def append_categories(target, cats):
    if not cats:
        return target
    return target.rstrip("\n") + "\n" + "\n".join("[[Category:%s]]" % c for c in cats) + "\n"


def load_pairs(state_path=STATE_PATH):
    """(qid, japanese_title, english_title) for every 2-title mainspace group."""
    with io.open(state_path, encoding="utf-8") as fh:
        state = json.load(fh)
    groups = collections.defaultdict(list)
    for title, qid in state.items():
        groups[qid].append(title)
    pairs = []
    for qid, titles in groups.items():
        if len(titles) != 2:
            continue
        jp = [t for t in titles if CJK_RE.search(t)]
        en = [t for t in titles if not CJK_RE.search(t)]
        if len(jp) != 1 or len(en) != 1:
            continue
        # Templates are excluded: a template's content is MARKUP, and redirecting one
        # hands the English markup to every page that asked for the Japanese template.
        # Emma's ruling 2026-08-28 was to drop the duplicate QID from those instead.
        if any(":" in t for t in titles):
            continue
        pairs.append((qid, jp[0], en[0]))
    pairs.sort(key=lambda p: p[1])
    return pairs


def lockout_blocks_us():
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_edit_allowed.py")
    if not os.path.isfile(checker):
        return False
    return subprocess.call([sys.executable, checker]) != 0


def main():
    parser = argparse.ArgumentParser(
        description="Redirect already-translated Japanese-titled duplicates.")
    parser.add_argument("--plan-only", action="store_true",
                        help="Measure against the live wiki and print the plan; no login, no edits.")
    parser.add_argument("--apply", action="store_true", help="Actually save (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=50, help="Cap per run (default 50).")
    parser.add_argument("--run-tag", default="", help="Edit-summary suffix linking back to the run.")
    args = parser.parse_args()

    if args.apply and not args.plan_only and lockout_blocks_us():
        print("SKIPPED: miraheze editing is locked. Nothing attempted.")
        return 0

    import mwclient
    from shinto_miraheze.user_agent import USER_AGENT

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120

    pairs = load_pairs()
    print("%d Japanese/English mainspace duplicate pairs in the live state file" % len(pairs))

    plan, held = [], []
    for qid, src_title, dst_title in pairs:
        try:
            src, dst = site.pages[src_title], site.pages[dst_title]
            if not src.exists:
                held.append((qid, src_title, dst_title, "source does not exist"))
                continue
            if not dst.exists:
                held.append((qid, src_title, dst_title, "target does not exist"))
                continue
            src_text, dst_text = src.text(), dst.text()
        except Exception as e:
            # A read failure must not shrink the plan into looking complete.
            print("ABORT: could not read %r/%r: %s" % (src_title, dst_title, e))
            return 2

        ok, reason, detail = check_pair(src_text, dst_text, src_title)
        if ok:
            plan.append((qid, src_title, dst_title, reason, detail))
        else:
            held.append((qid, src_title, dst_title, reason))

    print("\nQUALIFYING (%d):" % len(plan))
    for qid, s, d, reason, detail in plan:
        carry = detail.get("carry") or []
        extra = ("  +carry %s" % carry) if carry else ""
        print("  %-12s %s -> %s   (%s)%s" % (qid, s, d, reason, extra))
    print("\nHELD (%d) — refused rather than guessed at:" % len(held))
    for qid, s, d, reason in held:
        print("  %-12s %s -> %s\n      %s" % (qid, s, d, reason))

    if args.plan_only:
        return 0

    if not args.apply:
        print("\n[DRY] would redirect %d page(s). Re-run with --apply to save."
              % min(len(plan), args.max_edits))
        return 0

    from wiki_login import login_with_retry
    login_with_retry(site, USERNAME, PASSWORD)
    print("\nLogged in as %s" % USERNAME)

    done = errors = 0
    for qid, src_title, dst_title, reason, detail in plan:
        if done >= args.max_edits:
            print("Cap of %d reached, stopping. The rest run next tick." % args.max_edits)
            break
        try:
            carry = detail.get("carry") or []
            if carry:
                dst = site.pages[dst_title]
                dst.save(append_categories(dst.text(), carry),
                         summary=("Carry %d categor%s from [[%s]] before redirecting it %s"
                                  % (len(carry), "y" if len(carry) == 1 else "ies",
                                     src_title, args.run_tag)).strip())
                time.sleep(THROTTLE)
            site.pages[src_title].save(
                "#REDIRECT [[%s]]\n" % dst_title,
                summary=("Already translated at [[%s]]; redirecting so %s resolves to one page %s"
                         % (dst_title, qid, args.run_tag)).strip())
            time.sleep(THROTTLE)
            print("  redirected %s -> %s" % (src_title, dst_title))
            done += 1
        except Exception as e:
            print("  ERROR saving %r: %s" % (src_title, e))
            errors += 1

    print("\nRedirected: %d   Held: %d   Errors: %d" % (done, len(held), errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
