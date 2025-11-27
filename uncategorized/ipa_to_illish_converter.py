#!/usr/bin/env python3
"""
IPA to Illish Phonology Converter
==================================
Converts English IPA pronunciation to Illish orthography following
phonology rules: tone assignment, coda reduction, vowel length, nasalization.

Uses IPA tone letters (tone bars):
  ˩ = extra low tone
  ˥ = extra high tone
  ˩˥ = rising tone (low to high)
  ˥˩ = sinking tone (high to low)
  ˥˩˥ = peaking tone
  ˩˥˩ = dipping tone

Special rule: Rising tone at word end → vowel˩˥ + ʔ + vowel˥
Example: kept /kɛpt/ → ke˩˥ʔe˥

Usage:
    from ipa_to_illish_converter import english_ipa_to_illish
    illish_form = english_ipa_to_illish("kæt")  # Returns "ka˩" (with low tone letter)
"""

import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Tone letters (IPA tone bar notation)
TONE_LETTERS = {
    'low': '˩',          # extra low tone
    'high': '˥',         # extra high tone
    'rising': '˩˥',      # rising tone (low to high)
    'sinking': '˥˩',     # sinking tone (high to low)
    'peaking': '˥˩˥',    # peaking tone (high-low-high)
    'dipping': '˩˥˩'     # dipping tone (low-high-low)
}

# Vowel inventory
VOWELS = set('ɪɛæɔʊɑɒəɜaeiouɨʉɯʌ')
# Voiced consonants (obstruents AND liquids/nasals)
VOICED_CONSONANTS = set('bvdðgzʒmnŋlrwj')  # includes voiced obstruents, nasals, liquids, glides

def is_vowel(char):
    """Check if character is a vowel"""
    return char in VOWELS

def analyze_word(ipa_str):
    """
    Parse IPA string into syllables
    Returns: list of (onset, vowel, coda) tuples
    Handles diphthongs as single nuclei (e.g., oʊ, aɪ, etc.)
    """
    ipa = ipa_str.strip().strip('/').replace('ˈ', '').replace('ˌ', '')

    if not ipa:
        return []

    syllables = []
    i = 0

    while i < len(ipa):
        onset = ''
        nucleus = ''
        coda = ''

        # Collect onset consonants
        while i < len(ipa) and not is_vowel(ipa[i]):
            onset += ipa[i]
            i += 1

        # Collect nucleus (vowels + optional length mark, treating diphthongs as single unit)
        if i < len(ipa) and is_vowel(ipa[i]):
            nucleus += ipa[i]
            i += 1
            # Check for diphthong (vowel immediately followed by another vowel)
            if i < len(ipa) and is_vowel(ipa[i]):
                nucleus += ipa[i]
                i += 1
            # Check for length mark
            if i < len(ipa) and ipa[i] == 'ː':
                nucleus += ipa[i]
                i += 1

        # Collect coda consonants (up to next vowel or end)
        while i < len(ipa) and not is_vowel(ipa[i]):
            coda += ipa[i]
            i += 1

        if nucleus:
            syllables.append((onset, nucleus, coda))

    return syllables

def collapse_s_supercluster(onset):
    """
    Handle S + plosive + liquid clusters -> lateral affricate
    Only collapse complete supercluster patterns at WORD START
    Handles both 'r' (U+0072) and 'ɹ' (U+0279)
    str, spr, spl, skr -> tɬ (lateral affricate)
    """
    patterns = [
        ('str', 'tɬ'), ('stɹ', 'tɬ'),    # str with r or ɹ
        ('spr', 'tɬ'),
        ('spl', 'tɬ'),
        ('skr', 'tɬ'), ('skɹ', 'tɬ'),    # skr with r or ɹ
    ]
    for pattern, replacement in patterns:
        if onset.startswith(pattern):
            return replacement + onset[len(pattern):]
    return onset

def classify_coda(coda):
    """Classify coda type for tone assignment"""
    if not coda:
        return 'open'

    plosives = set('ptkbdg')
    fricatives = set('sfvθðzʃʒhʂʐɕʑ')
    nasals = set('mnŋ')
    liquids = set('lr')
    affricates = {'tʃ', 'dʒ'}

    if coda in affricates:
        return 'fricative'

    if len(coda) == 1:
        if coda in plosives:
            return 'plosive'
        elif coda in fricatives:
            return 'fricative'
        elif coda in nasals:
            return 'nasal'
        elif coda in liquids:
            return 'liquid'

    if len(coda) > 1:
        if any(c in liquids for c in coda):
            return 'liquid_cluster'
        if all(c in plosives for c in coda):
            return 'plosive_cluster'
        return 'other_cluster'

    return 'open'

def assign_lexical_tone(coda_type, coda=''):
    """
    Assign lexical tone based on coda
    Special rule: nasal + consonant = low tone
    """
    # Check for nasal + consonant cluster (e.g., 'ŋθ', 'ŋk', 'nt', 'ns')
    if coda and len(coda) > 1:
        nasals = set('mnŋ')
        consonants = set('ptkbdgfvszʃʒθðʂʐlrɹwj')
        # If first is nasal and second is any consonant: low tone
        if coda[0] in nasals and coda[1] in consonants:
            return 'low'

    tone_map = {
        'open': 'high',
        'plosive': 'low',
        'fricative': 'high',
        'nasal': 'high',
        'liquid': 'high',
        'plosive_cluster': 'rising',
        'liquid_cluster': 'sinking',
        'other_cluster': 'high'
    }
    return tone_map.get(coda_type, 'low')

def should_vowel_be_long(nucleus, coda):
    """
    Determine if vowel should be long
    Rules:
    1. Voiced OBSTRUENT coda → long vowel
    2. Nasal alone → short vowel (nasalize only, don't lengthen)
    3. Nasal + voiced consonant in cluster → long vowel
    4. Voiceless coda → short vowel
    """
    if not coda:
        # No coda = use what's in the IPA
        return 'ː' in nucleus

    # Check the last consonant in the coda
    if len(coda) >= 2 and coda[-2:] == 'dʒ':
        # dʒ is voiced obstruent
        return True

    last_consonant = coda[-1]
    nasals = set('mnŋ')
    voiced_obstruents = set('bvdðgzʒwj')

    # If coda is nasal + consonant cluster: check if the consonant is voiced
    if len(coda) > 1 and coda[0] in nasals:
        # Check second consonant - if it's voiced, lengthen
        if len(coda) >= 2 and coda[1] in voiced_obstruents:
            return True
        # Nasal + voiceless = short vowel
        return False

    # Single nasal coda alone: does NOT lengthen (only nasalizes)
    if last_consonant in nasals:
        return False

    # Voiced obstruent alone = long vowel
    if last_consonant in voiced_obstruents:
        return True

    # Voiceless consonant = short vowel (ignore any length mark in IPA)
    return False

def reduce_coda_to_illish(coda, is_final=False):
    """
    Reduce English coda to Illish inventory (s, f, m, n, l, Ø)
    Handles:
    - Superclusters (e.g., spl, str, etc. within codas) → tɬ (lateral affricate)
    - Nasal + stop clusters: keep nasal as nasalization + reduce final consonant
    - Other clusters: keep first consonant only
    Rule: All fricatives except F → S when at word-final position
    Returns: (illish_coda, is_nasalized)
    """
    if not coda:
        return '', False

    # Check for superclusters within coda (e.g., "kspl" contains "spl")
    supercluster_patterns = [('spl', 'tɬ'), ('str', 'tɬ'), ('stɹ', 'tɬ'), ('spr', 'tɬ'),
                              ('skr', 'tɬ'), ('skɹ', 'tɬ')]
    for pattern, replacement in supercluster_patterns:
        if pattern in coda:
            # Found a supercluster - use it and ignore consonants before it
            return replacement, False

    # Handle affricates (always -> s)
    if coda in {'tʃ', 'dʒ'}:
        return 's', False

    # Single consonants
    if len(coda) == 1:
        c = coda[0]
        if c in {'s', 'z', 'ʃ', 'ʒ', 'θ', 'ð', 'ʂ', 'ʐ', 'h'}:
            # All fricatives (except f, v which are handled below) -> s
            return 's', False
        elif c in {'f', 'v'}:
            # Labiodental fricatives stay as f
            return 'f', False
        elif c == 'm':
            return 'm', True
        elif c in {'n', 'ŋ'}:
            return 'n', True
        elif c == 'l':
            return 'l', False
        elif c == 'r' or c == 'ɹ':
            return 'l', False  # r/ɹ -> l in Illish
        elif c in 'ptkbdg':
            return '', False
        else:
            # Unknown consonant, treat as fricative
            return 's', False

    # Complex clusters
    nasals = set('mnŋ')
    plosives = set('ptkbdg')
    fricatives = {'s', 'z', 'ʃ', 'ʒ', 'θ', 'ð', 'ʂ', 'ʐ', 'h', 'f', 'v'}

    # Special case: nasal + consonant (e.g., 'ŋθ', 'nt', 'mp')
    # Distinguish: nasal + fricative (keep fricative) vs nasal + stop (keep nasal only)
    if len(coda) > 1 and coda[0] in nasals:
        # If followed by a fricative: keep the fricative, mark as nasalized
        if coda[-1] in fricatives:
            final_coda, _ = reduce_coda_to_illish(coda[-1], is_final)
            return final_coda, True
        else:
            # Otherwise (nasal + stop): keep nasal only, mark as nasalized
            nasal_coda, _ = reduce_coda_to_illish(coda[0], is_final)
            return nasal_coda, True

    # Default: keep first consonant only
    first_char = coda[0]
    return reduce_coda_to_illish(first_char, is_final)

def normalize_vowel(vowel_char):
    """Normalize IPA vowels to base orthographic vowel (a, e, i, o, u)"""
    normalize_map = {
        'ɑ': 'a', 'æ': 'a', 'ə': 'a', 'ʌ': 'u',
        'ɛ': 'e', 'ɪ': 'i', 'ɔ': 'o', 'ʊ': 'u',
        'ɒ': 'o', 'ɜ': 'e',
    }
    return normalize_map.get(vowel_char, vowel_char)

def apply_tone_letter(vowel_base, tone_name):
    """Apply tone letter (superscript) after vowel - returned separately"""
    tone_letter = TONE_LETTERS.get(tone_name, '')
    return vowel_base, tone_letter

def apply_nasalization(vowel_with_tone):
    """
    Add nasalization mark (combining tilde) to vowel
    Placed after the vowel but before tone letter
    """
    nasalization_mark = '\u0303'  # combining tilde
    # Insert nasalization mark after the vowel character (before tone letter)
    # Find where the tone letter is (if present)
    # Tone letters are: ˩ (U+02E9), ˥ (U+02E5), etc.
    tone_letters = {'˩', '˥', '˦', '˧', '˨'}

    # Find the vowel and insert nasalization after it
    if vowel_with_tone and vowel_with_tone[0] not in tone_letters:
        # First char is vowel, insert tilde after it
        return vowel_with_tone[0] + nasalization_mark + vowel_with_tone[1:]
    return vowel_with_tone

def english_ipa_to_illish(ipa_string):
    """
    Convert English IPA to Illish orthography

    Pipeline:
    1. Parse into syllables
    2. Apply onset rules (S-cluster collapse)
    3. Classify codas and assign tones
    4. Reduce codas to Illish inventory
    5. Apply tone letters and nasalization
    6. Handle rising tone word-final rule: tone² + ʔ + tone³
    """
    syllables = analyze_word(ipa_string)

    if not syllables:
        return ""

    result = []

    for idx, (onset, nucleus, coda) in enumerate(syllables):
        is_final = (idx == len(syllables) - 1)

        # Step 1: Onset rules
        onset = collapse_s_supercluster(onset)

        # Step 2: Coda classification and tone
        coda_type = classify_coda(coda)
        tone = assign_lexical_tone(coda_type, coda)

        # Step 3: Vowel length
        is_long = should_vowel_be_long(nucleus, coda)

        # Step 4: Reduce coda
        illish_coda, nasalized = reduce_coda_to_illish(coda, is_final)

        # Step 5: Build output
        # For diphthongs: use only the first vowel character
        # (e.g., "oʊ" → "o", "aɪ" → "a")
        vowel_chars = [c for c in nucleus if is_vowel(c)]
        if vowel_chars:
            vowel_base = vowel_chars[0]  # Take first vowel only
        else:
            vowel_base = nucleus.replace('ː', '')

        # Use original vowel, don't normalize
        vowel_base_out, tone_letter = apply_tone_letter(vowel_base, tone)

        if nasalized:
            vowel_base_out = apply_nasalization(vowel_base_out)

        if is_long and 'ː' not in vowel_base_out:
            vowel_base_out += 'ː'

        # Build syllable: onset + vowel + tone letter + coda
        syllable = onset + vowel_base_out + tone_letter + illish_coda
        result.append(syllable)

        # Step 6: Handle rising tone at word end
        # If this is the final syllable and tone is rising:
        # Add: ʔ + original_vowel + high tone letter
        if is_final and tone == 'rising':
            glottal_stop = 'ʔ'
            # For diphthongs, use only first vowel character
            vowel_for_glottal = vowel_base  # Already extracted first vowel character in step 5
            vowel_out, high_tone_letter = apply_tone_letter(vowel_for_glottal, 'high')
            result.append(glottal_stop + vowel_out + high_tone_letter)

    return ''.join(result)


# Test cases
if __name__ == '__main__':
    test_cases = [
        ('kæt', 'kæ˩'),                     # cat: voiceless t -> short vowel + low tone
        ('bæʃ', 'bæ˥s'),                    # bash: voiceless ʃ -> short vowel + high tone + s
        ('bæn', 'bæ̃˥n'),                    # ban: nasal coda alone -> short vowel + nasalization + high tone
        ('/kæt/', 'kæ˩'),                   # cat: slashes stripped
        ('sliːp', 'sli˩'),                  # sleep: voiceless p -> short vowel (strip ː from iː) + low tone
        ('ɪŋ', 'ɪ̃˥n'),                      # -ing: nasal coda alone -> short vowel + nasalization + high tone
        ('kɪl', 'kɪ˥l'),                    # kill: liquid coda alone -> short vowel + high tone
        ('kɛpt', 'kɛ˩˥ʔɛ˥'),                # kept: plosive cluster pt -> rising tone + glottal stop
        ('stɹɛŋθ', 'tɬɛ̃˩s'),               # strength: str collapse + nasal+stop=low tone + θ->s (word-final)
        ('ænt', 'æ̃˩n'),                     # ant: nasal+stop=low tone + nt->n coda
        ('strɔŋ', 'tɬɔ̃˥n'),                # strong: str collapse + nasal alone=high tone + short vowel
        ('bɑθ', 'bɑ˥s'),                    # bath: fricative at word end -> s
        ('kæf', 'kæ˥f'),                    # calf: f stays as f (f is exception to fricative rule)
        ('ɪkˈsploʊd', 'ɪ˥˩tɬoː˩'),         # explode: ik (k=stop,low tone) + ploud (spl→tɬ, oʊ=long, d=voiced,low)
    ]

    print("IPA to Illish Conversion Tests")
    print("=" * 70)

    for ipa_input, expected in test_cases:
        result = english_ipa_to_illish(ipa_input)
        status = "OK" if result == expected else "DIFF"
        print(f"{status:4} {ipa_input:15} -> {result:20} (expected: {expected})")
