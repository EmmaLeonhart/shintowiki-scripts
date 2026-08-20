"""Inject time-gated items into queue.md and [[Open questions]] on their due date.

Emma, 2026-08-20, on a decision she did not want to make yet:

    "it waits until September 1, and waiting means you write a script that injects it by a
     json into the queue or open questions at a certain date and the date is Sept 21, so
     write that thing, because it being visible in the queue as 'parked' adds clutter, and
     other time gated stuff also goes into this, github actions injects on that day into
     open questions and the queue"

So a deferred item does not sit in the queue wearing a PARKED label until its date comes
round. It lives in `scheduled_items.json` and appears in the queue on the day it becomes
workable -- which is also the only day anyone can act on it.

IDEMPOTENCE, and why it is not the json flag. Each injection writes a marker comment into
the target text, and the marker is what decides whether an item has already landed. The
`injected` field in the json is a record, not the guard. That ordering matters: the json is
a tracked file someone can revert, rewrite, or resolve a merge conflict in, and every one of
those would re-fire an item whose guard lived only there. The marker travels with the thing
it protects.

Deliberately NOT here: any notion of chasing. Nothing re-surfaces an injected item, nothing
dates it after the fact, and an item that lands and sits is not this script's business.

Usage:
    python scheduled/inject_due_items.py [--today YYYY-MM-DD] [--dry-run]

`--today` exists for tests and for a manual backfill; it never reads a clock other than the
one it is given.
"""
import argparse
import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STORE = os.path.join(HERE, "scheduled_items.json")

TARGETS = {
    "queue": os.path.join(ROOT, "queue.md"),
    "open-questions": os.path.join(ROOT, "git_synced", "Open questions.wiki"),
}

# The wiki section the injector owns. It appends here rather than into "Wiki-based queue",
# which is Emma's own surface for wiki-side work -- a scheduled CI item is not that, and
# writing into her section would make the two indistinguishable.
WIKI_SECTION = "== Scheduled items =="
WIKI_SECTION_BLURB = (
    "''Injected automatically on each item's due date by "
    "<code>scheduled/inject_due_items.py</code>. Nothing here was visible in "
    "<code>queue.md</code> before today -- that is the point of it. Delete an item once it is "
    "settled; nothing re-adds it.''"
)


def marker(item_id):
    return "<!-- scheduled:%s -->" % item_id


def load(path=None):
    """Read the store.

    `path=None` rather than `path=STORE`: a default argument binds at import time, so with
    the constant as the default this function would keep reading the original file even
    after STORE was repointed -- and it would do it while main() wrote to the NEW one. That
    split sent a test run's output into the real `Open questions` page.
    """
    with io.open(path or STORE, encoding="utf-8") as fh:
        return json.load(fh)


def due_items(data, today):
    """Items whose date has arrived. `today` is a datetime.date."""
    out = []
    for item in data.get("items", []):
        try:
            when = datetime.date.fromisoformat(item["due"])
        except (KeyError, ValueError):
            raise ValueError("item %r has a missing or malformed 'due'" % item.get("id"))
        if when <= today:
            out.append(item)
    return out


def already_present(text, item_id):
    return marker(item_id) in text


def render_md(item):
    body = "\n".join(item.get("body_md") or [])
    return "%s\n%s\n\n" % (marker(item["id"]), body)


def render_wiki(item):
    body = "\n".join(item.get("body_wiki") or [])
    if not body.strip():
        return ""
    return "%s\n%s\n\n" % (marker(item["id"]), body)


def inject_queue(text, item):
    """Insert before the item's anchor heading, or append if it is not found.

    An anchor that has been renamed must not silently drop the item on the floor, so a
    missing anchor appends rather than skipping.
    """
    block = render_md(item)
    anchor = item.get("queue_anchor")
    if anchor and anchor in text:
        i = text.index(anchor)
        return text[:i] + block + text[i:], "before %r" % anchor
    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + block, "appended (anchor not found)"


def inject_wiki(text, item):
    block = render_wiki(item)
    if not block:
        return text, "no wiki body -- skipped"
    if WIKI_SECTION in text:
        i = text.index(WIKI_SECTION) + len(WIKI_SECTION)
        # Land after the section heading and its blurb paragraph, before existing items.
        rest = text[i:]
        offset = len(rest) - len(rest.lstrip("\n"))
        head = rest[:offset]
        return text[:i] + head + block + rest[offset:], "into %r" % WIKI_SECTION
    section = "\n%s\n\n%s\n\n%s" % (WIKI_SECTION, WIKI_SECTION_BLURB, block)
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + section, "created %r" % WIKI_SECTION


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--today", help="ISO date to treat as today (tests, manual backfill)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.date.today())
    data = load()
    due = due_items(data, today)
    if not due:
        print("nothing due as of %s (%d scheduled)" % (today, len(data.get("items", []))))
        return 0

    changed_files, injected = {}, []
    for item in due:
        for target in item.get("targets", []):
            path = TARGETS.get(target)
            if path is None:
                print("  ! unknown target %r on %s -- skipped" % (target, item["id"]))
                continue
            text = changed_files.get(path)
            if text is None:
                text = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if already_present(text, item["id"]):
                print("  = %-38s %-15s already present" % (item["id"], target))
                continue
            if target == "queue":
                text, how = inject_queue(text, item)
            else:
                text, how = inject_wiki(text, item)
            changed_files[path] = text
            injected.append((item["id"], target, how))
            print("  + %-38s %-15s %s" % (item["id"], target, how))
        item["injected"] = today.isoformat()

    if args.dry_run:
        print("\n%d injection(s) [DRY RUN -- nothing written]" % len(injected))
        return 0

    for path, text in changed_files.items():
        io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    if changed_files:
        with io.open(STORE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    print("\n%d injection(s) across %d file(s)" % (len(injected), len(changed_files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
