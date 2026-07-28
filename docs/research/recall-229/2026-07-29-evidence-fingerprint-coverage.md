# Evidence fingerprints — build feasibility (M0) and persistence sizing (M4)

**Generated:** 2026-07-28T14:26:15.544499+00:00 · read-only · harness `backend/scripts/measure_evidence_fingerprint.py --coverage --retention`  
**Spec:** `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md` (§2 availability, §3.2 mig 092, §8 budget) · **Plan:** `docs/superpowers/plans/2026-07-28-entity-overlap-identity.md` (T-A1/T-A3)  
**Snapshot measured:** `2026-07-28T03:28:39.196920+00:00` · 2032 clusters · NULL-label rate 0.0 (VALID)

## M0 — can the fingerprint be built, and does it carry anything?

- **24192** `sample_signal_ids` references · **23599** resolved against `signals_v2` = **97.5%**
- **99.1%** of clusters carry at least one lane-E entity · empty-fingerprint rate (no entity, no domain, no URL, no headline key) **0.05%**
- **build wall-clock 11.7s** for the whole snapshot (23599 signals fetched) — budget §8 is ≤120 s: **INSIDE**
- storage **4.9 MB/snapshot** → **146.3 MB at 30-day retention** (budget §8 ≤200 MB: INSIDE)
- **4.7%** of clusters sit at the 24-id `sample_signal_ids` cap, i.e. their fingerprint is a near-complete, not complete, view of membership (spec §2.5)

| lane | per-cluster mean | p5 | p50 | p95 | max | clusters with zero |
|---|---|---|---|---|---|---|
| E entities | 22.76 | 3 | 18 | 57 | 171 | 0.94% |
| U domains | 8.45 | 1 | 8 | 17 | 24 | 0.05% |
| U url_keys | 11.61 | 8 | 10 | 22 | 24 | 0.05% |
| H headline_keys | 8.34 | 0 | 8 | 20 | 24 | 8.32% |

### Lane vocabularies and their document frequency

`df` = number of clusters in this snapshot carrying the item. This is the denominator every rarity gate reads.

| lane | distinct items | df_max | df p50 | df p99 | share at df=1 |
|---|---|---|---|---|---|
| entities | 30680 | 383 | 1 | 9 | 84.1% |
| url_keys | 23593 | 2 | 1 | 1 | 100.0% |
| domains | 3330 | 168 | 2 | 49 | 39.0% |
| headline_keys | 16235 | 23 | 1 | 2 | 98.7% |

> **The rarity-gate degeneracy.** A SHARED item has `df ≥ 2` by construction, so any gate expressed against the *vocabulary* df distribution (median 1; `norm_rarity(2, df_max)` = 0.4987 < 0.5) admits **nothing**. Two of the three pre-registered rarity gates are vacuous on the population they gate. Both are still run and reported in the M1/M2 table; the non-degenerate reading (`df ≤ median of the shared-item df distribution`) and a `df ≤ 2/3/5` ladder are reported beside them, each with its own false-side number. The kill thresholds (K2 = 2%, ≤3 components) are untouched.

### What sits at the top of each df distribution

The highest-df items are exactly what a permissive gate merges on, so they are worth looking at rather than summarising. Two of these are defects, not evidence, and both were found here:

| lane | the ten highest-df items |
|---|---|
| entities | `united states`&nbsp;383 · `donald trump`&nbsp;192 · `white house`&nbsp;109 · `trump`&nbsp;103 · `young`&nbsp;101 · `european union`&nbsp;101 · `x2013`&nbsp;100 · `vladimir putin`&nbsp;96 · `instagram`&nbsp;91 · `iran`&nbsp;87 |
| url_keys | `spiegel.de/politik/ukrainekrieg-eu-verhaengt-neue-sanktionen-gegen-rus`&nbsp;2 · `fox8live.com/2026/07/27/carly-simon-reveals-she-has-been-diagnosed-wit`&nbsp;1 · `richmondandtwickenhamtimes.co.uk/news/national/26413496.carly-simon-re`&nbsp;1 · `chesterstandard.co.uk/news/national/26413496.carly-simon-reveals-diagn`&nbsp;1 · `latimes.com/entertainment-arts/story/2026-07-27/carly-simon-parkinsons`&nbsp;1 · `presstelegram.com/2026/07/27/carly-simon-parkinsons-disease-skin-cance`&nbsp;1 · `delcotimes.com/2026/07/27/carly-simon-has-been-diagnosed-with-parkinso`&nbsp;1 · `cp24.com/news/entertainment/2026/07/27/carly-simon-has-been-diagnosed-`&nbsp;1 · `kmfm.co.uk/news/entertainment/carly-simon-reveals-parkinsons-disease-d`&nbsp;1 · `boston.com/culture/entertainment/2026/07/27/carly-simon-has-been-diagn`&nbsp;1 |
| domains | `inewsgr.com`&nbsp;168 · `rt.com`&nbsp;163 · `indiatimes.com`&nbsp;158 · `thehindu.com`&nbsp;97 · `zazoom.it`&nbsp;97 · `aol.co.uk`&nbsp;88 · `tribunnews.com`&nbsp;86 · `hindustantimes.com`&nbsp;84 · `mail.ru`&nbsp;82 · `topontiki.gr`&nbsp;77 |
| headline_keys | `2026`&nbsp;23 · `23`&nbsp;21 · `5`&nbsp;20 · `100`&nbsp;20 · `24`&nbsp;19 · `27`&nbsp;19 · `22`&nbsp;19 · `21`&nbsp;18 · `3`&nbsp;15 · `blackseanews`&nbsp;15 |

**Finding 1 — lane E carries an HTML-entity artifact.** `x2013` (an en-dash, `&#x2013;`) sits at df 100 in the entity vocabulary: the GDELT `persons[]`/`organizations[]` passthrough is entity-encoded, the same class of bug as #264. It is high-df so the rarity weighting neutralises it, but a permissive gate would merge on a dash.

**Finding 2 — lane H's normalizer collapses masthead-PREFIXED headlines to the outlet name.** `thread_ranking._norm_headline` strips the LAST `|`-separated segment, which is correct for `"<story> | Katherine Times"` and wrong for `"BlackSeaNews | <story>"` — the whole headline becomes `blackseanews` (df 15) or `patrisnews` (df 15). Bare numerals (`2026` df 23, `23` df 21) come from the same shape. This harness reuses the normalizer **verbatim**, as the spec requires, and reports the consequence instead of quietly patching it: a minimum-content guard on headline keys is a lane-H hygiene follow-up, and it is also why lane H's `df_max` is only 23.

### Per-family coverage (the witnesses M1 is scored on)

| family | clusters | refs | resolvable | ent/cluster | dom/cluster | url/cluster | headline/cluster | clusters w/ entity | languages |
|---|---|---|---|---|---|---|---|---|---|
| `GQ-12 caspian` | 9 | 136 | 100.0% | 28.3 | 13.1 | 15.1 | 11.4 | 9/9 | xx 81, en 51, tr 2, ar 2 |
| `berlin pride` | 22 | 257 | 99.6% | 13.8 | 9.5 | 11.6 | 9.5 | 22/22 | xx 205, en 45, ar 4, ro 1 |
| `fresh:paris-knife-attack` | 9 | 146 | 100.0% | 12.0 | 14.1 | 16.2 | 12.1 | 9/9 | xx 112, en 26, fr 3, ar 3 |
| `fresh:russian-missile-strikes-on-kyiv` | 9 | 142 | 99.3% | 20.1 | 9.2 | 15.7 | 8.4 | 9/9 | xx 104, en 33, ru 3, uk 1 |
| `fresh:wildfires-in-france-and-spain` | 8 | 116 | 100.0% | 18.6 | 10.2 | 14.5 | 12.0 | 8/8 | xx 78, en 21, ar 7, es 5 |
| `fresh:wildfires-in-france-and-spain#2` | 7 | 126 | 100.0% | 31.4 | 13.3 | 18.0 | 13.3 | 7/7 | xx 114, en 12 |

Snapshot-wide `source_lang` mix inside resolved sample signals: `{'xx': 14620, 'en': 7488, 'ru': 319, 'pt': 253, 'ar': 191, 'es': 142, 'tr': 136, 'id': 118, 'de': 83, 'uk': 81, 'fr': 64, 'it': 52, 'fa': 18, 'ro': 17}`

## M4 — evidence evaporates; what that costs the staged build

`sample_signal_ids` resolvability against `signals_v2`, by snapshot day. This is spec §2.4's table re-derived as a script.

| snapshot day | clusters | sample refs | resolvable | % resolvable |
|---|---|---|---|---|
| 2026-07-28 | 2032 | 24192 | 23599 | **97.5%** |
| 2026-07-27 | 3475 | 42159 | 34784 | **82.5%** |
| 2026-07-26 | 3593 | 43704 | 30516 | **69.8%** |
| 2026-07-25 | 3854 | 46765 | 27131 | **58.0%** |
| 2026-07-24 | 2395 | 29086 | 13567 | **46.6%** |
| 2026-07-23 | 2190 | 26455 | 8199 | **31.0%** |
| 2026-07-22 | 2517 | 30124 | 4943 | **16.4%** |
| 2026-07-21 | 2369 | 28520 | 0 | **0.0%** |
| 2026-07-20 | 3754 | 45638 | 0 | **0.0%** |
| 2026-07-19 | 1076 | 12840 | 0 | **0.0%** |
| 2026-07-17 | 1966 | 24320 | 0 | **0.0%** |
| 2026-07-16 | 21 | 444 | 0 | **0.0%** |
| 2026-07-15 | 49 | 1067 | 0 | **0.0%** |

- `signals_v2` holds **996878** rows spanning **176.9 h** — the hot window IS the evidence window.
- Days backfillable at ≥80% resolvability: **2**; days with any resolvable evidence at all: **7**.
- Active topics needing an anchor fingerprint for K4's 80% bar: **1165**.
- DP-1's same-snapshot half needs ZERO cold start (evidence is resolvable the night it is written). DP-2 and DP-1's cross-day half need `topic_evidence_fingerprints` on >=80% of active topics (K4); with only the backfillable days above, that coverage is reached by accumulation, not by backfill.

**Consequence for stage ordering (unchanged from the spec, now measured):** Stage 2 (DP-1 same-snapshot) can run tonight — its evidence is resolvable the night it is written. Stage 4 (DP-2 anchor guard) cannot: its anchors are older than the hot window, so it waits for accumulation, exactly as §6 orders it.

## Honest limits

- Lane E is biased toward **Latin-script proper nouns**: entity strings are stored in the source language and are not transliterated, so a Persian and a Romanian report of one event share the *event*, not the *string* (spec §2.5). The per-family language table above is where that bias becomes visible.
- `registrable_domain` uses a **short second-level-suffix list**, not a full public-suffix list; a handful of exotic ccTLDs will land on the wrong registrable name. That inflates domain df slightly (more clusters sharing a coarser domain), which is conservative on the false side.
- `nlp_persons` is noisy (spec §2.5 samples `{"name":"Policía","type":"GPE"}`). No hand-labelled noise floor is applied here — that is M3's job (`calibrate_evidence_rarity.py`, T-A2). Noise inflates the df=1 tail, which cannot create shared items but can distort `df_max`.
- `url_key` **keeps** the query string. The query-stripped variant was measured first and rejected: outlets that carry the article id in the query collapsed their whole output to one pseudo-locator (`shorouknews.com/news/view.aspx` df **35**, `pressorg24.com/news` df 17). Keeping the query costs recall when one link is syndicated with different tracking parameters — an error that can only withhold evidence, never fabricate it. With the query kept, the url_key vocabulary is 100% df=1 and `df_max` is 2, i.e. an exact-URL match is now a genuinely rare event.
- The **GQ-05 family is absent from the per-family table**: its fragments are an offline HDBSCAN rebuild (spec §2.5) and are not rows in `emergent_clusters`, so they have no `sample_signal_ids` to score here. Its coverage is reported inside the reconvergence artifact instead.
- Every number here is **one snapshot, one night** (07-28). The multi-snapshot df distribution, the `nlp_persons` noise floor and the `w_E/w_U/w_H` fit are M3's job (`calibrate_evidence_rarity.py`, T-A2).
