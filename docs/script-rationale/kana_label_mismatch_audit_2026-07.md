# Kana-vs-romaji label mismatch audit (queue #8 typo trace)

Generated 2026-07-06 via query-main + kana_english.romanize. Shrines whose EN label letters
diverge early from the romanized P1814 kana. **161 candidates** out of 7,335
deterministically-checkable shrines. NOT auto-correctable: the wrong side varies — some are label
typos (Saruka->Saruga), some have historical-kana P1814 (ちりふ=Chiryū), some labels carry legit
place prefixes (Kurume Suitengū). Each needs per-item review (RAG or Emma) before any QS.

| QID | ja | kana | EN label | kana romanized |
|---|---|---|---|---|
| Q3200625 | 水天宮 | すいてんぐう | Kurume Suitengū | Suitengu |
| Q3335115 | 那古野神社 | なごのじんじゃ | Nagoya Shrine | Nagonojinja |
| Q3473746 | 猿賀神社 | さるがじんじゃ | Saruka Shrine | Sarugajinja |
| Q11084040 | 新竹神社 | しんちくじんじゃ | Hsinchu Shrine | Shinchikujinja |
| Q11583957 | 矢切神社 | やきりじんじゃ | Yagiri Shrine | Yakirijinja |
| Q11584226 | 矢留大神宮 | やどみだいじんぐう | Yadome-daijingu | Yadomidaijingu |
| Q11589590 | 神峯神社 | こうのみねじんじゃ | Kounomine Shrine | Konominejinja |
| Q11597092 | 穂積阿蘇神社 | ほづみあそじんじゃ | Hozumori Aso Shrine | Hozumiasojinja |
| Q48758315 | 羽浦神社 | はのうらじんじゃ | Hanoura Shrine | Hanorajinja |
| Q19841356 | 祝園神社 | ほうそのじんじゃ | Housono Shrine | Hosonojinja |
| Q11556513 | 洲崎神社 | すさきじんじゃ | Sunosaki Shrine | Susakijinja |
| Q11557476 | 浅間神社 | あさまじんじゃ | Ichinomiya Asama Shrine | Asamajinja |
| Q48763725 | 水主神社 | みずしじんじゃ | Minushi Shrine | Mizushijinja |
| Q54153251 | 市原稲荷神社 | いちばらいなりじんじゃ | Ichihara Inari Shrine | Ichibarainarijinja |
| Q30925653 | 大麻山神社 | おおあさやまじんじゃ | Taimasan Shrine | Oasayamajinja |
| Q11584639 | 知立神社 | ちりふじんじゃ | Chiryū Shrine | Chirifujinja |
| Q11585337 | 石園座多久虫玉神社 | いそのにますたくむしたまじんじゃ | Iwazononiimasu Takumushitama Shrine | Isononimasutakumushitamajinja |
| Q11548625 | 水戸東照宮 | とうしょうぐう | Mito Tōshō-gū | Toshogu |
| Q11549616 | 氷川神社 | ひかわじんじゃ | Toyotama Hikawa Shrine | Hikawajinja |
| Q11578102 | 男乃宇刀神社 | おのうとじんじゃ | Onouto Shrine | Onotojinja |
| Q11633342 | 豊受大神社 | とゆけだいじんじゃ | Toyōke Daijinja | Toyukedaijinja |
| Q2827917 | 合氣神社 | あいきじんじゃ | Iwama Dōjō | Aikijinja |
| Q11572840 | 玉野御嶽神社 | たまのおんたけじんじゃ | Tamano Ontake Shrine | Tamanontakejinja |
| Q11573796 | 琴浦神社 | ことうらじんじゃ | Kotoura Shrine | Kotorajinja |
| Q11574829 | 生石神社 | おうしこじんじゃ | Oushiko Shrine | Oshikojinja |
| Q11575107 | 田ノ浦山宮神社 | たのうらやまみやじんじゃ | Tanoura Yamamiya Shrine | Tanorayamamiyajinja |
| Q22117916 | 稲前神社 | いなくまじんじゃ | Inasaki Shrine | Inakumajinja |
| Q22118539 | 貴布禰神社 | きふねじんじゃ | Kibune Shrine | Kifunejinja |
| Q22119431 | 調田坐一事尼古神社 | くだにますひとことねこじんじゃ | hikida Shrine | Kudanimasuhitokotonekojinja |
| Q22118972 | 四本木稲荷神社 | しほんぎいなりじんじゃ | Yomotogi Inari Shrine | Shihongiinarijinja |
| Q60988202 | 釜石製鐡所山神社 | かまいしせいてつしょさんじんじゃ | Nippon Steel Corporation North Nippon Works San Shrine | Kamaishiseitetsushosanjinja |
| Q11393653 | 兵庫縣神戸護國神社 | ひょうごけんこうべごこくじんじゃ | Hyogo Kobe Gokoku Shrine | Hyogokenkobegokokujinja |
| Q11555416 | 波々伯部神社 | ほうかべじんじゃ | Hohokabe Shrine | Hokabejinja |
| Q11565717 | 潮江天満宮 | うしおえてんまんぐう | Shioe Tenmangū | Ushioetenmangu |
| Q11565730 | 潮目天満神社 | しおのめてんまんじんじゃ | Shiome Tenman Shrine | Shionometenmanjinja |
| Q11400330 | 勝手神社 | かつてじんじゃ | Katte Shrine | Katsutejinja |
| Q11404780 | 十三騎神社 | じゅうさんきじんじゃ | Juusanki Shrine in Shinmei-sha | Jusankijinja |
| Q116157250 | 中洲國廣稲荷神社 | くにひろじんじゃ | Nakasu-kunihiro Inari Shrine | Kunihirojinja |
| Q116829251 | 神明社 | しんめいしゃ | Toro Shinmei-sha | Shinmeisha |
| Q55532964 | 鵜鳥神社 | うねどりじんじゃ | Unotori Shrine | Unedorijinja |
| Q55540317 | 大穴持神社 | おおなむぢじんじゃ | Ōmunaji Shrine | Onamujijinja |
| Q56061879 | 大石神社 | おおいしじんじゃ | Ooishi Shrine | Oishijinja |
| Q56195170 | 春日神社 | かすがじんじゃ | Akiyama Kasuga Shrine | Kasugajinja |
| Q21449537 | 高士神社 | クスクスじんじゃ | Gaoshi Shrine | Kusukusujinja |
| Q11539560 | 森島厳島浅間神社 | いつくしまじんじゃ | Morjima Itsukushima Sengen Shrine | Itsukushimajinja |
| Q11436783 | 大水上神社 | おおみなかみじんじゃ | Oominakami Shrine | Ominakamijinja |
| Q11433429 | 大和大国魂神社 | やまとおおくにたまじんじゃ | Yamato-Okunitama Shrine | Yamatokunitamajinja |
| Q11558680 | 海上八幡宮 | うなかみはちまんぐう | Uminaka-hachimangū | Unakamihachimangu |
| Q11611081 | 聖母宮 | しょうもぐう | Shoumogu | Shomogu |
| Q54153286 | 前野天満社 | まえのてんまんしゃ | Kumano-tenmansha | Maenotenmansha |
| Q11617049 | 茂宇気神社 | もうけじんじゃ | Mouke Shrine | Mokejinja |
| Q97175484 | 天祖神社 | てんそじんじゃ | Koto Tenso Shrine | Tensojinja |
| Q24862031 | 矢越八幡宮 | やごしはちまんぐう | Yahoshi-hachimangū | Yagoshihachimangu |
| Q24864032 | 堀出神社 | ほりいでじんじゃ | Horīde Shrine | Horiidejinja |
| Q106968548 | 熊野奥照神社 | くまのおくてるじんじゃ | Kumano Okuteru Shrine | Kumanokuterujinja |
| Q107410070 | 常陸国出雲大社 | ひたちこくいずもたいしゃ | Hitachi-no-Kuni Izumo-taisha | Hitachikokuizumotaisha |
| Q11438318 | 大祁於賀美神社 | おおおかみじんじゃ | Takeokami Shrine | Okamijinja |
| Q125688027 | 櫟谷七野神社 | いちいだにななのじんじゃ | Ichidani Nanano Shichino Kasuga Shrine (Kamigyo Kyoto) | Ichiidaninananojinja |
| Q126285710 | 神足神社 | こうたりじんじゃ | Koutari Shrine | Kotarijinja |
| Q11643225 | 郡浦神社 | こうのうらじんじゃ | Konoura Shrine | Konorajinja |
| Q43594603 | 倭恩智神社 | やまとおんちじんじゃ | Yamato Onchi Shrine | Yamatonchijinja |
| Q11668667 | 高之御前神社 | たかゆきおんざきじんじゃ | Taka-no-Gozen Shrine | Takayukionzakijinja |
| Q109062189 | 佐野八坂神社 | やさかじんじゃ | Sano Yasaka Shrine, Kanegasaku Matsudo | Yasakajinja |
| Q97218279 | 神明社 | しんめいしゃ | Tsukazaki Shinmei-sha | Shinmeisha |
| Q97310667 | 大和町八幡神社 | やまとちょうはちまんじんじゃ | Yamato Hachiman Shrine | Yamatochohachimanjinja |
| Q11442508 | 天太玉命神社 | あめのふとたまのみことじんじゃ | Ame-Futotama-no-Mikoto Shrine | Amenofutotamanomikotojinja |
| Q121626916 | 大野原八幡神社 | はちまんじんじゃ | Ōnohara Hachiman Shrine | Hachimanjinja |
| Q122314387 | 北市戎神社 | きたいちえびすじんじゃ | Kitachi Ebisu Shrine | Kitaichiebisujinja |
| Q11499585 | 敬満神社 | きょうまんじんじゃ | Keiman Shrine | Kyomanjinja |
| Q11457393 | 寒川神社 | さむかわじんじゃ | Samugawa Shrine | Samukawajinja |
| Q11658605 | 陸奥総社宮 | むつそうじゃぐう | Mutsu Sōsha-no-miya | Mutsusojagu |
| Q11447985 | 孕神社 | はらうみじんじゃ | Harami Shrine | Haraumijinja |
| Q11450246 | 安井金比羅宮 | やすいこんぴらぐう | Yasui Kompira-gu | Yasuikonpiragu |
| Q11451841 | 宗佐厄神八幡神社 | そうさやくじんはちまんじんじゃ | Sousayakujin-hachiman Shrine | Sosayakujinhachimanjinja |
| Q11427180 | 堀ノ内熊野神社 | ほりのうちくまのじんじゃ | Horinouchi Kumano Shrine | Horinochikumanojinja |
| Q115040730 | 氷川神社 | ひかわじんじゃ | Oto Hikawa Shrine | Hikawajinja |
| Q115040917 | 氷川神社 | ひかわじんじゃ | Oyaguchi Hikawa Shrine | Hikawajinja |
| Q115041081 | 氷川神社 | ひかわじんじゃ | Takagi Hikawa Shrine | Hikawajinja |
| Q115098098 | 神明神社 | しんめいじんじゃ | Mikura Shinmei Shrine | Shinmeijinja |
| Q115117373 | 飯塚氷川神社 | いいずかひかわじんじゃ | Īzukahikawa Shrine | Iizukahikawajinja |
| Q109767660 | 豊栄稲荷神社 | ほうえいいなりじんじゃ | Toyosaka Inari Shrine | Hoeiinarijinja |
| Q131283920 | 天照皇大神社 | てんしょうこうだいじんじゃ | Tenshō Daijinja | Tenshokodaijinja |
| Q11430652 | 多坐弥志理都比古神社 | おおにますみしりつひこじんじゃ | Oonimasumishiritsuhiko Shrine | Onimasumishiritsuhikojinja |
| Q65248672 | 伊豫岡八幡神社 | いよおかはちまんじんじゃ | Iyooka Hachiman Shrine | Iyokahachimanjinja |
| Q115038589 | 氷川神社 | ひかわじんじゃ | Oyaba Hikawa Shrine | Hikawajinja |
| Q134602865 | 火皇子神社 | ひのおうしじんじゃ | Hinōushi Shrine | Hinoshijinja |
| Q11676455 | 鹽竈神社 | しおがまじんじゃ | Shigama Shrine | Shiogamajinja |
| Q66085127 | 鴨大神御子神主玉神社 | かもおおかみみこかみぬしたまじんじゃ | Kamo-Ōkami-miko-kami-nushi-tama Shrine | Kamokamimikokaminushitamajinja |
| Q71917331 | 六軒町諏訪神社 | すわじんじゃ | Rokkenchō-Suwa Shrine | Suwajinja |
| Q111040360 | 長間神社 | ながんまじんじゃ | Nagamma Shrine | Naganmajinja |
| Q115194219 | 氷川神社 | ひかわじんじゃ | Tsuchiya Hikawa Shrine | Hikawajinja |
| Q115194250 | 氷川神社 | ひかわじんじゃ | Komurada Hikawa Shrine | Hikawajinja |
| Q65292740 | 須波阿湏疑神社 | すわあずきじんじゃ | Suwāzuki Shrine | Suwaazukijinja |
| Q84929833 | 大直禰子神社 | おおただねこじんじゃ | Otata-neko Shrine | Otadanekojinja |
| Q124392557 | 香港神社 | ほんこんじんじゃ | Hong Kong Shrine | Honkonjinja |
| Q118358805 | 斉斉哈爾神社 | チチハルじんじゃ | Qiqihar Shrine | Chichiharujinja |
| Q118959173 | 西小松川諏訪神社 | にしこまつがわすわじんじゃ | Nish-Komatsugawa Suwa Shrine | Nishikomatsugawasuwajinja |
| Q130436470 | 東八幡神社 | ひがしまちまんじんじゃ | Higashi Hachiman Shrine | Higashimachimanjinja |
| Q130581082 | 戸ケ崎香取神社 | かとりじんじゃ | Togasaki Katori Shrine | Katorijinja |
| Q105710159 | 越中護国八幡宮 | えっちゅうごこくはちまんぐう | Etchū Gokoku Hachimangū | Ecchugokokuhachimangu |
| Q134887393 | 飯玉神社 | いいたまじんじゃ | ītama Shrine | Iitamajinja |
| Q134149661 | 西浅草八幡神社 | にしあさくさはちまんじんじゃ | Nishu-asakusa Hachiman Shrine | Nishiasakusahachimanjinja |
| Q103914709 | 駒形大神社 | まがただいじんじゃ | Komagata Daijinja | Magatadaijinja |
| Q134957407 | 和物所稲荷神社 | あえもんじょいなりじんじゃ | Wamonoshoinari Shrine | Aemonjoinarijinja |
| Q97310706 | 氷川神社 | ひかわじんじゃ | Egota Hikawa Shrine | Hikawajinja |
| Q134893150 | 大津諏訪神社 | おおつすわじんじゃ | Ootsu Suwa Shrine | Otsusuwajinja |
| Q11473513 | 岡田宮 | おかだぐう | Okagagū | Okadagu |
| Q85884515 | 須佐之男尊神社 | すさのおのみことじんじゃ | Susanoo no mikoto Shrine | Susanonomikotojinja |
| Q17228074 | 海底神社 | かいていじんじゃ | Underwater Shrine | Kaiteijinja |
| Q17216962 | 志賀理和気神社 | しかりわけじんじゃ | Shigariwake Shrine | Shikariwakejinja |
| Q106852466 | 稲荷森稲荷神社 | いなりもりいなりじんじゃ | Tōkamori Inari Shrine | Inarimoriinarijinja |
| Q17194122 | 宇治山田神社 | うじようだじんじゃ | Ujōda Shrine | Ujiyodajinja |
| Q17210061 | 浅間神社 | せんげんじんじゃ | Ekoda-sengen Shrine | Sengenjinja |
| Q115034565 | 氷川神社 | ひかわじんじゃ | Nishiasuma Hikawa Shrine | Hikawajinja |
| Q106852475 | 銀杏岡八幡神社 | いちょうがおかはちまんじんじゃ | Ichigaoka Hachiman Shrine | Ichogaokahachimanjinja |
| Q134886342 | 三島愛宕神社 | みしまあたごじんじゃ | Mishimātago Shrine | Mishimaatagojinja |
| Q111076400 | 那須温泉神社 | ゆぜんじんじゃ | Nasu Yuzen Shrine | Yuzenjinja |
| Q131129374 | 大佐倉麻賀多神社 | おおざくらまかたじんじゃ | Makata Shrine (Ōzakura, Sakura) | Ozakuramakatajinja |
| Q128867054 | 大間々神明宮 | しんめいぐう | Omama-shinmei-gu | Shinmeigu |
| Q17220848 | 火雷神社 | ほのいかづちじんじゃ | Karai Shrine | Honoikazuchijinja |
| Q11475213 | 岩根沢三山神社 | いわねさわさんざんじんじゃ | Iwaneaswa Sanzan Shrine | Iwanesawasanzanjinja |
| Q11481110 | 師岡熊野神社 | もろおかくまのじんじゃ | Morooka Kumano Shrine | Morokakumanojinja |
| Q97754579 | 貴船神明社 | きふねしんめいしゃ | Kibune Shinmeisha | Kifuneshinmeisha |
| Q124804728 | 友呂岐神社 | ともろぎじんじゃ | Shrines in Neyagawa, Osaka | Tomorogijinja |
| Q135260026 | 二荒神社 | ふたあらじんじゃ | Futāra Shrine | Futaarajinja |
| Q134957836 | 飯森浅間神社 | いいもりせんげんじんじゃ | īmorisengen Shrine | Iimorisengenjinja |
| Q135185681 | 合祀：大津神社 | ひょうずじんじゃ | Co-Enshrinement of Hyōzu Shrine | Hyozujinja |
| Q135040450 | 御島石部神社 | みしまいそべじんじゃ | Mishimanoisobeno Shrine | Mishimaisobejinja |
| Q135040487 | 越敷神社 | おしきじんじゃ | Woshikino Shrine | Oshikijinja |
| Q11486674 | 建水分神社 | たけみくまりじんじゃ | Takemimakuri Shrine | Takemikumarijinja |
| Q135258978 | 大内神社 | おおうちじんじゃ | Ōuchi Shrine | Ochijinja |
| Q135260631 | 飯有神社 | いいありじんじゃ | īari Shrine | Iiarijinja |
| Q134988809 | 大内神社 | おおうちじんじゃ | Ōuchi Shrine | Ochijinja |
| Q134887266 | 飯塚神社 | いいづかじんじゃ | īzuka Shrine | Iizukajinja |
| Q135425370 | 飯玉神社 | いいたまじんじゃ | ītama Shrine | Iitamajinja |
| Q135425879 | 飯玉神社 | いいだまじんじゃ | īdama Shrine | Iidamajinja |
| Q135260131 | 幣石神社 | へいいしじんじゃ | Heīshi Shrine | Heiishijinja |
| Q135425461 | 飯玉神社 | いいだまじんじゃ | īdama Shrine | Iidamajinja |
| Q135433892 | 飯留神社 | いいどめじんじゃ | īdome Shrine | Iidomejinja |
| Q135425941 | 飯玉神社 | いいだまじんじゃ | īdama Shrine | Iidamajinja |
| Q135425181 | 飯玉神社 | いいだまじんじゃ | īdama Shrine | Iidamajinja |
| Q135424927 | 飯玉神社 | いいだまじんじゃ | īdama Shrine | Iidamajinja |
| Q135424956 | 飯玉神社 | いいたまじんじゃ | ītama Shrine | Iitamajinja |
| Q135434253 | 森稲妻神社 | もりいなづまじんじゃ | Morīnazuma Shrine | Moriinazumajinja |
| Q135459328 | 石上神社 | いしがみじんじゃ | Isonokami Shrine | Ishigamijinja |
| Q135425225 | 飯玉神社 | いいだまじんじゃ | īdama Shrine | Iidamajinja |
| Q135425226 | 飯玉神社 | いいたまじんじゃ | ītama Shrine | Iitamajinja |
| Q135425329 | 飯玉神社 | いいだまじんじゃ | īdama Shrine | Iidamajinja |
| Q135461607 | 安塚神社 | やすづかじんじゃ | Azuma Shrine | Yasuzukajinja |
| Q135461624 | 秋葉神社 | あきはじんじゃ | Akiba Shrine | Akihajinja |
| Q135461904 | 八幡神社 | やわたじんじゃ | Hachiman Shrine | Yawatajinja |
| Q135461322 | 八幡神社 | やはたじんじゃ | Hachiman Shrine | Yahatajinja |
| Q135462723 | 神明宮 | しんんめいぐう | Shinmei-gū | Shinnmeigu |
| Q135463563 | 八幡神社 | やはたじんじゃ | Hachiman Shrine | Yahatajinja |
| Q135462874 | 大山祗神社 | おおやまつみじんじゃ | Oyamazumi Shrine | Oyamatsumijinja |
| Q135463098 | 八幡社 | やはたしゃ | Hachiman Shrine | Yahatasha |
| Q135463693 | 二荒山神社 | ふたあらやまじんじゃ | Futarasan Shrine | Futaarayamajinja |
| Q135462993 | 大山祗神社 | おおやまつみじんじゃ | Oyamazumi Shrine | Oyamatsumijinja |
| Q135464338 | 二荒山神社 | ふたあらやまじんじゃ | Futarasan Shrine | Futaarayamajinja |
| Q135464460 | 石井神社 | いわいじんじゃ | Ishii Shrine | Iwaijinja |
| Q139661007 | 荒神社 | かわうじんじゃ | Kuwau Jinja | Kawaujinja |
