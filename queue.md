# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

# New Agenda

So I am starting a new agenda here based upon my understanding of what is still going on with the Wikidata labels. 

So yeah, this thing is right here relatively unstructured, and I'm trying to fix it up so this is more of a vision of what we're trying to do. This is more of a vision of what we're trying to do that kind of needs to be metabolised into a more proper queue. 

So I guess a key thing here, simply put, is that we are never going to introduce any kind of more direct editing of wikidata. That is completely non-negotiable. We are not going to be adding any kind of new type of editing of wikidata. We are entirely basing it off of this relatively drip-fed thing that does stuff over time. 

But from it here, here's a very massive amount of more vision stuff that needs to be metabolised as the first task of this cue into more of a proper thing that runs.
The vision here is essentially that, through a pipeline that we are developing here, what happens on Wikidata is that, in every run, there will be a search that is done to find all of the Shinto shrines that do not have English language labels. It is going to basically have a four-part pipeline, although I erroneously said three parts earlier, with progressing order:
1. If there's a Shinto shrine without an English language label but it has kana, then we put together the English name based off of deterministic rules based off of the kana.
2. If there's one without kana but it has English language labels for shrines with identical Japanese names, then we take the names from that.
3. If that is not an option, then we look: does the shrine have any labels in languages other than English that have a Latin or Cyrillic script, or otherwise a non-CJK script? We will use some sort of a transliteration library that you'll be able to get anywhere to transliterate it, cut off the second word, and replace the second word with shrine. This is admittedly a messy one, but I don't think we'll end up with this edge case very often.
4. Put it into the actual large language model remote queue for a translation.
Okay?


The idea behind it is that I think our pipeline currently pretty much entirely goes through the Indonesian labels, which is a bit of an annoyance. It is a bit of an annoyance. I don't want us to be doing anything that removes the existing work, like Indonesian label-derived stuff that's entering into the queue and stays in the queue.

My vision of our new system here is that we are moving towards generating everything based off of the English labels for all these subsequent languages. The idea with this pipeline is, simply put, that if there's any random shrine that just has a Japanese name, the Chinese labels in all the different sublanguages (which should be implemented or not, but I think they're implemented) are essentially generated in the suggestions from the Japanese label. Same with Korean.

For all languages but those things, it goes through our English language pipeline. It makes an English language label, and the English language label's work eventually turns into something later on. That is to say, from our thing that we have right here, the English language label gets applied, and then in subsequent runs of the programme, it finds the English language label and uses the information in the English language label to make the labels for all of these other languages, which then eventually go through. I think right now we have it so that it goes through the Indonesian language label, which is a bit weird, and the Toki Pona comes out of the English language label too. All this essentially is going through the English language label at this point. Eventually we are developing a very, very large linguistic coverage of all of the different Shinto shrines and their labelling. 

Yes, this is a very, very slow drip pipeline thing that's intended to get maximum labelling coverage for the Shinto shrines while also minimising the issues. 

I want you to develop this so that in addition to the random freeform language suggestions later in this document, you use the language coverage info in query.csv That one lists the numbers of labels present in every single different language for the shrine names and the ideas. Algorithms should be filling out every single one of those languages to the top. This should be a specific institutionalised thing in the indie lake metabolization of it. Every single language gets an item where we end up having a generator for it. I think a lot of the languages already have generators, but not all of them.

The idea is that if you are lost on the individual language and how to do it, you will look at the actual existing labels and continue whatever the pattern is based off of them, because you have the ability to look at Wikidata and find all this stuff, even though we're not directly editing Wikidata.

One thing that is important, particularly on the languages with very low amounts, is that the particular logic of them might be flawed. For example, I think that Tibetan, at least at one point, really did not have very good labelling. Its labelling was very weird. Just keep in mind that for the lower sample size ones, if the convention just looks really off, then make your own convention for the length, because this involves a lot of transliteration and stuff like that. I trust that you have the ability to do that so that we can make a very good pipeline that manages to properly cover all these languages. CJK languages just end up copying the characters there, and Korean is that weird special case too, but the rest of them, their names come from English. 

Oh, and in the rare event that there is a shrine that has a seat that doesn't have a Japanese label but, in any other CJK language, has a name, then our pipeline should just be copying that one's CJK one onto the Japanese label. In the event of it having some kind of, yeah, I think that that's pretty straightforward. Honestly, that's enough. We should have a part of the pipeline that, if there's one with a Chinese name but no Japanese name, then it copies it over, but do not fret about that thing. Shinto shrines without Japanese labels are weird edge cases. 

Oh actually in addition to the languages here we are adding a new queue item at the end to do stuff with

Here is an explanation

#
Yes — the queue is clear and there's a fair amount of auto-translation infrastructure for shrine labels. Here's the picture, organized by mechanism since "auto-translation" actually splits into three independent systems:

1. Rule-based label transliteration — shinto-label-generator/

This is the heaviest piece, and it's 100% deterministic transliteration, no MT/LLM. It takes existing Wikidata labels (mostly Indonesian/Japanese/kana) and mechanically produces labels in ~15 languages:

- Toki Pona (tokiponizer.py — full phonological mapper), Korean (hangul via Unicode arithmetic + hanja sino-readings), Chinese (man'yōgana table + OpenCC simplified), and a bulk pipeline for tr, de, nl, es, it, eu, lt, ru, uk, fa, ar, arz, hi, fr, pt — including genitive declension for Lithuanian/Russian/Ukrainian and Cyrillic/Perso-Arabic/Devanagari script maps.
- It also proposes Indonesian labels for Japanese-only items via pykakasi Hepburn romanization (the seed for everything downstream).
- Live in CI: regenerates monthly + on push, writes quickstatements/<lang>.txt.

2. The bridge to Wikidata — drip feed

The generator doesn't submit anything itself. modern-quickstatements/select_label_proposals.py pulls 20 random lines/day into label_proposals_drip.txt, and submit_daily_batch.py (the single daily submitter) pushes them via QuickStatements. Deliberately slow for community feedback; it floods the full pool on RAMP_DATE = 2027-05-23.

3. The only actual LLM/MT path — English labels

- generate_shrines_missing_en_label.py builds a daily SPARQL worklist (Shinto shrines with ja label + kana but no en).
- select_shrines_to_translate.py picks 5/day, fed to a remote Claude Sonnet routine (local cron, claude.ai) that machine-translates from ja label + kana → en_labels_sonnet.txt → daily submitter.
- This is the only true MT/LLM label generation in the repo. Everything else is rule-based or lookup.

Adjacent (not label generation)

- need_translation/ is full-article translation, not labels — synced bidirectionally by sync_need_translation.py; the actual translation happens off-repo via the claude.ai remote queue.
- Category-name translation (generate_category_translation_moves.py) is authoritative-lookup only — never machine-guesses, defers place-name cases to humans.

Bottom line on "degree": Quite mature for labels. Transliteration covers 15+ languages fully automatically and runs in CI; English is the one slot using an LLM, throttled to 5/day. The deliberate constraint everywhere is pace — 20 transliterated + 5 English labels per day, by design, to stay invisible-friendly on Wikidata and reviewable, not a throughput limit.

Want me to dig into any one of these — e.g. how many labels are currently queued vs. submitted, or whether any target language is underperforming?

# Conclusions

I am not really sure what to make of all this stuff. What I want to attempt to do is to make something that, with the large language model Claude translation stuff, continues with this: a daily set of translations of the Shrine names for Shrines on Wikidata that have Japanese labels but do not have English labels. 

So basically, it's going to be the same way that all of our other large language model tasks work. There's going to be a thing there for the Claude to translate the shrine names. 

But this is rather complicated. First of all, there are lots of instances of Shinto shrines that have kana readings but do not have English. In this case, I believe we already have an algorithm that does kana to English, but if we do not, we need to add this thing in. This is a thing that takes a priority. Our auto-translation of shrine names as proposals only occurs if there are no kana readings. 

But I actually have a secondary thing I want to do as well. My secondary thing before the auto-translation of the shrine names is that I want us to have something that, for anything that doesn't have an English name but has a Japanese name and it does not have a provided kana reading, we will search for shrines with identical Japanese names. If there is one, if all this, if there are other ones, let's just 

Okay, scenarios:
1. There is at least one shrine that has the same name, and that shrine that has the same name in Japanese has an English label. We use it. It simply goes through our thing into an English label that eventually goes through our quick statements infrastructure. The fact that there is another shrine that already has it, if there is any kind of English language alias, then we add the English language alias to the shrine in the quick statement stuff.
2. If there are multiple shrines with this that have different English language labels, what you will do is, if one of them is dominant and the other one is not, then you will basically, if one of them is more common than the other one, that one becomes the label, but we add an alias of the less common reading. If they're both the same, then just choose one of them at random.
3. At this point, we're not going to be including the aliases unless it's just one other one. I think this is pretty clear.
4. Once we're done with this, we have a queue of these shrines that we are adding English language labels to, based off of these two rules:
1. The kana
2. Based off of the readings
Then we go to the third rule, which is that it goes to the large-language model, and the large-language model does the translation. The Python library that made the Indonesian labels, we are not using it because that library was inaccurate. If there is generated stuff already in the pipeline, then let it be. It's not the worst stuff.


My presumption here in how all of this works is that we currently have a pipeline that, through a relatively roundabout way, ends up translating from the Japanese to Indonesian and then to all these other languages. This current infrastructure goes into English, and we have a large amount of rules already set up here, but the basic thing is 

Jinja -> Shrine
Jingu -> Grand Shrine (jingu as alias)
Taisha -> Grand Shrine (taisha as alias)
Daijinja -> Daijinja
-sha -> -sha Shrine
-gu -> -gu Shrine

Yeah, I'm pretty sure all this stuff is well documented enough that I don't really need to explain it that much. The basic thing is we're kind of anglicising this stuff a bit, but we're preserving it. We're not just calling it these random things, shrines we have. There's better documentation in the modern quick statements and stuff. 

I think that our pipeline, the way that it operates, tends to. Once there is an English language version of it, once there is an English language name, then the English language name goes into the Indonesian, and then the Indonesian ends up eventually getting into all these other languages. All that stuff is good. 


Another thing that I also want you to add here is that I'm not entirely sure about all the languages that are added. 


Okay

## Languages to add to pipeline stuff extension

Bengali
Vietnamese


Questionable I think Mistral was confusing things and these exist in the pipeline
1. Japanese already included
2. English already included?
3. Indonesian
4. Malay

## Marginal languages to include if we can

You’re right—my initial response was overly exhaustive. Let me cut to the chase:

### **Major Languages *Missing* from Your List**
Your pipeline already covers **most of the big ones** (Mandarin, Hindi, Arabic, Spanish, Russian, etc.). The **glaring omissions** are:

1. **English** – The global lingua franca.
2. **Japanese** – Major tech/cultural influence.
3. **Bengali** – 7th most spoken globally.
4. **Vietnamese** – Growing influence in Southeast Asia.
5. **Indonesian/Malay** – Lingua franca of Indonesia/Malaysia.

---
### **Why These?**
- **English** is non-negotiable for global reach.
- **Japanese** is critical for tech, pop culture, and academia.
- The others fill gaps in **speaker count** or **regional importance**.

---
### **The Cat?**
Still likely a typo or Easter egg. Unless you’re hiding a `cat.py` in your repo? 😼

---

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.

