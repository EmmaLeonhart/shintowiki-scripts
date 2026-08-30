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


def _find_one(text, name):
    """The single heading normalising to ``name``, or (None, reason)."""
    want = normalize_heading(name)
    hits = [h for h in _headings(text) if normalize_heading(h[1]) == want]
    if not hits:
        return None, "no heading %r" % name
    if len(hits) > 1:
        return None, "heading %r occurs %d times — ambiguous" % (name, len(hits))
    return hits[0], None


def carry_sections(source, target, plan, source_title=None):
    """Return (new_target, notes) or (None, refusal_reason).

    ``plan`` is [(source heading, target heading to insert before)]. The result is
    the target with those source sections inserted and nothing else changed.
    """
    if REDIRECT_RE.match(source):
        return None, "source is already a redirect"
    if REDIRECT_RE.match(target):
        return None, "target is a redirect, not an article"

    before_headings = [normalize_heading(h[1]) for h in _headings(target)]
    insertions, notes = [], []
    for src_name, anchor_name in plan:
        src_h, why = _find_one(source, src_name)
        if src_h is None:
            return None, "on the source: " + why

        block = source[src_h[2]:src_h[4]]
        if not source[src_h[3]:src_h[4]].strip():
            return None, ("source section %r is empty, so there is nothing to carry"
                          % src_name)

        # Already there — this is what makes a re-run a no-op rather than a duplicate.
        if normalize_heading(src_name) in before_headings:
            return None, "target already has a %r heading" % src_name
        cls = heading_classes(src_name, None)
        if cls:
            for h in _headings(target):
                if not target[h[3]:h[4]].strip():
                    continue
                if cls & (heading_classes(h[1], None) or set()):
                    return None, ("target already covers %r under %r — carrying it "
                                  "would duplicate the section" % (src_name, h[1]))

        # A named ref whose definition stays behind renders as a cite error.
        defined = set(REF_DEF_RE.findall(block)) | set(REF_DEF_RE.findall(target))
        dangling = sorted(set(REF_USE_RE.findall(block)) - defined)
        if dangling:
            return None, ("section %r cites ref name(s) %s defined outside it — "
                          "carrying it would break the citation"
                          % (src_name, ", ".join(repr(d) for d in dangling)))

        anchor, why = _find_one(target, anchor_name)
        if anchor is None:
            return None, "on the target: " + why
        insertions.append((anchor[2], block.rstrip("\n") + "\n\n"))
        notes.append("%s -> before %s (%db)"
                     % (src_name, anchor_name, len(block.encode("utf-8"))))

    out = target
    for at, block in sorted(insertions, key=lambda x: -x[0]):
        out = out[:at] + block + out[at:]

    # Insertion-only, asserted rather than assumed: nothing on the target may vanish.
    after = [normalize_heading(h[1]) for h in _headings(out)]
    for h in before_headings:
        if h not in after:
            return None, "BUG: heading %r disappeared from the target" % h
    if len(out) <= len(target):
        return None, "BUG: the target did not grow"
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

        new_text, result = carry_sections(src_text, dst_text, entry["sections"], src_title)
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
