#!/usr/bin/env python3
"""Update User:EmmaBot with the current pipeline run status."""

import datetime as dt
import json
import os
from pathlib import Path

import mwclient

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot@EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
STATUS_PAGE = os.getenv("WIKI_STATUS_PAGE", "User:EmmaBot")
BASE_PAGE_PATH = os.getenv("WIKI_STATUS_TEMPLATE_PATH", "EmmaBot.wiki")
START_MARKER = "<!-- BOT-RUN-STATUS:START -->"
END_MARKER = "<!-- BOT-RUN-STATUS:END -->"


def load_event_data():
    event_path = os.getenv("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        return {}
    try:
        with open(event_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def summarize_trigger(event_name, event):
    if event_name == "push":
        commit = (event.get("head_commit") or {})
        msg = (commit.get("message") or "").strip().splitlines()
        first_line = msg[0] if msg else "(no commit message)"
        short_sha = (os.getenv("GITHUB_SHA", "") or "")[:7]
        return f'push: "{first_line}" ({short_sha})'
    if event_name == "schedule":
        return "scheduled daily run"
    if event_name == "workflow_dispatch":
        actor = os.getenv("GITHUB_ACTOR", "unknown")
        return f"manual run by {actor}"
    return event_name or "unknown"


def build_status_block():
    event_name = os.getenv("GITHUB_EVENT_NAME", "local")
    event = load_event_data()
    now_utc = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    trigger_summary = summarize_trigger(event_name, event)
    run_id = os.getenv("GITHUB_RUN_ID", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    run_url = ""
    if repository and run_id:
        run_url = f"https://github.com/{repository}/actions/runs/{run_id}"

    lines = [
        START_MARKER,
        "== Bot run status ==",
        f"* Last pipeline start (UTC): {now_utc}",
        f"* Trigger: {trigger_summary}",
    ]
    if run_url:
        lines.append(f"* Workflow run: {run_url}")
    lines.append(END_MARKER)
    return "\n".join(lines)


def merge_base_and_status(base_text, status_block):
    text = base_text.strip()
    if START_MARKER in text and END_MARKER in text:
        before = text.split(START_MARKER, 1)[0].rstrip()
        after = text.split(END_MARKER, 1)[1].lstrip()
        merged = f"{before}\n\n{status_block}\n\n{after}".strip()
        return merged + "\n"
    return f"{text}\n\n{status_block}\n"


def main():
    if not PASSWORD:
        raise RuntimeError("WIKI_PASSWORD must be set")

    base_path = Path(BASE_PAGE_PATH)
    if not base_path.exists():
        raise FileNotFoundError(f"Template page file not found: {base_path}")
    base_text = base_path.read_text(encoding="utf-8")

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="BotStatusUpdater/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)

    status_block = build_status_block()
    new_text = merge_base_and_status(base_text, status_block)
    page = site.pages[STATUS_PAGE]
    page.save(new_text, summary="Bot: update pipeline run status")
    print(f"Updated {STATUS_PAGE}")


if __name__ == "__main__":
    main()
