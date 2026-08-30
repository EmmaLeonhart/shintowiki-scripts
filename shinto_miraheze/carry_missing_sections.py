#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
carry_missing_sections.py
=========================
Carries the content-bearing sections that ONLY the Japanese-titled page has onto
its English-titled twin, so the pair stops being a content decision and becomes an
ordinary redirect job for ``redirect_translated_duplicates.py``.

This is the third operation the duplicate-pair workstream needed and did not have.
The other two are both all-or-nothing about the body:

* ``merge_duplicate_pairs.py`` REPLACES the target's body, and refuses below a 2.0x
  source ratio — correct where the source is the fuller page, destructive anywhere
  else.
* ``redirect_translated_duplicates.py`` keeps the target untouched and redirects the
  source, and refuses when a content-bearing source heading has no counterpart —
  correct where the English page is already the superset.

Seven pairs are neither. Their sections are **complementary, not superset/subset**:
each page holds something the other does not, so replacing either body destroys the
half only that page had. What they need is a section-wise union — take the sections
that exist on one side only, put them on the target, change nothing that is already
there — and then let the redirect script's own gates decide the redirect on live text.

THE JUDGEMENT IS PER PAIR, NOT A GENERAL RULE
---------------------------------------------
``CARRIES`` names, for one pair, the exact source headings to carry and the exact
target heading each is inserted before. Nothing is inferred. This follows the same
reasoning as ``PAIR_HEADINGS`` in the redirect script: a decision made by reading two
particular articles is recorded against those two articles, so it cannot later match
silently on a page nobody looked at.

WHAT IS NEVER DONE HERE
-----------------------
* **Nothing on the target is removed or rewritten.** The edit is an insertion, and
  ``carry_sections`` asserts the old text's headings all survive and the page grew.
* **The source is not touched at all** — not blanked, not redirected. Redirecting is
  ``redirect_translated_duplicates.py``'s job, and leaving it there means the redirect
  is still gated on the correspondence check measured against the live pages, rather
  than authorised by this script having run.
* **Categories are not carried.** The redirect script already carries the narrow real
  case (English-named, non-maintenance, source-only) at redirect time.

THE GATE NEVER LOOKS AT A LEAD
-----------------------------
``redirect_translated_duplicates.py`` compares HEADINGS. A source lead that outweighs
the target's is invisible to it, and it will pass the pair regardless — 尾張氏's lead was
2,125b against 1,246b and held the clan's progenitor and its descendant houses. So an
entry may carry ``lead``: ``{"heading", "anchor", "append"?}``, which brings the lead
across under a heading of its own. Leading ``{{…}}`` blocks are dropped, because an
infobox is structured data about the source page's rendering rather than prose; anything
worth keeping from one goes in ``append``, written out and reviewable in the diff rather
than generated at run time.

Idempotence: a section whose heading is already on the target is refused, so a
re-run after a successful carry refuses the pair and a re-dispatch is safe.

    python carry_missing_sections.py                 # dry-run, prints the plan
    python carry_missing_sections.py --apply --run-tag "(run 123)"
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import argparse
import io
import os
import re
import subprocess
import sys
import time

if getattr(sys.stdout, "encoding", "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from shinto_miraheze.redirect_translated_duplicates import (
    heading_classes, normalize_heading,
)

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

# One entry per pair, each written after reading both live articles. ``sections`` is
# (heading on the source, heading on the target to insert it immediately before).
CARRIES = [
    {
        # 建稲種命 6,913b / Takeinadane 7,204b, read 2026-08-30. The English page has
        # a real lead but no Overview: it covers Atsuta, Miyazu-hime, Tagata Shrine
        # and "two sons and four daughters" and stops there. The source's Overview
        # (2,309b measured here, not the 1,923b the queue carried) is the parentage,
        # the six children and who they married into the imperial line, the service
        # under Keiko and Seimu, the eastern expedition with Yamato Takeru, and the
        # eight shrines that enshrine him — none of it on the target.
        #
        # ``See also`` is carried too, and it is NOT apparatus here despite the name:
        # its three bullets are annotated narrative — the Utsutsu Shrine drowning
        # legend and Yamato Takeru's "utsutsu kana", the Hazu Shrine burial on
        # Miyazaki Beach, and the Machiai-no-Ura naming. The redirect script exempts
        # ``see also`` as apparatus, so if it were left behind the redirect would pass
        # its gates and take 2,274b of real content with it silently. Carrying it is
        # what makes that exemption safe on this pair.
        "source": "建稲種命",
        "target": "Takeinadane",
        "sections": [("Overview", "Genealogy"), ("See also", "Notelist")],
    },
    {
        # 那須国造 12,838b / Nasu no Kuni no Miyatsuko 16,375b, both read 2026-08-30.
        # The target is the fuller page section for section — Overview 5,475b against
        # 2,517b, Ancestry 2,305b against 523b, Clan 3,138b against 1,962b — and its
        # Headquarters (962b) covers the source's Base prose (~1,033b, once the Territory
        # subsection nested under it is subtracted). The ONE gap is Territory, which is
        # what the redirect script's plan already said in as many words: "the English page
        # has no counterpart for: 'territory'".
        #
        # Territory is a ``===`` subsection of ``== Base ==`` on the source, so the anchor
        # is the target's ``== Shrine ==``: inserting before it lands Territory at the tail
        # of Headquarters, nested under it, which is the structure it already has.
        #
        # ``See also`` is NOT carried here, and the difference from 建稲種命 is the point.
        # There it was annotated narrative hiding under an apparatus name. Here the source's
        # two bullets — the kuni-no-miyatsuko list, the Nasu-clan descent theory — are the
        # same two the target already carries under ``See Also``, better templated. Checked
        # rather than assumed; the exemption is only safe when someone reads the section.
        "source": "那須国造",
        "target": "Nasu no Kuni no Miyatsuko",
        "sections": [("Territory", "Shrine")],
    },
    {
        # 牟義都国造 6,190b / Mukizu no Kuni no Miyatsuko 6,427b, both read 2026-08-30 —
        # the closest-matched pair in the set, 1.04x before the carry. Every source
        # section has its counterpart (Writing/Terminology, Base/Headquarters,
        # Tutelary Shrine/Shrine, People/Notable Figures, and Clan Temple/Associated
        # Temple via this pair's new ``PAIR_HEADINGS`` entry) except one.
        #
        # ``Descendants`` (374b — Mugetsu Hiro, an Asuka-period gōzoku, possibly a toneri
        # of Prince Ōama, active in the Jinshin War) has nothing on the target, which
        # stops at ``Notable Figures``. It anchors before ``See Also``, putting it where
        # the source has it: straight after the people section.
        #
        # Two things checked rather than assumed, both of which could have gone the other
        # way. The source's ``Tombs`` is an EMPTY wrapper (0b) under Tutelary Shrine, so
        # it carries nothing and its absence loses nothing. And ``See also`` really is
        # apparatus here — one link to the kuni-no-miyatsuko list, which the target
        # already has under ``See Also`` with a QID. Compare 建稲種命, where the same
        # heading held 2,274b of narrative.
        "source": "牟義都国造",
        "target": "Mukizu no Kuni no Miyatsuko",
        "sections": [("Descendants", "See Also")],
    },
    {
        # 尾張氏 6,347b / Owari clan 11,735b, both read 2026-08-30. The only pair that is
        # two genuinely different articles rather than two translations of one, so nothing
        # here is a translation gap — these are sections the English article simply does
        # not have.
        #
        # Both anchor before ``Genealogy``, which puts them after ``Cultural influence``
        # and is the first time two sections share an anchor. That is what surfaced the
        # insertion-order defect fixed above: one-at-a-time insertion at a single offset
        # reverses them.
        #
        # ``Related items`` (243b, a jawiki link list of Japanese-titled pages plus a stub
        # template) and ``Sources`` (443b, `{{Reflist}}`, the wikidata link and the
        # categories) are apparatus in fact as well as in name, read and not carried.
        #
        # THE LEAD IS CARRIED, and this pair is why the capability exists. The source's
        # lead is 2,125b against the target's 1,246b, and the correspondence gate compares
        # HEADINGS — it never looks at a lead, so it would have passed this pair while the
        # English page still lacked 天忍人命 / Ame no Oshihito (the progenitor), the Mino
        # and Hida residence before the clan became Owari-no-kuni-no-miyatsuko, and the
        # Sukune descendant houses (Moriobe of Atsuta's Dainai family, the Baba
        # chief-inspector family, the Tajima high-priest family, the Hakkenjingū priests).
        # Emma's call, 2026-08-30, asked with those facts named: carry it as a section,
        # then redirect.
        #
        # 世襲足媛 is NOT in that list although a kanji search says it is missing — she is
        # on the target as Yosotahonomihime, in the Kinai-regime section carried above.
        # Searching for the kanji of a person the English page names in rōmaji reports a
        # loss that is not there.
        #
        # ``append`` is the infobox reduced to prose. The jawiki infobox itself is not
        # carried — it is structured data about the source page's rendering, and a second
        # clan infobox mid-article is not what it means. Its remaining names are given as
        # plain kanji rather than links because NONE of 天忍人命, 尾張大隅, 尾張草香,
        # 尾張馬身, 尾張兼時, 尾張浜主, 村国氏 or 熱田神宮家 has a page on this wiki
        # (checked 2026-08-30), so linking them would manufacture eight red links.
        "source": "尾張氏",
        "target": "Owari clan",
        "sections": [
            ("The Owari clan from the perspective of the Kinai regime", "Genealogy"),
            ("Owari clan (Inaba Province)", "Genealogy"),
        ],
        "lead": {
            "heading": "Lineage and descendant houses",
            "anchor": "Cultural influence",
            "append": (
                "Also recorded in the clan infobox of the Japanese article merged here: "
                "the clan titles 尾張連 and later 尾張宿禰; the classification 神別 (天孫); "
                "a base in Aichi District, Owari Province (尾張国愛知郡); the progenitor "
                "天忍人命; the members 尾張大隅, 尾張草香, 尾張馬身, 尾張兼時 and 尾張浜主; "
                "and the descendant houses 熱田神宮家, 海部氏, 津守氏 and 村国氏."
            ),
        },
    },
    {
        # 健磐龍命 19,798b / Takeiwatatsu-no-Mikoto 13,510b, both read in full 2026-08-30.
        # The first pair where the SOURCE is the fuller page, and the one the queue named
        # as the clear case against lowering merge_duplicate_pairs.py's 2.0x gate: the
        # source holds Nihon Shoki, Fudoki, Engishiki and Kokuzo Hongi, the target holds
        # the Kihachi legend and the U-no-matsuri festival, and a body-replacing merge at
        # 1.47x would have destroyed the second set.
        #
        # Three content sections have no counterpart at all — Genealogy (4,044b),
        # Historical records (9,471b, with its Nihon Shoki / Fudoki of Higo Province /
        # Engishiki / Kokuzo Hongi / Traditions of Aso subsections) and Sites of legend
        # (501b). The target's Mythological background (overview) and Worship (shrine)
        # have no counterpart on the source, which is why this is a union and not a merge
        # in either direction.
        #
        # THE CITATIONS ARE WHY THIS PAIR IS DIFFERENT. A full audit of the source
        # (2026-08-30) found named refs defined in four different places:
        #   lead                  jingu, ruien, saijin, shiki, syoki
        #   Genealogy             ricchi, seishi1, sosyo
        #   Historical records    kokuzou, yoshimi, kako, karudera
        #   Sites of legend       ashi
        #   == Notes == / Sources gunshi, keizu, mura, ihon   ← APPARATUS
        # Carrying only the content sections would leave gunshi/keizu/mura/ihon behind and
        # break every citation using them. The lead is carried (it is 2,621b against the
        # target's 1,567b, so Emma's rule applies anyway) and brings its five; the four in
        # the apparatus are reproduced verbatim in ``lead.append`` inside the same
        # ``{{Reflist|refs=}}`` wrapper the source uses, which defines without rendering
        # markers mid-paragraph.
        #
        # ``kou`` is used twice in Genealogy and DEFINED NOWHERE on the source — a
        # pre-existing broken citation on 健磐龍命, confirmed by auditing every ref on the
        # page, not inferred. Its work is in the bibliography as
        # ``{{Cite book|author=Kurita Hiroshi|title=Kokuzo Hongi Kō|…|ref=kou}}``, so the
        # definition below transcribes that entry in the same house style as the other
        # four. That fixes a real break rather than carrying it onto a live page; it
        # invents no source.
        #
        # ``References`` is RENAMED to ``Bibliography`` as it lands. Both pages have a
        # ``References`` heading and they are different lists — the source's is eight
        # {{Cite book}} works with NDL links, and the carried refs' ``[[#gunshi|…]]``
        # anchors point into it, so it has to come across and cannot collide.
        "source": "健磐龍命",
        "target": "Takeiwatatsu-no-Mikoto",
        "sections": [
            ("Genealogy", "See also"),
            ("Historical records", "See also"),
            ("Sites of legend", "See also"),
            ("References", "See also", "Bibliography"),
        ],
        "lead": {
            "heading": "Overview",
            "anchor": "Mythological background",
        },
        # Definitions for the named refs the carried content uses but does not bring.
        # Four (gunshi, keizu, mura, ihon) were in the source's apparatus ``=== Sources
        # ===``; three (ruien, shiki, jingu) were inside its ``{{Infobox person}}``, which
        # the lead carry strips — found only because the citation check looks at the
        # assembled page. ``kou`` was defined NOWHERE on the source, a pre-existing break
        # confirmed by auditing every ref on the page; its work is in the bibliography as
        # ``{{Cite book|author=Kurita Hiroshi|title=Kokuzo Hongi Kō|…|ref=kou}}``, so this
        # transcribes that entry in the same house style as the other four rather than
        # carrying a broken citation onto a live page. Every value is verbatim from the
        # source except kou's, which is a transcription of data already on it.
        "ref_defs": {
            "gunshi": "''[[#gunshi|Aso County Gazetteer]]'' (阿蘇郡誌).",
            "keizu": "''[[#keizu|Compiled Genealogies of Ancient Clans]]'' (古代豪族系図集覧).",
            "mura": ("[http://www.ubuyama-v.jp/summary/history/ History of Ubuyama"
                     " Village] — Ubuyama Village official website (accessed 25 July"
                     " 2018 21:55 JST)."),
            "ihon": "''Aso Family Abbreviated Genealogy'' (阿蘇家略系譜).",
            "kou": "''[[#kou|Kokuzo Hongi Kō]]'' (国造本紀考).",
            "ruien": "''Kojirui-en: Jingi-bu 30''.",
            "shiki": "''[[Engishiki]]''.",
            "jingu": ("[http://miyazakijingu.jp/modules/about/index.php?content_id=2"
                      " Origin of Miyazaki Jingu] — Miyazaki Jingu official website"
                      " (accessed 6 July 2018 17:10 JST)."),
        },
    },
]

REDIRECT_RE = re.compile(r"^\s*#redirect\b", re.IGNORECASE)
HEADING_LINE_RE = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.M)
# A named ref USED without a body: <ref name="x" />. The DEF form carries a body.
REF_USE_RE = re.compile(r"<ref\s+name\s*=\s*[\"']?([^\"'>/]+?)[\"']?\s*/\s*>", re.I)
REF_DEF_RE = re.compile(r"<ref\s+name\s*=\s*[\"']?([^\"'>/]+?)[\"']?\s*>", re.I)


def _headings(text):
    """[(level, raw_name, start, body_start, end)] for every heading in ``text``.

    A section runs to the next heading of the same or shallower level, so carrying a
    ``==`` section brings its ``===`` subsections with it.
    """
    ms = list(HEADING_LINE_RE.finditer(text))
    out = []
    for i, m in enumerate(ms):
        level = len(m.group(1))
        end = len(text)
        for n in ms[i + 1:]:
            if len(n.group(1)) <= level:
                end = n.start()
                break
        out.append((level, m.group(2), m.start(), m.end(), end))
    return out


def _strip_leading_templates(text):
    """Return (prose, None) — the lead with its leading ``{{…}}`` blocks removed.

    An imported lead opens with an infobox, and an infobox is structured data about the
    SOURCE page's rendering, not prose to drop into the middle of another article. Braces
    are matched by depth rather than by regex because these boxes nest.
    """
    i, n = 0, len(text)
    while True:
        while i < n and text[i].isspace():
            i += 1
        if not text.startswith("{{", i):
            break
        depth, j = 0, i
        while j < n:
            if text.startswith("{{", j):
                depth += 1
                j += 2
            elif text.startswith("}}", j):
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        if depth != 0:
            return None, "unbalanced template braces in the source lead"
        i = j
    return text[i:].strip(), None


def _find_one(text, name):
    """The single heading normalising to ``name``, or (None, reason)."""
    want = normalize_heading(name)
    hits = [h for h in _headings(text) if normalize_heading(h[1]) == want]
    if not hits:
        return None, "no heading %r" % name
    if len(hits) > 1:
        return None, "heading %r occurs %d times — ambiguous" % (name, len(hits))
    return hits[0], None


def _depth_at(text, pos):
    """Template nesting depth at ``pos`` — 0 means ordinary article text."""
    return text.count("{{", 0, pos) - text.count("}}", 0, pos)


def _attach_ref_definitions(text, target, ref_defs):
    """Turn the FIRST ``<ref name="x"/>`` in the carried text into a full definition.

    A named ref whose definition lives in a section that is not being carried has to be
    supplied, and WHERE it is supplied decides whether the page renders. Putting the
    definitions in a ``{{Reflist|refs=}}`` block of their own looks tidy and is wrong:
    Cite renders a reference list at that point, listing what was used in PRIOR text, so
    every definition placed above its uses reports "defined in <references> is not used
    in prior text" and every use below it reports "no text was provided". Previewing
    健磐龍命's merge through ``action=parse`` before saving it turned 30 such errors up,
    including three on the TARGET's own refs, where the regex check had said the page was
    clean. Defining at first use needs no second list and lets the page's own
    ``{{reflist}}`` render everything.
    """
    for name, inner in ref_defs.items():
        if name in set(REF_DEF_RE.findall(target)) or name in set(REF_USE_RE.findall(target)):
            return None, ("ref %r already appears on the target — supplying a definition "
                          "for it here would edit the target's own citations" % name)
        use = re.compile(r"<ref\s+name\s*=\s*[\"']?%s[\"']?\s*/\s*>" % re.escape(name))
        # The first use at TEMPLATE DEPTH 0. A definition placed inside a template
        # parameter is not visible to ordinary uses: 健磐龍命's ``ruien`` landed inside a
        # ``{{Refnest|group="note"|…}}``, which defines it in the note group only, and
        # every main-group use then rendered "no text was provided". On the source that
        # went unnoticed because the infobox carried a second, top-level definition — and
        # the infobox is exactly what the lead carry strips. Found by previewing through
        # ``action=parse``; no regex over the wikitext would have shown it.
        m = next((x for x in use.finditer(text) if _depth_at(text, x.start()) == 0), None)
        if not m:
            continue                      # nothing carried uses it at top level
        text = (text[:m.start()]
                + "<ref name=\"%s\">%s</ref>" % (name, inner)
                + text[m.end():])
    return text, None


def carry_sections(source, target, plan, source_title=None, lead=None, ref_defs=None):
    """Return (new_target, notes) or (None, refusal_reason).

    ``plan`` is [(source heading, target heading to insert before)]. The result is
    the target with those source sections inserted and nothing else changed.

    ``lead``, when given, is ``{"heading", "anchor", "append"?}`` and carries the source's
    LEAD across under a heading of its own. The correspondence gate compares headings and
    never looks at a lead, so a source lead that outweighs the target's is invisible to it
    — 尾張氏's was 2,125b against 1,246b and held the clan's progenitor and its descendant
    houses. Emma's call, 2026-08-30: carry it as a section, then redirect.
    """
    if REDIRECT_RE.match(source):
        return None, "source is already a redirect"
    if REDIRECT_RE.match(target):
        return None, "target is a redirect, not an article"

    before_headings = [normalize_heading(h[1]) for h in _headings(target)]
    insertions, notes = [], []

    if lead:
        hs = _headings(source)
        raw = source[:hs[0][2]] if hs else source
        prose, why = _strip_leading_templates(raw)
        if prose is None:
            return None, why
        if not prose:
            return None, "the source lead is templates only, so there is nothing to carry"
        if normalize_heading(lead["heading"]) in before_headings:
            notes.append("lead as %r — already on the target, skipped" % lead["heading"])
        else:
            block = "== %s ==\n%s\n" % (lead["heading"], prose)
            if lead.get("append"):
                block += "\n%s\n" % lead["append"]
            anchor, why = _find_one(target, lead["anchor"])
            if anchor is None:
                return None, "on the target, for the lead: " + why
            insertions.append((anchor[2], block.rstrip("\n") + "\n\n"))
            notes.append("lead as %r -> before %s (%db)"
                         % (lead["heading"], lead["anchor"], len(block.encode("utf-8"))))
    for spec in plan:
        src_name, anchor_name = spec[0], spec[1]
        # A third element RENAMES the section as it lands. 健磐龍命's bibliography is
        # ``References`` on both pages, and the target's is a different list, so carrying
        # it needs a name of its own rather than a collision.
        new_name = spec[2] if len(spec) > 2 else src_name

        src_h, why = _find_one(source, src_name)
        if src_h is None:
            return None, "on the source: " + why

        if not source[src_h[3]:src_h[4]].strip():
            return None, ("source section %r is empty, so there is nothing to carry"
                          % src_name)
        if new_name == src_name:
            block = source[src_h[2]:src_h[4]]
        else:
            marks = "=" * src_h[0]
            block = ("%s %s %s\n%s" % (marks, new_name, marks,
                                       source[src_h[3]:src_h[4]].lstrip("\n")))
        src_name = new_name

        # Already there — SKIPPED, not refused. The guard exists to stop a section being
        # added twice, and skipping one that is already present serves that exactly.
        # Refusing the whole entry served it too, but it also made an entry that GREW
        # after a partial carry permanently unrunnable, which 尾張氏 hit the moment its
        # lead was added after its two sections had landed. A plain re-run is still
        # refused: every part is skipped, nothing is left to insert, and the check below
        # returns. The no-duplication property is unchanged.
        if normalize_heading(src_name) in before_headings:
            notes.append("%s — already on the target, skipped" % src_name)
            continue
        cls = heading_classes(src_name, None)
        if cls:
            for h in _headings(target):
                if not target[h[3]:h[4]].strip():
                    continue
                if cls & (heading_classes(h[1], None) or set()):
                    return None, ("target already covers %r under %r — carrying it "
                                  "would duplicate the section" % (src_name, h[1]))

        anchor, why = _find_one(target, anchor_name)
        if anchor is None:
            return None, "on the target: " + why
        insertions.append((anchor[2], block.rstrip("\n") + "\n\n"))
        notes.append("%s -> before %s (%db)"
                     % (src_name, anchor_name, len(block.encode("utf-8"))))

    # Blocks sharing an anchor are joined in DECLARED order and inserted once. Inserting
    # them one at a time at the same offset reverses them — the second insertion lands in
    # front of the first — which 尾張氏 was the first pair to hit, with two sections both
    # anchored before ``Genealogy``. Anchors themselves are applied back to front so the
    # earlier offsets stay valid.
    if not insertions:
        return None, "nothing left to carry — every part is already on the target"

    grouped = {}
    for at, block in insertions:
        grouped.setdefault(at, []).append(block)
    out = target
    for at in sorted(grouped, reverse=True):
        out = out[:at] + "".join(grouped[at]) + out[at:]

    if ref_defs:
        out, why = _attach_ref_definitions(out, target, ref_defs)
        if out is None:
            return None, why

    # Insertion-only, asserted rather than assumed: nothing on the target may vanish.
    after = [normalize_heading(h[1]) for h in _headings(out)]
    for h in before_headings:
        if h not in after:
            return None, "BUG: heading %r disappeared from the target" % h
    if len(out) <= len(target):
        return None, "BUG: the target did not grow"

    # Citations are checked on the ASSEMBLED page, not per section. A named ref may be
    # defined in another block travelling in the same run — 健磐龍命 defines its refs
    # across the lead, three content sections and an apparatus section, so a per-section
    # check refused a carry that was in fact complete. The property that matters is that
    # the carry introduces no broken citation, so a ref already dangling on the target is
    # excluded rather than blamed on this edit; a ref whose definition stays behind on
    # the source is still caught, because it is dangling after and was not before.
    was_dangling = set(REF_USE_RE.findall(target)) - set(REF_DEF_RE.findall(target))
    now_dangling = set(REF_USE_RE.findall(out)) - set(REF_DEF_RE.findall(out))
    introduced = sorted(now_dangling - was_dangling)
    if introduced:
        return None, ("the merged page would cite ref name(s) %s with no definition — "
                      "carrying it would break the citation"
                      % ", ".join(repr(d) for d in introduced))
    return out, notes


def lockout_blocks_us():
    checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_edit_allowed.py")
    if not os.path.isfile(checker):
        return False
    return subprocess.call([sys.executable, checker]) != 0


def main():
    parser = argparse.ArgumentParser(
        description="Carry source-only sections onto the English-titled twin.")
    parser.add_argument("--apply", action="store_true", help="Actually save (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=1,
                        help="Pairs per run (default 1, one per work-loop tick).")
    parser.add_argument("--run-tag", default="", help="Edit-summary suffix linking back to the run.")
    parser.add_argument("--only", default="", help="Restrict to this source title.")
    args = parser.parse_args()

    if args.apply and lockout_blocks_us():
        print("SKIPPED: miraheze editing is locked. Nothing attempted.")
        return 0

    import mwclient
    from shinto_miraheze.user_agent import USER_AGENT

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120

    entries = [c for c in CARRIES if not args.only or c["source"] == args.only]
    plan, held = [], []
    for entry in entries:
        src_title, dst_title = entry["source"], entry["target"]
        try:
            src, dst = site.pages[src_title], site.pages[dst_title]
            if not src.exists:
                held.append((src_title, dst_title, "source does not exist"))
                continue
            if not dst.exists:
                held.append((src_title, dst_title, "target does not exist"))
                continue
            src_text, dst_text = src.text(), dst.text()
        except Exception as e:
            print("ABORT: could not read %r/%r: %s" % (src_title, dst_title, e))
            return 2

        new_text, result = carry_sections(src_text, dst_text, entry["sections"],
                                          src_title, entry.get("lead"),
                                          entry.get("ref_defs"))
        if new_text is None:
            held.append((src_title, dst_title, result))
        else:
            plan.append((src_title, dst_title, new_text, result,
                         len(dst_text.encode("utf-8")), len(new_text.encode("utf-8"))))

    print("QUALIFYING (%d):" % len(plan))
    for s, d, _new, notes, before, after in plan:
        print("  %s -> %s   %db -> %db" % (s, d, before, after))
        for n in notes:
            print("      carry %s" % n)
    print("\nHELD (%d) — refused rather than guessed at:" % len(held))
    for s, d, reason in held:
        print("  %s -> %s\n      %s" % (s, d, reason))

    if not args.apply:
        print("\n[DRY] would edit %d target page(s). Re-run with --apply to save."
              % min(len(plan), args.max_edits))
        return 0

    from wiki_login import login_with_retry
    login_with_retry(site, USERNAME, PASSWORD)
    print("\nLogged in as %s" % USERNAME)

    done = errors = 0
    for src_title, dst_title, new_text, notes, _before, _after in plan:
        if done >= args.max_edits:
            print("Cap of %d reached, stopping. The rest run next tick." % args.max_edits)
            break
        try:
            names = ", ".join(n.split(" -> ")[0] for n in notes)
            site.pages[dst_title].save(
                new_text,
                summary=("Carry %s from the duplicate [[%s]] so nothing is lost when it "
                         "is redirected %s" % (names, src_title, args.run_tag)).strip())
            time.sleep(THROTTLE)
            print("  carried onto %s" % dst_title)
            done += 1
        except Exception as e:
            print("  ERROR saving %r: %s" % (dst_title, e))
            errors += 1

    print("\nCarried: %d   Held: %d   Errors: %d" % (done, len(held), errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
