"""
Add {{moved to|PAGE}} and {{moved from|PAGE}} templates to pages
based on the move log from shinto.miraheze.org.

For each move (OLD → NEW):
  - OLD page gets {{moved to|NEW}}
  - NEW page gets {{moved from|OLD}}
"""

import mwclient
import time
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
WIKI_URL = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'
SLEEP = 1.5

# All moves: (old_title, new_title)
MOVES = [
    ("Template:The 17 Generations of Deities", "Template/The 17 Generations of Deities"),
    ("User:Immanuelle/Kunishirotomi Kami", "User:Immanuelle/Kuninotoshimi-no-Kami"),
    ("User:Immanuelle/Hinaterunakatanomichioikochini Kami", "User:Immanuelle/Hinateri-Nukada-Bichio-Ikochini-no-Kami"),
    ("User:Immanuelle/Torinarumi Kami", "User:Immanuelle/Torinarumi-no-Kami"),
    ("User:Immanuelle/Nunototomi Torinarumi Kami", "User:Immanuelle/Nunototomi Torinarumi-no-Kami"),
    ("Inashironimasu Shrine", "Inashiro-ni-masu Shrine"),
    ("Prince Ameoshitarashi", "Prince Ametarashihiko"),
    ("Isonokamifutsumitama Shrine", "Isonokami Futsumitama Shrine"),
    ("Sugata Shrine (Q134888232)", "Sugata Shrine (Yamatokōriyama)"),
    ("Shirakunino Shrine", "Shirakuni Shrine"),
    ("Mononobe Shrine (Q18235752)", "Mononobe Shrine (Higashi-ku, Nagoya)"),
    ("Mononobe Shrine (Q11570699)", "Mononobe Shrine (Oda)"),
    ("Mononobe Shrine", "Mononobe Shrine (Kashiwazaki)"),
    ("Yuge Shrine (Q11487078)", "Yuge Shrine (Takashima)"),
    ("Mefu Shrine (Q3304192)", "Mefu Shrine (Takarazuka)"),
    ("Hitsujisaki Shrine (Q11660145)", "Hitsujisaki Shrine (Mano, Ishinomaki)"),
    ("Soganimasu Sogatsuhiko Shrine", "Soga-ni-masu Sogatsuhiko Shrine"),
    ("Keta Jinja", "Keta Shrine"),
    ("Ozu Shrine (Q97206855)", "Ozu Shrine (Moriyama)"),
    ("Kashima Shrine (Q135069030)", "Kashima Shrine (Kashiba City)"),
    ("Kataoka Shrine (Q43594918)", "Kataoka Shrine (Oji Town)"),
    ("Unkanjiniimasunaramoto Shrine", "Unkanji-niimasu Naramoto Shrine"),
    ("Izumi Shrine (Q11395685)", "Izumi Shrine (Kaga)"),
    ("Izumi Shrine (Q11554897)", "Izumi Shrine (Hitachi)"),
    ("Ushihiko Shrine (Q48758332)", "Ushihiko Shrine"),
    ("Ushihiko Shrine", "Ushihiko Shrine (Q135041302)"),
    ("Okuni Shrine (Q17221549)", "Okuni Shrine (Isesaki)"),
    ("Ōkunitama Shrine (Q11433670)", "Ōkunitama Shrine (Iwaki)"),
    ("Omiya Shrine (Q113679907)", "Omiya Shrine (Izu)"),
    ("Okada Shrine (Q106852596)", "Okada Shrine (Matsumoto)"),
    ("Okanoue Shrine (Q48758325)", "Okanoue Shrine"),
    ("Talk:Okanoue Shrine", "Talk:Okanoue Shrine (disambiguation)"),
    ("Okanoue Shrine", "Okanoue Shrine (disambiguation)"),
    ("Ogawa Shrine (Q135194226)", "Ogawa Shrine"),
    ("Ozu Shrine", "Ozu Shrine (Kuwana)"),
    ("Ono Shrine (Q11464225)", "Ono Shrine (Shiga)"),
    ("Ono Shrine (Q17225921)", "Ono Shrine (Atsugi)"),
    ("Ono Shrine (Q11464226)", "Ono Shrine (Fuchū)"),
    ("Kashima Miko Shrine (Q11677124)", "Kashima Miko Shrine"),
    ("Kashima Miko Shrine", "Kashima Miko Shrine (Ishinomaki)"),
    ("Kamo Shrine (Q11634949)", "Kamo Shrine (Ichinomiya)"),
    ("Kamo Shrine (Q106301088)", "Kamo Shrine (Saitama)"),
    ("Kamo Shrine (Q11675602)", "Kamo Shrine (Kawanishi)"),
    ("Kamo Shrine (Q54153261)", "Kamo Shrine (Kuroshio)"),
    ("Kamo Shrine (Q11634952)", "Kamo Shrine (Kiryu)"),
    ("Inbe Shrine (Q11490722)", "Inbe Shrine"),
    ("Inbe Shrine", "Inbe Shrine (Yoshinogawa)"),
    ("Oono Shrine (Q11439718)", "Ono Shrine (Ichinomiya)"),
    ("Oosakayamaguchi Shrine", "Ōsaka Yamaguchi Shrine (Anamushi)"),
    ("Ōsaka Yamaguchi Shrine", "Ōsaka Yamaguchi Shrine (Kashiba)"),
    ("Oosakayamaguchi Shrine (Q135069036)", "Ōsaka Yamaguchi Shrine"),
    ("Takumiya Shrine", "Enomiya Shrine"),
    ("Igatomega Shrine", "Ikaruga Shrine (Hatsu, Yokkaichi City)"),
    ("Ena Shrine (Q11492453)", "Ena Shrine (Nakatsugawa)"),
    ("Ikuta Shrine (Q710086)", "Ikuta Shrine"),
    ("Talk:Ikuta Shrine", "Talk:Ikuta Shrine (Q135187148)"),
    ("Ikuta Shrine", "Ikuta Shrine (Q135187148)"),
    ("Ikeda Shrine (Q134926975)", "Ikeda Shrine (Shizuoka)"),
    ("Oi Shrine (Q11493043)", "Oi Shrine (Tottori)"),
    ("Uwato Shrine (Q17217996)", "Uwato Shrine (Gōdo-chō)"),
    ("Amanoiwatate Shrine", "Ama-no-Iwatate Shrine"),
    ("Amasashihikonomikoto Shrine", "Amasashihiko-no-Mikoto Shrine"),
    ("Azusawakenomikoto Shrine", "Azusawake-no-Mikoto Shrine"),
    ("Ōshima Shrine, Okitsushima Shrine", "Ōshima & Okitsushima Shrine"),
    ("Izanagi Shrine (Q11379324)", "Izanagi Shrine (Yamadahigashi, Suita)"),
    ("Izanagi Shrine (Q11379365)", "Izanagi Shrine (Ikoma)"),
    ("Izanagi Shrine (Q11379322)", "Izanagi Shrine (Saidera, Suita)"),
    ("Asakura Shrine (Q17191190)", "Asakura Shrine (Wakayama)"),
    ("Asakura Shrine (Q11510876)", "Asakura Shrine (Uji, Kyoto)"),
    ("Inaba Shrine (Q701414)", "Inaba Shrine"),
    ("Inaba Shrine", "Inaba Shrine (Q135186443)"),
    ("Tatsumi Shrine Osaka", "Tatsumi Shrine (Osaka)"),
    ("Tawa Shrine (Q11430645)", "Tawa Shrine (Sanuki)"),
    ("Category:Merged Shikinaisha autogenerations", "Category:Shikinaisha merges"),
    ("Amefutotama-no-Mikoto Shrine", "Ame-Futotama-no-Mikoto Shrine"),
    ("Manguu Shrine", "Mangū Shrine"),
    ("Amenotoyotarashikarahimenomikoto Shrine", "Ame-no-Toyotarashikara-hime-no-mikoto Shrine"),
    ("Nyūkawa Shrine (Uchi district)", "Nyūkawa Shrine"),
    ("Nyuukawa Shrine (Uchi district)", "Nyūkawa Shrine (Uchi district)"),
    ("Komagataooshige Shrine", "Komagata-Ōshige Shrine"),
    ("Kokuwakura Shrine Haiden", "Kokuwakura Shrine"),
    ("Nagakura Shrine Haiden", "Nagakura Shrine (Nishigō-mura)"),
    ("Ami Shrine (Q17191824)", "Ami Shrine (Nakagō)"),
    ("Amatsu Shrine (Q172253)", "Amatsu Shrine"),
    ("Amatsu Shrine", "Amatsu Shrine (Q135197898)"),
    ("Moritano Shrine (Q11450096)", "Moritano Shrine (Minochi)"),
    ("Yagi Shrine (Q11666826)", "Yagi Shrine (Ikeda)"),
    ("Matsuo Shrine (Q11529679)", "Matsuo Shrine (Kameoka)"),
    ("Kattamine Shrine (Q65249271)", "Kattamine Shrine (Katta-dake)"),
    ("Kataoka Shrine (Q28682738)", "Kataoka Shrine (Yoshida)"),
    ("Tennougu Ootoshi Shrine", "Tennōgū Ōtoshi Shrine"),
    ("Suwa Shrine (Q135070129)", "Suwa Shrine (Izumo)"),
    ("Hikawami Shrine", "Mii Shrine (Hikawa, Shimane)"),
    ("Mii Shrine (Q11488771)", "Mii Shrine (Kakamigahara)"),
    ("Takase Shrine (Q3791906)", "Takase Shrine (Nanto)"),
    ("Taka Shrine (Q11430895)", "Taka Shrine (Minamisōma)"),
    ("Taga Shrine (Q11431090)", "Taga Shrine (Tagajō)"),
    ("Taki Shrine (Q11430618)", "Taki Shrine (Imabari)"),
    ("Talk:Kawadayama 12-gō Kofun", "Talk:Kōdayama Kofun Cluster"),
    ("Kawadayama 12-gō Kofun", "Kōdayama Kofun Cluster"),
    ("Arakashi Shrine (Q11618763)", "Arakashi Shrine"),
    ("Arakashi Shrine", "Arakashi Shrine (Q135039974)"),
    ("Iwashizu Shrine (Q11379248)", "Iwashizu Shrine"),
    ("Iwashizu Shrine", "Iwashizu Shrine (Q135185797)"),
    ("Imaki-Aosaka-Inami-Ikegami Shrine (Q72728268)", "Imaki-Aosaka-Inami-Ikegami Shrine (Kamikawa, Saitama)"),
    ("Yatsurugi Shrine (Q124496744)", "Yatsurugi Shrine (Yagami, Kuwabara-cho, Hashima City)"),
    ("Kawara Shrine (Naiku)", "Kawara Shrine (Owari)"),
    ("Kawara Shrine (Q17209206)", "Kawara Shrine (Naiku)"),
    ("Kawara Shrine (Owari)", "Kawahara Shrine"),
    ("Kasuga Shrine (Q11513674)", "Kasuga Shrine (Shimizu, Ibaraki, Osaka)"),
    ("Ikenimasu-asagirikihatahime Shrine", "Ikenimasu Asagiri Kihatahime Shrine"),
    ("Shirahige Shrine (Q124668655)", "Shirahige Shrine (Kakamigahara)"),
    ("Asori Shrine (Nakami, Meiwa Town)", "Ōmi Shrine (Nakami, Meiwa Town)"),
    ("Aguasa Shrine", "Aguma Shrine"),
    ("Achi Shrine (Q11657447)", "Achi Shrine (Achi Village)"),
    ("Tenkei Okyōsho", "Tenkei Mikyōsho"),
]


def has_template(text, template_name, page_arg):
    """Check if the template already exists in the text."""
    # Check for {{moved to|PAGE}} or {{moved from|PAGE}}
    # Case-insensitive check for the template name
    lower = text.lower()
    pattern1 = "{{" + template_name.lower() + "|" + page_arg.lower() + "}}"
    pattern2 = "{{" + template_name.lower() + " |" + page_arg.lower() + "}}"
    pattern3 = "{{" + template_name.lower() + "| " + page_arg.lower() + "}}"
    return pattern1 in lower or pattern2 in lower or pattern3 in lower


def add_template_to_page(site, title, template_text, summary):
    """Add a template to a page. Prepends for content pages, appends for redirects."""
    page = site.pages[title]
    if not page.exists:
        print(f"  SKIP (page does not exist): {title}")
        return False

    text = page.text()
    if text is None:
        text = ""

    # Check if template already there
    if template_text.lower() in text.lower():
        print(f"  SKIP (template already exists): {title}")
        return False

    # For redirects, append after the redirect line
    stripped = text.strip()
    if stripped.upper().startswith("#REDIRECT"):
        new_text = text.rstrip() + "\n" + template_text + "\n"
    else:
        # For content pages, prepend at the top
        new_text = template_text + "\n" + text

    page.save(new_text, summary=summary)
    print(f"  DONE: {title}")
    return True


def main():
    # Connect
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent='ShintoWikiBot/1.0 (immanuelle@shinto.miraheze.org)')
    site.login(USERNAME, PASSWORD)
    print(f"Logged in to {WIKI_URL}")

    # Collect all operations: { page_title: [template_strings] }
    # Process them to avoid duplicate edits to the same page
    operations = {}  # title -> list of (template_text, summary)

    for old_title, new_title in MOVES:
        # Source page gets {{moved to|new_title}}
        moved_to = "{{moved to|" + new_title + "}}"
        key_old = old_title
        if key_old not in operations:
            operations[key_old] = []
        operations[key_old].append((moved_to, f"Bot: Adding moved to template → [[{new_title}]]"))

        # Destination page gets {{moved from|old_title}}
        moved_from = "{{moved from|" + old_title + "}}"
        key_new = new_title
        if key_new not in operations:
            operations[key_new] = []
        operations[key_new].append((moved_from, f"Bot: Adding moved from template ← [[{old_title}]]"))

    # Now process all pages, combining multiple templates into one edit
    total = len(operations)
    done = 0
    skipped = 0
    errors = 0

    for i, (title, templates) in enumerate(operations.items(), 1):
        print(f"\n[{i}/{total}] Processing: {title}")
        page = site.pages[title]
        if not page.exists:
            print(f"  SKIP (page does not exist)")
            skipped += 1
            continue

        text = page.text()
        if text is None:
            text = ""

        # Filter out templates already present
        new_templates = []
        for tmpl_text, summary in templates:
            if tmpl_text.lower() in text.lower():
                print(f"  SKIP (already has): {tmpl_text}")
            else:
                new_templates.append(tmpl_text)

        if not new_templates:
            print(f"  SKIP (all templates already present)")
            skipped += 1
            continue

        # Build new text
        templates_block = "\n".join(new_templates)
        stripped = text.strip()
        if stripped.upper().startswith("#REDIRECT"):
            new_text = text.rstrip() + "\n" + templates_block + "\n"
        else:
            new_text = templates_block + "\n" + text

        # Build summary
        summary = "Bot: Adding move templates (" + ", ".join(new_templates) + ")"
        if len(summary) > 200:
            summary = f"Bot: Adding {len(new_templates)} move template(s)"

        try:
            page.save(new_text, summary=summary)
            print(f"  SAVED: Added {len(new_templates)} template(s)")
            done += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

        time.sleep(SLEEP)

    print(f"\n{'='*60}")
    print(f"Done! Processed: {done}, Skipped: {skipped}, Errors: {errors}")
    print(f"Total pages checked: {total}")


if __name__ == "__main__":
    main()
