"""
Romaji-to-Korean hangul transliterator.
Converts Japanese kana/romaji into Korean hangul approximation,
preserving voiced/unvoiced distinctions (unlike tokiponizer which devoices).
"""

from tokiponizer import normalize, kana_to_romaji, tokenize_romaji

# ----------------------------
# Romaji → Hangul syllable mapping
# ----------------------------
# Unlike tokiponizer, we preserve voicing distinctions.

ROMAJI_TO_HANGUL = {
    # Vowels
    "a": "아", "i": "이", "u": "우", "e": "에", "o": "오",

    # K-row
    "ka": "카", "ki": "키", "ku": "쿠", "ke": "케", "ko": "코",

    # S-row
    "sa": "사", "shi": "시", "su": "스", "se": "세", "so": "소",

    # T-row
    "ta": "타", "chi": "치", "tsu": "쓰", "tu": "쓰", "te": "테", "to": "토",

    # N-row
    "na": "나", "ni": "니", "nu": "누", "ne": "네", "no": "노",

    # H-row
    "ha": "하", "hi": "히", "hu": "후", "fu": "후", "he": "헤", "ho": "호",

    # M-row
    "ma": "마", "mi": "미", "mu": "무", "me": "메", "mo": "모",

    # Y-row
    "ya": "야", "yu": "유", "yo": "요",

    # R-row
    "ra": "라", "ri": "리", "ru": "루", "re": "레", "ro": "로",

    # W-row
    "wa": "와", "wi": "위", "we": "웨", "wo": "오",

    # Standalone n (ん) — handled specially below
    "n": "ㄴ",

    # Voiced: G-row
    "ga": "가", "gi": "기", "gu": "구", "ge": "게", "go": "고",

    # Voiced: Z-row
    "za": "자", "ji": "지", "zu": "즈", "ze": "제", "zo": "조",

    # Voiced: D-row
    "da": "다", "di": "지", "du": "즈", "de": "데", "do": "도",

    # Voiced: B-row
    "ba": "바", "bi": "비", "bu": "부", "be": "베", "bo": "보",

    # P-row
    "pa": "파", "pi": "피", "pu": "푸", "pe": "페", "po": "포",
}

# Yoon (palatalized) → Hangul
YOON_TO_HANGUL = {
    "kya": "캬", "kyu": "큐", "kyo": "쿄",
    "sha": "샤", "shu": "슈", "sho": "쇼",
    "cha": "차", "chu": "추", "cho": "초",
    "nya": "냐", "nyu": "뉴", "nyo": "뇨",
    "hya": "햐", "hyu": "휴", "hyo": "효",
    "mya": "먀", "myu": "뮤", "myo": "묘",
    "rya": "랴", "ryu": "류", "ryo": "료",
    "gya": "갸", "gyu": "규", "gyo": "교",
    "ja": "자",  "ju": "주",  "jo": "조",
    "bya": "뱌", "byu": "뷰", "byo": "뵤",
    "pya": "퍄", "pyu": "퓨", "pyo": "표",
    "dya": "댜", "dyu": "듀", "dyo": "됴",
}

# ----------------------------
# Unicode arithmetic for batchim (final consonant)
# ----------------------------
# Korean syllable blocks: base = 0xAC00
# Each block = (initial * 21 + medial) * 28 + final
# ㄴ (nieun) as final = 4

HANGUL_BASE = 0xAC00
FINAL_NIEUN = 4  # ㄴ batchim index

def _has_final(char):
    """Check if a hangul syllable character already has a final consonant (batchim)."""
    code = ord(char) - HANGUL_BASE
    if code < 0 or code >= 11172:
        return False
    return (code % 28) != 0

def _add_nieun_batchim(char):
    """Add ㄴ batchim to a hangul syllable that has no final consonant."""
    code = ord(char) - HANGUL_BASE
    if code < 0 or code >= 11172:
        return char + "ㄴ"
    if (code % 28) != 0:
        # Already has a batchim, can't merge — append standalone ㄴ
        return char + "ㄴ"
    return chr(ord(char) + FINAL_NIEUN)


def tokenize_romaji_korean(text):
    """Tokenize romaji for Korean mapping (uses same logic as tokiponizer
    but checks Korean-specific maps)."""
    tokens = []
    i = 0
    while i < len(text):
        matched = False
        for size in (3, 2, 1):
            chunk = text[i:i+size]
            if chunk in YOON_TO_HANGUL or chunk in ROMAJI_TO_HANGUL:
                tokens.append(chunk)
                i += size
                matched = True
                break
        if not matched:
            i += 1
    return tokens


def koreanize(text):
    """Convert Japanese text (kana or romaji) to Korean hangul approximation.

    Returns a single string (no variants, unlike tokiponize).
    """
    text = normalize(text)
    text = kana_to_romaji(text)

    tokens = tokenize_romaji_korean(text)

    # Map tokens to hangul
    hangul_parts = []
    for t in tokens:
        if t in YOON_TO_HANGUL:
            hangul_parts.append(YOON_TO_HANGUL[t])
        elif t in ROMAJI_TO_HANGUL:
            hangul_parts.append(ROMAJI_TO_HANGUL[t])

    # Merge standalone ㄴ (from ん) as batchim into preceding syllable
    merged = []
    for part in hangul_parts:
        if part == "ㄴ" and merged:
            prev = merged[-1]
            last_char = prev[-1]
            # Try to merge ㄴ as batchim into the last character
            if '\uAC00' <= last_char <= '\uD7A3' and not _has_final(last_char):
                merged[-1] = prev[:-1] + _add_nieun_batchim(last_char)
            else:
                merged.append("ㄴ")
        else:
            merged.append(part)

    return "".join(merged)


if __name__ == "__main__":
    print(koreanize("Hachiman"))      # 하치만
    print(koreanize("じんじゃ"))       # 진자
    print(koreanize("トヨタマヒメ"))   # 토요타마히메
    print(koreanize("かんだ"))         # 칸다
