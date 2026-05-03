#!/usr/bin/env python3
"""
cleanup_fandom_pages.py
=======================
Fandom-side cleanup for pages tracked in
``shinto_miraheze/sync_fandom_pages.state``. The bidirectional sync
(``sync_fandom_pages.py``) copies miraheze content verbatim to fandom,
which leaves the fandom copies full of constructs that don't work
there:

  * ``{{ill|...}}``                  -- relies on Lua modules that
                                        don't exist on fandom
  * ``{{wikidata link|...}}``        -- requires Wikibase Client
                                        (off on fandom)
  * ``{{shortdesc|...}}``,           -- ShortDescription extension
    ``{{SHORTDESC:...}}``               not enabled on fandom
  * triplicated ``<!--interwikis        bot-edit accumulation
    from wikidata-->`` blocks
  * pages that include BOTH
    ``{{Infobox Buddhist temple}}``
    AND ``{{Infobox religious
    building}}``                       Buddhist-temple is a redirect
                                        to religious-building so the
                                        page renders the same infobox
                                        twice; keep the religious
                                        -building call (it's the
                                        canonical one)

This script applies textual cleanups to the fandom-side copies only,
then updates the sync state's ``fan_revid``/``fan_sha`` to point at
the post-cleanup revision. ``sync_fandom_pages.py`` (modified in the
same change set) recognises the resulting "neither side changed but
content differs" case and treats it as a deliberate divergence
preserved across runs.

Out of scope (deliberately): rewriting the actual infobox templates
(Template:Infobox religious building etc.) as Fandom Portable
Infoboxes. That's a manual rewrite per template and is tracked in
todo.md as a follow-up.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

THROTTLE = 2.5

FAN_HOST = "shinto.fandom.com"
FAN_PATH = "/"
FANDOM_USERNAME = os.getenv("FANDOM_USERNAME", "")
FANDOM_PASSWORD = os.getenv("FANDOM_PASSWORD", "")

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / "sync_fandom_pages.state"

USER_AGENT = (
    "FandomCleanupBot/1.0 (User:EmmaBot; shinto.fandom.com cleanup)"
)


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(path: Path, state: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


# --- Cleanup transforms -------------------------------------------------

INTERWIKI_LINE_RE = re.compile(
    r"<!--\s*interwikis from wikidata\s*-->"
    r"(?:\[\[[^\]]+\]\])+"
    r"\s*\n?",
    re.IGNORECASE,
)


def dedupe_interwiki_blocks(text: str) -> str:
    """Collapse repeated ``<!--interwikis from wikidata-->[[...]][[...]]``
    blocks down to the LAST occurrence. Bot edits have left up to three
    consecutive copies on some pages."""
    matches = list(INTERWIKI_LINE_RE.finditer(text))
    if len(matches) <= 1:
        return text
    # Drop every match except the last; iterate in reverse so spans stay
    # valid as we splice.
    keep_idx = len(matches) - 1
    out = text
    for i, m in enumerate(matches):
        if i == keep_idx:
            continue
    # Easier: rebuild by stripping every occurrence then prepending the
    # last canonical block. The block content is almost identical across
    # repetitions; using the last one is fine.
    canonical = matches[-1].group(0)
    out = INTERWIKI_LINE_RE.sub("", text)
    return canonical + out


def find_balanced_template(text: str, start: int):
    """Given that ``text[start:]`` begins with ``{{``, return the index
    just past the matching closing ``}}``. Handles nested ``{{...}}``
    pairs but does not try to be clever about ``{{{...}}}`` parameter
    triples (good enough for the templates we're cleaning)."""
    depth = 0
    i = start
    while i < len(text) - 1:
        if text[i:i + 2] == "{{":
            depth += 1
            i += 2
            continue
        if text[i:i + 2] == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return i
            continue
        i += 1
    return -1


def _split_template_args(body: str) -> list[str]:
    """Split a template body (everything between ``{{name|`` and ``}}``)
    into top-level pipe-separated args, respecting brace and bracket
    nesting."""
    parts: list[str] = []
    depth_brace = 0
    depth_bracket = 0
    buf: list[str] = []
    for ch in body:
        if ch == "{":
            depth_brace += 1
            buf.append(ch)
        elif ch == "}":
            depth_brace -= 1
            buf.append(ch)
        elif ch == "[":
            depth_bracket += 1
            buf.append(ch)
        elif ch == "]":
            depth_bracket -= 1
            buf.append(ch)
        elif ch == "|" and depth_brace == 0 and depth_bracket == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _convert_ill_call(body_after_pipe: str) -> str:
    """Convert one {{ill|...}} body (the part after ``ill|``) into a
    plain wikilink. Returns the wikilink wikitext.

    Handles seen variants:
      {{ill|Buddhism|qid=Q748|1=Buddhism}}                     -> [[Buddhism]]
      {{ill|Fukutsu, Fukuoka|en|Fukutsu, Fukuoka|qid=...|lt=Fukutsu|1=Fukutsu}}
                                                               -> [[Fukutsu, Fukuoka|Fukutsu]]
      {{ill|Q22120745|qid=Q22120745|1=Yamato Northern 88 Sacred Sites}}
                                                               -> [[Yamato Northern 88 Sacred Sites]]
                                                                  (when target is a QID, fall back to display)
    """
    parts = _split_template_args(body_after_pipe)
    target = parts[0].strip() if parts else ""
    # Collect named args.
    named: dict[str, str] = {}
    positionals: list[str] = []
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            named[k.strip()] = v.strip()
        else:
            positionals.append(p.strip())

    display = named.get("lt") or named.get("1") or ""
    if not display and positionals:
        # ill's positional schema is unfortunately variable; fall back
        # to the first positional that doesn't look like a 2-letter
        # language code.
        for p in positionals:
            if p and not (len(p) <= 3 and p.isalpha()):
                display = p
                break

    # If target looks like a bare QID and we have a display, swap them
    # so the link points at a real page name rather than a Wikidata id.
    if target.startswith("Q") and target[1:].isdigit() and display:
        target = display

    if not target:
        return display or ""
    if not display or display == target:
        return f"[[{target}]]"
    return f"[[{target}|{display}]]"


def replace_template_calls(text: str, name_pattern: re.Pattern,
                           replacer):
    """Walk every ``{{name|...}}`` call where ``{{name`` matches
    ``name_pattern`` and replace it via ``replacer(body_after_name)``.

    ``replacer`` receives the body string AFTER the leading pipe (or
    empty string if no pipe) and returns the wikitext to substitute.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        m = name_pattern.match(text, i)
        if not m:
            out.append(text[i])
            i += 1
            continue
        end = find_balanced_template(text, i)
        if end < 0:
            # Unbalanced — bail out and keep the rest verbatim.
            out.append(text[i:])
            return "".join(out)
        full = text[i:end]
        # Body is everything between {{name and the closing }}.
        # Strip the {{name and the trailing }}; what remains starts
        # with either '|...' or empty.
        body_after_name = full[len(m.group(0)):-2]
        if body_after_name.startswith("|"):
            body_after_name = body_after_name[1:]
        replacement = replacer(body_after_name)
        out.append(replacement)
        i = end
    return "".join(out)


ILL_NAME_RE = re.compile(r"\{\{\s*ill\b", re.IGNORECASE)
WIKIDATA_LINK_RE = re.compile(r"\{\{\s*wikidata link\b", re.IGNORECASE)
SHORTDESC_RE = re.compile(r"\{\{\s*shortdesc\b", re.IGNORECASE)
SHORTDESC_MAGIC_RE = re.compile(
    r"\{\{\s*SHORTDESC\s*:[^{}]*?\}\}",
    re.IGNORECASE,
)


def convert_ill_to_wikilinks(text: str) -> str:
    return replace_template_calls(text, ILL_NAME_RE, _convert_ill_call)


def strip_wikidata_link(text: str) -> str:
    return replace_template_calls(text, WIKIDATA_LINK_RE, lambda body: "")


def strip_shortdesc(text: str) -> str:
    text = replace_template_calls(text, SHORTDESC_RE, lambda body: "")
    text = SHORTDESC_MAGIC_RE.sub("", text)
    return text


# Pages that have both {{Infobox Buddhist temple|...}} AND
# {{Infobox religious building|...}}: drop the Buddhist temple call
# (it's a redirect to religious-building, so keeping both renders the
# same infobox twice).
INFOBOX_BUDDHIST_RE = re.compile(
    r"\{\{\s*Infobox\s+Buddhist\s+temple\b",
    re.IGNORECASE,
)
INFOBOX_RELIGIOUS_RE = re.compile(
    r"\{\{\s*Infobox\s+religious\s+building\b",
    re.IGNORECASE,
)


def drop_redundant_buddhist_infobox(text: str) -> str:
    if not INFOBOX_RELIGIOUS_RE.search(text):
        return text
    # Walk and strip {{Infobox Buddhist temple|...}} occurrences.
    return replace_template_calls(text, INFOBOX_BUDDHIST_RE, lambda body: "")


# --- Per-page transform ------------------------------------------------

def cleanup_text(text: str) -> str:
    """Apply every cleanup transform in a deterministic order."""
    text = dedupe_interwiki_blocks(text)
    text = drop_redundant_buddhist_infobox(text)
    text = convert_ill_to_wikilinks(text)
    text = strip_wikidata_link(text)
    text = strip_shortdesc(text)
    # Collapse 3+ blank lines that the strips may have left behind.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# --- Wiki helpers (mirror sync_fandom_pages) ---------------------------

def fetch_page(site, title: str):
    result = site.api(
        "query",
        prop="revisions",
        rvprop="ids|content",
        rvslots="main",
        rvlimit=1,
        titles=title,
        formatversion="2",
    )
    pages = result.get("query", {}).get("pages", []) or []
    if not pages:
        return False, None, None
    page = pages[0]
    if page.get("missing"):
        return False, None, None
    revs = page.get("revisions") or []
    if not revs:
        return False, None, None
    rev = revs[0]
    return True, rev.get("revid"), rev.get("slots", {}).get("main", {}).get("content", "")


def _fetch_latest_revid(site, title):
    result = site.api(
        "query", prop="revisions", rvprop="ids", rvlimit=1,
        titles=title, formatversion="2",
    )
    pages = result.get("query", {}).get("pages", []) or []
    if not pages:
        return None
    revs = pages[0].get("revisions") or []
    return revs[0].get("revid") if revs else None


def write_page(site, title: str, text: str, summary: str):
    page = site.pages[title]
    result = page.save(text, summary=summary)
    new_revid = (result or {}).get("newrevid")
    if new_revid is None:
        new_revid = _fetch_latest_revid(site, title)
    return new_revid


# --- main --------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually edit fandom (default dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Cap on fandom edits per run (default 50).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    if not FANDOM_USERNAME or not FANDOM_PASSWORD:
        print("FATAL: FANDOM_USERNAME / FANDOM_PASSWORD env vars are required.")
        return 2

    state = load_state(STATE_FILE)
    if not state:
        print(f"State file {STATE_FILE} is empty; nothing to clean up.")
        return 0
    print(f"State: {len(state)} tracked pages")

    print(f"Logging in to {FAN_HOST}...")
    fan = mwclient.Site(FAN_HOST, path=FAN_PATH, clients_useragent=USER_AGENT)
    fan.connection.timeout = 120
    fan.login(FANDOM_USERNAME, FANDOM_PASSWORD)
    print("  OK")

    cleaned = unchanged = errors = skipped = 0
    edits_performed = 0

    for title in sorted(state.keys()):
        if edits_performed >= args.max_edits:
            skipped += 1
            continue

        try:
            exists, fan_revid, fan_text = fetch_page(fan, title)
        except Exception as e:
            errors += 1
            print(f"ERROR fetching {title}: {e}")
            continue
        if not exists:
            errors += 1
            print(f"MISSING on fandom: {title}")
            continue

        new_text = cleanup_text(fan_text)
        if new_text == fan_text:
            unchanged += 1
            continue

        if not args.apply:
            print(f"[DRY] CLEAN {title}  ({len(fan_text)} -> {len(new_text)} chars)")
            cleaned += 1
            continue

        try:
            new_fan_revid = write_page(
                fan, title, new_text,
                summary=(
                    f"Fandom-side cleanup: dedupe interwikis, drop "
                    f"{{{{ill}}}}/{{{{wikidata link}}}}/{{{{shortdesc}}}} {args.run_tag}"
                ),
            )
        except Exception as e:
            errors += 1
            print(f"ERROR saving {title}: {e}")
            continue

        new_sha = sha1_text(new_text)
        # Update sync state so next bidirectional sync sees this as the
        # baseline (no propagation back to miraheze).
        entry = state.get(title) or {}
        entry["fan_revid"] = new_fan_revid
        entry["fan_sha"] = new_sha
        state[title] = entry
        save_state(STATE_FILE, state)

        cleaned += 1
        edits_performed += 1
        print(f"CLEAN {title}  -> fandom rev {new_fan_revid}")
        time.sleep(THROTTLE)

    print(f"\n{'=' * 60}")
    print(f"Cleaned (edited):  {cleaned}")
    print(f"Already clean:     {unchanged}")
    print(f"Skipped (cap):     {skipped}")
    print(f"Errors:            {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
