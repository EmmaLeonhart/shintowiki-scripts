"""
migrate_talk_pages.py
=====================
Rebuilds shintowiki talk pages into a clean structure, with optional imports from
Japanese and English Wikipedia talk pages.

Default mode is dry-run. Use --apply to save edits.

Examples:
    python shinto_miraheze/migrate_talk_pages.py --limit 25
    python shinto_miraheze/migrate_talk_pages.py --titles "Ise Grand Shrine,Izumo-taisha" --apply
    python shinto_miraheze/migrate_talk_pages.py --titles-file titles.txt --apply
"""

import argparse
import datetime as dt
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
THROTTLE = 1.5

QID_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)\s*[\|\}]", re.IGNORECASE)
INTERWIKI_RE = {
    "ja": re.compile(r"\[\[\s*:?\s*ja\s*:\s*([^\]\|#]+)", re.IGNORECASE),
    "en": re.compile(r"\[\[\s*:?\s*en\s*:\s*([^\]\|#]+)", re.IGNORECASE),
}
LOCAL_DISCUSSION_RE = re.compile(
    r"(?is)^==\s*Local discussion\s*==\s*(.*?)(?=^==\s*[^=].*?\s*==\s*$|\Z)",
    re.MULTILINE,
)
QPAGE_RE = re.compile(r"^Q\d+$")


def fetch_json(url, params):
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "TalkPageMigrationBot/1.0 (User:Immanuelle; shinto.miraheze.org)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_qid(page_text):
    m = QID_RE.search(page_text or "")
    return m.group(1).upper() if m else None


def extract_interwiki_title(page_text, lang):
    m = INTERWIKI_RE[lang].search(page_text or "")
    if not m:
        return None
    return m.group(1).strip().replace("_", " ")


def get_sitelinks_from_wikidata(qid):
    data = fetch_json(
        "https://www.wikidata.org/w/api.php",
        {
            "action": "wbgetentities",
            "ids": qid,
            "props": "sitelinks",
            "format": "json",
        },
    )
    entity = data.get("entities", {}).get(qid, {})
    sitelinks = entity.get("sitelinks", {})
    ja_title = sitelinks.get("jawiki", {}).get("title")
    en_title = sitelinks.get("enwiki", {}).get("title")
    return ja_title, en_title


def fetch_wikipedia_talk_content(lang, article_title):
    if not article_title:
        return None
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    talk_title = f"Talk:{article_title}"
    data = fetch_json(
        api_url,
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "ids|content",
            "rvslots": "main",
            "titles": talk_title,
            "formatversion": "2",
            "format": "json",
        },
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    page = pages[0]
    if page.get("missing"):
        return None
    rev = (page.get("revisions") or [{}])[0]
    text = rev.get("slots", {}).get("main", {}).get("content", "")
    if not text.strip():
        return None
    return {
        "title": article_title,
        "talk_title": talk_title,
        "revid": rev.get("revid"),
        "text": text.rstrip(),
    }


def get_local_discussion_block(existing_talk_text):
    m = LOCAL_DISCUSSION_RE.search(existing_talk_text or "")
    if not m:
        return ""
    return m.group(1).strip()


def build_talk_text(base_title, local_discussion, ja_data, en_data, run_date):
    parts = []
    parts.append("{{talk page header}}")
    parts.append("")
    parts.append("<!-- This talk page covers the main article and all associated namespace layers -->")
    parts.append(
        f"<!-- Imported from Japanese/English Wikipedia talk pages on {run_date} (UTC) when available. -->"
    )
    parts.append("")
    parts.append("== Local discussion ==")
    if local_discussion:
        parts.append(local_discussion)
    else:
        parts.append("<!-- Add local discussion below this line. -->")
    parts.append("")

    if ja_data:
        parts.append(f"== Imported from Japanese Wikipedia ({run_date}) ==")
        parts.append(f"<!-- Source: ja:{ja_data['talk_title']} | revid={ja_data['revid']} -->")
        parts.append(ja_data["text"])
        parts.append("")

    if en_data:
        parts.append(f"== Imported from English Wikipedia ({run_date}) ==")
        parts.append(f"<!-- Source: en:{en_data['talk_title']} | revid={en_data['revid']} -->")
        parts.append(en_data["text"])
        parts.append("")

    if not ja_data and not en_data:
        parts.append("== Initial import ==")
        parts.append("<!-- No source talk page found on ja/en Wikipedia at migration time. -->")
        parts.append("")

    parts.append("<!-- Dummy comment to avoid immediate auto-archive of a fresh page. -->")
    return "\n".join(parts).rstrip() + "\n"


def iter_mainspace_titles(site, start_title=None):
    params = {
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": "max",
        "apfilterredir": "nonredirects",
    }
    if start_title:
        params["apfrom"] = start_title

    while True:
        result = site.api("query", **params)
        for entry in result["query"]["allpages"]:
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def parse_titles_arg(titles_arg):
    if not titles_arg:
        return []
    return [t.strip() for t in titles_arg.split(",") if t.strip()]


def parse_titles_file(path):
    titles = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                titles.append(s)
    return titles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Save edits (default is dry-run).")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process (0 = no limit).")
    parser.add_argument("--start-title", default="", help="Start title for all-mainspace mode.")
    parser.add_argument("--titles", default="", help="Comma-separated mainspace titles to process.")
    parser.add_argument("--titles-file", default="", help="Path to newline-delimited titles file.")
    parser.add_argument(
        "--fallback-same-title",
        action="store_true",
        help="If no ja/en mapping is found, try same title on ja/en Wikipedia.",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Overwrite even if the talk page already appears migrated.",
    )
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="TalkPageMigrationBot/1.0 (User:Immanuelle; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    explicit_titles = []
    explicit_titles.extend(parse_titles_arg(args.titles))
    if args.titles_file:
        explicit_titles.extend(parse_titles_file(args.titles_file))
    explicit_titles = list(dict.fromkeys(explicit_titles))

    if explicit_titles:
        titles_iter = iter(explicit_titles)
        print(f"Processing explicit title list: {len(explicit_titles)} titles")
    else:
        titles_iter = iter_mainspace_titles(site, start_title=args.start_title or None)
        print("Processing all non-redirect mainspace pages")

    run_date = dt.datetime.utcnow().strftime("%Y-%m-%d")
    processed = edited = skipped = errors = 0

    for title in titles_iter:
        if args.limit and processed >= args.limit:
            break
        if QPAGE_RE.match(title):
            continue

        processed += 1
        page = site.pages[title]
        talk_page = site.pages[f"Talk:{title}"]
        prefix = f"[{processed}] {title}"

        try:
            page_text = page.text() if page.exists else ""
            talk_text = talk_page.text() if talk_page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading page/talk page: {e}")
            errors += 1
            continue

        if (
            not args.force_overwrite
            and "{{talk page header}}" in (talk_text or "")
            and "<!-- Imported from Japanese/English Wikipedia talk pages on " in (talk_text or "")
        ):
            print(f"{prefix} SKIP (already migrated marker found)")
            skipped += 1
            continue

        qid = extract_qid(page_text)
        ja_title = en_title = None
        if qid:
            try:
                ja_title, en_title = get_sitelinks_from_wikidata(qid)
            except Exception as e:
                print(f"{prefix} WARN wikidata lookup failed for {qid}: {e}")

        if not ja_title:
            ja_title = extract_interwiki_title(page_text, "ja")
        if not en_title:
            en_title = extract_interwiki_title(page_text, "en")
        if args.fallback_same_title:
            ja_title = ja_title or title
            en_title = en_title or title

        try:
            ja_data = fetch_wikipedia_talk_content("ja", ja_title) if ja_title else None
        except Exception as e:
            print(f"{prefix} WARN ja talk fetch failed ({ja_title}): {e}")
            ja_data = None
        try:
            en_data = fetch_wikipedia_talk_content("en", en_title) if en_title else None
        except Exception as e:
            print(f"{prefix} WARN en talk fetch failed ({en_title}): {e}")
            en_data = None

        local_discussion = get_local_discussion_block(talk_text)
        new_talk_text = build_talk_text(title, local_discussion, ja_data, en_data, run_date)
        if (talk_text or "").rstrip() == new_talk_text.rstrip():
            print(f"{prefix} SKIP (no change)")
            skipped += 1
            continue

        source_bits = []
        if ja_data:
            source_bits.append(f"ja:{ja_data['title']}")
        if en_data:
            source_bits.append(f"en:{en_data['title']}")
        source_label = ", ".join(source_bits) if source_bits else "no ja/en source"

        if args.apply:
            try:
                talk_page.save(
                    new_talk_text,
                    summary=(
                        f"Bot: migrate talk page structure; import discussion seed ({source_label}); "
                        "add local discussion section + dated import note"
                    ),
                )
                edited += 1
                print(f"{prefix} EDITED ({source_label})")
                time.sleep(THROTTLE)
            except Exception as e:
                print(f"{prefix} ERROR saving talk page: {e}")
                errors += 1
        else:
            print(f"{prefix} DRY RUN would edit ({source_label})")

    print("\n" + "=" * 60)
    print(
        f"Done. Processed: {processed} | Edited: {edited} | "
        f"Skipped: {skipped} | Errors: {errors} | Mode: {'APPLY' if args.apply else 'DRY-RUN'}"
    )


if __name__ == "__main__":
    main()
