"""
common.py
=========
Shared infrastructure for namespace orchestrators.

Each orchestrator (mainspace / category / template) owns a single state file
that is shared across ALL per-page operations for that namespace. Every run:

  1. Load state (titles already visited in the current cycle).
  2. Iterate allpages(ns), skipping titles in state.
  3. For each page, run every registered op whose NAMESPACES includes ns.
     Ops mutate an accumulating text buffer; if any op changed the text, we
     save ONCE with a combined summary.
  4. Append the title to state regardless of outcome, so it isn't revisited
     inside this cycle.
  5. When the allpages iterator is exhausted, clear state so the next run
     starts a fresh sweep.

An "op" is any module in shinto_miraheze.orchestrators.ops that exposes:

    NAMESPACES: tuple[int, ...]
    NAME:       str
    def apply(title: str, text: str) -> tuple[str | None, str | None]:
        # Returns (new_text, summary_fragment) on change, or (None, None).

A "heavy" op (e.g. history_offload) that owns its own save/side-effects sets
HANDLES_SAVE = True and instead exposes:

    def run(site, page, run_tag: str, apply: bool) -> tuple[bool, str]:
        # Returns (page_was_modified, status_message). If modified, the
        # orchestrator refetches page text before the regular apply() ops run.

Heavy ops run in a pre-pass, before any regular apply() ops on the same page.
"""

import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USER_AGENT = "ShintoOrchestrator/1.0 (User:EmmaBot; shinto.miraheze.org)"
THROTTLE = 2.5

# Matches hard redirects AND the common template-based soft/category
# redirect forms. Exported so individual ops can opt out of running
# on redirects (e.g. history_offload refuses outright — delete+recreate
# would trash the #REDIRECT line and redirect history isn't worth
# preserving). The orchestrator itself does NOT pre-skip redirects:
# the walk visits them, appends them to state, and most ops naturally
# no-op on them. That way state tracking is uniform across redirects
# and real pages, and any future op that wants to run on redirects
# (e.g. fixing broken ones) can just not-check.
REDIRECT_RE = re.compile(
    r"^\s*("
    r"#redirect\b"
    r"|\{\{\s*(?:category|soft)[\s_]*redirect\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
INTERWIKI_RE = re.compile(r"^[A-Za-z]{2,}:")
LOCAL_NS_PREFIXES = (
    "Category:", "Template:", "Module:", "Help:", "Talk:", "User:",
    "File:", "MediaWiki:", "Shinto Wiki:", "Wikipedia:",
    "User talk:", "Template talk:", "Category talk:", "File talk:",
    "Help talk:", "Module talk:", "MediaWiki talk:",
)


def state_path(name: str) -> str:
    return os.path.join(os.path.dirname(__file__), f"{name}.state")


def load_state(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_state(path: str, title: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def clear_state(path: str) -> None:
    open(path, "w", encoding="utf-8").close()


def login_site() -> mwclient.Site:
    username = os.getenv("WIKI_USERNAME", "EmmaBot")
    password = os.getenv("WIKI_PASSWORD", "")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.login(username, password)
    print(f"Logged in as {username}")
    return site


def iter_allpages(site: mwclient.Site, namespace: int):
    params = {"list": "allpages", "apnamespace": namespace, "aplimit": "max"}
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("allpages", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def run_orchestrator(
    namespace: int,
    ns_label: str,
    ops: list,
    state_name: str,
    apply: bool,
    max_edits: int,
    run_tag: str,
    clear_on_exhaust: bool = True,
) -> tuple[int, bool]:
    """Core loop shared by all namespace orchestrators.

    Returns (edited_count, exhausted) — exhausted is True if allpages was
    fully walked without hitting max_edits. Set clear_on_exhaust=False to
    share a single state file across multiple namespaces (the misc
    orchestrator does this to sweep many namespaces under one budget).
    """
    applicable_ops = [op for op in ops if namespace in op.NAMESPACES]
    if not applicable_ops:
        print(f"No operations registered for ns={namespace} ({ns_label}); exiting.")
        return 0, True

    heavy_ops = [op for op in applicable_ops if getattr(op, "HANDLES_SAVE", False)]
    light_ops = [op for op in applicable_ops if not getattr(op, "HANDLES_SAVE", False)]

    print(f"Ops for {ns_label}: {', '.join(op.NAME for op in applicable_ops)}")

    site = login_site()
    path = state_path(state_name)
    done = load_state(path) if apply else set()
    print(f"State ({state_name}): {len(done)} titles already processed this cycle")

    edited = checked = skipped = errors = 0
    would_edit = 0  # dry-run counter (changes the code would have made)
    finished_all = True

    for title in iter_allpages(site, namespace):
        if apply and max_edits and edited >= max_edits:
            print(f"Reached max edits ({max_edits}); stopping mid-cycle.")
            finished_all = False
            break
        if not apply and max_edits and would_edit >= max_edits:
            print(f"Reached dry-run limit ({max_edits} would-edit pages); stopping.")
            finished_all = False
            break

        if title in done:
            continue

        # Interwiki titles in mainspace aren't real local pages.
        if namespace == 0 and INTERWIKI_RE.match(title) and not title.startswith(LOCAL_NS_PREFIXES):
            if apply:
                append_state(path, title)
            skipped += 1
            continue

        checked += 1
        if checked % 500 == 0:
            print(f"  ... scanned {checked} pages ({edited} edited)")

        try:
            page = site.pages[title]
            if not page.exists:
                if apply:
                    append_state(path, title)
                skipped += 1
                continue
            text = page.text()
        except Exception as e:
            print(f"[{checked}] {title} ERROR reading: {e}")
            errors += 1
            if apply:
                append_state(path, title)
            continue

        # NOTE: we deliberately do NOT pre-skip redirects here. Redirects
        # should be walked, appended to state, and either (a) no-op through
        # every op that checks its content (most do) or (b) get an
        # explicit refusal inside the op (history_offload, wikidata_link).
        # Skipping wholesale up front made it invisible whether a given op
        # was actually safe on redirects or not. Per-op refusal is clearer
        # and leaves room for future ops that legitimately want to edit
        # redirects (e.g. fix double redirects).

        # Heavy-op pre-pass: each heavy op owns its own save. If any modifies
        # the page, refetch text before the light ops see it.
        heavy_failure = False
        for op in heavy_ops:
            try:
                modified, msg = op.run(site, page, run_tag, apply)
            except Exception as e:
                print(f"[{checked}] {title} heavy op {op.NAME} ERROR: {e}")
                errors += 1
                heavy_failure = True
                break
            if msg:
                print(f"[{checked}] {title} [{op.NAME}] {msg}")
            if modified:
                try:
                    text = page.text()
                except Exception as e:
                    print(f"[{checked}] {title} refetch ERROR after {op.NAME}: {e}")
                    errors += 1
                    heavy_failure = True
                    break
                edited += 1
        if heavy_failure:
            if apply:
                append_state(path, title)
            continue

        new_text = text
        summaries = []
        for op in light_ops:
            try:
                candidate, fragment = op.apply(title, new_text)
            except Exception as e:
                print(f"[{checked}] {title} op {op.NAME} ERROR: {e}")
                errors += 1
                continue
            if candidate is not None and candidate != new_text:
                new_text = candidate
                if fragment:
                    summaries.append(fragment)

        if new_text == text:
            if apply:
                append_state(path, title)
            continue

        if not apply:
            print(f"[{checked}] {title} DRY RUN: {'; '.join(summaries) or '(no summary)'}")
            would_edit += 1
            continue

        summary = "Bot: " + "; ".join(summaries) + f" {run_tag}"
        try:
            page.save(new_text, summary=summary)
            edited += 1
            print(f"[{checked}] {title} EDITED: {'; '.join(summaries)}")
            append_state(path, title)
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {title} ERROR saving: {e}")
            errors += 1
            append_state(path, title)

    if finished_all and apply and clear_on_exhaust:
        print(f"\nCycle complete for {ns_label} — clearing state.")
        clear_state(path)

    print(f"\n{'=' * 60}")
    print(f"Namespace: {ns_label} (ns={namespace})")
    print(f"Checked:   {checked}")
    print(f"Edited:    {edited}")
    print(f"Skipped:   {skipped}")
    print(f"Errors:    {errors}")
    return edited, finished_all
