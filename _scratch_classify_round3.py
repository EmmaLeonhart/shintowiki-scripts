"""Classify git_synced/*.wiki files into buckets for round 3.

Buckets:
  a) template      — filename starts with Template%3A
  b) why-comment   — leading <!-- ... --> that is NOT a history-offload
                     system comment AND NOT a prior "Unknown why ..." annotation
  c) unknown-why   — no leading comment, OR only system history-offload,
                     OR only a prior "Unknown why" annotation

Print counts + the comment text from bucket (b) so I can read the
instructions before applying them.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = "git_synced"
HIST_RE = re.compile(r"<!--\s*History offloaded:", re.IGNORECASE)
UNKNOWN_RE = re.compile(r"<!--\s*Unknown why this page was added", re.IGNORECASE)
LEADING_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)

results = {"template": [], "unknown-why": [], "why-comment": []}
why_comments = {}

for fn in sorted(os.listdir(ROOT)):
    if not fn.endswith(".wiki"):
        continue
    path = os.path.join(ROOT, fn)
    if fn.startswith("Template%3A"):
        results["template"].append(fn)
        continue

    with open(path, "r", encoding="utf-8") as f:
        head = f.read(8192)

    # Walk leading comments in order; first non-system non-unknown comment is the why-comment
    pos = 0
    text = head
    found_why = None
    while True:
        # Skip leading whitespace
        while pos < len(text) and text[pos] in (" ", "\t", "\r", "\n"):
            pos += 1
        if pos >= len(text) or not text[pos:pos + 4].startswith("<!--"):
            break
        # Find end of this comment
        end = text.find("-->", pos)
        if end == -1:
            break
        comment = text[pos:end + 3]
        if HIST_RE.search(comment):
            pos = end + 3
            continue  # system comment, skip past it
        if UNKNOWN_RE.search(comment):
            pos = end + 3
            continue  # prior unknown-why, treat as no why
        # Real why-comment
        found_why = comment
        break

    if found_why is not None:
        results["why-comment"].append(fn)
        why_comments[fn] = found_why
    else:
        results["unknown-why"].append(fn)

print("=== Bucket counts ===")
for k, v in results.items():
    print(f"  {k}: {len(v)}")
print(f"  TOTAL: {sum(len(v) for v in results.values())}")

print()
print("=== why-comment files (instructions) ===")
for fn in results["why-comment"]:
    print(f"--- {fn} ---")
    print(why_comments[fn])
    print()
