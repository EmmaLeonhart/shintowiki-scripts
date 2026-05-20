#!/usr/bin/env python3
"""
consume_remote_queue.py
========================
Drains ``remote_queue.json``. Picks N items from the queue, calls Claude
via the Anthropic API to apply each item's per-file instruction, writes
the result back to the file, and lets the workflow commit + push.

This is the autonomous half of the remote-queue pipeline. The build side
(`remote_queue.py`, run daily by `build-remote-queue.yml`) emits a fresh
queue; this script consumes from it. The downstream wiki-cleanup sync
turns each consumed file into a wiki edit and (for items whose
categories drop) deletes the local file. The next nightly rebuild reflects
that, so done items naturally fall out of the queue.

Selection
---------
A cursor in ``consume_remote_queue.state`` walks the queue. When the
cursor exceeds the queue length it resets to 0. The queue rebuilds
daily, so cycling through is fine — items that got fixed don't reappear.

Output contract for Claude
--------------------------
The model receives a cached system prompt explaining it is editing a
local wiki source file, plus the item's per-file instruction and the
file's current contents. It must return ONLY the new file contents — no
preamble, no code fences, no commentary. If the instruction does not
apply, it returns the input verbatim.

Failure modes
-------------
- Empty / refusal response       → skip, log, do not write
- Identical to input             → skip, log, advance cursor
- API error (rate limit, 5xx)    → bail; SDK has already retried 2x
- File missing                   → skip (race with wiki-cleanup sync that
                                    deletes local files when category leaves)

Standard CLI flags: ``--apply`` (default dry-run), ``--max-edits``,
``--run-tag``. ``--run-tag`` is unused locally (no wiki edit happens
here) but accepted for parity with the rest of the script fleet.
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path

import anthropic

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent
QUEUE_PATH = REPO_ROOT / "remote_queue.json"
STATE_PATH = REPO_ROOT / "consume_remote_queue.state"
DEFAULT_MAX_EDITS = 3
MAX_CAP = 20

MODEL = "claude-opus-4-7"
MAX_TOKENS = 64000

SYSTEM_PROMPT = """You are editing a local wiki source file in the shintowiki-scripts repository.

The user message contains:
1. A per-file instruction describing the change to make.
2. The current contents of the file, delimited by `<<<FILE>>>` and `<<<END FILE>>>`.

Return ONLY the new file contents. No preamble, no code fences, no commentary, no `<<<FILE>>>` markers — just the raw wiki text. If the instruction does not apply to this file (e.g. the page doesn't have the structure the instruction targets), return the file's current contents verbatim.

Wiki conventions to honor:
- Preserve all `{{ill|...}}`, `{{jalink|...}}`, `{{nihongo|...}}`, `{{wikidata link|...}}`, `{{translated page|...}}` template calls verbatim unless the instruction explicitly tells you to modify them.
- Preserve `<ref>...</ref>` blocks verbatim.
- Preserve auto-generated blocks delimited by `<!-- BEGIN: ... -->` / `<!-- END: ... -->` markers.
- Categories at the bottom of the file (`[[Category:Foo]]`) are load-bearing — only remove a category if the instruction explicitly says to.
"""


def load_queue() -> list[dict]:
    if not QUEUE_PATH.is_file():
        return []
    data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    return data.get("items", [])


def load_cursor() -> int:
    if not STATE_PATH.is_file():
        return 0
    try:
        return int(STATE_PATH.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0


def save_cursor(cursor: int) -> None:
    STATE_PATH.write_text(f"{cursor}\n", encoding="utf-8")


def call_claude(client: anthropic.Anthropic, instruction: str, file_text: str) -> str:
    """Send one item to Claude and return the new file contents."""
    user_content = (
        f"{instruction}\n\n"
        f"<<<FILE>>>\n{file_text}\n<<<END FILE>>>"
    )
    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        final = stream.get_final_message()
    parts = [b.text for b in final.content if b.type == "text"]
    return "".join(parts).strip("\n") + "\n"


def process_item(
    client: anthropic.Anthropic,
    item: dict,
    apply: bool,
) -> tuple[str, str]:
    """Process one queue item. Returns (status, message)."""
    rel = item["file"]
    path = REPO_ROOT / rel
    if not path.is_file():
        return ("skipped", f"file missing: {rel} (already drained by sync?)")
    original = path.read_text(encoding="utf-8")
    instruction = item["instruction"]

    try:
        new_text = call_claude(client, instruction, original)
    except anthropic.RateLimitError as e:
        return ("error", f"rate limited: {e}")
    except anthropic.APIStatusError as e:
        return ("error", f"API error {e.status_code}: {e.message}")

    if not new_text.strip():
        return ("skipped", "model returned empty content")
    if new_text == original:
        return ("skipped", "model returned identical content")

    if apply:
        path.write_text(new_text, encoding="utf-8")
        return ("edited", f"wrote {len(new_text)} bytes")
    return ("would-edit", f"{len(new_text)} bytes (dry-run)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually write files (default: dry run)")
    ap.add_argument("--max-edits", type=int, default=DEFAULT_MAX_EDITS,
                    help=f"items to process this run (default {DEFAULT_MAX_EDITS}, cap {MAX_CAP})")
    ap.add_argument("--run-tag", default="", help="accepted for parity with other scripts; unused")
    args = ap.parse_args()

    n = max(1, min(args.max_edits, MAX_CAP))
    queue = load_queue()
    if not queue:
        print("queue is empty; nothing to do")
        return 0

    cursor = load_cursor()
    if cursor >= len(queue):
        cursor = 0
        print(f"cursor reset to 0 (queue length {len(queue)})")

    client = anthropic.Anthropic()

    selected = queue[cursor:cursor + n]
    print(f"processing {len(selected)} items starting at cursor {cursor} of {len(queue)}")
    counts = {"edited": 0, "would-edit": 0, "skipped": 0, "error": 0}

    for i, item in enumerate(selected):
        idx = cursor + i
        status, msg = process_item(client, item, args.apply)
        counts[status] += 1
        print(f"[{idx}/{len(queue)}] {status}: {item['file']} — {msg}")
        if status == "error":
            print("bailing on first error; not advancing cursor past it")
            save_cursor(idx)
            return 1

    new_cursor = cursor + len(selected)
    save_cursor(new_cursor)
    print(f"cursor advanced {cursor} -> {new_cursor}")
    print(f"summary: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
