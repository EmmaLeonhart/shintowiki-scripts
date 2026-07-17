"""
Generate GitHub Pages HTML for all QuickStatements languages.
Run from the repo root: python docs/generate_pages.py
Also called by the GitHub Actions regenerate workflow.
"""

import os
import html
import re
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR  = os.path.join(REPO_ROOT, "docs")
QS_DIR    = os.path.join(REPO_ROOT, "quickstatements")

# (code, english name, native name, flag, methodology HTML)
LANGS = [
    ("tok", "Toki Pona", "Toki Pona", "🌍", """\
      <p>Fetches shrines and temples from Wikidata via SPARQL that have Indonesian labels
      but no Toki Pona label. The Indonesian label ("Kuil X" or "Kuil Agung X") is used
      to extract the proper name, which is then passed through a custom phonological mapper:</p>
      <ul>
        <li>Voiced consonants devoiced: g→k, z→s, d→t, b→p</li>
        <li>Initial H→K, medial H→P</li>
        <li>Long vowels collapsed to short; r→l; chi→si; tsu→tu</li>
        <li>The mora <em>zu</em> is ambiguous (す or づ) — both <em>su</em> and <em>tu</em> variants are emitted</li>
      </ul>
      <p>The label is prefixed with <strong>tomo sewi</strong> (shrine) or
      <strong>tomo sewi suli</strong> (grand shrine / Kuil Agung).</p>"""),

    ("ko", "Korean", "한국어", "🇰🇷", """\
      <p>Two paths depending on the shrine's country:</p>
      <ul>
        <li><strong>Japanese shrines:</strong> Indonesian label → strip prefix →
        <code>koreanize()</code> (maps Hepburn romanization to Hangul, preserving
        voiced/unvoiced distinctions; ん→ㄴ batchim) → append Korean suffix:
        신사 (jinja), 신궁 (jingū), 사원 (temple), 대사원 (grand temple).</li>
        <li><strong>Non-Japanese shrines:</strong> Japanese Kanji label →
        <code>hanja.translate()</code> for the sino-Korean reading.</li>
      </ul>"""),

    ("zh", "Chinese", "中文", "🇨🇳", """\
      <p>Takes the Japanese Kanji label and applies two transformations:</p>
      <ol>
        <li>Kana characters are replaced with man'yōgana-style Chinese equivalents
        (e.g. の→之, ヶ→个, ノ→乃).</li>
        <li>The result is passed through OpenCC's <strong>t2s</strong> converter to
        convert Japanese shinjitai (新字体) to simplified Chinese characters.</li>
      </ol>
      <p>Pure Kanji labels pass through with only the shinjitai→simplified step.</p>"""),

    ("hi", "Hindi", "हिन्दी", "🇮🇳", """\
      <p>Fetches shrines missing a Hindi label. The extracted name is transliterated
      from romanized Japanese to Devanagari script using a syllable-based mapping:</p>
      <ul>
        <li>Vowels at word-start use independent Devanagari vowel letters:
        <em>a</em> → अ, <em>i</em> → इ, <em>u</em> → उ, <em>e</em> → ए, <em>o</em> → ओ</li>
        <li>Consonant syllables use inherent-vowel notation: <em>ka</em> → क, <em>ki</em> → कि,
        <em>ku</em> → कु, <em>ke</em> → के, <em>ko</em> → को</li>
        <li>Sibilants and affricates: <em>shi</em> → शि (श), <em>chi</em> → चि (च),
        <em>tsu</em> → त्सु, <em>fu</em> → फ़ु</li>
        <li>Voiced stops preserved: <em>ga</em> → ग, <em>ba</em> → ब, <em>da</em> → द</li>
        <li>Yōon syllables use consonant clusters: <em>kya</em> → क्य, <em>sha</em> → श,
        <em>ryu</em> → र्यु</li>
        <li>Moraic nasal ん → न</li>
      </ul>
      <p>Appended with <strong>मंदिर</strong> (shrine/temple) or
      <strong>महा मंदिर</strong> (grand shrine) for Kuil Agung.</p>
      <p>Example: <em>Kuil Ise</em> → <em>इसे मंदिर</em></p>"""),

    ("de", "German", "Deutsch", "🇩🇪", """\
      <p>Fetches shrines missing a German label. Extracts the proper name
      from the Indonesian label (stripping "Kuil" / "Kuil Agung" prefix) and appends
      <strong>Schrein</strong> (shrine) or <strong>Tempel</strong> (temple).</p>"""),

    ("fr", "French", "Français", "🇫🇷", """\
      <p>Fetches shrines missing a French label. Prepends 
      <strong>Sanctuaire</strong> (shrine) or <strong>Temple</strong> (temple) to the name.</p>"""),

    ("pt", "Portuguese", "Português", "🇵🇹", """\
      <p>Fetches shrines missing a Portuguese label. Prepends 
      <strong>Santuário</strong> (shrine) or <strong>Templo</strong> (temple) to the name.</p>"""),

    ("nl", "Dutch", "Nederlands", "🇳🇱", """\
      <p>Fetches shrines missing a Dutch label. Extracts the name from the Indonesian
      label and appends <strong>-shrijn</strong> (shrine) or <strong>tempel</strong> (temple).</p>"""),

    ("es", "Spanish", "Español", "🇪🇸", """\
      <p>Fetches shrines missing a Spanish label. Prepends
      <strong>Santuario</strong> (shrine) or <strong>Templo</strong> (temple) to the name.</p>"""),

    ("it", "Italian", "Italiano", "🇮🇹", """\
      <p>Fetches shrines missing an Italian label. Prepends
      <strong>Santuario</strong> (shrine) or <strong>Tempio</strong> (temple) to the name.</p>"""),

    ("tr", "Turkish", "Türkçe", "🇹🇷", """\
      <p>Fetches shrines missing a Turkish label. Appends
      <strong>Tapınağı</strong> (shrine/temple) to the extracted name.</p>"""),

    ("ru", "Russian", "Русский", "🇷🇺", """\
      <p>Fetches shrines missing a Russian label. The extracted name is transliterated
      to Cyrillic using the <strong>Polivanov system</strong>. The final word
      is declined into the genitive case. Prefixed with <strong>Храм</strong> (temple/shrine).</p>"""),

    ("uk", "Ukrainian", "Українська", "🇺🇦", """\
      <p>Fetches shrines missing a Ukrainian label. Uses the same Polivanov-based
      Cyrillic transliteration as Russian, with Ukrainian-specific substitutions.
      Prefixed with <strong>Святилище</strong> (shrine) or <strong>Храм</strong> (temple).</p>"""),

    ("lt", "Lithuanian", "Lietuvių", "🇱🇹", """\
      <p>Fetches shrines missing a Lithuanian label. The name undergoes phonological
      adaptation (ch→č, sh→š, w→v) and the final word is declined into the genitive
      case using Lithuanian vowel-ending rules. The word <strong>maldykla</strong>
      (shrine) or <strong>šventykla</strong> (temple) is appended.</p>"""),

    ("eu", "Basque", "Euskara", "🏔️", """\
      <p>Fetches shrines missing a Basque label. Appends
      <strong>santutegia</strong> (shrine) or <strong>tenplua</strong> (temple).
      Grand shrines use <strong>handia</strong> (e.g. santutegi handia).</p>"""),

    ("fa", "Farsi", "فارسی", "🇮🇷", """\
      <p>Fetches shrines missing a Farsi label. The extracted name is transliterated
      from romanized Japanese to Perso-Arabic script using a syllable-based mapping.</p>"""),

    ("ar", "Arabic (MSA)", "العربية", "🇸🇦", """\
      <p>Fetches shrines missing an Arabic (MSA) label. The extracted name is transliterated
      from romanized Japanese to Arabic script using a syllable-based mapping.</p>"""),

    ("arz", "Egyptian Arabic", "مصري", "🇪🇬", """\
      <p>Identical to the MSA Arabic pipeline with one phonological difference:
      in Egyptian Arabic, Japanese <em>g</em> maps to <strong>ج</strong>.</p>"""),

    ("id_proposed", "Indonesian (Proposed)", "Bahasa Indonesia", "🇮🇩", """\
      <p>Proposed Indonesian labels for Japanese-only shrines. Generated from
      Japanese Kanji/Kana using <code>pykakasi</code> for Romaji conversion.</p>"""),

    # Cross-category label sets — one file spanning ALL covered languages
    # (not per-language). Same QuickStatements format, so they render here too.
    ("shikinaisha_lists", "Shikinaisha lists (all langs)", "式内社一覧", "📜", """\
      <p>Labels for the <strong>Engishiki Jinmyōchō</strong> (延喜式神名帳) and its 69
      per-province "List of Shikinaisha" items, in 58 languages in one file. The
      "{list-word} Shikinaisha in {province}" frame is authored per language; the
      province name is transliterated (Latin keeps romaji), CJK from the kanji.</p>"""),

    ("kami_labels", "Kami / deities (all langs)", "神", "⛩️", """\
      <p>Multi-language labels for <strong>kami</strong> (Shinto deities;
      <code>P31/P279* Q524158</code>). Bare-name transliteration via
      <code>translit_common</code> — romaji → each script, CJK from the kanji, Korean
      phonetic. English-gloss labels (no romaji reading) get CJK only, never a
      phonetically-mangled transliteration.</p>"""),

    ("honorific_labels", "Shinto honorifics (all langs)", "神号", "🎌", """\
      <p>Multi-language labels for <strong>Shinto honorifics</strong>
      (<code>P31 Q137169543</code>) — the suffixes attached to kami names
      (大神 Ōkami, 大御神 Ōmikami, の命 no Mikoto, 権現 Gongen, 明神 Myōjin,
      大明神 Daimyōjin, 大仏 Daibutsu, さま sama, 姫 -hime, 彦 -hiko). Same
      bare-name transliteration as the kami pipeline via
      <code>translit_common</code>. Read live from the honorific class, so a new
      honorific item is picked up with no code change. No <code>mul</code>.</p>"""),

    ("shrine_rank_labels", "Shrine ranks (all langs)", "社格", "🏵️", """\
      <p>Labels for the <strong>shrine ranks</strong> (社格) — Kanpei Taisha, Ichinomiya,
      Myōjin Taisha, … (<code>P31 Q10444029</code>). Bare-term transliteration; Korean
      uses the sino-Korean (hanja) reading since ranks are Sino-Japanese compounds.</p>"""),

    ("province_labels", "Provinces of Japan (all langs)", "令制国", "🗾", """\
      <p>Labels for the old <strong>provinces of Japan</strong> (令制国;
      <code>P31 Q860290</code>). A per-language "{X} Province" frame paired with the
      shared name transliteration; CJK from the kanji (which carries 国).</p>"""),
]

PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{english} QuickStatements — Shrine Labels</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
      background: #0f1117; color: #e2e8f0;
      min-height: 100vh; padding: 2rem 1.5rem;
    }}
    .container {{ max-width: 860px; margin: 0 auto; }}
    .breadcrumb {{ font-size: 0.8rem; color: #475569; margin-bottom: 1.25rem; }}
    .breadcrumb a {{ color: #6366f1; text-decoration: none; }}
    .breadcrumb a:hover {{ text-decoration: underline; }}
    h1 {{ font-size: 1.4rem; color: #a5b4fc; margin-bottom: 0.3rem; }}
    .meta {{ font-size: 0.82rem; color: #475569; margin-bottom: 1.25rem; }}
    .copy-bar {{
      display: flex; align-items: center; gap: 1rem; margin-bottom: 0.6rem;
    }}
    .copy-btn {{
      background: #4f46e5; border: none; color: #fff; border-radius: 6px;
      padding: 0.45rem 1.2rem; font-size: 0.85rem; cursor: pointer;
      transition: background 0.15s;
    }}
    .copy-btn:hover {{ background: #4338ca; }}
    .copy-btn.copied {{ background: #16a34a; }}
    .qs-link {{ font-size: 0.82rem; color: #475569; text-decoration: none; }}
    .qs-link:hover {{ color: #a5b4fc; }}
    textarea {{
      width: 100%; height: 560px;
      background: #0a0c14; border: 1px solid #1e2130; border-radius: 8px;
      color: #cbd5e1;
      font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
      font-size: 0.72rem; line-height: 1.55; padding: 0.75rem;
      resize: vertical; outline: none; margin-bottom: 1.5rem;
    }}
    textarea:focus {{ border-color: #4f46e5; }}
    details {{
      background: #13151f; border: 1px solid #1e2130; border-radius: 8px;
      padding: 0.9rem 1.1rem;
    }}
    summary {{
      font-size: 0.85rem; color: #c4b5fd; cursor: pointer;
      font-weight: 600; user-select: none;
    }}
    summary:hover {{ color: #a5b4fc; }}
    .method-body {{
      margin-top: 0.85rem;
      font-size: 0.83rem; color: #94a3b8; line-height: 1.7;
    }}
    .method-body p {{ margin-bottom: 0.6rem; }}
    .method-body ul, .method-body ol {{
      padding-left: 1.4rem; margin-bottom: 0.6rem;
    }}
    .method-body li {{ margin-bottom: 0.25rem; }}
    .method-body code {{
      background: #1e2130; border-radius: 3px; padding: 0.1rem 0.35rem;
      font-family: monospace; font-size: 0.9em; color: #a5b4fc;
    }}
    .method-body strong {{ color: #c4b5fd; }}
    .method-body em {{ color: #94a3b8; }}
  </style>
</head>
<body>
<div class="container">
  <p class="breadcrumb"><a href="index.html">&larr; All languages</a></p>
  <h1>{flag} {english} ({native})</h1>
  <p class="meta">
    Wikidata QuickStatements &mdash; language code
    <code style="background:#1e2130;border-radius:3px;padding:0.1rem 0.35rem;font-size:0.9em;color:#a5b4fc">{code}</code>
    &mdash; {count} statements
  </p>

  <div class="copy-bar">
    <button class="copy-btn" id="copy-btn" onclick="copyAll()">Copy all</button>
    <a class="qs-link" href="https://quickstatements.toolforge.org/#/batch"
       target="_blank" rel="noopener">Open QuickStatements ↗</a>
  </div>

  <textarea id="ta" spellcheck="false" autocorrect="off" autocomplete="off"{rtl_attr}>{content}</textarea>

  <details>
    <summary>How this was generated</summary>
    <div class="method-body">
      {methodology}
    </div>
  </details>
</div>
<script>
  function copyAll() {{
    const ta  = document.getElementById('ta');
    const btn = document.getElementById('copy-btn');
    navigator.clipboard.writeText(ta.value).then(() => {{
      btn.textContent = 'Copied!';
      btn.classList.add('copied');
      setTimeout(() => {{ btn.textContent = 'Copy all'; btn.classList.remove('copied'); }}, 1800);
    }});
  }}
</script>
</body>
</html>
"""

RTL_LANGS = {"fa", "ar", "arz", "he", "ur"}

def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Update index.html date
    index_path = os.path.join(DOCS_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"last pipeline run \d{4}-\d{2}-\d{2}", f"last pipeline run {today}", content)
        with open(index_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"  Updated date in {index_path} to {today}")

    for code, english, native, flag, methodology in LANGS:
        txt_path = os.path.join(QS_DIR, code + ".txt")
        if not os.path.exists(txt_path):
            print(f"  Warning: {txt_path} not found, skipping.")
            continue
            
        raw = open(txt_path, encoding="utf-8").read()
        # Count only non-empty lines that don't start with #
        count = len([l for l in raw.splitlines() if l.strip() and not l.strip().startswith("#")])
        escaped = html.escape(raw)

        rtl_attr = ' dir="rtl"' if code in RTL_LANGS else ""
        out = PAGE_TEMPLATE.format(
            code=code.split("_")[0],
            english=english,
            native=native,
            flag=flag,
            count=f"{count:,}",
            content=escaped,
            methodology=methodology,
            rtl_attr=rtl_attr,
        )
        out_path = os.path.join(DOCS_DIR, code + ".html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)
        size_kb = os.path.getsize(out_path) // 1024
        print(f"  {code}.html — {count:,} statements, {size_kb} KB")

    print("Done.")

if __name__ == "__main__":
    main()
