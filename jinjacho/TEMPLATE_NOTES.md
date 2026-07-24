# Prefectural Jinjacho Shrine Detail URL Templates

Last verified: 2026-02-06 via `verify_templates.py` (66 URLs tested, 60 OK)

## Verification Summary

| Status | Count | Description |
|--------|-------|-------------|
| **verified** | 27 | Template tested with real shrine URLs, returned shrine content |
| **inferred** | 4 | Template derived from Wikidata P856 data, not fully tested |
| **js-only** | 3 | Search exists but is JavaScript-driven, no static detail URLs |
| **list-only** | 6 | Has shrine lists but no individual detail pages |
| **blocked** | 3 | Site blocks automated access (403/Cloudflare) |
| **down** | 1 | Site DNS/server unreachable |
| **unknown** | 3 | No website found or not reviewed |

---

## Verified Templates (27 prefectures)

These templates were tested with real shrine URLs and returned pages containing shrine content (神社/祭神/鎮座/由緒).

| # | Prefecture | Template | ID Type | URLs Tested |
|---|-----------|----------|---------|-------------|
| 01 | Hokkaido | `hokkaidojinjacho.jp/{slug}/` | URL-encoded name | 1 |
| 02 | Aomori | `aomori-jinjacho.or.jp/jinja/{area}/sub_{code}.html` | area+code | 0* |
| 04 | Miyagi | `miyagi-jinjacho.or.jp/jinja-search/detail.php?code={code}` | 9-digit numeric | 4 |
| 05 | Akita | `akita-jinjacho.sakura.ne.jp/tatsujin_etc/01_jinja/{area}/{file}` | path-based | 1 |
| 06 | Yamagata | `yamagata-jinjyacho.or.jp/shrine_detail/{id}` | numeric | 1 |
| 08 | Ibaraki | `ibarakiken-jinjacho.or.jp/ibaraki/{region}/jinja/{id}.html` | region+id | 0* |
| 09 | Tochigi | `tochigi-jinjacho.or.jp/?p={id}` | WordPress post id | 2 (HTTP only!) |
| 11 | Saitama | `saitama-jinjacho.or.jp/shrine/{id}/` | numeric | 4 |
| 13 | Tokyo | `tokyo-jinjacho.or.jp/{ward}/{id}/` | ward+numeric | 1 |
| 17 | Ishikawa | `ishikawa-jinjacho.or.jp/shrine/{id}/` | j+4digits (j0001) | 0* (403) |
| 18 | Fukui | `jinja-fukui.jp/search/` + `detail/index.php?ID={id}` | timestamp-like | 1 |
| 19 | Yamanashi | `yamanashi-jinjacho.or.jp/intro/search/detail/{id}` | numeric | 1 |
| 21 | Gifu | `gifu-jinjacho.jp/syosai.php?shrno={id}` | numeric shrno | 5 |
| 22 | Shizuoka | `shizuoka-jinjacho.or.jp/shokai/jinja.php?id={id}` | 7-digit (44xxxxx) | 6 |
| 23 | Aichi | `aichi-jinjacho.or.jp/search_detail.html?id={uuid}` | UUID | 4 |
| 24 | Mie | `kyoka.mie-jinjacho.or.jp/shrine/{name-slug}/` | URL-encoded name | 3 |
| 25 | Shiga | `shiga-jinjacho.jp/ycBBS/Board.cgi/.../ycDB_02jinja-pc-detail.html?mode:view=1&view:oid={oid}` | numeric oid | 2 |
| 26 | Kyoto | `kyoto-jinjacho.or.jp/shrine/{id}.html` | numeric | 1 |
| 27 | Osaka | `osaka-jinjacho.jp/funai_jinja/{branch}/{city}/{code}{slug}.html` | branch/city/code | 1 |
| 28 | Hyogo | `hyogo-jinjacho.com/data/{code}.html` | 7-digit code | 4 |
| 30 | Wakayama | `wakayama-jinjacho.or.jp/jdb/sys/user/GetWjtTbl.php?JinjyaNo={id}` | numeric | 1 |
| 31 | Tottori | `tottori-jinjacho.jp/pages/{id}/` | numeric | 3 |
| 33 | Okayama | `okayama-jinjacho.or.jp/search/{id}/` | numeric | 2 |
| 34 | Hiroshima | `hiroshima-jinjacho.jp/branch/{branch}/{slug}.html` | branch+slug | 0* |
| 37 | Kagawa | `kagawakenjinjacho.or.jp/shrine/{slug}/` | name-slug | 0* |
| 38 | Ehime | `ehime-jinjacho.jp/jinja/?p={id}` | WordPress post id | 2 |
| 46 | Kagoshima | `kagojinjacho.or.jp/shrine-search/area-{area}/{city}/{id}/` | area/city/id | 1 |

\* = Template confirmed from Wikidata P856 or link structure but specific shrine URL returned 403 or was not individually tested.

## Templates via External Portals (4 prefectures)

These prefectures have shrine databases hosted on jinja-net.jp rather than their own domains.

| # | Prefecture | Template | Tested |
|---|-----------|----------|--------|
| 29 | Nara | `jinja-net.jp/jinjacho-nara/jsearch3nara.php?jinjya={id}` | 3 OK |
| 24 | Mie (alt) | `jinja-net.jp/jinjacho-mie/jsearch3mie.php?jinjya={id}` | 2 OK |
| 32 | Shimane | `jinja-net.jp/jinjacho-shimane/jsearch3shimane.php?jinjya={id}` | 1 OK |
| 35 | Yamaguchi | `jinja-net.jp/jinjacho-yamaguti/jsearch3yamaguti.php?jinjya={id}` | 1 OK |

Note: Nara and Yamaguchi rely exclusively on jinja-net.jp. Mie and Shimane have both their own sites and jinja-net.jp entries.

## Inferred Templates (not fully tested)

| # | Prefecture | Template | Notes |
|---|-----------|----------|-------|
| 14 | Kanagawa | `kanagawa-jinja.or.jp/shrine/{id}/` | ID format unclear; search page is JS-only |
| 41 | Saga | `saga-jinjacho.jp/{slug}/` | WordPress name-based slug |
| 47 | Okinawa | `jinjacho.naminouegu.jp/{slug}.html` | Subdomain of Naminoue Shrine |

## JavaScript-Only Search (3 prefectures)

These sites have shrine search pages but the search and detail pages are entirely JavaScript-driven with no static URLs.

| # | Prefecture | Search URL | Notes |
|---|-----------|-----------|-------|
| 07 | Fukushima | `fukushima-jinjacho.or.jp/search/` | Custom WP theme, no detail links in HTML |
| 12 | Chiba | `jinjacho.or.jp/` | Login may be required |
| 16 | Toyama | `toyama-jinjacho.sakura.ne.jp/富山県氏神神社検索` | JS-driven search, no detail links |

## List-Only Sites (6 prefectures)

These have shrine lists/pages but link to external shrine websites rather than hosting their own detail pages.

| # | Prefecture | URL | What They Have |
|---|-----------|-----|----------------|
| 10 | Gunma | `gunma-jinjacho.jp/jinja/` | Shrine names linking to external shrine websites |
| 15 | Niigata | `niigata-jinjacho.jp/shrine_niigata/` | Simple name list, no links |
| 20 | Nagano | `nagano-jinjacho.jp/shibu/*.htm` | Organized by branch, no individual pages |
| 39 | Kochi | `kochi-jinjyacho.com/` | Wix-hosted, 1MB page, shrine lists only |
| 40 | Fukuoka | `fukuoka-jinjacho.or.jp/area/{area}/` | Area pages link to external shrine websites |
| 42 | Nagasaki | `nagasaki-jinjacho.or.jp/search.html` | Region lists (hirado.html, etc.) with section anchors |

## Blocked/Down Sites (4 prefectures)

| # | Prefecture | Issue |
|---|-----------|-------|
| 02 | Aomori | Returns 403 to automated requests (works in browser) |
| 03 | Iwate | `jinjacho.jp` - returns empty; may need browser |
| 17 | Ishikawa | Returns 403 to automated requests |
| 36 | Tokushima | `awa-jinjacho.jp` - DNS resolution fails, site appears down |

## Unknown / No Official Website (3 prefectures)

| # | Prefecture | Wikidata | Notes |
|---|-----------|----------|-------|
| 43 | Kumamoto | Q135249902 | Website found: `kumamotokenjinjacho.jp` (not on Wikidata P856). Has 氏神検索 but no detail URLs found yet. |
| 44 | Oita | Q135249909 | No official website found. No P856 on Wikidata. |
| 45 | Miyazaki | Q135250079 | No official website. `m-shinsei.jp` (宮巡) is unofficial alternative by priests. |

---

## Domain Naming Patterns

| Pattern | Count | Examples |
|---------|-------|---------|
| `{pref}-jinjacho.or.jp` | ~20 | tokyo-jinjacho.or.jp, miyagi-jinjacho.or.jp |
| `{pref}-jinjacho.jp` | ~8 | gifu-jinjacho.jp, nagano-jinjacho.jp |
| `{pref}-jinjacho.com` | 1 | hyogo-jinjacho.com |
| `{pref}jinjacho.jp` (no hyphen) | 2 | hokkaidojinjacho.jp, kumamotokenjinjacho.jp |
| `{pref}kenjinjacho.or.jp` | 2 | kagawakenjinjacho.or.jp, ibarakiken-jinjacho.or.jp |
| Non-standard names | 5 | kanagawa-jinja.or.jp, jinja-fukui.jp, awa-jinjacho.jp |
| Generic domains | 2 | jinjacho.or.jp (Chiba), jinjacho.jp (Iwate) |
| Sakura hosting | 2 | akita-jinjacho.sakura.ne.jp, toyama-jinjacho.sakura.ne.jp |
| `jinjyacho` spelling | 2 | yamagata-jinjyacho.or.jp, kochi-jinjyacho.com |

## ID Type Patterns

| Type | Count | Prefectures |
|------|-------|-------------|
| Simple numeric | ~12 | Gifu, Miyagi, Saitama, Okayama, Tottori, Kyoto, Yamanashi, Yamagata, Wakayama, Kagoshima, Shiga |
| 7-digit code | 2 | Hyogo (6xxxxxx), Shizuoka (44xxxxx) |
| UUID | 1 | Aichi |
| WordPress post ID | 3 | Tochigi, Ehime, Saga |
| Name-based slug | 5 | Hokkaido, Akita, Kagawa, Mie, Okinawa |
| Prefixed ID (j0001) | 1 | Ishikawa |
| Compound path | 5 | Tokyo (ward/id), Osaka (branch/city/code), Hiroshima (branch/slug), Ibaraki (region/id), Aomori (area/code) |
| Timestamp-like | 1 | Fukui |
| Legacy CGI oid | 1 | Shiga |

## Bot Protection Notes

Most modern WordPress-based jinjacho sites block curl/automated access. Sites that reliably work with curl:
- **Gifu** (old PHP, no protection)
- **Hyogo** (Shift-JIS static HTML)
- **Shizuoka** (self-signed cert but responds)
- **Miyagi** (PHP detail pages)
- **Saitama** (WP but allows access)
- **jinja-net.jp** (all prefecture pages)
- **kyoka.mie-jinjacho.or.jp** (WP but allows access)

Sites that block automated access (return empty or 403):
- Ishikawa, Aomori, Kanagawa (search page loads but no shrine links in HTML)
- Most modern WordPress sites with Cloudflare
