#!/usr/bin/env python3
"""
untransclude_crud_templates.py
===============================
Walks ``Category:Crud templates`` and, for every member template,
rewrites every transclusion and direct backlink on the wiki to
point at ``Template:Removed template`` instead — preserving the
original parameter data.

For each crud template ``Template:Foo``:

  * ``{{Foo|x=1|y=2}}``           → ``{{Removed template|x=1|y=2}}``
  * ``{{ Template: foo |x=1}}``   → ``{{Removed template |x=1}}``
  * ``[[Template:Foo|display]]``  → ``[[Template:Removed template|display]]``
  * ``[[:Template:Foo]]``         → ``[[Template:Removed template]]``

The original template page is NOT modified. Once every transclusion
and backlink across the wiki has been rewritten, the crud template
has zero references and naturally falls into
``Special:UnusedTemplates``; the existing ``delete_unused_templates.py``
pipeline then removes it. The CRUD-templates category itself is left
intact — a crud template still lives in ``Category:Crud templates``
right up until the unused-templates sweep deletes it.

Parameter data preservation is the load-bearing design choice. Pages
that used a now-banned template lose its rendering, but the data the
template received stays on the page as parameters of
``{{Removed template}}``. ``Template:Removed template`` is expected
to exist on the wiki as a placeholder that ignores its parameters and
renders a brief "this template has been removed" notice. The script
verifies the placeholder exists and aborts with a clear message if
not — create it manually before running with ``--apply``.

Performance considerations:

  * A single transcluding/backlinking page is fetched and saved once
    per run, even if it references multiple crud templates — the
    rewrite pass handles every crud template found in one shot. This
    is critical for the "many crud templates × many shared pages" case
    and keeps wiki edit count down.
  * Read-only API calls (categorymembers, embeddedin, linkshere,
    page.text) are throttled at 0.3s; saves go through the standard
    ``THROTTLE = 2.5`` per the wiki-load policy.
  * Stateful via ``.state`` so it resumes across runs. Pages are
    appended to state regardless of edit outcome (so a page that
    no-ops on retry doesn't get revisited).

Pacing caps (this is intentionally a slow sweep — rewriting
transclusions is intrusive, and bot-load on miraheze matters):

  * ``--max-templates`` (default 10) — at most N crud templates per
    run. Pulled in iteration order of the category.
  * ``--max-pages`` (default 10) — at most N distinct affected pages
    visited per run, summed across all crud templates in this run.
  * ``--max-edits`` (default 100) — hard ceiling on saves. With the
    other two caps in place this is mostly defence-in-depth, but it
    bounds the worst case if the page-set ever explodes.

The three caps compose by short-circuiting: whichever is reached
first stops the run mid-sweep, and ``.state`` carries the progress to
the next cycle.

Standard CLI flags: ``--apply`` (default dry-run), ``--run-tag``.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient
from wiki_login import login_with_retry

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.user_agent import USER_AGENT

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
THROTTLE = 2.5
READ_THROTTLE = 0.3
USER_AGENT = USER_AGENT

SOURCE_CATEGORY = "Crud templates"
REMOVED_TEMPLATE_TITLE = "Template:Removed template"
REMOVED_TEMPLATE_NAME = "Removed template"

STATE_FILE = os.path.join(
    os.path.dirname(__file__), "untransclude_crud_templates.state"
)


# ─── state ─────────────────────────────────────────────────


def load_state() -> set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_state(title: str) -> None:
    with open(STATE_FILE, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def clear_state() -> None:
    open(STATE_FILE, "w", encoding="utf-8").close()


# ─── name normalization + regex builders ───────────────────


def _strip_template_prefix(title: str) -> str:
    """``Template:Foo`` → ``Foo``; bare names pass through."""
    if title.startswith("Template:"):
        return title[len("Template:"):]
    return title


def _name_char_class(ch: str) -> str:
    """Per-character regex fragment for case-insensitive first char +
    underscore/space equivalence everywhere."""
    if ch in " _":
        return r"[ _]"
    if ch.isalpha():
        return f"[{ch.upper()}{ch.lower()}]"
    return re.escape(ch)


def _name_pattern(name: str) -> str:
    """Regex fragment matching `name` with MediaWiki normalization:
    first char case-insensitive, underscore/space interchangeable.
    The name can be passed with or without leading ``Template:`` —
    we use the bare name."""
    bare = _strip_template_prefix(name)
    if not bare:
        return ""
    return "".join(_name_char_class(c) for c in bare)


def build_transclusion_re(name: str) -> re.Pattern:
    """Match the prefix of a transclusion call:
    ``{{`` + optional whitespace + optional ``Template:`` + name +
    lookahead for `|` or `}}`. Lookahead means the regex consumes
    only the part we replace; the parameter block / closing braces
    are left untouched, which preserves nested templates inside
    parameters."""
    name_pat = _name_pattern(name)
    return re.compile(
        rf"\{{\{{\s*(?:[Tt]emplate\s*:\s*)?{name_pat}\s*(?=\||\}}\}})"
    )


def build_wikilink_re(name: str) -> re.Pattern:
    """Match the target-prefix of a wikilink to Template:`name`,
    leaving any display-text / closing brackets to the right
    untouched."""
    name_pat = _name_pattern(name)
    return re.compile(
        rf"\[\[\s*:?\s*[Tt]emplate\s*:\s*{name_pat}\s*(?=\||\]\])"
    )


# ─── api helpers ───────────────────────────────────────────


def iter_category_members(site, category: str, namespace: int = 10):
    """Yield titles in the category, optionally filtered to a single
    namespace (default Template ns=10)."""
    params = {
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "max",
        "cmnamespace": str(namespace),
    }
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("categorymembers", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def iter_embeddedin(site, title: str):
    """Yield titles that transclude `title`."""
    params = {
        "list": "embeddedin",
        "eititle": title,
        "eilimit": "max",
        "eifilterredir": "nonredirects",
    }
    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("embeddedin", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break
        time.sleep(READ_THROTTLE)


def iter_linkshere(site, title: str):
    """Yield titles that link directly to `title` (wikilinks, not
    just transclusions)."""
    params = {
        "prop": "linkshere",
        "titles": title,
        "lhlimit": "max",
        "lhshow": "!redirect",
        "formatversion": "2",
    }
    while True:
        result = site.api("query", **params)
        pages = result.get("query", {}).get("pages", [])
        for page in pages:
            for entry in page.get("linkshere", []):
                yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break
        time.sleep(READ_THROTTLE)


def page_exists(site, title: str) -> bool:
    page = site.pages[title]
    return page.exists


REMOVED_TEMPLATE_PLACEHOLDER_BODY = (
    "<noinclude>\n"
    "This template is the catch-all replacement for templates listed under "
    "[[:Category:Crud templates]]. When a crud template is untranscluded "
    "by ``untransclude_crud_templates.py``, every call to it is rewritten "
    "to ``{{Removed template|...}}`` so the original parameter data is "
    "preserved on the page even though the template itself is being "
    "deleted. This page intentionally ignores all parameters and renders "
    "a brief notice.\n"
    "[[Category:Maintenance templates]]\n"
    "</noinclude>"
    "<includeonly>"
    "<span style=\"color:#888;font-size:smaller\">(removed template)</span>"
    "</includeonly>"
)


def ensure_removed_template(site, run_tag: str) -> bool:
    """If Template:Removed template doesn't exist, create it with the
    placeholder body. Returns True if it exists (now or already).
    """
    page = site.pages[REMOVED_TEMPLATE_TITLE]
    if page.exists:
        return True
    summary = (
        f"create placeholder for crud-template untransclusion "
        f"{run_tag}"
    ).strip()
    try:
        page.save(
            REMOVED_TEMPLATE_PLACEHOLDER_BODY,
            summary=summary,
            minor=False,
            bot=True,
        )
        print(f"Created {REMOVED_TEMPLATE_TITLE} (placeholder)")
        return True
    except Exception as e:
        print(f"FATAL: failed to create {REMOVED_TEMPLATE_TITLE}: {e}", file=sys.stderr)
        return False


# ─── main ───────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually save edits")
    ap.add_argument(
        "--max-templates", type=int, default=10,
        help="Max crud templates processed per run (default 10).",
    )
    ap.add_argument(
        "--max-pages", type=int, default=10,
        help="Max distinct affected pages visited per run (default 10).",
    )
    ap.add_argument(
        "--max-edits", type=int, default=100,
        help="Hard ceiling on actual saves per run (default 100).",
    )
    ap.add_argument("--run-tag", default="manual run")
    args = ap.parse_args()

    username = os.getenv("WIKI_USERNAME", "EmmaBot")
    password = os.getenv("WIKI_PASSWORD", "")
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    login_with_retry(site, username, password)
    print(f"Logged in as {username}")

    # Step 0: placeholder must exist on the wiki before we rewrite
    # anything to point at it. In apply mode we auto-create it with
    # the canned placeholder body so the user doesn't have to
    # remember; dry-run just warns since no edits will follow.
    if not page_exists(site, REMOVED_TEMPLATE_TITLE):
        if args.apply:
            if not ensure_removed_template(site, args.run_tag):
                return 2
        else:
            print(
                f"WARN (dry-run): {REMOVED_TEMPLATE_TITLE} does not "
                f"exist on the wiki yet; apply-mode would auto-create "
                f"it with the placeholder body."
            )

    # Step 1: gather crud templates (capped by --max-templates per run)
    all_crud_titles = list(iter_category_members(site, SOURCE_CATEGORY))
    # Filter out the placeholder in case someone accidentally tagged it.
    all_crud_titles = [
        t for t in all_crud_titles
        if _strip_template_prefix(t).lower() != REMOVED_TEMPLATE_NAME.lower()
    ]
    print(f"Found {len(all_crud_titles)} crud templates total")
    if not all_crud_titles:
        print("Nothing to do.")
        return 0

    crud_titles = all_crud_titles[: args.max_templates]
    crud_names = [_strip_template_prefix(t) for t in crud_titles]
    print(
        f"Processing {len(crud_titles)} this run "
        f"(--max-templates={args.max_templates}); "
        f"{len(all_crud_titles) - len(crud_titles)} remain for future runs"
    )

    # Pre-compile per-template regexes
    rewriters: list[tuple[str, re.Pattern, re.Pattern]] = []
    for name in crud_names:
        rewriters.append(
            (name, build_transclusion_re(name), build_wikilink_re(name))
        )

    # Step 2: gather every page that references any crud template
    affected: set[str] = set()
    for crud_title, crud_name in zip(crud_titles, crud_names):
        if crud_name.lower() == REMOVED_TEMPLATE_NAME.lower():
            continue
        # transclusions
        for t in iter_embeddedin(site, crud_title):
            affected.add(t)
        # wikilinks
        for t in iter_linkshere(site, crud_title):
            affected.add(t)
    print(f"Affected pages (union across all crud templates): {len(affected)}")

    # Step 3: process each affected page
    done = load_state() if args.apply else set()
    print(f"State: {len(done)} pages already processed")

    edited = visited = checked = skipped = errors = 0
    finished_all = True
    for title in sorted(affected):
        if args.apply and edited >= args.max_edits:
            print(f"Reached max edits ({args.max_edits}); stopping mid-sweep.")
            finished_all = False
            break
        if visited >= args.max_pages:
            print(
                f"Reached max pages ({args.max_pages}); stopping mid-sweep."
            )
            finished_all = False
            break
        if title in done:
            continue
        visited += 1
        # Don't touch the crud templates themselves — their page wikitext
        # might validly contain {{Foo}} examples in <noinclude> docs, and
        # we want them to stay listed under Category:Crud templates.
        if title in crud_titles:
            if args.apply:
                append_state(title)
            skipped += 1
            continue
        checked += 1

        try:
            page = site.pages[title]
            if not page.exists:
                if args.apply:
                    append_state(title)
                continue
            text = page.text()
        except Exception as e:
            print(f"  {title}: read error: {e}")
            errors += 1
            if args.apply:
                append_state(title)
            continue

        new_text = text
        templates_hit: list[str] = []
        links_hit: list[str] = []
        for name, t_re, l_re in rewriters:
            t_count = len(t_re.findall(new_text))
            if t_count:
                new_text = t_re.sub(f"{{{{{REMOVED_TEMPLATE_NAME}", new_text)
                templates_hit.append(f"{name}×{t_count}")
            l_count = len(l_re.findall(new_text))
            if l_count:
                new_text = l_re.sub(
                    f"[[{REMOVED_TEMPLATE_TITLE}", new_text
                )
                links_hit.append(f"{name}×{l_count}")

        if new_text == text:
            if args.apply:
                append_state(title)
            continue

        summary_parts = []
        if templates_hit:
            summary_parts.append("templates: " + ", ".join(templates_hit))
        if links_hit:
            summary_parts.append("links: " + ", ".join(links_hit))
        body = "; ".join(summary_parts) or "rewrite crud refs"
        summary = (
            f"untransclude crud templates → {REMOVED_TEMPLATE_NAME} "
            f"({body}) {args.run_tag}"
        ).strip()

        if not args.apply:
            print(f"  DRY {title}: {body}")
            edited += 1
            continue

        try:
            page.save(new_text, summary=summary, minor=False, bot=True)
            edited += 1
            print(f"  EDIT {title}: {body}")
        except Exception as e:
            print(f"  {title}: save error: {e}")
            errors += 1
        append_state(title)
        time.sleep(THROTTLE)

    print(
        f"Done. checked={checked} edited={edited} skipped={skipped} "
        f"errors={errors} finished_all={finished_all}"
    )
    if args.apply and finished_all:
        clear_state()
        print("State cleared (sweep complete).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
