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
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from urllib.error import URLError, HTTPError

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "EmmaBot"
PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE = 1.5
DEFAULT_STATE_FILE = "shinto_miraheze/migrate_talk_pages.state"
DEFAULT_LOG_FILE = "shinto_miraheze/migrate_talk_pages.log"
RETRY_SLEEP = 5.0

QID_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)\s*[\|\}]", re.IGNORECASE)
LOCAL_DISCUSSION_RE = re.compile(
    r"(?is)^==\s*Local discussion\s*==\s*(.*?)(?=^==\s*[^=].*?\s*==\s*$|\Z)",
    re.MULTILINE,
)
DUMMY_COMMENT = ":Dummy comment added by script to avoid immediate auto-archive of a fresh page.~~~~"
HEADING_RE = re.compile(r"^\s*=+\s*[^=].*?\s*=+\s*$")
QPAGE_RE = re.compile(r"^Q\d+$")


def fetch_json(url, params):
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    req = urllib.request.Request(
        full_url,
        headers={"User-Agent": "TalkPageMigrationBot/1.0 (User:EmmaBot; shinto.miraheze.org)"},
    )
    last_err = None
    for _attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError) as e:
            last_err = e
            time.sleep(RETRY_SLEEP)
    raise last_err


def make_site():
    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="TalkPageMigrationBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    return site


def load_state(path):
    completed = set()
    if not os.path.exists(path):
        return completed
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
                completed.add(s)
    return completed


def append_state(path, title):
    with open(path, "a", encoding="utf-8") as f:
        f.write(title + "\n")


def append_log(path, data):
    payload = dict(data)
    payload["ts_utc"] = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def extract_qid(page_text):
    m = QID_RE.search(page_text or "")
    return m.group(1).upper() if m else None


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
    simple_title = sitelinks.get("simplewiki", {}).get("title")
    return ja_title, en_title, simple_title


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


def _append_dummy_if_missing(section_lines):
    """Append dummy comment to a section if it doesn't already end with one."""
    i = len(section_lines) - 1
    while i >= 0 and not section_lines[i].strip():
        i -= 1
    if i < 0:
        return section_lines
    if section_lines[i].startswith(":Dummy comment added by script to avoid immediate auto-archive of a fresh page."):
        return section_lines
    return section_lines + [DUMMY_COMMENT]


def inject_dummy_at_section_ends(text):
    """Ensure every heading-delimited section ends with the dummy comment."""
    if not text:
        return text

    lines = text.splitlines()
    out = []
    section = []
    in_section = False

    for line in lines:
        if HEADING_RE.match(line):
            if in_section:
                out.extend(_append_dummy_if_missing(section))
                section = []
            out.append(line)
            in_section = True
            continue
        if in_section:
            section.append(line)
        else:
            out.append(line)

    if in_section:
        out.extend(_append_dummy_if_missing(section))

    return "\n".join(out).rstrip()


def build_talk_text(base_title, local_discussion, ja_data, en_data, simple_data, run_date):
    parts = []
    parts.append("{{talk page header}}")
    parts.append("")
    parts.append("<!-- This talk page covers the main article and all associated namespace layers -->")
    parts.append(
        f"<!-- Imported from Japanese/English/Simple English Wikipedia talk pages on {run_date} (UTC) when available. -->"
    )
    parts.append("")
    parts.append("== Local discussion ==")
    parts.append(DUMMY_COMMENT)
    if local_discussion:
        parts.append(local_discussion)
    else:
        parts.append("<!-- Add local discussion below this line. -->")
    parts.append("")

    if ja_data:
        ja_rev_link = (
            f"https://ja.wikipedia.org/wiki/Special:PermanentLink/{ja_data['revid']}"
            if ja_data.get("revid")
            else ""
        )
        ja_heading = (
            f"== Imported from Japanese Wikipedia ({run_date}, [{ja_rev_link} revision]) =="
            if ja_rev_link
            else f"== Imported from Japanese Wikipedia ({run_date}) =="
        )
        parts.append(ja_heading)
        parts.append(DUMMY_COMMENT)
        parts.append(f"<!-- Source: ja:{ja_data['talk_title']} | revid={ja_data['revid']} -->")
        parts.append(inject_dummy_at_section_ends(ja_data["text"]))
        parts.append("")

    if en_data:
        en_rev_link = (
            f"https://en.wikipedia.org/wiki/Special:PermanentLink/{en_data['revid']}"
            if en_data.get("revid")
            else ""
        )
        en_heading = (
            f"== Imported from English Wikipedia ({run_date}, [{en_rev_link} revision]) =="
            if en_rev_link
            else f"== Imported from English Wikipedia ({run_date}) =="
        )
        parts.append(en_heading)
        parts.append(DUMMY_COMMENT)
        parts.append(f"<!-- Source: en:{en_data['talk_title']} | revid={en_data['revid']} -->")
        parts.append(inject_dummy_at_section_ends(en_data["text"]))
        parts.append("")

    if simple_data:
        simple_rev_link = (
            f"https://simple.wikipedia.org/wiki/Special:PermanentLink/{simple_data['revid']}"
            if simple_data.get("revid")
            else ""
        )
        simple_heading = (
            f"== Imported from Simple English Wikipedia ({run_date}, [{simple_rev_link} revision]) =="
            if simple_rev_link
            else f"== Imported from Simple English Wikipedia ({run_date}) =="
        )
        parts.append(simple_heading)
        parts.append(DUMMY_COMMENT)
        parts.append(f"<!-- Source: simple:{simple_data['talk_title']} | revid={simple_data['revid']} -->")
        parts.append(inject_dummy_at_section_ends(simple_data["text"]))
        parts.append("")

    if not ja_data and not en_data and not simple_data:
        parts.append("== Initial import ==")
        parts.append(DUMMY_COMMENT)
        parts.append("<!-- No source talk page found via linked QID sitelinks (ja/en/simple) at migration time. -->")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def get_namespace_maps(site):
    info = site.api("query", meta="siteinfo", siprop="namespaces|namespacealiases")
    ns_data = info.get("query", {}).get("namespaces", {})
    alias_data = info.get("query", {}).get("namespacealiases", [])

    id_to_name = {}
    name_to_id = {}
    for k, v in ns_data.items():
        ns_id = int(k)
        ns_name = v.get("*", "")
        id_to_name[ns_id] = ns_name
        name_to_id[ns_name.lower()] = ns_id
        canonical = (v.get("canonical") or "").strip()
        if canonical:
            name_to_id[canonical.lower()] = ns_id

    for alias in alias_data:
        name_to_id[alias.get("*", "").lower()] = int(alias.get("id"))

    return id_to_name, name_to_id


def iter_subject_titles_all_namespaces(site, subject_ns_ids, start_title=None):
    for ns_id in sorted(subject_ns_ids):
        params = {
            "list": "allpages",
            "apnamespace": ns_id,
            "aplimit": "max",
        }
        if start_title and ns_id == 0:
            params["apfrom"] = start_title

        while True:
            result = site.api("query", **params)
            for entry in result["query"]["allpages"]:
                yield entry["title"], ns_id
            if "continue" in result:
                params.update(result["continue"])
            else:
                break


def get_title_info(site, title):
    result = site.api("query", prop="info", titles=title, formatversion="2")
    pages = result.get("query", {}).get("pages", [])
    if not pages:
        return None, title
    page = pages[0]
    if page.get("missing"):
        return None, page.get("title", title)
    return page.get("ns"), page.get("title", title)


def is_redirect(site, title):
    result = site.api("query", prop="info", titles=title, formatversion="2")
    pages = result.get("query", {}).get("pages", [])
    if not pages:
        return False
    page = pages[0]
    return bool(page.get("redirect"))


def safe_is_redirect(site, title):
    last_err = None
    for _attempt in range(1, 4):
        try:
            return is_redirect(site, title), site
        except Exception as e:
            last_err = e
            time.sleep(RETRY_SLEEP)
            try:
                site = make_site()
            except Exception:
                pass
    raise last_err


def to_talk_title(subject_title, subject_ns_id, id_to_name):
    if subject_ns_id % 2 == 1:
        return None

    talk_ns_id = subject_ns_id + 1
    talk_ns_name = id_to_name.get(talk_ns_id)
    if talk_ns_name is None:
        return None

    subject_ns_name = id_to_name.get(subject_ns_id, "")
    if subject_ns_name and subject_title.startswith(subject_ns_name + ":"):
        base_title = subject_title[len(subject_ns_name) + 1 :]
    else:
        base_title = subject_title

    return f"{talk_ns_name}:{base_title}"


def to_subject_title(title, ns_id, id_to_name):
    """Map a talk-page title to its subject-page title when possible."""
    if ns_id is None:
        return title, 0
    if ns_id % 2 == 0:
        return title, ns_id

    subject_ns_id = ns_id - 1
    subject_ns_name = id_to_name.get(subject_ns_id, "")
    talk_ns_name = id_to_name.get(ns_id, "")
    if talk_ns_name and title.startswith(talk_ns_name + ":"):
        base_title = title[len(talk_ns_name) + 1 :]
    else:
        base_title = title

    subject_title = f"{subject_ns_name}:{base_title}" if subject_ns_name else base_title
    return subject_title, subject_ns_id


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
    parser.add_argument(
        "--start-title",
        default="",
        help="Start title for default all-namespace mode (applies to mainspace scan start).",
    )
    parser.add_argument("--titles", default="", help="Comma-separated subject-page titles to process.")
    parser.add_argument("--titles-file", default="", help="Path to newline-delimited titles file.")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="Path to resume-state file.")
    parser.add_argument("--log-file", default=DEFAULT_LOG_FILE, help="Path to JSONL run log.")
    parser.add_argument("--retry", type=int, default=3, help="Retries per page for read/save operations.")
    args = parser.parse_args()

    site = make_site()
    print(f"Logged in as {USERNAME}\n")
    completed_titles = load_state(args.state_file) if args.apply else set()
    if args.apply:
        print(f"Loaded {len(completed_titles)} completed titles from state file: {args.state_file}")

    explicit_titles = []
    explicit_titles.extend(parse_titles_arg(args.titles))
    if args.titles_file:
        explicit_titles.extend(parse_titles_file(args.titles_file))
    explicit_titles = list(dict.fromkeys(explicit_titles))

    id_to_name, _name_to_id = get_namespace_maps(site)
    subject_ns_ids = [ns_id for ns_id in id_to_name.keys() if ns_id >= 0 and ns_id % 2 == 0]

    if explicit_titles:
        title_ns_pairs = []
        for t in explicit_titles:
            ns_id, normalized_title = get_title_info(site, t)
            resolved_title = normalized_title if ns_id is not None else t
            subject_title, subject_ns_id = to_subject_title(resolved_title, ns_id, id_to_name)
            title_ns_pairs.append((subject_title, subject_ns_id))
        titles_iter = iter(title_ns_pairs)
        print(f"Processing explicit title list: {len(title_ns_pairs)} subject pages")
    else:
        titles_iter = iter_subject_titles_all_namespaces(
            site,
            subject_ns_ids=subject_ns_ids,
            start_title=args.start_title or None,
        )
        print("Processing all pages in all subject namespaces")

    run_date = dt.datetime.utcnow().strftime("%Y-%m-%d")
    processed = edited = skipped = errors = 0
    nochange_errors = 0

    for title, ns_id in titles_iter:
        if args.limit and processed >= args.limit:
            break
        if args.apply and title in completed_titles:
            skipped += 1
            print(f"SKIP (already covered in state): {title}")
            continue
        if ns_id == 0 and QPAGE_RE.match(title):
            print(f"SKIP (Q-page): {title}")
            skipped += 1
            append_log(args.log_file, {"title": title, "status": "skipped_qpage"})
            if args.apply:
                append_state(args.state_file, title)
                completed_titles.add(title)
            continue
        try:
            redirect, site = safe_is_redirect(site, title)
        except Exception as e:
            print(f"ERROR redirect-check failed for {title}: {e}")
            errors += 1
            append_log(args.log_file, {"title": title, "status": "error_redirect_check", "error": str(e)})
            continue
        if redirect:
            print(f"SKIP (redirect): {title}")
            skipped += 1
            append_log(args.log_file, {"title": title, "status": "skipped_redirect"})
            if args.apply:
                append_state(args.state_file, title)
                completed_titles.add(title)
            continue

        talk_title = to_talk_title(title, ns_id, id_to_name)
        if not talk_title:
            talk_title = f"Talk:{title}"

        processed += 1
        prefix = f"[{processed}] {title}"
        try:
            page = site.pages[title]
            talk_page = site.pages[talk_title]
        except Exception as e:
            print(f"{prefix} ERROR accessing page object: {e}")
            errors += 1
            append_log(args.log_file, {"title": title, "talk_title": talk_title, "status": "error_page_access", "error": str(e)})
            continue

        page_text = talk_text = None
        read_ok = False
        for _attempt in range(1, args.retry + 1):
            try:
                page_text = page.text() if page.exists else ""
                talk_text = talk_page.text() if talk_page.exists else ""
                read_ok = True
                break
            except Exception as e:
                print(f"{prefix} WARN read failed (attempt {_attempt}/{args.retry}): {e}")
                time.sleep(RETRY_SLEEP)
                try:
                    site = make_site()
                    page = site.pages[title]
                    talk_page = site.pages[talk_title]
                except Exception:
                    pass
        if not read_ok:
            err = "read retries exhausted"
            print(f"{prefix} ERROR {err}")
            errors += 1
            append_log(args.log_file, {"title": title, "talk_title": talk_title, "status": "error_read", "error": err})
            continue

        qid = extract_qid(page_text)
        ja_title = en_title = simple_title = None
        if qid:
            try:
                ja_title, en_title, simple_title = get_sitelinks_from_wikidata(qid)
            except Exception as e:
                print(f"{prefix} WARN wikidata lookup failed for {qid}: {e}")
        else:
            print(f"{prefix} WARN no linked QID found; imports limited to none")

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
        try:
            simple_data = fetch_wikipedia_talk_content("simple", simple_title) if simple_title else None
        except Exception as e:
            print(f"{prefix} WARN simple talk fetch failed ({simple_title}): {e}")
            simple_data = None

        local_discussion = get_local_discussion_block(talk_text)
        new_talk_text = build_talk_text(title, local_discussion, ja_data, en_data, simple_data, run_date)
        source_bits = []
        if ja_data:
            source_bits.append(f"ja:{ja_data['title']}")
        if en_data:
            source_bits.append(f"en:{en_data['title']}")
        if simple_data:
            source_bits.append(f"simple:{simple_data['title']}")
        source_label = ", ".join(source_bits) if source_bits else "no qid-linked ja/en/simple source"

        if args.apply:
            saved = False
            last_save_err = None
            for _attempt in range(1, args.retry + 1):
                try:
                    talk_page.save(
                        new_talk_text,
                        summary=(
                            f"Bot: migrate talk page structure; import discussion seed ({source_label}); "
                            "add local discussion section + dated import note"
                        ),
                    )
                    saved = True
                    edited += 1
                    print(f"{prefix} EDITED ({source_label})")
                    append_log(
                        args.log_file,
                        {"title": title, "talk_title": talk_title, "status": "edited", "sources": source_label},
                    )
                    append_state(args.state_file, title)
                    completed_titles.add(title)
                    time.sleep(THROTTLE)
                    break
                except Exception as e:
                    last_save_err = e
                    msg = str(e).lower()
                    if "nochange" in msg:
                        print(f"{prefix} NOCHANGE returned by API ({source_label})")
                        nochange_errors += 1
                        append_log(
                            args.log_file,
                            {"title": title, "talk_title": talk_title, "status": "nochange", "sources": source_label},
                        )
                        append_state(args.state_file, title)
                        completed_titles.add(title)
                        saved = True
                        break
                    print(f"{prefix} WARN save failed (attempt {_attempt}/{args.retry}): {e}")
                    time.sleep(RETRY_SLEEP)
                    try:
                        site = make_site()
                        talk_page = site.pages[talk_title]
                    except Exception:
                        pass
            if not saved:
                print(f"{prefix} ERROR saving talk page: {last_save_err}")
                errors += 1
                append_log(
                    args.log_file,
                    {
                        "title": title,
                        "talk_title": talk_title,
                        "status": "error_save",
                        "sources": source_label,
                        "error": str(last_save_err),
                    },
                )
        else:
            print(f"{prefix} DRY RUN would edit ({source_label})")
            append_log(args.log_file, {"title": title, "talk_title": talk_title, "status": "dry_run", "sources": source_label})

    print("\n" + "=" * 60)
    print(
        f"Done. Processed: {processed} | Edited: {edited} | "
        f"Skipped: {skipped} | Errors: {errors} | Mode: {'APPLY' if args.apply else 'DRY-RUN'}"
    )
    print(f"API nochange responses: {nochange_errors}")


if __name__ == "__main__":
    main()
