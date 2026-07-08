#!/usr/bin/env python3
"""
remote_queue.py
================
Builds a queue of agentic-work items for a remote Claude cron to
consume. Each item is a ``(file, instruction)`` pair — the remote
worker reads the file, applies the instruction, and commits.

This is the bridge between the repo's standing backlog (the bulk
LLM-grunge items in ``queue.md``) and an autonomous loop that can
finally let the wiki run without the human in the chain. The goal,
per the queue plan, is for the wiki to reach a "decent state for the
archives" without ongoing manual attention — even if the wiki itself
stops being hosted long-term.

Sources and how they map to instructions:

  duplicated_content/*.wiki
      Reorganize-to-remove-duplication. When the page is done, the
      worker drops [[Category:Pages with duplicated content]] from
      the file — the next sync push+deletes from the repo.
      ~353 items (the big chunk).

  need_translation/*.wiki
      Translate Japanese prose to English. When the page is done,
      the worker drops [[Category:Need translation]] from the file
      — the sync push+deletes from the repo. ~121 items.

  fandom_unique/*.wiki
      Replace miraheze-only templates ({{ill}}, {{wikidata link}},
      {{translated page}}, {{jalink}}) with plain wikilinks and
      fandom-compatible alternatives so the page renders on
      shinto.fandom.com. ~600 items.

  miraheze_unique/*.wiki (shrine-disambig subset)
      Strip the old human-curated lists inherited from the
      source-of-import pages and leave only a generic intro +
      the auto-generated `== Shrines with this name ==` block
      (delimited by the BEGIN/END markers). Detection: pages
      containing the auto-generated-block marker. ~115 items.

  miraheze_unique/*.wiki (shrine-disambig, no auto-gen block yet)
      Split into two sub-buckets by whether the regex kanji extractor
      can recover the kanji form:
        * kanji_known: the kanji is embedded directly in the instruction
          so the worker can SPARQL right away.
        * kanji_unknown: the worker has to read the page to find a
          kanji form (might be in an infobox parameter, an interwiki
          ``[[ja:...]]`` link, a non-standard ``{{nihongo}}`` call,
          etc.) or accept that the page has no recoverable kanji.

Japanese-titled pages are excluded — those moves are intentional
manual work per the queue plan.

Output: ``remote_queue.json`` at the repo root. The remote consumer
reads this; the queue is uncapped (1000+ items expected) — the
consumer paces itself, and the next nightly rebuild reflects the
new repo state regardless.
"""

import argparse
import datetime
import io
import json
import os
import random
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent
QUEUE_PATH = REPO_ROOT / "remote_queue.json"
SCHEMA_VERSION = 1


# ─── instruction templates ─────────────────────────────────

DUPLICATED_CONTENT_INSTRUCTION = (
    "This page is tagged [[Category:Pages with duplicated content]] because "
    "the ENTIRE ARTICLE BODY appears more than once on the page — a "
    "macro-scale, paragraph-level duplication where the whole article (or "
    "most of it) was copied in two or more times. This is NOT about duplicated "
    "infobox parameters, repeated interwiki/`[[ja:...]]` lines, or other "
    "small copy-edits. Do NOT dedupe infobox parameters or template lines — "
    "that is the wrong task and must not be done here. Leave any duplicated "
    "parameters exactly as they are: a separate deterministic script removes "
    "those programmatically, and the duplication itself often carries signal "
    "(e.g. conflicting values worth preserving), so editing them by hand here "
    "only destroys information.\n\n"
    "What it actually looks like: the same `==` sections (History, Overview, "
    "Deities, Access, References, Bibliography, etc.) appear twice or more. "
    "The second/extra copy is OFTEN introduced by an explicit marker heading "
    "such as `== Accidentally Overwritten Content ==`, `== merged content ==`, "
    "`== Merged second translation ==`, `== End Japanese ==`, or "
    "`== Japanese Wikipedia content ==`. Sometimes there is no marker and the "
    "body simply repeats. The duplicate copies are usually near-identical but "
    "their wording or details may deviate slightly.\n\n"
    "Your job is to MERGE the duplicate copies into ONE coherent article:\n"
    "  * Collapse each repeated section into a single section.\n"
    "  * Where the copies deviate, RECONCILE them — keep the union of facts, "
    "references, and detail. Do not drop information that exists in only one "
    "copy. Do not blindly delete a whole copy without checking the other for "
    "unique content first.\n"
    "  * Remove the redundant marker headings (`== Accidentally Overwritten "
    "Content ==`, `== merged content ==`, etc.) once their content is folded "
    "in.\n"
    "  * Preserve `{{ill|...}}`, `{{jalink|...}}`, `{{nihongo|...}}` calls and "
    "`<ref>...</ref>` blocks verbatim — link wrappers and citations, not prose "
    "to rewrite.\n"
    "  * Keep the infobox, bottom-of-page templates, and categories intact.\n\n"
    "Some pages also carry a Wikidata-autogenerated property dump — a block "
    "headed `== merged content ==` or a run of property sections like "
    "`== instance of (P31) ==`, `== part of (P361) ==`, "
    "`== coordinate location (P625) ==`, etc. Treat it as another copy to fold "
    "in: convert any fact NOT already present in the infobox, lede, or prose "
    "into normal prose (e.g. an `== Identifiers ==` or `== Other names ==` "
    "section for name-in-kana, street address, corporate/registry numbers, "
    "external IDs, ordinal-in-list with neighbors, etc.), and DROP the rows that "
    "merely restate the infobox/coordinates/image/country/deity. Do not keep the "
    "raw `== P31 ==`-style property headings.\n\n"
    "If one of the duplicate copies is raw untranslated Japanese (e.g. under "
    "`== Japanese Wikipedia content ==`), that copy is tracked separately "
    "under [[Category:Need translation]] — leave Japanese prose alone for the "
    "translation job rather than merging it into the English body.\n\n"
    "When the page reads as a single, non-duplicated article, remove "
    "`[[Category:Pages with duplicated content]]` from the file — that is what "
    "marks it done. The next CI sync will push the merged version to the wiki "
    "and delete the local file. Only remove the category once the macro-scale "
    "duplication is genuinely gone."
)

NEED_TRANSLATION_INSTRUCTION = (
    "Translate the Japanese-language content in this page to English. "
    "Many of these are kokuzo (国造) articles or shrine prose imported from "
    "ja.wikipedia. Preserve all `{{ill|...}}`, `{{jalink|...}}`, and "
    "`{{nihongo|...}}` template calls verbatim — those are link wrappers, "
    "not prose to translate. Preserve `<ref>...</ref>` blocks verbatim. "
    "Translate only the prose between templates and refs. When the page no "
    "longer contains CJK characters outside template parameters and refs, "
    "remove `[[Category:Need translation]]` from the file — the next CI sync "
    "will push the translation to the wiki and delete the local file. "
    "WARNING: this sync is destructive — removing the category deletes the "
    "file from the repo, so only drop it when translation is genuinely done."
)

CATEGORY_TRANSLATION_INSTRUCTION = (
    "This file is a WORK ITEM for translating a Japanese-named wiki category to "
    "its canonical English name — the residual that the deterministic resolver "
    "(generate_category_translation_moves.py) could NOT confidently name, routed "
    "here for agentic research. The file has a `<!-- SOURCE: Category:... -->` "
    "marker (the Japanese category), an empty `<!-- TRANSLATED: -->` marker for "
    "your answer, a sample of the category's members, and the category page's own "
    "wikitext.\n\n"
    "Your job: determine the correct English `Category:` title and write it into "
    "the TRANSLATED marker, e.g. `<!-- TRANSLATED: Category:Shinto shrines in "
    "Kyoto -->`. RESEARCH it — do not transliterate or guess blindly:\n"
    "  * Read the member sample to see what the category actually contains.\n"
    "  * Check the category wikitext for a `{{wikidata link|Q...}}` or an "
    "interwiki `[[ja:...]]`/`[[Category:ja:...]]` hint — if a Wikidata "
    "Wikimedia-category item exists, its enwiki category sitelink is authoritative.\n"
    "  * Otherwise map to the REAL enwiki category-naming convention for that topic "
    "(e.g. `Xの神社` → `Shinto shrines in X`, `Xの寺院` → `Buddhist temples in X`, "
    "`Xの重要文化財` → `Important Cultural Properties of X`, `X郡` → the district's "
    "English article title, `<sect>の寺院` → `<English sect name> temples`). Resolve "
    "place names authoritatively via the jawiki article's enwiki sitelink, not by "
    "romanizing.\n"
    "  * The destination MUST start with `Category:` and differ from the source.\n\n"
    "When you have written the TRANSLATED marker, you are DONE with this file — a "
    "deterministic collector (collect_category_translations.py) folds it into "
    "category_moves.csv and deletes it; the monthly move_categories step performs "
    "the actual page move. If the category is GENUINELY untranslatable (nonsense, "
    "no discernible meaning even after research), leave TRANSLATED empty and add a "
    "line `<!-- SKIP: <short reason> -->` so a human can look — never invent a name."
)

RONSHA_RANKING_INSTRUCTION = (
    "This file is a WORK ITEM ranking the candidates of a Shikinai Ronsha (a "
    "disputed Engishiki shrine identity) on Wikidata. The `<!-- RONSHA: ... -->` "
    "marker names the item; the `== Candidates ==` list holds its P460 "
    "said-to-be-the-same-as candidates, currently all unranked. RESEARCH each "
    "candidate (jawiki article, Kokugakuin database, location vs the Engishiki "
    "province/district, name continuity) and decide which single candidate is "
    "the LIKELIEST true shrine. Fill the `<!-- ANSWER: -->` marker with exactly "
    "one of `LIKELY: <candidate QID>` or `UNDECIDABLE: <why>` as the TASK "
    "comment describes. Do NOT edit Wikidata yourself - a collector turns "
    "answers into P1352 qualifier QuickStatements later (1 = likely, 0 = the "
    "rest). When ANSWER is filled you are done with the file."
)

LABEL_TYPO_REVIEW_INSTRUCTION = (
    "This file is a WORK ITEM reviewing a suspected Wikidata romaji typo. The "
    "shrine's English label letters diverge from its romanized kana reading "
    "(P1814) — see the `<!-- JA / KANA / EN_LABEL / KANA_ROMANIZED -->` marker. "
    "The WRONG SIDE VARIES: sometimes the label is misspelled (e.g. Saruka for "
    "さるが=Saruga), sometimes the P1814 kana is archaic/wrong (historical kana "
    "ちりふ for Chiryū; a kana missing a syllable), sometimes the label just "
    "carries a legit place prefix (Kurume Suitengū). RESEARCH the correct reading "
    "(jawiki article, official shrine site) and fill the `<!-- ANSWER: -->` marker "
    "with exactly one of `LABEL_TYPO: <corrected label>`, `KANA_ISSUE: <note>`, "
    "`PREFIX_OK: <note>`, or `OTHER: <explanation>` as the TASK comment in the "
    "file describes. Do NOT edit Wikidata yourself — a collector turns answers "
    "into QuickStatements later. When ANSWER is filled you are done with the file."
)

MIRAHEZE_SHRINE_DISAMBIG_NO_AUTOGEN_KANJI_KNOWN_TEMPLATE = (
    "This shrine disambiguation page (tagged [[Category:Shrine "
    "disambiguations]]) doesn't have the auto-generated `== Shrines "
    "with this name ==` block yet, but the kanji form is recoverable "
    "from the page: {kanji_repr}. Most likely the regular "
    "`generate_shrine_disambig_lists.py` sweep just hasn't visited "
    "this page yet (it's incremental and there's a backlog), or its "
    "SPARQL exact-label match returned zero results. Fix it directly: "
    "SPARQL Wikidata for items that are subclass-of Q845945 (Shinto "
    "shrine) carrying that kanji as an `ja` rdfs:label or skos:altLabel "
    "(broaden with prefix match if exact returns nothing), and write "
    "the section in the same format as other shrine-disambig pages. "
    "Wrap it in the standard `<!-- BEGIN: auto-generated Wikidata "
    "shrine list -->` / `<!-- END: auto-generated Wikidata shrine list "
    "-->` markers so the regular script keeps maintaining it on future "
    "sweeps. If SPARQL returns nothing meaningful even with the broader "
    "query, leave the page as-is."
)

MIRAHEZE_SHRINE_DISAMBIG_NO_AUTOGEN_KANJI_UNKNOWN_INSTRUCTION = (
    "This shrine disambiguation page (tagged [[Category:Shrine "
    "disambiguations]]) doesn't have the auto-generated `== Shrines "
    "with this name ==` block, and the regex kanji extractor couldn't "
    "recover a kanji form. Read the page carefully — the kanji might "
    "be in a non-standard place (an infobox parameter, an inline "
    "mention, a comment, a `{{nihongo|...}}` call missing the standard "
    "shape, or an interwiki link like `[[ja:KANJI]]`). If you find it, "
    "either (a) add a `{{Nihongo|EnglishName|KANJI|romaji}}` template "
    "near the top so the regular script can pick it up via its "
    "fallback paths, or (b) write the section directly and wrap it in "
    "the standard `<!-- BEGIN: auto-generated Wikidata shrine list -->` "
    "/ `<!-- END: auto-generated Wikidata shrine list -->` markers. If "
    "the page genuinely has no recoverable kanji (this disambiguation "
    "is purely English-context, or the underlying Japanese form is "
    "ambiguous), leave the page as-is — not every shrine disambig has "
    "a clean kanji equivalent."
)

MIRAHEZE_SHRINE_DISAMBIG_INSTRUCTION = (
    "This is a shrine disambiguation page (it contains the "
    "`<!-- BEGIN: auto-generated Wikidata shrine list -->` marker "
    "block). The page currently has BOTH the auto-generated list AND "
    "the old machine-translated curated content from the source-of-"
    "import page. The two coexisting is confusing — the old curated "
    "lists are typically section-headed by reading variant (`== "
    "Shōshoi ==`, `== Yamajinja ==`, `== Yama no Kamisha ==`, etc.) "
    "with bullets that say `Located in [place]` without QIDs or "
    "proper wikilinks to actual shrine pages.\n\n"
    "What to keep and what to drop:\n"
    "  * KEEP: the lede sentence(s) — the opening `'''Name''' (kanji) "
    "is a [[Shinto shrine]]…` line, plus any short prose that gives "
    "the name's meaning or context. Small amounts of name-specific "
    "content are fine.\n"
    "  * KEEP: a `{{disambiguation}}` template (add one if it's not "
    "already there).\n"
    "  * KEEP: the auto-generated block, in full, between its "
    "`<!-- BEGIN: ... -->` / `<!-- END: ... -->` markers — that's the "
    "actual disambig content.\n"
    "  * KEEP: bottom-of-page templates (`{{translated page|...}}`, "
    "`{{wikidata link|...}}`) and categories.\n"
    "  * DROP: every `==`-headed section above the auto-gen block "
    "that lists old curated entries (`== Shōshoi ==`, `== Yamajinja "
    "==`, named-variant sections, `== See Also ==` sections that "
    "just restate the auto-gen content, etc.).\n"
    "  * DROP: stray `{{ill|Disambiguation|...}}` calls that try to "
    "link to the Wikipedia disambiguation policy page — the proper "
    "`{{disambiguation}}` template above covers this.\n"
    "  * DROP: trailing summary sentences that comment on the curated "
    "lists (`In the Tōkai region, most of these are small shrines…`).\n\n"
    "Worked example — Mountain Shrine — see miraheze_unique/Mountain "
    "Shrine.wiki at HEAD. Before: ~70 lines of `* Located in …` "
    "bullets in four sections (Shōshoi / Yamajinja / Yama no Kamisha "
    "/ Yamagamisha) plus a broken `{{ill|Disambiguation|…}}` line, "
    "ABOVE the auto-gen block. After: 3-line lede, `{{disambiguation}}` "
    "template, the auto-gen block intact, footer templates and "
    "categories. Match that shape.\n\n"
    "Process the miraheze_unique/ file (the canonical source under "
    "the dual-sync model); the next sync will push the cleanup to "
    "both wikis. Do not edit the fandom_unique/ copy."
)

FANDOM_UNIQUE_INSTRUCTION = (
    "Rewrite this page so it renders correctly on shinto.fandom.com. The "
    "miraheze-only templates that don't exist on fandom: `{{ill|...}}`, "
    "`{{wikidata link|...}}`, `{{translated page|...}}`, `{{jalink|...}}`, "
    "and the various `{{...Faith|qq=}}` navboxes that depend on miraheze "
    "modules. Convert `{{ill|TITLE|...lang_codes...|1=DISPLAY}}` and "
    "`{{ill|TITLE|...|lt=DISPLAY|...}}` to plain `[[TITLE|DISPLAY]]` "
    "wikilinks (or `[[TITLE]]` when there's no display-text override). "
    "Drop `{{wikidata link|...}}` and `{{translated page|...}}` entirely — "
    "their content doesn't carry meaning on fandom. Drop "
    "[[Category:Pages with interwikis with duplicate languages]] and any "
    "other miraheze-only maintenance categories. Keep the article body and "
    "standard categories. Don't touch the miraheze_unique/ copy — that's a "
    "separate file under the dual-sync model."
)


# ─── queue builder ─────────────────────────────────────────


def _build_section(
    dir_name: str,
    instruction: str,
    *,
    filter_fn=None,
) -> list[dict]:
    items: list[dict] = []
    directory = REPO_ROOT / dir_name
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("*.wiki")):
        if filter_fn is not None and not filter_fn(path):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        items.append(
            {
                "id": rel,
                "file": rel,
                "category": dir_name,
                "instruction": instruction,
            }
        )
    return items


_DUP_CAT_RE = re.compile(
    r'\[\[\s*Category\s*:\s*Pages with duplicated content\s*\]\]', re.IGNORECASE
)


def _still_has_dup_category(path: Path) -> bool:
    """Filter for duplicated_content/: only queue files that STILL carry
    [[Category:Pages with duplicated content]].

    Statefulness for this pipeline is purely file-presence + category: a page
    needs work iff its file exists AND still has the category. Once the
    consumer removes the category (page merged), the file is fixed-but-pending-
    sync; excluding it here stops the consumer from re-doing a page that's
    already been merged but not yet pushed+deleted by sync_duplicated_content.
    """
    try:
        return bool(_DUP_CAT_RE.search(path.read_text(encoding="utf-8")))
    except OSError:
        return False


def _is_disambig_or_english_titled(path: Path) -> bool:
    """Filter for fandom_unique/: skip Japanese-titled pages.

    Pages whose stem is pure CJK aren't in scope for the autonomous
    template-fixup pass; the user moves those manually.
    """
    stem = path.stem
    if not stem:
        return False
    cjk_chars = sum(
        1
        for ch in stem
        if "぀" <= ch <= "ゟ"
        or "゠" <= ch <= "ヿ"
        or "㐀" <= ch <= "鿿"
    )
    return cjk_chars <= max(1, len(stem) // 4)


# Marker that ``generate_shrine_disambig_lists.py`` writes around its
# auto-generated bullet block. Used to identify shrine-disambig pages
# in miraheze_unique/ without resorting to filename heuristics.
_SHRINE_DISAMBIG_MARKER = "<!-- BEGIN: auto-generated Wikidata shrine list -->"
_SHRINE_DISAMBIG_CAT_RE = re.compile(
    r"\[\[\s*Category\s*:\s*[Ss]hrine\s+disambiguations?\s*(?:\|[^\]]*)?\]\]"
)


def _is_shrine_disambig(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return _SHRINE_DISAMBIG_MARKER in text


def _is_shrine_disambig_no_autogen(path: Path) -> bool:
    """Tagged as a shrine disambiguation but missing the auto-gen block."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    if _SHRINE_DISAMBIG_MARKER in text:
        return False
    return bool(_SHRINE_DISAMBIG_CAT_RE.search(text))


# Kanji extraction logic — mirrors
# ``shinto_miraheze/generate_shrine_disambig_lists.py``'s
# ``extract_kanji_names``. We inline rather than import because the
# script wraps ``sys.stdout`` at module load and that re-wrap detaches
# our own ``io.TextIOWrapper``, closing stdout for any later prints.
# The regex set is small and has been stable; if the script's
# extractor ever grows substantially, sync this copy.
_LEDE_KANJI_RE = re.compile(
    r"^'''([^']+)'''(?:\s+or\s+'''[^']+''')*\s*[（(]([^)）]+)[)）]",
    re.M,
)
_INLINE_BOLD_KANJI_RE = re.compile(r"'''([一-鿿぀-ゟ゠-ヿ々〆〇]+)'''")
_TRANSLATED_PAGE_JA_RE = re.compile(r"\{\{translated page\|ja\|([^|}]+)")
_WIKIDATA_LINK_JA_RE = re.compile(r"\{\{wikidata link\|[^{}]*?\|ja\|([^|}]+)")
_NIHONGO_RE = re.compile(r"\{\{[Nn]ihongo\|[^|}]+\|([^|}]+)")
_MIN_KANJI_LEN = 3


def _add_candidate(out: list[str], seen: set, s: str, *, min_len: int) -> None:
    s = s.strip()
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    if len(s) < min_len:
        return
    cjk_count = sum(
        1 for c in s if "一" <= c <= "鿿" or "぀" <= c <= "ヿ"
    )
    if cjk_count < min_len:
        return
    kanji_count = sum(1 for c in s if "一" <= c <= "鿿" or c in "々〆〇")
    if kanji_count < min(2, min_len):
        return
    if any(c in s for c in "[]{}|=<>"):
        return
    if s in seen:
        return
    seen.add(s)
    out.append(s)


def _extract_kanji_for_path(path: Path) -> list[str]:
    """Return CJK shrine-name candidates extracted from the page text,
    mirroring ``generate_shrine_disambig_lists.extract_kanji_names``."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    seen: set[str] = set()
    out: list[str] = []

    m = _LEDE_KANJI_RE.search(text)
    if m:
        for tok in re.split(r"[、,;]|\s+or\s+", m.group(2)):
            _add_candidate(out, seen, tok, min_len=_MIN_KANJI_LEN)

    for m in _INLINE_BOLD_KANJI_RE.finditer(text):
        _add_candidate(out, seen, m.group(1), min_len=_MIN_KANJI_LEN)

    # Fallback paths — same as the script, only run if the primary
    # paths produced nothing.
    if not out:
        for m in _TRANSLATED_PAGE_JA_RE.finditer(text):
            _add_candidate(out, seen, m.group(1), min_len=2)
    if not out:
        for m in _WIKIDATA_LINK_JA_RE.finditer(text):
            _add_candidate(out, seen, m.group(1), min_len=2)
    if not out:
        for m in _NIHONGO_RE.finditer(text):
            _add_candidate(out, seen, m.group(1), min_len=2)

    return out


def _build_no_autogen_disambig_items() -> list[dict]:
    """Walk miraheze_unique/ shrine-disambig pages without the auto-gen
    block and split them into kanji-known vs kanji-unknown sub-items.

    Kanji-known: the kanji is embedded directly in the per-item
    instruction so the remote worker can SPARQL right away without
    re-running the extractor.
    Kanji-unknown: the worker has to read the page and decide whether
    a kanji form exists, or leave it alone.
    """
    items: list[dict] = []
    directory = REPO_ROOT / "miraheze_unique"
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("*.wiki")):
        if not _is_shrine_disambig_no_autogen(path):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        kanji = _extract_kanji_for_path(path)
        if kanji:
            kanji_repr = ", ".join(f"`{k}`" for k in kanji)
            instruction = (
                MIRAHEZE_SHRINE_DISAMBIG_NO_AUTOGEN_KANJI_KNOWN_TEMPLATE
                .format(kanji_repr=kanji_repr)
            )
            items.append(
                {
                    "id": rel,
                    "file": rel,
                    "category": "miraheze_unique",
                    "subcategory": "shrine_disambig_no_autogen_kanji_known",
                    "kanji": kanji,
                    "instruction": instruction,
                }
            )
        else:
            items.append(
                {
                    "id": rel,
                    "file": rel,
                    "category": "miraheze_unique",
                    "subcategory": "shrine_disambig_no_autogen_kanji_unknown",
                    "instruction": (
                        MIRAHEZE_SHRINE_DISAMBIG_NO_AUTOGEN_KANJI_UNKNOWN_INSTRUCTION
                    ),
                }
            )
    return items


def build_queue() -> list[dict]:
    items: list[dict] = []
    items.extend(
        _build_section(
            "duplicated_content",
            DUPLICATED_CONTENT_INSTRUCTION,
            filter_fn=_still_has_dup_category,
        )
    )
    items.extend(_build_section("need_translation", NEED_TRANSLATION_INSTRUCTION))
    items.extend(
        _build_section(
            "fandom_unique",
            FANDOM_UNIQUE_INSTRUCTION,
            filter_fn=_is_disambig_or_english_titled,
        )
    )
    items.extend(
        _build_section(
            "miraheze_unique",
            MIRAHEZE_SHRINE_DISAMBIG_INSTRUCTION,
            filter_fn=_is_shrine_disambig,
        )
    )
    items.extend(_build_no_autogen_disambig_items())
    # Queue item 5: agentic RAG the category-translation residual. Each work-file
    # is a Japanese category needing an English name (see build_category_
    # translation_queue.py); the worker fills the TRANSLATED marker and
    # collect_category_translations.py folds answers into category_moves.csv.
    items.extend(_build_section("category_translation", CATEGORY_TRANSLATION_INSTRUCTION))
    # Queue #8: review the 161 kana-vs-label romaji-typo candidates (see
    # build_label_typo_review_queue.py + docs/kana_label_mismatch_audit_2026-07.md);
    # the worker researches which side is wrong and fills the ANSWER marker.
    items.extend(_build_section("label_typo_review", LABEL_TYPO_REVIEW_INSTRUCTION))
    items.extend(_build_section("ronsha_ranking_review", RONSHA_RANKING_INSTRUCTION))
    # Shuffle so the consumer picks pages in random order. With no cursor-based
    # statefulness (work is gated purely on file-presence + category), random
    # order keeps the consumer from repeatedly hitting the same early pages —
    # in particular ones already merged but not yet pushed+deleted by sync.
    random.shuffle(items)
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output",
        default=str(QUEUE_PATH),
        help="path to write the queue JSON (default: remote_queue.json at repo root)",
    )
    args = ap.parse_args()

    items = build_queue()
    queue = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "item_count": len(items),
        "items": items,
    }

    out_path = Path(args.output)
    out_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Wrote {out_path.relative_to(REPO_ROOT) if out_path.is_absolute() else out_path} "
        f"with {len(items)} items "
        f"(duplicated_content + need_translation + fandom_unique [non-CJK titles])."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
