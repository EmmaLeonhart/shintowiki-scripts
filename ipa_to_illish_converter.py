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
VOICED_OBSTRUENTS = set('bvdðgzʒ')  # dʒ handled separately

def is_vowel(char):
    """Check if character is a vowel"""
    return char in VOWELS

def analyze_word(ipa_str):
    """
    Parse IPA string into syllables
    Returns: list of (onset, vowel, coda) tuples
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

        # Collect nucleus (vowel + optional length mark)
        if i < len(ipa) and is_vowel(ipa[i]):
            nucleus += ipa[i]
            i += 1
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
    Handle S + plosive + liquid clusters -> tɬ
    Only collapse complete supercluster patterns
    """
    patterns = [
        ('str', 'tɬ'), ('spr', 'tɬ'), ('spl', 'tɬ'), ('skr', 'tɬ')
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

def assign_lexical_tone(coda_type):
    """Assign lexical tone based on coda"""
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
    """Determine if vowel should be long (from voiced obstruent in coda)"""
    has_length = 'ː' in nucleus

    if coda:
        # Check for voiced obstruents
        if len(coda) >= 2 and coda[-2:] == 'dʒ':
            return True
        if coda[-1] in VOICED_OBSTRUENTS:
            return True

    return has_length

def reduce_coda_to_illish(coda):
    """
    Reduce English coda to Illish inventory (s, f, m, n, l, Ø)
    Returns: (illish_coda, is_nasalized)
    """
    if not coda:
        return '', False

    # Handle affricates
    if coda in {'tʃ', 'dʒ'}:
        return 's', False

    # Single consonants
    if len(coda) == 1:
        c = coda[0]
        if c in {'s', 'z', 'ʃ', 'ʒ', 'θ', 'ð', 'ʂ', 'ʐ', 'h'}:
            return 's', False
        elif c in {'f', 'v'}:
            return 'f', False
        elif c == 'm':
            return 'm', True
        elif c in {'n', 'ŋ'}:
            return 'n', True
        elif c == 'l':
            return 'l', False
        elif c == 'r':
            return 'l', False  # r -> l in Illish
        elif c in 'ptkbdg':
            return '', False

    # Complex clusters: remove plosives and recurse
    non_plosives = [c for c in coda if c not in 'ptkbdg']
    if non_plosives:
        return reduce_coda_to_illish(''.join(non_plosives))

    return '', False

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
    Mark vowel as nasalized in phonological processing
    Note: We don't add a visible diacritic; nasalization is implied by the nasal coda (n/m)
    """
    # Currently just a placeholder - nasalization is phonetic, not orthographic
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
        tone = assign_lexical_tone(coda_type)

        # Step 3: Vowel length
        is_long = should_vowel_be_long(nucleus, coda)

        # Step 4: Reduce coda
        illish_coda, nasalized = reduce_coda_to_illish(coda)

        # Step 5: Build output
        vowel_base = nucleus.replace('ː', '')
        vowel_norm = normalize_vowel(vowel_base)
        vowel_base_out, tone_letter = apply_tone_letter(vowel_norm, tone)

        if nasalized:
            vowel_base_out = apply_nasalization(vowel_base_out)

        if is_long and 'ː' not in vowel_base_out:
            vowel_base_out += 'ː'

        # Build syllable: onset + vowel + coda + tone letter
        syllable = onset + vowel_base_out + illish_coda + tone_letter
        result.append(syllable)

        # Step 6: Handle rising tone at word end
        # If this is the final syllable and tone is rising:
        # Add: ʔ + vowel_norm + high tone letter
        if is_final and tone == 'rising':
            glottal_stop = 'ʔ'
            vowel_out, high_tone_letter = apply_tone_letter(vowel_norm, 'high')
            result.append(glottal_stop + vowel_out + high_tone_letter)

    return ''.join(result)


# Test cases
if __name__ == '__main__':
    test_cases = [
        ('kæt', 'ka˩'),                     # cat: plosive -> low tone
        ('bæʃ', 'bas˥'),                    # bash: fricative -> high tone + s
        ('bæn', 'ban˥'),                    # ban: nasal -> high tone + n coda
        ('/kæt/', 'ka˩'),                   # cat: slashes stripped
        ('sliːp', 'sliː˩'),                 # sleep: sl onset + i long + p plosive coda -> low tone
        ('ɪŋ', 'in˥'),                      # -ing: nasal -> high tone + n coda
        ('dʒʌs', 'dʒus˥'),                  # judge: dʒ onset + u vowel + s coda -> high + s
        ('kɛpt', 'ke˩˥ʔe˥'),                # kept: plosive cluster pt -> rising tone + glottal stop rule
    ]

    print("IPA to Illish Conversion Tests")
    print("=" * 70)

    for ipa_input, expected in test_cases:
        result = english_ipa_to_illish(ipa_input)
        status = "OK" if result == expected else "DIFF"
        print(f"{status:4} {ipa_input:15} -> {result:20} (expected: {expected})")
