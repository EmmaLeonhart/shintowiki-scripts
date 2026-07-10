# Ronsha list membership — the report Emma asked for (wiki-queue item (d))

**Report only.** Nothing emitted, nothing removed.

## The finding that collapses the problem

Emma 2026-07-10: *"Ronshas should not even have list membership."*

An Engishiki list item names its own members with **has part** statements, each carrying an
ordinal. Those targets are the **entry items** — instance of *Disputed Shikinaisha or Shikigeisha*
(806 of the 815 such items are list parts). A **Shikinai Ronsha** is a modern shrine that is merely
a *candidate* for an entry. It is not a member of the list.

| | |
|---|---:|
| items named as parts of an Engishiki list (the entries) | **2,839** |
| Ronsha claiming membership of a list | **2,277** |
| …of those, actually named as a part | **126** |
| **…of those, NOT named as a part — the junk** | **2,151** |

So the sub-classification below (one entry item vs several vs none) is beside the point: the 49
"ambiguous" and the 266 "no entry" cases are all simply Ronsha that should carry no list
membership at all. The list items were repaired after the jawiki piped-link import damage; the
shrine items were not.

Emma 2026-07-10 on the cause: *"on the Shinto Shrine wiki on Japanese Wikipedia there was a large
amount of pipe links in the list where there was a shrine that was part of another shrine, ended
up getting piped in, resulting in massive duplications that have since been fixed."*

## What remains to decide

Removing the list link from 2,151 Ronsha is a **remove-only** operation with nothing to add back.
That contradicts item (d)'s "add ONE derived from the list-entry item", which assumed the shrine
should keep a membership. Awaiting Emma's confirmation before any script is built.

The 126 Ronsha that ARE named as parts keep their membership; their statement should carry the
ordinal and neighbours the list gives.
## Result

| | |
|---|---:|
| Ronsha with a list membership | **2277** |
| **unambiguous** — one entry item, one clean statement | **1962** |
| **ambiguous** — several entry items or several ordinals | **49** |
| **no entry item reachable** | **266** |

The unambiguous ones can be migrated without a decision. The ambiguous ones are Emma's
blocker, listed in full below.

## Ambiguous — which entry's ordinal wins?

| Shrine | Kokugakuin ids | its own part-of statements | entry items and their ordinals |
|---|---|---:|---|
| [Q110915859](https://www.wikidata.org/wiki/Q110915859) Oshaku Shrine | 181573 181584 181588 181602 | 3 | List of Shikinaisha in Izu Province: [Q135039638](https://www.wikidata.org/wiki/Q135039638) Sakitamahimeno- Shrine @ 5, [Q135039642](https://www.wikidata.org/wiki/Q135039642) Hayashino- Shrine @ 14, [Q135039644](https://www.wikidata.org/wiki/Q135039644) Katasukano- Shrine @ 16, [Q134930277](https://www.wikidata.org/wiki/Q134930277) Ninomiya Shrine @ 17, [Q135039648](https://www.wikidata.org/wiki/Q135039648) Kamino- Shrine @ 20, [Q135039658](https://www.wikidata.org/wiki/Q135039658) Minamikono Shrine @ 34 |
| [Q18457651](https://www.wikidata.org/wiki/Q18457651) Watazumi Shrine | 183358 183373 183368 183372 | 5 | List of Shikinaisha in Tsushima: [Q135041526](https://www.wikidata.org/wiki/Q135041526) Watatsumi Shrine (Engishiki) @ 1, [Q135041536](https://www.wikidata.org/wiki/Q135041536) Watamiyakobimiko Shrine @ 11, [Q135041542](https://www.wikidata.org/wiki/Q135041542) Ohoshimano Shrine @ 15, [Q135041543](https://www.wikidata.org/wiki/Q135041543) Harahano Shrine @ 16, [Q135041548](https://www.wikidata.org/wiki/Q135041548) Watatsumino Shrine @ 20 |
| [Q11434131](https://www.wikidata.org/wiki/Q11434131) Ōshio Hachiman Shrine | 182210 182216 182220 182221 | 4 | List of Shikinaisha in Echizen Province: [Q135040130](https://www.wikidata.org/wiki/Q135040130) Takawokano Shrine @ 23, [Q135040139](https://www.wikidata.org/wiki/Q135040139) Ameyahoyorotsu- Shrine @ 29, [Q135040140](https://www.wikidata.org/wiki/Q135040140) Amekunitsuhikono Shrine @ 33, [Q135040141](https://www.wikidata.org/wiki/Q135040141) Amekunihimeno Shrine @ 34 |
| [Q11442606](https://www.wikidata.org/wiki/Q11442606) Ame-no-Tanagao Shrine | 183346 183347 183357 | 2 | List of Shikinaisha in Iki Island: [Q135041506](https://www.wikidata.org/wiki/Q135041506) Ame-no-Tanakawono Shrine @ 13, [Q135041507](https://www.wikidata.org/wiki/Q135041507) Ameno-tanakahimeno Shrine @ 14, [Q135041523](https://www.wikidata.org/wiki/Q135041523) Mononoheno- Shrine @ 24 |
| [Q11481363](https://www.wikidata.org/wiki/Q11481363) Jogu Shrine | 182216 182220 182221 | 2 | List of Shikinaisha in Echizen Province: [Q135040139](https://www.wikidata.org/wiki/Q135040139) Ameyahoyorotsu- Shrine @ 29, [Q135040140](https://www.wikidata.org/wiki/Q135040140) Amekunitsuhikono Shrine @ 33, [Q135040141](https://www.wikidata.org/wiki/Q135040141) Amekunihimeno Shrine @ 34 |
| [Q134927474](https://www.wikidata.org/wiki/Q134927474) Hachiman Shrine | 181576 181588 181610 | 2 | List of Shikinaisha in Izu Province: [Q135039639](https://www.wikidata.org/wiki/Q135039639) Takemikakano- Shrine @ 8, [Q135039648](https://www.wikidata.org/wiki/Q135039648) Kamino- Shrine @ 20, [Q135039666](https://www.wikidata.org/wiki/Q135039666) Takama Shrine @ 42 |
| [Q134930277](https://www.wikidata.org/wiki/Q134930277) Ninomiya Shrine | 181586 181588 181593 | 1 | List of Shikinaisha in Izu Province: [Q135039645](https://www.wikidata.org/wiki/Q135039645) Yasuno- Shrine @ 18, [Q135039648](https://www.wikidata.org/wiki/Q135039648) Kamino- Shrine @ 20, [Q135039653](https://www.wikidata.org/wiki/Q135039653) Ihanohimeno- Shrine @ 25 |
| [Q135190252](https://www.wikidata.org/wiki/Q135190252) Rokusho Shrine | 181505 181507 181506 | 3 | List of Shikinaisha in Tōtōmi Province: [Q135039595](https://www.wikidata.org/wiki/Q135039595) Takane Shrine @ 19, [Q135039596](https://www.wikidata.org/wiki/Q135039596) Rokusho Shrine @ 20, [Q135039597](https://www.wikidata.org/wiki/Q135039597) Wakayamatono Shrine @ 21 |
| [Q135192783](https://www.wikidata.org/wiki/Q135192783) Ninomiya Shrine (Tsubota) | 181586 181588 181593 | 3 | List of Shikinaisha in Izu Province: [Q135039645](https://www.wikidata.org/wiki/Q135039645) Yasuno- Shrine @ 18, [Q135039648](https://www.wikidata.org/wiki/Q135039648) Kamino- Shrine @ 20, [Q135039653](https://www.wikidata.org/wiki/Q135039653) Ihanohimeno- Shrine @ 25 |
| [Q11359018](https://www.wikidata.org/wiki/Q11359018) Kamigoryō Shrine | 180605 | 1 | List of Shikinaisha in Yamashiro Province: [Q135038772](https://www.wikidata.org/wiki/Q135038772) Izumo-no-winoheno Shrine @ 34, [Q135038773](https://www.wikidata.org/wiki/Q135038773) Izumotakanono Shrine @ 36 |
| [Q11369800](https://www.wikidata.org/wiki/Q11369800) Omi Shrine | 181852 | 1 | List of Shikinaisha in Ōmi Province: [Q135098105](https://www.wikidata.org/wiki/Q135098105) Nomino Shrine @ 68, [Q135098229](https://www.wikidata.org/wiki/Q135098229) Womino Shrine @ 72 |
| [Q11378828](https://www.wikidata.org/wiki/Q11378828) Iyo Shrine | 183265 183268 | 1 | List of Shikinaisha in Iyo Province: [Q135041429](https://www.wikidata.org/wiki/Q135041429) Iyono Shrine @ 21, [Q135041437](https://www.wikidata.org/wiki/Q135041437) Iyotsuhikono- Shrine @ 24 |
| [Q11379322](https://www.wikidata.org/wiki/Q11379322) Izanagi Shrine | 181053 | 2 | List of Shikinaisha in Settsu Province: [Q135039216](https://www.wikidata.org/wiki/Q135039216) Mishimakamono Shrine @ 32, [Q135039217](https://www.wikidata.org/wiki/Q135039217) Isanakino Shrine @ 33 |
| [Q11379324](https://www.wikidata.org/wiki/Q11379324) Izanagi Shrine | 181053 | 2 | List of Shikinaisha in Settsu Province: [Q135039216](https://www.wikidata.org/wiki/Q135039216) Mishimakamono Shrine @ 32, [Q135039217](https://www.wikidata.org/wiki/Q135039217) Isanakino Shrine @ 33 |
| [Q11390944](https://www.wikidata.org/wiki/Q11390944) Hachimangū Kinomiya Shrine | 181579 181596 | 2 | List of Shikinaisha in Izu Province: [Q135039641](https://www.wikidata.org/wiki/Q135039641) Ihare- Shrine @ 11, [Q135039655](https://www.wikidata.org/wiki/Q135039655) Ihakurawakeno- Shrine @ 28 |
| [Q11490723](https://www.wikidata.org/wiki/Q11490723) Inbe Shrine | 183192 | 2 | List of Shikinaisha in Awa Province (Tokushima): [Q135041321](https://www.wikidata.org/wiki/Q135041321) Imuheno Shrine @ 18, [Q135041330](https://www.wikidata.org/wiki/Q135041330) Amamurakumono Shrine @ 19 |
| [Q11516220](https://www.wikidata.org/wiki/Q11516220) Tsukiyomi-no-Miya (Naikū) | 181112 | 1 | List of Shikinaisha in Ise Province: [Q135039261](https://www.wikidata.org/wiki/Q135039261) Isanakino Shrine @ 4, [Q135039262](https://www.wikidata.org/wiki/Q135039262) Tsukiyomino Shrine @ 5 |
| [Q11547364](https://www.wikidata.org/wiki/Q11547364) Hibita Shrine | 181680 181680 | 1 | List of Shikinaisha in Sagami Province: [Q135039721](https://www.wikidata.org/wiki/Q135039721) Hihitano Shrine @ 5, [Q135039721](https://www.wikidata.org/wiki/Q135039721) Hihitano Shrine @ 5 |
| [Q11559099](https://www.wikidata.org/wiki/Q11559099) Kaijin Shrine | 183358 183369 183368 183370 | 4 | List of Shikinaisha in Tsushima: [Q135041526](https://www.wikidata.org/wiki/Q135041526) Watatsumi Shrine (Engishiki) @ 1, [Q135041536](https://www.wikidata.org/wiki/Q135041536) Watamiyakobimiko Shrine @ 11 |
| [Q11569577](https://www.wikidata.org/wiki/Q11569577) Katayama-hachimansha | 181414 | 1 | List of Shikinaisha in Owari Province: [Q135039518](https://www.wikidata.org/wiki/Q135039518) Toyamano Shrine @ 73, [Q135039520](https://www.wikidata.org/wiki/Q135039520) Katayamano Shrine @ 74 |
| [Q11672973](https://www.wikidata.org/wiki/Q11672973) Takabeya Shrine | 181679 | 1 | List of Shikinaisha in Sagami Province: [Q135039720](https://www.wikidata.org/wiki/Q135039720) Takaheyano Shrine @ 4, [Q135039720](https://www.wikidata.org/wiki/Q135039720) Takaheyano Shrine @ 4 |
| [Q11677110](https://www.wikidata.org/wiki/Q11677110) Kashima Amatarashi Wake Shrine | 182062 182063 182065 | 5 | List of Shikinaisha in Mutsu Province: [Q135039994](https://www.wikidata.org/wiki/Q135039994) Kashima-Itsunohikeno Shrine @ 25, [Q135039995](https://www.wikidata.org/wiki/Q135039995) Kashimawonatano Shrine @ 26 |
| [Q11677158](https://www.wikidata.org/wiki/Q11677158) Kashima Onata Shrine | 182063 | 3 | List of Shikinaisha in Mutsu Province: [Q135039994](https://www.wikidata.org/wiki/Q135039994) Kashima-Itsunohikeno Shrine @ 25, [Q135039995](https://www.wikidata.org/wiki/Q135039995) Kashimawonatano Shrine @ 26 |
| [Q11677857](https://www.wikidata.org/wiki/Q11677857) Koganeyama Shrine (Ishinomaki) | 182122 182089 | 2 | List of Shikinaisha in Mutsu Province: [Q135040009](https://www.wikidata.org/wiki/Q135040009) Kesemano Shrine @ 52, [Q135040041](https://www.wikidata.org/wiki/Q135040041) Kokaneyamano Shrine @ 85 |
| [Q134926924](https://www.wikidata.org/wiki/Q134926924) Sanai Shrine | 181613 181633 | 3 | List of Shikinaisha in Izu Province: [Q135039668](https://www.wikidata.org/wiki/Q135039668) Fumunashino Shrine @ 45, [Q135039676](https://www.wikidata.org/wiki/Q135039676) Ametsuseno- Shrine @ 65 |
| [Q134927903](https://www.wikidata.org/wiki/Q134927903) Unai Shrine | 181604 181633 | 1 | List of Shikinaisha in Izu Province: [Q135039660](https://www.wikidata.org/wiki/Q135039660) Ihatewakeno- Shrine @ 36, [Q135039676](https://www.wikidata.org/wiki/Q135039676) Ametsuseno- Shrine @ 65 |
| [Q134928742](https://www.wikidata.org/wiki/Q134928742) Nijugohashira Shrine | 181182 181186 | 2 | List of Shikinaisha in Ise Province: [Q135039292](https://www.wikidata.org/wiki/Q135039292) Nakaretano Shrine @ 75, [Q135039296](https://www.wikidata.org/wiki/Q135039296) Hichino Shrine @ 79 |
| [Q134930603](https://www.wikidata.org/wiki/Q134930603) Ryou Shrine | 181573 181605 | 1 | List of Shikinaisha in Izu Province: [Q135039638](https://www.wikidata.org/wiki/Q135039638) Sakitamahimeno- Shrine @ 5, [Q135039661](https://www.wikidata.org/wiki/Q135039661) Hotsusakeno- Shrine @ 37 |
| [Q134930633](https://www.wikidata.org/wiki/Q134930633) Habuhime Shrine (Shimoda) | 181570 181606 | 1 | List of Shikinaisha in Izu Province: [Q135039636](https://www.wikidata.org/wiki/Q135039636) Hafuhimeno- Shrine @ 2, [Q135039662](https://www.wikidata.org/wiki/Q135039662) Ohotsunoyukino- Shrine @ 38 |
| [Q135068666](https://www.wikidata.org/wiki/Q135068666) Okage Shrine (Otagi district) | 180605 | 1 | List of Shikinaisha in Yamashiro Province: [Q135038773](https://www.wikidata.org/wiki/Q135038773) Izumotakanono Shrine @ 36, [Q135038776](https://www.wikidata.org/wiki/Q135038776) Wono Shrine @ 39 |
| [Q135069931](https://www.wikidata.org/wiki/Q135069931) Kasano Shrine | 182342 | 1 | List of Shikinaisha in Kaga Province: [Q135040299](https://www.wikidata.org/wiki/Q135040299) Kasanono Shrine @ 42, [Q135040299](https://www.wikidata.org/wiki/Q135040299) Kasanono Shrine @ 42 |
| [Q135069932](https://www.wikidata.org/wiki/Q135069932) Kasano Shrine (Kaga Province) | 182342 | 1 | List of Shikinaisha in Kaga Province: [Q135040299](https://www.wikidata.org/wiki/Q135040299) Kasanono Shrine @ 42, [Q135040299](https://www.wikidata.org/wiki/Q135040299) Kasanono Shrine @ 42 |
| [Q135070063](https://www.wikidata.org/wiki/Q135070063) Ōube Hyoju Shrine (Okuno) | 182659 | 1 | List of Shikinaisha in Tajima Province: [Q135040644](https://www.wikidata.org/wiki/Q135040644) Ohofuhe- Shrine @ 45, [Q135040644](https://www.wikidata.org/wiki/Q135040644) Ohofuhe- Shrine @ 45 |
| [Q135186675](https://www.wikidata.org/wiki/Q135186675) E Shrine | 181259 181261 | 2 | List of Shikinaisha in Ise Province: [Q135039365](https://www.wikidata.org/wiki/Q135039365) Ohowino Shrine @ 152, [Q135039367](https://www.wikidata.org/wiki/Q135039367) Eno Shrine @ 154 |
| [Q135186710](https://www.wikidata.org/wiki/Q135186710) Kandate Iino Takaichi Shrine | 181268 181278 | 2 | List of Shikinaisha in Ise Province: [Q135039374](https://www.wikidata.org/wiki/Q135039374) Takaichino Shrine @ 161, [Q135039382](https://www.wikidata.org/wiki/Q135039382) Ihinono Shrine @ 171 |
| [Q135186711](https://www.wikidata.org/wiki/Q135186711) Iino Shrine | 181268 181278 | 2 | List of Shikinaisha in Ise Province: [Q135039374](https://www.wikidata.org/wiki/Q135039374) Takaichino Shrine @ 161, [Q135039382](https://www.wikidata.org/wiki/Q135039382) Ihinono Shrine @ 171 |
| [Q135193122](https://www.wikidata.org/wiki/Q135193122) Co-Enshrinement of Kuniwichino Shrine | 181711 | 1 | List of Shikinaisha in Musashi Province: [Q11404276](https://www.wikidata.org/wiki/Q11404276) Kitano Tenjinsha @ 22, [Q135098982](https://www.wikidata.org/wiki/Q135098982) Kuniwichino- Shrine @ 23 |
| [Q135193123](https://www.wikidata.org/wiki/Q135193123) Kuniichigi Shrine (Morito, Sakado) | 181711 | 1 | List of Shikinaisha in Musashi Province: [Q11404276](https://www.wikidata.org/wiki/Q11404276) Kitano Tenjinsha @ 22, [Q135098982](https://www.wikidata.org/wiki/Q135098982) Kuniwichino- Shrine @ 23 |
| [Q135194870](https://www.wikidata.org/wiki/Q135194870) Ōanamochi Miyo Shrine | 182354 182356 | 2 | List of Shikinaisha in Noto Province: [Q135040309](https://www.wikidata.org/wiki/Q135040309) Kumakafutsuarakashihikono Shrine @ 12, [Q135040311](https://www.wikidata.org/wiki/Q135040311) Ohonamochinokamikataishino Shrine @ 14 |
| [Q135195607](https://www.wikidata.org/wiki/Q135195607) Hinomisaki Shrine (branch shrine outside the precincts of Hongū Shrine) | 182793 182811 | 2 | List of Shikinaisha in Izumo Province: [Q135040778](https://www.wikidata.org/wiki/Q135040778) Nimasukarakuniitateno Shrine @ 19, [Q135040907](https://www.wikidata.org/wiki/Q135040907) Sakutano Shrine @ 38 |
| [Q135198631](https://www.wikidata.org/wiki/Q135198631) Kunitsu Shrine | 183349 183357 | 2 | List of Shikinaisha in Iki Island: [Q135041511](https://www.wikidata.org/wiki/Q135041511) Kunitsukami Shrine @ 16, [Q135041523](https://www.wikidata.org/wiki/Q135041523) Mononoheno- Shrine @ 24 |
| [Q135270117](https://www.wikidata.org/wiki/Q135270117) Ishino Shrine | 180738 | 1 | List of Shikinaisha in Yamato Province: [Q135038961](https://www.wikidata.org/wiki/Q135038961) Ishino Shrine @ 79, [Q11620954](https://www.wikidata.org/wiki/Q11620954) Katsuraki ni Imasu Honoikaduchi Shrine @ 80 |
| [Q135270129](https://www.wikidata.org/wiki/Q135270129) Wokatano Shrine | 181070 181071 | 1 | List of Shikinaisha in Settsu Province: [Q1466105](https://www.wikidata.org/wiki/Q1466105) Hirota Shrine @ 47, [Q135039222](https://www.wikidata.org/wiki/Q135039222) Wokatano Shrine @ 50 |
| [Q17228121](https://www.wikidata.org/wiki/Q17228121) Katada Shrine | 181129 181142 | 1 | List of Shikinaisha in Ise Province: [Q135039265](https://www.wikidata.org/wiki/Q135039265) Ohokunitamahimeno Shrine @ 22, [Q135039268](https://www.wikidata.org/wiki/Q135039268) Wemurano Shrine @ 35 |
| [Q22120521](https://www.wikidata.org/wiki/Q22120521) Miyake Shrine | 181260 181287 | 1 | List of Shikinaisha in Ise Province: [Q135039366](https://www.wikidata.org/wiki/Q135039366) Miyakeno Shrine @ 153, [Q135039393](https://www.wikidata.org/wiki/Q135039393) Ohokano- Shrine @ 180 |
| [Q30925511](https://www.wikidata.org/wiki/Q30925511) Sengen Shrine | 181571 181628 | 2 | List of Shikinaisha in Izu Province: [Q135039637](https://www.wikidata.org/wiki/Q135039637) Ikamuhimeno- Shrine @ 3, [Q135039674](https://www.wikidata.org/wiki/Q135039674) Homusuhino- Shrine @ 60 |
| [Q59282589](https://www.wikidata.org/wiki/Q59282589) Wanishita Shrine (Ichinomoto) | 180667 | 1 | List of Shikinaisha in Yamato Province: [Q135038818](https://www.wikidata.org/wiki/Q135038818) Wanishimono Shrine @ 8, [Q135038836](https://www.wikidata.org/wiki/Q135038836) Naratsuhiko Shrine @ 9 |
| [Q59282593](https://www.wikidata.org/wiki/Q59282593) Wanishita Shrine | 180667 | 1 | List of Shikinaisha in Yamato Province: [Q135038818](https://www.wikidata.org/wiki/Q135038818) Wanishimono Shrine @ 8, [Q135038836](https://www.wikidata.org/wiki/Q135038836) Naratsuhiko Shrine @ 9 |
| [Q98082987](https://www.wikidata.org/wiki/Q98082987) Amanokaguyama Shrine | 180853 180859 | 2 | List of Shikinaisha in Yamato Province: [Q135039029](https://www.wikidata.org/wiki/Q135039029) Unehino- Shrine @ 194, [Q135039033](https://www.wikidata.org/wiki/Q135039033) Amanokakoyamano- Shrine @ 200 |

## No entry item reachable

| Shrine | Kokugakuin ids | its own part-of statements |
|---|---|---:|
| [Q107020402](https://www.wikidata.org/wiki/Q107020402) Nishi Honden, Namura Shrine | 181815 | 1 |
| [Q112152942](https://www.wikidata.org/wiki/Q112152942) Yatsuki Tsutsukowake Shrine | 182038 | 1 |
| [Q11361262](https://www.wikidata.org/wiki/Q11361262) Shimotate Matsubara Shrine | 181736 | 2 |
| [Q11371267](https://www.wikidata.org/wiki/Q11371267) Futagami-Imizu Shrine | 182393 | 2 |
| [Q11404276](https://www.wikidata.org/wiki/Q11404276) Kitano Tenjinsha | 181710 181707 | 2 |
| [Q11415986](https://www.wikidata.org/wiki/Q11415986) Mukō Shrine | 180578 | 1 |
| [Q11427995](https://www.wikidata.org/wiki/Q11427995) Tsutsumine Shrine | 180922 | 1 |
| [Q11428793](https://www.wikidata.org/wiki/Q11428793) Shioyuhiko Shrine | 182144 | 1 |
| [Q114593121](https://www.wikidata.org/wiki/Q114593121) Baba Tsutsukowake Shrine | 182038 | 1 |
| [Q11465762](https://www.wikidata.org/wiki/Q11465762) Miyake Shrine (Matsubara) | 180966 | 1 |
| [Q11469988](https://www.wikidata.org/wiki/Q11469988) Yamatsuteru Shrine | 181833 | 1 |
| [Q11479957](https://www.wikidata.org/wiki/Q11479957) Tatsumi Shrine | 180946 | 1 |
| [Q11486118](https://www.wikidata.org/wiki/Q11486118) Watarai Kunimi Shrine | 181143 | 1 |
| [Q11488771](https://www.wikidata.org/wiki/Q11488771) Mii Shrine | 181948 | 1 |
| [Q11490808](https://www.wikidata.org/wiki/Q11490808) Shijiki Shrine | 183317 | 1 |
| [Q11492453](https://www.wikidata.org/wiki/Q11492453) Ena Shrine | 181960 | 1 |
| [Q11495515](https://www.wikidata.org/wiki/Q11495515) Narumi Shrine | 181451 | 1 |
| [Q11523053](https://www.wikidata.org/wiki/Q11523053) Murakuni Masumida Shrine | 181946 | 1 |
| [Q11544726](https://www.wikidata.org/wiki/Q11544726) Kushida Shrine (Matsusaka) | 181161 | 1 |
| [Q11556984](https://www.wikidata.org/wiki/Q11556984) Azai Shrine (Ichinomiya) | 181356 | 2 |
| [Q11584766](https://www.wikidata.org/wiki/Q11584766) Isonokamifutsumitama Shrine | 183069 | 1 |
| [Q11597109](https://www.wikidata.org/wiki/Q11597109) Hotaka Shrine | 181975 | 1 |
| [Q11597744](https://www.wikidata.org/wiki/Q11597744) Kamado Shrine | 183297 | 1 |
| [Q11603933](https://www.wikidata.org/wiki/Q11603933) Komori Katte Shrine | 181382 | 1 |
| [Q11608173](https://www.wikidata.org/wiki/Q11608173) Soja | 183089 | 1 |
| [Q11608777](https://www.wikidata.org/wiki/Q11608777) Migukurumitama Shrine | 180880 180885 | 2 |
| [Q11610732](https://www.wikidata.org/wiki/Q11610732) Miminashi Yamaguchi Shrine | 180854 180851 | 1 |
| [Q11612066](https://www.wikidata.org/wiki/Q11612066) Nobono Shrine | 181254 | 1 |
| [Q11613316](https://www.wikidata.org/wiki/Q11613316) Yodo Shrine | 180571 | 1 |
| [Q11631426](https://www.wikidata.org/wiki/Q11631426) Konda Hachimangū | 180959 | 1 |
| [Q11646130](https://www.wikidata.org/wiki/Q11646130) Nomi Shrine | 181041 | 1 |
| [Q11647974](https://www.wikidata.org/wiki/Q11647974) Kanasana Shrine | 181728 | 1 |
| [Q11668370](https://www.wikidata.org/wiki/Q11668370) Komagata Shrine | 182112 | 1 |
| [Q11675600](https://www.wikidata.org/wiki/Q11675600) Kamo Shrine (Sakaide) | 183228 | 1 |
| [Q11677124](https://www.wikidata.org/wiki/Q11677124) Kashima Miko Shrine | 182100 | 1 |
| [Q119929618](https://www.wikidata.org/wiki/Q119929618) Inashimo Shrine | 181641 | 1 |
| [Q119929663](https://www.wikidata.org/wiki/Q119929663) Hegurinoiwatoko Shrine | 180695 | 1 |
| [Q134893135](https://www.wikidata.org/wiki/Q134893135) Hayatamawakenomikoto Shrine | 181578 181573 | 2 |
| [Q134926963](https://www.wikidata.org/wiki/Q134926963) Himemiya Shrine | 181599 181591 | 2 |
| [Q135038778](https://www.wikidata.org/wiki/Q135038778) Matono Shrine | 180610 | 1 |
| [Q135038791](https://www.wikidata.org/wiki/Q135038791) Mahatakino Shrine | 180625 | 1 |
| [Q135038843](https://www.wikidata.org/wiki/Q135038843) Amenoihasuhino Shrine | 180681 | 1 |
| [Q135039036](https://www.wikidata.org/wiki/Q135039036) Shiratsutsumino Shrine | 180869 | 1 |
| [Q135039161](https://www.wikidata.org/wiki/Q135039161) Kaden Shrine | 180974 | 1 |
| [Q135039173](https://www.wikidata.org/wiki/Q135039173) Ahano Shrine | 180996 | 1 |
| [Q135039188](https://www.wikidata.org/wiki/Q135039188) Wokamino Shrine | 181012 | 1 |
| [Q135039229](https://www.wikidata.org/wiki/Q135039229) Utsukano Shrine | 181084 | 1 |
| [Q135039254](https://www.wikidata.org/wiki/Q135039254) Ida Shrine | 181101 | 1 |
| [Q135039274](https://www.wikidata.org/wiki/Q135039274) Take Shrine | 181163 | 1 |
| [Q135039297](https://www.wikidata.org/wiki/Q135039297) Sakikurusuno Shrine co-EnShrinement | 181187 | 1 |
| [Q135039301](https://www.wikidata.org/wiki/Q135039301) Isawano Shrine | 181191 | 1 |
| [Q135039309](https://www.wikidata.org/wiki/Q135039309) Ironouheno Shrine | 181200 | 1 |
| [Q135039310](https://www.wikidata.org/wiki/Q135039310) Ohokushino Shrine | 181203 | 1 |
| [Q135039315](https://www.wikidata.org/wiki/Q135039315) Ohomuwano Shrine Co-Enshrinement | 181209 | 1 |
| [Q135039385](https://www.wikidata.org/wiki/Q135039385) Takawokano Shrine | 181280 | 1 |
| [Q135039477](https://www.wikidata.org/wiki/Q135039477) Asawino Shrine | 181356 | 2 |
| [Q135039530](https://www.wikidata.org/wiki/Q135039530) Kahashimano Shrine | 181427 | 1 |
| [Q135039533](https://www.wikidata.org/wiki/Q135039533) Kaneno Shrine | 181430 | 1 |
| [Q135039541](https://www.wikidata.org/wiki/Q135039541) Oi Shrine | 181438 | 1 |
| [Q135039545](https://www.wikidata.org/wiki/Q135039545) Ishitsukurino Shrine | 181441 | 1 |
| [Q135039548](https://www.wikidata.org/wiki/Q135039548) Shimotsuchikamano Shrine | 181444 | 1 |
| [Q135039737](https://www.wikidata.org/wiki/Q135039737) Ihahino Shrine | 181706 | 1 |
| [Q135039836](https://www.wikidata.org/wiki/Q135039836) Himetano Shrine | 181856 | 1 |
| [Q135039883](https://www.wikidata.org/wiki/Q135039883) Ohosakino Shrine | 181907 | 1 |
| [Q135039944](https://www.wikidata.org/wiki/Q135039944) Yamaihe Shrine | 182009 | 1 |
| [Q135039996](https://www.wikidata.org/wiki/Q135039996) Kashima Shrine | 182066 | 1 |
| [Q135040039](https://www.wikidata.org/wiki/Q135040039) Oroheshino Shrine | 182117 | 1 |
| [Q135040071](https://www.wikidata.org/wiki/Q135040071) Karitahimeno Shrine | 182161 | 1 |
| [Q135040120](https://www.wikidata.org/wiki/Q135040120) Asomurano- Shrine | 182202 | 1 |
| [Q135040262](https://www.wikidata.org/wiki/Q135040262) Tokarino Shrine | 182303 | 1 |
| [Q135040434](https://www.wikidata.org/wiki/Q135040434) Awomino Shrine | 182429 | 1 |
| [Q135040469](https://www.wikidata.org/wiki/Q135040469) Ichikahano Shrine | 182461 | 1 |
| [Q135040470](https://www.wikidata.org/wiki/Q135040470) Ishiwino Shrine | 182462 | 1 |
| [Q135040493](https://www.wikidata.org/wiki/Q135040493) Kamunono Shrine | 182487 | 1 |
| [Q135040514](https://www.wikidata.org/wiki/Q135040514) Samiyano Shrine | 182519 | 1 |
| [Q135040515](https://www.wikidata.org/wiki/Q135040515) Karinono Shrine | 182520 | 1 |
| [Q135040524](https://www.wikidata.org/wiki/Q135040524) Ashii Shrine | 182531 | 1 |
| [Q135040566](https://www.wikidata.org/wiki/Q135040566) Urano Shrine | 182571 | 1 |
| [Q135040569](https://www.wikidata.org/wiki/Q135040569) Miheno Shrine | 182575 | 1 |
| [Q135040651](https://www.wikidata.org/wiki/Q135040651) Himefuno Shrine | 182668 | 1 |
| [Q135041137](https://www.wikidata.org/wiki/Q135041137) Sukanonoamenotakarawakakono- Shrine | 182987 | 1 |
| [Q135041148](https://www.wikidata.org/wiki/Q135041148) Mikatatano Shrine | 183010 | 1 |
| [Q135041185](https://www.wikidata.org/wiki/Q135041185) Kutono Shrine | 183058 | 1 |
| [Q135041188](https://www.wikidata.org/wiki/Q135041188) Nakatano Shrine | 183060 | 1 |
| [Q135041199](https://www.wikidata.org/wiki/Q135041199) Fuse Shrine | 183070 | 1 |
| [Q135041202](https://www.wikidata.org/wiki/Q135041202) Kamineno Shrine | 183071 | 1 |
| [Q135041208](https://www.wikidata.org/wiki/Q135041208) Ise Shrine | 183076 | 1 |
| [Q135041216](https://www.wikidata.org/wiki/Q135041216) Momoiyamano Shrine | 183085 | 1 |
| [Q135041245](https://www.wikidata.org/wiki/Q135041245) Hikosasukino Shrine | 183109 | 1 |
| [Q135041250](https://www.wikidata.org/wiki/Q135041250) Takao- Shrine | 183115 | 1 |
| [Q135041251](https://www.wikidata.org/wiki/Q135041251) Warihimeno Shrine | 183117 | 1 |
| [Q135041288](https://www.wikidata.org/wiki/Q135041288) Kamo Shrine | 183166 | 1 |
| [Q135041389](https://www.wikidata.org/wiki/Q135041389) Uhei Shrine | 183232 | 1 |
| [Q135041470](https://www.wikidata.org/wiki/Q135041470) Materafuno Shrine | 183298 | 1 |
| [Q135041502](https://www.wikidata.org/wiki/Q135041502) Sashifutsuno Shrine | 183343 | 1 |
| [Q135069537](https://www.wikidata.org/wiki/Q135069537) Hikawa Shrine | 181707 | 1 |
| [Q135070196](https://www.wikidata.org/wiki/Q135070196) Ikeda Shrine | 183088 | 1 |
| [Q135070326](https://www.wikidata.org/wiki/Q135070326) Uhei Shrine Hongu | 183232 | 1 |
| [Q135098886](https://www.wikidata.org/wiki/Q135098886) Nakarano Shrine | 180937 | 1 |
| [Q135098895](https://www.wikidata.org/wiki/Q135098895) Ame-no-Mikumari-toyoura Shrine | 181030 | 1 |
| [Q135098903](https://www.wikidata.org/wiki/Q135098903) Mitekurano Shrine | 181050 | 1 |
| [Q135098916](https://www.wikidata.org/wiki/Q135098916) Hatorinoitomano Shrine | 181166 | 1 |
| [Q135098926](https://www.wikidata.org/wiki/Q135098926) Nakaretanouheno Shrine | 181184 | 1 |
| [Q135098983](https://www.wikidata.org/wiki/Q135098983) Ishitsukurino Shrine | 181875 | 1 |
| [Q135099507](https://www.wikidata.org/wiki/Q135099507) Kusumi Shrine | 180928 | 1 |
| [Q135185020](https://www.wikidata.org/wiki/Q135185020) Kataoka Shrine Former Site | 180724 | 1 |
| [Q135185533](https://www.wikidata.org/wiki/Q135185533) Kusumi Shrine former site | 180928 | 1 |
| [Q135185575](https://www.wikidata.org/wiki/Q135185575) Nagara Shrine former site | 180937 | 1 |
| [Q135185616](https://www.wikidata.org/wiki/Q135185616) Tsurumino Shrine former site | 180950 | 1 |
| [Q135185626](https://www.wikidata.org/wiki/Q135185626) Konda Hachimangū former site | 180959 | 1 |
| [Q135185635](https://www.wikidata.org/wiki/Q135185635) Miyake Shrine (Matsubara) former site | 180966 | 1 |
| [Q135185681](https://www.wikidata.org/wiki/Q135185681) Co-Enshrinement of Hyōzu Shrine | 180996 180995 | 1 |
| [Q135185682](https://www.wikidata.org/wiki/Q135185682) Awa Shrine Site | 180996 | 1 |
| [Q135185705](https://www.wikidata.org/wiki/Q135185705) Akaruhimenomikoto Shrine former site | 181029 | 1 |
| [Q135186128](https://www.wikidata.org/wiki/Q135186128) Watara Kunimi Shrine former site | 181143 | 1 |
| [Q135186175](https://www.wikidata.org/wiki/Q135186175) Kushida Shrine (Matsusaka) former site | 181161 | 1 |
| [Q135186179](https://www.wikidata.org/wiki/Q135186179) Take Shrine former site | 181163 | 1 |
| [Q135186180](https://www.wikidata.org/wiki/Q135186180) Take Shrine former site | 181163 | 1 |
| [Q135186191](https://www.wikidata.org/wiki/Q135186191) Hatorinoitomano Shrine former site | 181166 | 1 |
| [Q135186310](https://www.wikidata.org/wiki/Q135186310) Nakaretanouheno Shrine Former site | 181184 | 1 |
| [Q135186331](https://www.wikidata.org/wiki/Q135186331) Sakikurusuno Shrine former site | 181187 | 1 |
| [Q135186341](https://www.wikidata.org/wiki/Q135186341) Isawano Shrine former site | 181191 | 1 |
| [Q135186407](https://www.wikidata.org/wiki/Q135186407) Ironouheno Shrine former site | 181200 | 1 |
| [Q135186416](https://www.wikidata.org/wiki/Q135186416) Ohokushino Shrine former site | 181203 | 1 |
| [Q135186425](https://www.wikidata.org/wiki/Q135186425) Ohomuwano Shrine former site | 181209 | 1 |
| [Q135186728](https://www.wikidata.org/wiki/Q135186728) Takawokano Shrine former site | 181280 | 1 |
| [Q135187134](https://www.wikidata.org/wiki/Q135187134) Komori Katte Tenjin-sha | 181382 | 1 |
| [Q135190167](https://www.wikidata.org/wiki/Q135190167) Narumi Shrine former site | 181451 | 1 |
| [Q135190203](https://www.wikidata.org/wiki/Q135190203) Kasumekasuga Shrine | 181476 | 1 |
| [Q135190207](https://www.wikidata.org/wiki/Q135190207) Kumaku Shrine (subshrine) | 181477 | 1 |
| [Q135190209](https://www.wikidata.org/wiki/Q135190209) Kumaku Shrine (subshrine 2) | 181477 | 1 |
| [Q135190217](https://www.wikidata.org/wiki/Q135190217) Toga Shrine okumiya | 181482 | 1 |
| [Q135190221](https://www.wikidata.org/wiki/Q135190221) Ishimaki Shrine (Shimosha) | 181485 | 1 |
| [Q135192598](https://www.wikidata.org/wiki/Q135192598) Kaba Shinmeigu Shrine | 181512 | 1 |
| [Q135192726](https://www.wikidata.org/wiki/Q135192726) Inane Shrine (Haiden) | 181574 | 1 |
| [Q135192727](https://www.wikidata.org/wiki/Q135192727) Inane Shrine (Honden) | 181574 | 1 |
| [Q135193327](https://www.wikidata.org/wiki/Q135193327) Ihahino Shrine former site | 181706 | 1 |
| [Q135193340](https://www.wikidata.org/wiki/Q135193340) Tamashiki Shrine | 181713 | 1 |
| [Q135193341](https://www.wikidata.org/wiki/Q135193341) Kisai Castle Ruins | 181713 | 1 |
| [Q135193348](https://www.wikidata.org/wiki/Q135193348) Obusuma Shrine former site | 181715 | 1 |
| [Q135193364](https://www.wikidata.org/wiki/Q135193364) Nireyama Shrine | 181720 | 1 |
| [Q135193365](https://www.wikidata.org/wiki/Q135193365) Shōtengū | 181720 | 1 |
| [Q135193366](https://www.wikidata.org/wiki/Q135193366) Nireyama Shrine | 181720 | 1 |
| [Q135193369](https://www.wikidata.org/wiki/Q135193369) Nagahatabe Shrine former site | 181722 | 1 |
| [Q135193370](https://www.wikidata.org/wiki/Q135193370) Nagahatabe Shrine former site | 181722 | 1 |
| [Q135193395](https://www.wikidata.org/wiki/Q135193395) Kanasana Shrine former site | 181728 | 1 |
| [Q135193397](https://www.wikidata.org/wiki/Q135193397) Takagi Shrine former site | 181729 | 1 |
| [Q135193398](https://www.wikidata.org/wiki/Q135193398) Iko‑no‑Hayamitama Hime Shrine | 181730 | 1 |
| [Q135193399](https://www.wikidata.org/wiki/Q135193399) Iko-no-hayamitama Hime-no Shrine former site | 181730 | 1 |
| [Q135193515](https://www.wikidata.org/wiki/Q135193515) Kojino Shrine Kamisha | 181809 | 1 |
| [Q135193516](https://www.wikidata.org/wiki/Q135193516) Kojino Shrine | 181809 | 1 |
| [Q135193523](https://www.wikidata.org/wiki/Q135193523) Nagasun Shrine | 181815 | 1 |
| [Q135193631](https://www.wikidata.org/wiki/Q135193631) Yamatsuteru Shrine | 181833 | 1 |
| [Q135193657](https://www.wikidata.org/wiki/Q135193657) Kamikoso Shrine | 181844 | 1 |
| [Q135193658](https://www.wikidata.org/wiki/Q135193658) Kawamichi Shrine | 181844 | 1 |
| [Q135193669](https://www.wikidata.org/wiki/Q135193669) Himetano Shrine former site | 181856 | 1 |
| [Q135193705](https://www.wikidata.org/wiki/Q135193705) Ishitsukurino Shrine former site | 181875 | 1 |
| [Q135193764](https://www.wikidata.org/wiki/Q135193764) Hioki Shrine | 181904 | 1 |
| [Q135193765](https://www.wikidata.org/wiki/Q135193765) Sakanami Shrine | 181904 | 1 |
| [Q135193774](https://www.wikidata.org/wiki/Q135193774) Ohosakino Shrine former site | 181907 | 1 |
| [Q135193944](https://www.wikidata.org/wiki/Q135193944) Murakuni Masumida Shrine Former Site | 181946 | 1 |
| [Q135193949](https://www.wikidata.org/wiki/Q135193949) Mii Shrine former site | 181948 | 1 |
| [Q135193982](https://www.wikidata.org/wiki/Q135193982) Ena Shrine | 181960 | 1 |
| [Q135194114](https://www.wikidata.org/wiki/Q135194114) Arei Shrine okumiya | 181974 | 1 |
| [Q135194118](https://www.wikidata.org/wiki/Q135194118) Hotaka Shrine okumiya | 181975 | 1 |
| [Q135194158](https://www.wikidata.org/wiki/Q135194158) Nakatanino Shrine Kamisha | 181981 | 1 |
| [Q135194159](https://www.wikidata.org/wiki/Q135194159) Nakatanino Shrine Shimosha | 181981 | 1 |
| [Q135194194](https://www.wikidata.org/wiki/Q135194194) Higanotome Shrine | 181984 | 1 |
| [Q135194198](https://www.wikidata.org/wiki/Q135194198) Higanotome Shrine | 181984 | 1 |
| [Q135194261](https://www.wikidata.org/wiki/Q135194261) Yamaihe Shrine okumiya | 182009 | 1 |
| [Q135194309](https://www.wikidata.org/wiki/Q135194309) Taga Shrine (Takasaki, Tagajō) | 182051 | 1 |
| [Q135194310](https://www.wikidata.org/wiki/Q135194310) Taga Shrine | 182051 | 1 |
| [Q135194311](https://www.wikidata.org/wiki/Q135194311) Taga Shrine | 182051 | 1 |
| [Q135194312](https://www.wikidata.org/wiki/Q135194312) Taga Shrine (Ichikawa, Tagajō City) | 182051 | 1 |
| [Q135194336](https://www.wikidata.org/wiki/Q135194336) Kuronuma Shrine (Oyamadoden, Fukushima City) | 182067 | 1 |
| [Q135194337](https://www.wikidata.org/wiki/Q135194337) Kuronuma Shrine (Kanazawa, Matsukawa) | 182067 | 1 |
| [Q135194339](https://www.wikidata.org/wiki/Q135194339) Kuronuma Shrine | 182067 | 1 |
| [Q135194402](https://www.wikidata.org/wiki/Q135194402) Kashima Miko Shrine Former Site | 182100 | 1 |
| [Q135194429](https://www.wikidata.org/wiki/Q135194429) Komagata Shrine okumiya | 182112 | 1 |
| [Q135194431](https://www.wikidata.org/wiki/Q135194431) Oroheshino Shrine former site | 182117 | 1 |
| [Q135194471](https://www.wikidata.org/wiki/Q135194471) Shioyuhiko Shrine okumiya | 182144 | 1 |
| [Q135194485](https://www.wikidata.org/wiki/Q135194485) Karitahimeno Shrine former site | 182161 | 1 |
| [Q135194508](https://www.wikidata.org/wiki/Q135194508) Asomurano- Shrine former site | 182202 | 1 |
| [Q135194773](https://www.wikidata.org/wiki/Q135194773) Shirayama Hime Shrine okumiya | 182321 | 1 |
| [Q135194890](https://www.wikidata.org/wiki/Q135194890) Noto Ikutama-hiko Shrine (Keta Hongū) | 182365 | 1 |
| [Q135194892](https://www.wikidata.org/wiki/Q135194892) Noto Ikutama-hiko Shrine | 182365 | 1 |
| [Q135194893](https://www.wikidata.org/wiki/Q135194893) Notobu Shrine | 182365 | 1 |
| [Q135194934](https://www.wikidata.org/wiki/Q135194934) Suzu Shrine Takakuragu | 182383 | 1 |
| [Q135194935](https://www.wikidata.org/wiki/Q135194935) Suzu Shrine Kinbungu | 182383 | 1 |
| [Q135194936](https://www.wikidata.org/wiki/Q135194936) Suzu Shrine okumiya | 182383 | 1 |
| [Q135194949](https://www.wikidata.org/wiki/Q135194949) Hime Shrine (Oyabe) | 182390 | 1 |
| [Q135194951](https://www.wikidata.org/wiki/Q135194951) Hime Shrine (Yanase, Tonami) | 182390 | 1 |
| [Q135194952](https://www.wikidata.org/wiki/Q135194952) Hime Shrine (Shimonakajo, Tonami) | 182390 | 1 |
| [Q135194953](https://www.wikidata.org/wiki/Q135194953) Hime Shrine (Nanto) | 182390 | 1 |
| [Q135194956](https://www.wikidata.org/wiki/Q135194956) Motoogami Shrine | 182391 | 1 |
| [Q135195009](https://www.wikidata.org/wiki/Q135195009) Sugihara Shrine (Yao Town, Toyama City) | 182410 | 1 |
| [Q135195010](https://www.wikidata.org/wiki/Q135195010) Sugihara Shrine (Taya, Fuchu Town) | 182410 | 1 |
| [Q135195012](https://www.wikidata.org/wiki/Q135195012) Sugihara Shrine (Hamako, Fuchu Town) | 182410 | 1 |
| [Q135195016](https://www.wikidata.org/wiki/Q135195016) Ichihara Shrine (Shimmei, Namerikawa City) | 182414 | 1 |
| [Q135195017](https://www.wikidata.org/wiki/Q135195017) Ichihara Shrine (Yanagihara, Namerikawa City) | 182414 | 1 |
| … | | 66 more |

---

# Script 2 built, 2026-07-10 — and what it refuses to touch

`modern-quickstatements/generate_list_membership_removals.py` (REMOVE-ONLY, **unregistered**,
19 tests) takes the Engishiki list link away from every Ronsha the list does not name. Run it by
hand; it writes `list_membership_removals.txt` and submits nothing.

Measured against live Wikidata:

| | |
|---|---:|
| Ronsha claiming membership of an Engishiki list | **2,277** |
| …the list names as a part — kept, script 1's business | **126** |
| …the list does not name — removed | **2,151** |
| removal lines emitted (duplicates get one line each) | **2,236** |

Each Ronsha claims exactly one list, and no item is in both the keep and the remove set. That
matters because **QuickStatements removes by value, not by statement id**: `-Q1|P361|Qlist` deletes
*a* statement pointing at `Qlist`, and on an item holding both a clean membership and junk pointing
at the same list, it could take the clean one. The script checks the property per (item, list) pair
at the moment it runs, and then re-checks it over the finished lines, rather than trusting that
today's data stays true.

## The 30 statements nothing can clean

**22 of the 126 named parts carry the identical `part of` statement two or three times over** — the
same import damage, on the items that survived it. `Q11631810` has three; twenty-one others have
two.

Script 1 adds the ordinal, the neighbours and the references to one of them. Script 2 refuses to
remove any of them, because a value-matched removal on an item the list names is precisely the
destructive case. And QuickStatements offers no way to say *"remove this statement and not its
identical twin"*.

So the pipeline cannot fix these, and the only mechanism that could is a browser remove-and-re-add,
per item. **Emma 2026-07-10: report only, leave them.** Three statements saying the same true thing
are untidy, not wrong.

| item | list | statements |
|---|---|---:|
| Q11631810 | Q11368560 | 3 |
| Q135039477 · Q11433065 · Q11556984 · Q17225818 and 17 others | various | 2 |
