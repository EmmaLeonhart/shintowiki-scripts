#!/usr/bin/env python3
"""Has Emma's Wikidata account (Immanuelle) edited since the last check?

Read-only. Emma, 2026-10-03: she hand-runs the QuickStatements home-page batch; once her
account stops editing, the batch is finished and the generators should be re-run so the
page holds the next batch. Local session crons call this on her schedule (22:10, then every
10 min for an hour, every 30 min for four hours, hourly for a week).

State in `edit_watch.state` (JSON): last_seen (newest edit timestamp seen), last_check,
done. Prints exactly one of:
    SKIP            done already, or a check ran under 5 minutes ago
    STILL_EDITING   a newer edit than last_seen exists (last_seen updated)
    STOPPED         no edit since last_seen; the caller re-runs the pipeline
"""
import datetime
import json
import os
import sys

import requests

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edit_watch.state")
UA = ("shintowiki-scripts/1.0 (https://github.com/emmaleonhart/shintowiki-scripts) "
      "read-only usercontribs check")
USER = "Immanuelle"


def main():
    with open(STATE, encoding="utf-8") as f:
        st = json.load(f)
    now = datetime.datetime.now(datetime.timezone.utc)
    if st.get("done"):
        print("SKIP (pipeline already re-run at %s)" % st.get("done_at"))
        return
    if st.get("last_check"):
        last = datetime.datetime.fromisoformat(st["last_check"])
        if (now - last).total_seconds() < 300:
            print("SKIP (checked %s)" % st["last_check"])
            return
    r = requests.get("https://www.wikidata.org/w/api.php", params=dict(
        action="query", list="usercontribs", ucuser=USER, uclimit=1,
        ucprop="timestamp", format="json"), headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    contribs = r.json()["query"]["usercontribs"]
    newest = contribs[0]["timestamp"] if contribs else ""
    st["last_check"] = now.isoformat()
    if newest > st["last_seen"]:
        print("STILL_EDITING newest=%s previous=%s" % (newest, st["last_seen"]))
        st["last_seen"] = newest
    else:
        print("STOPPED newest=%s (no edit since last_seen)" % newest)
        st["done"] = True
        st["done_at"] = now.isoformat()
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
