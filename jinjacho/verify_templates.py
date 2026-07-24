"""
Verify jinjacho shrine detail URL templates by testing real URLs from Wikidata.
Tests HTTP status codes and checks for shrine-related content.
"""
import csv
import io
import re
import sys
import time
import urllib.request
import urllib.error
import ssl
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# URLs to test - picked from Wikidata P856 and shrines_and_websites.csv
# Format: (prefecture, url, expected_template_note)
TEST_URLS = [
    # Gifu - syosai.php?shrno={id}
    ("Gifu", "https://www.gifu-jinjacho.jp/syosai.php?shrno=193", "syosai.php?shrno=193"),
    ("Gifu", "https://www.gifu-jinjacho.jp/syosai.php?shrno=2286", "syosai.php?shrno=2286"),
    ("Gifu", "https://www.gifu-jinjacho.jp/syosai.php?shrno=142", "syosai.php?shrno=142"),
    ("Gifu", "https://www.gifu-jinjacho.jp/syosai.php?shrno=798", "syosai.php?shrno=798"),
    ("Gifu", "https://www.gifu-jinjacho.jp/syosai.php?shrno=1254", "syosai.php?shrno=1254"),

    # Hyogo - /data/{code}.html
    ("Hyogo", "https://www.hyogo-jinjacho.com/data/6301007.html", "data/6301007"),
    ("Hyogo", "https://www.hyogo-jinjacho.com/data/6308105.html", "data/6308105"),
    ("Hyogo", "https://www.hyogo-jinjacho.com/data/6322009.html", "data/6322009"),
    ("Hyogo", "https://www.hyogo-jinjacho.com/data/6308071.html", "data/6308071"),

    # Shizuoka - /shokai/jinja.php?id={id}
    ("Shizuoka", "http://www.shizuoka-jinjacho.or.jp/shokai/jinja.php?id=4413061", "id=4413061"),
    ("Shizuoka", "http://www.shizuoka-jinjacho.or.jp/shokai/jinja.php?id=4409164", "id=4409164"),
    ("Shizuoka", "http://www.shizuoka-jinjacho.or.jp/shokai/jinja.php?id=4402102", "id=4402102"),
    ("Shizuoka", "http://www.shizuoka-jinjacho.or.jp/shokai/jinja.php?id=4402140", "id=4402140"),
    ("Shizuoka", "http://www.shizuoka-jinjacho.or.jp/shokai/jinja.php?id=4415065", "id=4415065"),
    ("Shizuoka", "http://www.shizuoka-jinjacho.or.jp/shokai/jinja.php?id=4413004", "id=4413004"),

    # Aichi - /search_detail.html?id={uuid}
    ("Aichi", "https://www.aichi-jinjacho.or.jp/search_detail.html?id=bb10f2cc-3e65-4e3f-aad0-e4259400d028", "uuid=bb10f2cc"),
    ("Aichi", "https://www.aichi-jinjacho.or.jp/search_detail.html?id=de0a002d-afb7-445a-9056-0b307ed4d4a9", "uuid=de0a002d"),
    ("Aichi", "https://www.aichi-jinjacho.or.jp/search_detail.html?id=c3f9cf79-b0b0-4b51-ba37-2dcd86867ca7", "uuid=c3f9cf79"),
    ("Aichi", "https://www.aichi-jinjacho.or.jp/search_detail.html?id=90cc869d-739e-4208-b108-91f4c98ba3de", "uuid=90cc869d"),

    # Ishikawa - /shrine/{jNNNN}/
    ("Ishikawa", "https://www.ishikawa-jinjacho.or.jp/shrine/j1706/", "j1706"),
    ("Ishikawa", "https://www.ishikawa-jinjacho.or.jp/shrine/j1590/", "j1590"),
    ("Ishikawa", "https://www.ishikawa-jinjacho.or.jp/shrine/j1730/", "j1730"),

    # Miyagi - /jinja-search/detail.php?code={code}
    ("Miyagi", "https://miyagi-jinjacho.or.jp/jinja-search/detail.php?code=310020365", "code=310020365"),
    ("Miyagi", "https://miyagi-jinjacho.or.jp/jinja-search/detail.php?code=310020456", "code=310020456"),
    ("Miyagi", "https://miyagi-jinjacho.or.jp/jinja-search/detail.php?code=310020547", "code=310020547"),
    ("Miyagi", "https://miyagi-jinjacho.or.jp/jinja-search/detail.php?code=310020562", "code=310020562"),

    # Saitama - /shrine/{id}/
    ("Saitama", "https://www.saitama-jinjacho.or.jp/shrine/9107/", "shrine/9107"),
    ("Saitama", "https://www.saitama-jinjacho.or.jp/shrine/9124/", "shrine/9124"),
    ("Saitama", "https://www.saitama-jinjacho.or.jp/shrine/10223/", "shrine/10223"),
    ("Saitama", "https://www.saitama-jinjacho.or.jp/shrine/9588/", "shrine/9588"),

    # Okayama - /search/{id}/
    ("Okayama", "https://www.okayama-jinjacho.or.jp/search/18043/", "search/18043"),
    ("Okayama", "https://www.okayama-jinjacho.or.jp/search/16627/", "search/16627"),

    # Kyoto - /shrine/{id}.html
    ("Kyoto", "https://www.kyoto-jinjacho.or.jp/shrine/14.html", "shrine/14"),

    # Osaka - /funai_jinja/{branch}/{city}/{code}{slug}.html
    ("Osaka", "https://www.osaka-jinjacho.jp/funai_jinja/dai1shibu/nose-cho/01020kusasajinja.html", "funai_jinja/..."),

    # Shiga - CGI DB
    ("Shiga", "https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=630", "oid=630"),
    ("Shiga", "https://www.shiga-jinjacho.jp/ycBBS/Board.cgi/02_jinja_db/db/ycDB_02jinja-pc-detail.html?mode:view=1&view:oid=526", "oid=526"),

    # Mie (kyoka subdomain) - /shrine/{name-slug}/
    ("Mie", "http://kyoka.mie-jinjacho.or.jp/shrine/%E7%A3%AF%E7%A5%9E%E7%A4%BE/", "Iso Shrine"),
    ("Mie", "http://kyoka.mie-jinjacho.or.jp/shrine/%E4%BC%8A%E5%8B%A2%E5%AF%BA%E7%A5%9E%E7%A4%BE/", "Isedera Shrine"),
    ("Mie", "http://kyoka.mie-jinjacho.or.jp/shrine/%E9%AB%98%E5%90%91%E7%A5%9E%E7%A4%BE/", "Takabuku"),

    # jinja-net.jp - Nara
    ("Nara (jinja-net)", "https://jinja-net.jp/jinjacho-nara/jsearch3nara.php?jinjya=5808", "jinjya=5808"),
    ("Nara (jinja-net)", "https://jinja-net.jp/jinjacho-nara/jsearch3nara.php?jinjya=33932", "jinjya=33932"),
    ("Nara (jinja-net)", "https://jinja-net.jp/jinjacho-nara/jsearch3nara.php?jinjya=33741", "jinjya=33741"),

    # jinja-net.jp - Mie
    ("Mie (jinja-net)", "https://jinja-net.jp/jinjacho-mie/jsearch3mie.php?jinjya=63753", "jinjya=63753"),
    ("Mie (jinja-net)", "https://jinja-net.jp/jinjacho-mie/jsearch3mie.php?jinjya=63604", "jinjya=63604"),

    # jinja-net.jp - Shimane
    ("Shimane (jinja-net)", "http://www.jinja-net.jp/jinjacho-shimane/jsearch3shimane.php?jinjya=29807", "jinjya=29807"),

    # jinja-net.jp - Yamaguchi
    ("Yamaguchi (jinja-net)", "http://www.jinja-net.jp/jinjacho-yamaguti/jsearch3yamaguti.php?jinjya=53120", "jinjya=53120"),

    # Tokyo - /{ward}/{id}/
    ("Tokyo", "http://www.tokyo-jinjacho.or.jp/setagaya/5212/", "setagaya/5212"),

    # Kagoshima - /shrine-search/area-{area}/{city}/{id}/
    ("Kagoshima", "https://www.kagojinjacho.or.jp/shrine-search/area-kagoshima/%E3%81%84%E3%81%A1%E3%81%8D%E4%B8%B2%E6%9C%A8%E9%87%8E%E5%B8%82/941/", "shrine-search/941"),

    # Akita
    ("Akita", "http://akita-jinjacho.sakura.ne.jp/tatsujin_etc/01_jinja/nikaho/10_kinbou.html", "tatsujin_etc/..."),

    # Wakayama - GetWjtTbl.php?JinjyaNo={id}
    ("Wakayama", "https://wakayama-jinjacho.or.jp/jdb/sys/user/GetWjtTbl.php?JinjyaNo=1", "JinjyaNo=1"),

    # Kanagawa - /shrine/{id}/
    ("Kanagawa", "https://www.kanagawa-jinja.or.jp/shrine/1-0001/", "shrine/1-0001"),

    # Tottori - /pages/{id}/
    ("Tottori", "https://tottori-jinjacho.jp/pages/1/", "pages/1"),

    # Yamanashi - /intro/search/detail/{id}
    ("Yamanashi", "https://www.yamanashi-jinjacho.or.jp/intro/search/detail/1", "detail/1"),

    # Yamagata - /shrine_detail/{id}
    ("Yamagata", "https://yamagata-jinjyacho.or.jp/shrine_detail/1", "shrine_detail/1"),

    # Hokkaido (test homepage since slugs need names)
    ("Hokkaido", "https://hokkaidojinjacho.jp/", "homepage"),

    # Kagawa
    ("Kagawa", "https://kagawakenjinjacho.or.jp/shrine/", "shrine list"),

    # Ehime - WordPress
    ("Ehime", "https://ehime-jinjacho.jp/jinja/", "jinja list"),

    # Saga - WordPress
    ("Saga", "https://saga-jinjacho.jp/", "homepage"),

    # Tochigi - WordPress
    ("Tochigi", "https://www.tochigi-jinjacho.or.jp/", "homepage"),

    # Kumamoto (newly discovered)
    ("Kumamoto", "https://kumamotokenjinjacho.jp/", "homepage"),

    # Fukui
    ("Fukui", "https://www.jinja-fukui.jp/", "homepage"),

    # Okinawa
    ("Okinawa", "https://jinjacho.naminouegu.jp/", "homepage"),

    # Aomori
    ("Aomori", "https://www.aomori-jinjacho.or.jp/jinja/", "jinja list"),

    # Ibaraki
    ("Ibaraki", "https://www.ibarakiken-jinjacho.or.jp/", "homepage"),

    # Hiroshima
    ("Hiroshima", "https://www.hiroshima-jinjacho.jp/", "homepage"),

    # Shimane
    ("Shimane", "https://www.shimane-jinjacho.or.jp/", "homepage"),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}

# Allow self-signed certs (Shizuoka has one)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Shrine-related keywords to check if page has real content
SHRINE_KEYWORDS = ['神社', '祭神', '鎮座', '由緒', '住所', '例祭', '御祭神', 'shrine', '主祭神']

results = []

print(f"Testing {len(TEST_URLS)} URLs...")
print("=" * 100)

for i, (pref, url, note) in enumerate(TEST_URLS):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        status = resp.getcode()
        raw = resp.read()

        # Try to decode
        try:
            body = raw.decode('utf-8')
        except:
            try:
                body = raw.decode('shift-jis')
            except:
                try:
                    body = raw.decode('euc-jp')
                except:
                    body = raw.decode('latin-1')

        length = len(body)

        # Check for shrine content
        found_keywords = [kw for kw in SHRINE_KEYWORDS if kw in body]

        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', body, re.DOTALL)
        title = title_match.group(1).strip()[:60] if title_match else "(no title)"

        # Check for Cloudflare/bot block indicators
        is_cf_blocked = 'cf-browser-verification' in body or 'Just a moment' in body or '_cf_chl' in body
        is_empty = length < 100

        if is_cf_blocked:
            verdict = "CLOUDFLARE_BLOCKED"
        elif is_empty:
            verdict = "EMPTY"
        elif len(found_keywords) >= 2:
            verdict = "OK_SHRINE_CONTENT"
        elif length > 500:
            verdict = "OK_PAGE_LOADED"
        else:
            verdict = "SMALL_PAGE"

        result = {
            'prefecture': pref,
            'url': url,
            'note': note,
            'status': status,
            'length': length,
            'title': title,
            'keywords': ','.join(found_keywords[:4]),
            'verdict': verdict,
        }

    except urllib.error.HTTPError as e:
        result = {
            'prefecture': pref,
            'url': url,
            'note': note,
            'status': e.code,
            'length': 0,
            'title': '',
            'keywords': '',
            'verdict': f"HTTP_{e.code}",
        }
    except Exception as e:
        err_type = type(e).__name__
        result = {
            'prefecture': pref,
            'url': url,
            'note': note,
            'status': 0,
            'length': 0,
            'title': '',
            'keywords': '',
            'verdict': f"ERROR_{err_type}",
        }

    results.append(result)

    # Print progress
    v = result['verdict']
    icon = '✓' if v.startswith('OK') else '✗' if 'ERROR' in v or 'BLOCKED' in v or 'EMPTY' in v else '?'
    print(f"[{i+1:2d}/{len(TEST_URLS)}] {icon} {pref:22s} {v:25s} {result.get('status',''):>3} {result.get('length',0):>7}b  {note}")

    time.sleep(0.5)  # Be respectful

# Write results to CSV
with open(r'C:\Users\Immanuelle\Documents\Github\jinjacho\verification_results.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['prefecture', 'note', 'status', 'length', 'verdict', 'title', 'keywords', 'url'])
    writer.writeheader()
    for r in results:
        writer.writerow(r)

# Summary
print()
print("=" * 100)
print("SUMMARY BY VERDICT:")
by_verdict = defaultdict(list)
for r in results:
    by_verdict[r['verdict']].append(r['prefecture'])
for v in sorted(by_verdict.keys()):
    prefs = sorted(set(by_verdict[v]))
    print(f"  {v:30s}: {len(by_verdict[v]):2d} URLs - {', '.join(prefs)}")

print()
print("SUMMARY BY PREFECTURE:")
by_pref = defaultdict(list)
for r in results:
    by_pref[r['prefecture']].append(r['verdict'])
for pref in sorted(by_pref.keys()):
    verdicts = by_pref[pref]
    ok_count = sum(1 for v in verdicts if v.startswith('OK'))
    print(f"  {pref:25s}: {ok_count}/{len(verdicts)} OK  [{', '.join(set(verdicts))}]")
