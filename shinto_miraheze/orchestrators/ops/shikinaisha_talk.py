"""
shikinaisha_talk op
====================
For every mainspace page in ``[[Category:Wikidata generated shikinaisha pages]]``,
adds a "==This page was generated from Wikidata==" section to the
corresponding talk page, citing the QID pulled from the page's
``{{wikidata link|Q…}}`` template.

Ported from ``shinto_miraheze/tag_shikinaisha_talk_pages.py``. The
standalone script used ``site.categories[...]`` to iterate category
members directly; this op piggybacks on the mainspace-orchestrator's
existing allpages walk and does the category-membership check against
the page text we already fetched. Skipping pages not in the category
is a cheap substring check, not an API call.

Heavy op (``HANDLES_SAVE = True``) because the edit lands on the
TALK page, not on the visited mainspace page. The orchestrator's
refetch-after-heavy-op is harmless — the mainspace page wasn't
touched, it just reads the same bytes back once.
"""

import re
import time

NAME = "shikinaisha_talk"
NAMESPACES = (0,)
HANDLES_SAVE = True

THROTTLE = 2.5

CATEGORY_RE = re.compile(
    r"\[\[\s*Category\s*:\s*Wikidata[ _]generated[ _]shikinaisha[ _]pages\s*\]\]",
    re.IGNORECASE,
)
QID_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)\s*[\|\}]", re.IGNORECASE)
SECTION_RE = re.compile(r"==\s*This page was generated from Wikidata\s*==", re.IGNORECASE)


def _build_section(qid: str | None) -> str:
    link = f"[[d:{qid}]]" if qid else "''(QID not found)''"
    return (
        "\n==This page was generated from Wikidata==\n"
        f"This page was originally generated programmatically from {link} ~~~~\n"
    )


def run(site, page, run_tag: str, apply: bool) -> tuple[bool, str]:
    try:
        text = page.text()
    except Exception as e:
        return False, f"could not read page: {e}"

    if not CATEGORY_RE.search(text):
        return False, ""

    talk_title = f"Talk:{page.name}"
    talk_page = site.pages[talk_title]
    try:
        talk_text = talk_page.text() if talk_page.exists else ""
    except Exception as e:
        return False, f"could not read talk page: {e}"

    if SECTION_RE.search(talk_text):
        return False, "talk page already has generation notice"

    qid_match = QID_RE.search(text)
    qid = qid_match.group(1).upper() if qid_match else None
    new_talk_text = (talk_text.rstrip() + _build_section(qid)).strip() + "\n"

    if not apply:
        return False, f"DRY RUN: would add generation notice to [[{talk_title}]] (qid={qid})"

    summary_tail = f" ([[d:{qid}]])" if qid else ""
    try:
        talk_page.save(
            new_talk_text,
            summary=f"Bot: add Wikidata generation notice{summary_tail} {run_tag}",
        )
    except Exception as e:
        msg = str(e).lower()
        if "nochange" in msg:
            return False, "talk page NOCHANGE (already has section)"
        return False, f"saving talk page failed: {e}"

    time.sleep(THROTTLE)
    return True, f"added generation notice to [[{talk_title}]] (qid={qid})"
