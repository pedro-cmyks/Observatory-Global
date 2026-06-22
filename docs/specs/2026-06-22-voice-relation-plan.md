# Voice Mix — the source→subject relation: plan + justification (2026-06-22)

Pedro's directive: attack both open problems, check whether the **Islamic
world** is represented, and *finish* the Voice Mix so the product makes one
relation explicit — **who is speaking, and about where** — and justify why we
present it that way.

## 0. What the data says (measured, not assumed)

Voice Mix audit + Islamic-world query, prod, 168h:

- Global: English = 96.5% of language-known signals; 21 languages now flow
  (was 2 real non-English a day ago), but English still dominates by volume.
- **Islamic world is covered as SUBJECT but has almost no VOICE:**
  - Iran: 5,932 signals, **1%** in Persian/Arabic.
  - Turkey: 4,060 signals, **0%** Turkish.
  - Indonesia: 4,153 signals, **2%** Indonesian.
  - Pakistan: 1,053, **0%** Urdu. Egypt 1,969, 4% Arabic. Gulf states ~0%.
- Same pattern as China (`country=CN` voice mix = en/es/de). These places are
  *talked about* by outsiders, not *heard from*.

Conclusion: the diversity problem is not only "how many languages exist" but
**"who gets to speak about whom."** That is the relation we must surface.

## 1. The core idea — three dimensions, one relation

Every signal carries three distinct geographic/voice facts that the product has
been silently collapsing into one ("country"):

| dimension | column | answers |
|---|---|---|
| **Subject** | `country_code` | what place the story is ABOUT |
| **Origin** | `source_origin_country` | where the OUTLET sits (who is talking) |
| **Language** | `source_lang` | the language of utterance (whose audience) |
| (whose interest) | `is_state_media` | is the voice a state actor |

The product-relevant relation is **Subject ↔ Speaker**:

- **Endogenous voice** — speaker country/language == subject. Locals describing
  themselves. (Iran covered in Persian by Iranian outlets.)
- **Exogenous voice** — speaker != subject. Outsiders describing them.
  (Iran covered in English by Western wires.)

We define, per subject scope, a **self_voice_ratio** = share of coverage that is
endogenous (origin == subject OR language == subject's primary language). Its
complement is foreign voice, with a named **dominant outsider**.

## 2. Why present it this way (the justification Pedro asked for)

1. **A volume map conflates subject with voice and hides framing.** When Iran
   lights up red, that looks like "Iran coverage." It is actually "Western
   coverage *of* Iran" 99% of the time. Showing only *where news happens*
   silently launders *whose perspective* it is. Separating Subject from Speaker
   is the one move that makes that distortion visible instead of invisible.
2. **"Diversity" is meaningless without the relation.** Adding 11 languages is
   worthless if they never speak about the places in the news. self_voice_ratio
   is the metric that says whether expansion actually reached the subject — it
   is how we *prove* diversity rather than assert it.
3. **It matches the mission.** Atlas is narrative intelligence across
   perspectives. A perspective has a speaker and a subject; collapsing them
   destroys the very signal we exist to measure (single-narrative risk,
   information deserts, state-media capture, foreign-only/unverified-by-locals).
4. **It is honest about our own pipeline.** GDELT is an English firehose; if we
   don't show self_voice_ratio, our own English bias hides inside an
   authoritative-looking "global" map. The metric holds *us* accountable.

Design rule going forward: **every Voice Mix number is a (speaker, subject)
pair.** The UI must always be able to answer "who said this, and about where."

## 3. Problem A — non-Latin geo-tagging (mis-attributed speakers)

`ingest_rss.extract_country()` is English-keyword-only. Non-Latin headlines
(zh/ja/ko/ru/fa/ar/hi…) never match → fall back to the outlet's home country.
Effect: a DW-Chinese story about Syria is tagged `DE`; Al Jazeera Arabic about
Gaza tagged `QA`. This *systematically misroutes endogenous voice away from its
subject* — the exact thing the relation needs to be correct.

Plan:
1. Native-language country lexicons for the high-value languages (ar/fa/ru/zh/
   tr — capitals, country names, leaders in-script). Cheapest, biggest fix for
   MENA where one Arabic lexicon serves ~20 countries.
2. Fallback to the e5 semantic layer / existing NLP geo when lexicon misses
   (signal_embeddings already multilingual).
3. Until fixed, Voice Mix must **label** signals whose subject came from
   outlet-fallback (low geo confidence) so self_voice_ratio isn't overcounted.
   `geo_confidence` already distinguishes them (rss = 0.6).

## 4. Problem B — non-English volume vs the GDELT English firehose

GDELT delivers ~52K en + ~92K untagged / 168h; our native feeds add hundreds
per cycle. english_share_of_known moves only as non-English *accumulates*.

Plan:
1. RSS cadence already bumped 4th→2nd cycle (done).
2. Islamic-world + high-volume feeds (this pass) raise the non-English base.
3. Report self_voice_ratio per subject so we optimize the *useful* non-English
   (coverage of the subject), not raw multilingual volume.
4. Longer term (#229): cluster the persisted multilingual embedding corpus so
   non-English signals form threads instead of drowning in the English count.

## 5. Islamic-world source expansion (this pass)

Verified-live feeds added (RSS WAVE 6):
- Turkish: BBC Türkçe, Anadolu Ajansı (state), Cumhuriyet.
- Urdu: BBC Urdu.
- Indonesian: Antara (terkini).
- Bengali: BBC Bangla, Prothom Alo.
- Arabic depth: **Al Jazeera Arabic**, Sky News Arabia — the pan-Arab voices
  that were entirely missing (we only had Western-Arabic: France24/BBC/DW/RT).

New languages: tr, ur, id, bn. The Muslim world spans ~50 countries and many
languages; this pass covers the largest blocs (Arab, Turkic, Persian, South/SE
Asian Muslim). Central Asian (kk/uz), Pashto, Hausa, Somali, Malay remain gaps
(tracked).

## 6. Voice Mix completion (the relation, in code)

`app/services/voice_mix.py` + `/api/v2/voice-mix` gain:
- `voices_by_language` and `voices_by_origin` — who is speaking, ranked.
- `self_voice_ratio` + `foreign_voice_ratio` + `dominant_outsider`
  (only when `?country=CC`, using a country→primary-language map).
- `state_media_pct` already present (whose interest).
Same formula shared by the offline audit (single source of truth).

## 7. Execution order

1. (done) measure Islamic world + design the relation.
2. Islamic-world feeds (WAVE 6).
3. Voice Mix relation metric + tests.
4. Deploy + prove with Iran/China (high foreign-voice ratio = the relation
   working).
5. Then Problem A lexicon (separate, larger) and the CountryBrief surface.

## 8. Live result (deployed 2026-06-22)

Islamic-world feeds landed: one RSS cycle = 15 languages, 81% non-English,
with **tr 49 (was 0), bn 38, id 26, ur 2** — voices that did not exist before.

The relation, live via `/api/v2/voice-mix?country=CC`:

| subject | coverage about it | self_voice_ratio | dominant outsider |
|---|---|---|---|
| Iran (IR) | 6,062 | **0.014** | GB (en 2,631) |
| China (CN) | 9,371 | 0.316 | DE |
| Turkey (TR) | 4,171 | 0.240 (was ~0) | RU |

Iran heard from itself 1.4% of the time — the distortion is now a number on a
contract surface, exactly as intended. **Caveat (honest):** these self-voice
ratios are a FLOOR. Problem A (non-Latin geo-tagging) routes BBC/DW-Persian
stories *about Iran* to GB/DE (the outlet) instead of IR, so real endogenous
voice is undercounted until the native-language country lexicon ships.

**Update — Problem A first cut SHIPPED (`62f97a2`, deployed):** native-script
country patterns (`_NATIVE_COUNTRY_PATTERNS`) for the highest-volume non-Latin
subjects (CN/JP/KR/TW/RU/UA/IR/IN/US/IL/GZ/SY/DE across zh/ja/ko/cyrillic/ar/
hi), wired into `extract_country`; plus the RSS encoding fix (`resp.read()` →
feedparser detects charset, fixing the folha_pt/antara utf-8 crash). Verified:
`ایران`→IR, `中国`→CN, `Украина`→RU. So Iran's measured 1.4% self-voice already
includes correct Persian/Arabic geo-tagging — it is *honest*, not an artifact:
Iran really is ~99% foreign-voiced because we hold few Persian feeds against
GDELT's English flood. Remaining Problem A: full Arabic-subject lexicon
(السعودية/مصر/العراق…), Turkish/Urdu/Bengali subjects, and the e5/NLP geo path.

Shipped: `3064dd5` + `62f97a2`. Endpoint contract `voice-mix-v0` now carries `relation`,
`voices_by_origin`, `primary_languages`. 13 tests green.
