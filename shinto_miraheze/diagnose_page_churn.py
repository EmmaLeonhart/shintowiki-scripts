#!/usr/bin/env python3
"""
diagnose_page_churn.py
======================
Phase 1 of the "diagnose and fix the page-churn loops" queue item
(2026-05-26): pull recent revisions of a sample of pages and identify
where two bot scripts/ops are alternating on the same page — which is
the churn pattern Emma flagged.

Sampling: walks ``[[Category:Git synced pages]]`` on
shinto.miraheze.org (the category Emma specifically named for the
git_synced ↔ orchestrator churn) and picks ``SAMPLE_SIZE`` titles at
random. For each, fetches the last ``REV_LIMIT`` revisions via
``prop=revisions&rvprop=timestamp|user|comment``.

Per-revision script attribution is by **edit-summary keyword
matching** (the project's bot edits prefix summaries with stable
keywords — ``Sync from repo git_synced/``, ``Bot: untransclude crud
templates``, ``canonicalise Template:Infobox case``, etc.). Anything
unmatched is reported as ``unknown``.

Output: a markdown report at ``docs/page_churn_diagnostic.md`` with
per-page edit traces + a histogram of script-pair alternations across
the sample. Read-only; no wiki edits, no commits.

This is the **diagnose** step. The **fix** step depends on which
script-pairs the report flags as alternating, and which side's view
of the canonical page form is correct — that needs Emma's input
before any code changes downstream.
"""

import argparse
import collections
import io
import random
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
USER_AGENT = (
    "DiagnosePageChurn/1.0 (User:EmmaBot; shinto.miraheze.org; "
    "read-only diagnostic)"
)
HTTP_TIMEOUT = 30
CATEGORY = "Git synced pages"
SAMPLE_SIZE = 20
REV_LIMIT = 30
OUTPUT_PATH = "docs/page_churn_diagnostic.md"

# Each row: (script_id, list of keyword substrings — case-insensitive)
# The FIRST match wins, so order matters when patterns overlap. Add
# rows here as new bot scripts surface in summaries.
SCRIPT_PATTERNS: list[tuple[str, list[str]]] = [
    ("sync_git_synced", ["sync from repo git_synced/"]),
    ("sync_miraheze_unique", ["sync from repo miraheze_unique/"]),
    ("sync_fandom_unique", ["sync from repo fandom_unique/"]),
    ("sync_duplicated_content", ["sync from repo duplicated_content/"]),
    ("sync_need_translation", ["sync from repo need_translation/"]),
    ("untransclude_crud", ["untransclude crud templates"]),
    ("canonicalize_template_case", ["canonicalise template:infobox case",
                                    "canonicalize template:infobox case"]),
    ("wikidata_link_tag", ["pages without wikidata", "templates missing wikidata"]),
    ("wikidata_lookup", ["sync sitelinks from wikidata", "resolve qid from interwiki",
                         "stamp check_date", "drop stale pair", "consistent_qid"]),
    ("grokipedia_link", ["grokopedia", "grok="]),
    ("ill_category_to_link", ["{{ill}} from ill category", "ill_category_to_link"]),
    ("straggler_link_to_ill", ["convert straggler wikilink",
                               "straggler_link_to_ill"]),
    ("normalize_ill", ["normalize {{ill}}", "normalize ill"]),
    ("strip_html_comments", ["strip html comment", "strip_html_comments"]),
    ("strip_afc_templates", ["strip {{afc"]),
    ("strip_char_count_cats", ["strip char-count", "strip_char_count_cats"]),
    ("untranslated_japanese", ["untranslated japanese", "tag untranslated"]),
    ("remove_defaultsort", ["remove defaultsort", "remove_defaultsort"]),
    ("history_offload", ["history offload", "archive history",
                         "offloading history", "history cleanup",
                         "miraheze stability"]),
    ("categories_to_bottom", ["move categories to bottom",
                              "categories_to_bottom"]),
    ("duplicate_qids", ["duplicate qid", "duplicate_qids"]),
    ("deleted_qids_in_ill", ["deleted qid in {{ill}}", "deleted_qids_in_ill"]),
    ("interlang_consolidate", ["consolidate interlang", "interlang_consolidate"]),
    ("noinclude_wrap", ["noinclude wrap", "noinclude_wrap"]),
    ("shikinaisha_talk", ["shikinaisha talk", "shikinaisha_talk"]),
    ("normalize_category_page", ["normalize category page",
                                 "normalize_category_page"]),
    ("strip_self_categorization", ["strip self-categori", "strip_self"]),
    ("template_mainspace_usage", ["templates transcluded in mainspace",
                                  "template_mainspace_usage"]),
    ("remove_legacy_cat_templates", ["デフォルトソート",
                                     "remove_legacy_cat_templates"]),
    ("enwiki_wikidata_link", ["enwiki wikidata link",
                              "enwiki_wikidata_link"]),
    ("fix_double_redirects", ["fix double redirect", "fix_double_redirects"]),
    ("delete_unused_categories", ["unused categories", "delete_unused_categories"]),
    ("delete_orphaned_talk_pages", ["orphaned talk page", "delete_orphaned_talk_pages"]),
    ("delete_orphans", ["delete orphan (special:lonelypages)", "delete_orphans"]),
    ("triage_emmabot_categories", ["triage emmabot categories",
                                   "triage_emmabot_categories"]),
    ("create_wanted_categories", ["wanted categor", "create_wanted_categories"]),
    ("remove_crud_categories", ["remove crud categor", "remove_crud_categories",
                                 "crud category cleanup"]),
    # Cross-wiki category-mirror tagger (writes "tag [[Category:Independently
    # git synced pages]] on this miraheze wiki to mirror tagging on the
    # other"). Not an orchestrator op — a standalone script outside the
    # current orchestrator set.
    ("tag_independently_git_synced", ["tag [[category:independently git synced pages]]"]),
    ("reimport_from_enwiki", ["reimport from enwiki", "imported full"]),
]


_BOT_USERS = frozenset({"EmmaBot", "EmmaBot Sonnet"})

# HotCat is a gadget — humans use it to (un)categorise pages. The
# resulting edit summary embeds "using [[Help:Gadget-HotCat|HotCat]]".
_HOTCAT_MARKER = "using [[help:gadget-hotcat|hotcat]]"


def _attribute(user: str, comment: str) -> str:
    """Return the script_id whose pattern first matches the comment.

    Order of decisions:
      1. Non-bot user → ``human`` (with ``human (HotCat)`` when the
         HotCat gadget marker is present, since that's a distinctive
         category-edit signal worth tracking separately).
      2. Bot user with matching SCRIPT_PATTERNS rule → that script_id.
      3. Bot user with no matching rule → ``unknown``.

    The user check is up front so a SCRIPT_PATTERNS rule can't
    accidentally claim a human edit just because the human happened to
    quote a known keyword in their summary."""
    c = (comment or "").lower()
    if user and user not in _BOT_USERS:
        if _HOTCAT_MARKER in c:
            return "human (HotCat)"
        return "human"
    for script_id, patterns in SCRIPT_PATTERNS:
        for p in patterns:
            if p in c:
                return script_id
    return "unknown"


def _api(params: dict) -> dict:
    """One MediaWiki query call. Returns the parsed JSON body."""
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    resp = requests.get(
        WIKI_API,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def list_category_members(category: str) -> list[str]:
    """All page titles in ``[[Category:<category>]]``, mainspace
    only."""
    titles: list[str] = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmnamespace": "0",
        "cmlimit": "max",
    }
    while True:
        data = _api(params)
        for m in data.get("query", {}).get("categorymembers", []):
            t = m.get("title")
            if t:
                titles.append(t)
        if "continue" in data:
            params.update(data["continue"])
        else:
            break
    return titles


def fetch_revisions(title: str, limit: int) -> list[dict]:
    """Most-recent-first revisions for ``title``. Each rev dict has
    ``timestamp``, ``user``, ``comment`` keys (or empty strings)."""
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "timestamp|user|comment",
        "rvlimit": str(limit),
        "rvdir": "older",
    }
    data = _api(params)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return []
    revs = pages[0].get("revisions", []) or []
    return revs


_NON_CHURN_ATTRIB = frozenset({"unknown", "human", "human (HotCat)"})


def detect_alternation(scripts_in_order: list[str]) -> tuple[str, str, int] | None:
    """If the most-recent revisions show two scripts toggling, return
    the (script_a, script_b, toggle_count) for the longest such streak.
    Otherwise None.

    Definition: a 'toggle' is consecutive A→B→A→B where neither script
    is in ``_NON_CHURN_ATTRIB`` (unknown / human edits don't count as
    half of a bot-vs-bot churn pair). We count starting from the most-
    recent revision back until the pattern breaks.
    """
    if len(scripts_in_order) < 3:
        return None
    # walk newest-first
    a = scripts_in_order[0]
    b = scripts_in_order[1]
    if a == b or a in _NON_CHURN_ATTRIB or b in _NON_CHURN_ATTRIB:
        return None
    toggles = 2  # the first A,B already establishes 1 alternation
    expected = a
    for s in scripts_in_order[2:]:
        if s == expected:
            toggles += 1
            expected = b if expected == a else a
        else:
            break
    if toggles >= 3:
        # canonical-order the pair so (A,B) and (B,A) histogram as one
        pair = tuple(sorted([a, b]))
        return (pair[0], pair[1], toggles)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--rev-limit", type=int, default=REV_LIMIT)
    parser.add_argument("--category", default=CATEGORY)
    parser.add_argument("--output", default=OUTPUT_PATH)
    parser.add_argument("--seed", type=int, default=None,
                        help="optional random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    print(f"Listing [[Category:{args.category}]] members...")
    all_titles = list_category_members(args.category)
    print(f"  found {len(all_titles)} mainspace pages")

    if len(all_titles) > args.sample_size:
        sample = random.sample(all_titles, args.sample_size)
    else:
        sample = list(all_titles)
    sample.sort()

    print(f"Sampling {len(sample)} pages, pulling last "
          f"{args.rev_limit} revisions each...")

    per_page: list[tuple[str, list[dict], list[str]]] = []
    alternation_hits: list[tuple[str, str, str, int]] = []
    pair_histogram: collections.Counter = collections.Counter()
    script_total: collections.Counter = collections.Counter()

    for i, title in enumerate(sample, 1):
        revs = fetch_revisions(title, args.rev_limit)
        scripts = [_attribute(r.get("user", ""), r.get("comment", "")) for r in revs]
        per_page.append((title, revs, scripts))
        for s in scripts:
            script_total[s] += 1
        alt = detect_alternation(scripts)
        if alt:
            a, b, n = alt
            alternation_hits.append((title, a, b, n))
            pair_histogram[(a, b)] += 1
        print(f"  [{i}/{len(sample)}] {title}: {len(revs)} revs, "
              f"alternation={'yes' if alt else 'no'}")

    # Build markdown report
    out = []
    out.append("# Page-churn diagnostic — phase 1")
    out.append("")
    out.append(
        f"Generated by `shinto_miraheze/diagnose_page_churn.py`. "
        f"Sample size: {len(sample)} pages from "
        f"`[[Category:{args.category}]]` ({len(all_titles)} total). "
        f"Last {args.rev_limit} revisions per page."
    )
    out.append("")
    out.append("Re-run after wiki state changes; the script is read-only.")
    out.append("")
    out.append("## Alternation summary")
    out.append("")
    if not alternation_hits:
        out.append(
            "**No two-script alternation streaks (≥3 toggles) detected** "
            f"in the sample of {len(sample)} pages."
        )
    else:
        out.append(
            f"{len(alternation_hits)} of {len(sample)} sampled pages "
            "show a two-script alternation streak (≥3 most-recent "
            "consecutive A→B→A→B revisions where neither side is unknown)."
        )
        out.append("")
        out.append("### Script-pair frequency")
        out.append("")
        for (a, b), n in pair_histogram.most_common():
            out.append(f"* `{a}` ↔ `{b}`: **{n} page(s)**")
    out.append("")
    out.append("## Per-page edit traces")
    out.append("")
    out.append("(Most-recent revision first. `script=…` is the keyword-")
    out.append("matched attribution from the edit summary; `unknown` means")
    out.append("no rule in `SCRIPT_PATTERNS` matched.)")
    out.append("")
    for title, revs, scripts in per_page:
        alt = detect_alternation(scripts)
        marker = ""
        if alt:
            a, b, n = alt
            marker = f"  — **ALTERNATION** `{a}` ↔ `{b}` × {n} toggles"
        out.append(f"### {title}{marker}")
        out.append("")
        out.append("```")
        for rev, script in zip(revs, scripts):
            ts = rev.get("timestamp", "")
            user = rev.get("user", "")
            comment = (rev.get("comment", "") or "").replace("\n", " ")
            if len(comment) > 110:
                comment = comment[:107] + "..."
            out.append(f"{ts}  user={user:14s}  script={script:30s}  "
                       f"{comment}")
        out.append("```")
        out.append("")
    out.append("## Script-attribution counts across sample")
    out.append("")
    out.append("(How many revisions were attributed to each script. A")
    out.append("high `unknown` count means `SCRIPT_PATTERNS` needs more")
    out.append("rules — improving attribution is a follow-up.)")
    out.append("")
    for s, n in script_total.most_common():
        out.append(f"* `{s}`: {n}")
    out.append("")

    text = "\n".join(out) + "\n"
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"\nWrote {args.output} ({len(text)} chars)")
    print(f"Alternation pages: {len(alternation_hits)} / {len(sample)}")
    print(f"Distinct pairs:    {len(pair_histogram)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
