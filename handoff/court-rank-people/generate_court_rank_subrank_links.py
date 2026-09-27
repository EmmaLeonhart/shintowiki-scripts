"""
Link each court-rank SUB-RANK item to its parent base rank (Emma 2026-07-23:
"sub-ranks like Junior Eighth Rank, Lower Grade should link to the higher ones").

Decisions (Emma 2026-07-23):
  * link property = P361 (part of) — the base ranks are instances (P31 court
    rank), so part-of fits better than subclass-of.
  * 外従五位上/下 had no base 外従五位 item — CREATE it in this batch and link the
    two upper/lower items to it (via QuickStatements LAST), with 外従五位 itself
    part of 外位 (Q11430321, the outer-rank grouping).

The 24 ordinary sub-ranks (Q140679480…Q140679507) were created 2026-07-23 with
only P31; this adds `<sub> P361 <base>`. QIDs baked in from the create result.

Output: modern-quickstatements/court_rank_subrank_links.txt  (paste-ready QS V1)
One paste: 24 part-of lines, then a CREATE block for 外従五位 + its two links.
Writes only the .txt.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "court_rank_subrank_links.txt")
LINK = "P361"                    # part of
OUTER_GROUP = "Q11430321"        # 外位 — parent of the new 外従五位 base

# ordinary sub-rank QID -> (ja, parent base-rank QID). From the create run.
SUBRANK_PARENT = {
    "Q140679480": ("正四位上", "Q11123338"),
    "Q140679481": ("正四位下", "Q11123338"),
    "Q140679482": ("従四位上", "Q11071127"),
    "Q140679483": ("従四位下", "Q11071127"),
    "Q140679485": ("正五位上", "Q11123280"),
    "Q140679486": ("正五位下", "Q11123280"),
    "Q140679487": ("従五位上", "Q11071125"),
    "Q140679488": ("従五位下", "Q11071125"),
    "Q140679489": ("正六位上", "Q11545372"),
    "Q140679491": ("正六位下", "Q11545372"),
    "Q140679492": ("従六位上", "Q14624983"),
    "Q140679493": ("従六位下", "Q14624983"),
    "Q140679494": ("正七位上", "Q11545345"),
    "Q140679495": ("正七位下", "Q11545345"),
    "Q140679497": ("従七位上", "Q11488718"),
    "Q140679498": ("従七位下", "Q11488718"),
    "Q140679499": ("正八位上", "Q11545368"),
    "Q140679500": ("正八位下", "Q11545368"),
    "Q140679501": ("従八位上", "Q11488720"),
    "Q140679502": ("従八位下", "Q11488720"),
    "Q140679503": ("大初位上", "Q11433041"),
    "Q140679505": ("大初位下", "Q11433041"),
    "Q140679506": ("少初位上", "Q11464527"),
    "Q140679507": ("少初位下", "Q11464527"),
}
# the two whose base (外従五位) is created below and referenced via LAST
GAIJUGOI_UPPER = "Q140679508"    # 外従五位上
GAIJUGOI_LOWER = "Q140679509"    # 外従五位下


def main():
    lines = [f"{q}\t{LINK}\t{parent}" for q, (ja, parent) in SUBRANK_PARENT.items()]

    # create the base 外従五位 item, then link the two upper/lower items to it
    lines += [
        "CREATE",
        'LAST\tLja\t"外従五位"',
        'LAST\tLen\t"Outer Junior Fifth Rank"',
        'LAST\tDen\t"court rank in Japan"',
        'LAST\tDja\t"日本の位階"',
        "LAST\tP31\tQ99196082",
        f"LAST\t{LINK}\t{OUTER_GROUP}",
        f"{GAIJUGOI_UPPER}\t{LINK}\tLAST",
        f"{GAIJUGOI_LOWER}\t{LINK}\tLAST",
    ]

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {len(SUBRANK_PARENT)} part-of links + 外従五位 create block "
          f"(prop={LINK}) -> {OUT}")


if __name__ == "__main__":
    main()
