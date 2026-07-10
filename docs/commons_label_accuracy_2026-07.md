# Commons → English-label accuracy (2026-07)

**Report only.** Grades `commons_normalize` against enwiki titles for Japanese shrines + temples. No edits proposed. Regenerate: `modern-quickstatements/report_commons_label_accuracy.py`.

| | |
|---|---:|
| in-scope items (Commons category) | 7997 |
| non-romaji Commons name (out of scope — kana stage handles) | 4 |
| gradeable (romaji Commons name + enwiki title) | 937 |
| **exact** | 737 |
| **macron-only** (acceptable) | 109 |
| **mismatch** (real failure) | 91 |
| **rejected** (normalizer returned nothing) | 0 |

**Core-reading accuracy = 90.3%** (exact + macron-only, over gradeable).

## Mismatches — the real failures

| item | Commons | candidate | enwiki |
|---|---|---|---|
| [Q3594054](https://www.wikidata.org/wiki/Q3594054) | Category:Otasan-jinja | Otasan Shrine | Ōta Shrine |
| [Q3698846](https://www.wikidata.org/wiki/Q3698846) | Category:Onbashira Festival | Onbashira Festival Shrine | Onbashira |
| [Q3936229](https://www.wikidata.org/wiki/Q3936229) | Category:Taichung Shrine | Taichung Shrine | Taichu Jinja |
| [Q4696584](https://www.wikidata.org/wiki/Q4696584) | Category:Aichiken-Gokoku-jinja | Aichiken-Gokoku Shrine | Aichi Gokoku Shrine |
| [Q10863796](https://www.wikidata.org/wiki/Q10863796) | Category:Ichinomiya nukisaki-jinja | Ichinomiya nukisaki Shrine | Nukisaki Shrine |
| [Q10877366](https://www.wikidata.org/wiki/Q10877366) | Category:Niukawakami-jinja Kamisha | Niukawakami-jinja Kami-sha Shrine | Niukawakami Upper Shrine |
| [Q10877367](https://www.wikidata.org/wiki/Q10877367) | Category:Niukawakami-jinja Shimosha | Niukawakami-jinja Shimo-sha Shrine | Niukawakami Lower Shrine |
| [Q195684](https://www.wikidata.org/wiki/Q195684) | Category:Iyahiko-jinja | Iyahiko Shrine | Yahiko Shrine |
| [Q245731](https://www.wikidata.org/wiki/Q245731) | Category:Ohyamato-jinja | Ohyamato Shrine | Ōyamato Shrine |
| [Q717682](https://www.wikidata.org/wiki/Q717682) | Category:Kanda-Myojin | Kanda-Myojin Shrine | Kanda Shrine |
| [Q6370171](https://www.wikidata.org/wiki/Q6370171) | Category:Karenko Shinto Shrine | Karenko Shinto Shrine | Karenkō Shrine |
| [Q6936905](https://www.wikidata.org/wiki/Q6936905) | Category:Taiwan Gokoku Shrine | Taiwan Gokoku Shrine | Taiwan Martyr Shrine |
| [Q7797685](https://www.wikidata.org/wiki/Q7797685) | Category:Imperial Palace Sanctuaries | Imperial Palace Sanctuaries Shrine | Three Palace Sanctuaries |
| [Q8010918](https://www.wikidata.org/wiki/Q8010918) | Category:Koxinga's Shrine | Koxinga's Shrine | Koxinga Shrine |
| [Q11392320](https://www.wikidata.org/wiki/Q11392320) | Category:Rokusonnnou-Jinja | Rokusonnnō Shrine | Rokusonnō Shrine |
| [Q3090870](https://www.wikidata.org/wiki/Q3090870) | Category:Funabashi-daijingū | Funabashi Daijingu | Ōhi Shrine |
| [Q10946254](https://www.wikidata.org/wiki/Q10946254) | Category:Utsunomiya Futaarayama-jinja | Utsunomiya Futaarayama Shrine | Utsunomiya Futarayama Shrine |
| [Q888184](https://www.wikidata.org/wiki/Q888184) | Category:Hinokuma-jingu Kunikakasu-jingu | Hinokuma-jingu Kunikakasu Grand Shrine | Hinokuma Shrine |
| [Q1306606](https://www.wikidata.org/wiki/Q1306606) | Category:Kamo-jinja | Kamo Shrine | Kamo shrines |
| [Q1442645](https://www.wikidata.org/wiki/Q1442645) | Category:Fushimi Sambo Inari-jinja Shrine | Fushimi Sambo Inari-jinja Shrine | Fushimi Sanpō Inari Shrine |
| [Q521319](https://www.wikidata.org/wiki/Q521319) | Category:Takekoma-jinja | Takekoma Shrine | Takekoma Inari Shrine |
| [Q546197](https://www.wikidata.org/wiki/Q546197) | Category:Omiwa-jinja (Ichinomiya) | Omiwa Shrine | Ōmiwa Shrine, Ichinomiya |
| [Q704636](https://www.wikidata.org/wiki/Q704636) | Category:Naminoue-gū | Naminōe-gu Shrine | Naminoue Shrine |
| [Q704865](https://www.wikidata.org/wiki/Q704865) | Category:Hida-ichinomiya Minashi-jinja | Hida-ichinomiya Minashi Shrine | Minashi Shrine |
| [Q3342246](https://www.wikidata.org/wiki/Q3342246) | Category:Niukanshoubu-jinja | Niukanshōbu Shrine | Niukanshōfu Shrine |
| [Q3439900](https://www.wikidata.org/wiki/Q3439900) | Category:Rokusho-jinja (Okazaki) | Rokusho Shrine | Rokusho Shrine, Okazaki |
| [Q3473746](https://www.wikidata.org/wiki/Q3473746) | Category:Saruga shrine | Saruga Shrine | Saruka Shrine |
| [Q3571318](https://www.wikidata.org/wiki/Q3571318) | Category:Yaho Temman-gū | Yaho Temman-gu Shrine | Yabo Tenmangū |
| [Q3571407](https://www.wikidata.org/wiki/Q3571407) | Category:Yamada Ten'man-gû | Yamada Ten'man-gu Shrine | Yamada Tenmangū |
| [Q11643733](https://www.wikidata.org/wiki/Q11643733) | Category:Tsubaki Nakato-jinja | Tsubaki Nakato Shrine | Tsubaki Shrine |
| [Q3541617](https://www.wikidata.org/wiki/Q3541617) | Category:Tsubaki Ōkami Yashiro | Tsubaki Ōkami Yashiro Shrine | Tsubaki Grand Shrine |
| [Q3547609](https://www.wikidata.org/wiki/Q3547609) | Category:Ubagami Daijin-gū | Ubagami Daijin-gu Shrine | Ubagami Daijingū |
| [Q3136198](https://www.wikidata.org/wiki/Q3136198) | Category:Hirakiki-jinja | Hirakiki Shrine | Hirasaki Shrine |
| [Q11395802](https://www.wikidata.org/wiki/Q11395802) | Category:Ideha-jinja | Ideha Shrine | Dewa Shrine |
| [Q11413133](https://www.wikidata.org/wiki/Q11413133) | Category:Kishibe-jinja | Kishibe Shrine | Kishibe Tile Kiln Site |
| [Q11652880](https://www.wikidata.org/wiki/Q11652880) | Category:Nagasakiken-Gokoku-jinja | Nagasakiken-Gokoku Shrine | Nagasaki Gokoku Shrine |
| [Q11434174](https://www.wikidata.org/wiki/Q11434174) | Category:Odara-Yosemiya site | Odara-Yosemiya site Shrine | Ōdara Yosemiya |
| [Q20982935](https://www.wikidata.org/wiki/Q20982935) | Category:Sengen Shrine (Nishi-ku, Nagoya) | Sengen Shrine | Fuji Sengen Shrine (Nishi-ku, Nagoya) |
| [Q21449537](https://www.wikidata.org/wiki/Q21449537) | Category:Kuskus Shrine | Kuskus Shrine | Gaoshi Shrine |
| [Q11456842](https://www.wikidata.org/wiki/Q11456842) | Category:Toyamaken-Gokoku-jinja | Toyamaken-Gokoku Shrine | Toyama Gokoku Shrine |
| [Q11483206](https://www.wikidata.org/wiki/Q11483206) | Category:Heisenji | Heisen-ji Temple | Heisenji Hakusan Shrine |
| [Q133857952](https://www.wikidata.org/wiki/Q133857952) | Category:Tientsin Shrine | Tientsin Shrine | Tianjin Shrine |
| [Q11535030](https://www.wikidata.org/wiki/Q11535030) | Category:Kakimoto-jinja (Akashi) | Kakimoto Shrine | Kakinomoto Shrine (Akashi) |
| [Q11572731](https://www.wikidata.org/wiki/Q11572731) | Category:Tamanooya-jinja | Tamanōya Shrine | Tamanooya Jinja |
| [Q11581011](https://www.wikidata.org/wiki/Q11581011) | Category:Naiku | Naiku Shrine | Kotai jingu |
| [Q11633343](https://www.wikidata.org/wiki/Q11633343) | Category:Geku | Geku Shrine | Toyouke Daijingu |
| [Q1627016](https://www.wikidata.org/wiki/Q1627016) | Category:Higashi Honganji | Higashi Hongan-ji Temple | Hongan-ji |
| [Q1741668](https://www.wikidata.org/wiki/Q1741668) | Category:Kinpusenji | Kinpusen-ji Temple | Kimpusen-ji |
| [Q1760419](https://www.wikidata.org/wiki/Q1760419) | Category:Risshaku-ji | Risshaku-ji Temple | Yama-dera |
| [Q2380134](https://www.wikidata.org/wiki/Q2380134) | Category:Zenrinji Eikando | Zenrinji Eikan-do Temple | Eikan-dō Zenrin-ji |
| [Q3201314](https://www.wikidata.org/wiki/Q3201314) | Category:Kōshō-ji (Nagoya) | Kōshō-ji Temple | Kōshō-ji, Nagoya |
| [Q285602](https://www.wikidata.org/wiki/Q285602) | Category:Higashi Hongan-ji Hakodate Betsuin | Higashi Hongan-ji Hakodate Betsu-in Temple | Ōtani Hongan-ji Hakodate Betsu-in |
| [Q3192708](https://www.wikidata.org/wiki/Q3192708) | Category:Jigen-ji Kannon-in | Jigen-ji Kannon-in Temple | Kannon-in |
| [Q3197507](https://www.wikidata.org/wiki/Q3197507) | Category:Kichijoji (Bunkyo, Tokyo) | Kichijo-ji Temple | Kisshō-ji |
| [Q3342007](https://www.wikidata.org/wiki/Q3342007) | Category:Ninja-dera | Ninja-dera Temple | Myōryū-ji |
| [Q2963263](https://www.wikidata.org/wiki/Q2963263) | Category:Senyō-ji (Chuo-ku, Chiba) | Senyō-ji Temple | Chiba-dera |
| [Q11370077](https://www.wikidata.org/wiki/Q11370077) | Category:Joshin-ji (Setagaya) | Joshin-ji Temple | Kuhonbutsu Jōshin-ji |
| [Q11378194](https://www.wikidata.org/wiki/Q11378194) | Category:Sen'yū-ji | Sen'yū-ji Temple | Senyū-ji (Imabari) |
| [Q11386255](https://www.wikidata.org/wiki/Q11386255) | Category:Gyokuzoin (Heguri, Nara) | Gyokuzo-in Temple | Shigisan Gyokuzōin |
| [Q11092571](https://www.wikidata.org/wiki/Q11092571) | Category:Chyogosonshiji | Chyogosonshi-ji Temple | Chōgosonshi-ji |
| [Q3518099](https://www.wikidata.org/wiki/Q3518099) | Category:Tori-Tenjyo-ji | Tori-Tenjyo-ji Temple | Tenjō-ji |
| [Q3547078](https://www.wikidata.org/wiki/Q3547078) | Category:Tanemakidaishi | Tanemakidaishi Shrine | Tōrin-in (Naruto) |
| [Q3128068](https://www.wikidata.org/wiki/Q3128068) | Category:Hase-dera (Atsugi, Kanagawa) | Hase-dera Temple | Iiyama Kannon |
| [Q3571897](https://www.wikidata.org/wiki/Q3571897) | Category:Kongō-ji (Kyoto) | Kongō-ji Temple | Yasaka Kōshin-dō |
| [Q3575218](https://www.wikidata.org/wiki/Q3575218) | Category:Zenkō-ji Anjō-in (Inabadori, Gifu) | Zenkō-ji Anjō-in Temple | Zenkō-ji (Gifu) |
| [Q3576268](https://www.wikidata.org/wiki/Q3576268) | Category:Zuiryō-ji (Gifu) | Zuiryō-ji Temple | Zuiryū-ji (Gifu) |
| [Q3594043](https://www.wikidata.org/wiki/Q3594043) | Category:Onodera | Ono-dera Temple | Ōno-ji |
| [Q3482457](https://www.wikidata.org/wiki/Q3482457) | Category:Shōnen-ji (Takachiho) | Shōnen-ji Temple | Shonenji Temple, Takachiho |
| [Q3095172](https://www.wikidata.org/wiki/Q3095172) | Category:Gankei-ji | Gankei-ji Temple | Gangyō-ji |
| [Q1072538](https://www.wikidata.org/wiki/Q1072538) | Category:Sanzen'in | Sanzen'-in Temple | Sanzen-in |
| [Q1072965](https://www.wikidata.org/wiki/Q1072965) | Category:Hojyuji (Kyoto, Kyoto) | Hojyu-ji Temple | Hōjūjidono |
| [Q11641897](https://www.wikidata.org/wiki/Q11641897) | Category:Daruma-ji (Takasaki) | Daruma-ji Temple | Shorinzan Daruma Temple |
| [Q11641901](https://www.wikidata.org/wiki/Q11641901) | Category:Takkoku-no-iwaya Bishamon-dō | Takkoku-no-iwaya Bishamon-do Temple | Takkoku-no-Iwaya |
| [Q3138262](https://www.wikidata.org/wiki/Q3138262) | Category:Ōfuna Kannon-ji | Ōfuna Kannon-ji Temple | Ōfuna Kannon |
| [Q11428052](https://www.wikidata.org/wiki/Q11428052) | Category:Hōon-in | Hōon-in Temple | Hōon'in |
| [Q20983125](https://www.wikidata.org/wiki/Q20983125) | Category:Shōman-ji (Nagoya) | Shōman-ji Temple | Shōman-ji, Nagoya |
| [Q24864158](https://www.wikidata.org/wiki/Q24864158) | Category:Raizan-Sennyoji | Raizan-Sennyo-ji Temple | Sennyo-ji |
| [Q28692387](https://www.wikidata.org/wiki/Q28692387) | Category:Shōjū-in (Tokoname) | Shōjū-in Temple | Shōjū-in, Tokoname |
| [Q11679196](https://www.wikidata.org/wiki/Q11679196) | Category:Ryūkō-ji (Uwajima) | Ryūkō-ji Temple | Ryuukou-ji |
| [Q11474382](https://www.wikidata.org/wiki/Q11474382) | Category:Iwaya-ji (Kumakōgen) | Iwaya-ji Temple | Iwaya-ji, Ehime |
| [Q17218754](https://www.wikidata.org/wiki/Q17218754) | Category:Yanaka Tenno-ji | Yanaka Tenno-ji Temple | Tennō-ji (Taitō) |
| [Q11489138](https://www.wikidata.org/wiki/Q11489138) | Category:Ohashi Kannon | Ohashi Kannon Shrine | Ohashi Kannon-ji |
| [Q54152981](https://www.wikidata.org/wiki/Q54152981) | Category:Komyoji Rurikoin | Komyoji Ruriko-in Temple | Rurikō-in |
| [Q11529611](https://www.wikidata.org/wiki/Q11529611) | Category:Matsunoo-dera (Maizuru) | Matsunō-dera Temple | Matsunoo-dera |
| [Q11545558](https://www.wikidata.org/wiki/Q11545558) | Category:Iwama-dera | Iwama-dera Temple | Shōhō-ji (Ōtsu) |
| [Q11560913](https://www.wikidata.org/wiki/Q11560913) | Category:Kiyomizudera (Kato) | Kiyomizu-dera Temple | Banshū Kiyomizu-dera |
| [Q11561306](https://www.wikidata.org/wiki/Q11561306) | Category:Kiyotaki-dera | Kiyotaki-dera Temple | Kiyotaki-ji (Tsuchiura) |
| [Q11563955](https://www.wikidata.org/wiki/Q11563955) | Category:Todoroki Fudo-son | Todoroki Fudo-son Shrine | Mangan-ji (Setagaya) |
| [Q11555353](https://www.wikidata.org/wiki/Q11555353) | Category:Hōkanji | Hōkan-ji Temple | Yasaka Pagoda |
| [Q97206336](https://www.wikidata.org/wiki/Q97206336) | Category:Nanzō-in (Higashi-Mizumoto, Katsushika) | Nanzō-in Temple | Tōsen-ji |
| [Q11630596](https://www.wikidata.org/wiki/Q11630596) | Category:Kannonji (Higashiyama-ku, Kyoto) | Kannon-ji Temple | Imakumano Kannon-ji |

## Rejected — gradeable items the normalizer declined

| item | Commons | enwiki |
|---|---|---|
