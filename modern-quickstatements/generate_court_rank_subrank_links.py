"""
Follow-up to the sub-rank CREATE batch: link each newly-created court-rank
sub-rank item to its parent BASE rank (Emma 2026-07-23: "sub-ranks like Junior
Eighth Rank, Lower Grade should link to the higher ones like Junior Eighth Rank").

The 26 sub-rank items were created 2026-07-23 (Q140679480…Q140679509) with only
P31 = Q99196082; this adds the parent link. QIDs are baked in from the actual
create result (authoritative, and avoids WDQS indexing lag on brand-new items).

LINK_PROP: P279 (subclass of) by default — PENDING Emma's confirm (vs P361 part
of). 外従五位上/下's parent is set to 外位 (Q11430321), where its alias currently
lives — also flagged for Emma (vs 従五位 Q11071125).

Output: modern-quickstatements/court_rank_subrank_links.txt  (paste-ready QS V1)
Writes only the .txt.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "court_rank_subrank_links.txt")
LINK_PROP = "P279"   # PENDING Emma: subclass of (P279) vs part of (P361)

# subrank QID -> (ja label, parent base-rank QID). From the 2026-07-23 create run.
SUBRANK_PARENT = {
    "Q140679480": ("正四位上", "Q11123338"),  # 正四位
    "Q140679481": ("正四位下", "Q11123338"),
    "Q140679482": ("従四位上", "Q11071127"),  # 従四位
    "Q140679483": ("従四位下", "Q11071127"),
    "Q140679485": ("正五位上", "Q11123280"),  # 正五位
    "Q140679486": ("正五位下", "Q11123280"),
    "Q140679487": ("従五位上", "Q11071125"),  # 従五位
    "Q140679488": ("従五位下", "Q11071125"),
    "Q140679489": ("正六位上", "Q11545372"),  # 正六位
    "Q140679491": ("正六位下", "Q11545372"),
    "Q140679492": ("従六位上", "Q14624983"),  # 従六位
    "Q140679493": ("従六位下", "Q14624983"),
    "Q140679494": ("正七位上", "Q11545345"),  # 正七位
    "Q140679495": ("正七位下", "Q11545345"),
    "Q140679497": ("従七位上", "Q11488718"),  # 従七位
    "Q140679498": ("従七位下", "Q11488718"),
    "Q140679499": ("正八位上", "Q11545368"),  # 正八位
    "Q140679500": ("正八位下", "Q11545368"),
    "Q140679501": ("従八位上", "Q11488720"),  # 従八位
    "Q140679502": ("従八位下", "Q11488720"),
    "Q140679503": ("大初位上", "Q11433041"),  # 大初位
    "Q140679505": ("大初位下", "Q11433041"),
    "Q140679506": ("少初位上", "Q11464527"),  # 少初位
    "Q140679507": ("少初位下", "Q11464527"),
    "Q140679508": ("外従五位上", "Q11430321"),  # 外位 (flag: vs 従五位)
    "Q140679509": ("外従五位下", "Q11430321"),
}


def main():
    lines = []
    for sub_qid, (ja, parent) in SUBRANK_PARENT.items():
        lines.append(f"{sub_qid}\t{LINK_PROP}\t{parent}")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {len(lines)} parent links (prop={LINK_PROP}) -> {OUT}")


if __name__ == "__main__":
    main()
