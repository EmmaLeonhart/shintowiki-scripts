#!/usr/bin/env python3
"""
case_collision_report.py
========================
Find paths in the git index that collide on case (e.g.
``Template%3AInfobox Organization.wiki`` and
``Template%3AInfobox organization.wiki`` both tracked separately).
On Windows the filesystem is case-insensitive, so only ONE of each
pair can physically exist on disk; every git op overwrites whichever
variant was last-written, and the index then shows the OTHER one as
"modified" forever — which jams ``git pull --rebase``.

For each collision group the script reports both/all variants, their
blob hashes, blob sizes, and a verdict:

  * "IDENTICAL"   — blob hashes match. Safe to ``git rm --cached`` the
    lower-case variant (or whichever is wrong) with zero data loss.
  * "DIFFERENT"   — blob hashes differ. The two variants have genuinely
    different content; a human has to decide which is canonical before
    one can be removed.

Read-only. Doesn't modify the working tree or index. Stable to re-run.
"""

from __future__ import annotations

import collections
import subprocess
import sys


def list_tracked_files() -> list[tuple[str, str, int]]:
    """Return [(path, blob_sha, size_bytes), ...] from ``git ls-files``."""
    # `-s` gives mode + sha + stage + path; `-z` and `--full-name` are not
    # needed for our purpose. We pair with `cat-file --batch-check` for size.
    out = subprocess.check_output(
        ["git", "ls-files", "-s"], encoding="utf-8"
    )
    entries: list[tuple[str, str]] = []
    for line in out.splitlines():
        # format: "100644 <sha>\t<path>"  (tab-separated path)
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) < 2:
            continue
        sha = parts[1]
        entries.append((path, sha))

    # Bulk-fetch sizes via cat-file --batch-check
    proc = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectsize)"],
        input="\n".join(sha for _, sha in entries),
        capture_output=True, text=True, check=True,
    )
    sizes = [int(s) for s in proc.stdout.splitlines()]
    return [(p, sha, sz) for (p, sha), sz in zip(entries, sizes)]


def find_collisions(
    entries: list[tuple[str, str, int]],
) -> dict[str, list[tuple[str, str, int]]]:
    """Group entries by lowercase path; return only groups with >= 2 members."""
    groups: dict[str, list[tuple[str, str, int]]] = collections.defaultdict(list)
    for path, sha, size in entries:
        groups[path.lower()].append((path, sha, size))
    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}


def format_report(collisions: dict[str, list[tuple[str, str, int]]]) -> str:
    lines: list[str] = []
    lines.append(f"Case-collision report")
    lines.append(f"=====================")
    lines.append("")
    if not collisions:
        lines.append("No case collisions detected. ✓")
        return "\n".join(lines)

    total_files = sum(len(v) for v in collisions.values())
    identical = sum(
        1 for v in collisions.values()
        if len({sha for _, sha, _ in v}) == 1
    )
    different = len(collisions) - identical
    lines.append(f"Collision groups: {len(collisions)}")
    lines.append(f"Files involved:   {total_files}")
    lines.append(f"  IDENTICAL (safe to dedupe): {identical}")
    lines.append(f"  DIFFERENT (needs decision): {different}")
    lines.append("")

    # Group by directory for readability
    by_dir: dict[str, list[list[tuple[str, str, int]]]] = collections.defaultdict(list)
    for variants in collisions.values():
        d = variants[0][0].rsplit("/", 1)[0] if "/" in variants[0][0] else "."
        by_dir[d].append(variants)

    for d in sorted(by_dir):
        lines.append(f"### {d}  ({len(by_dir[d])} groups)")
        lines.append("")
        for variants in sorted(by_dir[d]):
            shas = {sha for _, sha, _ in variants}
            verdict = "IDENTICAL" if len(shas) == 1 else "DIFFERENT"
            lines.append(f"  [{verdict}]")
            for path, sha, size in variants:
                lines.append(f"    {sha[:10]}  {size:>7} B  {path}")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    entries = list_tracked_files()
    collisions = find_collisions(entries)
    report = format_report(collisions)
    print(report)
    return 0 if not collisions else 1


if __name__ == "__main__":
    sys.exit(main())
