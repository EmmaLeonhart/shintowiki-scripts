#!/usr/bin/env python3
"""
dedupe_duplicate_qids.py
========================
Resolves duplicate-QID pairs from ``orchestrators/duplicate_qids.state``
by moving the non-canonical title to a redirect pointing at the canonical
title.

TWO SEPARATE QUESTIONS, and conflating them is how this file went wrong twice:

  * **Which page is canonical?** — ``pick_canonical``.
  * **May the other page be REDIRECTED OVER?** — ``PROVEN_REASONS``.

A group can have an obvious canonical and still be untouchable, because the
non-canonical page holds content that only exists there.

Canonical selection, in priority order
--------------------------------------
  1. The sole page with no ``(Qnnn)`` suffix. A QID-stub title is a generator
     PLACEHOLDER, so a real name always beats one — including when the stub's own
     QID happens to be the group's, which the reverse ordering got wrong and which
     accounted for 16 of 18 "unexplained" groups on 2026-08-27.
  2. Wikidata's own naming, applied strictly: exactly one page EQUALS the item's
     English label and every other real-named page is a registered English alias.
  3. Among several real names, the one that is a real ARTICLE rather than a
     property dump (a page that is an infobox plus ``== instance of (P31) ==``
     sections and nothing else). Mainspace only — prose length says nothing about
     a template, whose content is its markup.
  4. Among stubs only, the page whose own title QID is the group's.

Anything else is reported as ambiguous, never guessed: two real articles, two
unrelated stubs, a template beside a mainspace page (a wrong ``{{wikidata link}}``,
not a duplicate), a template ``/doc`` subpage inheriting its parent's link.

Permission to overwrite content
-------------------------------
Only a move whose reason is in ``PROVEN_REASONS`` may replace a live page:

  * ``REASON_WD_REDIRECT`` — the demoted page's title QID is a Wikidata REDIRECT
    into the group's QID, so the items were already merged upstream. Emma's
    ruling, 2026-08-26: *"if one redirects into another on wikidata then that's
    clear evidence you can just redirect it on the shintowiki too."*
  * ``REASON_PROPERTY_DUMP`` — the demoted page is a generated dump, so there is
    nothing to lose.
  * ``REASON_WD_ALIAS`` — a registered alias AND not a real article. Wikidata
    saying two names denote one thing does not mean one article contains the other.

⚠ **The JP-script → rōmaji heuristic is deliberately NOT proven, and now emits
nothing executable at all.** In mainspace the dump rule reaches every measured pair
first (and is better, being proven); for templates prose cannot decide. It is kept
because it still classifies, not because it acts. It was harmless for as long as
this script only performed MediaWiki *moves* — a move cannot clobber a live page —
and adding the redirect-over-content path in 2026-08-26 briefly made it
destructive: it would have redirected 健磐龍命 (19,095 bytes, with Nihon Shoki and
Fudoki sections) onto a page containing neither.

An unmeasured page counts as an ARTICLE everywhere. Unknown never authorises an
edit.

Flags
-----
``--plan-only`` builds and prints the plan, then exits BEFORE login — every
planning stage is read-only, so anyone can check the numbers a report quotes
without credentials. ``--apply`` (default dry-run), ``--max-edits`` (cap per run,
default 50), ``--run-tag`` (edit-summary link back to the CI run; required for
anything that edits, not for ``--plan-only``).

A wiki outage ABORTS rather than degrading: a partial read would silently produce a
smaller plan that looks complete.
"""

import argparse
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

import urllib.parse
import urllib.request

import mwclient
from wiki_login import login_with_retry

# Force UTF-8 so Japanese titles survive a cp1252 Windows console. Guarded on
# the current encoding: under pytest, stdout is an already-UTF-8 capture object
# with no .buffer, and rewrapping it made the module unimportable -- the wrapper
# outlived the captured file and teardown died on a closed handle. Anything that
# is already UTF-8 needs no help.
if getattr(sys.stdout, "encoding", "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

# Was a module-level hardcoded "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) ..."
# literal shadowing the canonical constant. Two problems: it pinned a version that is now three
# releases stale, and this file is wiki-side only, so the persona was RIGHT and only the
# version was wrong -- which is the quiet half of the same bug: a stale literal drifts
# silently while the canonical constant moves.
from shinto_miraheze.user_agent import USER_AGENT

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DUPES_STATE = os.path.join(SCRIPT_DIR, "orchestrators", "duplicate_qids.state")
DONE_STATE = os.path.join(SCRIPT_DIR, "dedupe_duplicate_qids.state")

GIT_SYNCED_RE = re.compile(r"\[\[\s*Category\s*:\s*Git synced pages\s*\]\]",
                           re.IGNORECASE)
JP_RE = re.compile(r"[぀-ヿ一-鿿＀-￯]")
QID_PAREN_RE = re.compile(r"\(Q\d+\)")

# A page is a Wikidata PROPERTY DUMP, not an article, if almost nothing survives
# stripping its `== … (Pxxx) ==` sections, templates and markup. Measured across
# the whole duplicate report on 2026-08-27, dumps land at 90-174 bytes of prose
# and real articles at 587-11,419 — so this threshold sits in a wide gap, not on a
# fine line. `shinto_miraheze/classify_duplicate_group_pages.py` produces the map.
ARTICLE_PROSE_BYTES = 200

REASON_WD_REDIRECT = "Wikidata redirect → same item"
REASON_PROPERTY_DUMP = "property dump → article (same QID)"
REASON_WD_ALIAS = "Wikidata alias → label title (same item)"
# Reasons allowed to overwrite a live page's content with a redirect. A Wikidata
# redirect proves one entity; a property dump has no content to lose. The
# JP-script heuristic is deliberately absent — see perform_move.
PROVEN_REASONS = frozenset({REASON_WD_REDIRECT, REASON_PROPERTY_DUMP,
                            REASON_WD_ALIAS})

# Skip outcomes that are FINAL: the work is genuinely finished or the source is
# gone, so recording them in the done-state is correct and stops a pointless
# re-check every run.
TERMINAL_SKIPS = ("skipped:src already redirect", "skipped:src missing")


def is_terminal_skip(result: str) -> bool:
    """Only a terminal skip belongs in the done-state.

    ⚠ Every skip used to be recorded, and `pending` filters out anything in the
    done-state — so a page skipped for a reason that MIGHT CHANGE was buried
    permanently. That silently retired the 44 JP-script pages, which are skipped
    for lack of proof, not because they are resolved: the moment a Wikidata
    redirect appears or a human merges the content, they should come back.
    Likewise a destination that is currently a redirect may stop being one.

    Re-checking a conditional skip costs two API reads per run and no edits — a
    skip never increments the move counter, so it cannot consume the edit budget.
    """
    return result.startswith(TERMINAL_SKIPS)

# Prose length only means something for ARTICLES. A template or a category has
# little prose by nature, so the dump test classifies almost any of them as a dump
# and the tie-break then picks whichever happens to have more words. Measured
# 2026-08-27, that proposed `Template:Topic category` -> `Template:テーマカテゴリ`
# and `Template:Japanese year` -> `Template:和暦`, pointing English at Japanese and
# inverting this wiki's own convention. Mainspace only.
NAMESPACED_RE = re.compile(r"^[A-Za-z][A-Za-z ]*:")

# A destination must not be a malformed title. `Mishima Shrine (Minamiizu )` has a
# trailing space inside its disambiguator; redirecting a well-formed page into it
# would make the typo canonical.
MALFORMED_TITLE_RE = re.compile(r"\s\)|\s$|  ")


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING: could not read {path}: {e}")
        return {}


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


WD_API = "https://www.wikidata.org/w/api.php"
WD_BATCH = 40


def resolve_qid_redirects(qids, user_agent: str) -> dict:
    """Map each QID to the QID Wikidata actually serves for it.

    ``wbgetentities`` keys its response by the id you ASKED for, while the
    entity's own ``id`` field is the id you LANDED on. Requested != returned
    therefore means the requested QID is a redirect into the returned one.

    ⛔ Do NOT add ``redirects=no``. It suppresses the resolution, every pair
    comes back looking like two distinct live items, and the caller draws the
    exact opposite conclusion. That mistake was made on 2026-08-26 and caught
    only because the two "distinct" items had byte-identical claims.

    A QID that is missing/deleted maps to None. On a network error the batch is
    dropped rather than guessed — an unresolved QID simply fails the redirect
    test, which is the safe direction.
    """
    out: dict = {}
    ids = sorted({q for q in qids if q})
    for i in range(0, len(ids), WD_BATCH):
        batch = ids[i:i + WD_BATCH]
        url = WD_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(batch),
            "format": "json", "props": "info",
        })
        try:
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=60) as fh:
                data = json.load(fh)
        except Exception as e:
            print(f"  Wikidata resolve failed for batch {i // WD_BATCH}: {e}; "
                  f"{len(batch)} QIDs left unresolved this run")
            time.sleep(1.0)
            continue
        for key, ent in (data.get("entities") or {}).items():
            out[key] = None if "missing" in ent else ent.get("id")
        time.sleep(0.25)
    return out


def fetch_labels(qids, user_agent: str) -> dict:
    """QID -> (english label, set of english aliases). Wikidata's own naming.

    Used only where it can be decisive: a group whose titles are variant
    romanisations of one name. See pick_canonical for why that is narrow.
    """
    out: dict = {}
    ids = sorted({q for q in qids if q})
    for i in range(0, len(ids), WD_BATCH):
        batch = ids[i:i + WD_BATCH]
        url = WD_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(batch),
            "format": "json", "props": "labels|aliases", "languages": "en",
        })
        try:
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=60) as fh:
                data = json.load(fh)
        except Exception as e:
            print(f"  Wikidata label fetch failed for batch {i // WD_BATCH}: {e}")
            time.sleep(1.0)
            continue
        for key, ent in (data.get("entities") or {}).items():
            if "missing" in ent:
                continue
            label = (ent.get("labels") or {}).get("en", {}).get("value")
            aliases = {a["value"] for a in (ent.get("aliases") or {}).get("en", [])}
            out[key] = (label, aliases)
        time.sleep(0.25)
    return out


def pick_canonical(qid: str, pages: list[str],
                   prose_lengths: dict | None = None,
                   labels: dict | None = None) -> str | None:
    """The sole real-named page, else the page that OWNS the group's QID.

    ⚠ ORDER IS LOAD-BEARING, and it used to be the other way round. A title like
    ``Takanono Shrine (Q135040588)`` is a generator PLACEHOLDER, not a name anyone
    chose; the real name is the intended final title, which is why the repo's
    original heuristic said QID-stub loses to real name. Preferring the
    QID-owning page inverted that: for a group of ``X`` plus ``X (Qnnn)`` where
    the stub's own QID is the group's, it picked the stub as canonical, then found
    nothing left to prove (the real-named page has no QID in its title to resolve)
    and dropped the whole group into the ambiguous bucket.

    Measured 2026-08-27: that mis-ordering accounted for 16 of the 18 groups filed
    under "QID stub with no Wikidata redirect", i.e. almost the entire unexplained
    residue of the report. It would also have redirected real titles onto
    placeholder ones had those pages not already been fixed by hand.

    QID ownership still decides, but only among stubs — ``X (Q1)`` vs ``X (Q2)``
    filed under Q1 — where there is no real name to prefer.

    Returns None when neither test picks exactly one page: two real names, two
    unrelated stubs, a three-page group with two candidates. Ambiguous groups are
    reported, never guessed.
    """
    no_stub = [p for p in pages if not QID_PAREN_RE.search(p)]

    # A property dump is not a real name. It has no `(Qnnn)` suffix, so a
    # title-only test cannot tell it from an article, and every one sitting
    # opposite a genuine article turned a mechanical merge into a decision handed
    # to a human — 12 of the 25 such groups on 2026-08-27. An unmeasured page
    # counts as an article: unknown must never demote something real.
    # Wikidata's own naming, applied STRICTLY. Exactly one page must equal the
    # item's English label and EVERY other real-named page must be a registered
    # English alias of the same item — i.e. Wikidata already says these are other
    # names for one thing. Anything less gets no verdict.
    #
    # The strictness is the point, tested against the groups that must NOT resolve:
    # `Benzaiten` / `Benzaiten shrines` declines because "Benzaiten shrines" is not
    # an alias (it is a different subject sharing a QID — a wrong-link problem, not
    # a merge), and so do Hime Shrine/Himegami, Amatsu Shrine/(Itoigawa), the two
    # Achi Shrines and Sōja shrine/Template. Only variant romanisations of one
    # name resolve — Shioe/Shionoe, Shinmei-sha variants, Kaneno/Kinshin.
    if labels and len(no_stub) > 1 and qid in labels:
        label, aliases = labels[qid]
        if label:
            named = [p for p in no_stub if p == label]
            others = [p for p in no_stub if p != label]
            if len(named) == 1 and others and all(p in aliases for p in others):
                return named[0]

    # ⚠ Only a TIE-BREAKER among several real names. Applying it to a lone real
    # name is a regression I measured before shipping: a group of `X (Qnnn)` plus a
    # dump-shaped `X` was resolving fine, and disqualifying `X` for being a dump
    # pushed it into the ambiguous bucket — moves 131 -> 103, ambiguity 46 -> 75.
    # A dump is a page that needs CONTENT, not a page with the wrong title; when it
    # is the only real name it is still the right destination.
    if prose_lengths and len(no_stub) > 1 and not any(NAMESPACED_RE.match(p) for p in no_stub):
        articles = [p for p in no_stub
                    if prose_lengths.get(p, ARTICLE_PROSE_BYTES) >= ARTICLE_PROSE_BYTES]
        if len(articles) == 1 and not MALFORMED_TITLE_RE.search(articles[0]):
            return articles[0]
        return None          # several articles, none, or a malformed target

    if len(no_stub) == 1:
        return no_stub[0]
    if no_stub:
        return None          # two or more real names — a human picks
    exact = [p for p in pages if QID_PAREN_RE.search(p)
             and QID_PAREN_RE.search(p).group(0)[1:-1] == qid]
    if len(exact) == 1:
        return exact[0]
    return None


def title_qid(title: str) -> str | None:
    m = QID_PAREN_RE.search(title)
    return m.group(0)[1:-1] if m else None


def build_move_plan(state: dict, resolved: dict | None = None,
                    prose_lengths: dict | None = None,
                    labels: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Return (auto_moves, ambiguous_groups) from the duplicate-QID state.

    PRIMARY RULE (Emma, 2026-08-26): *"if one redirects into another on wikidata
    then that's clear evidence you can just redirect it on the shintowiki too."*
    When a page's own title QID resolves to the group's QID, the two pages are two
    pages for one Wikidata item and the non-canonical one is redirected.

    This OUTRANKS the old title heuristics, which guessed from title shape and got
    it wrong in both directions: 29 of 43 stubs checked on 2026-08-26 were filed
    under a QID other than the one in their own title, and 8 pairs carried visibly
    different shrine names (the historical Engishiki name beside the modern shrine
    name) that the heuristics would have refused or mis-ordered.

    The heuristics remain as a FALLBACK for titles carrying no QID at all
    (Japanese-script vs rōmaji), where there is nothing for Wikidata to resolve.

    ``resolved`` maps QID -> the QID Wikidata serves for it. Pass None to skip the
    primary rule entirely (offline/unit-test use) and fall back to heuristics.
    """
    resolved = resolved or {}
    prose_lengths = prose_lengths or {}
    labels = labels or {}
    qid_to_pages: dict[str, list[str]] = defaultdict(list)
    for title, qid in state.items():
        qid_to_pages[qid].append(title)

    auto_moves: list[dict] = []
    ambiguous: list[dict] = []

    for qid, pages in sorted(qid_to_pages.items()):
        if len(pages) < 2:
            continue

        # Template /doc pairs — the doc subpage inherits its parent's
        # {{wikidata link}}. Never a duplicate; the fix is stripping the
        # template from the subpage, not merging the two.
        if any("/doc" in p and p.startswith("Template:") for p in pages):
            ambiguous.append({"qid": qid, "pages": pages, "reason": "template/doc pair"})
            continue

        # A Template: or Category: page grouped with a MAINSPACE page is a
        # wrong-link, not a duplicate: a navbox is not the concept it navigates.
        # Measured 2026-08-27, `Template:Ichinomiya` sits on Q1656379 ("Shinto
        # shrine with the highest rank in a province") beside the article
        # `Ichinomiya`, and `Template:Sōja shrines` on Q1107129 beside `Sōja
        # shrine`. Merging either would delete a navbox into an article. The fix
        # belongs on the template's {{wikidata link}}.
        #
        # Template-to-template pairs are NOT this — `Template:警告` beside
        # `Template:Warning` is a genuine cross-language duplicate — so this fires
        # only on a MIX of namespaced and mainspace titles.
        namespaced = [p for p in pages if NAMESPACED_RE.match(p)]
        if namespaced and len(namespaced) != len(pages):
            ambiguous.append({
                "qid": qid, "pages": pages,
                "reason": "template/category grouped with a mainspace page — "
                          "wrong {{wikidata link}}, not a merge",
            })
            continue

        # ── PRIMARY: proven Wikidata redirect ──────────────────────
        canonical = pick_canonical(qid, pages, prose_lengths, labels)
        if canonical is not None:
            proven = []
            for p in pages:
                if p == canonical:
                    continue
                if resolved.get(title_qid(p)) == qid:
                    proven.append((p, REASON_WD_REDIRECT))
                elif (not title_qid(p) and qid in labels
                      and p in (labels[qid][1] or set())
                      # ⚠ Wikidata saying two names denote one thing does NOT mean
                      # one article contains the other. Without this check the
                      # alias rule would redirect over a real page: measured
                      # 2026-08-27, `Teranomikoto Shrine` is a registered alias of
                      # Kamisawa Shrine's item AND carries an imported
                      # `== Japanese Wikipedia content ==` section that Kamisawa
                      # does not have. Same reasoning that gated the JP-script
                      # heuristic. An UNMEASURED page counts as an article — the
                      # safe direction.
                      and prose_lengths.get(p, ARTICLE_PROSE_BYTES) < ARTICLE_PROSE_BYTES):
                    proven.append((p, REASON_WD_ALIAS))
                elif (not title_qid(p) and p in prose_lengths
                      and prose_lengths[p] < ARTICLE_PROSE_BYTES):
                    # Same QID, and nothing to lose: the page is a generated
                    # property dump whose prose is boilerplate.
                    proven.append((p, REASON_PROPERTY_DUMP))
            if proven:
                for non_canon, why in proven:
                    auto_moves.append({
                        "qid": qid, "from": non_canon, "to": canonical,
                        "reason": why,
                    })
                proven_pages = {p for p, _ in proven}
                unproven = [p for p in pages
                            if p != canonical and p not in proven_pages]
                if unproven:
                    ambiguous.append({"qid": qid, "pages": unproven,
                                      "reason": "no Wikidata redirect into the group QID"})
                continue

        # ── FALLBACK: title heuristics, QID-less titles only ───────
        has_qid_stub = [p for p in pages if QID_PAREN_RE.search(p)]
        no_qid_stub = [p for p in pages if not QID_PAREN_RE.search(p)]

        has_jp = [p for p in pages if JP_RE.search(p)]
        no_jp = [p for p in pages if not JP_RE.search(p)]

        if has_jp and len(no_jp) == 1 and not has_qid_stub:
            # Split by what the demoted page actually HOLDS. An unproven move is
            # skipped at execution anyway, so emitting one as an "auto-move"
            # overstates the plan: it promises an edit that can never happen.
            # Measured 2026-08-27, 41 of these 44 demote a REAL ARTICLE, and in
            # most cases the Japanese page is the LARGER of the two
            # (健磐龍命 10,069 → 6,873 prose bytes; 上毛野国造 4,658 → 2,959). Those
            # are content merges for a human, not redirects. Unmeasured counts as
            # an article — the safe direction.
            # A TEMPLATE's content is its markup, not its prose, so prose length
            # cannot clear it: Template:警告 measures 0 prose and is 4,074 bytes of
            # working template. Namespaced pairs are therefore always a merge for a
            # human. Combined with the dump rule reaching every measured mainspace
            # pair first, this leaves the script heuristic emitting nothing
            # executable — which is the honest state, not a rule to keep pretending
            # with.
            if any(NAMESPACED_RE.match(p) for p in pages):
                mergeable = list(has_jp)
            else:
                mergeable = [p for p in has_jp
                             if prose_lengths.get(p, ARTICLE_PROSE_BYTES) >= ARTICLE_PROSE_BYTES]
            demotable = [p for p in has_jp if p not in mergeable]
            for non_canon in demotable:
                auto_moves.append({
                    "qid": qid, "from": non_canon, "to": no_jp[0],
                    "reason": "JP-script → ASCII/rōmaji",
                })
            if mergeable:
                ambiguous.append({
                    "qid": qid, "pages": mergeable + [no_jp[0]],
                    "reason": "two real articles — a content merge, not a redirect",
                })
            continue

        # Name the reason it ACTUALLY fell through. These labels are the only
        # description anyone gets of the residue, and a wrong one sends the next
        # reader hunting a defect that is not there: 18 groups sat under "no
        # Wikidata redirect" on 2026-08-27 when 16 were a canonical-precedence bug
        # and the other 2 had a perfectly good redirect but two real names.
        if len(no_qid_stub) > 1:
            reason = "two or more real names — no single canonical"
        elif has_qid_stub and not no_qid_stub:
            reason = "both QID stubs, neither owns the group QID"
        elif has_qid_stub:
            reason = "QID stub with no Wikidata redirect into the group QID"
        else:
            reason = "unclear canonical"
        ambiguous.append({"qid": qid, "pages": pages, "reason": reason})

    return auto_moves, ambiguous


def perform_move(site, src: str, dst: str, run_tag: str, apply: bool,
                 proven: bool = False) -> str:
    """Move src → dst (leave redirect). Returns: 'moved', 'skipped', or 'error:<msg>'."""
    try:
        src_page = site.pages[src]
    except Exception as e:
        return f"error:fetch src: {e}"

    if not src_page.exists:
        return "skipped:src missing"

    src_text = src_page.text()
    if re.match(r"^\s*#redirect\b", src_text, re.IGNORECASE):
        return "skipped:src already redirect"

    try:
        dst_page = site.pages[dst]
        dst_exists = dst_page.exists
    except Exception as e:
        return f"error:fetch dst: {e}"

    if dst_exists:
        dst_text = dst_page.text()
        if re.match(r"^\s*#redirect\b", dst_text, re.IGNORECASE):
            return "skipped:dst is a redirect (title collision)"
        if not proven:
            # ⛔ Content overwrite is allowed ONLY for a proven Wikidata redirect.
            # The JP-script heuristic was safe for as long as this branch just
            # skipped: a move cannot clobber a live page, so a wrong guess cost
            # nothing. Adding the redirect-over-content path below turned that
            # same heuristic into a content-destroying one -- measured 2026-08-27,
            # its 45 pending moves include 健磐龍命 (19,095 b, with Nihon Shoki and
            # Fudoki sections) redirecting onto a 13,161 b page that does not
            # contain them. Two titles sharing a QID is not evidence that one
            # article contains the other.
            return "skipped:dst exists as real page (heuristic move, unproven)"
        # Both pages exist as real pages. A MediaWiki move REFUSES this, which
        # is why every duplicate-QID group came back "skipped:dst exists as real
        # page": the move path could only ever help when the canonical title was
        # still free, and for a duplicate it never is. Replacing the
        # non-canonical page's content with a redirect is the merge that
        # actually applies. Only reachable once the caller has proven
        # same-entity via the Wikidata redirect.
        summary = (f"Bot: redirect duplicate QID page to canonical title "
                   f"(same Wikidata item) {run_tag}").strip()
        if not apply:
            return "dry:would redirect over content"
        try:
            new_text = f"#REDIRECT [[{dst}]]\n"
            # git_synced/ membership is load-bearing: dropping the category makes
            # the next sync treat the page as removed-from-repo and untrack it.
            if GIT_SYNCED_RE.search(src_text):
                new_text += "\n[[Category:Git synced pages]]\n"
            src_page.save(new_text, summary=summary)
            return "redirected"
        except Exception as e:
            return f"error:{e}"

    summary = f"Bot: redirect duplicate QID title to canonical page {run_tag}".strip()

    if not apply:
        return "dry:would move"

    try:
        src_page.move(dst, reason=summary, no_redirect=False)
        return "moved"
    except Exception as e:
        return f"error:{e}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually perform moves (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Maximum page moves per run (default 50).")
    parser.add_argument("--run-tag", default="",
                        help="Edit-summary suffix linking back to the CI run. "
                             "Required for anything that edits; not for --plan-only.")
    parser.add_argument("--plan-only", action="store_true",
                        help="Print the plan and exit BEFORE logging in. Every "
                             "planning stage is read-only, so this needs no bot "
                             "password and can be run by anyone to check the "
                             "numbers a report quotes.")
    args = parser.parse_args()
    if not args.plan_only and not args.run_tag:
        parser.error("--run-tag is required unless --plan-only is given")

    state = load_json(DUPES_STATE)
    if not state:
        print(f"No state loaded from {DUPES_STATE} — nothing to do.")
        return

    done: dict = load_json(DONE_STATE)  # {"from_title": "to_title"}
    print(f"Loaded {len(state)} tracked titles; {len(done)} moves already recorded.")

    # Resolve every QID appearing in a duplicate group against Wikidata. A
    # requested id that comes back as a DIFFERENT id is a redirect, which is
    # the evidence the planner needs to call two pages one entity.
    qid_to_pages_m: dict[str, list[str]] = defaultdict(list)
    for _t, _q in state.items():
        qid_to_pages_m[_q].append(_t)
    dup_qids = {q for q, ps in qid_to_pages_m.items() if len(ps) > 1}
    to_resolve = set(dup_qids)
    for q in dup_qids:
        for pg in qid_to_pages_m[q]:
            tq = title_qid(pg)
            if tq:
                to_resolve.add(tq)
    print(f"Resolving {len(to_resolve)} QIDs against Wikidata...")
    resolved = resolve_qid_redirects(to_resolve, USER_AGENT)
    n_red = sum(1 for k, v in resolved.items() if v and v != k)
    print(f"  {n_red} of {len(resolved)} resolve to a different QID (redirects)")

    # Measure the real-named pages so a property dump is not mistaken for an
    # article. Done HERE rather than inside build_move_plan on purpose: the
    # planner stays pure (titles + two lookup maps), so every test can call it
    # without network I/O. See classify_duplicate_group_pages for the method and
    # for the nested-template trap in measuring prose.
    from shinto_miraheze.classify_duplicate_group_pages import (
        WikiUnavailable, fetch_contents, is_property_dump, prose_length,
    )
    candidates = sorted({p for q in dup_qids for p in qid_to_pages_m[q]
                         if not title_qid(p)})
    prose_lengths = {}
    if candidates:
        print(f"Measuring {len(candidates)} real-named pages (article vs property dump)...")
        try:
            fetched = fetch_contents(candidates)
        except WikiUnavailable as e:
            # Refuse to plan rather than plan from partial data. See WikiUnavailable.
            print()
            print(f"ABORTING: {e}")
            raise SystemExit(1)
        for title, text in fetched.items():
            if text is None:
                continue
            # Heading test first, prose second. A page carrying `== x (Pnnn) ==`
            # headings is a dump however much text it holds — measured 2026-08-28,
            # the six groups left for a human were each an article beside a dump,
            # and PROSE MISSED ALL SIX because those dumps also import the jawiki
            # article and its citations. Prose still decides the headless stubs.
            prose_lengths[title] = 0 if is_property_dump(text) else prose_length(text)
        dumps = sum(1 for n in prose_lengths.values() if n < ARTICLE_PROSE_BYTES)
        print(f"  {dumps} of {len(prose_lengths)} are property dumps")

    # Wikidata's own naming, for groups whose titles are variant romanisations.
    print(f"Fetching English labels/aliases for {len(dup_qids)} group QIDs...")
    labels = fetch_labels(dup_qids, USER_AGENT)

    auto_moves, ambiguous = build_move_plan(state, resolved, prose_lengths, labels)
    pending = [m for m in auto_moves if m["from"] not in done]

    # Separate the executable count from the total. They diverged badly once —
    # the plan advertised 146 auto-moves of which only 102 could ever run, because
    # unproven heuristic moves always skip. A single headline number hid that.
    executable = [m for m in auto_moves if m["reason"] in PROVEN_REASONS]
    print(f"Move plan: {len(auto_moves)} total auto-picks, "
          f"{len(executable)} PROVEN (can actually edit), "
          f"{len(pending)} pending (not yet done), "
          f"{len(ambiguous)} ambiguous (skipped).")
    print()
    by_reason = Counter(m["reason"] for m in auto_moves)
    for reason, count in sorted(by_reason.items(), key=lambda kv: -kv[1]):
        mark = "proven  " if reason in PROVEN_REASONS else "unproven"
        print(f"  moves     {count:4}  [{mark}] {reason}")
    for reason, count in sorted(Counter(g["reason"] for g in ambiguous).items(),
                                key=lambda kv: -kv[1]):
        print(f"  ambiguous {count:4}            {reason}")
    print()

    if args.plan_only:
        print("--plan-only: stopping before login. Nothing was edited, and no "
              "credentials were used.")
        return

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")
    print()

    moved = skipped = errors = 0
    budget = args.max_edits

    for i, move in enumerate(pending, 1):
        if moved >= budget:
            print(f"Budget of {budget} moves reached, stopping.")
            break

        src, dst, reason, qid = move["from"], move["to"], move["reason"], move["qid"]
        print(f"[{i}/{len(pending)}] {reason} | {qid}")
        print(f"  MOVE  {repr(src)}")
        print(f"    →   {repr(dst)}")

        result = perform_move(site, src, dst, args.run_tag, args.apply,
                              proven=reason in PROVEN_REASONS)
        print(f"  → {result}")

        if result.startswith(("moved", "redirected", "dry")):
            if result.startswith(("moved", "redirected")):
                moved += 1
                done[src] = dst
            print()
            time.sleep(THROTTLE)
        elif result.startswith("skipped"):
            skipped += 1
            if is_terminal_skip(result):
                done[src] = f"skipped:{result}"
            else:
                print("  (conditional — not recorded; will be re-checked next run)")
            print()
        else:
            errors += 1
            print()

    if args.apply and (moved or skipped):
        save_json(DONE_STATE, done)
        print(f"Saved {DONE_STATE} ({len(done)} entries).")

    print()
    print("=" * 60)
    print(f"Moves performed:  {moved}")
    print(f"Skipped:          {skipped}")
    print(f"Errors:           {errors}")
    print(f"Budget remaining: {max(0, budget - moved)}")
    print()
    if ambiguous:
        print(f"Ambiguous groups not auto-resolved ({len(ambiguous)}):")
        for g in ambiguous:
            print(f"  {g['qid']} ({g['reason']}):")
            for p in g["pages"]:
                print(f"    - {p}")


if __name__ == "__main__":
    main()
