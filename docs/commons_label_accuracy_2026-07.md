# Commons → English-label accuracy (2026-07)

**Report only.** Grades `commons_normalize` against enwiki titles for Japanese shrines + temples. No edits proposed. Regenerate: `modern-quickstatements/report_commons_label_accuracy.py`.

| | |
|---|---:|
| in-scope items (Commons category) | 400 |
| non-romaji Commons name (out of scope — kana stage handles) | 3 |
| gradeable (romaji Commons name + enwiki title) | 173 |
| **exact** | 130 |
| **macron-only** (acceptable) | 11 |
| **mismatch** (real failure) | 20 |
| **rejected** (normalizer returned nothing) | 12 |

**Core-reading accuracy = 81.5%** (exact + macron-only, over gradeable).

## Mismatches — the real failures

| item | Commons | candidate | enwiki |
|---|---|---|---|
| [Q3594054](https://www.wikidata.org/wiki/Q3594054) | Category:Otasan-jinja | Otasan Shrine | Ōta Shrine |
| [Q3936229](https://www.wikidata.org/wiki/Q3936229) | Category:Taichung Shrine | Taichung Shrine | Taichu Jinja |
| [Q4696584](https://www.wikidata.org/wiki/Q4696584) | Category:Aichiken-Gokoku-jinja | Aichiken-Gokoku Shrine | Aichi Gokoku Shrine |
| [Q195684](https://www.wikidata.org/wiki/Q195684) | Category:Iyahiko-jinja | Iyahiko Shrine | Yahiko Shrine |
| [Q245731](https://www.wikidata.org/wiki/Q245731) | Category:Ohyamato-jinja | Ohyamato Shrine | Ōyamato Shrine |
| [Q6370171](https://www.wikidata.org/wiki/Q6370171) | Category:Karenko Shinto Shrine | Karenko Shinto Shrine | Karenkō Shrine |
| [Q6936905](https://www.wikidata.org/wiki/Q6936905) | Category:Taiwan Gokoku Shrine | Taiwan Gokoku Shrine | Taiwan Martyr Shrine |
| [Q8010918](https://www.wikidata.org/wiki/Q8010918) | Category:Koxinga's Shrine | Koxinga's Shrine | Koxinga Shrine |
| [Q11392320](https://www.wikidata.org/wiki/Q11392320) | Category:Rokusonnnou-Jinja | Rokusonnnō Shrine | Rokusonnō Shrine |
| [Q888184](https://www.wikidata.org/wiki/Q888184) | Category:Hinokuma-jingu Kunikakasu-jingu | Hinokuma-jingu Kunikakasu Grand Shrine | Hinokuma Shrine |
| [Q1306606](https://www.wikidata.org/wiki/Q1306606) | Category:Kamo-jinja | Kamo Shrine | Kamo shrines |
| [Q1442645](https://www.wikidata.org/wiki/Q1442645) | Category:Fushimi Sambo Inari-jinja Shrine | Fushimi Sambo Inari-jinja Shrine | Fushimi Sanpō Inari Shrine |
| [Q3090870](https://www.wikidata.org/wiki/Q3090870) | Category:Funabashi-daijingū | Funabashi Daijingu | Ōhi Shrine |
| [Q10863796](https://www.wikidata.org/wiki/Q10863796) | Category:Ichinomiya nukisaki-jinja | Ichinomiya nukisaki Shrine | Nukisaki Shrine |
| [Q10877366](https://www.wikidata.org/wiki/Q10877366) | Category:Niukawakami-jinja Kamisha | Niukawakami-jinja Kami-sha Shrine | Niukawakami Upper Shrine |
| [Q10877367](https://www.wikidata.org/wiki/Q10877367) | Category:Niukawakami-jinja Shimosha | Niukawakami-jinja Shimo-sha Shrine | Niukawakami Lower Shrine |
| [Q3136198](https://www.wikidata.org/wiki/Q3136198) | Category:Hirakiki-jinja | Hirakiki Shrine | Hirasaki Shrine |
| [Q10946254](https://www.wikidata.org/wiki/Q10946254) | Category:Utsunomiya Futaarayama-jinja | Utsunomiya Futaarayama Shrine | Utsunomiya Futarayama Shrine |
| [Q11395802](https://www.wikidata.org/wiki/Q11395802) | Category:Ideha-jinja | Ideha Shrine | Dewa Shrine |
| [Q3571318](https://www.wikidata.org/wiki/Q3571318) | Category:Yaho Temman-gū | Yaho Temman-gu Shrine | Yabo Tenmangū |

## Rejected — gradeable items the normalizer declined

| item | Commons | enwiki |
|---|---|---|
| [Q3698846](https://www.wikidata.org/wiki/Q3698846) | Category:Onbashira Festival | Onbashira |
| [Q5367406](https://www.wikidata.org/wiki/Q5367406) | Category:Kasugayama Primeval Forest | Kasugayama Primeval Forest |
| [Q5507355](https://www.wikidata.org/wiki/Q5507355) | Category:Fuji Sengen Shrine (Naka-ku, Nagoya) | Fuji Sengen Shrine (Naka-ku, Nagoya) |
| [Q6102414](https://www.wikidata.org/wiki/Q6102414) | Category:Izumo Taishakyo Mission of Hawaii | Izumo Taishakyo Mission of Hawaii |
| [Q717682](https://www.wikidata.org/wiki/Q717682) | Category:Kanda-Myojin | Kanda Shrine |
| [Q840967](https://www.wikidata.org/wiki/Q840967) | Category:Tsubaki Grand Shrine of America | Tsubaki Grand Shrine of America |
| [Q6958481](https://www.wikidata.org/wiki/Q6958481) | Category:Nagao-jinja (Katsuragi, Nara) | Nagao Shrine |
| [Q7797685](https://www.wikidata.org/wiki/Q7797685) | Category:Imperial Palace Sanctuaries | Three Palace Sanctuaries |
| [Q2868748](https://www.wikidata.org/wiki/Q2868748) | Category:Atago-jinja (Minato, Tokyo) | Atago Shrine (Tokyo) |
| [Q10885171](https://www.wikidata.org/wiki/Q10885171) | Category:Izawa-no-miya | Izawa-no-miya |
| [Q3571407](https://www.wikidata.org/wiki/Q3571407) | Category:Yamada Ten'man-gû | Yamada Tenmangū |
| [Q11381867](https://www.wikidata.org/wiki/Q11381867) | Category:Sumiyoshi-jinja (Otaru, Hokkaido) | Sumiyoshi Shrine (Hokkaidō) |
