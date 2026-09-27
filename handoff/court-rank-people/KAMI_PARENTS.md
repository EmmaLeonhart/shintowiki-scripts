# Kami parents (P40 child + other-parent qualifier): second handoff in this directory

This directory's main README is about court ranks on people. **This file is a separate, second job
that also moves to this repository**: the parent/child links between Japanese deities (kami). It sits
here instead of in its own directory so it isn't missed.

Files in this directory:
- `generate_kami_parent_qualifiers.py`: the generator (157 lines)
- `kami_parent_qualifiers.txt`: its last output, 94 QuickStatements lines

Both moved from `modern-quickstatements/` in `EmmaLeonhart/shintowiki-scripts` on 2026-09-27. There
it is paused from the daily drip and removed from CI, so nothing there will send these lines.

## What it does

On Wikidata a kami can have *child* (P40) statements, and the child's own item can record its
*father* (P22) and *mother* (P25). This job adds the child's **other** parent as a qualifier on the
parent's P40 statement:

    Izanagi  P40 (child)  Amaterasu   + qualifier  P25 (mother) = Izanami

It is a **join over data already on Wikidata, not an inference**. If `A` has child `C`, `C` records
`A` as its father (or mother), and `C` records someone else as its mother (or father), that other
parent goes on `A`'s P40 statement as a qualifier. Emma, 2026-07-16: *"the child being able to go
through to grab the mother and father of the child and then add this as a qualifier is something …
we can actually pretty easily do … and it is valuable."*

## The rules (and why each one exists)

1. **Only kami.** `A` must be an instance of (a subclass of) the kami class the script names.
2. **Only where the qualifier is missing.** The query filters out P40 statements that already carry
   it, so the output shrinks as lines land (self-healing; no cursor needed).
3. **The child must really name `A` as that parent.** Otherwise the "other" parent is meaningless.
4. **Refuse a child with more than one father or more than one mother.** That's a question about
   the data model, not something a script should settle. Emma: *"it's not the job of the script to
   find ontology errors, it's the job to extend existing patterns."*
5. **Refuse unknown-value / no-value parents.** They come back from SPARQL as blank nodes, not items.
6. **Add-only.** It never removes anything.

## Why it is more tangled than it looks

- **It copies whatever the child's item says, including dubious or single-tradition genealogies.**
  Japanese myth has competing lineages (Kojiki vs Nihon Shoki vs shrine traditions), and Wikidata
  mixes them. Examples in the current output:
  - Futodama is recorded as the father of Ame no Uzume and Kamo Taketsunumi.
  - Ōkuninushi and Konohanasakuyahime appear as the parents of Honoakari.
  - Himetataraisuzuhime has two fathers (Ōmononushi and Kotoshironushi), and both get the same
    mother qualifier.

  The script adds context to claims that are already there; it doesn't vet them. Whether that's
  acceptable is this repository's call, under its own rules.
- **It depends on the child's P22/P25 being right.** If someone later fixes a child's parent, the
  qualifier this job added to the parent's P40 is not corrected. Nothing re-checks it after it lands.
- **Nothing else reads these qualifiers.** In shintowiki-scripts no generator depended on them, so
  moving the job breaks nothing there.
- **Code dependency:** the generator imports `wdqs_transport` (WDQS POST with backoff and the
  User-Agent) from the shrine repo. Replace it with this repository's equivalent.

## Size: 94 lines, 51 parent kami

Re-run the query rather than replaying the .txt, so anything that landed isn't sent twice. The
current output, grouped by the parent whose P40 statement gets the qualifier:

- 伊奘冉尊 / Izanami (Q682306): 蛭児 / Hiruko + father 伊奘諾尊 / Izanagi;  / Ame no Torifune + father 伊奘諾尊 / Izanagi; シナツヒコ / Shinatsuhiko + father 伊奘諾尊 / Izanagi; ククノチ / Kukunochi + father 伊奘諾尊 / Izanagi; 大事忍男 / Ōgotooshio + father 伊奘諾尊 / Izanagi; 家宅六神 / Katakurokushin + father 伊奘諾尊 / Izanagi; 道返 / Chigaeshi + father 伊奘諾尊 / Izanagi; 海神 / Ōwatatsumi + father 伊奘諾尊 / Izanagi; 軻遇突智 / Kagutsuchi + father 伊奘諾尊 / Izanagi; 素戔嗚尊 / Susanoo + father 伊奘諾尊 / Izanagi; オオゲツヒメ / Ōgetsuhime + father 伊奘諾尊 / Izanagi; オオヤマツミ / Ōyamatsumi + father 伊奘諾尊 / Izanagi; 天照大神 / Amaterasu + father 伊奘諾尊 / Izanagi; 月読尊 / Tsukuyomi + father 伊奘諾尊 / Izanagi; カヤノヒメ / Kayanohime + father 伊奘諾尊 / Izanagi
- 伊奘諾尊 / Izanagi (Q813858): 蛭児 / Hiruko + mother 伊奘冉尊 / Izanami;  / Ame no Torifune + mother 伊奘冉尊 / Izanami; シナツヒコ / Shinatsuhiko + mother 伊奘冉尊 / Izanami; ククノチ / Kukunochi + mother 伊奘冉尊 / Izanami; 大事忍男 / Ōgotooshio + mother 伊奘冉尊 / Izanami; 家宅六神 / Katakurokushin + mother 伊奘冉尊 / Izanami; 軻遇突智 / Kagutsuchi + mother 伊奘冉尊 / Izanami; 素戔嗚尊 / Susanoo + mother 伊奘冉尊 / Izanami; オオゲツヒメ / Ōgetsuhime + mother 伊奘冉尊 / Izanami; オオヤマツミ / Ōyamatsumi + mother 伊奘冉尊 / Izanami; 天照大神 / Amaterasu + mother 伊奘冉尊 / Izanami; 月読尊 / Tsukuyomi + mother 伊奘冉尊 / Izanami
- フトダマ / Futodama (Q11059539): 天石門別 / Ame no Iwatowake + mother 天比理刀咩命 / Ame no Hiritome; 天櫛耳命 / Ame no Kushimimi + mother 天比理刀咩命 / Ame no Hiritome; 賀茂建角身命 / Kamo Taketsunumi + mother 天比理刀咩命 / Ame no Hiritome; オオミヤノメ / Ōmiyanome + mother 天比理刀咩命 / Ame no Hiritome; 天鈿女命 / Ame no Uzume + mother 天比理刀咩命 / Ame no Hiritome
- 天比理刀咩命 / Ame no Hiritome (Q85879124): 天石門別 / Ame no Iwatowake + father フトダマ / Futodama; 天櫛耳命 / Ame no Kushimimi + father フトダマ / Futodama; 賀茂建角身命 / Kamo Taketsunumi + father フトダマ / Futodama; オオミヤノメ / Ōmiyanome + father フトダマ / Futodama; 天鈿女命 / Ame no Uzume + father フトダマ / Futodama
- 大国主神 / Ōkuninushi (Q276944): 木俣神 / Ki-no-Mata-no-Kami + mother 八上比売 / Yagami-hime; 下照姫 / Shitateruhime + mother 田心姫 / Takiribime; 鳥鳴海神 / Torinarumi no kami + mother 鳥耳神 / Totori no kami; 火明命 / Honoakari + mother 木花開耶姫 / Konohanasakuyahime
- 大物主神 / Ōmononushi (Q10936701): 五十鈴依媛命 / Isuzuyorihime + mother 玉依媛 / Tamakushihime; 媛蹈鞴五十鈴媛命 / Himetataraisuzuhime + mother 玉依媛 / Tamakushihime; 鴨王 / Kamo no Kimi + mother 玉依媛 / Tamakushihime
- 玉依姫 / Tamayorihime (Q3082751): 彦五瀬命 / Hiko Itsuse no Mikoto + father 彦波瀲武鸕鶿草葺不合尊 / Ugayafukiaezu; 三毛入野命 / Mikeiri no Mikoto + father 彦波瀲武鸕鶿草葺不合尊 / Ugayafukiaezu; 稲飯命 / Inai no Mikoto + father 彦波瀲武鸕鶿草葺不合尊 / Ugayafukiaezu
- 田心姫 / Takiribime (Q10932870): 下照姫 / Shitateruhime + father 大国主神 / Ōkuninushi; 味耜高彦根神 / Ajisukitakahikone + father 大国主神 / Ōkuninushi
- 木花開耶姫 / Konohanasakuyahime (Q1781862): 彦火火出見尊 / Hoori + father 天津彦彦火瓊瓊杵尊 / Ninigi; 火闌降命 / Hosuseri + father 天津彦彦火瓊瓊杵尊 / Ninigi
- 事代主神 / Kotoshironushi (Q8009611): 媛蹈鞴五十鈴媛命 / Himetataraisuzuhime + mother 玉依媛 / Tamakushihime; 鴨王 / Kamo no Kimi + mother 玉依媛 / Tamakushihime
- 彦火火出見尊 / Hoori (Q1051960): 彦波瀲武鸕鶿草葺不合尊 / Ugayafukiaezu + mother トヨタマヒメ / Toyotamahime
- 八上比売 / Yagami-hime (Q10891903): 木俣神 / Ki-no-Mata-no-Kami + father 大国主神 / Ōkuninushi
- 八色雷公 / Yakusaikazuchi (Q10892534): 賀茂別雷命 / Kamo Wakeikazuchi + mother 玉依媛 / Tamakushihime
- 多比理岐志麻流美神 / Tahiriki-Shimarumi-no-Kami (Q10932738): 美呂浪神 / Mironami-no-Kami + mother 活玉前玉比売神 / Ikutamatakitamahime Kami
- 饒速日命 / Nigihayahi (Q10949054): ウマシマジ / Umashimaji + mother ミカシキヤヒメ / Mikashikiyahime
- アシナヅチ / Ashinazuchi (Q109554668): 奇稲田姫 / Kushinadahime + mother テナヅチ / Tenazuchi
- テナヅチ / Tenazuchi (Q109554669): 奇稲田姫 / Kushinadahime + father アシナヅチ / Ashinazuchi
- 建比良鳥命 / Takehiratori (Q11065428): クシヤタマ / Kushiyatama + mother 天甕津日女命 / Amamikatsuhime no Mikoto
- 栲幡千千姫 / Takuhadachijihime (Q11110848): 天津彦彦火瓊瓊杵尊 / Ninigi + father 正哉吾勝勝速日天忍穂耳尊 / Ame no Oshihomimi
- 沼河比売 / Nunakawa hime (Q11142832): 建御名方神 / Takeminakata + father 大国主神 / Ōkuninushi
- ミカシキヤヒメ / Mikashikiyahime (Q11341880): ウマシマジ / Umashimaji + father 饒速日命 / Nigihayahi
- 神大市姫 / Kamuōichihime (Q11588867): ウカノミタマ / Ukanomitama + father 素戔嗚尊 / Susanoo
- 速甕之多気佐波夜遅奴美神 / Hayamike-no-Takekasayanosunumi-no-Kami (Q135328851): 甕主日子神 / Mikemunushi-no-Hiko-no-Kami + mother 前玉比売 / Sakitamahime
- 甕主日子神 / Mikemunushi-no-Hiko-no-Kami (Q135328853): 多比理岐志麻流美神 / Tahiriki-Shimarumi-no-Kami + mother 比那良志毘売 / Hinarashibime
- 美呂浪神 / Mironami-no-Kami (Q135328861): 布忍富鳥鳴海神 / Nunobutomi-Torinarumi-no-Kami + mother 青沼馬沼押比売 / Aonuma-Mashi-no-Maou-hime
- 布忍富鳥鳴海神 / Nunobutomi-Torinarumi-no-Kami (Q135328864): 天日腹大科度美神 / Ame-no-Hibaraooshinadomi-no-Kami + mother 若尽女神 / Wakatsukushime-no-Kami
- 前玉比売 / Sakitamahime (Q135330068): 甕主日子神 / Mikemunushi-no-Hiko-no-Kami + father 速甕之多気佐波夜遅奴美神 / Hayamike-no-Takekasayanosunumi-no-Kami
- 活玉前玉比売神 / Ikutamatakitamahime Kami (Q135330219): 美呂浪神 / Mironami-no-Kami + father 多比理岐志麻流美神 / Tahiriki-Shimarumi-no-Kami
- 若尽女神 / Wakatsukushime-no-Kami (Q135330271): 天日腹大科度美神 / Ame-no-Hibaraooshinadomi-no-Kami + father 布忍富鳥鳴海神 / Nunobutomi-Torinarumi-no-Kami
- 遠津待根神 / Totsumatone-no-Kami (Q135330329): 遠津山岬多良斯神 / Totsuyami-Sakitara-no-Kami + father 天日腹大科度美神 / Ame-no-Hibaraooshinadomi-no-Kami
- 青沼馬沼押比売 / Aonuma-Mashi-no-Maou-hime (Q136705879): 布忍富鳥鳴海神 / Nunobutomi-Torinarumi-no-Kami + father 美呂浪神 / Mironami-no-Kami
- 比売神 / Himegami (Q22070227): 天押雲根命 / Ame no Oshikumone + father 天児屋命 / Ame no Koyane
- トヨタマヒメ / Toyotamahime (Q2329261): 彦波瀲武鸕鶿草葺不合尊 / Ugayafukiaezu + father 彦火火出見尊 / Hoori
- 天児屋命 / Ame no Koyane (Q2564508): 天押雲根命 / Ame no Oshikumone + mother 比売神 / Himegami
- 素戔嗚尊 / Susanoo (Q272993): 八島士奴美神 / Yashimajinumi no kami + mother 奇稲田姫 / Kushinadahime
- オオヤマツミ / Ōyamatsumi (Q386563): 木花開耶姫 / Konohanasakuyahime + mother カヤノヒメ / Kayanohime
- 淤美豆奴神 / Omizunu (Q48745416): 天之冬衣神 / Ame no Fuyu Kinu no kami + mother 布帝耳神 / Futemimi
- 木花知流比売 / Konohanachiruhime (Q48745675): 布波能母遅久奴須奴神 / Fuha-no-Mojikunusunu + father 八島士奴美神 / Yashimajinumi no kami
- 国忍富神 / Kuninotoshimi-no-Kami (Q48759713): 速甕之多気佐波夜遅奴美神 / Hayamike-no-Takekasayanosunumi-no-Kami + mother 葦那陀迦神 / Ashinataka-no-Kami
- 鳥耳神 / Totori no kami (Q48760952): 鳥鳴海神 / Torinarumi no kami + father 大国主神 / Ōkuninushi
- 奇稲田姫 / Kushinadahime (Q505469): 八島士奴美神 / Yashimajinumi no kami + father 素戔嗚尊 / Susanoo
- 鳥鳴海神 / Torinarumi no kami (Q55522639): 国忍富神 / Kuninotoshimi-no-Kami + mother 日名照額田毘道男伊許知邇神 / Hinateri-Nukada-Bichio-Ikochini-no-Kami
- 八島士奴美神 / Yashimajinumi no kami (Q55522907): 布波能母遅久奴須奴神 / Fuha-no-Mojikunusunu + mother 木花知流比売 / Konohanachiruhime
- 葦那陀迦神 / Ashinataka-no-Kami (Q55533749): 速甕之多気佐波夜遅奴美神 / Hayamike-no-Takekasayanosunumi-no-Kami + father 国忍富神 / Kuninotoshimi-no-Kami
- 天日腹大科度美神 / Ame-no-Hibaraooshinadomi-no-Kami (Q60996386): 遠津山岬多良斯神 / Totsuyami-Sakitara-no-Kami + mother 遠津待根神 / Totsumatone-no-Kami
- 布帝耳神 / Futemimi (Q65266228): 天之冬衣神 / Ame no Fuyu Kinu no kami + father 淤美豆奴神 / Omizunu
- 布波能母遅久奴須奴神 / Fuha-no-Mojikunusunu (Q65266248): 深淵之水夜礼花神 / Fukabuchi-no-Mizuyarehana + mother 日河比売 / Hikawa-hime
- 日名照額田毘道男伊許知邇神 / Hinateri-Nukada-Bichio-Ikochini-no-Kami (Q65269923): 国忍富神 / Kuninotoshimi-no-Kami + father 鳥鳴海神 / Torinarumi no kami
- 日河比売 / Hikawa-hime (Q65270244): 深淵之水夜礼花神 / Fukabuchi-no-Mizuyarehana + father 布波能母遅久奴須奴神 / Fuha-no-Mojikunusunu
- 深淵之水夜礼花神 / Fukabuchi-no-Mizuyarehana (Q65272471): 淤美豆奴神 / Omizunu + mother 天之都度閇知泥神 / Ame-no-Tsudoechine
- カヤノヒメ / Kayanohime (Q8191878): 木花開耶姫 / Konohanasakuyahime + father オオヤマツミ / Ōyamatsumi
