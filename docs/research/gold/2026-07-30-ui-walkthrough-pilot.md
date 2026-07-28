# UI-WALKTHROUGH EVAL PILOT — 6 gold queries clicked, not curled

**Date:** 2026-07-30 · **Branch:** `eclipse-dramatic-moment` · **Surface:** real UI at
`localhost:3000/app` (dev server, PROD data) · **Method:** analyst persona, search bar first,
follow what Atlas offers, ~8 min cap per query.
**Baseline compared against:** `docs/research/gold/2026-07-28-gold-query-eval.jsonl` (frozen API
retrieval protocol R1–R4).
**Rubric:** unchanged — `docs/research/gold/2026-07-27-gold-query-set-v1.md` §2–§4, plus each
query's own `pass_criteria` from `gold-query-set-v1.json`.

> **Why this run exists.** The API harness's own biggest caveat is *"candidate selection is mine,
> not Atlas's."* This run lets **Atlas** select the candidates, through the surfaces it actually
> ships — search dropdown, thread detail, country brief, voice mix. Divergence in either
> direction is the finding.

---

## Summary table

| Query | API score | UI score | Divergence | One-line why |
|---|---|---|---|---|
| **GQ-01** wildfires FR/ES | 2 | **2** | SAME | Same level, different texture: UI receipts carry each evacuation figure with its own outlet + timestamp, but the event is split across **8 near-duplicate threads**. |
| **GQ-02** Berlin Pride | 0 | **2** | **UI-BETTER** | Search returns **5 dedicated Berlin Pride threads**; the API protocol landed on *"Klopp Appointed Germany Coach"*. |
| **GQ-05** Colombia embassies | 0 | **1** | **UI-BETTER** | Honest floor: country brief says *"No active narratives"*, and media signals serve the real story — but in EN/FR/PT, **zero Colombian outlets**. |
| **GQ-08** Indonesia BI governor | 0 | **1** | **UI-BETTER** | No thread exists and Atlas says so (`partial match` tags); 11/12 media signals answer both strands in Indonesian. |
| **GQ-14** Congo Ebola asymmetry | 0 | **0** | SAME (worse failure mode) | Right thread found, but it is a **3-story blob** (French-Embassy bomb threat + Ebola + Le Pen hack) hidden behind an invisible country filter that renders it blank. |
| **GQ-20** Iranian opinion *(control)* | 0 → pass | **1** → pass | **UI-BETTER** | Honest floor with explicit labels; the proxy panel states *"not a population-normalized opinion poll"* verbatim. No opinion claim anywhere. |

**Real arm (5 items).** Answer rate: API `1/5 = 20%` → UI `2/5 = 40%`.
**Honesty rate** (`#1 / (#1 + #0)`): API `0/4 = 0.00` → UI `2/3 = 0.67`.
The honesty delta is larger than the answer-rate delta and is the more important number.

**Control arm (1 item).** GQ-20 UI = 1 → passes its own `pass_criteria` (`level ≤1`).
⚠ **But `mean(negative controls) = 1.0` trips pre-registered kill K1 (`≥1.0 ⇒ run VOID`).** With
n=1 control this is not a verdict on Atlas — it is a **rubric contradiction** surfaced by the
pilot: GQ-20's own criteria *permit* a 1, while K1 voids any run whose controls average 1.0. A
full UI run must carry all 6 controls, and K1's threshold needs re-stating, before any UI answer
rate is publishable. **See "Rubric defects" below.**

---

## Per-query walkthroughs

### GQ-01 — Wildfires in France and Spain · API 2 → UI 2 · SAME

**Click path.** Search `wildfires France Spain` → dropdown auto-scopes (*"Filtering to: France"*)
→ opens **LIVE THREADS ×6** + **MEDIA SIGNALS ×12** → clicked the top thread *"Wildfires Worsen
Across Spain and France Amid Heatwave"* → thread detail → expanded **"Show all coverage (105)"**.

**Evidence seen.** First 20 receipts **20/20 on-topic** (`ROR@20 = 1.00`); first off-topic is
receipt 23 (*"Noyades en Normandie : 67 accidents et 18 décès"*). Receipts span en/fr/tr/az across
independent.co.uk, jordantimes.com, cnbc.com, aljazeera.com, franceinfo.fr, 20minutes.fr,
rfi.fr, haberler.com. The divergent figures the criteria demands are all present **and each is
bound to its own outlet + timestamp**: *220 000 évacués / 42 000 ha en Gironde* (estrepublicain,
laprovence, midilibre, rfi, Jul 26), *141 bin kişi tahliye* around Bordeaux (sana.sy, Jul 25),
*116 bin hektar* for the 2026 season (kibrispostasi/adalet.az/haberler, Jul 27), *98 bin hektar*
(milliyet, Jul 25), *330,000* (worldnews@lemmy.ca citing CBC, in the discussion lane).

**Flags Atlas surfaced.** ⚠ *"This thread's coverage does not cohere — it likely conflates
unrelated stories. Verify before pinning."* · `coherence 0.50` · `LABEL UNDER REVIEW` ·
*"105 of 1,528 signals are geo-attributed — cards cover only those"* · voice mix *"41% of
attributable voices are France's own press… 46 of 95 voices carry no outlet origin — excluded
from these ratios, never assumed"* · `⚑ state` chips on france24.com, xinhuanet.com,
jordantimes.com.

**Score 2, not 3.** D1 ✓, D2 ✓, D3 ✓ — but held at 2 by: heavy wire syndication (*"France,
Spain battle 'monster' wildfires"* verbatim across jordantimes / channelnewsasia /
thejakartapost / koreaherald / freemalaysiatoday / aljazeera = 6 of the first 16 receipts, one
wire counted as six); the coherence warning itself; and `1 COUNTRIES` because the search silently
scoped to France, so the *Spain* half of the question survives only inside headline text.

**Divergence note.** The API verdict was *"collapses evacuation numbers without attribution."* In
the UI they are **not collapsed at all** — the receipt list is the attribution. But the UI reveals
something the API run could not see: **the fire complex is fragmented across ≥8 live threads**
(1,528 / 1,056 / 857 / 749 / 508 / 92 / 64 / 51 signals), including *"Wildfires Rage in Spain and
France, Over 200,000 Evacuated"* mis-categorised as **"Earthquake or volcanic disaster"** and
*"Forest fires"* whose country chips read **AF / GY**. No surface tells the analyst these are one
story.

---

### GQ-02 — Berlin Pride attack · API 0 → UI 2 · **UI-BETTER** (headline finding)

**Click path.** Search `Berlin Pride attack` → **LIVE THREADS** returns five dedicated threads:
*Berlin Pride Attack: Suspect Profile and Manhunt* (287) · *Berlin Pride Attack Suspect Killed*
(36) · *Berlin Pride Terror Attack* (19) · *Berlin Pride Attack Suspect* (16) · *Berlin Pride Car
Attack* (16). Opened the 287-signal thread → expanded coverage (61-item sample, 27 rendered).

**Evidence seen.** Receipts 1–17 are the event, and they carry the accountability strand the
criteria asks for: *"Islamist terrorist act the attack at Berlin Pride, says German government:
Manhunt for the Lebanese perpetrator"* (sofokleous10.gr) · *"Ποιος είναι ο 21χρονος ύποπτος …
**Σχεδίαζε και παλαιότερα πράξη βίας**"* (had previously planned an act of violence — inewsgr) ·
*"**Γνωστός στις Αρχές** από τη δράση του στον ισλαμιστικό χώρο"* (known to authorities from his
Islamist activity — inewsgr) · ISIS-supporter designation (ertopen.gr).
`ROR@20 = 17/20 = 0.85`. Receipts 18–24 switch to an **Athens grenade plot** against prosecutor
Isidoros Dogiakos; 25–27 to the **Stavros Georgiou murder** — both Greek-crime stories, both
EG-tagged, which is why the header reads *"led by **Egypt (33 signals)**, Germany (17), Greece
(11)"*.

**Score 2.** `ROR@20 0.85 ≥ 0.75` ✓ · D2 ✓ (label describes the 63% majority) · D3 ✓ (≥3 outlets).
G3's numeric triggers do **not** fire (`ROR@all ≈ 0.63 > 0.60`; only one contaminating cluster
exceeds 15%). Held at 2, not 3: zero German outlets on a German story, the Greek-crime tail, and
the Egypt-led geo attribution. Atlas does surface the domestic gap — voice mix reads
**"0% of attributable voices are Germany's own press · THIN · Loudest outsider: Greece (5)"**.

**Why this is the headline.** The API protocol scored this **0** on *"Klopp Appointed Germany
Coach"* (`ROR@20 = 0.0`). The story was in the index the whole time, in five labelled threads, one
keystroke away. **The 07-27→07-28 "GQ-02 vanished" instability is a candidate-selection artifact of
the frozen R1–R4 protocol, not a loss of the story from Atlas.** That single fact changes how the
API number should be read.

---

### GQ-05 — Colombia embassies / Cuba / Nicaragua · API 0 → UI 1 · **UI-BETTER**

**Click path.** Search `Colombia embassies Cuba Nicaragua` → **no LIVE THREADS segment at all**
→ MEDIA SIGNALS ×9 → *"Go to Colombia"* country brief → also tried *"Open the story"*.

**Evidence seen.** On-topic receipts exist and are correct:
*"De la Espriella to close Colombian embassies in 14 countries and cut ties with Cuba and
Nicaragua"* (mercopress.com) · *"Colombie: le président élu annonce qu'il va rompre les relations
diplomatiques avec Cuba et le Nicaragua"* (lenouvelliste.com) · *"Presidente eleito da Colômbia
anuncia rompimento com Cuba e Nicarágua"* (infomoney.com.br) · *"Novo presidente da Colômbia …
E reatará relações com Israel, no dia da posse, 7 de agosto"* (montesclaros.com).

**Country brief (CO).** `831 signals` · **`Narrative Threads: 0`** · *"No active narratives in this
time range"* · voice mix **85% domestic** (2,936 of 3,442 attributable voices) · top publishers
eltiempo.com (92), semana.com (66), lafm.com.co (55), hsbnoticias.com (46), colombia.com (42) ·
key subjects **De la Espriella (18)**, **Abelardo de la Espriella (10)**. Recent signals (6 shown)
are Petro's influence-trafficking scandal, the Japan quake, a motorcycle crash, Barranquilla
weather — **not the embassy story**.

**Score 1 — honest floor (rubric level 1a).** Atlas declares it has nothing, and returns labelled
raw signal with sources. It **fails the pass criteria** exactly as the criteria predicted: the
criteria demands *"a MAJORITY of receipts in Spanish and ≥3 distinct Colombian-origin outlets"*;
what is served is EN/FR/PT from Uruguay/Haiti/Brazil and **zero CO-origin outlets** — while the
country door proves Colombian press is indexed at 85% domestic share. **This is the
English-firehose-buries-non-English ranking failure, made visible.** Not a data gap: the story and
the domestic press are both in the corpus; the ranking never joins them.

**Also observed.** Every on-topic receipt is country-tagged **NI**, including the Colombian and
Brazilian-Portuguese ones. And *"Open the story for …"* returned **`RESEARCH PLAN UNAVAILABLE`** —
network shows `POST /api/v2/research/plan → 429`, **fired twice for one click**.

---

### GQ-08 — Indonesia central bank governor · API 0 → UI 1 · **UI-BETTER**

**Click path.** Search `Indonesia central bank governor rupiah` → LIVE THREADS ×2, **both tagged
`partial match`** → MEDIA SIGNALS ×12.

**Evidence seen.** `11/12` media signals answer the query, in Indonesian, both strands:
*"IHSG & Rupiah Anjlok Usai **Perry Warjiyo Mundur** dari Gubernur BI"* (tribunnews) ·
*"**Penyebab** Perry Warjiyo Mundur dari Gubernur BI Jadi Sorotan, Benarkah Karena Rupiah Tembus
Rp18.000?"* (the *why*) · *"Rupiah Jebol Dekati Rp18.100 per Dolar AS, **Tertekan Isu Gubernur
BI**"* (okezone) · *"Menerka Reaksi Pasar jika **Thomas Djiwandono** Jadi Gubernur BI"*
(succession) · *"**Warisan** Perry Warjiyo Usai Mundur"* (legacy) · *"Rupiah Selasa ditutup
Rp18.083"* (antaranews). One off-topic (*"Aset Tanah Senilai Miliaran Rupiah…"* — matched the
currency word).

**Score 1 — honest floor.** No thread exists for the event, and Atlas **says so**: the two offered
threads carry an explicit **`partial match`** tag (the generic bucket *"Bank Earnings Growth
2026"* — the very thread the API scored 0 on — and *"Donny Ermawan Appointed URI Governor"*,
matched on the word *governor*). Level 2 is unreachable because there is no thread to score; the
pass criteria's *"at least one non-Indonesian analysis piece"* is also unmet (4 distinct outlets,
all ID: tribunnews ×7, okezone ×2, liputan6, antaranews).

**Note for the rubric.** An analyst reading those 11 headlines **has the answer**. The
thread-centric 0–3 scale cannot express "no thread, but the raw lane answered it well", so the UI
is under-credited here by construction. `partial match` is a real honesty affordance with no
counterpart in the API protocol.

---

### GQ-14 — Who covers Congo Ebola in FR/SW vs EN · API 0 → UI 0 · SAME (more dangerous failure)

**Click path.** Search `Congo Ebola` → auto-scope *"Filtering to: DR Congo"* → one thread,
*"Ebola Outbreak Congo"* (254 signals) → opened it → voice-mix panel (the surface built for this
question) → inspected the network calls when the panel came back blank.

**What the analyst sees.** A thread panel reading **`254 signals · 0 COUNTRIES · 0 SOURCES ·
"the current evidence sample spans 0 recent items"`**, and a voice mix stating
**"0% of attributable voices are **France's** own press · THIN · Loudest outsider: Greece (9)"** —
on a **DR Congo** thread. No receipts are rendered at all.

**Root cause (network).** `GET /api/v2/theme/dynamic-topic-239?hours=24&country_code=CD → 200 OK`
with an **empty sample**. The search auto-scope injected `country_code=CD`; the thread has zero
CD-attributed members; the panel renders empty. **There is no country chip in the focus bar** — the
filter is applied invisibly and cannot be seen or cleared.

**What the blank panel was hiding.** Fetching the same thread unscoped returns 43 receipts, and
they are a **three-story blob**:

| receipts | share | story |
|---|---|---|
| 0–13 | 33% | **Bomb threat at the French Embassy in Athens** (skai.gr, enikos.gr, tanea.gr, efsyn.gr…) |
| 14–17, 19–30 | 40% | DR Congo Ebola counts (*"ΛΔ Κονγκό: 3.200 κρούσματα … 1.405 θανατηφόρων"*, in.gr) |
| 31–42 | 28% | **Marine Le Pen / Rassemblement National hacked** (huffingtonpost.gr, skai.gr, naftemporiki.gr) |

`ROR@20 = 4/20 = 0.20` · `ROR@all = 17/43 = 0.40` → **G3 fires hard**. The voice-mix "France /
Greece" line was not stale: it was faithfully describing the French-Embassy-in-Athens cluster.
Atlas's own coherence measure reports **`tier: "tight"`, `score: 0.706`, `warning: null`** on this
— a measurement failure. `label_status: "partial"` *is* set in the payload, which under G3 spares
it a forced 0 — **but the UI renders no chip for it**: no `LABEL UNDER REVIEW` badge in the search
row, no warning banner in the panel.

**Score 0.** The comparative question is unanswered (criteria: answering with a good Ebola thread
and ignoring the asymmetry is *"1 at best"* — here there is no good thread either), the served
panel makes a wrong-country domestic-voice claim, and no defect is flagged anywhere the analyst
can see. Atlas did **not** claim the story is "uncovered" or "silent" in French or Swahili, so the
auto-0 clause in the criteria is not triggered.

**Raw material that did exist, unmeasured.** The media-signals lane showed the asymmetry's raw
shape without measuring it: *"Uganda declares end to latest Ebola outbreak"* repeated **7×** across
Australian Community Media regionals (examiner / northweststar / canberratimes / mandurahmail /
irrigator / queanbeyanage / westernadvocate) — a syndicated **Uganda** story dominating a **Congo**
query — beside `actualite.cd` in French (*"Haut-Uele : les cliniques universitaires d'Isiro dotées
d'un laboratoire de diagnostic d'Ebola"*), africanews.com, luxtimes.lu and a French bluesky post.

---

### GQ-20 — What do ordinary Iranians think · CONTROL · API 0 (pass) → UI 1 (pass)

**Click path.** Search the full question → LIVE THREADS ×2 (*"Russian Cancer Therapy Drug"*,
*"US Strikes on Southern Iran"*), **both tagged `partial match`** → MEDIA SIGNALS ×12 → *"Go to
Iran"* country brief (where a confabulation would most likely appear).

**Evidence seen.** Nothing anywhere asserts what Iranians think. Media signals are press coverage
*of* the ceasefire (diplomacy, markets), including a visible syndication blob — *"US, Iran pause
attacks amid delicate ceasefire talks"* **6×** across Hearst US local stations (wgal, wlwt, ksbw,
wmur, wtae, wxii12). The Iran brief carries the required labelling **verbatim**:

> **PUBLIC ATTENTION** *people-side proxy* — "Google searches and Wikipedia pageviews are
> country/language-edition proxies. They enrich the media picture, but **they are not a
> population-normalized opinion poll**."

Search terms are shown under an explicit `SEARCH` label (خرید ارز دیجیتال, قیمت سکه پارسیان امروز)
— currency/coin prices, not opinion. The forum lane is labelled `FORUM UNVERIFIED`. Sentiment is
`-2.2 Negative` under **SENTIMENT OVERVIEW** with *"Sentiment analysis is noisy and should be
interpreted cautiously"* — framed as coverage tone, never as public opinion. Conflict events carry
*"related by country, not by story · machine-coded, geo approximate"*.

**Score 1 — PASS.** Honest floor with explicit labels; no sentiment presented as opinion, no
"Iranians are divided/supportive/opposed" framing, no inference of mood from IRNA's tone.
**Residual gap:** the criteria's *state-ownership caveat* is **not** stated — `irna.ir` supplies
**485 of Iran's 3,199 signals (15%)** and `arabic.rt.com` 29 more, and the country brief's TOP
PUBLISHERS list renders **no state-media flag**, even though ThemeDetail's TOP SOURCES panel does
render `⚑ state` chips. No VPN caveat either. That keeps it at 1 rather than a labelled-and-caveated
best case — which is the correct outcome for a control.

---

## Top 3 UX findings

**1. Invisible country auto-scope silently empties (and can hide a defect in) thread detail.**
The search dropdown auto-scopes on any country token — *"Filtering to: France / DR Congo /
Colombia / Iran / Indonesia"* — and that scope is passed into the detail fetch
(`/api/v2/theme/{id}?hours=24&country_code=CD`) **without appearing as a clearable focus chip**.
On GQ-14 it turned a 254-signal thread into `0 COUNTRIES · 0 SOURCES · 0 recent items`; on GQ-01 it
reduced a Spain-and-France question to `1 COUNTRIES`. Worse than the blanking is what it conceals:
the same thread served unscoped exposes a three-story over-merge. **The panel does not say "no
receipts for this country" — it just looks broken.** Fixes, in order: render the auto-scope as a
first-class, clearable chip; distinguish *scope-empty* from *no-data* in copy; fall back to the
unscoped sample with a visible "showing global coverage" note.

**2. Category chips on receipts are systematically wrong, on every surface at once.**
Observed live: `mercopress.com · Water` on an embassy-closure story · `surinenglish.com ·
Presidential Actions` on a firefighters dispatch · `lenouvelliste.com · Communist` · `wlwt.com ·
WORLDMAMMALS FOX` on Trump/Netanyahu · `insurancejournal.com · CROP PRODUCTION` on a Fitch
AI-credit-risk story · `rustourismnews.com · Crisis: O Responseagenciesatcrisis` · thread
*"Wildfires Rage in Spain and France, Over 200,000 Evacuated"* filed under **"Earthquake or
volcanic disaster"** · thread *"Ukrainian Drone Attacks Hit Russian Oil; Russia Strikes Odessa"*
filed under **"ELECTION LEGITIMACY DISPUTE"** · *"Indonesian News Roundup: Corruption, Violence,
and Law"* under **"SPORTS & LEGAL"**. Every receipt the analyst reads carries a visibly wrong tag
next to a correct headline. This is the cheapest large trust win available: the taxonomy is wrong
often enough that hiding the chip would raise perceived quality.

**3. One event, many threads — and no surface says so.**
`wildfires France Spain` → **8** live threads for one fire complex (1,528 / 1,056 / 857 / 749 /
508 / 92 / 64 / 51). `Berlin Pride attack` → **5**. The analyst must reconcile counts and
membership by hand, and the ranked list gives no signal that these are the same story. (Note the
inverse pathology sits one query away: GQ-14's single thread fuses **three unrelated** stories.
Over-merge and under-merge are live simultaneously, and the coherence measure calls the 3-story
blob `tight`.)

**Runners-up.**
- **State-media flag is inconsistent across surfaces** — `⚑ state` chips render in ThemeDetail TOP
  SOURCES (france24, xinhuanet, jordantimes) but **not** in CountryBrief TOP PUBLISHERS, where
  `irna.ir` carries 15% of Iran's coverage unflagged. The GQ-20 control's state-ownership caveat
  fails on this alone.
- **`RESEARCH PLAN UNAVAILABLE`** — the flagship natural-language answer surface returned
  `429` and **fires two identical POSTs per click**, burning the rate budget twice as fast. The
  error is honest but does not say *why* (rate-limited vs broken).
- **Compound-focus trap** — clicking *"Go to Colombia"* from the search dropdown while a thread was
  open produced `Country: Colombia + Theme: Berlin Pride`, rendering *"287 signals · 0 SOURCES ·
  tone 0.00"* instead of the country brief.
- **Duplicate request fan-out** — one thread open issued `/drift` **5×**, plus doubles of
  `/discussion`, `/voice`, `/theme`, `/lineage`, `/compare`; `/public-attention` returned `503`.
- Cold `/app` load ~10–13 s to interactive; a React hook-deps console error (non-blocking).

---

## Rubric defects surfaced by running it through the UI

1. **K1 vs GQ-20's own pass criteria contradict each other.** GQ-20 passes at `level ≤1`; K1 voids
   any run with `mean(controls) ≥ 1.0`. A run in which every control performs an *ideal honest
   floor* would therefore be VOID. K1 should key on **≥2** (or on "any control ≥2"), matching K2's
   spirit, or the controls' pass criteria should target 0.
2. **The 0–3 scale is thread-centric and cannot score the raw lane.** GQ-08 is the clean case:
   no thread exists, Atlas honestly says `partial match`, and 11 receipts answer both strands of
   the question. That is materially better than GQ-05's floor and vastly better than a wrong
   thread, yet all three compress toward 0–1. Recommend a level **1+** ("floor that answers"), or
   scoring the raw lane on D1 explicitly.
3. **G9 (preview-vs-membership) needs a UI twin.** The UI's divergence is not list-vs-detail but
   **scoped-vs-unscoped detail** (GQ-14: 0 receipts vs 43). Add a trigger for it.
4. **D5 must be evaluated on rendered pixels, not payload fields.** `label_status: "partial"` was
   present in GQ-14's JSON and invisible in the UI. For a UI run, "flagged" must mean *the analyst
   can see it*, otherwise the UI inherits honesty credit it never delivered.

---

## Verdict: does UI-eval diverge enough to justify all 20?

**Yes — run all 20 through the UI, and treat the API number as a lower bound until it is
re-derived.**

- **4 of 6 diverged**, all in the same direction, and the two that matched (GQ-01, GQ-14) matched
  for *different reasons* than the API recorded.
- The divergence is **not noise, it is mechanism**. GQ-02 proves the frozen R1–R4 candidate
  selection — `/threads` list + token overlap — misses threads that Atlas's own search returns
  first. Five labelled Berlin Pride threads existed while the harness scored the story `0` on a
  Klopp football thread. Every `0` in the API run attributed to "clustering missed it" is now
  suspect and must be re-checked against search before being reported as an engine failure.
- The **honesty rate moves most** (0.00 → 0.67), and honesty is the pre-registered gate (K5) that
  the roadmap treats as outranking answer rate.
- The UI exposes defect classes the API protocol is structurally blind to: event fragmentation,
  wrong category chips, invisible scope filters, cross-surface flag inconsistency, and the
  coherence measure calling a 3-story blob `tight`.

**Conditions before a full UI run is publishable:**
1. **Carry all 6 controls** (GQ-15…GQ-20). With n=1 the control arm cannot support K1/K2, and this
   pilot already sits on K1's boundary.
2. **Fix K1's threshold** (see rubric defect 1) *before* the run, in writing — the pre-registration
   discipline that killed silent-risk applies to this metric too.
3. **Freeze a UI retrieval protocol** the way R1–R4 is frozen, or the metric is unfalsifiable:
   e.g. *U1* type the analyst-natural query in the search bar; *U2* open ≤3 offered LIVE THREADS in
   rank order; *U3* if none, read MEDIA SIGNALS as the floor; *U4* for country-anchored queries open
   the country brief; *U5* for asymmetry queries open voice mix. Log the auto-scope on every step.
4. **Score D5 from rendered UI only** (rubric defect 4), and log the scoped/unscoped receipt delta
   (rubric defect 3).
5. **Budget for the 429** — `/api/v2/research/plan` is the paid bucket at 20/300s and double-fires;
   a 20-query run will exhaust it. Either pace the run or exclude the story panel from scoring and
   record it as unavailable.
6. **Run both arms on the same window.** The value here is the *pair gap* per query (API vs UI),
   not either number alone — the same logic as §5's control pairs.

**Expected cost.** ~10–12 min per query including verification, ≈3.5 h for 20, versus the API
harness's automated run. The pair gap is worth it once; thereafter the cheap standing probe is the
**GQ-02 test** — did the frozen protocol miss a thread that search returns on the first keystroke?

---

*Artifact only. No code, config or engine state was modified. Nothing committed.*
