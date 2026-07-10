#!/usr/bin/env python3
"""Watch for on-wiki attention to ブルーノ・プラス, and record it for `conflict_gate`.

Emma 2026-07-10:

    "Look at the Japanese Wikipedia project chat. Watch the Japanese Wikipedia
    project chat. Watch their talk page. … If any mention of this person occurs
    there, occurs at the Administrators' notice board, or occurs in the Wikiproject
    Japan talk page, or there's any activity on their talk page for anything like
    this, I think that the only sensible thing to do would be this: this thing
    triggers a month-long pause on the editing."

    "My fear with this person is mostly that this person is an LTA who is going to
    get a lot of attention to themselves."

So the trigger is not *their* behaviour — it is **attention to them**. The editor is
active on Wikidata, but Emma named the Japanese-Wikipedia venues too, so both projects
are watched; a superset is cheap and a missed venue is not.

READ-ONLY. This script never edits anything, never posts anywhere, and never names
our operation. It writes `conflict_watch.state` and a report, and that is all.

    python watch_conflicting_editor.py [--json]
"""
import argparse
import datetime
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from conflict_gate import (
    ATTENTION_PAUSE_DAYS,
    WATCHED_USER,
    fetch_last_watched_edit,
    pause_reason,
    resume_date,
)

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "conflict_watch.state")
UA = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"

WIKIDATA = "https://www.wikidata.org/w/api.php"
JAWIKI = "https://ja.wikipedia.org/w/api.php"

# Three venue classes, because Emma gave them three different rules.
#
# (1) The Japanese project chat. Presence of the name -> INDEFINITE hold. Emma:
#     "it has a 90-day expiration on conversations in it … it has a tendency to
#     necro a bit more. If this person's name … is ever present in Japanese
#     Wikipedia Project Chat, then we put it on hold. Just no edits."
PROJECT_CHAT = (JAWIKI, "Wikipedia:井戸端")

# (2) Noticeboards and discussion venues. A mention -> 30 days from the mention.
#     "If there has been a mention of them on the administrators' notice board
#     within the last month, then no editing."
NOTICEBOARDS = [
    (WIKIDATA, "Wikidata:Project chat"),
    (WIKIDATA, "Wikidata:Administrators' noticeboard"),
    (WIKIDATA, "Wikidata:Requests for deletions"),
    (WIKIDATA, "Wikidata talk:WikiProject Japan"),
    (JAWIKI, "Wikipedia:管理者伝言板/荒らし"),
    (JAWIKI, "Wikipedia:管理者伝言板/投稿ブロック"),
    (JAWIKI, "Wikipedia:コメント依頼"),
    (JAWIKI, "プロジェクト‐ノート:日本"),
]

# (3) Their talk pages. ANY activity within a month -> 30 days from that activity.
#     "If there has been any activity within a month on their talk page, then there
#     will be a month of no edits." Note this is activity, not a mention: the name
#     is trivially present on their own talk page, so presence would pin the gate
#     shut for ever.
TALK_PAGES = [
    (WIKIDATA, "User talk:" + WATCHED_USER),
    (JAWIKI, "利用者‐会話:" + WATCHED_USER),
]


def _api(endpoint, params):
    params = dict(params, format="json")
    url = endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def _to_date(ts):
    return datetime.date(int(ts[0:4]), int(ts[5:7]), int(ts[8:10]))


def page_mentions_user(endpoint, title, user=WATCHED_USER):
    """(mentioned?, last_revision_date). A missing page is not a mention."""
    d = _api(endpoint, {"action": "query", "prop": "revisions", "titles": title,
                        "rvprop": "content|timestamp", "rvslots": "main",
                        "rvlimit": 1, "formatversion": 2})
    pages = d.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return False, None
    revs = pages[0].get("revisions", [])
    if not revs:
        return False, None
    text = revs[0].get("slots", {}).get("main", {}).get("content", "") or ""
    return (user in text), _to_date(revs[0]["timestamp"])


def talk_page_activity(endpoint, title):
    """Date of the most recent revision, or None if the page does not exist."""
    d = _api(endpoint, {"action": "query", "prop": "revisions", "titles": title,
                        "rvprop": "timestamp|user|comment", "rvlimit": 5,
                        "formatversion": 2})
    pages = d.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return None, []
    revs = pages[0].get("revisions", [])
    if not revs:
        return None, []
    return _to_date(revs[0]["timestamp"]), [
        (r["user"], r["timestamp"], (r.get("comment") or "")[:60]) for r in revs
    ]


def scan():
    """Everything the gate needs, plus a human-readable trail."""
    findings = {"project_chat_hold": False, "noticeboard_mentions": [],
                "talk_activity": [], "checked": []}

    wiki_of = lambda ep: "wikidata" if ep == WIKIDATA else "jawiki"

    endpoint, title = PROJECT_CHAT
    try:
        mentioned, when = page_mentions_user(endpoint, title)
        findings["project_chat_hold"] = bool(mentioned)
        findings["checked"].append({"wiki": wiki_of(endpoint), "page": title,
                                    "class": "project-chat", "mentioned": mentioned})
    except Exception as exc:
        # Fail closed: an unreachable project chat is treated as a hold, because we
        # cannot show that the name is absent.
        findings["project_chat_hold"] = True
        findings["checked"].append({"wiki": wiki_of(endpoint), "page": title,
                                    "class": "project-chat", "error": str(exc)})

    for endpoint, title in NOTICEBOARDS:
        try:
            mentioned, when = page_mentions_user(endpoint, title)
        except Exception as exc:
            findings["checked"].append({"wiki": wiki_of(endpoint), "page": title,
                                        "class": "noticeboard", "error": str(exc)})
            continue
        findings["checked"].append({"wiki": wiki_of(endpoint), "page": title,
                                    "class": "noticeboard", "mentioned": mentioned})
        if mentioned:
            # The page's last-edited date is an upper bound on when the mention
            # appeared. Conservative: it can only lengthen the pause, never shorten it.
            findings["noticeboard_mentions"].append(
                {"wiki": wiki_of(endpoint), "page": title, "seen": str(when)})
        time.sleep(0.3)

    for endpoint, title in TALK_PAGES:
        try:
            when, revs = talk_page_activity(endpoint, title)
        except Exception as exc:
            findings["checked"].append({"wiki": wiki_of(endpoint), "page": title,
                                        "class": "talk", "error": str(exc)})
            continue
        if when is not None:
            findings["talk_activity"].append(
                {"wiki": wiki_of(endpoint), "page": title, "last_edited": str(when),
                 "recent": revs})
        time.sleep(0.3)

    return findings


def _latest(entries, key):
    dates = [datetime.date.fromisoformat(e[key]) for e in entries]
    return max(dates) if dates else None


def signals(findings):
    """(project_chat_hold, talk_activity, noticeboard_mention)."""
    return (findings["project_chat_hold"],
            _latest(findings["talk_activity"], "last_edited"),
            _latest(findings["noticeboard_mentions"], "seen"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    today = datetime.datetime.now(datetime.timezone.utc).date()
    findings = scan()
    last_edit = fetch_last_watched_edit()
    hold, talk, board = signals(findings)
    resume = resume_date(last_edit, talk, board, hold)

    state = {
        "checked_at": today.isoformat(),
        "watched_user": WATCHED_USER,
        "last_watched_edit": last_edit.isoformat() if last_edit else None,
        "project_chat_hold": hold,
        "talk_activity": talk.isoformat() if talk else None,
        "noticeboard_mention": board.isoformat() if board else None,
        "resume_date": resume.isoformat() if resume else None,
        "findings": findings,
    }
    io.open(STATE_FILE, "w", encoding="utf-8", newline="\n").write(
        json.dumps(state, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    print("Watched user:  {}".format(WATCHED_USER))
    print("Today (UTC):   {}".format(today))
    print("Last edit:     {}".format(last_edit))
    print()
    print("Venues checked:")
    for c in findings["checked"]:
        if "error" in c:
            mark = "?? unreachable"
        else:
            mark = "MENTIONED" if c["mentioned"] else "clean"
        print("  [{:14}] ({:12}) {}:{}".format(mark, c["class"], c["wiki"], c["page"]))
    print()
    if findings["talk_activity"]:
        print("Talk-page activity (any activity counts):")
        for t in findings["talk_activity"]:
            print("  {}:{} last edited {}".format(t["wiki"], t["page"], t["last_edited"]))
            for user, ts, comment in t["recent"][:3]:
                print("      {}  {}  {}".format(ts, user, comment))
    else:
        print("Talk pages: no activity (neither page exists).")
    print()
    print("Signals:")
    print("  jawiki 井戸端 hold      : {}".format("YES — INDEFINITE HOLD" if hold else "no"))
    print("  talk activity          : {}".format(talk or "none"))
    print("  noticeboard mention    : {}".format(board or "none"))
    print("  attention pause length : {} days".format(ATTENTION_PAUSE_DAYS))
    print()
    print("Drip resumes:  {}".format(resume if resume else "INDEFINITELY HELD"))
    reason = pause_reason(today, last_edit, talk, board, hold)
    print(reason if reason else "RUNNING — the gate is open.")
    print("\nwrote {}".format(STATE_FILE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
