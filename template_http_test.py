import csv
import os
import random
import re
import time
import uuid
from collections import defaultdict
from urllib.parse import urlparse

import requests

QUERY_PATH = r"C:\Users\Immanuelle\Documents\Github\jinjacho\query.csv"
RESULTS_PATH = r"C:\Users\Immanuelle\Documents\Github\jinjacho\template_http_test_results.csv"
REPORT_PATH = r"C:\Users\Immanuelle\Documents\Github\jinjacho\TEMPLATE_TEST_REPORT.md"

SAMPLES_PER_TEMPLATE = 20
RATE_LIMIT_SECONDS = 1.0
TIMEOUT_SECONDS = 10
BATCH_TEMPLATES = 5  # templates per run

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
})

TEMPLATE_RE = re.compile(r"\{([^}]+)\}")


def read_templates(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("shrineDetailTemplate"):
                rows.append(r)
    return rows


def read_existing_counts(path):
    counts = defaultdict(int)
    if not os.path.exists(path):
        return counts
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            t = r.get("shrineDetailTemplate", "")
            if t:
                counts[t] += 1
    return counts


def extract_placeholders(template):
    return TEMPLATE_RE.findall(template)


def domain_for(template):
    return urlparse(template).netloc.lower()


def random_uuid():
    return str(uuid.uuid4())


def random_numeric(width=None):
    n = random.randint(1, 99999)
    if width:
        return str(n).zfill(width)
    return str(n)


def random_j_prefixed():
    return f"j{random_numeric(width=4)}"


def random_slug():
    choices = ["example", "jinja", "shrine", "hachimansha", "kumano", "sengen", "tenjin"]
    return random.choice(choices)


def discover_sitemaps(base_url):
    urls = []
    for suffix in ["/robots.txt", "/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]:
        try:
            r = SESSION.get(base_url + suffix, timeout=TIMEOUT_SECONDS)
            if r.status_code == 200:
                urls.append(base_url + suffix)
        except requests.RequestException:
            pass
    return urls


def extract_urls_from_text(text):
    return re.findall(r"https?://[^\s'\"]+", text)


def discover_candidate_urls(template):
    parsed = urlparse(template)
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates = []
    for sm in discover_sitemaps(base):
        try:
            r = SESSION.get(sm, timeout=TIMEOUT_SECONDS)
            if r.status_code == 200:
                urls = extract_urls_from_text(r.text)
                candidates.extend(urls)
        except requests.RequestException:
            continue

    template_path = parsed.path
    if template_path:
        pattern = re.escape(template_path)
        pattern = re.sub(r"\\\{[^}]+\\\}", r"[^/]+", pattern)
        path_re = re.compile(pattern)
        filtered = []
        for u in candidates:
            try:
                up = urlparse(u)
                if up.netloc.lower() == parsed.netloc.lower() and path_re.search(up.path):
                    filtered.append(u)
            except Exception:
                pass
        return list(dict.fromkeys(filtered))
    return list(dict.fromkeys(candidates))


def build_sample_urls(template, notes):
    placeholders = extract_placeholders(template)
    samples = []

    if any(ph in ("slug", "ward", "area", "city", "branch", "region") for ph in placeholders):
        candidates = discover_candidate_urls(template)
        for u in candidates[:SAMPLES_PER_TEMPLATE]:
            samples.append(u)
        if samples:
            return samples, "discovered"

    for _ in range(SAMPLES_PER_TEMPLATE):
        vals = {}
        for ph in placeholders:
            if ph.lower() in ("uuid",):
                vals[ph] = random_uuid()
            elif ph.lower() in ("id", "shrno", "code", "jinjyano"):
                if notes and "j0001" in notes.lower():
                    vals[ph] = random_j_prefixed()
                else:
                    vals[ph] = random_numeric()
            elif ph.lower() in ("ward", "area", "city", "branch", "region", "slug", "hash"):
                vals[ph] = random_slug()
            else:
                vals[ph] = random_numeric()

        url = template
        for k, v in vals.items():
            url = url.replace("{" + k + "}", v)
        samples.append(url)

    return samples, "generated"


def write_results(path, rows):
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        fieldnames = [
            "item",
            "itemLabel",
            "officialWebsite",
            "shrineDetailTemplate",
            "templateConfidence",
            "sampleUrl",
            "sampleSource",
            "httpStatus",
            "responseSize",
            "error",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def write_report(path, results):
    by_template = defaultdict(lambda: {"ok": 0, "fail": 0, "other": 0, "total": 0})
    for r in results:
        key = r["shrineDetailTemplate"]
        by_template[key]["total"] += 1
        if r["httpStatus"] == "200":
            by_template[key]["ok"] += 1
        elif r["httpStatus"]:
            by_template[key]["fail"] += 1
        else:
            by_template[key]["other"] += 1

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Template HTTP Validity Test Report\n\n")
        f.write(f"Samples per template: {SAMPLES_PER_TEMPLATE}\n")
        f.write(f"Rate limit: {RATE_LIMIT_SECONDS}s per domain\n")
        f.write(f"Timeout: {TIMEOUT_SECONDS}s\n\n")
        f.write("## Summary\n\n")
        f.write("template, total, 200_ok, non_200, errors\n")
        for t, stats in by_template.items():
            f.write(f"{t}, {stats['total']}, {stats['ok']}, {stats['fail']}, {stats['other']}\n")


def main():
    rows = read_templates(QUERY_PATH)
    counts = read_existing_counts(RESULTS_PATH)
    per_domain_last = defaultdict(lambda: 0.0)

    # pick templates that still need samples
    pending = []
    for r in rows:
        t = r["shrineDetailTemplate"].strip()
        if counts.get(t, 0) < SAMPLES_PER_TEMPLATE:
            pending.append(r)

    pending = pending[:BATCH_TEMPLATES]

    if not pending:
        print("No pending templates.")
        return

    results = []

    for r in pending:
        template = r["shrineDetailTemplate"].strip()
        notes = r.get("templateNotes", "")
        domain = domain_for(template)

        urls, source = build_sample_urls(template, notes)
        # only take remaining samples
        already = counts.get(template, 0)
        needed = max(0, SAMPLES_PER_TEMPLATE - already)
        for u in urls[:needed]:
            elapsed = time.time() - per_domain_last[domain]
            if elapsed < RATE_LIMIT_SECONDS:
                time.sleep(RATE_LIMIT_SECONDS - elapsed)

            status = ""
            size = ""
            error = ""
            try:
                resp = SESSION.get(u, timeout=TIMEOUT_SECONDS, allow_redirects=True)
                status = str(resp.status_code)
                size = str(len(resp.text or ""))
            except requests.RequestException as e:
                error = str(e)

            per_domain_last[domain] = time.time()

            results.append({
                "item": r.get("item", ""),
                "itemLabel": r.get("itemLabel", ""),
                "officialWebsite": r.get("officialWebsite", ""),
                "shrineDetailTemplate": template,
                "templateConfidence": r.get("templateConfidence", ""),
                "sampleUrl": u,
                "sampleSource": source,
                "httpStatus": status,
                "responseSize": size,
                "error": error,
            })

    if results:
        write_results(RESULTS_PATH, results)

        # rebuild report from full results file
        all_results = []
        with open(RESULTS_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                all_results.append(r)
        write_report(REPORT_PATH, all_results)

        print(f"Wrote {len(results)} rows. Pending templates remaining: {max(0, len(rows)-len(pending))} (approx).")


if __name__ == "__main__":
    main()
