# Gold set extension — 5 EXTERNAL-AGENDA queries (EQ-01..05)

**Date:** 2026-07-29 · **Target:** https://observatory-global.vercel.app (PRODUCTION)
**Rubric:** `docs/research/gold/rubric-v2-ui.md` (v2, rendered-pixels rule)
**Status:** pre-registration written BEFORE any Atlas surface was opened. Browsing log appended below it.

---

## 0. Why these 5 exist (anti-circularity)

GQ-01..20 were authored from Atlas's **own raw `signals_v2` headlines**. That construction guarantees
every gold query is answerable *in principle* — the story is by definition in the corpus. It therefore
**cannot measure the ingestion gap (#235)**: a story Atlas never fetched can never become a gold query,
so the gold set is blind to exactly the failure Pedro most wants measured.

These 5 are authored from **outside the corpus** — my own world knowledge of standing analyst agendas
and of stories that were in motion as of my training horizon and are structurally still running in
late July 2026. Two honesty notes, stated up front because they bound what these queries can prove:

1. **I am not reading a July-2026 wire.** My knowledge horizon is ~May 2026. So I do *not* author these
   from "what happened this week". I author them from **standing agendas** — questions a conflict/OSINT/
   policy analyst would put to any global monitor on any day of 2026, anchored on slow-moving situations
   whose existence does not depend on a specific late-July event. This is the right construction anyway:
   a standing agenda is exactly what a subscriber brings to Atlas, and it is corpus-independent.
2. Consequence: for each query the **ingestion-gap check is mandatory and load-bearing**. "Atlas shows
   nothing" is ambiguous between *the story is quiet this week* and *Atlas cannot see this region*.
   Only a WebSearch against world press separates those. Verdicts are recorded as one of:
   `NOT-INGESTED` (story is live in world press, Atlas empty/thin) ·
   `QUIET` (little world press this window; Atlas emptiness is honest and correct) ·
   `INGESTED` (Atlas has it).

**Mix required by the brief, and how it is satisfied:**

| Requirement | Query |
|---|---|
| ≥2 plausibly under-ingested (regional press / non-English-first / small-country domestic) | EQ-01 (Bolivia, es), EQ-02 (Sahel, fr), EQ-05 (Myanmar, my) — **3** |
| ≥1 supply-chain / economic-security class | EQ-03 (critical minerals / export controls) |
| ≥1 slow-burn (not a spike) | EQ-01 and EQ-04 (both chronic, neither event-driven) |
| ≥1 where the honest answer may be a measured absence | EQ-05 (access-restricted theatre, near-zero foreign press) |
| No reuse of GQ-01..20 topics | verified against `gold-query-set-v1.json` — no overlap of country×theme |

---

## 1. THE FIVE QUERIES (pre-registered, frozen before browsing)

### EQ-01 — Bolivia: fuel and dollar shortage
> **"Bolivia's fuel and dollar shortage — how bad are the diesel queues now, and is the government cutting the fuel subsidy?"**

- **Class:** under-ingested · non-English-first (Spanish) · small-country domestic economics · **slow-burn**
- **Why an analyst asks it:** Bolivia is the textbook slow-motion macro crisis — collapsing gas export
  revenue, dwindling FX reserves, a fuel subsidy the state can no longer finance, and a new government
  that has to touch the third rail. Commodity desks, sovereign-risk analysts and LatAm regional desks
  all carry this as a standing watch item. It never produces a single dramatic spike; it produces a
  grinding sequence of queue photos, subsidy trial balloons and reserve prints.
- **A correct answer needs:** (a) the concrete situation on the ground — queues/shortages, where;
  (b) the policy state — is subsidy reform announced, phased, reversed; (c) **domestic Bolivian outlets**
  in Spanish, not just an English wire summary. Domestic voice is the discriminator here.
- **Expected difficulty:** high. CLAUDE.md's own feed audit says the LatAm RSS lane is roughly one
  flagship per country with zero regional press; Bolivia is not among the named ones.

---

### EQ-02 — Sahel: jihadist pressure on the Malian capital and the AES bloc
> **"Mali and the Sahel — what is the security situation around Bamako, and how is the AES bloc (Mali, Burkina Faso, Niger) holding up after leaving ECOWAS?"**

- **Class:** under-ingested · non-English-first (French + regional West African press) · security
- **Why an analyst asks it:** the Sahel is the single largest theatre of jihadist territorial pressure
  and the AES exit from ECOWAS re-drew West African security architecture. Fuel-supply strangulation of
  the capital is the specific mechanism analysts watch, because it converts rural insurgency into a
  regime-survival question. Conflict researchers, humanitarian planners and energy/logistics desks all
  hold this as standing.
- **A correct answer needs:** (a) the mechanism and status — blockade/convoy attacks/supply into Bamako;
  (b) the bloc-level politics — AES cohesion, ECOWAS relations, external partners; (c) **French-language
  and West African regional sourcing**. An answer built only from English wire copy is a partial answer
  and should be scored as such.
- **Expected difficulty:** high-medium. Atlas ingests some French flagships; the question is whether
  *regional* Sahelian press appears at all, or whether Bamako is seen only through Paris.

---

### EQ-03 — Critical minerals and export controls
> **"Critical minerals and rare earth export controls — who has restricted what, and which industries are exposed?"**

- **Class:** **supply-chain / economic security** · cross-country synthesis · policy
- **Why an analyst asks it:** export licensing on rare earths, gallium/germanium and battery-chain
  inputs is the central instrument of contemporary economic statecraft. It is the question every
  industrial-policy, defence-industrial and automotive-supply-chain analyst carries permanently. It is
  also the hardest *shape* of question for a news-clustering engine: the story is not one event in one
  place, it is a **standing policy régime** whose evidence is scattered across ministries, trade press
  and corporate earnings calls in at least four countries.
- **A correct answer needs:** (a) named restricting jurisdictions and named restricted materials;
  (b) named exposed downstream sectors (magnets → EV/wind/defence); (c) ideally the counter-moves
  (stockpiling, alternative sourcing, WTO/trade responses). Attribution matters: this is a domain where
  state media frame the same measure as routine licensing vs. as coercion.
- **Expected difficulty:** medium. High global press volume, but **structurally diffuse** — this probes
  whether Atlas can hold a *régime* rather than an *event*. A plausible failure mode is a thread that is
  really one company's earnings, or a blob that fuses trade policy with unrelated tariff news.

---

### EQ-04 — H5N1 avian influenza spillover
> **"H5N1 bird flu — where has it spilled into mammals or people recently, and are health authorities changing their risk assessment?"**

- **Class:** **slow-burn** (chronic, non-spiking) · health security · cross-country
- **Why an analyst asks it:** pandemic-preparedness desks, agricultural commodity analysts and health
  ministries all run H5N1 as a permanent background watch. Its defining property for this test is that
  it **almost never spikes** — it is a continuous drip of poultry culls, dairy-herd detections, sporadic
  human cases and periodic risk-assessment language changes. A monitor tuned to volume and acceleration
  is structurally biased against exactly this shape of story, which is why it belongs in this set.
- **A correct answer needs:** (a) specific recent detections with country and host species;
  (b) any **change in official risk language** (the actual signal — WHO/ECDC/CDC/WOAH assessments);
  (c) attribution to health authorities rather than to secondary aggregation.
- **Expected difficulty:** medium-high, and interesting *because* the failure mode is predictable: a
  volume-and-velocity ranker should rank this near zero even when the corpus contains it. If receipts
  exist but no thread does, that is a **1b (informed, not answered)** and it is a clean measurement of
  the ranking bias, not of the ingestion gap.

---

### EQ-05 — Myanmar: Rakhine State humanitarian situation
> **"Myanmar's Rakhine State — what is the humanitarian situation under Arakan Army control, and is anyone reporting from inside?"**

- **Class:** **measured-absence candidate** · under-ingested · non-English-first (Burmese) ·
  access-restricted theatre
- **Why an analyst asks it:** Rakhine combines the three conditions that produce information deserts —
  an active armed non-state administration, a state that restricts journalist access, and famine-risk
  reporting that depends on a handful of exile outlets and UN agencies. It is a live humanitarian file
  for OCHA/WFP planners and a live protection file for Rohingya-focused researchers.
- **A correct answer needs:** (a) the humanitarian facts — food security, displacement, access;
  (b) **who is able to report** — exile Burmese outlets, UN agencies, or nobody;
  (c) crucially, if Atlas has nothing, the *honest* answer is an explicit measured absence, and the
  second half of the question ("is anyone reporting from inside?") means **a well-labelled absence is
  itself substantively responsive**. This query is deliberately constructed so that an honest 1a is
  a genuinely useful analyst output, not a failure.
- **Expected difficulty:** highest. This is the query most likely to return nothing, and the one where
  the *manner* of returning nothing is the whole measurement.

---

## 2. Scoring plan (frozen with the queries)

Per rubric v2: levels 0 / 1a / 1b / 2 / 3, rendered pixels only, mandatory content inventory quoting the
screen, N1 promised-vs-delivered NAV-LOSS tracked independently of level. These 5 are **not controls** —
no K1/K2 kill applies. Added for this run only, and pre-registered here:

> **Ingestion-gap verdict** per query ∈ {NOT-INGESTED, QUIET, INGESTED}, decided by ≤2 min of WebSearch
> against world press when Atlas is empty or thin. Recorded even when Atlas answers well.

---

## 3. RUN LOG

*(appended during browsing — everything above this line was written before the first Atlas request)*

**Environment:** prod `observatory-global.vercel.app`, desktop 1811×2074 viewport, single browser session,
2026-07-29 13:33–13:51 UTC. Console baseline at entry: **175 countries · 94,197 signals**, 12+ global
threads served, tour dismissed. No fixtures, no API shims — every observation below is rendered pixels
or a measured DOM geometry check where clipping was suspected.

---

### EQ-01 — Bolivia fuel and dollar shortage · **LEVEL 1a** · NAV-LOSS · ingestion: **INGESTED**

**Search (full sentence phrasing).** Typing the analyst phrasing `Bolivia fuel dollar shortage subsidy`
returned **no LIVE THREADS segment at all** — only three generated actions ("Open the story for…",
"Go to Bolivia · COUNTRY BRIEF", "Start investigation… · WORKBENCH") plus a disclosure toggle.
Expanding it rendered:

> `Related phrasings: fueldollarshortagesubsidy`

i.e. the matcher had concatenated my four tokens into one string. This is an honest disclosure of a
broken behaviour — the substring matcher cannot handle a multi-token natural question. Re-running with
the bare country name `Bolivia` immediately produced a LIVE THREADS segment and 5+ MEDIA SIGNALS,
confirming the failure is query-shape, not corpus.

**Story panel.** "Open the story" → `POST /api/v2/research/plan` → **429**, rendered as a bare
`RESEARCH PLAN UNAVAILABLE`. Honest in that it claims nothing, but it gives the analyst **no reason** —
"we are rate-limited" and "there is no data" are presented identically. (On a later query the same
panel, un-throttled, rendered a full ledger — see EQ-04 — so this is purely the 429 path.)

**Country brief — CONTENT INVENTORY (quoting the screen).**
- Header re-scoped to `1 countries · 75 signals`; chips `Source Mix 10 / 20% foreign · Atlas Topics 12 ·
  Narrative Threads 0 · Evidence Signals 75`; `75 SIGNALS · -2.2 SENTIMENT · 0 THREADS`.
- Standfirst: *"Bolivia shows 75 signals in this 24h window, led by Public Sector, Police, and Violence
  & Killings. On the people-side layer, public attention is visible around tottenham - sydney and aviación."*
- **VOICE MIX: "80% covered by its own press — 359 of 449 attributable voices are domestic. Loudest
  outsider: AR (26)."**
- **TOP PUBLISHERS: eldeber.com.bo (16) · opinion.com.bo (12) · eju.tv (7) · erbol.com.bo (7) ·
  eldia.com.bo (6)**, "Show all 10 publishers". Five genuine Bolivian domestic outlets.
- RECENT SIGNALS (6 rendered of 75): *Enduro Tropical 2026* (diez.bo) · a street death in La Siberia
  (rosario3.com, an **Argentine** outlet) · *"La gobernabilidad entra en una etapa decisiva"* (eldeber) ·
  *"Bolivia y Perú recuperan la agenda de cooperación portuaria"* (eldeber) · an Armenian embassy item in
  Armenian (aravot.am) · *dinosaur footprints* (timesofindia).
- Honesty chips rendered: `WIKI — No Wikipedia pageview data for this proxy.` · `FORUM UNVERIFIED` ·
  `Narrative threads — No active narratives in this time range` · the people-side proxy caveat in full.
- Trust indicators: `Source Diversity 91 · Source Quality 30 · Volume 0.8x normal (z: -0.5)`.
- KEY SUBJECTS: `pike gomez 2`, `clement alvarez 1`, `dorian medina 1`, … — all 1–2 count, low value.

**Focus re-scoping (protocol step 3).** Verified on screen: map dimmed to a highlighted Bolivia with the
rest of South America greyed; header count `175 → 1 countries`; threads panel replaced by *"No active
narratives in this time range"*; dock relabelled `PUBLIC ATTENTION · BOLIVIA`. All four surfaces
re-scoped correctly.

**NAV-LOSS.** The `Bolivia` search rendered a MEDIA SIGNALS list containing
*"Ex-ministro da Bolívia é preso por compra de gasolina que danificou mais de 30 mil veículos"*
(globo.com) — **the only fuel-related receipt Atlas surfaced anywhere in this query**. Opening the
offered destination ("Go to Bolivia") replaced the list with six different receipts and **dropped that
item entirely**. Promised: 1 fuel-relevant receipt. Delivered: 0. Tagged `NAV-LOSS`.

**Blob flag.** The `Bolivia` search listed under **LIVE THREADS**:
*"Iran Strikes US Sites in Bahrain, Jordan; Ukraine, Kenya, Saudi Deal — 14,734 signals · Armed conflict
escalation"* — a five-country fusion offered as a thread result for a Bolivia query. Counted as 1 blob.

**Ingestion-gap check.** WebSearch confirms the story is major and live: dollar rationing with a
parallel market ~20% off the official rate, gas-export collapse, a **December 2025 decree ending fuel
subsidies**, nationwide queues throttling trucking/farming/mining, and a Wikipedia article
*"2026 Bolivian protests"*. **Verdict: INGESTED** — the feeds are present and healthy (80% self-voice is
among the best I saw), one fuel receipt is retrievable by search, but the country's single biggest story
never reaches a thread and never reaches the brief's rendered receipts.

**Score 1a.** No thread; the absence is stated plainly and repeatedly; raw material is labelled; nothing
misleading is asserted. Not 1b — the six rendered receipts (a motorbike race, a dinosaur, a road death)
do not substantively answer the question.

---

### EQ-02 — Mali / Sahel security and the AES bloc · **LEVEL 1b** · severe NAV-LOSS · ingestion: **INGESTED**

**Search.** `Mali Bamako Sahel` → no LIVE THREADS segment, but a `COUNTRIES: ML Mali` hit and a
**substantial, on-topic, French-language MEDIA SIGNALS list**:

| Receipt (as rendered) | Outlet |
|---|---|
| *"US Weighs Military Action in Mali as Sahel Insurgency Enters Dangerous New Phase"* | slguardian.org |
| *"Éventuelle intervention militaire contre les groupes terroristes dans le Sahel : Le Mali n'est ni demandeur ni preneur d'une opération militaire américaine contre-productive"* | **bamada.net** |
| *"Rapport 2026 de l'ACLED : L'or, la cible stratégique des groupes armés au Sahel"* | **bamada.net** |
| *"Terrorisme au Sahel : Le Président Diomaye réaffirme son soutien sécuritaire à Assimi Goïta après l'attaque meurtrière au Mali"* | **dakaractu.com** |
| *"Diomaye à Bamako 24 heures pour renouer les fils du dialogue sahélien"* | **dakaractu.com** |
| *"Sahel : Birgitte Markussen chargée d'appliquer la nouvelle approche de l'UE"* | **journaldumali.com** |
| *"Russian-Made Shahed-136 Drones Hit Africa's Sahel Conflict"* | riotimesonline.com |

Read together these **do answer the question**: the US is weighing military action, Bamako publicly
refuses it as "contre-productive", Senegal's Diomaye is running shuttle diplomacy to Bamako in support of
Goïta, the EU has a new Sahel envoy, and ACLED frames gold as the armed groups' strategic target.
That is a real situational read, in the region's own language, from the region's own press.

**Country brief — CONTENT INVENTORY.**
- `1 countries · 68 signals`; `Source Mix 15 / 51% foreign · Narrative Threads 0 · Evidence Signals 68`;
  `-1.0 SENTIMENT · 0 THREADS`.
- Standfirst: *"Mali shows 68 signals in this 24h window, led by **Terrorism, Ethnicity: Mali, and Crisis
  Event**. Public-attention proxies are quiet or unavailable for this country in the current window."*
  — the topic mix is correct.
- **VOICE MIX: "49% covered by its own press — 131 of 267 attributable voices are domestic. Loudest
  outsider: DE (19)."**
- **TOP PUBLISHERS: bamada.net (17) · maliactu.net (6) · dw.com ⟨MAJOR⟩ (4) · malijet.com (3) ·
  studiotamani.org (3)**, 15 total. Four genuinely Malian outlets incl. Studio Tamani.
- **KEY SUBJECTS: `Bassirou Diomaye Faye 7` · `Diomaye Faye 3` · `Assimi Goïta 3` · `sadio camara 1` ·
  `Sahel Insurgency 1`** — the correct principals, including the defence minister. Mixed with noise
  (`le figaro`, `jewel crown`, `indian a faladie`).
- Honesty chips: `SEARCH — No Google Trends data for this window.` · `WIKI — No Wikipedia pageview data
  for this proxy.` · `FORUM UNVERIFIED` · `No active narratives in this time range`.
- RECENT SIGNALS (6 rendered of 68): *"Mali: Amnesty dénonce des «crimes de guerre» après l'exécution de
  soldats «hors de combat»"* (dakaractu) ✅ · *"Oumar Coulibaly, une figure du personal branding"* ❌ ·
  *"30 briques de chanvre indien saisies"* ❌ · *"Première session ordinaire du tribunal militaire de
  Kayes"* ~ · *"«Alger et Bamako ne sont pas ennemis»"* (Tebboune) ✅ · **"PSG, Barça : on sait quand
  Ferran Torres prendra sa décision"** ❌ football.

**NAV-LOSS — the severest of the five.** The search surface rendered **seven directly on-topic
security/diplomacy receipts**. The destination it offered rendered **none of them**, substituting a
football transfer rumour and a cannabis seizure. The country panel's own KEY SUBJECTS still names
Diomaye Faye, Assimi Goïta and Sadio Camara — so the surface *knows* the story at entity level while its
receipts do not show it. Promised 7, delivered 0. `NAV-LOSS`.

**Ingestion-gap check.** WebSearch confirms and enriches: **JNIM's fuel blockade of Bamako in place
since September 2025**; coordinated 25 April attacks across Bamako, Kati, Gao, Mopti, Sévaré; **Defence
Minister Gen. Sadio Camara killed by a suicide VBIED at Kati**; the US administration weighing strikes on
JNIM; FM Abdoulaye Diop not ruling out US cooperation subject to sovereignty; AES formed 2023, ECOWAS
exit January 2025. **Verdict: INGESTED** — francophone West African regional press is genuinely present
(bamada.net, maliactu.net, malijet.com, studiotamani.org, dakaractu.com, journaldumali.com, lesahel.org).
My pre-registered "under-ingested" expectation is **refuted**.

**Score 1b.** No thread, but rendered receipts substantively answer the question — credited to *informed
rate*, not *answered rate*, exactly as the rubric intends.

---

### EQ-03 — Critical minerals / rare-earth export controls · **LEVEL 0** · NAV-LOSS · ingestion: **INGESTED**

This query produced the run's strongest and most actionable defect.

**Search, analyst phrasing `rare earth export controls`.** The LIVE THREADS segment returned **six
threads, all about earthquakes**:

| Thread offered | Signals | Category |
|---|---|---|
| Severe weather and earthquake hit Japan and Brazil | 283 | Earthquake or volcanic disaster |
| Daily Earthquake Updates | 280 | Earthquake or volcanic disaster |
| Earthquake Reports Indonesia | 239 | Earthquake or volcanic disaster |
| Mexico Earthquake Tsunami Warning | 164 | Earthquake or volcanic disaster |
| Earthquake in Elazığ | 43 | Earthquake or volcanic disaster |
| Earthquakes No Tsunami Risk | 18 | Earthquake or volcanic disaster |

The substring matcher matched **"earth"** inside **"earthquake"**. In the DOM each row carries the G5
degradation label — the full string is `283 signals · Earthquake or volcanic disaster · partial match`.

**But it is not on screen.** Suspecting clipping, I measured the rendered geometry rather than trusting
the DOM:

```
clientWidth 63 · scrollWidth 271 · truncated true · pctVisible 23%
clientWidth 70 · scrollWidth 271 · truncated true · pctVisible 26%
clientWidth 70 · scrollWidth 271 · truncated true · pctVisible 26%
   (computed style: text-overflow: ellipsis)
```

**Only 23–26% of the string renders.** The visible text is `283 signal…`; the words **"partial match" are
clipped off-screen on every row**. Confirmed independently in the screenshot, where the rows read
`Severe weather and… 283 signa…`. Per rubric v2's D5-pixels rule — *"a chip in JSON but not on screen
scores as absent"* — the degraded-match disclosure is **absent as rendered**.

This is the decisive product finding: **the shipped G5 degraded-search honesty fix is defeated by CSS
truncation in the search dropdown.** The flag is computed, serialized and inserted into the DOM, then
placed at the tail of a 271px string inside a 63–70px box. What the analyst actually sees is six
confident, high-volume threads offered as results for "rare earth export controls", with no warning.

**Alternate phrasing `critical minerals`** degrades honestly instead: **no LIVE THREADS at all**, only
MEDIA SIGNALS — *Sidney Resources' $222.7M Idaho critical-minerals mill* · *Hudbay Minerals Q2 results* ·
**"Rare minerals go on display at Brantwood House, Coniston"** (a museum exhibit, matched on "minerals")
×2 · *Morocco Strategic Minerals* assay results ×3 (**the same release syndicated across
juniorminingnetwork, leaderpost and finanznachrichten**) · *"Africa's critical minerals take centre stage
in Ghana"* · **"Trump's critical minerals push faces U.S. supply shortfall"** ×2. On its own this
phrasing would score **1a**.

Also captured, from the first phrasing's MEDIA SIGNALS:
**"China slaps export controls on 14 EU entities in retaliation for Russia-related sanctions"**
(naharnet.com) — which WebSearch confirms is *exactly* the live July-2026 story (MOFCOM banning dual-use
shipments to 14 EU companies, amid the most stringent rare-earth/magnet controls yet and ~$2.9bn of US
funding committed 2–26 June to build a non-China magnet chain). **Atlas had the right receipt and buried
it at position 3 of a noise-dominated list, under a thread lane offering earthquakes.**

**Verdict: INGESTED.** The material is in the corpus; retrieval and threading fail it.

**NAV-LOSS.** Promised 6 threads; all six are off-topic, so 100% of the promised thread affordance is
unusable. Tagged.

**Score 0.** Rubric level 0 covers *"a confidently-presented wrong thread … or a degraded state that does
not say so"*. Six wrong threads are presented and, as rendered, the state does not say so. I record the
mitigation explicitly: the disclosure **is** implemented and would score 1a if it were visible, and the
same threads self-flag correctly at their own detail page (see the coda). The defect is one CSS rule
deep, not an architectural failure — which is what makes it worth fixing immediately.

---

### EQ-04 — H5N1 avian influenza · **LEVEL 1b** · NAV-LOSS · ingestion: **INGESTED**

**Search `bird flu H5N1`.** LIVE THREADS returned two, both wrong, both with the disclosure clipped:
- **"Zapatero Denies Influence" — 55 signals · `Football / Player Feuds` · partial match** — matched
  **"flu"** inside **"in·flu·ence"**.
- **"Shabana Azmi Swine Flu" — 17 signals · Disease outbreak · partial match** — right disease family,
  wrong virus, an actress health story.

**MEDIA SIGNALS, by contrast, are excellent** — 12 receipts, all genuinely H5N1, in **four languages**:
*"H5N1 spreading locally in Australian native birds"* (thepoultrysite) · Thai *"เซาท์ออสเตรเลียพบสัตว์ปีกต้องสงสัยติดเชื้อ
H5N1 เพิ่ม 11 ราย"* (ryt9.com) · Hindi *"ऑस्ट्रेलिया में एच5एन1 बर्ड फ्लू के सात नए संदिग्ध मामले"* (deshbandhu.co.in) ·
Indonesian *"7 kasus suspek baru flu burung H5N1…"* (antaranews) · *"South Australia reports spike in H5N1
bird flu cases —Xinhua"* (english.news.cn) · thestar.com.my · en.tempo.co · newkerala · prokerala ·
bignewsnetwork · **"Australia confirms fourth case of H5N1 in Queensland"** (thepoultrysite).

Two problems inside that strength:
1. **Syndication:** at least 8 of the 12 are the *same Xinhua wire* about "7 new suspected cases in South
   Australia", re-published across Malaysia, India, Indonesia, Thailand and three aggregators. Twelve
   receipts, roughly three stories.
2. **No state-media marking.** `english.news.cn` (Xinhua) renders with a plain category chip
   (`· Minister`, `· Authorities`) and **no ⚑ STATE marker** in the search dropdown, twice.

**Story panel — the honesty high-water mark of the run.** Un-throttled this time
(`/api/v2/research/plan → 200`), it rendered:

```
STORY · bird flu H5N1
GAP   Thread lane unavailable (TimeoutError); coverage unknown.                          THREAD   0.12
GAP   Semantic signal headline unavailable (ann_timeout).
      This is a failed lookup, not a measured absence.                                   SEMANTIC 0.12
▸ ARCHIVE ACTIVITY · TIME TRAVEL
▾ LOW-CONFIDENCE CANDIDATES — ALL ACCESSIBLE (144)
146 CANDIDATES EVALUATED · 2 PRIMARY · 144 LOW CONFIDENCE · 146 ACCESSIBLE ·
PARTIAL LEDGER · LANE DEGRADATION DISCLOSED
```

The named `ann_timeout` degradation and the sentence **"This is a failed lookup, not a measured absence"**
are exactly the rail the project set out to build, rendered verbatim, and the ledger reconciles
(146 = 2 + 144). The cost is that the analyst receives **zero content** from this panel.

**A precise instrument, found by expanding the tray.** The 144 candidates, all tagged `WEAK`:

| Candidate | Semantic | Investigative |
|---|---|---|
| Disease outbreak | **0.82** | 0.34 |
| Financial Market Updates and Stock Movements | **0.84** | 0.30 |
| **Tax Evasion in Private Schools** | **0.84** | 0.29 |
| Iran Strikes US Sites in Bahrain, Jordan… | 0.84 | 0.29 |
| Daily Earthquake Updates | 0.83 | 0.28 |
| West Nile Virus Detected | 0.84 | 0.28 |
| Michigan Cyclosporiasis Outbreak | 0.83 | 0.27 |
| Andhra Pradesh Covid-19 Cases | 0.82 | 0.25 |

For the query *bird flu H5N1*, **"Tax Evasion in Private Schools" scores semantic 0.84 while "Disease
outbreak" scores 0.82.** The entire 144-candidate field sits in a **0.02 band (0.82–0.84)**. This is the
e5 compression pathology made visible in the product: at thread-centroid granularity the semantic lane is
**non-discriminative and locally inverted**, and all usable ordering comes from the investigative score.
It also confirms the EQ-04 hypothesis exactly: **no H5N1 thread exists** despite 12 corpus receipts — the
nearest health threads are West Nile, Cyclosporiasis and Covid.

**NAV-LOSS.** Search promised 12 on-topic receipts; the primary "Open the story" destination delivered
0 of them and 144 unrelated candidates instead. Tagged.

**Ingestion-gap check.** WebSearch confirms: on **28 July 2026 H5 was confirmed in seven greater crested
terns** in South Australia (Cape Jaffa, Southend, Port MacDonnell), **27 confirmed detections in wild
seabirds** nationally, **no poultry/agriculture detections**, human risk assessed **low**. Atlas's
receipts track this accurately (the "7" matches), though several wire copies frame the terns as
*poultry* (`สัตว์ปีก`), a wire-side imprecision Atlas inherits. **Verdict: INGESTED.**

**Score 1b.** The rendered receipts answer the *"where has it spilled"* half with specific, attributed
numbers (7 new suspected in South Australia, 4th Queensland case, local spread in native birds). The
*"are authorities changing their risk assessment"* half is unanswered, and coverage is Australia-only.

---

### EQ-05 — Myanmar / Rakhine · **LEVEL 1a** · NAV-LOSS · ingestion: **NOT-INGESTED**

**Search `Rakhine Arakan Army Myanmar`.** No threads. Exactly **two** MEDIA SIGNALS:
- *"Wei Hsueh-Kang: United Wa State Army's U.S.-Sanctioned Chinese Warlord in Myanmar"* (jamestown.org)
- **"Arakan Army Holds Virtual Summit with Opposition Steering Council Amid Myanmar Junta Outreach to
  Major EAOs"** (**bnionline.net** — Burma News International, an exile network)

One genuinely on-topic receipt, and it concerns AA politics, not the humanitarian file.

**Country brief — CONTENT INVENTORY.**
- `1 countries · **19 signals**` — vs Bolivia 75 and Mali 68. `Source Mix 14 / **84% foreign** ·
  Narrative Threads 0 · Evidence Signals 19`; `-3.3 SENTIMENT` carrying a **`LIMITED`** chip (honest
  low-n flag); `0 THREADS`.
- **VOICE MIX: "16% covered by its own press — 9 of 58 attributable voices are domestic. Loudest
  outsider: CN (6)."** The information-desert number, rendered.
- **TOP PUBLISHERS: `reddit/r/myanmar` (5) · myanmar-now.org (2) · manilatimes.net (1) ·
  taipeitimes.com (1) · kotaradio.com (1)** — the single largest "publisher" for Myanmar is a **Reddit
  forum**. Genuine Burmese outlets present but tiny: myanmar-now.org, karennews.org.
- RECENT SIGNALS (6): the cyberscam bill ×3 (manilatimes / taipeitimes / kotaradio — syndicated) ·
  *"Telecom Scam Operations Relocate to Three Pagoda Pass"* (karennews.org) · the UWSA warlord profile ·
  a Spanish colour piece (clarin.com). **Zero Rakhine, zero humanitarian, zero displacement.**
- KEY SUBJECTS: `min aung hlaing 2` · `suu kyi 1` · `amy pope 1` (IOM) · `shwe kokko 1` ·
  `Wei Hsueh-Kang 1`, plus Reddit-title noise (`Respectful Debate-`, `Chin Hakha Muslims`).
- FORUM UNVERIFIED carries a **Rohingya item dated today**: *"Anwar says Myanmar agrees to take in 5,000
  Rohingya refugees … (July 29)"* — correctly labelled unverified, correctly not treated as evidence.
- Public attention: `မြန်မာ` #1, **`spider man brand new day` #2**, `သတင်း` #3, `moon geun young` #4.

**Focus re-scoping.** Verified: map dimmed to a highlighted Myanmar, header `1 countries · 19 signals`,
threads *"No active narratives in this time range"*, dock `PUBLIC ATTENTION · MYANMAR`.

**NAV-LOSS.** The one on-topic receipt (bnionline.net Arakan Army summit) did not survive into the
country brief. Promised 1, delivered 0.

**Ingestion-gap check.** WebSearch confirms a major, live humanitarian file: **over 2 million people in
Rakhine threatened with starvation**, 15M+ facing acute food insecurity nationally, a **junta blockade on
nearly all humanitarian aid since November 2023**, Arakan Army restrictions on livelihoods and
agriculture, **400,000+ IDPs in Rakhine and southern Chin**, **150,000+ Rohingya fled to Bangladesh**,
with HRW's World Report 2026 and a Genocide Watch 2026 emergency designation.
**Verdict: NOT-INGESTED** — this is the one clean #235 hit of the five.

**Score 1a — and the best-handled absence of the run.** The humanitarian question is unanswered, but the
query's second half (*"is anyone reporting from inside?"*) is genuinely answered by rendered measurement:
**16% self-voice, 9 of 58 attributable, 84% foreign, top publisher a Reddit forum, LIMITED sentiment
chip**. This is precisely the pre-registered case where an honest absence is itself a useful analyst
output, and Atlas delivers that half well. Nothing is fabricated; every gap is named.

---

### Coda — is the destination surface at fault? No.

Because no external query produced an on-topic thread, the thread-detail surface was never reached
on-query. To establish whether that is a retrieval failure or a rendering failure, I opened
**"Daily Earthquake Updates"** — one of the six threads wrongly offered for EQ-03 — directly:

> `Daily Earthquake Updates` **LABEL UNDER REVIEW** · **RESURRECTED**
> Global · 280 signals · Last 24h · active since Jul 16 · **HOT WINDOW**
> **⚠ This thread's coverage does not cohere — it likely conflates unrelated stories. Verify before
> pinning. — coherence 0.49**
> *"Signal labeled 'Daily Earthquake Updates' shows mixed content including earthquake queries, weather
> disruptions, and ferry cancellations across Turkey, Indonesia, and Spain…"*
> *"Signal is not a coherent story; it aggregates earthquake searches with unrelated weather and transport
> disruptions."*
> **"68 of 280 signals are geo-attributed — cards cover only those"**
> Country cards: Turkey 28 (41%, −2.1) · Indonesia 15 · Libya 8 · Spain 8 · Venezuela 8 · Mexico 1 `THIN`
> `PUBLIC ATTENTION · THIS THREAD` / `DISCUSSION · UNVERIFIED` · Activity Timeline (Volume · Subjects ·
> Voice mix · Tone)

The detail surface is **strong and self-critical**: it flags its own incoherence, publishes the
coherence score, explains the fusion in prose, discloses the geo-attribution denominator, and marks a
thin country. **The destination is not the problem.** Every failure in this run is upstream — retrieval,
threading, and one CSS truncation.

*(Caveat on the same page: the attached `DISCUSSION · UNVERIFIED` items score 90–92% while being about
Trump/Iran talks, a Turkish narcotics operation and the Fed — the discussion-attach noise class, still
live, though correctly fenced as unverified.)*

---

## 4. SUMMARY TABLE

| ID | Query | Level | Answered | Informed | Honest | NAV-LOSS | Ingestion verdict |
|---|---|:--:|:--:|:--:|:--:|:--:|---|
| EQ-01 | Bolivia fuel & dollar shortage | **1a** | ✗ | ✗ | ✓ | ✓ | **INGESTED** (threading fails) |
| EQ-02 | Mali / Sahel security & AES | **1b** | ✗ | **✓** | ✓ | ✓ *(severe)* | **INGESTED** (refutes pre-reg) |
| EQ-03 | Rare-earth / critical-mineral export controls | **0** | ✗ | ✗ | **✗** | ✓ | **INGESTED** (retrieval fails) |
| EQ-04 | H5N1 avian influenza | **1b** | ✗ | **✓** | ✓ | ✓ | **INGESTED** |
| EQ-05 | Myanmar / Rakhine humanitarian | **1a** | ✗ | ✗ | ✓ | ✓ | **NOT-INGESTED** |

**Metrics (n=5, external-agenda arm; no controls, so no K1/K2 applies):**
- **Answered rate (≥2): 0/5 = 0%** — no external query produced an on-topic thread whose rendered content
  answered it.
- **Informed rate (≥1b): 2/5 = 40%** — EQ-02 and EQ-04 are answerable from rendered receipts alone.
- **Honesty rate: 4/5 = 80%** — four failures are honest floors; EQ-03 is the single misleading one, and
  only because a rendered disclosure is clipped.
- **NAV-LOSS: 5/5 (100%)** — every query lost promised material between search and destination.
- **Blob-flags observed: 3** (Iran-Strikes 14,734 offered for "Bolivia"; 6 earthquake threads for
  "rare earth"; 2 flu-substring threads) — all three *carry* a degraded/coherence flag somewhere in the
  system; the two in the search dropdown render it clipped.

**Comparison to the internal arm.** The 20-query internal set measured a 7–14% answer rate. This external
arm measures **0% answered / 40% informed**. The gap is the anti-circularity premium: queries drawn from
Atlas's own headlines are guaranteed to have a corpus story behind them; standing analyst agendas are not.

---

## 5. #235 IMPLICATIONS — where the misses actually point

**The headline result inverts the pre-registration.** I expected 3 of 5 to fail on ingestion. **Four of
five failed with the material already in the corpus.** Feed coverage is materially better than the
CLAUDE.md feed audit implies:

| Region | Domestic/regional outlets observed live | Self-voice |
|---|---|---|
| Bolivia | eldeber.com.bo, opinion.com.bo, eju.tv, erbol.com.bo, eldia.com.bo (+5 more) | **80%** |
| Francophone West Africa | bamada.net, maliactu.net, malijet.com, studiotamani.org, dakaractu.com, journaldumali.com, lesahel.org | **49%** |
| Myanmar | myanmar-now.org, karennews.org, bnionline.net, r/myanmar | **16%** |

So **#235 should be re-scoped, not merely continued.** Three concrete implications:

1. **The binding constraint is threading, not ingestion.** Bolivia has 5 domestic outlets, 80% self-voice,
   a national fuel/subsidy crisis with street protests — and **0 threads**. Mali has the correct topic mix
   (*Terrorism, Crisis Event*), the correct principals (Goïta, Diomaye Faye, Sadio Camara) and 68 signals —
   and **0 threads**. At 19–75 signals/24h a country simply cannot clear the clustering floor, so
   **every small and mid-sized country is structurally thread-less regardless of feed quality.** Adding
   feeds to these countries will not produce threads; it will produce more unthreaded receipts. This is
   the same finding the internal arm reached from the other direction (argmax dispersion, 43/54
   Berlin-Pride fragments), now confirmed at the country scale.

2. **The one true ingestion gap is access-restricted theatres.** Myanmar/Rakhine is the clean miss:
   19 signals/24h, 84% foreign, the top publisher a Reddit forum, and **zero receipts** on a file where
   2M people face starvation and 400k are displaced. The feeds that would close it are exile and
   ethnic-media outlets — myanmar-now.org and karennews.org are *already ingested but at 1–2 signals/day*,
   which suggests a **fetch-depth/cadence problem on low-volume feeds rather than a missing-feed problem**.
   Companion candidates in the same class: DVB, Irrawaddy, Mizzima, Narinjara (Rakhine-specific), plus
   UN OCHA/WFP situation reports — the last being the systematic fix for humanitarian files, since
   agency reporting is precisely what substitutes for press in an access desert.

3. **Retrieval is now a larger loss than ingestion.** EQ-03 had the exactly-right receipt in the corpus
   ("China slaps export controls on 14 EU entities") and served earthquakes instead. EQ-02 had seven
   right receipts and served a football transfer. A feed-expansion programme cannot fix either. The
   priority order that this run supports is: **(a) un-clip the degraded chip, (b) fix the multi-token
   matcher, (c) carry search receipts into the destination, (d) lower the threading floor for thin
   countries, (e) then extend feeds — starting with access-restricted theatres and agency reporting.**

**A note for the gold-set programme itself.** These 5 did what they were built to do: the internal set
could not have produced EQ-05 (Atlas has no Rakhine headlines to derive a query from) and would not have
produced EQ-03's clipping defect (the internal queries match real threads, so the degraded path is rarely
exercised). Recommend the external arm becomes a standing minority share of every gold run, and that
**"receipts promised by search vs. receipts delivered at the destination"** be promoted to a first-class
measured metric — it fired on 5/5 here.

