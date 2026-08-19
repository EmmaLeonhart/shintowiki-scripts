#!/usr/bin/env python3
"""
generate_shrine_disambig_lists.py
==================================
Per the leading instruction comment on ~165 shrine pages in
git_synced/, this script grabs every shrine on Wikidata sharing the
page's Japanese name and renders a bullet list. The author writes it
as: "we essentially link to things on wikidata, which is like
``{{ill|ENGLISH LABEL (QID)|lt=ENGLISH LABEL|qid=QID}}``" with one
bullet per match.

Approach:
  * For each git_synced/*.wiki whose first content line starts with
    "<!--I am adding this comment" (the shrine-SPARQL instruction
    marker), extract the Japanese kanji name(s) from the page —
    primarily from the leading prose line ``'''<Title>''' (<kanji>)``
    and any inline ``'''<kanji>'''`` bolds that look like shrine
    name variants.
  * SPARQL Wikidata for items that are subclass-of Shinto shrine
    (Q845945) and carry an exact ja label match for each kanji name.
    Exact-match was chosen because STRSTARTS over the shrine subclass
    tree timed out at >60s; the rare disambiguator-suffixed labels
    like ``隼神社 (京都市)`` will be missed on this pass but caught later
    if we expand to UNION over altLabels.
  * Render bullets as
    ``* {{ill|<EN label> (<QID>)|lt=<EN label>|qid=<QID>}} - <loc>``
    where <EN label> falls back to the ja label when no en label
    exists on Wikidata.
  * Insert/replace a marked block in the page:
        <!-- BEGIN: auto-generated Wikidata shrine list -->
        == Shrines on Wikidata with this name ==
        ...bullets...
        <!-- END: auto-generated Wikidata shrine list -->
    Re-running overwrites the block, so the section stays in sync with
    Wikidata as new items get added — the human-curated lists above
    are untouched.

Edits go to local git_synced/ files only; sync_git_synced_pages.py
pushes them to the wiki on the next cycle. No direct shintowiki API
hits from this script.

THROTTLE: 2.5s between SPARQL queries — same convention as wiki
edits per CLAUDE.md, and well below WDQS's quota. Each page issues
N queries where N = number of distinct kanji names on that page
(usually 1, sometimes ~10 for multi-name shrines like Ebisu).

429 policy: any HTTP 429 from Wikidata terminates the script with
clean exit (status 0); next run picks up where we left off via the
state file.

Standard flags: --apply (default dry-run), --max-edits, --run-tag.
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
# Shrine disambig pages live in BOTH miraheze_unique/ and fandom_unique/
# under the dual-sync model (migrated out of git_synced/ on 2026-05-10).
# We walk miraheze_unique/ to find candidates (canonical source of truth
# for membership), and write the auto-generated block to BOTH directories
# so each per-wiki sync picks up the change on its next cycle.
MIRAHEZE_UNIQUE_DIR = os.path.join(REPO_ROOT, "miraheze_unique")
FANDOM_UNIQUE_DIR = os.path.join(REPO_ROOT, "fandom_unique")
STATE_FILE = os.path.join(SCRIPT_DIR, "generate_shrine_disambig_lists.state")
ERROR_LOG = os.path.join(SCRIPT_DIR, "generate_shrine_disambig_lists.errors")

THROTTLE = 2.5  # seconds between SPARQL queries
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

# Was a module-level hardcoded "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) ..."
# literal shadowing the canonical constant. Two problems: it pinned a version that is now three
# releases stale, and the only endpoint this file talks to is query.wikidata.org, so it was
# sending the WIKI-SIDE persona to Wikidata -- the linkage the two agents exist to prevent.
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT as USER_AGENT
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Marker for the auto-generated section. Used both to find the block
# on re-runs (so we can replace it) and to detect that we already
# inserted something on a previous pass.
BEGIN_MARKER = "<!-- BEGIN: auto-generated Wikidata shrine list -->"
END_MARKER = "<!-- END: auto-generated Wikidata shrine list -->"
SECTION_HEADER = "== Shrines with this name =="

# Marker line inserted at the top of each shrine disambig page during
# the dual-sync migration (commit ?). Pages carrying this marker are
# the SPARQL refresh's targets — much narrower than the old
# "<!--I am adding this comment..." detection which only matched the
# legacy git_synced/ instruction comment that's no longer present
# after migration.
INSTRUCTION_PREFIX = "<!-- shrine-disambig-page: refresh wikidata list -->"

# Skip pages whose kanji name is shorter than this — single-character
# CJK names like 国 produce thousands of SPARQL hits, mostly noise.
# 3 chars is the minimum for a standard "<name>神社" or "<name>大神宮"
# pattern.
MIN_KANJI_LEN = 3

CJK_RE = re.compile(r"[一-鿿々〆〇ぁ-ゖァ-ヺ]+")
QID_RE = re.compile(r"^Q\d+$")

_retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
)
_http = requests.Session()
_http.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
_http.mount("http://", HTTPAdapter(max_retries=_retry_strategy))


class RateLimitError(Exception):
    pass


def log_error(message: str, *, fatal: bool = False):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    sev = "FATAL" if fatal else "ERROR"
    line = f"[{ts}] [{sev}] generate_shrine_disambig_lists: {message}\n"
    print(f"   ! {sev}: {message}", file=sys.stderr)
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def checked_post(url: str, **kwargs):
    resp = _http.post(url, **kwargs)
    if resp.status_code == 429:
        log_error(f"429 Too Many Requests from {resp.url} — terminating", fatal=True)
        raise RateLimitError(f"429: {resp.url}")
    return resp


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"processed": []}
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ─── KANJI EXTRACTION ─────────────────────────────────────────────

# Match leading bold + parenthetical, allowing optional intermediate
# `or '''<Alt Title>'''` chains (pages like Fuji Sengen Shrine list two
# romanized variants before the kanji paren) and accepting both
# half-width `(` `)` and full-width `（` `）` (e.g. Himuro Shrines
# uses the full-width form).
LEDE_KANJI_RE = re.compile(
    r"^'''([^']+)'''(?:\s+or\s+'''[^']+''')*\s*[（(]([^)）]+)[)）]",
    re.M,
)
# Match `'''...'''` where the body is *only* CJK characters
# (kanji + hiragana + katakana + a few common iteration marks). The
# earlier non-greedy `[^']*?[一-鿿]+[^']*?` form bridged across bolds
# — its first match consumed the entire span between two distant
# `'''` delimiters because no single-quote characters appeared in
# between, eating the first variant kanji in the process.
INLINE_BOLD_KANJI_RE = re.compile(r"'''([一-鿿぀-ゟ゠-ヿ々〆〇]+)'''")
WIKIDATA_LINK_QID_RE = re.compile(r"\{\{wikidata link\|(Q\d+)")


def extract_kanji_names(text: str) -> list[str]:
    """Pull every distinct CJK shrine-name candidate out of a page.

    Strategy:
      1. Lede pattern: `'''<Title>''' (<kanji>)` — most reliable;
         the kanji in the immediate parenthetical is almost always
         the page's primary Japanese name.
      2. Inline bold kanji: `'''<kanji>'''` patterns elsewhere in the
         body — catches multi-name disambig pages (e.g., Ebisu lists
         8 variant kanji forms as bold inline strings).

    Deduplicated, ordered, filtered to len >= MIN_KANJI_LEN.
    """
    seen = set()
    out = []

    def add(s: str, *, min_len: int = MIN_KANJI_LEN):
        """Validate and accept a candidate name.

        `min_len` defaults to MIN_KANJI_LEN (3) — the standard
        `<name>神社` shape needs at least 3 chars. Fallback paths
        (template-driven extraction) pass min_len=2 so that 2-kanji
        explicit mentions like `明治` (Meiji era) survive — at that
        point the kanji has been deliberately surfaced by the page,
        not heuristically picked up from the prose.
        """
        s = s.strip()
        # Strip leading/trailing parentheticals and whitespace
        s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
        if len(s) < min_len:
            return
        # Must be majority CJK
        cjk_count = sum(1 for c in s if "一" <= c <= "鿿" or "぀" <= c <= "ヿ")
        if cjk_count < min_len:
            return
        # Must contain at least one kanji ideograph. Names that are
        # all hiragana/katakana (e.g. `いつくしまじんじゃ`,
        # `いづものいわいのかむやしろ`) are romanized readings of the
        # canonical kanji form — they almost never appear as primary
        # rdfs:label values on Wikidata shrine items, so SPARQL would
        # return 0 hits. Filtering them out avoids burning a query.
        kanji_count = sum(1 for c in s if "一" <= c <= "鿿" or c in "々〆〇")
        if kanji_count < min(2, min_len):
            return
        # Reject if it contains characters that don't belong in a shrine name
        if any(c in s for c in "[]{}|=<>"):
            return
        if s in seen:
            return
        seen.add(s)
        out.append(s)

    # 1) Lede kanji
    m = LEDE_KANJI_RE.search(text)
    if m:
        # The parenthetical may contain comma- or `or`-separated names
        # like `(隼神社、はやぶさじんじゃ)` or `(五條天神社 or 五条天神社)`.
        for tok in re.split(r"[、,;]|\s+or\s+", m.group(2)):
            add(tok)

    # 2) Inline bold kanji
    for m in INLINE_BOLD_KANJI_RE.finditer(text):
        add(m.group(1))

    # 3) Fallback for pages without a bold lede: pull the canonical
    # Japanese name out of one of several templates that consistently
    # carry the page's kanji form somewhere in their parameters.
    if not out:
        # 3a) {{translated page|ja|<kanji>|...}} — bottom-of-page
        for m in re.finditer(r"\{\{translated page\|ja\|([^|}]+)", text):
            add(m.group(1), min_len=2)
    if not out:
        # 3b) {{wikidata link|...|ja|<kanji>|...}} — `ja` may sit
        # anywhere after the QID, not just immediately after.
        # Handles e.g. {{wikidata link|Q1|en|Foo|ja|<kanji>|...}}
        for m in re.finditer(r"\{\{wikidata link\|[^{}]*?\|ja\|([^|}]+)", text):
            add(m.group(1), min_len=2)
    if not out:
        # 3c) Lede {{Nihongo|<en>|<kanji>|<romaji>}} as the first
        # bold marker on pages like Kōtai Shrine (disambiguation),
        # where there is no `'''<en>''' (<kanji>)` form.
        for m in re.finditer(r"\{\{[Nn]ihongo\|[^|}]+\|([^|}]+)", text):
            add(m.group(1), min_len=2)
    if not out:
        # 3d) Inline "the Japanese characters <kanji>" mentions —
        # catches Meiji-style ledes that name the kanji in prose
        # without bolding or templating them.
        for m in re.finditer(
            r"(?:Japanese characters?|kanji|written\s+(?:as|in)\s+(?:Japanese\s+as\s+)?)\s+([一-鿿々〆〇]{2,})",
            text,
        ):
            add(m.group(1), min_len=2)

    return out


# ─── WIKIDATA QUERY ───────────────────────────────────────────────

SPARQL_TEMPLATE = """
SELECT DISTINCT ?item ?itemLabel ?jaLabel ?locationLabel WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q845945 .
  ?item rdfs:label "{kanji}"@ja .
  ?item rdfs:label ?jaLabel . FILTER(LANG(?jaLabel)="ja")
  OPTIONAL {{ ?item wdt:P131 ?location . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ja". }}
}}
LIMIT 100
"""


def query_shrines_for_kanji(kanji: str) -> list[dict]:
    """SPARQL for shrines whose ja label is exactly `kanji`.

    Returns list of dicts: {qid, en_label, ja_label, location}.
    Empty list on query failure (logged, non-fatal); RateLimitError
    propagates so the caller can abort the script cleanly.
    """
    # Escape backslashes/quotes in case the kanji contains them
    if '"' in kanji or "\\" in kanji:
        log_error(f"refusing kanji with quote/backslash: {kanji!r}")
        return []

    q = SPARQL_TEMPLATE.format(kanji=kanji)
    try:
        resp = checked_post(
            SPARQL_ENDPOINT,
            data={"query": q, "format": "json"},
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/sparql-results+json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        bindings = resp.json().get("results", {}).get("bindings", [])
    except RateLimitError:
        raise
    except Exception as e:
        log_error(f"SPARQL failed for {kanji!r}: {e}")
        return []

    # Deduplicate by QID (a result can repeat across multiple ja labels
    # if the item has aliases — we want one row per shrine).
    by_qid: dict[str, dict] = {}
    for b in bindings:
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        en = b.get("itemLabel", {}).get("value", "").strip()
        ja = b.get("jaLabel", {}).get("value", "").strip()
        loc = b.get("locationLabel", {}).get("value", "").strip()
        if qid in by_qid:
            # Keep the row with location info if previous had none
            if loc and not by_qid[qid].get("location"):
                by_qid[qid]["location"] = loc
            continue
        by_qid[qid] = {
            "qid": qid,
            "en_label": en if en else ja,  # fallback to ja if no en
            "ja_label": ja,
            "location": loc,
        }
    return list(by_qid.values())


# ─── RENDERING ─────────────────────────────────────────────────────

def render_bullets(kanji_to_results: dict[str, list[dict]]) -> str:
    """Build the bullet list. Group by kanji-name when the page has
    multiple distinct names (Ebisu-style), each under its own
    subheading. Single-name pages get a flat list.
    """
    lines = [SECTION_HEADER, ""]
    multi = len(kanji_to_results) > 1

    # Track QIDs already emitted across all groups to avoid duplicates
    # — an item can show up under multiple alias kanji forms.
    seen_qids: set[str] = set()

    for kanji, results in kanji_to_results.items():
        if multi:
            lines.append(f"=== {kanji} ===")
        if not results:
            lines.append(f"''No Wikidata items currently labeled {kanji}.''")
            lines.append("")
            continue
        # Sort by EN label for stable output (so re-runs don't churn diffs)
        for r in sorted(results, key=lambda x: (x["en_label"].lower(), x["qid"])):
            if r["qid"] in seen_qids:
                continue
            seen_qids.add(r["qid"])
            ill = (
                f"{{{{ill|{r['en_label']} ({r['qid']})|"
                f"lt={r['en_label']}|qid={r['qid']}}}}}"
            )
            suffix = f" — {r['location']}" if r["location"] else ""
            lines.append(f"* {ill}{suffix}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


SECTION_BLOCK_RE = re.compile(
    re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER),
    re.S,
)


def insert_or_replace_block(text: str, block_body: str) -> str:
    """Replace the existing auto-generated block, or insert one
    just before the page's *footer* — the trailing block of
    {{translated page}} / {{wikidata link}} / [[Category:...]] lines
    that sits after the article body.

    Earlier version inserted before the first [[Category:...]] line,
    which bit us because most shrine pages carry
    [[Category:git synced pages]] up top (right after the syncing
    instruction comment) — that's not the footer category block, so
    the auto-generated section ended up above the actual page body.
    """
    block = f"{BEGIN_MARKER}\n{block_body}{END_MARKER}\n"

    if SECTION_BLOCK_RE.search(text):
        return SECTION_BLOCK_RE.sub(block.rstrip(), text)

    # Prefer inserting just before the {{translated page}} or
    # {{wikidata link}} template — these consistently mark the start
    # of the trailing footer block.
    for pat in (
        r"\n\{\{translated page\b",
        r"\n\{\{wikidata link\b",
    ):
        m = re.search(pat, text)
        if m:
            i = m.start() + 1  # keep the preceding newline attached to body
            return text[:i].rstrip() + "\n\n" + block + "\n" + text[i:]

    # Otherwise locate the FINAL contiguous block of `[[Category:...]]`
    # lines: find the last category line, walk back through any
    # preceding Category lines + blank-line gaps, then insert just
    # before the start of that block.
    cats = list(re.finditer(r"^\[\[Category:[^\]]*\]\]\s*$", text, re.M))
    if cats:
        # Walk forward from each Category match: the "footer block" is
        # the maximal trailing run of Category-only lines (allowing
        # blank lines and trailing whitespace). Start from the last
        # match and walk backward through prior Category-lines.
        last = cats[-1]
        start_idx = last.start()
        # Scan upwards for prior consecutive Category lines
        prior_idx = start_idx
        for cm in reversed(cats[:-1]):
            between = text[cm.end():prior_idx]
            # Allow only whitespace/newlines between categories
            if re.fullmatch(r"\s*", between):
                prior_idx = cm.start()
            else:
                break
        i = prior_idx
        return text[:i].rstrip() + "\n\n" + block + "\n" + text[i:]

    # No categories at all — append at end
    return text.rstrip() + "\n\n" + block


# ─── PAGE WALKING ─────────────────────────────────────────────────

def find_target_pages() -> list[str]:
    """List miraheze_unique/*.wiki paths whose leading marker
    identifies them as shrine disambig pages — these are the
    canonical source-of-truth for the refresh. Each match's
    counterpart in fandom_unique/ is updated alongside in write
    time.
    """
    out = []
    if not os.path.isdir(MIRAHEZE_UNIQUE_DIR):
        return out
    for fn in sorted(os.listdir(MIRAHEZE_UNIQUE_DIR)):
        if not fn.endswith(".wiki"):
            continue
        p = os.path.join(MIRAHEZE_UNIQUE_DIR, fn)
        try:
            with open(p, encoding="utf-8") as f:
                head = f.read(200)
        except OSError:
            continue
        if INSTRUCTION_PREFIX in head:
            out.append(p)
    return out


# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually write changes")
    ap.add_argument("--max-edits", type=int, default=10, help="max pages to edit")
    ap.add_argument("--run-tag", default="", help="wiki-formatted run tag for edit summaries")
    ap.add_argument("--page", default=None, help="restrict to a single page (filename without .wiki or basename)")
    args = ap.parse_args()

    # State here is purely for 429-recovery within a single sweep:
    # if Wikidata starts 429-ing, we save progress and the NEXT
    # invocation skips the pages we already handled in this sweep.
    # Once a sweep completes cleanly (no 429), the state is reset so
    # the next CI cycle re-processes every page from scratch — that's
    # how new Wikidata shrine items get picked up automatically.
    state = load_state()
    processed: set[str] = set(state.get("processed", []))

    targets = find_target_pages()
    if args.page:
        targets = [p for p in targets if args.page in os.path.basename(p)]
        if not targets:
            print(f"no matching page for --page={args.page!r}")
            return 1

    print(f"Found {len(targets)} candidate shrine-disambig pages")
    if processed:
        print(f"Resuming: skipping {len(processed)} pages handled in a prior 429-aborted sweep")
    edits = 0

    for path in targets:
        if edits >= args.max_edits:
            print(f"Reached max-edits cap ({args.max_edits}); stopping.")
            break

        fn = os.path.basename(path)
        if fn in processed and not args.page:
            continue

        with open(path, encoding="utf-8") as f:
            text = f.read()

        kanji_list = extract_kanji_names(text)
        if not kanji_list:
            print(f"  skip {fn}: no kanji name extracted")
            processed.add(fn)
            continue

        print(f"\n== {fn} ==")
        print(f"  kanji: {kanji_list}")

        kanji_to_results: dict[str, list[dict]] = {}
        for i, kanji in enumerate(kanji_list):
            if i > 0:
                time.sleep(THROTTLE)
            try:
                results = query_shrines_for_kanji(kanji)
            except RateLimitError:
                print("\nAborting: rate-limited by Wikidata. Resume later.")
                save_state({"processed": sorted(processed)})
                return 0
            print(f"    {kanji}: {len(results)} match{'es' if len(results) != 1 else ''}")
            kanji_to_results[kanji] = results

        if all(not r for r in kanji_to_results.values()):
            print(f"  no Wikidata matches for any kanji — skip")
            processed.add(fn)
            continue

        block_body = render_bullets(kanji_to_results)
        new_text = insert_or_replace_block(text, block_body)

        if new_text == text:
            print(f"  no change (block already in sync)")
            processed.add(fn)
            continue

        # Compute the fandom_unique/ counterpart's content. If that
        # file exists, replay the same block-insert against ITS text
        # so we don't clobber any intentional fandom-side overrides;
        # if it doesn't exist yet, just write the same content as
        # miraheze (bootstrap-seed will eventually do this anyway, but
        # writing it here keeps both sides in lock-step on this cycle).
        fd_path = os.path.join(FANDOM_UNIQUE_DIR, fn)
        if os.path.exists(fd_path):
            with open(fd_path, encoding="utf-8") as f:
                fd_text = f.read()
            new_fd_text = insert_or_replace_block(fd_text, block_body)
        else:
            new_fd_text = new_text

        if args.apply:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            with open(fd_path, "w", encoding="utf-8") as f:
                f.write(new_fd_text)
            print(f"  wrote miraheze_unique/{fn} + fandom_unique/{fn}")
        else:
            print(f"  DRY-RUN: would write miraheze_unique/{fn} + fandom_unique/{fn}")
            # Print a tiny preview
            preview = block_body.split("\n")[:8]
            for line in preview:
                print(f"    | {line}")

        processed.add(fn)
        edits += 1
        # Throttle between pages too (in addition to between SPARQL
        # queries within a page).
        time.sleep(THROTTLE)

    # Clean sweep — reset state so the next CI cycle re-processes
    # every page from the top and picks up any new Wikidata items.
    # If we'd 429-aborted mid-sweep, we'd have already returned 0
    # above with `save_state` carrying the partial progress.
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print(f"\nDone. Edits this run: {edits}. State cleared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
