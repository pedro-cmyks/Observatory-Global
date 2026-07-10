# Coherence guard content-signal extension (#224 false negative) — 2026-07-10

## The measured false negative

`dynamic-topic-755` "NATO Summit in Ankara" served coherence
`{score 0.617, tier "tight", space whitened-e5-k1, no warning}` while its
members were eyeball-confirmed CONTAMINATED: a real NATO-Ankara core mixed with
Algerian earthquakes/wildfires, Mahrez-retirement football, Egyptian gold-price
listings, Libya/Syria items — an **Arabic-language blob** (same pathology as the
Spanish dt-52 black-hole, which the guard did catch at 0.531 loose).

Why cosine fails here: same-language content clusters tightly with itself in e5
**even after whitening k=1** — a language-cohesive grab-bag reads "tight".
dt-755 sat in the mixed band (0.617 < 0.70) but was rescued by the
country-dominance exemption (topCountryShare 0.53 ≥ 0.5, TR+DZ only).

## Encoding question (task step 1) — verified, NO substrate bug

`signal_embeddings` has exactly ONE writer: `scripts/embed_hot_corpus.py`
(grep: no other `INSERT INTO signal_embeddings`). It has embedded
`html.unescape(headline)` since its first commit (`207fedad`, 2026-06-11) —
the "&#x…;" encoded forms in `signals_v2.headline` never reached the embedding
model. No re-embed needed.

## Content signals (measured on 24 live threads, embedding-free)

Measured with junk filtering: tokens len≥4, non-digit, minus a small
multilingual function-word list, minus tokens present in the row's own
`source_name` (outlet suffixes like "– النهار أونلاين" otherwise become the
"top story token" — dt-755's raw top-2 tokens were the En-Nahar suffix).

**`storyTokenCoverage`** = share of members whose headline contains one of the
thread's top-3 doc-freq content tokens. Separation found:

| thread | label | coverage | ground truth |
|---|---|---|---|
| dt-755 | NATO Summit in Ankara | **0.349** | blob (confirmed) |
| dt-667 | Poland Declassifies Military Aid | **0.452** | blob (4 distinct stories: Poland provocation / Patriot declassify / DE mobilization-return / Monaco Yermolaev) |
| dt-837 | Senegal Political Turmoil | **0.467** | political grab-bag |
| dt-52 | Cepeda Concedes | **0.472** | blob (known) |
| dt-416 | Jimmy Mohamed Allegations | **0.476** | contaminated (RTL.fr front-page dump: canicule/Le Pen/typhoon/recipes mixed into the story) |
| — gap — | | | |
| dt-535 | Roxana Guzmán Murder | 0.636 | clean (floor) |
| dt-14 | Violent Crimes and Arrests | 0.645 | grab-bag but cosine-mixed already |
| dt-605/713/440/… | | 0.65–0.92 | clean |
| dt-1419 | Keiko Proclamation | **1.0** | clean |
| dt-792 | Milei Inauguration | **1.0** | clean |

Cut chosen mid-gap: **0.55**. Guarded against the cross-language/morphology
confound (a real multilingual event splits token coverage across scripts) by a
conjunction with **`topActorShare` < 0.5** — latin-normalized `persons` stay
shared across scripts for a real single event (dt-443 Zaporizhzhia actor 0.72),
while blobs share neither (dt-755 actor 0.116, dt-52 0.25, dt-837 0.03).
Weather threads (no actors) stay clean because their token coverage is high
(canicule 1.0, calor 0.909). Min members 10 for the grab-bag flag.

**`repeatedHeadlineShare`** = max identical normalized (html-unescaped)
headline / members. The "جريدة البلاد repeated identically" pattern = front-page
dump. Cut 0.4 (nothing in the live sample trips it; it exists as the cheap dump
detector for the class the analyst saw in other windows).

Signals that did NOT separate on this window (measured, rejected):
headline diversity (1.0 everywhere), repeated-identical share on the 30d
window (0.02–0.2 flat), language concentration via `source_lang` (metadata is
mostly 'xx' — degenerate).

## Guard changes (`backend/app/routers/themes.py::_thread_coherence`)

Contract preserved ({score, tier, distinctCountries, topCountryShare, members,
warning, space}); additive fields: `storyTokenCoverage`,
`repeatedHeadlineShare`, `topActorShare`, `contentFlag`
(`grab_bag`|`syndicated_dump`|null), `embeddedMembers`, `reason`.

- Member query now LEFT JOINs embeddings and also pulls headline/source/persons.
- Content flags escalate a cosine-"tight" thread to **mixed** (warn-only, never
  blocks — same philosophy as #224). Cosine loose/mixed tiers unchanged.
- ≥5 members but <5 embedded → honest `{tier: "unknown", reason:
  "insufficient_embeddings", score: null}` instead of null-silent (the 20h
  engine-gap class). Frontend renders nothing (badge gated on `warning`;
  `score.toFixed` only reached when warning set) — verified against
  `ThemeDetail.tsx`.

## Before/after (live DB, same members)

| thread | before | after |
|---|---|---|
| dt-755 | tight 0.617, no warning | **mixed**, contentFlag grab_bag, coverage 0.349 |
| dt-52 | loose 0.531 | loose (unchanged) + contentFlag grab_bag |
| dt-416 | tight 0.611, no warning | **mixed**, grab_bag 0.476 |
| dt-837 | tight 0.635, no warning | **mixed**, grab_bag 0.467 |
| dt-667 | mixed (country rule) | mixed (unchanged; now also grab_bag) |
| dt-1419 Keiko | tight 0.657 | tight, coverage 1.0, no flag |
| dt-792 Milei | tight 0.816 | tight, coverage 1.0, no flag |
| dt-1220/407/443/535/628 clean | tight | tight, no flags |

Net: 3 confirmed-contaminated threads flip tight→mixed; zero clean threads
regress.

## Label-mismatch class (task step 4) — FOLLOW-UP, not shipped

dt-1932 ("DR Congo Ebola" label over all-Nigerian members) and dt-1675
(Netanyahu label over Putin/Ukraine members) have **zero v1-compat evidence
members in the 30d window** — the guard has nothing to compare against the
label. The cheap token version (label tokens ∩ member headline tokens) also
false-positives on every cross-language thread (English label "NATO Summit in
Ankara" over Arabic headlines shares zero tokens with genuinely-matching
coverage). An honest check needs label-implied country/person resolution
(country-name→ISO + persons vocab) — scoped follow-up, not a cheap add.
dt-56-class mismatches (label "Trump Tariffs" over Duterte members) are already
caught by the cosine loose tier (0.556).

## Tests

`backend/tests/test_theme_coherence_content.py` (7) freezes
`_coherence_content_signals` against the measured pathologies: grab-bag low
coverage, outlet-suffix stripping, multilingual-event actor protection,
front-page dump, HTML-entity normalization. 22 pass with neighboring theme
suites.
