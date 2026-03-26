#!/usr/bin/env python3
"""Update User:EmmaBot with the current pipeline run status."""

import datetime as dt
import json
import os
import argparse
import re
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
IMMEDIATE_START = "<!-- BOT-IMMEDIATE:START -->"
IMMEDIATE_END = "<!-- BOT-IMMEDIATE:END -->"
TODO_PATH = os.getenv("WIKI_TODO_PATH", "todo.md")


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


def build_status_block(workflow_status=None, stage=None):
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
    ]
    if workflow_status:
        lines.append(f"* Workflow status: '''{workflow_status}'''")
    if stage:
        lines.append(f"* Current stage: '''{stage}'''")
    lines.extend([
        f"* Last pipeline start (UTC): {now_utc}",
        f"* Trigger: {trigger_summary}",
    ])
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


def md_inline_to_wiki(text):
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"[\2 \1]", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"'''\1'''", text)
    return text


def extract_immediate_items_from_todo(path):
    todo_text = Path(path).read_text(encoding="utf-8")
    lines = todo_text.splitlines()

    in_section = False
    items = []
    for raw in lines:
        line = raw.rstrip()
        if not in_section:
            if line.strip().lower() == "## immediate / in progress":
                in_section = True
            continue

        if line.startswith("## "):
            break
        if not line.strip() or line.strip() == "---":
            continue

        m = re.match(r"^\s*-\s*\[( |x|X)\]\s*(.+)$", line)
        if m:
            items.append(f"* {md_inline_to_wiki(m.group(2).strip())}")
            continue

        m2 = re.match(r"^\s*-\s+(.+)$", line)
        if m2:
            items.append(f"* {md_inline_to_wiki(m2.group(1).strip())}")

    if not items:
        items.append("* No immediate tasks listed in TODO.md")
    return "\n".join(items)


def merge_base_and_immediate(base_text, immediate_text):
    if IMMEDIATE_START not in base_text or IMMEDIATE_END not in base_text:
        raise RuntimeError("EmmaBot.wiki is missing BOT-IMMEDIATE markers.")

    before = base_text.split(IMMEDIATE_START, 1)[0].rstrip()
    after = base_text.split(IMMEDIATE_END, 1)[1].lstrip()
    block = f"{IMMEDIATE_START}\n{immediate_text}\n{IMMEDIATE_END}"
    merged = f"{before}\n{block}\n\n{after}".strip()
    return merged + "\n"


def update_stage_only(site, stage_text, run_tag):
    """Lightweight update: only replace the status block on the live wiki page."""
    page = site.pages[STATUS_PAGE]
    current = page.text()
    if START_MARKER not in current or END_MARKER not in current:
        print("WARNING: status markers not found on wiki page; skipping stage update.")
        return

    before = current.split(START_MARKER, 1)[0].rstrip()
    after = current.split(END_MARKER, 1)[1].lstrip()

    # Rebuild the status block but keep most lines, just insert/replace the stage line
    old_block = current.split(START_MARKER, 1)[1].split(END_MARKER, 1)[0]
    new_lines = []
    stage_added = False
    for line in old_block.splitlines():
        if line.startswith("* Current stage:"):
            continue  # drop old stage line
        new_lines.append(line)
        if line.startswith("* Workflow status:") and not stage_added:
            new_lines.append(f"* Current stage: '''{stage_text}'''")
            stage_added = True

    # If there was no workflow status line, append stage at end
    if not stage_added:
        new_lines.append(f"* Current stage: '''{stage_text}'''")

    new_block = "\n".join(new_lines)
    merged = f"{before}\n{START_MARKER}{new_block}{END_MARKER}\n\n{after}".strip() + "\n"
    page.save(merged, summary=f"Bot: stage → {stage_text} {run_tag}")
    print(f"Updated stage: {stage_text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tag", required=True, help="Wiki-formatted run tag link for edit summaries.")
    parser.add_argument("--status", choices=["active", "inactive"], default=None,
                        help="Set workflow status to active or inactive.")
    parser.add_argument("--stage", default=None,
                        help="Lightweight update: set current stage on the wiki page without rebuilding.")
    args = parser.parse_args()

    if not PASSWORD:
        raise RuntimeError("WIKI_PASSWORD must be set")

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="BotStatusUpdater/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)

    # Lightweight stage-only update — skip the full page rebuild
    if args.stage and not args.status:
        update_stage_only(site, args.stage, args.run_tag)
        return

    base_path = Path(BASE_PAGE_PATH)
    if not base_path.exists():
        raise FileNotFoundError(f"Template page file not found: {base_path}")
    base_text = base_path.read_text(encoding="utf-8")
    immediate_text = extract_immediate_items_from_todo(TODO_PATH)
    page_text_with_immediate = merge_base_and_immediate(base_text, immediate_text)

    status_block = build_status_block(workflow_status=args.status, stage=args.stage)
    new_text = merge_base_and_status(page_text_with_immediate, status_block)
    page = site.pages[STATUS_PAGE]
    status_label = f" ({args.status})" if args.status else ""
    page.save(new_text, summary=f"Bot: update pipeline run status{status_label} {args.run_tag}")
    print(f"Updated {STATUS_PAGE}{status_label}")


if __name__ == "__main__":
    main()
