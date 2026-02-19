# wikibot

A bot framework for editing MediaWiki wikis, primarily [shinto.miraheze.org](https://shinto.miraheze.org), with integration against Wikidata and the [pramana.dev](https://pramana.dev) server.

---

## Current state

The root directory and `shinto_miraheze/` contain hundreds of accumulated one-off scripts, log files, and data CSVs from several years of iterative work. Most of these are legacy ChatGPT-era scripts that are no longer needed. A cleanup pass is planned (see [VISION.md](VISION.md)).

The active, maintained scripts are documented in [SCRIPTS.md](SCRIPTS.md).

---

## Active scripts (shinto.miraheze.org pipeline)

| Script | Purpose |
|--------|---------|
| `shinto_miraheze/resolve_category_wikidata_from_interwiki.py` | Resolves Wikidata QIDs for category pages by querying their interwiki links |
| `create_category_qid_redirects.py` | Creates `Q{QID}` redirect pages in mainspace pointing to their category |
| `fix_ill_destinations.py` | Fixes broken ILL template destinations |
| `add_moved_templates.py` | Adds `{{moved to}}` / `{{moved from}}` templates after page moves |
| `remove_defaultsort_digits.py` | Removes `{{DEFAULTSORT:}}` from Wikidata-generated shikinaisha pages |
| `fix_dup_cat_links.py` | One-off: fixes `[[Category:X]]` → `[[:Category:X]]` in dup disambiguation pages |

---

## Credentials / secrets

**All scripts currently have hardcoded credentials.** This must be fixed before the repo can be made public. See [VISION.md § Secrets](VISION.md#secrets) for the plan.

Until then, do not share this repo publicly.

Required credentials (to be moved to environment variables or a `.env` file):
- `USERNAME` / `PASSWORD` — MediaWiki bot account (`Immanuelle` on shinto.miraheze.org)
- Pramana server credentials (future)

---

## Setup

```bash
pip install mwclient requests
```

Run any script directly:
```bash
python create_category_qid_redirects.py
python shinto_miraheze/resolve_category_wikidata_from_interwiki.py
```

---

## See also

- [VISION.md](VISION.md) — full architecture plan and future direction
- [SCRIPTS.md](SCRIPTS.md) — catalog of all scripts with status
- [API.md](API.md) — how every external service is accessed (mwclient, Wikidata, Wikipedia APIs)
- [SHINTOWIKI_STRUCTURE.md](SHINTOWIKI_STRUCTURE.md) — page structure on shintowiki: `{{ill}}`, `{{wikidata link}}`, QID redirects, category/template/talk page conventions, known issues

  URGENT

  OK so I had a bit of a fuck up where I sent a very very large prompt to Claude code about what I was doing and then as it was doing other work and I probably should've saved it in like no pad or something but basically basically my computer ended up crashing the wall it was executing so I'm just trying to say basically what it is here so what I am trying to get is basically like I want us to actually be tracking the two due stuff in the I want us to be tracking the to-do stuff for the wiki in this repository now because right now because earlier it was mostly just either half hazard pages on the wiki which which made it to the Claude wasn't really able to help that much with figuring out what the direction was and also I'm just kind of me remembering stuff and like me remembering stuff is good and all but it's I'm not the most reliable so yeah but I'm in a rush right now and that's why it is that I'm editing this based I'm I'm editing this through my phone with speech to text kind of panicking of it but yeah to see what is happening right now but basically OK so essentially on the wiki that there was a whole debacle where the wiki ended up getting suspended and reinstated but like the history isn't properly being imported you can look at the main space of the the main page of the wiki and stuff to kind of get a general idea but the basic issue is that the wiki was restored with XML wiki was restored with XML from archived.org the XML that was made with the wiki the XML that was made the XML that the wiki was restored from was technically the entire history of the wiki but it was like weirdly partially archived and then I took only the most recent version of it to reimport in reimport in January and so and so they're still pending on the actual import of the full history but I'm gonna try to explain what was going on so basically I mean I'm gonna try to explain it so so basically as as you can see on the main page of the wiki basically the main page of the as you can see on the main page of the wiki basically but we need to properly preserve the history and so I introduced templates to do like moving the histories to do like history merges so that the pages maintain their histories and I think that that is pretty self-explanatory there's there's weirdness of there's weirdness of it of course there's a lot of edge cases and I did categorization document I did categorization to document the edge cases of all the stuff I did categorization to document the edge cases of all the stuff so you don't really really need to do a fuck ton of stuff with the categorizations you just need to kind of basically understand it but do keep in mind that like essentially there were two different different waves of movement because of like some weird unicorn code Uno code shit there are some weird un basically and this means that there's like a couple of different reason reasons why it is that a page might've been might be above a move target and a move and move destination there might be there might be two different ones but yeah that's just a thing to kind of vaguely established but yeah I know we're just doing it because we want the histories to be properly coherent but I wanna explain roughly the timeline of the wiki so I was I started using Wikipedia in in 2020 in 2023 I started to get serious problems with Wikipedia basically my my pages were often that I've moved into but moved from main space to draft Space or other above I was doing a lot of translation I had like a translation workflow set up but the problem is basically as you can kind of see in the vision.TXT you think they didn't like that they didn't like that I was doing that because because they didn't like I'm not I'm not gonna get I'm not going to go into the full details of all like my trauma from Wikipedia I ended up with a very very large amount of amount of pages in draft space because I had editing restrictions put on me making it so that I couldn't put published a main space so I ended up getting a peak around 4000 drafts I was blocked from editing I ended up getting blocked permitting around 2023 and was unable to keep the drafts from being deleted so what I ended up doing was I ended up basically I had some drafts that I was editing on simple English Wikipedia for a while but I decided to make this wiki and I imported my simple English Wikipedia draft my English Wikipedia draft if they existed and some of them came from everybody wiki I believe I had about maybe a couple hundred pages or so to start from that I started doing other stuff like I did history import pretty much all of the pretty much all of the Japanese origin pages have history history imports of their Japanese editing history which is part of the reason why it is that the wicked size is so massive

  eventually I started using eventually I came to the I came to the practice of starting to basically use the inter language link template to go to any article that I did not but that did not exist in English Wikipedia briefly I had all the things that linked to English Wikipedia go directly to English Wikipedia but that kind of cause problems and like and one other and the other user ended up not liking that not liking that so I ended up eventually going towards the current practice is every single link in the entire wiki is an inter language link every single link on Wikipedia is the English every single link is the inter language link and earlier I used to use it primarily based around the earlier I used to use a primarily based around the Japanese Wikipedia based around the Japanese Wikipedia link there that I had a couple random drafts that were about other things like a couple of Russian orthodox icons and deities and had a couple a couple Russian Orthodox icons in Td and a couple a couple Russian Orthodox icons and deities and some like ancient Egyptian stuff so like there's there's a bit of like stuff that's not Japanese of origin and but yeah like in order in order to do proper proper citation of the histories there's a translated page template on almost every single page sometimes because of the auto because of the way that I was using ChatGPT to translate pages early on and add in their inter language links most of them go well a couple of them go to like go to the wrong pages a couple of them go to the wrong pages a couple of them go to the wrong pages mostly it's around like disambiguation pages where like something has like this there's also a couple duplicated pages and you can see them in the category she can show emerges although that is a horrible category so I am just going to rename it right now I'm going to rename the category right now and if you check if you check right now but you will see on the wiki is that I have immediately renamed it to something something that's more descriptive and better I don't know what it is yet I'm actively doing it while I'm recording this I'm actively doing this while recording It but I am actively doing it while I'm recording it but my guess is it's probably gonna be something yeah yeah pages with duplicated content yeah I've factored it all to be pages with duplicate content using special replace text

  
