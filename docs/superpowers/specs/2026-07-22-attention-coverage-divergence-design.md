# Attention–Coverage Divergence (silent risk, re-scoped) — design

**Date:** 2026-07-22
**Status:** **BLOCKED (2026-07-22, same day)** — approved, then undercut by its own
measurement before any code was written. See §0. Do not implement Tasks 10–15 of
the plan. Tasks 1–3 (pure modules) and Task 7 (delete the inverted info-desert
floor) survive; everything that depends on `coverage_count` meaning "covered"
does not.

---

## 0. The blocking result (added after the measurement completed)

This spec was written from partial probe output. The completed synthesis
(`docs/research/silent-risk/2026-07-22-silent-risk-source-measurement.md`) ran a
control this design never did, and it invalidates the foundation.

**The placebo.** Score the same trend keywords against press published **5–7 days
before they trended**:

| matcher arm | silent% vs current press | silent% vs PRE-TREND press | discriminative gap |
|---|---|---|---|
| original (buggy) | 44.5% | 59.4% | 15.0pp |
| both bugs fixed | 33.0% | 50.3% | 17.3pp |
| + idf-coverage ≥ 0.60 | 26.5% | 42.7% | 16.2pp |

Fixing the matcher makes it claim ~18pp more coverage but **does not make it
discriminate better**, and the thresholded variant discriminates *worse*. Of the
761 pairs the bug fix rescues from silence, **465 (61%) are also "covered" by
press that predates the keyword's trend**. Therefore `coverage_count` is a
**lexical-match rate, not a coverage measurement**, and §4.2's divergence — which
is built on it — is unvalidated.

**The missing control.** §3.1 cited a 22.5% story base rate in the silent set.
The covered set was never measured. It is **15.8%** (z = 1.51, not significant).
So the silent set is not story-enriched, and 22.5% is a property of Google
Trends, not of silence.

**What survives.** The GDELT encoder defect, now root-caused in code:
`ingest_v2.py:427` stores the `<PAGE_TITLE>` capture raw while the same function
unescapes the same string ~30 lines later. Blast radius far exceeds this feature —
~47% of GDELT rows were embedded, NER'd and dedup'd from mojibake. Also surviving:
the deletion of `_INFO_DESERT_FLOOR` (measured inverted), and the finding that
forums, wiki and the ensemble are not viable sources.

**What must happen before this spec is unblocked.** Run the placebo against the
**domain-level** metric, not the per-keyword one. §4.2 aggregates to
`(parent_domain, country)` shares, which the placebo never tested; if domain-level
divergence against pre-trend press is indistinguishable from divergence against
current press, the metric is dead and this spec should be closed rather than
fixed. That test is cheap and is the only thing worth doing next.

---
**Supersedes:** the parked silent-risk detector (`app/services/silent_risk.py`,
`app/routers/attention_threads.py`, `GET /api/v2/attention/silent-risks`)
**Follow-up chip it closes:** `2026-07-22-under-the-radar-rescoped-coverage-gaps-design.md`
§"Out of scope" item 2 ("Silent-risk meaningful")
**Does NOT touch:** the Under-the-Radar dock tab / coverage-gaps spec (separate,
possibly in flight), or the eclipse dramatic-moment chip.

---

## 1. What changed, and why the old framing is dead

The parked detector claims: *a topic with high public attention and near-zero
media coverage = the press is not covering it.* Measurement killed that claim
twice over.

**(a) We cannot verify press silence.** Five of the strongest "uncovered"
candidates were web-checked against the open internet. All five were covered,
often heavily, by outlets Atlas does not ingest:

| candidate | country | reality |
|---|---|---|
| `απαγόρευση εργασίας λόγω καύσωνα` | GR | mandatory 13:00–17:00 outdoor-work stoppage, €2,000/worker fine — ΤΑ ΝΕΑ, LiFO, news247, powergame |
| `inundaciones en nogales` | MX | 1 dead, 14 rescued from a bus, 45mm in <1h, governor on site — La Jornada, Excélsior, TV Azteca, El Imparcial |
| `jurisdicción especial para la paz` | CO | president-elect attacks the JEP; UN Security Council reaffirms — El Heraldo, Semana, Vanguardia |
| `standard bank mortgage bond default` | ZA | R2.1m summary judgment, same day — IOL |
| `разлив нефти` | RU | shadow-fleet tanker spill off Oman — Reuters |

Only a magnitude-2.8 Dubbo earthquake was genuinely near-uncovered. **A detector
that says "the press is silent" is wrong roughly as often as it fires.**

**(b) Most measured "silence" was our own encoder.** 46.6% of the 48h press
corpus stores HTML numeric character references (`hurac&#xE1;n`), and it is
**100% the GDELT lane** (gdelt 48.8% encoded; independent 1/8,596; wire, state
and social all 0). A single `html.unescape` over the corpus changes the script
census beyond recognition:

| script | as stored | after unescape |
|---|---|---|
| greek | **0** | **8,202** |
| hebrew | 0 | 715 |
| cyrillic | 2,719 | 24,589 |
| arabic | 2,352 | 8,691 |
| devanagari | 163 | 3,014 |
| thai | 15 | 470 |
| tamil / telugu | 0 / 0 | 149 / 138 |

Atlas is **not** blind to Greek. It holds 8,202 Greek headlines. Every
"Atlas-blind" conclusion drawn from the stored corpus — including an earlier
draft of this design — was an artifact of the same bug.

So the product does not get to say *the press is silent*, and it does not get to
say *we are blind* either. What it can say, and can prove, is that **public
attention and Atlas coverage are out of proportion** — a ratio between two
fields we both measure. That is the metric this spec builds.

---

## 2. Method, and the instrument that had to be fixed first

Everything below is measured on prod, read-only, 2026-07-22, with a
7-probe fan-out where **each probe was then adversarially re-measured by an
independent agent instructed to refute it**. That step earned its keep: it
refuted the first headline number of this very session.

The original harness scored 43.8% of (country, keyword) trend pairs as having
zero press coverage. Three instrument bugs, all found by refutation:

1. **HTML entities** (above) — `fold()` turns `&#xE1;` into a bare token `xe1`,
   so an accented word cannot exist. `huracán`: 0 matches → 16 in the same 48h
   window from `html.unescape` alone.
2. **Index gate** — the inverted index is keyed on exact whitespace tokens but
   verification is by substring, so morphology kills the lookup
   (`predicción`/`predicciones` never yields the bare token `prediccion`).
   Worse, `min(toks, key=lambda t: len(inv.get(t, ())))` picks the **missing**
   token, because absent → length 0 → the minimum. Any keyword with one
   out-of-vocabulary token scored silent by construction.
3. **Conjunction** — requiring *all* tokens is too strict; abbreviations
   ("nottm" for Nottingham) guarantee a miss.

Corrected silent rate, three independent recomputations. They differ because
each fixes a different subset; the ordering is consistent and the direction is
one-way:

| correction applied | silent rate |
|---|---|
| none (original harness) | 43.8% |
| `html.unescape` only | **34.6%** |
| unescape + idf-coverage ≥ 0.60 + index fix | **27.8%** |
| unescape + char-trigram index + idf-cov ≥ 0.60 + script-safe fold | **25.7%** |

**Nothing downstream of the corpus may be trusted until the encoder is fixed at
ingest.** That work is a separate task already in flight; this design depends on
it and re-measures after it lands (§8).

---

## 3. Findings per candidate source

### 3.1 Google Trends — the only viable primary source · STRONG LEVER

- `trends_v2`: 327k rows / 14 days, **99 countries**, ~100–230 distinct keywords
  per country per 24h, fresh to the hour. "Trending now" RSS, so *rising* is
  true by construction — no baseline model needed.
- Already ingested (`app/services/ingest_trends.py`), every 2nd cycle.
- Genuine signal is present. Hand-labelled base rate on the silent set
  (n=280, two independent samples, 23.3% and 21.5%): **22.5% are a real story or
  a hazard lookup** (95% Wilson CI 18.0–27.7%). Projected: ~650 signal-bearing
  items/day in the silent set.
- Composition of the rest: sport 25.7%, commercial/utility 14.3%, entertainment
  13.2%, bare-person-ambiguous 10.4%, other noise 7.9%, routine weather 5.4%,
  lottery 0.7%.

### 3.2 Wikipedia full pageview API · WEAK LEVER

A true 30-day per-article baseline does fix the mechanical defect the parked
detector is stuck on — the top-N store makes every title look like
`baseline = 0`, when in the real data only 5/282 titles genuinely have no
history. It reorders the ranking substantially and evergreen noise falls out.

But it does not make wiki usable as a primary source:
- Only 14.2% of the top-120 by true surge is news-relevant; news-relevant **and**
  press-silent is 8.3%; honest yield ≈ **3–4 genuine events per 120 scored
  titles/day**.
- 33% of apparent silence is a cross-language transliteration artifact (Kevin
  Keegan surfaces independently in nl/th/el/he as four "silent" rows).
- Structural false positives the baseline cannot remove: Wikipedia's own
  featured-article of the day, old films broadcast on TV, calendar/saint's-day
  pages, and obituaries (9–11 of every top-80).
- **The breadth inverts the mission**: the per-country top list returns HTTP 404
  for RU, CN, TR, IR, EG, PK, BD, VN, SA, VE, BY, CU, SY, IQ, AF, YE, ET, MM, PS,
  KZ, AZ and 12 more — precisely the low-press-freedom set.

*Contradiction on the record:* the probe measured 3/25 overlap between
true-surge and raw-views rankings; its verifier measured 12/25 against the
ranking production actually serves. Both agree the baseline changes the ranking;
they disagree on magnitude. Not averaged, not resolved — wiki is a secondary
lane either way.

### 3.3 Forums / social · DEAD END as a primary source

- Social corpus ≈ 4,150 rows/day; **80.3% ungeocoded**; bluesky is 79% of it and
  country-blind; the ingest samples 25s/hour ≈ 0.56% of the week.
- Every term clearing a surge threshold is a single automated account: an EU CVE
  disclosure bot (11 of the top 12 terms by surge ratio), NWS weather-alert bots,
  an AQI bot, a radio bot, a Dutch job bot, restock/deal bots.
- Of the 8 hand-picked real overlooked stories, social corroborated **1**.
- Largest news community = `lemmy/news@feddit.it` at 17.4 posts/day. All viable
  communities are Anglophone or Italian, tech/politics — **none overlaps the
  countries where trends found real stories**.

**Rule: social presence may raise confidence; social absence is never evidence.**
(The verifier added that Atlas social attention is largely *press-derivative*,
which further disqualifies it as an independent vote.)

### 3.4 Multi-source ensemble · NOT AVAILABLE

- Only 69 of 2,888 trends-silent pairs (**2.4%**) have any second source.
- 7 of 8 known-good leads sit where no ensemble can fire.
- The 69 survivors are junk: footballers, and cross-country false friends
  (`liquid glass`, an iOS feature, firing in ET/LK/KW/NP off one English post).

*Verifier correction, accepted:* the 2.4% is not a law of nature — it is
`if rank > 25: break` in `ingest_wiki.py`. The honest statement is **"reachable
but useless at today's wiki pool"**, not "unreachable". Raising the cap is a
cheap future experiment, not a v1 dependency.

**Cross-country agreement is the wrong axis and must not be used.** It is
anti-correlated with the target: `nottm forest vs blackburn rovers` trends in 21
countries, `weather` in 24. The only genuine news high in that ranking is
already heavily covered. All 8 known-good leads have
`n_countries_trending = 1`.

### 3.5 Not an early-warning signal

Trend keywords silent on day D, checked for press on D+1 and D+2:
**16.3% lead, 83.7% never covered**, and the strongest "leads" are scheduled
sport (UFC, World Cup fixtures). The product must not be sold as prediction.

### 3.6 Voice-mix as a ranking driver · REJECTED (it stays as a label)

- `self_voice_ratio` vs corrected silent%: **r = −0.185**, non-monotonic across
  buckets. `log(domestic press)` vs silent%: r = +0.028.
- An attention/supply *ratio* ranking is a denominator artifact:
  r(log press, log silent-per-1k-press) = **−0.816**.
- `_INFO_DESERT_FLOOR = 40` is **miscalibrated and inverted**. Real per-country
  24h press distribution (220 countries): p5=2, p25=19, p50=86, p75=419,
  p95=4,179. The floor sits at ~p31, labels 74/220 countries a desert, and
  labels **0 of the 99 countries that actually have trends attention**. Silence
  *rises* with press volume (17.9% at 0–50 press vs 33.6% at 800–1600).

**Decision: delete `_INFO_DESERT_FLOOR`.** Do not replace it with another guessed
constant. Voice-mix stays as descriptive context on an item, never a rank term.

---

## 4. The metric

### 4.1 One shared space

Public attention is today decorative: `trends_v2` reaches the engine at exactly
one place — `thread_intelligence.py:1668` — as a `LIKE` over English theme words
producing a chip in the thread detail. It never types, scores, ranks, or clusters.

This design types it. Every trend keyword is embedded with multilingual-e5,
**whitened with Atlas's own global transform** (`app/data/e5_whitening.npz`),
and matched by argmax against anchors built from the 30 seed `atlas_topics`
(label + description) **plus explicit negative anchors** for the measured noise
classes (sport fixture, lottery, entertainment, routine weather, commercial
lookup, bare person, video game).

Attention and coverage then live in the same `(category, country)` space, and
become comparable for the first time.

Measured, on 400 silent keywords across 99 countries:

| | raw e5 | whitened |
|---|---|---|
| similarity spread (p99−p1) | 0.122 | **0.308** |
| max crisis−noise margin | +0.052 | **+0.206** |
| crisis-argmax share | 23.8% | 28.0% |

End-to-end with the corrected matcher, `margin ≥ 0.06`: **159 candidates across
60 countries, median 2 per country.** Cross-lingual noise rejection works with no
per-language lexicon — routine weather rejected in ar/el/ko/pt/ro, lottery in
th/es.

**Why not rules.** A hand-built multilingual rule filter reaches 93.9% precision
(exact, all 98 tray items labelled) but only **7–14% recall**, and it overfits
catastrophically: 74.3% recall on the dev sample it was written from, 7.1%
held-out; 17 of its 25 firing rules match exactly one item in all 2,888.
73% of its misses are a missing risk-word translation across ~17 language-script
pairs, and **47–55% of silent queries are a bare named entity with no common
noun to match at all** — a hard ceiling for any lexical approach, and precisely
what an embedding crosses. Rules are kept only as a cheap pre-filter for the
three unambiguous classes (lottery, fixture `X vs Y`, routine forecast), never as
the gate.

**Honesty constraint on the category.** The crisis-vs-noise *binary* is reliable;
the *specific* category often is not (`snelheidscontrole` → gang-control,
`uppehållstillstånd` → fuel-subsidy). Therefore the item surfaces the
`parent_domain` only, hedged as "closest Atlas domain", never a confident
category assertion. The margin is what gates; the label is a hint.

### 4.2 Divergence, not silence

Computed at **`parent_domain` granularity, not `slug`** — because §4.1 measured
that the specific category is often wrong while the domain is stable. For each
`(domain, country)` in a window:

```
attention_share = domain's share of that country's typed trend volume
coverage_share  = domain's share of that country's Atlas press volume
divergence      = attention_share − coverage_share
```

- **Under the radar** = `divergence > 0` — attention outruns coverage.
- **New** = the domain has attention in the current window and **zero** Atlas
  coverage in the trailing 7-day baseline for that country — i.e. not merely
  under-covered now, but absent from that country's coverage history.
- Both are claims about *proportion inside Atlas's own corpus*. Neither claims
  the press is silent. Neither claims we are blind.

This is the sibling of attention-eclipse, and the relationship is explicit:
eclipse measures concentration **inside** coverage (one story taking ≥20% of the
room); divergence measures coverage **against** an independent field. Same shared
story-state, a third reading — no parallel truth model.

### 4.3 The gap is a work-list

Where divergence stays high for a `(country, language)` after the encoder fix,
the item names what is missing so it can be **fixed, not confessed**. Measured
today: `ingest_rss.py` carries 200 domains — at most one flagship national outlet
per country, **no regional press and no Greek/Hebrew/Thai-language press**.
Colombia is `eltiempo.com` only; Mexico is `jornada.com.mx` only; South Africa is
empty. Nogales was regional news; the JEP story ran in El Heraldo, Semana and
Vanguardia.

Output feeds the #235 "every country a domestic voice" program directly: each
row is `country + language + category + example query` → the feed lane to acquire.

---

## 5. Contracts

### 5.1 `GET /api/v2/attention/divergence`

Replaces `/api/v2/attention/silent-risks` (contract `silent-risks-v0` retired).

```
GET /api/v2/attention/divergence?country=CC&hours=24&limit=15
contract: attention-coverage-divergence-v1
```

Response, per item:

| field | meaning |
|---|---|
| `query` | the trend keyword, verbatim, original script |
| `country_code`, `script` | where, and in what writing system. **Script, not language** — §9 records that no language-ID pass was run, and serving a guessed language would violate rail 5 |
| `attention_volume`, `attention_rank` | from `trends_v2` |
| `domain`, `domain_margin` | closest Atlas parent domain + whitened-e5 margin |
| `noise_class` | the winning negative anchor when it wins (classify, never drop) |
| `coverage_count`, `coverage_samples[]` | corrected-matcher press hits + receipts |
| `divergence` | attention_share − coverage_share for its `(domain, country)` |
| `is_new` | no coverage baseline in the window |
| `press_supply` | headlines Atlas holds for that country/script (context, not a gate) |
| `verify_url` | external search escape hatch — the analyst checks the world, we never claim it |
| `reason_codes[]` | why it ranked / why it was trayed |

Plus a window-level block: `attention_share_by_domain`, `coverage_share_by_domain`,
`tray[]` (everything filtered, with its reason), and `notes[]`.

**No item is ever silently dropped.** The three rule classes and the sub-margin
items go to `tray[]` with a reason code, per the standing no-silent-filtering rail.

### 5.2 Thread enrichment — read-only

Threads gain `public_demand`: the countries whose typed attention matches the
thread's domain and window. **Serving only. It does not enter `rank_threads`
until an A/B measures it.** Atlas law: never flip front-page ordering blind.

---

## 6. Surfaces

Per Pedro, all three, each scoped to its own level:

1. **L1 Country Edition** — a band beside the existing coverage-gap band:
   *"lo que la gente en \<país\> está buscando y Atlas no está cubriendo en
   proporción"*. Trends is per-country by construction, so the data shape matches
   the surface. Median 2 candidates/country/day is a band-sized number.
2. **L1 Brief** — a global section over the same metric, aggregated by domain
   rather than by query (the global roll-up of raw queries re-concentrates on
   big-country noise; the domain roll-up does not).
3. **L2 console** — **restructure the existing PUBLIC ATTENTION + forum-discussion
   sections of `AnomalyPanel` (`AnomalyPanel.tsx:241-317` and `:318+`), not a new
   dock tab.** Those sections already *are* the public-attention surface; today
   they render raw Trends[S]/Wiki[W]/Forum[F] lists. They become the interpreted
   view: each attention item carries its coverage state and divergence, so the
   panel answers "what are people looking at, and is it covered?" instead of
   listing what people looked at. Re-scopes on focus via the existing
   `useFocusRelation` hook.

**Not touched:** the Under-the-Radar dock tab (coverage gaps — separate spec),
the eclipse Brief strip, `/api/v2/attention/eclipse`.

---

## 7. Honesty rails

1. Never assert the press is silent. Measured: 5/5 externally checked assertions
   would have been false.
2. Never assert Atlas is blind from stored-corpus counts alone — that was the
   encoder artifact. Blindness claims require the post-fix corpus.
3. Classify, never drop. Sport, lottery, weather and entertainment are labelled
   and trayed with reason codes, never discarded.
4. The category is a hedged hint (`parent_domain`); only the crisis-vs-noise
   margin is presented as measured.
5. Every item ships a `verify_url`. The analyst checks the world; Atlas reports
   only its own corpus.
6. Not a prediction. 83.7% of silent topics are never covered; nothing in the UI
   may imply early warning.
7. Degraded lanes surface as honest gaps, never as zero.

---

## 8. Dependency and re-measure gates

**Blocking dependency:** the GDELT-lane HTML-entity fix (separate task, in
flight). It changes the corpus this metric is computed on.

After it lands, re-measure before shipping thresholds:

| quantity | today | gate |
|---|---|---|
| corrected silent rate | 25.7–34.6% | recompute on the fixed corpus |
| whitened-e5 margin τ | 0.06 (159 cands / 60 countries) | re-tune to a target band size |
| per-country press supply | pre-fix census | recompute; drives §4.3 work-list |
| signal base rate | 22.5% (n=280) | re-label a sample post-fix |
| near-duplicate collapse | 3.0% at token-jaccard 0.5 | raise the threshold — 0.5 wrongly merges different cities (`previsão do tempo joinville` ↔ `santos`) |

---

## 9. Open questions / not measured

- **Post-fix silence is unknown.** Every number here is pre-fix. The metric's
  shape holds; its thresholds do not.
- **Language ID, not script.** Script is a good proxy only for non-Latin. Turkish
  and Hindi hide inside a 296k-row "latin" bucket, so their supply numbers are
  unreliable. `source_lang` is unusable as primary — 185k of 306k rows are `xx`.
  A language-ID pass is needed and was not run.
- **The wiki top-N cap** (`ingest_wiki.py`, `rank > 25`) has never been tested
  raised. Cheap experiment, would settle whether the ensemble is genuinely
  reachable.
- **`public_demand` in ranking** is deliberately unwired pending an A/B.
- **Bare named entities** (47–55% of queries) carry a large share of true signal
  and are the weakest part of the pipeline. Entity typing (NER + gazetteer, which
  Atlas has) is the obvious next lever and is not in v1.
- The intent-filter base rate and the tray precision are hand-labels by a single
  annotator, not a gold set with inter-annotator agreement.

---

## 10. Provenance

Measured 2026-07-22 on prod, read-only. 7 parallel probes, each adversarially
re-measured by an independent agent instructed to refute it; three probes were
refuted or narrowed, including the session's own opening number. Harnesses:
`sr_probe.py`, `sr_crosslingual_type.py`, `sr_whiten_compare.py`, `sr_lead_lag.py`,
`sr_pipeline.py`. External validation via web search on five candidates.
Full findings: `docs/research/silent-risk/2026-07-22-silent-risk-source-measurement.md`.
