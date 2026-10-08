"""Turn [[links]] and old-style {{ill}}s in a retranslated page into Emma's ill format.

Emma, 2026-10-08: every link that has a Japanese counterpart is written
{{ill|ENGLISH_TITLE|ja|JAPANESE_TITLE|lt=english display|lt_ja=japanese display}}
with no qid (a later script adds those). Links with no Japanese counterpart in the
map (publishers of English books, etc.) stay plain.

Usage: python retranslation/ill_convert.py <new.wiki>   (rewrites the file in place)
"""
import io
import re
import sys

# English title -> Japanese title (and Japanese display, when it differs from the title)
JA = {
    "Himetataraisuzu-hime": ("媛蹈鞴五十鈴媛命", None),
    "Isuzuyori-hime": ("五十鈴依媛命", None),
    "Japanese mythology": ("日本神話", None),
    "Emperor Jimmu": ("神武天皇", None),
    "Nihon Shoki": ("日本書紀", None),
    "Kotoshironushi": ("事代主神", None),
    "Wani (dragon)": ("和邇", "八尋熊鰐"),
    "Sendai Kuji Hongi": ("先代旧事本紀", None),
    "Miwa clan": ("三輪氏", None),
    "Kamo clan": ("賀茂朝臣氏", "賀茂氏"),
    "Emperor Suizei": ("綏靖天皇", None),
    "Emperor Annei": ("安寧天皇", None),
    "Kojiki": ("古事記", None),
    "Ōkume": ("大久米命", None),
    "Shimogamo Shrine": ("賀茂御祖神社", None),
    "Tamayori-hime (mother of Jimmu)": ("タマヨリビメ (日向神話)", "タマヨリビメ"),
    "List of Japanese deities": ("日本の神の一覧", None),
    "Utagawa Kuniyoshi": ("歌川国芳", None),
    "Mount Miwa": ("三輪山", None),
    "Ōkuninushi": ("大国主", None),
    "Tamakushi-hime": ("玉櫛媛", None),
    "Ōmononushi": ("大物主神", None),
    "Hyūga Province": ("日向国", None),
    "Miyazaki Prefecture": ("宮崎県", None),
    "Nara Basin": ("奈良盆地", None),
    "Jimmu's Eastern Expedition": ("神武東征", None),
    "Mount Unebi": ("畝傍山", None),
    "Kashihara, Nara": ("橿原市", None),
    "Japanese imperial year": ("神武天皇即位紀元", None),
    "Tagishimimi": ("手研耳命", None),
    "Ahiratsu-hime": ("吾平津媛", None),
    "Hikoyai": ("日子八井命", None),
    "Kamuyaimimi": ("神八井耳命", None),
    "Ō clan": ("多氏", None),
    "Settsu Province": ("摂津国", None),
    "Yamato Province": ("大和国", None),
    "Izumo": ("出雲神話", None),
    "Shinsen Shōjiroku": ("新撰姓氏録", None),
    "Yatagarasu": ("八咫烏", None),
    "Mishima District, Osaka": ("三島郡 (大阪府)", "三島郡"),
    "Engishiki": ("延喜式", None),
    "Mishima Kamo Shrine": ("三島鴨神社", None),
    "Takatsuki": ("高槻市", None),
    "Ibaraki, Osaka": ("茨木市", None),
    "Motoori Norinaga": ("本居宣長", None),
    "Sangō, Nara": ("三郷町", None),
    "Ikoma District, Nara": ("生駒郡", None),
    "Ugayafukiaezu": ("ウガヤフキアエズ", None),
    "Toyotama-hime": ("トヨタマヒメ", None),
    "Hoori": ("ホオリ", None),
    "Susanoo": ("スサノオ", None),
    "Lilium japonicum": ("ササユリ", None),
    "Sai River (Nara)": ("狭井川", None),
    "Ōmiwa Shrine": ("大神神社", None),
    "Yamato River": ("大和川", None),
    "tatara": ("たたら製鉄", None),
    "Amaterasu": ("天照大神", None),
    "Ama-no-Iwato": ("天岩戸", None),
    "Izumo no Kuni Fudoki": ("出雲国風土記", None),
    "Daisen Kofun": ("仁徳天皇陵", None),
    "dōtaku": ("銅鐸", None),
    "Kashihara Shrine": ("橿原神宮", None),
    "Emperor Meiji": ("明治天皇", None),
    "Sakurai, Nara": ("桜井市", None),
    "Mashiki, Kumamoto": ("益城町", None),
    "Kōsa, Kumamoto": ("甲佐町", None),
    "Heibonsha": ("平凡社", None),
    "Taryo Obayashi": ("大林太良", None),
    "Empress of Japan": ("皇后 (日本)", "皇后"),
    "Amenohikatakushihikata": ("天日方奇日方命", None),
    "Isonokami-ni-imasu Takumushitama Shrine": ("石園座多久虫玉神社", None),
    "Mishima-mizokui": ("三嶋溝抗命", None),
    "Mizokui Shrine": ("溝咋神社", None),
    "Isagawa Shrine": ("率川神社", None),
}


def ill(en, display):
    ja, ja_disp = JA[en]
    return "{{ill|%s|ja|%s|lt=%s|lt_ja=%s}}" % (en, ja, display, ja_disp or ja)


def convert(text):
    def link(m):
        target, _, disp = m.group(1).partition("|")
        if target in JA:
            return ill(target, disp or target)
        return m.group(0)

    def old_ill(m):
        parts = m.group(1).split("|")
        en = parts[0]
        named = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        if en in JA:
            return ill(en, named.get("lt", en))
        return m.group(0)

    text = re.sub(r"\{\{ill\|([^{}]+)\}\}", old_ill, text)
    text = re.sub(r"\[\[(?!Category:|File:|#)([^\[\]]+)\]\]", link, text)
    return text


if __name__ == "__main__":
    p = sys.argv[1]
    s = io.open(p, encoding="utf-8").read()
    out = convert(s)
    io.open(p, "w", encoding="utf-8", newline="\n").write(out)
    left = [l for l in re.findall(r"\[\[([^\]]+)\]\]", out) if not l.startswith(("Category:", "File:", "#"))]
    print(p, "plain links left:", left)
