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

A light op may also set PRE_HEAVY = True to opt into running BEFORE the
heavy-op pre-pass. All PRE_HEAVY light ops are run first as a group with
a single combined save; the page is then refetched and heavy ops + the
remaining light ops run as normal. Used for cleanups (interlang
consolidation, comment stripping) that should be reflected in
history_offload's fandom mirror and XML archive snapshots.
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

# Hard cap on state-file growth per run. Once this many titles have been
# appended to state in a single run, the walk stops mid-cycle and the
# remainder waits for the next run. Without this cap, a run where every
# page is a no-op (nothing to edit) would walk the entire namespace —
# potentially tens of thousands of pages — in a single CI run. At ~5-10
# pages/sec that's multi-hour no-op walks. This bounds one run at
# roughly "fetch 1000 pages worth of content" = ~10-15 min.
MAX_STATE_GROWTH_PER_RUN = 1000

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


def iter_allpages(site: mwclient.Site, namespace: int, start_from: str = ""):
    """Yield every page title in `namespace`, optionally starting alphabetically
    at `start_from`. The `start_from` value is a title WITHOUT the namespace
    prefix (MediaWiki's apfrom parameter expects the in-namespace title, since
    apnamespace is specified separately)."""
    params = {"list": "allpages", "apnamespace": namespace, "aplimit": "max"}
    if start_from:
        params["apfrom"] = start_from
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("allpages", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def _namespace_prefix(site: mwclient.Site, namespace: int) -> str | None:
    """Returns 'Template:' for ns=10, '' for ns=0 (mainspace), None if the
    namespace name can't be resolved from the site's siteinfo (in which case
    the caller should skip the apfrom optimization for safety)."""
    if namespace == 0:
        return ""
    try:
        name = site.namespaces.get(namespace, "")
    except Exception:
        return None
    if not name:
        return None
    return f"{name}:"


def _compute_apfrom(done: set[str], namespace_prefix: str | None) -> str:
    """Return the alphabetically-max title in `done` that belongs to the
    given namespace (matched by prefix), with the prefix stripped for use
    with allpages' `apfrom` parameter. Empty string if there are no matches
    or the prefix couldn't be resolved — caller should then walk from the
    beginning of the namespace."""
    if namespace_prefix is None:
        return ""
    if namespace_prefix:
        stripped = [t[len(namespace_prefix):] for t in done if t.startswith(namespace_prefix)]
    else:
        stripped = list(done)
    if not stripped:
        return ""
    return max(stripped)


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
    all_light_ops = [op for op in applicable_ops if not getattr(op, "HANDLES_SAVE", False)]
    pre_heavy_ops = [op for op in all_light_ops if getattr(op, "PRE_HEAVY", False)]
    light_ops = [op for op in all_light_ops if not getattr(op, "PRE_HEAVY", False)]

    print(f"Ops for {ns_label}: {', '.join(op.NAME for op in applicable_ops)}")

    site = login_site()
    path = state_path(state_name)
    done = load_state(path) if apply else set()
    print(f"State ({state_name}): {len(done)} titles already processed this cycle")

    # Performance: use MediaWiki's `apfrom` to start the walk server-side at
    # the alphabetically-last title already in state for this namespace. That
    # avoids enumerating the already-done prefix at one API call per 500
    # titles just to discard each via the in-memory 'done' lookup.
    ns_prefix = _namespace_prefix(site, namespace)
    start_from = _compute_apfrom(done, ns_prefix)
    if start_from:
        print(f"Resuming walk at apfrom={start_from!r} (server-side skip of {len(done)} prior titles)")

    edited = checked = skipped = errors = 0
    would_edit = 0  # dry-run counter (changes the code would have made)
    state_growth = 0  # titles appended to state in THIS run (bounded below)
    finished_all = True

    def _mark_done(t: str) -> None:
        """Append `t` to state and bump the per-run growth counter. All
        in-loop append_state calls go through this helper so the cap
        applies uniformly regardless of outcome (edit / no-op / error)."""
        nonlocal state_growth
        append_state(path, t)
        state_growth += 1

    for title in iter_allpages(site, namespace, start_from=start_from):
        if apply and state_growth >= MAX_STATE_GROWTH_PER_RUN:
            print(f"Reached max state growth per run ({MAX_STATE_GROWTH_PER_RUN}); stopping mid-cycle.")
            finished_all = False
            break
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
                _mark_done(title)
            skipped += 1
            continue

        checked += 1
        if checked % 500 == 0:
            print(f"  ... scanned {checked} pages ({edited} edited)")

        try:
            page = site.pages[title]
            if not page.exists:
                if apply:
                    _mark_done(title)
                skipped += 1
                continue
            text = page.text()
        except Exception as e:
            print(f"[{checked}] {title} ERROR reading: {e}")
            errors += 1
            if apply:
                _mark_done(title)
            continue

        # NOTE: we deliberately do NOT pre-skip redirects here. Redirects
        # should be walked, appended to state, and either (a) no-op through
        # every op that checks its content (most do) or (b) get an
        # explicit refusal inside the op (history_offload, wikidata_link).
        # Skipping wholesale up front made it invisible whether a given op
        # was actually safe on redirects or not. Per-op refusal is clearer
        # and leaves room for future ops that legitimately want to edit
        # redirects (e.g. fix double redirects).

        # Pre-heavy phase: run light ops marked PRE_HEAVY=True with a
        # single combined save, BEFORE any heavy op gets to see the page.
        # This is what makes cleanups (interlang consolidation, comment
        # stripping) propagate into history_offload's fandom mirror and
        # XML archive snapshots in the same cycle, instead of having to
        # wait for a follow-up cycle.
        pre_heavy_failed = False
        if pre_heavy_ops:
            candidate = text
            pre_summaries: list[str] = []
            for op in pre_heavy_ops:
                try:
                    new, fragment = op.apply(title, candidate)
                except Exception as e:
                    print(f"[{checked}] {title} pre-heavy op {op.NAME} ERROR: {e}")
                    errors += 1
                    continue
                if new is not None and new != candidate:
                    candidate = new
                    if fragment:
                        pre_summaries.append(fragment)
            if candidate != text:
                if not apply:
                    print(f"[{checked}] {title} DRY RUN (pre-heavy): {'; '.join(pre_summaries) or '(no summary)'}")
                    would_edit += 1
                    continue
                summary = "Bot: " + "; ".join(pre_summaries) + f" {run_tag}"
                try:
                    page.save(candidate, summary=summary)
                    edited += 1
                    print(f"[{checked}] {title} EDITED (pre-heavy): {'; '.join(pre_summaries)}")
                    time.sleep(THROTTLE)
                except Exception as e:
                    print(f"[{checked}] {title} ERROR saving pre-heavy: {e}")
                    errors += 1
                    pre_heavy_failed = True
                if not pre_heavy_failed:
                    try:
                        text = page.text()
                    except Exception as e:
                        print(f"[{checked}] {title} refetch ERROR after pre-heavy: {e}")
                        errors += 1
                        pre_heavy_failed = True
        if pre_heavy_failed:
            if apply:
                _mark_done(title)
            continue

        # Heavy-op pre-pass: each heavy op owns its own save. If any modifies
        # the page, refetch text before the light ops see it.
        #
        # Ops may opt into "defer if a prior heavy op already modified this
        # page in this visit" by setting DEFER_IF_PRIOR_MODIFIED = True.
        # Used by lower-priority ops (e.g. template_mainspace_usage) to
        # yield edit budget to higher-priority ops (e.g. history_offload) —
        # the deferred op will run on the next cycle's visit when the
        # higher-priority op is a no-op for that page.
        heavy_failure = False
        prior_heavy_modified = False
        for op in heavy_ops:
            if prior_heavy_modified and getattr(op, "DEFER_IF_PRIOR_MODIFIED", False):
                print(f"[{checked}] {title} [{op.NAME}] deferred (prior heavy op modified this page)")
                continue
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
                prior_heavy_modified = True
        if heavy_failure:
            if apply:
                _mark_done(title)
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
                _mark_done(title)
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
            _mark_done(title)
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"[{checked}] {title} ERROR saving: {e}")
            errors += 1
            _mark_done(title)

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
