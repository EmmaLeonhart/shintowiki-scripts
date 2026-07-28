"""
Prefectural shrine-association (神社庁) website links → P973 (described at URL).

There is NO dedicated Wikidata external-ID property for the prefectural jinjacho
databases (searched 2026-07-24), so — per Emma — link each shrine to its jinjacho
page with P973 (described at URL, datatype=url). The shrine→URL resolution is already
done in the private `jinjacho` repo, subtree-merged here as jinjacho/shrines_and_websites.csv
(columns: shrine entity-URL, shrineLabel, website).

Emits  QID|P973|"<url>"  — add-only; the daily editor skips a statement that already
exists, so this static snapshot is a no-op once landed (re-generate from a refreshed
CSV to add more). Output: modern-quickstatements/jinjacho_p973.txt
"""

import os
import csv
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JINJACHO = os.path.join(os.path.dirname(HERE), "jinjacho")
# Two sources, same three columns. The first is the hand-built 88-row sample that
# shipped 2026-07-24; the second is grown by crawl_jinjacho_shrines.py ->
# match_jinjacho_shrines.py. Absent second file = the original behaviour.
CSVS = [
    os.path.join(JINJACHO, "shrines_and_websites.csv"),
    os.path.join(JINJACHO, "crawled_shrines_matched.csv"),
]
OUT = os.path.join(HERE, "jinjacho_p973.txt")
QID_RE = re.compile(r"(Q\d+)")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    lines, seen = [], set()
    for path in CSVS:
        if not os.path.exists(path):
            continue
        n0 = len(lines)
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                m = QID_RE.search(row.get("shrine", "") or "")
                url = (row.get("website", "") or "").strip()
                if not m or not url.startswith("http"):
                    continue
                key = (m.group(1), url)
                if key in seen:
                    continue
                seen.add(key)
                esc = url.replace('"', '%22')
                lines.append(f'{m.group(1)}|P973|"{esc}"')
        print(f"  {len(lines) - n0:5d} from {os.path.basename(path)}")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} P973 links -> {OUT}")
    for ln in lines[:6]:
        print("  ", ln)


if __name__ == "__main__":
    main()
