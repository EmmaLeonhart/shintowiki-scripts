#!/usr/bin/env python3
"""
audit_double_category_qids.py
==============================
Read-only audit of [[Category:Double category qids]]. Companion to
``resolve_double_category_qids.py``: that script handles the easy case
(every linked category redirects to the same final target → replace
the dab page with a plain redirect). This script reports the remaining
hard cases, where two or more linked categories resolve to distinct,
live targets. Those need human judgment about which category should
keep the QID or whether the categories should be merged wiki-side.

Writes a report page at [[Double category QIDs audit]]. For each
unresolved dab, the report lists the linked categories and whether
each currently has members (a proxy for "is this a real live category
or a stale stub?"). Does not edit any page other than the report.

Standard flags: ``--apply`` (default dry-run), ``--max-edits`` (only
the report page is written, default 1), ``--run-tag``.
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

USER_AGENT = "AuditDoubleCategoryQids/1.0 (User:EmmaBot; shinto.miraheze.org)"

SOURCE_CAT = "Double category qids"
REPORT_TITLE = "Double category QIDs audit"

REDIRECT_RE = re.compile(r"#REDIRECT\s*\[\[([^\]]+)\]\]", re.IGNORECASE)
LINK_RE = re.compile(r"\[\[:([^\]]+)\]\]")


def normalize_title(title: str) -> str:
    title = title.split("#")[0]
    title = title.replace("_", " ")
    title = " ".join(title.split())
    return title.strip()


def strip_leading_colon(title: str) -> str:
    return title.lstrip(":")


def resolve_final_target(site, title: str, max_depth: int = 10) -> str:
    seen = set()
    current = normalize_title(strip_leading_colon(title))
    for _ in range(max_depth):
        key = current.casefold()
        if key in seen:
            return current
        seen.add(key)
        try:
            page = site.pages[current]
            text = page.text() if page.exists else ""
        except Exception:
            return current
        if not text:
            return current
        m = REDIRECT_RE.match(text)
        if m is None:
            return current
        current = normalize_title(strip_leading_colon(m.group(1)))
    return current


def count_members(site, category_title: str) -> int:
    """Return the number of members in a category page, or -1 if the
    page does not exist. We don't need an exact count — just "has
    members or not" — so cap the iteration."""
    if not category_title.lower().startswith("category:"):
        return -1
    try:
        page = site.pages[category_title]
        if not page.exists:
            return -1
        count = 0
        for _ in page:  # iterates members
            count += 1
            if count >= 1000:
                return count
        return count
    except Exception:
        return -1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Save the report (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=1,
                        help="Only one write happens; cap exists for parity.")
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    cat = site.categories[SOURCE_CAT]
    dab_pages = [p for p in cat if p.namespace == 0]
    print(f"Scanning {len(dab_pages)} dab pages in [[Category:{SOURCE_CAT}]]")

    resolvable = 0
    unresolvable: list[dict] = []
    errors = 0

    for i, page in enumerate(dab_pages, 1):
        title = page.name
        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"[{i}] {title} ERROR reading: {e}")
            errors += 1
            continue
        if not text:
            continue

        links = LINK_RE.findall(text)
        if len(links) < 2:
            continue

        resolved = [resolve_final_target(site, link) for link in links]
        normalized = {t.casefold() for t in resolved}
        if len(normalized) == 1:
            resolvable += 1
            continue

        # Unresolvable — collect data for the report.
        targets_info = []
        for link, target in zip(links, resolved):
            targets_info.append({
                "raw": link,
                "target": target,
                "members": count_members(site, target),
            })
        unresolvable.append({"dab": title, "targets": targets_info})
        print(f"[{i}] {title}: {len(targets_info)} distinct targets")

    print(f"\nResolvable (same target): {resolvable}")
    print(f"Unresolvable:             {len(unresolvable)}")
    print(f"Errors:                   {errors}")

    # ── Build report ──
    lines = [
        "{{DISPLAYTITLE:Double category QIDs audit}}",
        "Auto-generated by [[User:EmmaBot]] — do not edit manually.",
        "",
        "Dab pages from [[Category:Double category qids]] whose linked "
        "categories resolve to *distinct* live targets. These need human "
        "judgment: decide which category should keep the QID, or merge "
        "the categories wiki-side. The easy cases (all links resolve "
        "to the same target) are auto-fixed by "
        "[[User:EmmaBot]] via ``resolve_double_category_qids.py`` and "
        "do not appear here.",
        "",
        f"* Dab pages scanned: '''{len(dab_pages)}'''",
        f"* Auto-resolvable (same target): '''{resolvable}'''",
        f"* '''Needing human review: {len(unresolvable)}'''",
        "",
    ]

    if unresolvable:
        lines.append("== Needs human review ==")
        lines.append("")
        for entry in sorted(unresolvable, key=lambda e: e["dab"]):
            lines.append(f"=== [[{entry['dab']}]] ===")
            for t in entry["targets"]:
                m = t["members"]
                if m == -1:
                    note = "''missing page''"
                elif m == 0:
                    note = "''empty''"
                else:
                    shown = f"{m}+" if m >= 1000 else str(m)
                    note = f"{shown} member(s)"
                lines.append(f"* ``[[:{t['raw']}]]`` → [[:{t['target']}]] — {note}")
            lines.append("")
    else:
        lines.append("''No entries currently need human review.''")
        lines.append("")

    lines.append("[[Category:Maintenance reports]]")
    report = "\n".join(lines) + "\n"

    if not args.apply:
        print(f"[DRY] would write {len(unresolvable)} entries to [[{REPORT_TITLE}]]")
        return

    page = site.pages[REPORT_TITLE]
    summary = (f"Bot: refresh Double category QIDs audit "
               f"({len(unresolvable)} need review, {resolvable} auto-resolvable) "
               f"{args.run_tag}")
    page.save(report, summary=summary)
    time.sleep(THROTTLE)
    print(f"Saved [[{REPORT_TITLE}]]")


if __name__ == "__main__":
    main()
