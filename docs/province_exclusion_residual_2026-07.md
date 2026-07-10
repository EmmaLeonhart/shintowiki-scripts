# Province-exclusion residual — what the batch does NOT touch

2026-07-09. Companion to `generate_province_exclusions.py` (script 1, ADD-only) and
`generate_province_exclusion_removals.py` (script 2, SPARQL-gated). Everything here is
**reported, not edited**.

## 1. The seven no-class exclusions — there is no general criterion

Emma asked whether these seven need "a criterion that we need to add generally". They do not:
they are excluded for at least **four different reasons**, and three of them carry
`P31 = Shikinaisha (Q134917286)`, which contradicts being excluded from the Shikinaisha list
at all. A blanket criterion would paper over four distinct data problems.

| Shrine | On list | What it actually is |
|---|---|---|
| `Q11566292` Takihara-no-miya | Ise | **Is** Shikinaisha. A *betsugū* + `Shikinai Subshrine (Q135100459)` of Ise — excluded because it's a sub-shrine, not a separate list entry. |
| `Q11608851` Miwa Shrine | Shinano | **Is** Shikinaisha. Description says "described by Nihon Sandai Jitsuroku" — i.e. it is a **kokushi genzaisha** but lacks `P31 = Q118304363`. |
| `Q11572397` Tamatsukuriyu Shrine | Izumo | **Is** Shikinaisha (`Shikinai Shōsha`, `Kokuhei-sha`). Why it is on an exclusion list is unexplained. |
| `Q11358379` Kamiichinomiya Ōawa Shrine | Awa (Tokushima) | `P31 = Shikinai Ronsha (Q135022904)` — a *disputed candidate*. Exclusion is arguably correct, but the reason is "disputed", not any of our three classes. |
| `Q11438245` Ōishi Shrine | Harima | `P31 = Wikimedia article covering multiple topics (Q21484471)`. Not one shrine — a combined article about shrines in Akō **and** Kyoto. |
| `Q3594036` Ōmiya Hachiman Shrine | **Musashi** | Described as a shrine in **Hyōgo Prefecture**. Musashi is Tokyo/Saitama. Either the item or the list membership is wrong. |
| `Q135112892` Ōmuroyama Sengen Shrine | Izu | A plain `Shinto shrine` with no ranking and no class at all. |

**Recommendation:** no criterion. Three of these (Takihara-no-miya, Miwa, Tamatsukuriyu) need a
decision about whether a Shikinaisha may appear on its own list's `P3113`; `Ōishi Shrine` needs
splitting or delisting; `Ōmiya Hachiman Shrine` needs its province checked; `Miwa Shrine` should
probably gain `P31 = kokushi genzaisha`.

## 2. Six cross-list conflicts — only two are errors

A shrine already excluded on a different province's list than its coordinates indicate.

| Shrine | Coords say | Currently listed on | Verdict |
|---|---|---|---|
| `Q11509681` Himure Hachimangū | Ōmi (21 km from any other province) | **Etchū** | **Error.** Script 2 removes it, after the Ōmi add lands. |
| `Q11605711` Shibi Shrine | Satsuma | **Izumi Province** (~600 km away) | **Error.** Script 2 removes it, after the Satsuma add lands. |
| `Q11441628` Osaka Gokoku Shrine | Kawachi (1.0 km from boundary) | Settsu | **Polygon is wrong** — see §3. Existing Settsu statement is correct. Untouched. |
| `Q11451877` Munakata Shrine | Yamashiro (5.4 km) | Imperial Palace / Heian-kyō | Out of scope — Emma: *"Just don't do it. That one is solved."* Untouched. |
| `Q11513659` Kasuga Shrine (Kitakyushu) | Chikuzen (1.1 km from boundary) | Buzen | Border case; data cannot adjudicate. Untouched. |
| `Q11432216` Oi Shrine (Shimada) | Tōtōmi (5.8 km) | Suruga | Border case (the Ōi River *was* the boundary). Untouched. |

## 3. The boundary data is wrong across southern Osaka

Probing the merged polygons against known landmarks:

| Point | Truth | Dataset says |
|---|---|---|
| Sumiyoshi Taisha — **the ichinomiya of Settsu** | Settsu | **河内 (Kawachi)** ✗ |
| Osaka Gokoku Shrine (Suminoe-ku) | Settsu | **河内 (Kawachi)** ✗ |
| Osaka Castle (Chūō-ku) | Settsu | 摂津 ✓ |
| Shitennō-ji (Tennōji-ku) | Settsu | 摂津 ✓ |
| Hiraoka Shrine (Higashiōsaka) | Kawachi | 河内 ✓ |
| Mozu tombs (Sakai) | Izumi | 和泉 ✓ |

The 河内 polygon over-extends westward across Sumiyoshi-ku and Suminoe-ku. Any `河内`
assignment in that corridor is suspect. This is why script 2 does **not** act on
Osaka Gokoku Shrine.

## 4. Twenty-one borderline assignments (emitted anyway, per Emma)

These 21 of the 113 new exclusions lie within 3 km of a neighbouring province — inside the
error margin just demonstrated. Emma 2026-07-09 chose to **emit all 111** rather than hold them,
so they are in the batch; this table exists so they can be found again.

`Q135194773` 加賀/飛騨 0.02 km · `Q3200625` 筑後/肥前 0.15 · `Q705121` 摂津/山城 0.7 ·
`Q500763` 備前/備中 0.73 · `Q246455` 大和/河内 0.78 · `Q11441628` 河内/和泉 1.01 ·
`Q11647974` 武蔵/上野 1.06 · `Q712617` 長門/豊前 1.2 · `Q11282543` 筑後/肥前 1.35 ·
`Q705949` 河内/摂津 1.41 · `Q11370831` 長門/豊前 1.5 · `Q704622` 大隅/日向 1.57 ·
`Q11665771` 筑前/豊前 1.58 · `Q11577728` 豊前/長門 1.61 · `Q11405620` 肥前/筑後 1.87 ·
`Q3082076` 近江/山城 2.26 · `Q656451` 近江/山城 2.34 · `Q11573763` 長門/周防 2.38 ·
`Q140190511` 播磨/備前 2.38 · `Q11616915` 豊前/豊後 2.49 · `Q11554359` 近江/伊賀 2.74

`Q705949` (河内, 1.41 km from 摂津) sits in the same corridor as Sumiyoshi Taisha and is the
most likely of these to be wrong.

## 5. Seven shrines outside every province — correctly so

Hokkaidō (6) and Okinawa (1) have no Engishiki list. Nearest province and distance:
Hakodate Hachiman 28.6 km · Naminoue-gū 116 km · Tarumaezan 136 km · Hokkaidō Jingū 171 km ·
Sumiyoshi (Otaru) 182 km · Obihiro 220 km · Kamikawa 269 km.

Two further shrines *were* outside every polygon because the Bakumatsu data omits their
islands, and are now named exceptions in `ISLAND_EXCEPTIONS`: Aoshima Shrine (0.3 km → Hyūga)
and Koganeyama Shrine (1.5 km → Mutsu, Kinkasan island).
