# UI GOLD EVAL — rubric v2 (content-first) — full-20 run

**Rubric:** `docs/research/gold/rubric-v2-ui.md` (frozen 2026-07-30, content-first, rendered-pixels-only)
**Query set:** `docs/research/gold/gold-query-set-v1.json`
**Surface:** `http://localhost:3000/app` — Vite dev server, **PROD data**, no fixture shims
**Branch:** `eclipse-dramatic-moment` · **Corpus at run time:** 164 countries · ~129.4–133.2 K signals · window `FROM 21 JUL 2026` · 24 h
**Viewport:** 1512×950 desktop · tours dismissed · one browser, sequential
**Baselines compared per query:** API arm `docs/research/gold/2026-07-28-gold-query-eval.jsonl` · UI pilot `docs/research/gold/2026-07-30-ui-walkthrough-pilot.md`

**Batch protocol.** 20 queries in 4 batches of 5, appended to this one file so partial completion
stays a valid partial record. Each batch is delimited by `═══ BATCH n ═══` and closes with its own
summary block. Per-query retrieval protocol (the pilot's proposed U1–U5, applied here):

| step | action |
|---|---|
| **U1** | type the analyst-natural question into the search bar; record the auto-scope |
| **U2** | open offered LIVE THREADS in rank order (≤3) |
| **U3** | if none, read MEDIA SIGNALS as the honest floor |
| **U4** | for country-anchored queries, open the country brief |
| **U5** | for asymmetry queries, open voice mix |
| **U6** | on every arrival, run the mandatory CONTENT INVENTORY and record N1 promised-vs-delivered |

**Standing note on N1.** Recorded per query below. The mechanism is identical in every case and is
stated once here: **opening any result clears the search input** (`input.value === ""`, verified in
DOM on GQ-01 and GQ-02) **and no arrival surface carries a related-results affordance.** There is no
back-to-results control anywhere. Every N1 loss in this run traces to that single behaviour.

---

═══════════════════════════════ BATCH 1 — GQ-01…GQ-05 ═══════════════════════════════

## GQ-01 — Wildfires in France and Spain: evacuations + fire front

**Typed (U1):** `Wildfires in France and Spain evacuated fire front`
**Auto-scope rendered:** `Filtering to: France · results scoped to this country` (in the dropdown header only).

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS ×6**, every row carrying a rendered `Label under review` chip and a `partial match` tag:

| # | label (as rendered) | signals | category chip |
|---|---|---|---|
| 1 | Trump Threatens Iran Amid Military and Diplomatic Tensions | 3,880 | Corruption investigation |
| 2 | Wildfires Worsen Across Spain and France Amid Heatwave | 1,528 | Heat and public health risk |
| 3 | Wildfires Threaten Bordeaux, Defense and Nuclear Sites | 1,056 | Heat and public health risk |
| 4 | Heatwave Alerts Across Spain and Beyond | 880 | Heat and public health risk |
| 5 | Spain Wildfires Force Evacuations Near Madrid, Valencia | 857 | Wildfire or severe-storm disaster |
| 6 | Wildfires Rage in Spain and France, Over 200,000 Evacuated | 749 | **Earthquake or volcanic disaster** |

Rank 1 for a wildfire query is an Iran military thread. Row 6 — the thread whose label carries the
exact number the question asks for — is filed under *Earthquake or volcanic disaster*.

**MEDIA SIGNALS ×12** (all `ES`-tagged): **5/12 on-topic.** The other 7 are substring matches on
`front`: *"Canarias impulsa la construcción industrializada… **afrontar** la demanda"* (laprovincia.es
and eldia.es, `Industrial Disaster`), *"accident **frontal**"* (emporda.info), *"alejar la
**confrontación**"* (abc.es), *"Fiscal y **Fronteras** de la Guardia Civil"* (elmercuriodigital.net,
`Employment`), *"Ayuso **confronta** con el PP"* (elplural.com, `Delay`), *"la guerra **frontal** …
de sus aeropuertos"* (elconfidencial.com). On-topic ones: *"Spain and France confront 'unprecedented'
fire season"* (westhawaiitoday.com, chip `Technology`), *"Incendies en Europe: fumées sans
frontières"* (lavenir.net, chip `Employment`), *"España afronta unas 'horas cruciales' en la lucha
contra el fuego"* (huffingtonpost.es, chip `Employment`), *"Los incendios de Madrid y Ávila afrontan
horas clave"* (elcorreo.com), and a junk row *"Llamas Sin Fronteras 7019617 3"* (20minutos.es).

### CONTENT INVENTORY — surface B: thread detail (rank 2, 1,528 signals)

**Honesty chips AS RENDERED:** ⚠ *"This thread's coverage does not cohere — it likely conflates
unrelated stories. Verify before pinning."* · `coherence 0.50` · `HOT WINDOW` ·
*"105 of 1,528 signals are geo-attributed — cards cover only those"* · discussion lane labelled
`DISCUSSION · UNVERIFIED` · biography glass-box *"stitched in OpenAI space · θ topic↔era 0.827 ·
θ era↔era 0.862 · stitch sim 0.83"*. **No `⚑ state` chip anywhere — all 20 TOP SOURCES render
`UNCLASSIFIED`.**

**Scoped-vs-unscoped delta (pilot rubric defect 3).** The panel rendered **twice**. First paint,
unscoped: `10 COUNTRIES · 20 SOURCES`, 221 receipts, *"led by France (105), **Japan (37)**,
**Greece (35)**"*, geo split France 48% / Japan 17% / Greece 16% / Netherlands 5% / **Spain 4%** /
Cyprus 4% / China 4%. Second paint, France-scoped: `1 COUNTRIES`, **105 receipts**, *"TOP 1 OF 1
COUNTRIES · France 105 sig · 100%"*. **The scope silently deleted the Spain half of a
Spain-and-France question and hid ~37% off-geo contamination.** The header still reads `Global · 1528
signals`. **The focus bar shows only `THEME …` — there is no country chip, so the France filter
cannot be seen or cleared.**

**Receipts rendered: 30 of the claimed 105.** ROR@20 = **20/20 = 1.00**; first off-topic is #23
(*"Noyades en Normandie : 67 accidents et 18 décès"*). ROR@30 = 29/30.
Languages **fr, en, tr, az, sr** (**no es receipt at all; no Spanish outlet in the set**).
25 distinct outlets across ~15 origin countries: independent.co.uk, jordantimes.com, kibrispostasi.com,
adalet.az, havadiskibris.com, haberler.com, cnbc.com, yahoo.com, aljazeera.com, channelnewsasia.com,
thejakartapost.com, lanouvellerepublique.fr, rte.ie, koreaherald.com, franceinfo.fr,
freemalaysiatoday.com, 20minutes.fr, estrepublicain.fr, laprovence.com, midilibre.fr, rfi.fr,
malatyaguncel.com, milliyet.com.tr, sana.sy, tanjug.rs, stuff.co.nz.

**The divergent figures — each bound to its own outlet and timestamp, not collapsed:**

| figure as displayed | outlet(s) | stamp | scope implied by the headline |
|---|---|---|---|
| `220 000 personnes évacuées` + `42 000 hectares` | estrepublicain.fr · laprovence.com · midilibre.fr · rfi.fr | Jul 26, 00:12–01:15 | Gironde |
| `42.000 hectares` | 20minutes.fr | Jul 26, 14:45 | Gironde |
| `141 Bin Kişi Tahliye Edildi` | sana.sy | Jul 25, 09:15 | around Bordeaux |
| `140 000 personnes évacuées` + `19 000 hectares` | estrepublicain.fr | Jul 25, 01:15 | sud-ouest |
| `140 000 évacuées` + `30 000 hectares` | midilibre.fr | Jul 25, 01:15 | Gironde |
| `116 bin hektar` / `116 000 hektar` | kibrispostasi.com · adalet.az · havadiskibris.com · haberler.com | Jul 27, 07:45–11:00 | France, 2026 season |
| `98 bin hektar` | haberler.com · malatyaguncel.com · milliyet.com.tr | Jul 25–26 | France, season |
| `70 hiljada hektara` (EFFIS) | tanjug.rs | Jul 25, 08:00 | France |
| `330,000` evacuated (CBC) | worldnews@lemmy.ca | — | **discussion lane, `UNVERIFIED`** |

**Fire-front status is answerable from receipts:** *"la situation « globalement stable au cours de la
nuit », les secours restent « pleinement mobilisés »"* (lanouvellerepublique.fr, Jul 27 01:30) and
*"84 sapeurs-pompiers blessés par le feu, resté « globalement stable »"* (franceinfo.fr, Jul 27 00:15).

**VOICE MIX (stale under scope):** *"EN 35 · FR 4 · unknown 56 · **41%** of attributable voices are
France's own press · 20 of 49 attributable voices are domestic · Loudest outsider: Greece (7) ·
46 of 95 voices carry no outlet origin — excluded from these ratios, never assumed."* The 95-voice
denominator is the unscoped set while the receipts are the 105 France-scoped ones.

**Syndication, unmarked:** *"France, Spain battle 'monster' wildfires…"* runs verbatim at
jordantimes, aljazeera, channelnewsasia, thejakartapost, koreaherald, freemalaysiatoday, yahoo,
stuff.co.nz — **one AFP wire occupying 8 of the first 28 receipts with no syndication marker.**

### N1 — NAV-LOSS ✱
**Promised:** 6 threads (5 of them the same fire complex) + 12 media signals.
**Delivered on arrival:** 0. No related/sibling/"stories inside" section exists in the detail
(sections are: Narrative Biography · Public Attention · How It's Covered · Activity Timeline · Key
Subjects · Top Sources · all-coverage · Voice Mix · Deep History). Search input verified empty.
**Concretely lost:** *Wildfires Threaten Bordeaux, Defense and Nuclear Sites* (1,056) · *Heatwave
Alerts Across Spain and Beyond* (880) · *Spain Wildfires Force Evacuations Near Madrid, Valencia*
(857) · *Wildfires Rage in Spain and France, Over 200,000 Evacuated* (749) · plus, from the right
rail, *Incendios Forestales en Europa* (92), *Forest fires* (64, country chips **AF / GY**),
*Wildfires Rage Across Spain and France, Mass Evacuations* (64), *Wildfires* (51, 29 % confidence).
**≥8 live threads for one fire complex and no surface says they are one story.**

### Score **2** · API 2 · pilot 2 · **SAME**
D1 ✓ (ROR@20 1.00) · ≥2 of es/fr/en ✓ · ≥3 outlets / ≥2 origin countries ✓✓ · divergent evacuation
and burnt-area figures attributed and dated, not collapsed ✓. Held at 2: the blob is real (~37%
off-geo unscoped) though **flagged**, so the criteria's 0-clause does not fire; and level 3's
"other threads reachable from within the detail" fails outright (NAV-LOSS). Spain is represented in
the rendered receipt set only by non-Spanish outlets.

---

## GQ-02 — Berlin Pride attack: what happened + why authorities criticised

**Typed (U1):** `Berlin Pride attack German authorities criticised` — no auto-scope.

### FINDING: the complete question destroys retrieval; the short one restores it

| typed | LIVE THREADS returned |
|---|---|
| `Berlin Pride attack German authorities criticised` | **0 Berlin threads.** All 6 rows are Iran/Ukraine/Russia matched on the word *attack*: Iran Attack on US Bases (4,953) · Trump escalates Iran tensions over Houthi attacks (1,913) · Ukrainian Drone Attacks on Russia (654) · Drone Attacks on Moscow (326) · Drone Attacks in Belgorod (311) · Russian Drone Attacks on Civilians (300) |
| `Berlin Pride attack` (reformulated) | the 5 dedicated threads: **Berlin Pride Attack: Suspect Profile and Manhunt (287)** · Berlin Pride Attack Suspect Killed (36) · Berlin Pride Terror Attack (19) · Berlin Pride Attack Suspect (16) · Berlin Pride Car Attack (16) |

Adding the accountability half of the gold question — the half the criteria's level 3 asks for —
removes the right answer. This is a retrieval defect distinct from anything the pilot or the API arm
recorded.

**MEDIA SIGNALS on the full question** did carry the accountability strand exactly:
*"German authorities criticised over presumed Pride attacker"* (citizen.co.za, chip
`Policy: Policy Political`) · *"German authorities criticised after Pride attack"* (al-monitor.com)
· *"German authorities criticised after Pride attack"* (channelnewsasia.com). The other 9 are
`criticised` substring matches (Wokingham council, Mamdani property database, Barclays/El Niño,
Scottie Scheffler, Paul Biya, BBC soap set, Welsh Government, Indian celebrities, Merz reshuffle).
**On the short query MEDIA SIGNALS collapses to 1/12 on-topic** — the rest match `attack`, including
*"Dev Anand's son Suniel Anand dies of **heart attack**"* and *"baby severely injured in family
**dog attack** in Palencia"*.

### CONTENT INVENTORY — thread detail (287 signals)

Header: *"Berlin Pride Attack: Suspect Profile and Manhunt **RESURRECTED** · Global · 287 signals ·
Last 24h · active since Jun 30 · HOT WINDOW"*.
**Honesty chips AS RENDERED: none on the thread itself — no coherence warning, no `LABEL UNDER
REVIEW`, no `partial` tag.** Rendered caveats present: *"61 of 287 signals are geo-attributed"* ·
`DISCUSSION · UNVERIFIED` · relationships panel *"⚠ 2d apart — aggregates 2 snapshot steps, not
one"* + *"7 ended by substrate churn (topic re-founded/merged), not narrative change. 6 genuine
narrative change."* · biography *"stitch sim 0.84"*.
`HOW IT'S COVERED`: **Egypt 33 sig · 54% · −8.4 tone** / Germany 17 · 28% / Greece 11 · 18%.
`TOP SOURCES`: 20 rows, **all Greek/Cypriot**, all `UNCLASSIFIED` — inewsgr.com 9, lykavitos.gr 3,
news.gr 3, iefimerida.gr 3, tothemaonline.com 2, dnews.gr 2, protothema.gr 2, tanea.gr 2, thebest.gr
2, voria.gr 2, taxydromos.gr 2, newsbomb.gr 2, naftemporiki.gr 2, then sofokleous10.gr, kathimerini.gr,
newsbeast.gr, ertopen.com, lifo.gr, in.gr, news.makedonias.gr at 1. **Zero German outlets.**
`KEY SUBJECTS`: **`PERSON alexander ntomprint 9`** — a corrupted round-trip of *Alexander Dobrindt*
through Greek *Ντομπρίντ* — and `PERSON abdul rahman 4`. The top-ranked subject of the thread is a
mangled name.
`VOICE MIX`: *"**0%** of attributable voices are Germany's own press · **THIN** · 0 of 5 attributable
voices are domestic. Loudest outsider: Greece (5). 4 of 9 voices carry no outlet origin — excluded
from these ratios, never assumed."* The domestic gap **is** honestly surfaced.
`DISCUSSION · UNVERIFIED`: 6 items, **0 on-topic** (Trump/F-35 Turkey, Corinthia factory explosion,
Colombia–Cuba/Nicaragua embassies, a US congressman, Turkish TÜGVA, a Búzios driver).

**Receipts rendered: 30 of a 61 sample. ROR@20 = 17/20 = 0.85. ROR@30 = 17/30 = 0.567.**
Receipts 1–17 are the event and carry the accountability substance the criteria asks for:
*"Islamist terrorist act the attack at Berlin Pride, says German government: Manhunt for the Lebanese
perpetrator"* (sofokleous10.gr) · *"Berlin: 'Terrorist' attack at Pride – German national and **ISIS
supporter** the suspect"* (ertopen.com) · *"Who is the 21-year-old suspect … **He had planned an act
of violence before**"* (inewsgr.com) · *"Photo of suspect released – **Known to authorities for his
activity in the Islamist scene**"* (inewsgr.com) · *"'He is armed and dangerous'"* (tanea.gr).

**The blend, unflagged.** Receipts 18–30 are two unrelated Athens crime stories:
- **18–25 (8 receipts, 27%)** — grenade plot against prosecutor **Isidoros Dogiakos**
  (lykavitos.gr, news.makedonias.gr, achaianews.gr, madata.gr, news.gr, bankingnews.gr, thebest.gr)
- **26–30 (5 receipts, 17%)** — murder of lawyer **Stavros Georgiou** by a 28-year-old Egyptian
  (topontiki.gr, iefimerida.gr, e-thessalia.gr, voria.gr ×2)

Both contaminating clusters exceed 15% and ROR@all(rendered) = 0.567 < 0.60 — the pilot's own G3
triggers, which it recorded as *not* firing at ROR@all ≈ 0.63 with one cluster. **Coherence renders
no warning at all on this 3-story thread**, the same measurement failure the pilot found on GQ-14.
The only visible hint is the geo stat *Egypt 54%*, which reads as coverage, not contamination.

**Syndication measured, not assumed.** Normalised-token Jaccard ≥0.6 over the 30 rendered headlines:
**headline diversity 0.80, repeated-headline share 0.20** (first 20: 0.75 / 0.25). Largest
near-duplicate group = 5. G2's thresholds (diversity <0.5, repeated >0.35) **do not fire** — the
UK-regional English wire cluster the criteria warned about is absent from this thread, which is
Greek-language coverage. 12 distinct outlets, but **one origin country** (GR, +1 CY).

### N1 — NAV-LOSS ✱
**Promised:** 5 Berlin Pride threads. **Delivered:** 0 references. Right rail contains **zero**
"Berlin" rows after opening (verified). Search input verified empty.
**Concretely lost:** *Berlin Pride Attack Suspect Killed* (36) · *Berlin Pride Terror Attack* (19,
the only one carrying a `Label under review` chip) · *Berlin Pride Attack Suspect* (16) · *Berlin
Pride Car Attack* (16). Also lost: the three `German authorities criticised` receipts, which live
only under the *other* phrasing.

### Score **1** (blob-capped; receipts informed) · API 0 · pilot 2 · **UI-BETTER vs API, WORSE vs pilot**
Retrieval is level-2 quality (ROR@20 0.85, correct specific label, G1/G2 clear). It cannot hold 2
because level 2 requires **"no unflagged cross-story blending"** and 43% of the rendered coverage is
two unrelated Athens crime stories with **zero** coherence warning and **zero** label-court chip. It
is not 0 because the thread is the right thread, the label is accurate, and receipts 1–17 answer the
question with attribution. **Counts toward informed rate.**
*Rubric-boundary note for the record: v2's ladder has no rung for "correct thread + informed
receipts + unflagged contaminated tail". The pilot's 2 and this 1 differ on a measured degradation
(ROR@all 0.63→0.567, one contaminating cluster→two, both >15%), not on interpretation.*

---

## GQ-03 — DR Congo Ebola: cases, deaths, international response

**Typed (U1):** `Ebola outbreak DR Congo cases deaths international response`
**Auto-scope rendered:** `Filtering to: DR Congo · results scoped to this country`.

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS ×1:** *Ebola Outbreak Congo · 254 signals · Disease outbreak · partial match*.
**MEDIA SIGNALS ×12 — 12/12 on-topic**, all `CD`-tagged, but 12 receipts = **5 distinct stories**:

- *"Ebola response workers strike in DR Congo as death toll spikes"* — aljazeera.com
- *"DR Congo reports **nearly 3,000 Ebola cases** as PM calls for faster response-Xinhua"* —
  english.news.cn, **listed twice verbatim**
- *"Ebola response needs urgent scale-up after two months"* — msf.org (chip `Anti-Corruption Authorities`)
- *"Existing vaccines induce antibody response against the Ebola virus…"* — umn.edu, **twice**
- *"World Insights: Fastest-ever Ebola outbreak tests global health response"* — **×6** across
  beijingbulletin.com, chinanationalnews.com, africaleader.com, nigeriasun.com, kenyastar.com,
  sierraleonetimes.com

**One Xinhua wire occupies 6 of 12 slots and `english.news.cn` carries no state-media marker.**

### CONTENT INVENTORY — surface B: thread detail — **DEGRADED**

First paint showed real content: `2 COUNTRIES · 20 SOURCES`, 43 receipts, *"led by **France** (26
signals), Congo (17)"*, `TOP 2 OF 2 COUNTRIES · France 26 sig · 60% / Congo 17 sig · 40%`, sources
*inewsgr.com, enikos.gr, skai.gr*. **It then re-rendered and collapsed, and stayed collapsed:**

> Ebola Outbreak Congo `NEW` — **Global · 254 signals** · Last 24h · active since Jun 24 · `HOT WINDOW`
> This dynamic narrative thread is active in the selected window with 254 signals.
> Coverage tone is mixed (0.00), and the current evidence sample spans **0 recent items**.
> `254 24h · raw SIGNALS` · `0.00 AVG SENTIMENT` · **`0 COUNTRIES`** · **`0 SOURCES`**

`HOW IT'S COVERED`, `TOP SOURCES` and the coverage list **disappeared entirely** (sections dropped
from 6 to 3). What remained, stale and wrong:

> `VOICE MIX · WHO SPEAKS?` — unknown 14 — **0% of attributable voices are France's own press** ·
> `THIN` · 0 of 9 attributable voices are domestic. **Loudest outsider: Greece (9).**

…rendered under a thread titled **Ebola Outbreak Congo**. Meanwhile the dock re-scoped to a third
country: `THREAD: Ebola Outbrea… | DYNAMIC-TOPIC- → **US**`, with `CONFLICTS · UNITED STATES —
San Francisco, California` and `PUBLIC ATTENTION · UNITED STATES`.

**Root cause confirmed in the network tab:** `GET /api/v2/theme/dynamic-topic-239?hours=24&country_code=CD
→ 200 OK`, **fired twice**. The thread holds no CD-attributed members in the window, so the panel
empties. **The focus bar shows only `THEME Ebola Outbreak Congo` — the CD filter is invisible and
unclearable.** This is the pilot's GQ-14 blanking bug, reproduced on a different query. Also observed:
`/theme/{id}/drift` fired **5×** and `/compare` and `/lineage` **2×** each for one open.

### CONTENT INVENTORY — surface C: DR Congo country brief (U4)

Reaching it produced the pilot's **compound-focus trap** first (`COUNTRY DR Congo` + `THEME Ebola
Outbreak Congo`, header `1 countries · 82 signals`, panel still `0 recent items`, rail *"No active
narratives in this time range"*). Clearing the theme chip gave the brief:

- `82 signals` · **`Narrative Threads 0`** · `0 THREADS` · Atlas Topics 12 · Source Mix 10, 32% foreign
- *"DR Congo shows 82 signals in this 24h window, led by Democracy, Minister, and Public Health. On
  the people-side layer, public attention is visible around **galatasaray – venezia** and **chelsea –
  sydney wanderers**."*
- `PUBLIC ATTENTION people-side proxy` — *"Google searches and Wikipedia pageviews are
  country/language-edition proxies… **they are not a population-normalized opinion poll**"* ✓;
  `WIKI` — *"No Wikipedia pageview data for this proxy."* ✓
- `FORUM UNVERIFIED` — **this is where the death figure lives**: *"Ebola cases in Congo **near 3,000,
  including over 1,300 deaths** apnews.com"* (bluesky), plus a French item on a second American cured
  in Germany
- `VOICE MIX` — **68% covered by its own press · 210 of 311 attributable voices are domestic ·
  Loudest outsider: CN (16)** ✓ ownership-based
- `TOP PUBLISHERS` — actualite.cd 33, mediacongo 6, radiookapi.net 5, mediacongo.net 4,
  businessghana.com 2 — real Congolese outlets ✓
- `RECENT SIGNALS` — Bintou Keita appointed minister in Guinea; *"Ituri: ADF intensify attacks in
  Mambasa, six more civilians abducted"* — **not the outbreak**
- `KEY SUBJECTS` — therese wagner 2, **wikimedia commons 2 (`PERSON`)**, chris baryomunsi 1,
  **july a kindu 1**, **whatsapp linkedin 1 (`PERSON`)**, isaac bogoch 1, craig spencer 1, amanda rojek 1

### Built-in falsification check — **PASSED**
Only two figures render anywhere: *"nearly 3,000 cases"* (Xinhua, search lane) and *"near 3,000 …
over 1,300 deaths"* (bluesky citing AP, `FORUM UNVERIFIED`). **Nothing presents the 930/1,000/1,354/1,400
death-toll spread or the 2,900/3,075/3,200 case spread as a live who-says-what disagreement, and no
single "confirmed" total is asserted.** The criteria's auto-FAIL clause does not fire.

### N1 — NAV-LOSS ✱
**Promised:** 1 thread + 12/12 on-topic media signals. **Delivered:** a thread panel with 0 receipts,
and a country brief whose recent signals are Guinea and ADF attacks. **All 12 on-topic receipts —
including the only case figure and the MSF/WHO response strand — are unreachable from either
arrival surface.**

### Score **0** · API 0 · **SAME** · not piloted
Level 0 per the rubric's own words: *"a degraded/empty state that does not say so."* A 254-signal
thread renders `0 COUNTRIES · 0 SOURCES · 0 recent items` under a header still claiming `Global ·
1528`-style totals, with no statement that a filter caused it, no clearable chip, and a **stale
voice-mix panel making a confident claim about France's domestic press on a DR Congo story** while
the dock scopes to the US. Recorded explicitly: the raw lane was 12/12 on-topic and would have
supported **1b** had the thread not been served in this state, and the falsification check passed —
so this 0 is a **presentation** failure, not a fabrication failure.

---

## GQ-04 — Marcos / Philippines: corruption + State of the Nation Address

**Typed (U1):** `Marcos Philippines corruption state of the nation address`
**Auto-scope rendered:** `Filtering to: Philippines · results scoped to this country`.

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS: the section is absent entirely — zero threads offered.**
**MEDIA SIGNALS ×12, all `PH`-tagged — 10/12 on-topic** (ROR 0.833):

- *"Marcos puts anti-graft campaign at center of address to Congress"* — philstar.com
- *"Philippines' Marcos puts anti-graft campaign at centre of address to Congress"* —
  businesstimes.com.sg *(same Reuters copy as the row above — the only D3 duplication visible)*
- *"**Filipino Religious demand corruption response** in Marcos' State of the Nation address"* —
  thetablet.co.uk, chip **`Water`**
- *"Philippines' Marcos uses national address to **promise relief, but funding questions loom**"* — scmp.com
- *"THE PHILIPPINES-QUEZON CITY-STATE OF THE NATION ADDRESS-**PROTEST**"* — philippinetimes.com
- *"Marcos addresses **Cebu's traffic and port challenges** in his SONA"* — manilatimes.net
- *"Suspected bomb found near Philippine Senate before President Marcos' address"* — news.az
- *"SONA 2026 Live Updates"* — inquirer.net · *"LIVE Coverage / LIVE updates"* — philstar.com ×2

Off-topic 2/12, both `address` substring matches (*"NMP urged to help **address** Philippine officer
deficit"*, *"Senate bill eyes nutrition council revamp to **address** malnutrition"*).
Outlets span **PH, GB, HK, SG, AZ** — ≥3 distinct across ≥2 origin countries ✓.

### Surface B — "Open the story" (cross-thread narrative), the flagship NL surface

> `STORY · Marcos Philippines corruption`
> **`RESEARCH PLAN UNAVAILABLE`**

Network: `POST /api/v2/research/plan → 429 Too Many Requests`, **fired twice for one click** — the
pilot's finding, unchanged. The error names no cause (rate-limited vs broken). This was the first
`/research/plan` call of the session.

### CONTENT INVENTORY — surface C: Philippines country brief (U4)

- `421 signals` · **`Narrative Threads 0`** · `0 THREADS` · Atlas Topics 12 · Source Mix 10, 35% foreign
- *"Philippines shows 421 signals in this 24h window, led by Policy Uncertainty, Presidential Actions,
  and Public Sector… Most-covered figures: **ferdinand marcos jr** and bangko sentral."*
- `KEY SUBJECTS`: ferdinand marcos jr 18, bangko sentral 7, martin romualdez 6, **Sara Duterte 5**,
  donald trump 4, lydia cotterill 4, **marcos jr 3**, **sara duterte 3** — the same two people
  listed twice under different casing/truncation
- `VOICE MIX`: **65% covered by its own press · 833 of 1276 attributable voices are domestic ·
  Loudest outsider: DE (58)** ✓
- `TOP PUBLISHERS`: manilatimes.net 146, philstar.com 50, sunstar.com.ph 28, rappler.com 27,
  bworldonline.com 27 ✓ genuine domestic
- `CONFLICT EVENTS` — *"related by country, not by story · machine-coded, geo approximate"* ✓
- `PUBLIC ATTENTION` — the proxy caveat renders ✓; `SEARCH` #3 is *"sara duterte impeachment evidence
  presentation"* (genuinely relevant)
- `RECENT SIGNALS` — includes the on-topic critical op-ed *"**The 'Enoki SONA' reflects Marcos'
  incompetence**"* (manilatimes.net), but the **first** row is *"Patricia Noarbe, pareja de **Marcos**
  Llorente…"* (clarin.com) — the Spanish footballer
- `FORUM UNVERIFIED` — 2 of 4 rows are **Bible verses**: *"Evangelho de **Marcos**, capítulos 8 ao
  16"* and *"**Marcos** 7:36-37"* (biblia@lemmy.world)

### N1 — NAV-LOSS ✱ (and a door-to-door contradiction)
Searching `Philippines` offers **4 LIVE THREADS** — *Q2 2026 Earnings Reports* (343), *Super Typhoon
Bavi* (235), *China Disasters and Tensions* (189), *Rubio Warns on Iran Hormuz* (83). Clicking
**"Go to Philippines" from that same dropdown** lands on a country brief that states
**`Narrative Threads 0`** and *"No active narratives in this time range"*. **4 promised, 0
delivered, one click apart.** Separately, none of the 12 on-topic SONA media signals survives into
the country brief, whose recent signals are entirely different.

### Score **1b** · API 0 · **UI-BETTER** · not piloted
Thread-less but informed. No thread is offered anywhere and the absence is stated on screen
(`Narrative Threads 0` / `0 THREADS`) — so no category bucket is presented as an answer and the
criteria's G1 cap has nothing to fire on. The rendered receipts substantively answer *what he said*:
**anti-graft campaign at the centre of the address**, relief promises with **funding questions**,
**Cebu traffic and ports**, plus the criticism strand (**religious groups demanding a corruption
response**, a SONA **protest**, the *'Enoki SONA'* op-ed). Level 2 is unreachable with no thread to
score. **Counts toward informed rate, not answered rate.**

---

## GQ-05 — Colombia: embassy closures / cutting ties with Cuba and Nicaragua

**Typed (U1):** `Colombia president-elect closing embassies cutting ties Cuba Nicaragua`
**Auto-scope rendered:** `Filtering to: Colombia · results scoped to this country`.

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS: section absent — zero threads offered** (matches the pilot).
**MEDIA SIGNALS ×9 — every one tagged `NI`**, including the Colombian, Haitian and Brazilian rows.
**4/9 on-topic (ROR 0.44):**

- *"De la Espriella to close Colombian embassies in **14 countries** and cut ties with Cuba and
  Nicaragua"* — **mercopress.com** (UY), **en**, chip **`Water`**
- *"Colombie: le président élu annonce qu'il va rompre les relations diplomatiques avec Cuba et le
  Nicaragua"* — **lenouvelliste.com** (HT), **fr**, chip **`Communist`**
- *"Presidente eleito da Colômbia anuncia rompimento com Cuba e Nicarágua"* — **infomoney.com.br**
  (BR), **pt**, chip `Diplomacy & Negotiations`
- *"Novo presidente da Colômbia anuncia que seu país romperá relações diplomáticas com Cuba e
  Nicarágua. **E reatará relações com Israel, no dia da posse, 7 de agosto**"* — **montesclaros.com**
  (BR), **pt**

Off-topic 5/9 — all Nicaragua/Cuba-US items, not the Colombian announcement: martinoticias.com,
cubaheadlines.com ×2, r7.com, foxnews.com (*"After Cuba, Nicaragua is next"*).

**Language/origin verdict: zero Spanish-language on-topic receipts and zero Colombian-origin
outlets.** The criteria's *"MAJORITY of receipts in Spanish and ≥3 distinct Colombian-origin
outlets"* fails on every clause.

### CONTENT INVENTORY — surface B: Colombia country brief (U4)

- `820 signals` · **`Narrative Threads 0`** · `0 THREADS` · Source Mix 10, **15% foreign**
- `VOICE MIX`: **85% covered by its own press · 2952 of 3455 attributable voices are domestic ·
  Loudest outsider: AR (54) · 1% is foreign media in the local language (soft power, not
  self-coverage)** ✓ ownership-based, and it explicitly separates soft power from self-coverage
- `TOP PUBLISHERS`: **eltiempo.com 90, semana.com 59, lafm.com.co 55, hsbnoticias.com 46,
  colombia.com 41** — the Colombian press is abundantly indexed
- `KEY SUBJECTS`: `EVENT el nino 20`, **`PERSON De la Espriella 14`**, `PLACE america latin 12`,
  `PERSON ie Rodríguez 11` (garbled), **`PERSON Abelardo de la Espriella 9`** (duplicate of the
  first), `ORG el pais 8`, `PLACE republica dominicana 7`, `PERSON miguel uribe turbay 5`
- `RECENT SIGNALS`: Bogotá robbery-murder, **VP-elect José Manuel Restrepo travelling to Peru to
  represent De La Espriella's government at Fujimori's inauguration** (adjacent, not the announcement),
  María Camila Potosí disappearance, Petro influence-peddling scandal (larepublica.pe), Japan
  earthquake, an Atlántico motorcycle crash — **the embassy story is not among them**
- `PUBLIC ATTENTION`: proxy caveat renders ✓; content is football (*real madrid vs leganes*, `WIKI`
  Lamine Yamal 74,442 / Ferran Torres / Marc Cucurella) plus *viviane morales*
- `FORUM UNVERIFIED` (r/colombia): *"Un facto que vi en ig"*, *"¿De verdad somos mediocres?"*,
  *"Por que colombia está tan llena de Odio y Egoísmo?"*, *"Que sean feos nos los hace
  incestuosos..."* — correctly labelled

**Counterpart-voice absence (level-3 requirement): not surfaced anywhere.** The Colombia voice mix
names Argentina as loudest outsider and never mentions Cuba or Nicaragua, while every search receipt
was tagged `NI` with no Nicaraguan outlet present.

### N1 — NAV-LOSS ✱
**Promised:** 9 media signals, 4 of them the answer. **Delivered at the country door:** 0 of them —
`RECENT SIGNALS` is a disjoint set. The only surface that ever held the answer was the search
dropdown, and it is destroyed by the click that follows it.

### Score **1b** · API 0 · pilot 1 · **UI-BETTER vs API; same tier as pilot, better specified**
Honest floor with labelled raw signal and sources (`Narrative Threads 0`, *"No active narratives in
this time range"*), and the rendered receipts do substantively answer *"what exactly has been
announced"*: **embassies in 14 countries closed, ties cut with Cuba and Nicaragua, relations with
Israel restored, on inauguration day 7 August** — each attributed. Level 2 is blocked by the
language/origin criteria. **This is confirmed as a ranking failure, not a data gap:** eltiempo,
semana and lafm are indexed at 85% domestic share in the same window, and the story reaches the
analyst only through Uruguayan, Haitian and Brazilian outlets. (It is also in the corpus in Greek —
the identical story surfaced in GQ-02's discussion lane as *"Κολομβία: Ο εκλεγμένος πρόεδρος
διακόπτει διπλωματικές σχέσεις με Νικαράγουα και Κούβα"*.)

---

## ═══ BATCH 1 SUMMARY ═══

| Query | API | Pilot | **v2** | Divergence vs API | N1 | Why (one line) |
|---|---|---|---|---|---|---|
| **GQ-01** wildfires FR/ES | 2 | 2 | **2** | SAME | ✱ | ROR@20 1.00 with every evacuation/hectare figure bound to its own outlet+date; blob real but **flagged** (⚠ coherence 0.50). |
| **GQ-02** Berlin Pride | 0 | 2 | **1** | UI-BETTER | ✱ | Right thread, ROR@20 0.85 — but 43% of rendered coverage is two Athens crime stories with **no coherence warning and no label chip**. |
| **GQ-03** DRC Ebola | 0 | — | **0** | SAME | ✱ | 254-signal thread renders `0 COUNTRIES · 0 SOURCES · 0 items` under an invisible `country_code=CD`, with a stale **"France's own press"** claim on a Congo story. |
| **GQ-04** Marcos SONA | 0 | — | **1b** | UI-BETTER | ✱ | No thread anywhere and Atlas says so; 10/12 raw receipts answer the SONA + corruption strands. |
| **GQ-05** Colombia embassies | 0 | 1 | **1b** | UI-BETTER | ✱ | Honest floor + 4 receipts giving the full announcement, but **0 Spanish-language, 0 Colombian-origin** — a ranking failure over an 85%-domestic index. |

**Metrics (batch 1, all 5 are `should_answer`; no controls in this batch).**

- **Answered rate** (≥2): **1/5 = 20%**
- **Informed rate** (≥1b): **4/5 = 80%** — GQ-01, GQ-02, GQ-04, GQ-05
- **Honesty rate** (honest failure ÷ non-answered): **3/4 = 0.75** — GQ-02, GQ-04, GQ-05 honest; GQ-03 misleading
- **NAV-LOSS count: 5/5**
- **Unflagged-blob count: 1** — GQ-02 (GQ-01's blob is flagged; GQ-03's is unobservable because the panel is empty)
- **Divergence vs API:** UI-BETTER ×3, SAME ×2, UI-WORSE ×0
- **Divergence vs pilot** (3 overlapping): SAME ×1 (GQ-01), WORSE ×1 (GQ-02, on a measured degradation), refined ×1 (GQ-05 1 → 1b)

**Batch-1 defects (product, not scoring).**

1. **N1 is a single root cause, and it is total (5/5).** Opening any result **clears the search
   input**, and no arrival surface has a related-results affordance. The search dropdown is the only
   place a query's results exist. Sharpest instances: 5 sibling wildfire threads (GQ-01), 4 sibling
   Berlin threads (GQ-02), 12/12 on-topic Ebola receipts (GQ-03), 4 embassy receipts (GQ-05).
2. **Invisible country auto-scope, now shown to hide evidence rather than just blank panels.** On
   GQ-01 it cut the thread 10 countries/221 receipts → 1 country/105, **deleting the Spain half of a
   Spain-and-France question and concealing 37% off-geo contamination**, while the header still read
   `Global`. On GQ-03 it emptied a 254-signal thread outright. **It never appears as a clearable
   chip.**
3. **Coherence does not fire on real blobs.** GQ-02's 3-story thread carries no warning and no
   label-court chip; GQ-01's 2-story-plus thread does. Same class as the pilot's `tier: "tight"` on
   a 3-story blob.
4. **Search recall collapses when the question gets more complete.** `Berlin Pride attack` → 5
   correct threads; `Berlin Pride attack German authorities criticised` → 0, replaced by six
   Iran/Ukraine "attack" threads. The added tokens are the ones the gold criteria calls level-3
   material.
5. **Door-to-door count contradiction.** Search `Philippines` offers 4 live threads; "Go to
   Philippines" from the same dropdown reports `Narrative Threads 0`. Same for DR Congo (1 thread
   offered → `0`) and Colombia (`0`/`0`, consistent).
6. **`/research/plan` → 429, still double-firing** one POST per click; error text names no cause.
   The flagship natural-language surface was unavailable on its first use of the session.
7. **Category chips remain systematically wrong**, unchanged from the pilot: `mercopress.com · Water`
   on an embassy closure, `thetablet.co.uk · Water` on a corruption story, `lenouvelliste.com ·
   Communist`, `msf.org · Anti-Corruption Authorities` on an Ebola scale-up, `westhawaiitoday.com ·
   Technology` on a fire season, thread *"Wildfires Rage in Spain and France, Over 200,000
   Evacuated"* filed under **Earthquake or volcanic disaster**, thread *"Ukrainian Drone Attacks Hit
   Russian Oil"* filed under **ELECTION LEGITIMACY DISPUTE** with country `DE` and subjects Fauci /
   Rand Paul / Tulsi Gabbard.
8. **No `⚑ state` chip rendered in this entire batch.** All 40 observed `TOP SOURCES` rows read
   `UNCLASSIFIED`, and `english.news.cn` (Xinhua) plus six Xinhua-syndicated content farms carried no
   ownership marker on GQ-03.
9. **Raw-lane matcher is substring-based and language-blind.** `fire front` matched Spanish
   *fronteras / afronta / confronta / frontal* (7/12 off-topic); `attack` matched *heart attack* and
   *dog attack*; `address` matched *address malnutrition*; **`Marcos` matched the Gospel of Mark and
   a Spanish footballer's partner**.
10. **Entity-layer corruption.** `PERSON alexander ntomprint` is the top key subject of the Berlin
    thread (a round-trip of *Dobrindt* through Greek); `PERSON wikimedia commons`, `PERSON whatsapp
    linkedin`, `PERSON july a kindu` on DR Congo; case/truncation duplicates (`Sara Duterte`/`sara
    duterte`, `De la Espriella`/`Abelardo de la Espriella`).
11. **Duplicate request fan-out persists:** `/theme/{id}/drift` ×5, `/compare` ×2, `/lineage` ×2 for
    a single thread open.
12. **Voice-mix panels go stale and mis-anchor across re-renders:** "France's own press" on a DR
    Congo thread, an unscoped 95-voice denominator against 105 scoped receipts on GQ-01.

**What the batch says about the pilot's central claim.** The pilot showed navigation connects. This
batch shows what arrives: on 4 of 5 queries the receipts on screen are genuinely informative and
carry outlet + timestamp + language, which is why the informed rate (80%) is four times the answered
rate (20%). The failure is almost never "Atlas has nothing" — it is that **the surface that holds
the answer is destroyed by the click that leaves it**, and that the flags meant to warn about
blending fire on the flagged blob and stay silent on the unflagged one.

*Batches 2–4 append below this line.*

═══════════════════════════════ BATCH 2 — GQ-06…GQ-10 ═══════════════════════════════

**Run conditions.** Same browser session, sequential, `http://localhost:3000/app`, viewport
1512×950, prod data. Corpus at batch-2 start: **164 countries · 133,213 signals**, window
`FROM 21 JUL 2026`, 24 h (drifted to 131,920 by the last query). Screenshots were unavailable this
batch (the Browser pane was not compositing), so **every quotation below is taken from the live DOM
via `get_page_text` / `innerText`, which is the rendered text layer** — the same pixels, read as
text. Where a chip renders as a glyph with no text, that is stated explicitly and measured
(bounding box + tooltip), because it is exactly the D5-pixels question.

**Standing N1 note (batch 1) re-verified, not re-discovered.** On all five queries the search input
was confirmed empty after opening a result (`input.value === ""`), the dropdown was gone, and no
arrival surface carried a related-results affordance. **5/5 CONFIRMED.**

---

## GQ-06 — US/Iran strike pause: US-Western vs Iranian vs Gulf framing, state outlets marked

**Typed (U1):** `US Iran paused strikes Iranian Gulf framing state media`
**Auto-scope rendered:** `Filtering to: Iran · results scoped to this country` (dropdown header only).

### NEW FINDING, and it partially CONTRADICTS batch 1: the label-court chip is a 7-px unlabelled dot

Batch 1 recorded GQ-01's threads as "carrying a rendered `Label under review` chip". Measured here in
the DOM, the search-dropdown court status is **`<span class="label-review-chip label-review-chip--dot">`
with `innerText === ""` and a bounding box of 7 × 7 px** — a bare dot whose only content is a hover
tooltip. Five of the six offered threads carried one:

| # | thread (as rendered) | signals · category | court dot tooltip |
|---|---|---|---|
| 1 | **Trump Halts Iran Strikes to Pursue Diplomatic Deal** | 490 · Armed conflict escalation · partial match | ⬤ *"This label only partially matches its receipts."* |
| 2 | US Military Strikes on Iran | 275 · Armed conflict escalation · partial match | — none — |
| 3 | US Strikes on Iran | 244 · Armed conflict escalation · partial match | ⬤ *"This label **did not match** its receipts."* |
| 4 | US-Iran Strikes Escalate | 226 · Armed conflict escalation · partial match | ⬤ *"This label **did not match** its receipts."* |
| 5 | Jordan Intercepts Iranian Missiles | 170 · Armed conflict escalation · partial match | ⬤ *"This label only partially matches its receipts."* |
| 6 | US Strikes Iran Third Night | 168 · Armed conflict escalation · partial match | ⬤ *"This label **did not match** its receipts."* |

So the court verdict — including three outright FAILED — reaches the analyst as an unlabelled dot.
The full-text `LABEL UNDER REVIEW` string batch 1 saw does render, but in the **right-rail Narrative
Threads panel**, not in the search dropdown. Two renderings of the same fact, one legible.

### CONTENT INVENTORY — surface A: search dropdown

**MEDIA SIGNALS ×12**, all `IR`-tagged. 12/12 topically adjacent (pause / mediation / Hormuz), but
**5 of 12 are one wire copy verbatim** — *"Mediators see progress in efforts to halt Iran war as drone
attacks rattle region"* at wellandtribune.ca, texarkanagazette.com, reviewonline.com, salemnews.net
(+ newstodaynet.com as *"…in diplomacy to stop Iran war"*). **No syndication marker.** Languages
bg / en / it / sq. **No Persian, no Arabic receipt.** The Gulf/Arab strand exists only through
third parties: middleeasteye.net, themedialine.org, ansa.it, egyptindependent.com.

### CONTENT INVENTORY — surface B: thread detail, rank 1 (490 signals)

Header: *"Trump Halts Iran Strikes to Pursue Diplomatic Deal · **Global · 490 signals** · Last 24h ·
active since Jun 11 · `HOT WINDOW`"* — while the body reads `1 COUNTRIES · 20 SOURCES` and
*"33 of 490 signals are geo-attributed"*, `TOP 1 OF 1 COUNTRIES BY VOLUME · Iran 33 sig · 100%`.

**Invisible auto-scope CONFIRMED in the network tab:** `GET /api/v2/theme/dynamic-topic-121?hours=24
&country_code=IR → 200 OK`, **fired twice**, plus one unscoped call. The focus bar reads
`THEME | Trump Halts Iran Strikes to Pursue Diplomatic Deal | × | MAP · THREADS · STREAM · UNIVERSE
RE-SCOPED | ×` — **no country chip, so the IR filter cannot be seen or cleared.** `/theme/{id}/drift`
fired **6×**, `/compare` and `/lineage` **2×** each. Batch-1 defects 2 and 11 CONFIRMED verbatim.

**Honesty chips AS RENDERED:** `HOT WINDOW` · `NARRATIVE BIOGRAPHY · 13 WEEKS` `CANDIDATE STITCH` ·
the biography glass-box *"stitched in OpenAI space · θ topic↔era 0.827 · θ era↔era 0.862 · stitch sim
0.88 · union of 4 measured lineages (lin-88 + lin-1096 + lin-2087 + lin-5809)"* · *"33 of 490 signals
are geo-attributed — cards cover only those"* · `DISCUSSION · UNVERIFIED` · `⚠ 2d apart — aggregates 2
snapshot steps, not one` + *"3 ended by substrate churn (topic re-founded/merged), not narrative
change. 1 genuine narrative change."*
**Absent: any coherence warning; any label-court status (the rank-1 dot's "only partially matches"
does not render on the detail panel at all); any state-media marker.**

**Receipts rendered: 30 of the 33 sample. ROR@20 = 20/20 = 1.00. ROR@30 = 30/30 = 1.00.**
The retrieval is excellent and the pause is answered with dates and attribution — canal26.com
*"Iran and the United States halt attacks in the Middle East as Donald Trump awaits a diplomatic
solution"* (Jul 27 15:00), 20minutos.es *"Trump halts attacks on Iran over fear of running out of
ammunition, according to US media"* (Jul 26 20:00), infobae.com *"Trump assured that he will not allow
Iran to have a nuclear weapon after the resumption of negotiations"*, plus the US-Congress strand
(*"House of Representatives voted to end the war between Donald Trump and Iran"* tribuna.com.mx,
*"El Senado de EE.UU. rechaza la resolución para limitar los poderes de guerra"* cadena3.com).

**And that is where the query dies. The full 30-receipt set is Hispanophone third-party press:**
canal26.com · laprovincia.es · 20minutos.es · hoy.com.do · confirmado.com.ve · lanueva.com ·
tn.com.ar · tribuna.com.mx ×2 · lahora.gt · biobiochile.cl · proceso.hn · lopezdoriga.com ·
abc.com.py · infobae.com ×2 · larepublica.co · itongadol.com ×3 · diariopanorama.com ·
tiempodesanjuan.com · cadena3.com ×2 · rpp.pe · eldiariony.com · mdzol.com · cnn.com (Spanish
edition) · unionradio.net · eleconomista.com.mx.
**Zero Iranian outlets. Zero Gulf/Arab outlets. Zero Western English-language outlets.** Of the three
framings the question asks to place side by side, **none is represented by its own press.**

`TOP SOURCES` — all 20 rows read `UNCLASSIFIED`.
`KEY SUBJECTS` — **`PERSON al golfo persico 1`**: the Persian Gulf typed as a person.
`VOICE MIX · WHO SPEAKS?` — *"unknown 4 · **0%** of attributable voices are Iran's own press · `THIN`
· 0 of 2 attributable voices are domestic. Loudest outsider: Argentina (1). 2 of 4 voices carry no
outlet origin — excluded from these ratios, never assumed."* — an n=4 denominator sitting under a
20-source / 33-receipt panel. Batch-1 defect 12 CONFIRMED.

### CONTENT INVENTORY — surface C: Iran country brief (U4) — **the trust failure**

Reached via `Go to Iran · COUNTRY BRIEF →`; produced the **compound-focus trap** first
(`COUNTRY Iran` + `THEME Trump Halts Iran Strikes` both live) and needed the theme chip cleared.

- `3,247 signals` · `8 THREADS` · Atlas Topics 12 · Source Mix 10
- `NARRATIVE THREADS` (8): Iran Threatens Ukraine Over Ship Attack 74 · Iran's Pickaxe Mountain
  Threat 24 · US Strikes Iran Seventh Night 158 · Iran Oil Sales During War 37 · Multiple Global
  Events: Quake, Lawsuits, Politics 49 · **Jordan Intercepts Iranian Missiles 17** · Iran Hormuz
  Strait Tensions 17 · Iran Attacks UAE Tankers 16
- `PUBLIC ATTENTION people-side proxy` — the *"not a population-normalized opinion poll"* caveat
  renders ✓; `WIKI` — *"No Wikipedia pageview data for this proxy."* ✓
- `FORUM UNVERIFIED` ✓ labelled
- **`TOP PUBLISHERS who's covering this country`: `irna.ir` **495 signals** (#1 by a factor of 14) ·
  bluesky 36 · `arabic.rt.com` **31** · aljazeera.com 25 · haberler.com 23 — rendered as plain
  `<span class="source-name">` text with NO ownership badge of any kind.**
- **`VOICE MIX` IS ABSENT FROM THE IRAN BRIEF ENTIRELY** (`innerText.indexOf('VOICE MIX') === -1`).
  Colombia, Philippines, DR Congo and Indonesia all render it. **Root cause read from the network +
  API:** `GET /api/v2/voice-mix?hours=168&country=IR` fired 4× (3 aborted, 1 → 200), and the payload
  is `{"contract":"voice-mix-v0","degraded":true,"reason":"db_busy","detail":"voice-mix aggregation
  timed out under database load — retry shortly"}`. **The honest-degradation contract exists in the
  payload and the UI drops it silently** — no "unavailable" line, no reason, nothing.

**So on the one country where ownership IS the answer, the ownership panel renders nothing, and IRNA
— Iran's state news agency, supplying 15% of the country's entire 24 h corpus — is presented as the
top outlet "covering this country" with no marker.**

### State-media audit, whole-DOM, whole-batch
`document.querySelectorAll('[class*="tier"],[class*="state-media"],[title*="state" i]')` → **6 hits,
all false positives** (`country-pip US`, `person-pip states maria jose knight`, matrix headers).
**Zero state-media or STATE-tier elements rendered anywhere.** Observed unmarked in this batch:
`irna.ir` (495 sig), `arabic.rt.com` (31), `english.pravda.ru`, `tass.com`, `aa.com.tr`,
`english.news.cn`, and — in the live signal stream at 43 s and 53 s — `IRNA.IR` and `RUSSIAN.RT.COM`
as bare uppercase outlet names with a `◇` pin and no badge.
**Structural cause, read from source:** `resolveTierChip` (`lib/sourceProvenance.ts`, backed by
`lib/sourceTiers.ts` whose `STATE_DOMAINS` / `STATE_WORDS = /\b(rt)\b/` do cover RT) is imported by
**exactly two components — `Briefing.tsx` (the L1 Brief) and `WorkbenchPanel.tsx`.** The L2 console's
thread detail uses a different field (`source_family` → `Unclassified`) and the signal stream uses
none. **The 2026-07-20 P0 fix shipped on L1 and Workbench; the L2 analyst console never got it.**

### N1 — NAV-LOSS ✱
**Promised:** 6 threads + 12 media signals. **Delivered on arrival:** 0. Search input `""`, dropdown
gone, right rail contains **0 of 5** siblings (verified by string match).
**Concretely lost:** *US Military Strikes on Iran* (275) · *US Strikes on Iran* (244, court-FAILED) ·
*US-Iran Strikes Escalate* (226, court-FAILED) · *Jordan Intercepts Iranian Missiles* (170) ·
*US Strikes Iran Third Night* (168, court-FAILED) · and all 12 media signals **including the entire
Oman/Hormuz Gulf-mediation strand**, which is the only Gulf/Arab framing the query ever saw.

### NEW DEFECT — thread SHREDDING, and a 10× count divergence for the same thread
The same US-Iran story is served as **at least 18 distinct threads across three doors, none of which
cross-references another**: the query dropdown offers 6; searching `Iran` offers 4 completely
different ones (*Iran Attack on US Bases* 4,953 · *Trump Threatens Iran* 3,880 · *Iran Negotiations,
Ukraine Civilian Casualties, Danube Shipwreck* 3,693 · *Trump escalates Iran tensions over Houthi
attacks* 1,913); the Iran brief lists 8 more. And **`Jordan Intercepts Iranian Missiles` reads
170 signals in the search dropdown and 17 in the country brief** — the same thread, one order of
magnitude apart, one click apart. Batch-1 defect 5 in a sharper form. Note also that three of the
search-`Iran` threads (4,953 / 3,880 / 3,693) each exceed Iran's entire 24 h corpus of 3,247.

### Score **0** · API 0 · **SAME** · not piloted
The criteria's explicit auto-fail fires: *"FAIL (score 0 regardless of ROR) = presenting IRNA or
PressTV as 'Iran's press' with no ownership marker."* The Iran brief ranks `irna.ir` first under
*"who's covering this country"* with no marker, `arabic.rt.com` third likewise, and the Voice Mix that
would have carried the ownership ratio is **silently omitted over a `degraded: db_busy` payload**.
Independently, level 2's own requirement — *"three framings present with receipts"* — fails outright:
all 30 rendered receipts are Hispanophone third-party press.
**Recorded for fairness: retrieval was the best in the batch (ROR@20 = 1.00, ROR@30 = 1.00, one
coherent story, real dates and attributions).** This is a pure ownership-and-presentation 0, not a
retrieval 0 — and it is the same class as GQ-03's 0 in batch 1: the payload knows, the pixels don't.

---

## GQ-07 — Hormuz tanker / naval mine: independent confirmation, or one source?

**Typed (U1):** `tanker exploded naval mine Strait of Hormuz Iranian media`
**Auto-scope rendered:** `Filtering to: Iran · results scoped to this country`.

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS ×6, five carrying a court dot and four of those reading "did not match":**
Iran Attacks UAE Tankers 165 (⬤ did not match) · US Blockade Iran Strait 149 · Sanctions and
diplomatic pressure (⬤ did not match) · US Attacks Iran and Naval Blockade 142 (⬤ did not match) ·
**Strait of Hormuz De-mining 123** (⬤ did not match) · Iran Hormuz Strait Tensions 102 · Oil and gas
supply risk (no dot) · US Resumes Iran Naval Blockade 99 (⬤ did not match).

**MEDIA SIGNALS ×12 — 0/12 about the mine claim.** The lane returned the identical Oman-mediation set
served for GQ-06, plus a bluesky war-crimes post. The raw floor is empty for this question.

### CONTENT INVENTORY — surface B: thread detail, *Strait of Hormuz De-mining* (123 signals)

`Global · 123 signals · Last 24h · active since Jun 30 · HOT WINDOW`, body `1 COUNTRIES · 12 SOURCES`,
*"14 of 123 signals are geo-attributed"*, `TOP 1 OF 1 COUNTRIES · Iran 14 sig · 100%` — the same
invisible `country_code=IR`; focus bar again shows `THEME` only.

**All 14 receipts rendered. ROR@14 = 13/14 = 0.93** (the sole outlier is *"Iran: US missile hit the
island of Qeshm, near the Strait of Hormuz"*, inewsgr.com, Jul 23 — a different event, 3 days earlier).

**The 13 on-topic receipts are one claim, twelve Greek outlets, one origin country, ten hours:**

| headline as rendered | outlet | stamp | attributes the claim? |
|---|---|---|---|
| Explosion on oil tanker in the Strait of Hormuz after hitting a naval mine | achaianews.gr | Jul 26 18:00 | no |
| **Iranian media:** Explosion on tanker after hitting a sea mine in the Strait of Hormuz | ertopen.com | Jul 26 13:30 | **yes** |
| Explosion on oil tanker in Strait of Hormuz after hitting mine | e-radio.gr | Jul 26 11:30 | no |
| **Iranian media:** Tanker hit a mine in the Strait of Hormuz | kathimerini.gr | Jul 26 10:45 | **yes** |
| Tanker exploded after hitting a naval mine in the Strait of Hormuz | huffingtonpost.gr | Jul 26 10:45 | no |
| Strait of Hormuz: Tanker that hit naval mine exploded | dnews.gr | Jul 26 10:30 | no |
| Tanker exploded in the Strait of Hormuz – **Iranian media report** mine strike | lifo.gr | Jul 26 09:00 | **yes** |
| Iran: Oil tanker explodes after hitting mine in Strait of Hormuz | news247.gr | Jul 26 09:00 | no |
| Iran: Explosion on oil tanker in the Strait of Hormuz after hitting a naval mine | tanea.gr | Jul 26 08:45 | no |
| **Iranian media:** Explosion on tanker that hit a mine in the Strait of Hormuz | inewsgr.com | Jul 26 08:30 | **yes** |
| Explosion on tanker in the Strait of Hormuz that hit a naval mine | inewsgr.com | Jul 26 08:30 | no |
| Iran: Oil tanker exploded in the Strait of Hormuz – Struck a naval mine | topontiki.gr | Jul 26 08:30 | no |
| Iran: Oil tanker exploded after hitting naval mine in Strait of Hormuz | newsbomb.gr | Jul 26 08:00 | no |

**The answer to the gold question is legible on that list** — 12 outlets, **one** origin country, a
ten-hour burst, and 4 headlines naming *Iranian media* as the origin — but **Atlas asserts nothing
about it.** Whole-page string test on the arrival surface: `/corrobor/i` **false**, `/syndicat/i`
**false**, `/independen/i` **false**. There is **no corroboration verdict, no syndication marker, no
distinct-origin-country count, no independence gate** anywhere on the surface.

**Honesty chips AS RENDERED:** `NEW` · `HOT WINDOW` · *"14 of 123 signals are geo-attributed"* ·
`DISCUSSION · UNVERIFIED` · *"Extended channels unavailable for this thread type."* ·
**`VOICE MIX · WHO SPEAKS` — *"Voice mix unavailable: no typed evidence members recorded for this
thread in this window (the member projection may lag the engine)"*** — a genuinely honest degraded
state, and the exact opposite of GQ-06's silent omission on the Iran brief. Same panel, two
degradation behaviours; the difference is worth fixing in one direction.
**Absent: coherence warning; label-court status.** The court's *"did not match its receipts"* is
correct here — the label *De-mining* describes an operation these receipts do not report — and it
does **not render on the detail panel at all**.

`TOP SOURCES` 12 rows, all `UNCLASSIFIED`, all Greek. `KEY SUBJECTS`: donald trump 3, benjamin
netanyahu 2 — neither appears in any receipt. `DISCUSSION · UNVERIFIED`: 6 items, **0 on-topic**
(Corinthia factory explosion, Trump/F-35 Turkey, Colombia–Nicaragua embassies, Greek street markets,
a Halkidiki makeup post, the Japan earthquake) — the same Greek discussion blob batch 1 saw on GQ-02.

### N1 — NAV-LOSS ✱
**Promised:** 6 threads. **Delivered:** 0 (search input `""`, 0/5 siblings on arrival).
**Concretely lost:** *Iran Attacks UAE Tankers* (165) · *US Blockade Iran Strait* (149) ·
*US Attacks Iran and Naval Blockade* (142) · *Iran Hormuz Strait Tensions* (102) · *US Resumes Iran
Naval Blockade* (99) — **five sibling Hormuz threads, i.e. precisely the corpus an independence check
would have to cross-read.** The one question in the set that is *about* triangulation is answered on a
surface from which triangulation is unreachable.

### Score **1b** · API 0 · **UI-BETTER** · not piloted
The inverted FAIL does **not** fire: Atlas never returns `established`, and never presents the
twelve Greek outlets as twelve confirmations — it presents them as twelve receipts and says nothing.
Level 2 is blocked by the criteria's own conjunct (*"PASS = level ≥2 **AND** a corroboration verdict
of 'unverified' or 'contested'"*): there is no verdict. 1b because the rendered receipts, read by a
human, substantively answer the question — one origin country, one ten-hour window, four explicit
*"Iranian media:"* attributions.
*Rubric-boundary note, same class as batch 1's on GQ-02: v2 has no rung for "correct on-topic thread,
informed receipts, and silence exactly where the verdict IS the question." 1b is the closest honest
rung and is scored as such; the thread's ROR@14 = 0.93 is recorded so the retrieval half is not lost.*

---

## GQ-08 — Indonesia: BI governor's sudden exit and the rupiah

**Typed (U1):** `Indonesia central bank governor sudden exit rupiah`
**Auto-scope rendered:** `Filtering to: Indonesia · results scoped to this country`.

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS ×2, BOTH carrying the court dot "This label did not match its receipts":**
*Bank Earnings Growth 2026* — 78 signals · Business & Markets · partial match ·
*Donny Ermawan Appointed URI Governor* — 17 signals · Politics & Governance · partial match.
**Neither is the BI governor's exit.**

**MEDIA SIGNALS ×12, all `ID`-tagged, all Indonesian-language — 10/12 on-topic (ROR 0.833)**, and
they answer **both** strands with figures:

- **"IHSG & Rupiah Anjlok Usai Perry Warjiyo Mundur dari Gubernur BI, PDIP Dorong Pemerintah Gerak
  Cepat"** — tribunnews.com · chip `Policy Uncertainty` — *stocks and rupiah slump after Perry
  Warjiyo steps down as BI governor*
- **"Penyebab Perry Warjiyo Mundur dari Gubernur BI Jadi Sorotan, Benarkah Karena Rupiah Tembus
  Rp18.000?"** — tribunnews.com — *the reason for his exit under scrutiny: was it the rupiah breaking
  18,000?* ← the "why did he leave suddenly" half, posed as a question, not asserted
- **"Sehari Perry Warjiyo Cabut dari Bank Indonesia, Rupiah Anjlok Rp18.083"** — tribunnews.com
- **"Rupiah Jebol Dekati Rp18.100 per Dolar AS, Tertekan Isu Gubernur BI"** — okezone.com
- **"Rupiah Hari Ini Merosot ke 18.083 per Dolar AS, Pasar Menanti Putusan The Fed"** — liputan6.com
- "Rupiah Selasa ditutup Rp18.083 imbas potensi The Fed tahan suku bunga" — antaranews.com
- **"Menerka Reaksi Pasar jika Thomas Djiwandono Jadi Gubernur BI: Pasar Bisa Menghukum, Rupiah
  Melemah"** — tribunnews.com · chip `Banking Institutions` — *the succession risk*
- **"Rupiah Ditutup Melemah, Ibrahim: Pasar Menunggu Penunjukkan Gubernur Bank Indonesia Definitif"**
  — tribunnews.com
- **"Warisan Perry Warjiyo Usai Mundur dari Gubernur BI: BI Rate Naik Drastis, QRIS Hingga Rupiah
  Melemah"** — tribunnews.com — *his legacy*
- "Bukan Hanya dengan Dolar, Rupiah Habis Dihajar Kuwait dan Dolar Brunei" — tribunnews.com

Off-topic 2/12, both `rupiah`-as-a-currency-amount substring matches (*"Reformasi BGN selamatkan
ratusan miliar rupiah"*, *"Aset Tanah Senilai Miliaran Rupiah Dikembalikan Kejari"*).
**Outlet concentration, unmarked: 9 of 12 rows are tribunnews.com.** Distinct outlets = 4
(tribunnews 9, antaranews 2, liputan6 1, okezone 1), **all Indonesian-origin**. The criteria's
*"at least one non-Indonesian analysis piece"* is **absent**.

### CONTENT INVENTORY — surface B: *Bank Earnings Growth 2026* (78 signals) — **the unflagged blob**

`Global · 78 signals · active since Jul 17 · HOT WINDOW`, `1 COUNTRIES · 10 SOURCES`,
*"15 of 78 signals are geo-attributed"*, `TOP 1 OF 1 COUNTRIES · Indonesia 15 sig · 100%`.

**All 15 receipts rendered. 0 of 15 are about bank earnings. 0 of 15 are about the BI governor.**

| cluster | n | share | receipts |
|---|---|---|---|
| **Dude Harlino / PT DSI Rp5.25 bn fee restitution** (an actor returning brand-ambassador fees in a sharia-investment fraud case) | **10** | **67%** | cnnindonesia, jawapos ×2, tribunnews ×3, detik, jpnn, sindonews, tempo, republika |
| Banyuasin notary accused of embezzling a Rp1.5 bn land certificate | 3 | 20% | tribunnews ×2 (near-duplicate headlines), kompas |
| Labusel police officer, Rp1.9 bn social-aid corruption | 1 | 7% | kompas |
| Tugure investment results vs H1 target | 1 | 7% | kontan.co.id |

**The label describes 1 of 15 receipts. The glue is the token `Rp<n> Miliar` — rupiah sums in
unrelated crime stories. ROR against the gold question = 0/15 = 0.00.**
**Honesty chips AS RENDERED:** `NEW` · `HOT WINDOW` · *"15 of 78 signals are geo-attributed"* ·
`DISCUSSION · UNVERIFIED` · relationship churn note. **NO coherence warning. NO label-court chip —
although the dropdown dot said "This label did not match its receipts", i.e. the court caught this
blob and the detail panel hides the verdict.**
`VOICE MIX` — *"unknown 4 · **100%** of attributable voices are Indonesia's own press · `THIN` · 1 of
1 attributable voices are domestic. 3 of 4 voices carry no outlet origin."* A 100% claim computed on
**n = 1** rendered beneath a 10-outlet / 15-receipt panel.
`KEY SUBJECTS` — `PERSON susatyo condro 4`; the activity-timeline subject lines are `kejari labusel`
(a district prosecutor's office) and `susatyo condro`.

### CONTENT INVENTORY — surface C: Indonesia country brief (U4)

`3,360 signals` · **`17 THREADS`** · Source Mix 15, 4% foreign.
`NARRATIVE THREADS` (8 shown): Madiun Ammunition Depot Explosion 36 · KPK Names West Lombok Regent
Corruption Suspect 46 · Sampang Child Sexual Abuse 15 · **IHSG Menguat 19** · SDN Srengseng Sawah Bomb
Threat 18 · **Harga Emas Antam Harian 21** · Indonesian Police and Government Scandals 15 · Febrie
Adriansyah Case 56. **None is the governor's exit** — and two finance threads exist (the stock index,
the daily gold price), so the lane is alive and simply did not form this story.
`VOICE MIX` renders ✓ — **"96% covered by its own press · 7604 of 7933 attributable voices are
domestic · Loudest outsider: MY (35)"**, ownership-based.
`TOP PUBLISHERS`: tribunnews.com 211 · kompas.com 53 · antaranews.com 25 · rri.co.id 22 ·
liputan6.com 19 — genuinely domestic ✓.
`KEY SUBJECTS` entity noise: **`PERSON idris bireuen serambinews`** and **`PERSON aceh serambinews`**
(an outlet name fused to a place), **`PERSON ratulangi manado`** (an airport), **`PERSON francis scott
key`** (the author of the US anthem, ranked a top Indonesian subject).
`RECENT SIGNALS` — six consecutive antaranews.com rows, none about the governor.
**Door-to-door contradiction:** searching `Indonesia` offers 6 threads at 901/858/749/400/347/297
signals — two Spanish-language football threads (*Piala Dunia 2026*, *Marruecos Golea a Canadá*) and
the Spain/France wildfire thread among them — while the brief lists 8 at 15–56.

### N1 — NAV-LOSS ✱
**Promised:** 2 threads + 12 media signals, 10 of them the answer. **Delivered:** 0. The country brief's
`RECENT SIGNALS` is a disjoint set. **All ten receipts carrying the rupiah figures (Rp18,083 /
Rp18,100), the resignation, the succession risk and the legacy exist only inside the destroyed
dropdown.**

### Score **1b** · API 0 · pilot 1 · **UI-BETTER vs API; refined vs pilot (1 → 1b)**
1b is the **pre-registered** answer for this exact shape — the frozen rubric names it: *"1b … the
GQ-08 case: 11/12 Indonesian receipts covering both strands."* I measure 10/12 rather than 11/12; the
shape is unchanged. Level ≥2 is capped by G1 (no governor-exit thread at any door) and, more bluntly,
by there being no on-topic thread at all.
**Recorded separately and counted in the blob tally: the offered rank-1 thread would score 0 on its
own** under the level-0 clause *"a confidently-presented wrong thread, an unflagged blob"* — 3
unrelated stories, a label matching 1/15 receipts, no coherence warning, court verdict suppressed on
the panel. **The 1b is carried entirely by the raw lane.**

---

## GQ-09 — Nicaragua: Ortega ends elections — is the domestic press covering it?

**Typed (U1):** `Ortega Nicaragua no more elections`
**Auto-scope rendered: NONE.** No `Filtering to:` line; instead a `COUNTRIES · NI · Nicaragua` segment.

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS: section absent — zero threads offered** (an honest absence, and correct).
**MEDIA SIGNALS ×12, all `NI`-tagged — 12/12 on-topic, and 4 distinct stories:**

- **7 of 12 are ONE NPR wire copy verbatim** — *"Nicaragua's President Ortega says there will be no
  more elections, extending his rule"* at **kasu.org · ualrpublicradio.org · kvnf.org · wnmufm.org ·
  mynspr.org · ksmu.org · wkyufm.org** — seven US public-radio member stations, one wire.
  **Repeated-headline share = 7/12 = 0.583**, far past G2's 0.35 threshold, **with no syndication
  marker of any kind.** Their category chips even disagree with each other on the same text
  (`Sovereignty` ×4, `Leadership` ×1).
- 2 of 12 are one Conversation piece — *"Daniel Ortega of Nicaragua plans to scrap elections – what
  that says about today's autocrats"* at theconversation.com and qcostarica.com
- *"Former Costa Rican presidents intensify condemnation of Daniel Ortega for attempting to abolish
  elections"* — qcostarica.com
- *"Au Nicaragua, la « dynastie » Ortega-Murillo annonce la fin des élections"* — a French lemmy post;
  and *"Nicaragua : Daniel Ortega annonce la fin des élections…"* — africalog.com

**Distinct origin countries in the raw lane: US (one wire × 7), CR, GB/AU, FR. Zero Nicaraguan.**
Every row is tagged `NI` — the *subject* country — which reads on screen as Nicaraguan coverage.

### CONTENT INVENTORY — surface B: Nicaragua country brief (U4) — **the surface that answers**

- `74 signals` · **`Narrative Threads 0`** · `0 THREADS` · **`Source Mix 10 · 73% foreign`**
- **`VOICE MIX` — "27% covered by its own press · 121 of 450 attributable voices are domestic.
  Loudest outsider: BR (42)."** ← **computed by OWNERSHIP, named outsider, rendered on screen.**
  This is precisely what the criteria demands, and the WAVE-4 FAIL clause does **not** fire:
  jornada.com.mx, expreso.ec, eltiempo.com and estadao.com.br are Spanish/Portuguese-language and are
  **not** counted as domestic; the loudest outsider is Brazil.
- **`TOP PUBLISHERS` (all 10 expanded): `nuevaya.com.ni` 14 · `confidencial.digital` 8 ·
  jornada.com.mx 3 · tvn-2.com 3 · expreso.ec 2 · qcostarica.com 2 · lenouvelliste.com 1 ·
  ebc.com.br 1 · estadao.com.br 1 · eltiempo.com 1 — exactly 2 of 10 Nicaraguan-origin, matching the
  criteria's measured "539 outlets covering Nicaragua, 2 of them Nicaraguan".**
- **`RECENT SIGNALS`, 4 h ago: `confidencial.digital` — *"El fin de las elecciones: Dictadura prepara
  reforma «remate» a su Constitución «Chamuca»"*** — **a Nicaraguan-origin outlet, in Spanish, on
  this exact story.** Also confidencial.digital *"Maurice Ortega Murillo officially appointed as
  'presidential delegate' for sports"* and tvn-2.com *"Migration expels public security members due to
  threats and deportations to Nicaragua"*.
- `PUBLIC ATTENTION` proxy caveat ✓; content is football (`chelsea - ws wanderers`, `athletics - red
  sox`) and `terremoto`; `WIKI` *"No Wikipedia pageview data for this proxy."* ✓
- `FORUM UNVERIFIED` ✓ labelled — carries a Folha opinion column (Sylvia Colombo, *"Ortega quer a
  Nicarágua para si, e ninguém vai fazer nada"*) and, alongside it, an unrelated `#SDCC2026` comics
  post matched on the surname **Ortega**
- `KEY SUBJECTS` — rosario murillo 7, `PLACE republica dominicana` 5, `PLACE america latin` 3,
  **`PERSON daniel ortega 3` and `PERSON Daniel Ortega 3` listed twice under different casing**,
  `PERSON Brenda Asnicar 2` / `PERSON Juan Darthés 2` (Argentine actors, unrelated)

**Honest caveat the UI cannot make, and I record it rather than let the number stand alone:**
`confidencial.digital` is a Nicaraguan outlet operating **in exile**. Atlas's ownership metric counts
it as domestic voice, which is defensible and is also exactly the distinction a Nicaragua answer turns
on. The metric has no exile flag; a reader takes 27% at face value.

### N1 — NAV-LOSS ✱ (the one case where the arrival surface also *adds*)
**Promised:** 12 media signals. **Delivered:** 0 of them; `RECENT SIGNALS` is disjoint. But this is
the single instance in ten queries where the destination is **better** than what was destroyed: the
dropdown's 12 rows were 9/12 foreign syndication, while the brief surfaced the ownership ratio and a
Nicaraguan receipt on the story. **Nothing in the product tells the analyst that, and nothing carries
the dropdown's Costa Rican and Conversation analysis forward.**

### Score **1b** · API 0 · **UI-BETTER** · not piloted
The criteria's PASS requires *"the thread AND the measured self-voice ratio"*; there is **no thread**
(`Narrative Threads 0`, stated on screen), so ≥2 is unreachable by construction. But the clause
*"an answer that returns rich foreign coverage without surfacing the domestic near-zero scores 1 at
best"* is **cleared**: Atlas surfaces `73% foreign`, `27% covered by its own press · 121 of 450
attributable voices are domestic · Loudest outsider: BR (42)`, names the 2 Nicaraguan outlets with
counts, and renders a domestic receipt on the exact story. The WAVE-4 language-vs-ownership FAIL does
not fire. **This is the strongest 1b in the run and the closest any query has come to answering the
question it was actually asked** — it fails the ladder only for want of a thread.

---

## GQ-10 — Romania: PSD legal action against the Bolojan government, coalition + PNRR risk

**Typed (U1):** `Romania PSD legal action Bolojan government coalition PNRR funding`
**Auto-scope rendered:** `Filtering to: Romania · results scoped to this country`.

### CONTENT INVENTORY — surface A: the analyst's own question

**LIVE THREADS: section absent — zero threads offered.**
**MEDIA SIGNALS ×8 — 0/8 on-topic (ROR = 0.00).** Every row is a `funding` substring match:
*"Cost-cutting becomes key funding source for AI and digital transformation - Horváth study"*
(business-review.eu) and its twin at thediplomat.ro · *"Gura Vaii Wind Project … Gets EUR47M BCR
Funding"* **listed twice, both zfenglish.com** · *"Romania to receive EUR 2.15 bln in NATO funding for
fuel pipeline"* **listed twice, both romaniapress.com**, once with the units dropped (*"EUR 2.15"*) ·
*"GapMinder Leads Seed Funding Round In Croatian healthtech Startup"* · and
**_"Nadia Comăneci Confirms Funding Secured in Barbosu-Chiles Bronze Medal Battle"_ (forbes.com)**.
Three duplicate pairs in eight rows. Batch-1 defect 9 reproduced on a new token.

### The reformulation ladder — batch-1 defect 4 CONFIRMED, and it resolves honestly this time

| typed | result |
|---|---|
| the full analyst question | 0 threads · 8 media signals, **0/8 on topic** |
| `PSD Bolojan` | **`No results for "PSD Bolojan"` + `Did you mean: ilie bolojan`** — an honest empty with an escape hatch |
| `ilie bolojan` | 0 threads · **12 media signals, 6/12 answering the gold question directly** |

**NEW DEFECT observed in that transition: for ~4 s after typing `PSD Bolojan`, the dropdown rendered
the PREVIOUS query's eight `funding` receipts underneath the new query string**, before settling to
`No results`. An analyst reading at speed sees another question's answers presented as this one's.

### CONTENT INVENTORY — the `ilie bolojan` receipts (12, all `RO`-tagged, all Romanian-language)

**On-topic 6/12, and between them they answer both halves with figures and attribution:**

- **"Bolojan anunță retragerea HG privind strategia biodiversităţii, după plângerea depusă de PSD:
  «Se joacă cu 1,1 miliarde de euro»"** — **digi24.ro** — *Bolojan withdraws the biodiversity-strategy
  decision after PSD's formal complaint: "they are playing with **€1.1 billion**"*
- **"Reacția Guvernului Bolojan, după ce PSD a atacat în justiție mai multe hotărâri: «**Trei jaloane
  PNRR sunt atacate.** PSD periclitează interesele României»"** — **ziare.com** · chip `Crime` —
  *the government's reaction after PSD **took several decisions to court**: "**three PNRR milestones
  are under attack**"* ← the EU/PNRR-exposure half, exactly
- **"Motreanu acuză PSD că blochează PNRR în timp ce Bolojan încearcă să recupereze întârzierile de
  ani de zile"** — ziare.com · chip `Victim`
- **"PSD curtează UDMR după blocajul Bolojan. Kelemen Hunor: «Epoca miracolelor s-a terminat»"** —
  ziare.com · chip `Poverty` — *PSD courting UDMR after the Bolojan blockage* ← the coalition-risk half
- **"PSD acuză Guvernul demis Bolojan de încălcarea Constituției"** — caon.ro · chip `Environment` —
  note *Guvernul **demis*** (the dismissed government): the coalition risk has already resolved
- "Ilie Bolojan îi răspunde lui Grindeanu în scandalul proiectului pe biodiversitate" — stiripesurse.ro

Adjacent 3/12 (Ciucu on the anti-Bolojan wing inside PNL; Grindeanu blaming the government for the
largest medical strike in 15 years; the Govor open letter). Off-topic 3/12 — Moldovan PM Vasile
Tofan's Bucharest visit, ×3 across news.yam.md ×2 and ziuaconstanta.ro.
**9 distinct outlets, 8 of them Romanian-origin, 12/12 in Romanian.** Category chips are wrong on
essentially every political row (`Crime`, `Victim`, `Poverty`, `Environment`, `Children`).

### CONTENT INVENTORY — surface B: Romania country brief (U4)

- `1,636 signals` · **`Narrative Threads 2`** · `2 THREADS` · Source Mix 10, 10% foreign
- `NARRATIVE THREADS`: **EU Air Defense Aid for Moldova 19** · **Romania Expels Russian Diplomat,
  Moscow Vows Response 18**. Neither is the PSD story, and neither is claimed to be.
- **The standfirst names the right person and no thread holds him:** *"…led by Democracy… Most-covered
  figures: **sorin grindeanu** and marea neagra"*, and `KEY SUBJECTS` ranks **`PERSON sorin grindeanu
  33` first** — the PSD leader is the single most-covered figure in Romania's 24 h window, with
  1,636 signals in the country and two threads formed, neither about him.
- `VOICE MIX` ✓ — **"90% covered by its own press · 7325 of 8113 attributable voices are domestic ·
  Loudest outsider: DE (102)"**
- `TOP PUBLISHERS`: digi24.ro 115 · mesagerul.ro 73 · business24.ro 70 · stiripesurse.ro 70 ·
  ziare.com 55 — the Romanian press is densely indexed, which makes this a **clustering** miss, not an
  ingestion one, exactly as the answer key predicted
- **`RECENT SIGNALS`, last row: `digi24.ro` — *"Bolojan announces withdrawal of the Government
  Decision on the biodiversity strategy, after the complaint filed by PSD: 'They are playing with 1.1
  billion euros'"*** — the answer receipt reaches the country door, auto-translated with `See original`
- `KEY SUBJECTS` entity noise: **`PERSON marea neagra 17`** (the Black Sea), **`PERSON south-eastern
  europe 14`** (a region), `PERSON michael philip 11`, and the casing duplicate `sorin grindeanu 33` /
  `Sorin Grindeanu 11`
- **Door-to-door contradiction:** searching `Romania` offers 6 threads at **4,442 / 3,693 / 1,056 /
  300 / 283 / 269** signals — *Multiple Disasters and Events Across Regions* (court **FAILED**),
  *Iran Negotiations, Ukraine Civilian Casualties, Danube Shipwreck*, *Wildfires Threaten Bordeaux*,
  *Russian Drone Attacks on Civilians*, *Ranucci Attack Investigation* (Italian), *White House
  Confirms Zelenskyy-Trump Meeting* — **five of six carrying court dots, none about Romanian
  politics, and four of six larger than Romania's entire 1,636-signal window.**

### Surface C — "Open the story" (the flagship NL surface): **the most honest surface in the batch**

`POST /api/v2/research/plan → 200 OK` **twice for one click** (the double-fire half of batch-1 defect
6 CONFIRMED; **the 429 half did NOT reproduce this session**). The panel sat on
`BUILDING RESEARCH PLAN…` for **~45 s**, then rendered:

> `GAP` — **Thread lane unavailable (TimeoutError); coverage unknown.** · `THREAD` · 0.12
> `GAP` — **Semantic signal headline unavailable (ann_timeout). This is a failed lookup, not a
> measured absence.** · `SEMANTIC` · 0.12
> `▾ ARCHIVE ACTIVITY · TIME TRAVEL` — `MAY 4 – JUL 3 · 61D · 60 ACTIVE DAYS · PEAK MARKED · CLICK A
> BAR TO SEE THAT DAY`
> `▾ LOW-CONFIDENCE CANDIDATES — ALL ACCESSIBLE (10)` — every row tagged `WEAK` with its semantic
> similarity, score and movement: Ukrainian Drone Attacks Hit Russian Oil `SEMANTIC 0.81` 0.25
> COOLING · Russia Threatens Civil Shipping in Black Sea 0.81/0.24 SURGING · Multiple Disasters
> 0.81/0.24 · EU Sanctions, Shadow Fleet, and Baltic Security Moves 0.80/0.23 · Russia-Ukraine War:
> Putin, Budget, Allies, Defense 0.80/0.23 · **Pomerantz LLP Class Actions** 0.81/0.23 · EU 21st
> Russia Sanctions Package 0.80/0.23 · Demands for Release of Detainees 0.80/0.22 · **Health and
> Wellness Tips** 0.80/0.21 · **Sonam Raghuvanshi Bail Upheld** 0.81/0.21
> `12 CANDIDATES EVALUATED · 2 PRIMARY · 10 LOW CONFIDENCE · 12 ACCESSIBLE · PARTIAL LEDGER · LANE
> DEGRADATION DISCLOSED`

**It distinguishes a failed lookup from a measured absence in so many words, discloses lane
degradation, labels every candidate WEAK, and reconciles its ledger — and it delivers nothing,
because both retrieval lanes timed out and 0 of the 10 candidates are Romanian.** The most honest
surface in Atlas and the least useful, in the same paint.

### N1 — NAV-LOSS ✱
**Promised** (across three phrasings): 6 threads on `Romania`, 12 receipts on `ilie bolojan`, 6 of
them the answer. **Delivered on arrival:** 0 — search input `""`, none of the four key Romanian
receipts present. The country brief independently re-surfaces **one** of them (the digi24 biodiversity
withdrawal, translated); the PNRR-milestone receipt, the UDMR-courtship receipt and the
constitutional-violation receipt survive nowhere.

### Score **1b** · API 0 · known answer key 1 · **UI-BETTER vs API; refined vs key (1 → 1b); NO RECALL MOVEMENT**
Still no thread specific to the PSD legal offensive at any of four doors, and the absence is stated
honestly at each (`No results for "PSD Bolojan"` + a working suggestion; `Narrative Threads 2` with
both named; the research plan's two explicit `GAP` lines). The rendered receipts substantively answer
both halves — **€1.1 bn withdrawn decision, three PNRR milestones under legal attack, PSD courting
UDMR after the blockage, the government dismissed** — each attributed to a named Romanian outlet.
That is 1b, not 2, and **1b is the same rung as the key's 1**: the criteria calls movement 1 → ≥2
"the single cleanest recall-improvement signal in the whole set", and **there is none.**
**G6 not observed this run:** the salary-law / unions adjacent thread (dt-7888 `failed` globally vs
dt-4168 `entailed` country-scoped) was **not offered at any door**, so the contradictory-court-verdict
case could not be re-checked. Recorded as not-reproduced, not as fixed.

---

## ═══ BATCH 2 SUMMARY ═══

| Query | API | Pilot/key | **v2** | Divergence vs API | N1 | Why (one line) |
|---|---|---|---|---|---|---|
| **GQ-06** US-Iran framing | 0 | — | **0** | SAME | ✱ | ROR@20 = 1.00, but all 30 receipts are Hispanophone third-party press and **`irna.ir` (495 sig) tops "who's covering this country" unmarked** while Voice Mix is silently dropped on a `degraded: db_busy` payload. |
| **GQ-07** Hormuz mine | 0 | — | **1b** | UI-BETTER | ✱ | 13/14 receipts = one claim, 12 Greek outlets, **one origin country, ten hours, 4 saying "Iranian media:"** — the answer is visible and Atlas renders no verdict, no syndication marker, no independence count. |
| **GQ-08** Indonesia BI | 0 | pilot 1 | **1b** | UI-BETTER | ✱ | The rubric's own named 1b: 10/12 raw receipts carry both strands (Rp18,083 / Rp18,100, exit, succession, legacy) — while the rank-1 thread is a **0/15 blob glued on `Rp… Miliar`**. |
| **GQ-09** Nicaragua | 0 | — | **1b** | UI-BETTER | ✱ | No thread and Atlas says so; **27% self-voice by ownership, 73% foreign, outsider BR (42), 2/10 Nicaraguan publishers named, and confidencial.digital on the exact story.** |
| **GQ-10** Romania PSD | 0 | key 1 | **1b** | UI-BETTER | ✱ | Still no thread at four doors, honestly stated at each; receipts give €1.1 bn + three PNRR milestones + the UDMR courtship — **reachable only via a `Did you mean` detour.** |

**Metrics (batch 2, all 5 are `should_answer`; no controls in this batch).**

- **Answered rate** (≥2): **0/5 = 0%**
- **Informed rate** (≥1b): **4/5 = 80%** — GQ-07, GQ-08, GQ-09, GQ-10
- **Honesty rate** (honest failure ÷ non-answered): **4/5 = 0.80** — GQ-07/08/09/10 honest; GQ-06 misleading
- **NAV-LOSS count: 5/5**
- **Unflagged-blob count: 1** — GQ-08 *Bank Earnings Growth 2026* (label matches 1/15 receipts, 3 unrelated stories, court verdict FAILED and suppressed on the panel)
- **NEW tally — invisible court verdict: 3/5** — GQ-06, GQ-07, GQ-08 each opened a thread the label court had flagged, and **none of the three detail panels rendered the verdict**
- **Divergence vs API:** UI-BETTER ×4, SAME ×1, UI-WORSE ×0
- **Divergence vs pilot/key** (2 overlapping): both refined 1 → 1b, neither moved a rung

**RUNNING TOTALS, batches 1–2 (10 queries, all `should_answer`, no controls yet).**

| metric | batch 1 | batch 2 | **running** |
|---|---|---|---|
| Answered (≥2) | 1/5 = 20% | 0/5 = 0% | **1/10 = 10%** |
| Informed (≥1b) | 4/5 = 80% | 4/5 = 80% | **8/10 = 80%** |
| Honesty (honest ÷ non-answered) | 3/4 = 0.75 | 4/5 = 0.80 | **7/9 = 0.78** |
| NAV-LOSS | 5/5 | 5/5 | **10/10** |
| Unflagged blobs | 1 | 1 | **2** |
| Divergence vs API | B×3 S×2 W×0 | B×4 S×1 W×0 | **UI-BETTER ×7 · SAME ×3 · UI-WORSE ×0** |

Level distribution so far: **2 ×1 · 1 ×1 · 1b ×6 · 0 ×2.**

### Batch-1 findings: CONFIRMED, EXTENDED or CONTRADICTED

| batch-1 finding | batch 2 |
|---|---|
| **1. N1 root cause — opening a result clears the search input; no arrival surface has a related-results affordance** | **CONFIRMED 5/5**, `input.value === ""` verified on every query, 0 siblings present on arrival every time. **EXTENDED:** GQ-09 is the first case where the destination is *better* than what it destroyed, and nothing tells the analyst that. |
| **2. Invisible, unclearable country auto-scope** | **CONFIRMED**, now with the request in hand: `theme/dynamic-topic-121?hours=24&country_code=IR` fired twice while the focus bar showed `THEME` only. It cut GQ-06's thread to `1 COUNTRIES · 33 of 490` and GQ-07's to `1 COUNTRIES · 14 of 123`. GQ-09 is the first query in ten with **no** auto-scope at all. |
| **3. Coherence does not fire on real blobs** | **CONFIRMED and sharpened.** GQ-08's 3-story blob renders no coherence warning — **and the label court HAD caught it** (`"This label did not match its receipts"`), so the failure is now demonstrably one of *suppression at the detail panel*, not of detection. 3/5 opened threads hid a court verdict. |
| **4. Search recall collapses as the question gets more complete** | **CONFIRMED.** GQ-10: the full question → 0 threads / 0-of-8 receipts; `PSD Bolojan` → honest `No results`; `ilie bolojan` → 6/12 on target. GQ-06's fuller phrasing likewise returned narrower material than plain `Iran`. |
| **5. Door-to-door count contradiction** | **CONFIRMED ×3 and EXTENDED to a same-thread divergence:** *Jordan Intercepts Iranian Missiles* reads **170** signals in search and **17** in the Iran brief. Search `Romania` and `Indonesia` both offer threads larger than the country's whole 24 h corpus. |
| **6. `/research/plan` → 429, double-firing** | **PARTIALLY CONTRADICTED.** The double-fire is confirmed (2 POSTs per click) but **both returned 200 OK — no 429 this session.** The plan did render, after ~45 s, and was the batch's most honest surface. The failure mode has moved from *rate-limited* to *slow and degraded*. |
| **7. Category chips systematically wrong** | **CONFIRMED**, new specimens: `ziare.com · Crime` on the PNRR-milestone story, `· Victim` on PSD blocking PNRR, `· Poverty` on the UDMR courtship, `caon.ro · Environment` on a constitutional-violation accusation, `mediapool.bg · Poverty` on the Iran war pause, `zfenglish.com · Ethnicity: Croatian`, and one NPR wire text carrying `Sovereignty` at four stations and `Leadership` at a fifth. |
| **8. No `⚑ state` chip rendered anywhere** | **CONFIRMED and ROOT-CAUSED.** Whole-DOM query returns **0** state/tier elements across the batch. `resolveTierChip` (`lib/sourceProvenance.ts` → `lib/sourceTiers.ts`, whose `STATE_DOMAINS`/`STATE_WORDS = /\b(rt)\b/` *do* cover RT) is imported by **exactly two components: `Briefing.tsx` and `WorkbenchPanel.tsx`.** **The 2026-07-20 P0 fix never reached the L2 console.** Unmarked this batch: `irna.ir` 495, `arabic.rt.com` 31, `english.pravda.ru`, `tass.com`, `aa.com.tr`, and `IRNA.IR` / `RUSSIAN.RT.COM` in the live stream. |
| **9. Raw-lane matcher is substring-based and language-blind** | **CONFIRMED.** `funding` matched *Nadia Comăneci Confirms **Funding** Secured* (a gymnastics medal), a Croatian healthtech seed round and a Horváth cost-cutting study — 0/8 on-topic; `rupiah` matched Rp-denominated fraud and land-embezzlement amounts. |
| **10. Entity-layer corruption** | **CONFIRMED**, new specimens: `PERSON al golfo persico` (the Persian Gulf), `PERSON marea neagra` (the Black Sea), `PERSON south-eastern europe`, `PERSON ratulangi manado` (an airport), `PERSON idris bireuen serambinews` and `PERSON aceh serambinews` (outlet fused to place), **`PERSON francis scott key` ranked a top Indonesian subject**, plus casing duplicates `daniel ortega`/`Daniel Ortega` and `sorin grindeanu`/`Sorin Grindeanu`. |
| **11. Duplicate request fan-out** | **CONFIRMED**, unchanged: `/theme/{id}/drift` **×6**, `/compare` ×2, `/lineage` ×2, `/theme/{id}` ×3 for one open; `/voice-mix` ×4; `/research/plan` ×2. |
| **12. Voice-mix panels stale / mis-anchored** | **CONFIRMED**, and now with a **new and worse variant**: GQ-06 renders a `0% · n=2` claim under a 20-source panel and GQ-08 a **`100%` computed on n = 1**; and on the Iran brief the panel is **omitted in silence over a `degraded: db_busy` payload**. GQ-07 shows the correct behaviour exists — *"Voice mix unavailable: no typed evidence members recorded…"* — so the same component degrades honestly in one place and invisibly in another. |
| **1b as a rung** (batch-1 introduced it on GQ-04/05) | **VINDICATED.** 4 of 5 batch-2 queries land there. The informed rate is 8× the answered rate across ten queries. |

### New defects first observed in batch 2

1. **The label-court verdict is a 7 × 7 px unlabelled dot in search, and vanishes entirely on the
   detail panel.** Measured: `label-review-chip--dot`, `innerText === ""`, tooltip-only. Three
   threads I opened were court-**FAILED** and **none** said so on arrival. The strongest honesty
   signal Atlas computes is the one least visible where it matters.
2. **`resolveTierChip` is not wired into the L2 console at all** — two importers, both outside it.
   This is a one-line diagnosis for the standing zero-⚑ finding, and it means the state-media P0 is
   *shipped but unreachable* from the analyst surface.
3. **Silent degradation of `/voice-mix`.** The payload says `degraded: true · reason: db_busy ·
   detail: "voice-mix aggregation timed out under database load"`; the UI renders **nothing** — no
   heading, no reason. The analyst cannot tell "Atlas has no ownership measurement for Iran" from
   "the query timed out". The honest string exists elsewhere in the same component.
4. **The search dropdown renders the previous query's results under the new query text** for ~4 s
   (`PSD Bolojan` displayed the eight `funding` receipts before settling to `No results`).
5. **Thread shredding, and a same-thread 10× count divergence.** ≥18 distinct US-Iran threads across
   three doors with zero cross-reference; *Jordan Intercepts Iranian Missiles* = 170 signals in
   search, 17 in the country brief.
6. **Wire syndication is never marked in the raw lane.** 7 of 12 GQ-09 receipts are one NPR copy
   across seven US public-radio stations; 5 of 12 GQ-06 receipts are one wire; GQ-10 showed three
   verbatim duplicate pairs in eight rows, one of them with the units silently dropped
   (*"EUR 2.15 bln"* → *"EUR 2.15"*). D3 is not applied anywhere the analyst can see.
7. **`/research/plan` takes ~45 s and both retrieval lanes time out**, then reports it impeccably.
   Worth naming as a defect *and* as the template every other surface should copy.

**What batch 2 adds to the batch-1 thesis.** Batch 1 concluded that the surface holding the answer is
destroyed by the click that leaves it. Batch 2 sharpens the *second* half: **Atlas increasingly
measures the right thing and then does not render it.** The label court caught GQ-08's blob and the
panel hid the verdict. The ownership metric is correct on Nicaragua, Indonesia and Romania and is
dropped in silence on Iran. The state-media classifier exists, is correct about RT, and is not
imported by the console. The research plan distinguishes a failed lookup from a measured absence in
so many words — on the one query where both its lanes timed out. Across ten queries the answered rate
is 10% and the informed rate is 80%; the gap is not a retrieval gap.

*Batches 3–4 append below this line.*

═══════════════════════════════ BATCH 3 — GQ-11…GQ-15 ═══════════════════════════════

**Run conditions.** Same repo/branch, `http://localhost:3000/app`, viewport 1512×950, prod data,
sequential. Corpus at batch-3 start: **164 countries · 138,421 signals**, window `FROM 21 JUL 2026`,
24 h (drifted to 163 countries · 136,326 by GQ-15). **Screenshots composited this batch**, so pixel
claims are backed by both the image and DOM geometry (`getBoundingClientRect`), not innerText alone —
which is what produced this batch's biggest finding. **GQ-15 is the run's first control.**

**Standing N1 note re-verified, not re-discovered.** `input.value === ""` confirmed after every
arrival (GQ-11 → Pakistan brief, GQ-12 → thread detail, GQ-13 → Sudan brief, GQ-14 → DR Congo brief,
GQ-15 → research plan), dropdown gone each time, no related-results affordance on any arrival
surface. **5/5 CONFIRMED.** (Whole-page regex for a related affordance returns a *false positive* on
the string *"related by country, not by story"* in CONFLICT EVENTS — that is a provenance caveat, not
a navigation control. Recorded so the check is not mis-scored later.)

---

## ⚠ BATCH-3 HEADLINE FINDING #1 — the search dropdown renders thread labels at **0 px**

Measured on the very first query and reproduced on **4 of 5**. In the `LIVE THREADS` section every
`.search-item-name` has **`width: 0`** with `overflow: hidden` and `scrollWidth` 148–197 px. The
screenshot corroborates exactly: the dropdown shows `THREAD` + *"75 signals · Corruption
investigation · partial match"* and **no thread name at all**.

Root cause, read off computed style — `.search-item` is `flex-direction: row; flex-wrap: nowrap`,
width 266 px, with three children:

| child | flex | flex-shrink | rendered width |
|---|---|---|---|
| `.search-item-tag` (`THREAD`) | `0 0 auto` | **0** | 51 |
| `.search-item-name` (**the label**) | `1 1 0%` | **1** | **0** |
| `.search-item-meta` (`N signals · category · partial match`) | `0 0 auto` | **0** | 230 |

51 + 230 = 281 > 266, and **the label is the only shrinkable child**, so it absorbs the entire
deficit. The decoration is unshrinkable; the identity is the only thing that can vanish. Because meta
width scales with category-name length, **longer category names delete the thread label outright**
(`Elections and Political Campaigns` measures 275 px on its own). `MEDIA SIGNALS` rows are unaffected
(name renders at 220 px, ellipsised).

**This partially CONTRADICTS how batches 1–2 could report dropdown thread labels at all.** Batch 2
states explicitly that screenshots were unavailable and every quotation was taken via
`get_page_text` / `innerText` — which returns text regardless of rendered width. On the D5-pixels
rule the rubric actually applies, **the search dropdown's thread labels in this run were not on
screen.** The analyst chooses between rows identified only by a signal count and a category.

## ⚠ BATCH-3 HEADLINE FINDING #2 — a **failed** retrieval lane is rendered as **"No results"**

Read from `backend/app/routers/search.py`: `degraded_segments.append("signal_matches")` (line 680)
and `…append("live_threads")` (line 609) each fire **only inside an `except Exception` handler**
around a `conn.fetch(…, timeout=SEARCH_MATCH_TIMEOUT_SECONDS)` where
`SEARCH_MATCH_TIMEOUT_SECONDS = 5.0`. `degraded: true` therefore means **the query failed or timed
out** — it is emphatically *not* "the query ran and found nothing."

Every `/api/v2/search/unified` call in batch 3 came back degraded, and the UI never said so once:

| typed | `degraded_segments` | what the pixels said |
|---|---|---|
| `Azad Kashmir elections first phase rigging allegations` | `signal_matches` | **`No results for "…"`** |
| `Azad Kashmir` | `live_threads`, `signal_matches` | **the previous query's 12 Iran receipts, under `COUNTRIES · IR · Iran`** |
| `Kashmir election rigging` | `signal_matches` | **`No results for "…"`** |
| `Pakistan` | `live_threads`, `public_attention`, `signal_matches` | empty dropdown, **no notice at all** |
| `Ukraine struck Iranian ship Caspian Sea response` | `signal_matches` | no MEDIA SIGNALS section, no notice |
| `Threatens Ukraine Over Ship Attack` (a thread's own label) | `live_threads`, `signal_matches` | empty dropdown, no notice |
| `war what happened this week` (Sudan) | `signal_matches` | empty dropdown, no notice |
| `Australian bushfire emergency …` (**control**) | `signal_matches` | empty dropdown, no notice |

Two distinct failures ride on this. **(a) A failed lookup is relabelled a measured absence** —
literally the distinction `/research/plan` renders correctly in words (*"This is a failed lookup, not
a measured absence"*) on the same screen-set. **(b) When the degraded payload is empty, the dropdown
keeps the previous query's results**: typing `Azad Kashmir` left `COUNTRIES · IR · Iran` and twelve
Iran receipts on screen **permanently** (re-read at 3 s and again at 8 s — unchanged). This is
batch-2 new-defect 4 (*"stale results for ~4 s before settling"*) **CONFIRMED and severely
EXTENDED**: it does not settle, because there is no non-degraded payload to settle to.

---

## GQ-11 — Azad Kashmir first-phase elections: the rigging allegations

**Typed (U1):** `Azad Kashmir elections first phase rigging allegations` · **auto-scope: NONE**
(second query in fifteen with no `Filtering to:` line, after GQ-09).

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS ×4 — 0/4 on topic**, every one a substring match on `rigging` / `first` / `elections`,
and **all four labels rendered at 0 px** (names below are read from the DOM, not the screen):

| # | label (DOM) | rendered width | signals · category | court dot |
|---|---|---|---|---|
| 1 | HP India Fined for Bid **Rigging** | **0 px** | 75 · Corruption investigation | ⬤ *partially matches* |
| 2 | Greece Receives SAFE **First** Tranche | **0 px** | 44 · Currency and debt stress | — |
| 3 | Carney Calls By**elections** | **0 px** | 37 · Elections and Political Campaigns | ⬤ *partially matches* |
| 4 | Tango Aircraft **First** Flight | **0 px** | 24 · Science & Technology | ⬤ **did not match** |

**MEDIA SIGNALS: `No results for "Azad Kashmir elections first phase rigging allegations"`** — which
the payload shows was a **timed-out lane**, not an absence (headline finding #2).

Reformulations: `Kashmir election rigging` → 4 threads (HP India Bid Rigging 75, Trump Accuses China
Election Interference 43 **court-failed**, Carney Calls Byelections 37, Arizona Primary Election
Preview 36 **court-failed**), **0/4 on topic**, labels again 0 px, MEDIA SIGNALS again `No results`
over a degraded lane. `Azad Kashmir` → **the Iran ghost-receipt case above**. `Pakistan` → three
lanes degraded, dropdown offers only `Go to Pakistan`.

### CONTENT INVENTORY — surface B: Pakistan country brief (U4) — the surface that carries the story

- `568 signals` · **`Narrative Threads 0`** · `0 THREADS` · Source Mix 10 · Atlas Topics 12 ·
  `-1.8 SENTIMENT` · `Volume 1.2x normal (z: 0.5)` · Source Diversity 92 / Source Quality 70
- Standfirst: *"Pakistan shows 568 signals in this 24h window, led by Minister, Public Sector, and
  Policy: Policy Government… Most-covered figures: **azad jammu** and **muslim league-nawaz**."*
- `CONFLICT EVENTS` — *"2 events in Pakistan this window · machine-coded, geo approximate"* ✓ caveat
  renders; one is **`Military force · Kashmir, North-West Frontier, Pakistan`**
- **`RECENT SIGNALS` (6 rows, the only on-topic material anywhere):**
  - **independent.co.uk**, *just now* — ***"At least 14 killed as start of crucial election in
    Pakistan-administered Kashmir marred by violence"*** — chip **`PUBLIC HEALTH`**
  - **laosnews.net**, *just now* — ***""Attempt to camouflage Pakistan's illegal occupation, hide
    grave human rights violations": MEA slams "cosmetic" elections in PoJK"*** — chip **`PUBLIC
    HEALTH`** — the **Indian** framing
  - bbc.com, 5 h — *"Maryam Nawaz's 'gift of buses' to Kashmiri people and debate on province's
    resources…"* (adjacent Kashmir politics, auto-translated, `See original`)
  - off-topic 3/6: prothomalo.com (Kuwait–Pakistan defence), en.dailypakistan.com.pk ×2 (Lahore
    police, a celebrity rift)
- `TOP PUBLISHERS`: tribune.com.pk 42 · express.pk 39 · dawn.com 36 · propakistani.pk 28 ·
  **radio.gov.pk 24** — the Pakistani press is densely indexed, **and `radio.gov.pk`, the state
  broadcaster on a `.gov.pk` domain, renders with no ownership marker**
- **`VOICE MIX` IS ABSENT** (`innerText.indexOf('VOICE MIX') === -1`), with no notice. Payload:
  `GET /api/v2/voice-mix?hours=168&country=PK` → `{"degraded":true,"reason":"db_busy","detail":
  "voice-mix aggregation timed out under database load — retry shortly"}` — **byte-identical to the
  Iran payload batch 2 found.** Fired 3× (1 aborted, 2 × 200).
- `KEY SUBJECTS` entity noise: **`PERSON azad jammu 22`** (a place, and the top-ranked subject),
  **`PERSON muslim league-nawaz 17`** (a party), **`PERSON allahu akbar 9`** (a phrase), alongside
  real people (shehbaz sharif 14, randhir jaiswal 13, imran khan 9, ishaq dar 8)

**Verdict on the question:** the *first phase* is answered — it began, it was marred by violence, at
least 14 dead — and one **delegitimisation** framing is present (India's MEA calling the polls
"cosmetic"). **The Pakistani "rigging allegations mar polls" framing is absent, and there are zero
Pakistani-origin outlets among the on-topic receipts** (independent.co.uk GB, bbc.com GB,
laosnews.net — a content-farm mirror of the same family as GQ-03's nigeriasun/kenyastar cluster,
carrying Indian agency copy). The criteria's *"≥3 distinct Pakistani- or Indian-origin outlets"*
fails.

### N1 — NAV-LOSS ✱
**Promised** across four phrasings: 8 threads (none on topic) + one `No results` + twelve Iran ghost
receipts. **Delivered on arrival:** search input `""`, dropdown gone. The two receipts that answer the
question exist **only** in the country brief and are reachable from no search phrasing.

### NEW DEFECT — the right rail asserts a scope it has not applied
With `COUNTRY Pakistan` focused, the Narrative Threads panel rendered the strip **`Scoped to Pakistan
✕`** above five threads whose own country chips are `IR`, `IR/US`, `RU/BR/CA/US`, `FR/ES` — *Iran
Negotiations…* (211), *Iran Attack on US Bases* (600), *Trump tariff policies* (50), *Spain Wildfires*
(73), *Trump escalates Iran tensions* (165). **Zero Pakistan.** Meanwhile the country brief on the
same screen reads `Narrative Threads 0`. This is not batch-1 defect 5 (count divergence between two
doors) — it is a **false scope label over unscoped global content, contradicting the panel beside
it**. (On GQ-12 the same strip *did* eventually scope correctly to Iran, so the strip lags rather
than never works — but it never says it is lagging.)

### Score **1a** · API 0 · **UI-BETTER** · not piloted
Honest floor. No thread at any door and the absence is stated on screen (`Narrative Threads 0` /
`0 THREADS`), so no bucket is passed off as an answer. Not 1b: only two on-topic receipts render,
they answer the *first phase* rather than the *rigging allegations*, and the domestic-outlet
requirement fails outright. Not 0: the arrival surface is honest, its caveats render, and no false
claim is made about Kashmir.
*Boundary recorded for the record: the search surface on this query does hit level-0 language twice
— a degraded lane titled `No results`, and another country's twelve receipts left standing under the
typed query. Following batch 1's precedent of scoring the arrival surface (GQ-03 scored 0 because the
**arrival** was the silent-degraded one), the query holds at 1a and both search behaviours are
carried in the defect list instead.*

---

## GQ-12 — Ukraine struck an Iranian ship in the Caspian: how is Iran responding?

**Typed (U1):** `Ukraine struck Iranian ship Caspian Sea Iran response`
**Auto-scope rendered:** `Filtering to: Iran · results scoped to this country`.

### The auto-scope MUTILATES the query — batch-1/2 defect 2, extended
The request actually sent was `q=Ukraine struck Iranian ship Caspian Sea **response**&country=IR` —
**the token `Iran` is stripped from the query string** and converted into a country filter. Same on
GQ-13 (`war in Sudan what happened this week` → `q=war what happened this week&country=SD`) and on
the attempt to search a thread by its own label (`Iran Threatens Ukraine Over Ship Attack` →
`q=Threatens Ukraine Over Ship Attack&country=IR`). The analyst's words are silently rewritten.

### CONTENT INVENTORY — surface A: search dropdown

**LIVE THREADS ×6 — bucket-reuse, precisely as the criteria predicted, and the wrong sea:**

| # | tag | label | signals | `label_status` |
|---|---|---|---|---|
| 1 | `EVENT` | Russia Threatens Civil Shipping in **Black Sea** | **4,007** | **failed** ⬤ |
| 2 | `EVENT` | Iran Negotiations, Ukraine Civilian Casualties, **Danube** Shipwreck | **3,693** | null |
| 3 | `THREAD` | Ukraine EU Membership Blocked | 151 | **failed** ⬤ |
| 4 | `THREAD` | Indian Seafarers Killed in **Odesa** | 126 | entailed |
| 5 | `THREAD` | Escalation in **Black Sea** | 83 | partial ⬤ |
| 6 | `EVENT` | Ukrainian Army Leadership Change | 74 | **failed** ⬤ |

All six labels rendered at 0 px. **Caspian appears nowhere.** Three of six are court-FAILED and the
verdict reaches the analyst as a 7 × 7 px dot carrying `data-tip` (not `title`) — batch-2 new-defect 1
CONFIRMED, with the attribute name corrected. MEDIA SIGNALS absent (degraded).

Reformulating to `Caspian ship attack` produced a working raw lane and **0/12 on topic** — *pepper-
spraying drones that ram attackers*, *Kalshi attacks Wisconsin law*, *Azerbaijan court convicts 9
journalists* (**listed twice**, yoursourceone.com and wsls.com), *three-year-old hospitalised after
dog attack*, *headbutt attack*, *Berlin Pride*, *cyberattack to prevent cyberattacks*, *US diplomats
storm out of UN*. **Not one receipt contains the word "Caspian."** The most distinctive token in the
query was dropped and the match ran on `attack` — batch-1 defect 9 CONFIRMED in its sharpest form.

### UI-MISS: the answer thread is Atlas's own **lead** for Iran, and search never offers it
The Iran country brief's standfirst reads: ***""Iran Threatens Ukraine Over Ship Attack" leads Iran's
coverage — 74 signals, within 3,140 total this 24h window."*** It is first in the brief's
`NARRATIVE THREADS` list. Search never returned it under three phrasings **including its exact
label** — that attempt came back with `live_threads` degraded and an empty dropdown, so the analyst
cannot tell "no such thread" from "the lookup failed."

### CONTENT INVENTORY — surface B: thread detail *Iran Threatens Ukraine Over Ship Attack*

Reached via `Go to Iran` → right rail (the country-brief chip click did not open it; the rail did).
The Iran brief itself sat on `LOADING BRIEF…` for **~25 s**.

Header: *"Iran Threatens Ukraine Over Ship Attack `NEW` · ← Global · 🇮🇷 Iran · **32 signals**"*,
`HOT WINDOW`, `1 COUNTRIES · 19 SOURCES`, tone **−4.60**.

**The rendered summary answers the question, and carries its own independence caveat:**
> *"Iran's foreign minister warned that Ukraine's attack on an Iranian vessel in the **Caspian Sea**
> will not go unanswered."*
> *"Iranian officials escalated rhetoric, threatening retaliation for a Ukrainian ship attack, as
> coverage surged across **Turkish and Slovenian media**."*
> *"Multiple sources (rtvslo.si, memleket.com.tr, haberler.com, etc.) quote Iran's Foreign Minister
> Arakchi stating the attack 'cannot remain without response.'"*
> **"No independent confirmation of the attack or its details; all reports rely on Iranian official
> statements."**

That last sentence is the corroboration statement GQ-07 was scored down for lacking — it exists, on
this thread, in prose.

**All 19 receipts rendered. ROR@19 = 18/19 = 0.947.** Each carries outlet + timestamp + tone + `IR`
tag; non-English rows carry `See original`. The single outlier is #19 (odatv.com, Jul 23, *"Irak'tan
İran'a destek mesajı"* — Iraq's message of support, 3 days earlier).

| receipt (as rendered) | outlet | stamp |
|---|---|---|
| Aragchi: Ukrainian attack on Iranian vessel 'cannot remain without response' | rtvslo.si | Jul 27 06:30 |
| Iran's stern warning to Ukraine: **Caspian Sea** attack will not go unanswered | memleket.com.tr | Jul 27 03:30 |
| Iranian Foreign Minister **Araghchi**: Ukraine's attack on our ship will not go unanswered | haberler.com | Jul 27 01:30 |
| Harsh message from Tehran to Kyiv: The attack will not go unanswered! | haber7.com | Jul 27 01:30 |
| Iran: Ukraine may soon understand that Iran does not leave any action unanswered | trthaber.com | Jul 26 20:15 |
| Threat from Iran to Ukraine: The attack will not go **unpunished** | turkiyegazetesi.com.tr | Jul 26 13:45 |
| Iran's Foreign Minister says Ukraine's ship attack 'will not go unanswered' | **aa.com.tr · `STATE` ⚑ state** | Jul 26 11:50 |
| Iran's harsh response to the attack in the **Caspian Sea**: 'It will not go unanswered' | bursadabugun.com | Jul 26 11:30 |
| **Iran Parliament Vice Speaker: Ukraine's foolish act will not go unanswered** | anlatilaninotesi.com.tr | Jul 26 10:30 |

(plus ntv.com.tr, yenimesaj.com.tr, haberaktuel.com, dnevnik.hr, dha.com.tr, cnnturk.com, mynet.com,
cumhuriyet.com.tr, netinternethaber.com)

**Two Iranian voices are separated and attributed** — the Foreign Minister and the Parliament Vice
Speaker — which is the "how is Iran responding" half.

**Honest limits, recorded:** 17 of 19 outlets are Turkish, 1 Slovenian, 1 Croatian. **Zero Iranian
and zero Ukrainian outlets** — Iran's response reaches the analyst entirely through Turkish relay.
The prose names that ("Turkish and Slovenian media"); the Voice Mix does not — it reads *"unknown 5 ·
**0%** of attributable voices are Iran's own press · `THIN` · 0 of 2 attributable voices are
domestic. **Loudest outsider: Croatia (1)**"* — an n = 2 denominator under a 19-source panel, naming
Croatia as loudest outsider when 17/19 are Turkish. Batch-2 defect 12 CONFIRMED.

### ⚠ CONTRADICTION of the standing zero-⚑ finding — `⚑ state` **does** render in the L2 console
`aa.com.tr` renders `STATE` + **`⚑ state`** in `TOP SOURCES`, class `source-tier-badge
source-tier-state`. This is the **first state-media chip in fifteen queries**, and it means batch-2's
new-defect 2 needs splitting into a three-way diagnosis, verified in source:

| surface | mechanism | state marking |
|---|---|---|
| `Briefing.tsx`, `BriefNewspaper.tsx`, `WorkbenchPanel.tsx` | `resolveTierChip` (frontend domain list, `sourceTiers.ts`) | ✓ |
| **`ThemeDetail.tsx` (L2 thread detail)** | **backend `credibility.label`** → `source-tier-badge source-tier-${…}` (lines 1326 / 1557 / 1608) | **✓ — renders `⚑ state` for aa.com.tr** |
| **`CountryBrief.tsx` TOP PUBLISHERS** | **none** — line 899 is a bare `<span className="source-name">{source.name}</span>`, no tier/state/credibility reference anywhere in the file | **✗** |

So batch 2 is right that `resolveTierChip` never reaches L2 (importers confirmed: Briefing,
WorkbenchPanel, BriefNewspaper, plus its own lib/test), but **wrong that L2 therefore cannot mark
state media** — the thread detail has an independent, working, backend-driven path. **The real hole
is `CountryBrief.tsx`**, which is exactly where GQ-06 scored 0 for `irna.ir` (495 signals) and
`arabic.rt.com` unmarked, and where `radio.gov.pk` (GQ-11) and `irna.ir` + `arabic.rt.com` (GQ-13)
went unmarked again today. **The fix is one component, not the whole console.**

### NEW DEFECT — the same thread reads **74** and **32** simultaneously on one screen
The right rail renders *Iran Threatens Ukraine Over Ship Attack · **74** 24h* while the detail panel
beside it reads *"← Global · Iran · **32** signals"* and `32 24h · raw SIGNALS`. Batch-2 defect 5
(*170 vs 17, one click apart*) CONFIRMED and sharpened: **no click is required — both numbers are
visible at once.**

### N1 — NAV-LOSS ✱
**Promised:** 6 threads (all mega-buckets) + the `Caspian ship attack` set. **Delivered:** 0. Detail
sections are only four — thread header · `TOP SOURCES` · `VOICE MIX` · `DEEP HISTORY` — with **no
sibling / related / "stories inside" section** (`related` string test false). Concretely lost: the
five other Hormuz/Black-Sea threads and, more importantly, **the Ukrainian side of the event**, which
appears in no reachable surface.

### Score **2** · API 0 · **UI-BETTER** · not piloted
The criteria's PASS condition — *"a thread that HOLDS THE CONNECTION between the two theatres"* — is
met outright: the label names both parties, the summary names the Caspian Sea, and the receipts are
that event and nothing else. ROR@19 = 0.947 ≥ 0.75 ✓; ≥3 distinct outlets ✓ (19); key claims
attributed to named officials ✓; **no unflagged cross-story blending** (18/19 one story, and the
one outlier is visibly dated three days earlier) ✓. **G7 does not fire** — window count 32 (rail 74),
both ≫ the <10 trigger, so this is not answering with history.
Held at 2, not 3: no related-threads affordance exists in the detail (NAV-LOSS), the Ukrainian
counterpart strand is unreachable, and the source concentration is named only in prose while the
Voice Mix panel misreports it (*Croatia (1)* over 17 Turkish outlets, n = 2).
**This is the run's second level-2 and its first since GQ-01 — and it is a better 2 than GQ-01's**,
because the independence caveat renders in words and the receipt set is genuinely one story.

---

## GQ-13 — the war in Sudan: what happened this week

**Typed (U1):** `war in Sudan what happened this week` → sent as `q=war what happened this
week&country=SD`. **Auto-scope rendered:** `Filtering to: Sudan · results scoped to this country`.

### CONTENT INVENTORY — surface A: search dropdown = **the G5 failure mode, exactly**
**Zero LIVE THREADS. Zero MEDIA SIGNALS. No `No results` line. No notice.** The dropdown offers only
`Go to Sudan`, `Open the story`, `Start investigation`. Payload: `live_threads: []` (genuinely empty
— not in `degraded_segments`), `signal_matches: []` **with `degraded_segments: ["signal_matches"]`**.
The criteria names this precisely as a FAIL condition: *"a silent empty (G5) indistinguishable from a
timeout."* On this surface, that is what it is.

*(Payload curiosity worth logging: `countries: [{"code":"SD","name":"SD"}]` — the country **name** is
unresolved to the code. The frontend prints "Sudan" from its own alias table.)*

### ⚠ NEW DEFECT (level-0 class) — an Iran thread rendered under a **Sudan flag**
Arriving at Sudan while a thread focus was still live produced a compound focus (`COUNTRY Sudan ×` +
`THEME Iran Threatens Ukraine Over Ship Attack ×`, **both chips visible and clearable**, which is an
improvement on GQ-03/GQ-06's invisible scope) — but the panel rendered:

> **Iran Threatens Ukraine Over Ship Attack** `NEW`
> ← Global · 🇸🇩 **Sudan · 32 signals**
> `HOT WINDOW` · ⚑ **2 conflict events in Sudan this window** · *related by country, not by story*
> "This dynamic narrative thread is active in the selected window with **32 signals**."
> "Coverage tone is mixed (0.00), and the current evidence sample spans **0 recent items**."
> `32 24h · raw SIGNALS` · `0.00 AVG SENTIMENT` · **`0 COUNTRIES`** · **`0 SOURCES`**

An Iranian thread, carrying a **Sudanese flag**, a **Sudan** signal attribution and a **Sudan**
conflict-event count, while simultaneously reporting `0 COUNTRIES · 0 SOURCES · 0 recent items` under
a header still asserting 32 signals. This is batch-1's GQ-03 pattern **plus an active geographic
misattribution**. (Clearing the theme chip is also mis-wired: clicking the `×` on the THEME chip
removed the **COUNTRY** chip instead.)

### CONTENT INVENTORY — surface B: Sudan country brief (U4) — an exemplary honest floor
- `65 signals` · **`Narrative Threads 0`** · `0 THREADS` · **`Source Mix 10 · 95% foreign`** ·
  `-1.7 SENTIMENT`
- Standfirst: *"Sudan shows 65 signals in this 24h window, led by Armed Conflict, Water, and
  Paramilitaries. **Public-attention proxies are quiet or unavailable for this country in the current
  window.**"*
- `SEARCH` — **"No Google Trends data for this window."** ✓ · `WIKI` — *"No Wikipedia pageview data
  for this proxy."* ✓ · `FORUM UNVERIFIED` ✓ labelled
- `TRUST INDICATORS`: Source Diversity 99 · **Source Quality 40** · **Volume 0.9x normal (z: −0.6)**
- **`VOICE MIX` RENDERS**: ***"5% covered by its own press · 12 of 248 attributable voices are
  domestic. Loudest outsider: ZA (35). 12% is foreign media in the local language (soft power, not
  self-coverage)."*** — ownership-based, with the soft-power bucket held separate ✓
- `TOP PUBLISHERS`: aljazeera.net 4 · almasryalyoum.com 3 · **dabangasudan.org 3** · aa.com.tr 2 ·
  haberler.com 2 — small counts, honestly small
- **`RECENT SIGNALS` — 6/6 on topic, and between them they answer "this week":**
  - **france24.com**, 9 h — ***"Sudanese army advances and Rapid Support Forces lose control of a
    main road linking Omdurman and El Obeid"***
  - **aa.com.tr**, 10 h — ***"Sudan army's advance to the west changes military balances in civil
    war"***
  - **arabic.rt.com**, 9 h — *"Sudan.. **Dagalo** calls on his forces to change their military plan"*
  - **irna.ir**, 2 h — *"**Displacement of 20,000 people in Darfur**, Sudan due to violence and
    insecurity"*
  - skynewsarabia.com, 11 h — *"Gold.. the lifeline of the Sudanese army's war"*
  - aa.com.tr, 6 h — *"Food support from Turkish Red Crescent to those in need in Sudan"*
- `FORUM UNVERIFIED` adds *"Drone Strikes Are Destroying the Infrastructure of Survival in the Heart
  of Sudan"*, *"Sudan: Army regains control of crucial highway (military sources) | Africanews"*,
  *"In El Obeid, Sudanese women face drones by day, rape by night, to reach water"* (+ one off-topic
  Burkina Faso row)
- `KEY SUBJECTS`: omar al-bashir 3, **mohamed hamdan dagalo 2**, **abdel fattah al-burhan 2**,
  badr abdelatty 1 — the correct principals
- **Ownership gap, unmarked: 2 of the 6 receipts are `irna.ir` (Iranian state) and `arabic.rt.com`
  (Russian state)**, rendered as plain outlet names — the `CountryBrief.tsx:899` hole from GQ-12's
  correction, on a war story.

### N1 — NAV-LOSS ✱
**Promised:** nothing (the dropdown was empty). **Delivered:** the brief. This is the one query in the
batch where nothing was destroyed because nothing was offered — the loss is that the analyst has no
way to know the search lane failed rather than found nothing.

### Score **1b** · API 1 · **SAME (refined 1 → 1b)** · not piloted
Level 2 for this item requires *"a thin thread that CARRIES its thinness"* — there is **no thread at
all** (`Narrative Threads 0`), so ≥2 is unreachable by construction. The FAIL clauses do **not** fire
at the arrival surface: nothing confident is assembled, and the brief is emphatically not a silent
empty — it carries `95% foreign`, `5% covered by its own press`, `Volume 0.9x normal (z: −0.6)`,
`Source Quality 40`, *"Public-attention proxies are quiet or unavailable"* and *"No Google Trends data
for this window."* The receipts substantively answer *what happened this week* — **the army advanced
west, the RSF lost the Omdurman–El Obeid highway, Dagalo ordered a change of plan, 20,000 displaced
in Darfur, gold financing the war** — each attributed. That is 1b.
**The G5 clause is not clean, though, and it is recorded rather than waved through: the search door
*was* a silent empty over a degraded lane.** It does not carry the score because the analyst's
arrival surface is the brief, and the brief is the most honest thin-country render in the run.

---

## GQ-14 — Congo Ebola coverage in French and Swahili versus English

**Typed (U1):** `Congo Ebola coverage French Swahili versus English`
**Auto-scope rendered:** `Filtering to: DR Congo · results scoped to this country`.

### CONTENT INVENTORY — surface A: search dropdown
**LIVE THREADS ×2**, both labels at 0 px: **Ebola Outbreak Congo** 254 · Disease outbreak
(⬤ *only partially matches*) · **Mundial 2026 Coverage** 117 · Sports (⬤ **did not match**) — the
football thread matched on the word *coverage*.

**MEDIA SIGNALS ×10 — and this is the finding: 10/10 are in ENGLISH, 9 of 10 from one Chinese state
outlet, 4 of them exact verbatim duplicates:**

| headline | outlet | chip | note |
|---|---|---|---|
| DR Congo's confirmed Ebola cases top **3,200** as outbreak remains in sustained transmission-Xinhua | english.news.cn | `Democracy` | **listed twice** |
| DR Congo reports nearly **3,000** Ebola cases as PM calls for faster response-Xinhua | english.news.cn | `Authorities` | **listed twice** |
| Insecurity continues to impact Ebola outbreak response in DR Congo: UN-Xinhua | english.news.cn | `Disease Outbreak` | **listed twice** |
| DR Congo certifies first-ever lithium export-Xinhua | english.news.cn | `Energy & Mining` | **listed twice**, off-topic |
| 32 civilians killed in eastern DR Congo attacks -Xinhua | english.news.cn | `Authorities` | off-topic |
| Rise in Ebola cases in Congo – Shafaqna English | shafaqna.com | `Communicable Disease` | |

A query that explicitly asks about **French and Swahili** returns **zero French and zero Swahili
receipts**, and `english.news.cn` (Xinhua) carries **no state-media marker** on any of its nine rows.

### CONTENT INVENTORY — surface B: *Ebola Outbreak Congo* detail — **batch 1's GQ-03 reproduced verbatim**
> Ebola Outbreak Congo `NEW` — **Global · 254 signals** · Last 24h · active since Jun 24 · `HOT WINDOW`
> "This dynamic narrative thread is active in the selected window with 254 signals."
> "Coverage tone is mixed (0.00), and the current evidence sample spans **0 recent items**."
> `254 24h · raw SIGNALS` · `0.00 AVG SENTIMENT` · **`0 COUNTRIES`** · **`0 SOURCES`**
> `VOICE MIX · WHO SPEAKS?` — unknown 14 — **"0% of attributable voices are France's own press"** ·
> `THIN` · "0 of 9 attributable voices are domestic. **Loudest outsider: Greece (9).**"

**Byte-for-byte the same panel batch 1 recorded on 2026-07-30** — same topic id, same `unknown 14`,
same `Greece (9)`, same stale claim about **France's** press on a **DR Congo** thread. Network
confirms the mechanism unchanged: `GET /api/v2/theme/dynamic-topic-239?hours=24&country_code=CD`
fired **twice**, plus `lineage` ×2 and `drift` ×2. **This is not a transient — it is a stable,
reproducible mis-anchored render.** Batch-1 defects 2, 11 and 12 CONFIRMED together.

### CONTENT INVENTORY — surface C: DR Congo country brief (U5, the designated asymmetry surface)
- `75 signals` · **`Source Mix 15 · 33% foreign`** · **`Narrative Threads 0`** · `0 THREADS`
- **`VOICE MIX`: "67% covered by its own press · 209 of 310 attributable voices are domestic.
  Loudest outsider: CN (16)."** ✓ ownership-based, and stable against batch 1's 68% / 210 / 311
- `TOP PUBLISHERS`: **actualite.cd 29 · mediacongo 6 · radiookapi.net 5** · umn.edu 2 ·
  mediacongo.net 2 — the Francophone Congolese press dominates the index
- `RECENT SIGNALS` — 5 of 6 from actualite.cd (French, auto-translated with `See original`), two of
  them Ebola: ***"Haut-Uele: Isiro university clinics equipped with an Ebola diagnostic
  laboratory"*** and *"Ebola: Infected in DRC, a second American patient cured of the virus in
  Germany"*; `FORUM UNVERIFIED` carries the French original *"Ebola : Infecté en RDC, un second malade
  américain guéri du virus en Allemagne … #fr #france"*
- `KEY SUBJECTS` entity noise unchanged from batch 1: **`PERSON wikimedia commons`**, **`PERSON july a
  kindu`**, **`PERSON whatsapp linkedin`**

### The decisive measurement — whole-DOM string test on the arrival surface
| test | result |
|---|---|
| `/swahili/i` anywhere on the page | **false** |
| `/french/i` anywhere on the page | **false** |
| any language ratio (`FR n` / `EN n` / `fr:en`) | **false** |
| `/uncovered\|silent\|no coverage in\|not covered in\|blind to/i` | **false** |

**Atlas never names a language, never reports a distribution, and never mentions Swahili** — but it
also **never makes the forbidden claim**. The criteria's auto-FAIL (*"ANY claim that the story is
'uncovered' or 'silent' in French or Swahili"*) does **not** fire. What Atlas renders instead is an
Ebola/DRC summary — i.e. an answer to GQ-03, which the criteria anticipates verbatim: *"Answering
with a good Ebola thread and ignoring the comparative question scores 1 at best."*

The origin half is partially inferable — `33% foreign`, `67% own press`, `Loudest outsider: CN (16)`,
Francophone publishers dominating, against a search lane that returned 10/10 English Xinhua — but
inference by the analyst is not a rendered answer, and the fr:en ratio and the Swahili tail (the two
things the criteria names) are absent.

### N1 — NAV-LOSS ✱
**Promised:** 2 threads + 10 receipts. **Delivered:** a thread panel with `0 SOURCES` and a country
brief whose recent signals are a road accident, a Guinean ministerial appointment, ADF abductions and
a referendum bill. Search input `""`.

### Score **1a** · API 0 · pilot 0 · **UI-BETTER vs both**
Honest floor. Absence stated (`Narrative Threads 0`), the ownership metric renders correctly and
matches batch 1, the proxy caveats render, and **the forbidden over-claim is not made**. Not 1b: the
rendered receipts answer a different question than the one asked; the comparative measurement the
query is *about* exists nowhere in pixels. Not 0 at query level — though the *thread* surface on its
own reproduces batch-1 GQ-03's level-0 render exactly, which is carried in the defect list rather
than double-counted here, because U5 (the voice-mix surface designated for this question) works.

---

## GQ-15 — **NEGATIVE CONTROL** — Australian bushfire emergency: which states are evacuating?

**Typed (U1):** `Australian bushfire emergency which states are evacuating`, then
`Australian bushfire emergency evacuations`. **Auto-scope:** `Filtering to: Australia`.

### Surface A: search dropdown
**Zero LIVE THREADS · zero MEDIA SIGNALS**, both phrasings. Payload: `live_threads: []` **genuinely
empty** (not in `degraded_segments` — a real measured absence for the thread lane), `signal_matches:
[]` degraded. No answer-claim of any kind. No notice of the degradation either.

### Surface B: **"Open the story"** — the flagship NL / sanctioned-LLM surface
`POST /api/v2/research/plan`, ~30 s on `BUILDING RESEARCH PLAN…`, then:

> `STORY · Australian bushfire emergency`
> `GAP` — **Thread lane unavailable (TimeoutError); coverage unknown.** · `THREAD` · 0.12
> `GAP` — **Semantic signal headline unavailable (ann_timeout). This is a failed lookup, not a
> measured absence.** · `SEMANTIC` · 0.12
> `▸ ARCHIVE ACTIVITY · TIME TRAVEL`
> `▸ LOW-CONFIDENCE CANDIDATES — ALL ACCESSIBLE (54)`
> `56 CANDIDATES EVALUATED · 2 PRIMARY · 54 LOW CONFIDENCE · 56 ACCESSIBLE · PARTIAL LEDGER · LANE
> DEGRADATION DISCLOSED`

**No Australian state is named. No evacuation figure. No synthesis prose. No fire is asserted to
exist.** The two "PRIMARY" entries are the two GAP rows themselves.

### The paired-scoring payoff — the Bordeaux failure **is present and is correctly quarantined**
Expanding the 54 low-confidence candidates shows the semantic lane doing exactly what the query set
warned about — and being contained:

`WEAK Wildfire or severe-storm disaster SEMANTIC 0.80` · `WEAK High Temperature Warning 0.84` ·
`WEAK Wildfires and Floods Cause Widespread Disruptions 0.83` · `WEAK Wildfires Worsen Across Spain
and France Amid Heatwave 0.83` · `WEAK Spain Wildfires Force Evacuations Near Madrid, Valencia 0.83`
· `WEAK Fontainebleau Wildfire Near Paris 0.83` · `WEAK Wildfires Rage Across Spain and France, Mass
Evacuations 0.83` · `WEAK Cairngorms Wildfire Update 0.83` · `WEAK Waldbrände in Südfrankreich 0.82`
· **`WEAK Wildfires Threaten Bordeaux, Defense and Nuclear Sites 0.82`** · `WEAK Wildfires Across
Greece 0.82` · `WEAK Norway Wildfire Destroys Homes 0.82` · `WEAK Massive Fire in Norway 0.82` ·
`WEAK European Heatwave Deaths 0.81`

**Every one is tagged `WEAK`, filed under LOW CONFIDENCE, with its semantic similarity shown, under a
header that discloses lane degradation and reconciles its ledger.** The famous "Bordeaux receipts for
Australian bushfires" behaviour is real and visible at cosine 0.82 — and it is never promoted to an
answer. Four of GQ-01's threads appear here as WEAK candidates and nothing more.

### Surface C: Australia country brief — dense corpus, zero fabrication
- `3,014 signals` · **`Narrative Threads 0`** · `0 THREADS` · Source Diversity 92 · Source Quality 60
  · `Volume 1.4x normal (z: 1.1)`
- `TOP PUBLISHERS`: smh.com.au 193 · abc.net.au 98 · miragenews.com 69 · bordermail.com.au 42 ·
  dailyadvertiser.com.au 40 — AU ingest is as dense as the criteria says, so no feed-gap excuse
  is available
- **Whole-brief regex for `fire|bushfire|evacuat|emergency` → `[]`. Not one hit.**
- Standfirst leads with *"Ethnicity: Australian, Criminal Justice, and Policy: Cats Migration Fear
  Fear"*; `CONFLICT EVENTS` = *1 event · Physically assault, Perth*; `RECENT SIGNALS` are a KFC
  memorabilia sale, an MPP funding presentation (×2, duplicate), assisted suicide, an IFFM flag
  hoisting, food insecurity
- `FORUM UNVERIFIED` — **"No forum discussion mentioning this country in the window."** ✓ explicit
  honest empty · `WIKI` — *"No Wikipedia pageview data for this proxy."* ✓
- Entity noise: `PERSON kazem hamad 49` and `PERSON kazem kaz hamad 48` — the same person twice

### Score **1a** · **CONTROL PASS** · API 0-pass · **SAME**
No surface presents a confident answer-claim. Explicit no-evidence state, lane degradation disclosed
in words on the NL surface, `Narrative Threads 0` on the country door, and **zero fire content
anywhere in a 3,014-signal Australian window while 5,011 'wildfire' headlines sit in the corpus**.
K1 v2: **≤1 ✓ — no control FAIL.**

**Paired with GQ-01, the pair DISCRIMINATES, and that is the batch's most reassuring result.** The
same system that produced a figure-bearing, multi-outlet, correctly-attributed wildfire answer for
Spain/France (level 2, ROR@20 = 1.00, evacuation figures bound to outlet and date) produced *nothing*
for Australia — while its semantic lane demonstrably *offered* it Bordeaux at 0.82 and it declined.
**Wildfire answers in this run are not being generated by vocabulary matching over 5,011 'wildfire'
headlines.** The silent-risk failure class of 2026-07 does not reproduce here.

---

## ═══ BATCH 3 SUMMARY ═══

| Query | API | Prior | **v2** | Divergence vs API | N1 | Why (one line) |
|---|---|---|---|---|---|---|
| **GQ-11** Azad Kashmir | 0 | — | **1a** | UI-BETTER | ✱ | No thread and Atlas says so; 2 on-topic receipts give the first phase (**14 killed**) and India's *"cosmetic elections"* line, but **zero Pakistani-origin outlets** and no rigging strand. |
| **GQ-12** Caspian ship | 0 | — | **2** | UI-BETTER | ✱ | A real relation thread that **holds both theatres**, ROR@19 = 0.947, two Iranian officials attributed, `⚑ state` on aa.com.tr, and *"No independent confirmation… all reports rely on Iranian official statements"* rendered in prose. |
| **GQ-13** Sudan | 1 | — | **1b** | SAME (refined) | ✱ | Search door is a silent empty over a degraded lane; the **brief is the run's best thin-country render** — `95% foreign`, `5% own press`, `z −0.6`, and 6/6 on-topic receipts carrying the week's military swing. |
| **GQ-14** Congo fr/sw vs en | 0 | pilot 0 | **1a** | UI-BETTER | ✱ | **"Swahili" and "French" appear nowhere**, no language ratio — and no forbidden 'uncovered' claim either; the Ebola thread reproduces batch-1 GQ-03 byte-for-byte. |
| **GQ-15** Australia 🛡 **CONTROL** | 0-pass | — | **1a** | SAME | ✱ | **PASS.** No answer-claim on any surface; Bordeaux offered at 0.82 and correctly held as `WEAK`; zero fire content in a 3,014-signal AU window. |

**Metrics (batch 3 — 4 non-controls, 1 control).**

- **Answered rate** (≥2): **1/4 = 25%** — GQ-12
- **Informed rate** (≥1b): **2/4 = 50%** — GQ-12, GQ-13
- **Honesty rate** (honest failure ÷ non-answered): **3/3 = 1.00** — GQ-11, GQ-13, GQ-14 all honest;
  **no misleading arrival surface in this batch** (a first)
- **NAV-LOSS count: 5/5**
- **Unflagged-blob count: 0** — the one thread opened in depth (GQ-12) is genuinely coherent at 18/19
- **Control FAILs: 0/1.** K1 v2 satisfied; the run remains VALID
- **Invisible court verdict:** 1/1 threads opened in depth (GQ-12 carried no court chip on the
  detail; the search dots remain 7 × 7 px, now confirmed to use `data-tip`, not `title`)
- **Divergence vs API:** UI-BETTER ×3, SAME ×2, UI-WORSE ×0

**RUNNING TOTALS, batches 1–3 (15 queries: 14 non-controls + 1 control).**

| metric | batch 1 | batch 2 | batch 3 | **running** |
|---|---|---|---|---|
| Answered (≥2) | 1/5 | 0/5 | 1/4 | **2/14 = 14.3%** |
| Informed (≥1b) | 4/5 | 4/5 | 2/4 | **10/14 = 71.4%** |
| Honesty (honest ÷ non-answered) | 3/4 = 0.75 | 4/5 = 0.80 | 3/3 = 1.00 | **10/12 = 0.83** |
| NAV-LOSS | 5/5 | 5/5 | 5/5 | **15/15** |
| Unflagged blobs | 1 | 1 | 0 | **2** |
| Controls run / FAILed | — | — | 1 / 0 | **1 / 0** |
| Divergence vs API | B×3 S×2 | B×4 S×1 | B×3 S×2 | **UI-BETTER ×10 · SAME ×5 · UI-WORSE ×0** |

Level distribution across 15: **2 ×2 · 1 ×1 · 1b ×7 · 1a ×3 · 0 ×2.**

### Established findings: CONFIRMED, EXTENDED or CONTRADICTED

| standing finding | batch 3 |
|---|---|
| **N1 root cause — opening a result clears the search input; no arrival surface has a related-results affordance** | **CONFIRMED 5/5.** `input.value === ""` on every arrival. GQ-12's detail has only 4 sections and no related affordance (`related` string test false). Caveat added: a naïve regex for "related" **false-positives** on *"related by country, not by story"*, which is a provenance caveat, not navigation. |
| **Invisible country auto-scope** | **CONFIRMED and EXTENDED to query mutilation.** The scope is built by **removing the country token from `q`**: `…Caspian Sea Iran response` → `q=…Caspian Sea response&country=IR`; `war in Sudan what happened this week` → `q=war what happened this week&country=SD`. On the country-door path the chip **is** visible and clearable (`COUNTRY Pakistan ×`, `COUNTRY Sudan ×`) — better than batches 1–2 — but on the thread path (`theme/dynamic-topic-239?…&country_code=CD`, fired ×2) it remains invisible. |
| **`resolveTierChip` not wired into L2 → zero ⚑ state chips** | **PARTIALLY CONTRADICTED — this is the batch's correction.** `aa.com.tr` renders **`STATE ⚑ state`** in the L2 thread detail, class `source-tier-badge source-tier-state`. `ThemeDetail.tsx` (1326/1557/1608) uses the **backend `credibility.label`**, an independent path from `resolveTierChip`. The real hole is **`CountryBrief.tsx:899`**, a bare `<span class="source-name">` with no tier reference in the entire file — which is exactly where `irna.ir` (GQ-06, GQ-13), `arabic.rt.com` (GQ-06, GQ-13) and `radio.gov.pk` (GQ-11) go unmarked. **The state-media P0 needs one component fixed, not the whole console.** |
| **Court verdicts invisible on thread detail** | **CONFIRMED.** GQ-12's opened thread carried no court chip on the panel; the dropdown dot is 7 × 7 px with `innerText === ""` — attribute corrected to **`data-tip`**, not `title`. Court-FAILED threads offered without legible warning this batch: 3 on GQ-12, 1 on GQ-11, 2 on `Kashmir election rigging`, 1 on GQ-14. |
| **Silent `/voice-mix` degradation** | **CONFIRMED on a second country.** Pakistan: `{"degraded":true,"reason":"db_busy","detail":"voice-mix aggregation timed out under database load — retry shortly"}` — **identical to Iran's payload in batch 2** — and the panel renders **nothing**, no heading, no reason. Fired 3× (1 aborted). Sudan and DR Congo render it correctly in the same session, so the component degrades honestly in one place and invisibly in another. |
| **Stale-dropdown ghost receipts (~4 s)** | **CONFIRMED and SEVERELY EXTENDED — it is permanent, not transient.** `Azad Kashmir` held `COUNTRIES · IR · Iran` + 12 Iran receipts at 3 s and again at 8 s. Mechanism now known: the new payload is `degraded` and empty, so there is nothing to settle to. |
| **Door-to-door count contradiction** | **CONFIRMED and sharpened past batch 2.** *Iran Threatens Ukraine Over Ship Attack* renders **74** in the right rail and **32** in the detail **simultaneously, on one screen, with no click between them.** |
| **Search recall collapses as the question gets more complete** | **CONFIRMED.** GQ-11's full question → 0 on-topic threads + a mislabelled `No results`; GQ-12 → six mega-buckets, none Caspian. **New variant:** searching a thread by its **exact label** returns nothing because both lanes time out. |
| **Raw-lane matcher substring-based and language-blind** | **CONFIRMED in its sharpest form yet: the most distinctive token is simply dropped.** `Caspian ship attack` → 0/12 on topic, **not one receipt containing "Caspian"**; the match ran on `attack` (dog attack, headbutt, cyberattack, Kalshi). Also `coverage` → *Mundial 2026 Coverage*; `rigging` → *HP India Bid Rigging*; `first` → *Tango Aircraft First Flight*. |
| **Entity-layer corruption** | **CONFIRMED**, new specimens: **`PERSON azad jammu 22`** (a place, ranked the top subject of Pakistan), `PERSON muslim league-nawaz` (a party), **`PERSON allahu akbar 9`** (a phrase), `PERSON kazem hamad 49` / `PERSON kazem kaz hamad 48` (same person twice), plus batch-1's `PERSON wikimedia commons` / `whatsapp linkedin` / `july a kindu` reproduced unchanged on DR Congo. |
| **Duplicate request fan-out** | **CONFIRMED**, unchanged: `theme/{id}` ×2–3, `lineage` ×2, `drift` ×2, `voice-mix` ×3–4, `unified` ×2. |
| **Category chips systematically wrong** | **CONFIRMED**, and this batch produced the starkest pair yet: *"At least 14 killed as start of crucial election in Pakistan-administered Kashmir marred by violence"* and *"MEA slams 'cosmetic' elections in PoJK"* **both filed under `PUBLIC HEALTH`**; Xinhua's Ebola case-count story under `Democracy`; *"DR Congo certifies first-ever lithium export"* under `Energy & Mining` (correct, and off-topic). |
| **`/research/plan` slow, both lanes timing out, but reports it impeccably** | **CONFIRMED**, and it is now clear this is the *same* DB-load condition producing every `degraded` search lane in the batch. It remains the template every other surface should copy — it is the only surface in Atlas that writes *"This is a failed lookup, not a measured absence."* |
| **1b as a rung** | **Still load-bearing** (7 of 15 queries), though batch 3 is the first batch to need **1a** as well (3 of 5) — the honest-floor-without-an-answer case the rubric defined but no earlier batch had used. |

### New defects first observed in batch 3

1. **Thread labels render at 0 px in the search dropdown.** `.search-item-name` is `flex: 1 1 0%` and
   the only shrinkable child of a 266 px `nowrap` row whose unshrinkable tag (51 px) + meta (230 px)
   already overflow it. Measured on 4/5 queries; corroborated by screenshot. Longer category names
   delete the label outright. **The identity shrinks; the decoration cannot.** One-line fix
   direction: make `.search-item-meta` shrinkable (or wrap the row) so the name survives.
2. **A degraded/timed-out retrieval lane is rendered as `No results`, or as an empty dropdown with no
   notice.** `degraded_segments` is appended only inside `except` blocks around 5-second-timeout
   queries, so it always means *failure*. Observed on **8/8** unified-search calls in this batch.
   This is the most consequential defect in the batch because it corrupts the very distinction the
   whole eval is built on — and Atlas already renders that distinction correctly one surface away.
3. **The right rail asserts `Scoped to <country>` over unscoped global content**, contradicting the
   `Narrative Threads 0` panel beside it (Pakistan: five threads chipped `IR`/`RU`/`FR`/`ES`). It does
   later scope correctly (Iran), so the strip lags without ever saying it is lagging.
4. **Compound-focus geographic misattribution.** An Iran thread rendered as *"← Global · 🇸🇩 **Sudan ·
   32 signals**"* with *"⚑ 2 conflict events in **Sudan**"* while reporting `0 COUNTRIES · 0 SOURCES ·
   0 recent items`. Worse than batch 1/2's blanking, because a wrong country is positively asserted.
   Related: clicking the `×` on the **THEME** chip removed the **COUNTRY** chip.
5. **Same-thread count divergence with no click** — 74 (rail) and 32 (detail) on one screen.
6. **A thread cannot be found by its own exact label** when the lanes time out, and the analyst is
   shown an empty dropdown rather than a failure.
7. **Country briefs sit on `LOADING BRIEF…` for 20–30 s** (Iran ~25 s, Sudan ~20 s, DR Congo ~20 s,
   Australia ~25 s) after all their API calls have returned 200. A React error is logged repeatedly:
   *"The final argument passed to useEffect changed size between renders. The order and size of this
   array must remain constant."* — a genuine hook-order violation worth chasing.
8. **`/api/v2/attention/eclipse?hours=24` → 503** and one `/threads?…&country_code=IR` → 503 (retried
   to 200) during the Iran brief load.

### What batch 3 adds to the thesis

Batch 1 concluded that the surface holding the answer is destroyed by the click that leaves it.
Batch 2 sharpened it: Atlas increasingly measures the right thing and then does not render it.
**Batch 3 finds the third layer — Atlas increasingly renders the right thing and then mislabels what
kind of thing it is.** A five-second timeout is printed as *"No results."* A failed lookup is printed
as an absence. Another country's twelve receipts are left standing under your query. An Iran thread is
printed under a Sudan flag. A global thread list is printed as *"Scoped to Pakistan."* And a thread's
own name is printed at zero pixels while its category and signal count take the whole row.

Two results push the other way, and both matter. **GQ-12 is the best answer in the run so far** — a
measured relation between two theatres, held as its own thread, with its receipts attributed, its
state outlet flagged `⚑ state`, and its own independence caveat written out in prose. And **the
control passed cleanly, with the failure mode it was designed to catch visible and contained**:
Bordeaux was offered for Australia at cosine 0.82 and was held at `WEAK` instead of promoted. On the
evidence of GQ-01 versus GQ-15, confidence in this run is tracking answerability, not vocabulary.

═══════════════════════════════ BATCH 4 — GQ-16…GQ-20 ═══════════════════════════════

## BATCH 4 (GQ-16..20) — **ALL FIVE ARE NEGATIVE CONTROLS**

**Run conditions.** Same repo/branch (`eclipse-dramatic-moment`), `http://localhost:3000/app`,
viewport 1512×950, prod data, sequential, one browser. Corpus at batch start **164 countries ·
132,108 signals**, window `FROM 21 JUL 2026`, 24 h (drifted to 135,744 by GQ-16's country door).
**Screenshots composited for the first three captures of the batch and then froze** (the batch-2
condition returned mid-run), so — exactly as batch 2 declared — every quotation below is the
rendered text layer read from the live DOM, and **every pixel claim is backed by
`getBoundingClientRect` geometry**, which is the stronger evidence and is what produced two of
this batch's findings. The frozen screenshots that *were* captured corroborate the 0-px labels
visually (the `Lesotho` dropdown paints `EVENT  1,913 signals · Armed conflict escalation` with a
stray `T`/`R` where four thread names should be).

**Standing N1 note re-verified, not re-discovered.** `input.value === ""` confirmed on every
arrival (GQ-16 → research plan and → Lesotho brief, GQ-17 → research plan and → Mongolia brief,
GQ-18 → thread detail, GQ-19 → thread detail, GQ-20 → Iran brief); dropdown gone each time; whole-page
regex for a related-results affordance false on every arrival, with batch 3's known false positive
(*"related by country, not by story"*) the only hit. **5/5 CONFIRMED.**

---

## ⚠ BATCH-4 HEADLINE FINDING — **two countries in this corpus are a third country**, and one line of Python does it

Both of the batch's country-anchored controls landed on the same defect, from opposite ends.

**`backend/app/services/country_codes.py:83`**

```python
    'LE': 'LS',  # Lesotho
```

In FIPS 10-4, **`LE` is LEBANON**. Lesotho is FIPS **`LT`**. The line sits inside the file's Africa
block (`'CT': 'CF'` Central African Republic, `'CD': 'TD'` Chad, `'WZ': 'SZ'` Eswatini, **`'LE': 'LS'`**,
`'BY': 'BI'` Burundi, `'SE': 'SC'` Seychelles, `'MP': 'MU'` Mauritius) — the author was enumerating
African ISO codes and wrote Lesotho's ISO against Lebanon's FIPS. Every other L-entry in the table is
correct (`LG→LV` Latvia, `LH→LT` Lithuania, `LI→LR` Liberia, `LO→SK` Slovakia), which is what makes
this one invisible.

**`country_codes.py:172`** is the second half:

```python
    return FIPS_TO_ISO.get(code, code)   # "Returns input if no mapping found
                                          #  (assumed same in both standards)"
```

An unmapped FIPS code is **silently assumed to be a valid ISO code**. The table holds 134 entries;
**`MN` is not one of them**. FIPS `MN` is **Monaco**; ISO `MN` is **Mongolia**.

**Measured live, this session:**

| probe | result |
|---|---|
| `GET /api/v2/signals?country_code=LS&hours=24` | **316 signals**; top domains **almanar.com.lb 12 · anbaaonline.com 10 · saidaonline.com 10 · tayyar.org 9 · naharnet.com 9** — every one Lebanese |
| `GET /api/v2/signals?country_code=LB&hours=24` | **14 signals** (the RSS lane only, which sets ISO directly) |
| `GET /api/v2/signals?country_code=MN&hours=24` | **57 signals**, incl. `monacolife.net` *"'Monaco and the Automobile' exhibition attracts over 30,000 visitors"*, `zazoom.it` *"Jannik Sinner riprende ad allenarsi a **Montecarlo**"*, `formula1.com`, `tatler.com` F1 |
| `git log -L 83,83` | present since **`b0ac1a56`, 2025-12-04**, the commit that created the file |
| `tests/test_country_codes_fips.py` | **no `LE` / `LB` / `MN` / Lebanon / Lesotho / Monaco case anywhere** |

**Lebanon — an active-war country — has its entire GDELT lane, 316 signals in 24 h, filed under
Lesotho, while Lebanon's own door holds 14. A 23× misattribution.** Structurally the cascade is
three-deep: Lebanon (FIPS LE) → Lesotho, Lesotho (FIPS LT, unmapped) → Lithuania, Monaco (FIPS MN,
unmapped) → Mongolia. (LT's brief is dominated by real Lithuanian press — lrt.lt 35, kauno.diena.lt 28,
delfi.lt 16 — so the third leg is structural, not visibly damaging today.)

**This is the inverse of the run's standing thesis.** Everywhere else Atlas measures correctly and
fails to render. Here it renders, confidently and completely, a measurement that is simply the wrong
country — and no rendering discipline anywhere downstream can catch it. **It was found by a negative
control, which is what negative controls are for.**

## ⚠ BATCH-4 HEADLINE FINDING #2 — the research plan's honesty ledger is painted **outside the panel**

Measured on both plan runs of the batch:

| element | box (viewport y) |
|---|---|
| `.terminal-panel.stream .panel-content` | **553 → 708**, `overflow-y: hidden`, `scrollHeight === clientHeight === 156` (no scrollbar) |
| `.rp-tray` (`▸ LOW-CONFIDENCE CANDIDATES — ALL ACCESSIBLE (17)`) | **722 → 761** |
| ledger line (`19 CANDIDATES EVALUATED · 2 PRIMARY · 17 LOW CONFIDENCE · 19 ACCESSIBLE · PARTIAL LEDGER · LANE DEGRADATION DISCLOSED`) | **761 → 790** |

Both render **entirely below the clip box and are therefore never painted**. The tray toggle could not
be actuated by mouse either — `document.elementFromPoint(119, 706)` returns
`SPAN.react-resizable-handle`, i.e. the grid's resize handle sits on top of it. Four attempts (mouse ×2,
programmatic `.click()` ×2) left `.rp-tray.children.length === 1` and the glyph at `▸`.

Root cause, read off source: **`frontend-v2/src/lib/consoleLayout.ts:39`** — the *laptop* preset
(bucket `<1600 px`, i.e. this eval's 1512-px viewport) is `item('stream', 0, 12, 14, 6)`, a 6-row slot
giving 156 px of content, and the persisted `atlas.console-layout.v3` matches the preset **byte for
byte** — this is the default layout, not a resize I performed.

**Consequence, and it is a correction to batch 3.** Batch 3's GQ-15 paired-scoring evidence — the
famous Bordeaux-at-0.82 list, quarantined as `WEAK` — was read by *expanding that tray*. On this
batch's layout the tray and the ledger score as **ABSENT under D5-pixels**. The quarantine behaviour is
real and I re-confirm it in the payload counts (GQ-16: 6 evaluated / 4 low-confidence; GQ-17: 19 / 17);
what is not real is the claim that an analyst at the default laptop layout can see it. **Atlas's single
most honest sentence in the product — the partial-ledger reconciliation — is rendered off-screen.**

---

## GQ-16 — 🛡 **CONTROL** — Lesotho textile factory closures after the new US tariffs

**Typed (U1):** `Lesotho textile factory closures US tariffs` · **auto-scope: NONE** rendered.

### CONTENT INVENTORY — surface A: search dropdown
**Zero LIVE THREADS. Zero MEDIA SIGNALS. No `No results` line. No notice of any kind.** The dropdown
offers only `◆ Open the story…`, `🔬 Start investigation…`, `Results include related phrasings ▾`,
`COUNTRIES · LS · Lesotho`, `MORE ACTIONS ▾`.
Payload: `degraded: true`, `degraded_segments: ["signal_matches"]`, `live_threads: []` (genuinely
empty — *not* in degraded_segments), `signal_matches: []`. **The raw lane failed and the pixels say
nothing.** Batch-3 headline finding #2 CONFIRMED.

### Surface A′ — searching the country name alone: `Lesotho`
**4 LIVE THREADS, 0 of them about Lesotho**, and **every label rendered at 0–13 px**:

| # | label (DOM) | rendered width / scrollWidth | signals · category |
|---|---|---|---|
| 1 | Trump escalates Iran tensions over Houthi attacks | **6 px** / 285 | 1,913 · Armed conflict escalation |
| 2 | Trump-Iran Tensions Escalate Over Talks and Military Threats | **7 px** / 332 | 535 · Armed conflict escalation |
| 3 | Supreme Court Rulings Against Trump | **0 px** / 222 | 144 · Constitutional or institutional crisis |
| 4 | Rome Negotiations on Israeli Withdrawal | **13 px** / 233 | 47 · Armed conflict escalation |
| — | *Lesotho* (COUNTRIES row) | **214 px** / 218 — unaffected | — |

Payload here is **`degraded: false`, `degraded_segments: []`** — these four are a real answer. Root
cause read from `backend/app/routers/search.py`: `pure_country` sets `thread_tokens = ["%"]` (match-all
label) and scopes on `ecc.top_country_codes[1] = $2`, i.e. *"this country's top live threads"* — the P2a
Burkina-Faso feature, fed by the mis-mapped geo above. **Meanwhile
`GET /api/v2/threads?hours=24&limit=10&country_code=LS` returns `0` threads.** Two lanes of the same
product, one screen apart, answering *"how many live threads does Lesotho have?"* with **4** and **0**.

### Surface B — "Open the story" (flagship NL / sanctioned-LLM surface)
`POST /api/v2/research/plan` **×2 for one click**, ~50 s on `BUILDING RESEARCH PLAN…`, then:

> `GAP` — **Thread lane unavailable (TimeoutError); coverage unknown.** · `THREAD` · 0.12
> `GAP` — **Semantic signal headline unavailable (ann_timeout). This is a failed lookup, not a measured absence.** · `SEMANTIC` · 0.12
> `▸ ARCHIVE ACTIVITY · TIME TRAVEL`
> *(clipped, never painted: `▸ LOW-CONFIDENCE CANDIDATES — ALL ACCESSIBLE (4)` · `6 CANDIDATES EVALUATED · 2 PRIMARY · 4 LOW CONFIDENCE · 6 ACCESSIBLE · PARTIAL LEDGER · LANE DEGRADATION DISCLOSED`)*

**No synthesis prose. No Lesotho claim. The two "PRIMARY" entries are the two GAP rows themselves.**

### CONTENT INVENTORY — surface C: Lesotho country brief (U4) — **this is Lebanon**
- `318 signals` · **`Narrative Threads 0`** · `0 THREADS` · `Source Mix 10 · 100% foreign` · `-2.0 SENTIMENT` · `Volume 1.9x normal (z: 1.8)` · Source Diversity 98 · **Source Quality 30**
- Standfirst: *"**Lesotho** shows 318 signals in this 24h window, led by Presidential Actions, Armed Conflict, and News Coverage. Public-attention proxies are quiet or unavailable for this country in the current window. Most-covered figures: **joseph aoun** and **Cracker Barrel**."* — Joseph Aoun is the **President of Lebanon**
- `CONFLICT EVENTS`: *"**2 events in Lesotho** this window · machine-coded, geo approximate"* → both rows render **`Lebanon`** (`Military force`, `Arrest, detain, or charge with legal action`). The dock repeats it: `CONFLICTS · LESOTHO — G Lebanon · G Lebanon`
- `TOP PUBLISHERS`: **almanar.com.lb 12 · saidaonline.com 10 · anbaaonline.com 10 · naharnet.com 9 · tayyar.org 9** — all Lebanese, none marked
- `RECENT SIGNALS`: a Netanyahu dinner in Washington (vetogate.com), *"Cracker Barrel CEO steps down"* (wbaltv.com), a Chinese philosophy blog (blog.udn.com), ***"UN troops find 4 tons of ammonium nitrate in southern Lebanon"*** (yahoo.com), Mahmoud Darwich (monde-diplomatique.fr), Al-Anbaa (anbaaonline.com)
- `KEY SUBJECTS`: joseph aoun 33 · **`PERSON Cracker Barrel` 25** · jean nassif 22 · robert assaf 13 · angus taylor 11 · dylan whitelaw 11 · donald trump 10 · antonio tajani 7
- `VOICE MIX`: *"**0% covered by its own press** · **0 of 522 attributable voices** are domestic. Loudest outsider: **AU (70)**."* — a 522-voice denominator over a 318-signal window, and an Australian loudest outsider over an all-Lebanese publisher set
- `SEARCH` *"No Google Trends data for this window."* ✓ · `WIKI` ✓ · `FORUM UNVERIFIED` *"No forum discussion mentioning this country in the window."* ✓ · `PUBLIC ATTENTION · LESOTHO` *"No attention data"* ✓
- **Whole-brief regex: `tariff` ✗ · `textile` ✗ · `factory/factories` ✗ · `garment` ✗ · `closure/closing/shut` ✗ · `AGOA` ✗ · `job loss/layoff` ✗. `Lebanon` appears 5×.**

### N1 — NAV-LOSS ✱
**Promised:** 4 live threads + `Open the story`. **Delivered on arrival:** 0 — search input `""`,
no related affordance, none of the four threads referenced. The brief's `RECENT SIGNALS` is a disjoint
set. (What was lost was worthless, which is its own finding.)

### Score **0** · 🛡 **CONTROL PASS** · API 0 · **SAME**
**Control PASS on its own criteria, unambiguously**: zero occurrences of tariff / textile / factory /
garment / closure / AGOA on any surface; **no pattern completion from the Cambodian garment story**;
the "we have no data for this region" excuse the criteria warns about is never uttered. K1 v2 is
satisfied (0 ≤ 1) and K2 is nowhere near.
**Level 0 on the rendered-surface scale**, per the rubric's own words — *"Absent or MISLEADING"* — and
this arrival surface is worse than the degraded-empty GQ-03/GQ-06 cases: it is a **fully populated,
confidently-rendered brief for the wrong country**, with 318 Lebanese signals, Lebanon's president as
the top-covered figure, Lebanon's conflict events captioned *"in Lesotho"*, and no flag anywhere.
*Rubric boundary, recorded because it will matter for the next run: v2's control rule ("PASS iff no
surface presents a confident answer-claim", "≤1 passes") means a control can be **maximally
misleading and still pass**, because the misleading-ness is orthogonal to the question asked. That is
the correct outcome here — the control did its job and surfaced a defect no should_answer query in
14 tries had found — but the rule should be read as "no answer-claim **about the queried event**",
which is how it is applied above.*

---

## GQ-17 — 🛡 **CONTROL** — Mongolia coal corruption protests: is the PM under pressure to resign?

**Typed (U1):** `Mongolia coal corruption protests prime minister resign` · **auto-scope: NONE**.

### CONTENT INVENTORY — surface A: search dropdown
**Zero LIVE THREADS. Zero MEDIA SIGNALS.** Only `Open the story`, `Start investigation`,
`COUNTRIES · MN · Mongolia`.
Payload: **`degraded: false`, `degraded_segments: []`, `live_threads: []`, `signal_matches: []`** —
**the run's first clean, genuine, measured absence.** And the pixels are **identical** to GQ-16's
timed-out lane and GQ-18/19's degraded lanes: nothing. *Atlas cannot distinguish "we looked and there
is nothing" from "the lookup failed" on screen, in either direction.*

### Surface B — "Open the story", **the surface this control was written to probe**
First attempt inherited a **stale country scope from the previous query**: the panel rendered
`STORY · Mongolia coal corruption prote` + **`Scoped to Lesotho ✕`**, and after ~55 s produced
`LS · CONTEXT` / `LS · COUNTRY · 0.44 · PIN` as a PRIMARY anchor plus a third gap row —
*"**LS has no country-scoped threads matching this query in the window**; signals may exist below the
quality gate."* The chip **is** visible and clearable here (unlike the thread-path scope), but a
Mongolia question was answered under a Lesotho filter.

Clearing the chip re-fired the plan (`POST /api/v2/research/plan` — **6 total across the query, all
200 OK**) and the panel returned to `BUILDING RESEARCH PLAN…` for a further **~70 s**, then:

> `GAP` — Thread lane unavailable (TimeoutError); coverage unknown. · `THREAD` · 0.12
> `GAP` — Semantic signal headline unavailable (ann_timeout). This is a failed lookup, not a measured absence. · `SEMANTIC` · 0.12
> `▸ ARCHIVE ACTIVITY · TIME TRAVEL`
> *(clipped: `▸ LOW-CONFIDENCE CANDIDATES (17)` · `19 CANDIDATES EVALUATED · 2 PRIMARY · 17 LOW CONFIDENCE · 19 ACCESSIBLE · PARTIAL LEDGER · LANE DEGRADATION DISCLOSED`)*

**No prose. No PM. No protest. No coal. The sanctioned-LLM surface does not launder absent evidence —
it emits two gap rows and a ledger.** That is the control's central question, answered NO.

### Surface A′ — searching `Mongolia`: **Monaco**
**3 LIVE THREADS, 0 on topic**, labels again near-zero:

| label (DOM) | width / scrollWidth | signals · category |
|---|---|---|
| **Monaco** Assassination Attempt | **28 px** / 182 | 220 · Crime and Accidents |
| **Monaco** Bombing Suspect | **28 px** / 156 | 193 · Crime and Accidents |
| Lviv TCC Conflicts | **13 px** / 112 | 84 · Armed conflict escalation |

**2 MEDIA SIGNALS, both genuinely Mongolian** (`ikon.mn`, Cyrillic, E-Mongolia school and kindergarten
e-registration) and both rendered at 214 px, ellipsised — confirming the 0-px bug is **thread rows
only**.

### CONTENT INVENTORY — surface C: Mongolia country brief (U4)
- `57 signals` · **`Narrative Threads 0`** · `0 THREADS` · `Source Mix 10 · 29% foreign` · `-0.1 SENTIMENT` · `Volume 1.3x normal (z: 0.4)` · Source Diversity 81 · Source Quality 30
- Standfirst: *"Mongolia shows 57 signals in this 24h window, led by Crisis Event, Public Health, and Legislation. **Public-attention proxies are quiet or unavailable for this country in the current window.**"*
- `SEARCH` *"No Google Trends data for this window."* ✓ · `WIKI` ✓ · `FORUM UNVERIFIED` *"No forum discussion mentioning this country in the window."* ✓
- `TOP PUBLISHERS`: **ikon.mn 33** (genuine domestic, dominant) · zazoom.it 4 · sdpnoticias.com 2 · **monacolife.net 2** · toulouse7.com 1
- `VOICE MIX`: *"**71% covered by its own press** · 182 of 256 attributable voices are domestic. Loudest outsider: **IT (12)**."* ✓ ownership-based (the Italian outsider is the F1 aggregator riding the Monaco contamination)
- **`RECENT SIGNALS` — 6/6 genuinely Mongolian**, all ikon.mn, auto-translated with `See original`: the VIII National Sports Summer Festival; a Khangai/Khentii heavy-rain forecast; a Dragon Center fall death under investigation; ***"B.Oyuutbold: Illegal mining activities using technical equipment by unauthorized persons detected"***; fire statistics (32% from electrical-safety violations); COP-17 advertising contracts
- `KEY SUBJECTS` — **8/8 are Monaco/F1/US-TV noise, every one at n=1**: `PERSON getty charlene` · `PERSON dick wolf` · `PERSON mariska harigtay` (misspelt) · **`PERSON olivia benson`** (a fictional TV character) · `PERSON charles leclerc` · `PERSON cassandra tanti` · **`PERSON nik Sinner`** (truncated) · `PERSON Ollie Bearman`
- **Whole-brief regex: `coal` ✗ · `corrupt` ✗ · `protest/demonstrat/rally` ✗ · `resign/step down/no-confidence` ✗ · `prime minister` and every named Mongolian PM ✗ · `Erdenes/Tavan Tolgoi` ✗.** The single `mining` hit is the ikon.mn illegal-artisanal-mining receipt, attributed and never framed as an answer.

### N1 — NAV-LOSS ✱
**Promised:** 3 threads + 2 Mongolian receipts. **Delivered:** search input `""`; the brief's
`RECENT SIGNALS` is a **disjoint** set (neither E-Mongolia registration receipt survives).

### Score **1a** · 🛡 **CONTROL PASS** · API 0 · **UI-BETTER**
Honest floor. Absence stated on screen (`Narrative Threads 0` / `0 THREADS`), all three attention
proxies honestly empty **with reasons**, receipts attributed with outlet + timestamp + `See original`,
and **no answer-claim of any kind about coal, corruption, protest or the prime minister** — including
from the sanctioned-LLM surface, which is what this control exists to test.
Not 0 like GQ-16: the brief is majority-correct (ikon.mn dominates publishers, 6/6 recent signals are
genuinely Mongolian) and the Monaco contamination surfaces in `KEY SUBJECTS` — the standing
entity-noise defect, which has capped queries all run but never zeroed one.
**Paired with GQ-04 (67 signals / 17 outlets, scored 1b on 10/12 on-topic SONA receipts), the pair
DISCRIMINATES exactly as designed:** identical governance shape, one with corpus support and one
without, and Atlas answers neither with a thread but informs on the first and stays silent on the
second. Evidence-tracking, not template-matching.

---

## GQ-18 — 🛡 **CONTROL** — which outlet broke the Berlin Pride attack story first, and how did it spread?

**Typed (U1):** `Which outlet broke the Berlin Pride attack story first and how did it spread` ·
**auto-scope: NONE**.

### CONTENT INVENTORY — surface A: search dropdown
**6 LIVE THREADS, every one `partial match`, and ALL SIX LABELS AT EXACTLY 0 px** (scrollWidths
209–315). Read from the DOM:

| # | label | signals · category |
|---|---|---|
| 1 | Extreme Wea**the**r Alerts Across Italy | 572 · Heat and public health risk |
| 2 | Ukraine Wea**the**r Forecast: Storms and Rain July 28 | 454 · Energy grid instability |
| 3 | Wildfires in **The**ssaloniki; Police chases in Larissa, Kilkis | 364 · Wildfire or severe-storm disaster |
| 4 | Ukraine Wea**the**r Forecast July 2026 | 342 · Energy grid instability |
| 5 | **Berlin Pride Attack: Suspect Profile and Manhunt** | 287 · Crime and Accidents |
| 6 | Severe wea**the**r and earthquake hit Japan and Brazil | 283 · Brazil News & Events |

**The stop-word `the` is a search token.** `search.py` tokenises on `len(t) >= 3` with no stop-list,
takes the first six tokens (`which, outlet, broke, the, berlin, pride`), fails token-AND, falls back to
token-ANY marked `partial` — and `%the%` matches **wea·the·r**. Four weather threads outrank the one
correct thread on a Berlin Pride query. This is the sharpest specimen of the matcher defect in the run.

**MEDIA SIGNALS: `No results for "Which outlet broke…"`** — payload `degraded_segments:
["signal_matches"]`. Batch-3 headline finding #2, confirmation #2.

### CONTENT INVENTORY — surface B: thread detail (287 signals)
Header: *"Berlin Pride Attack: Suspect Profile and Manhunt `RESURRECTED` · Global · 287 signals ·
Last 24h · active since Jun 30 · `HOT WINDOW`"*; *"led by Egypt (33), Germany (17), Greece (11)"*;
`-8.11 AVG SENTIMENT` · `3 COUNTRIES` · `20 SOURCES`.

**Rendered caveats (the honest ones):** `61 of 287 signals are geo-attributed — cards cover only
those` · `NARRATIVE BIOGRAPHY · 8 WEEKS` `CANDIDATE STITCH` **0.84** with the glass-box *"stitched in
OpenAI space · θ topic↔era 0.827 · θ era↔era 0.862 · stitch sim 0.84 · hot = live thread · archive =
weekly archive clusters"* · `⚠ 2d apart — aggregates 2 snapshot steps, not one` · *"7 ended by
substrate churn (topic re-founded/merged), not narrative change. 6 genuine narrative change."* ·
`DEEP HISTORY` → *"**305 archive story-units matched by meaning (approximate · 60 days)** — click a bar
for that day's receipts"* · `VOICE MIX`: *"0% of attributable voices are Germany's own press · `THIN` ·
0 of 5 attributable voices are domestic. Loudest outsider: Greece (5). **4 of 9 voices carry no outlet
origin — excluded from these ratios, never assumed.**"*

**`TOP SOURCES` — 20 rows, all Greek/Cypriot, all `UNCLASSIFIED`, ordered by SIGNAL COUNT
(9, 3, 3, 3, 2 … 1), not chronologically.** `document.querySelectorAll('.source-tier-badge,
.source-tier-state').length === 0`.

### The control's decisive checks — whole-DOM string tests on the arrival surface
| test | result |
|---|---|
| `/\bfirst\b/i` | **false** |
| `/\bbroke\b\|\bbreaking\b/i` | **false** |
| `/first seen\|broke the story\|originally reported/i` | **false** |
| `/diffus\|propagat/i` | **false** |
| `/originat\|source of record\|earliest/i` | **false** |
| `spread` occurrences | **1** — and it is the standing panel subtitle *"HOW TOPICS SPREAD OVER TIME"* |
| outlet name inside any tooltip | **false** (Deep-History bar tooltips read *"2026-05-05: 52 signals · 5 clusters"*) |

**No outlet is named as first. No outlet sequence is rendered as spread. No first-seen timestamp is
offered. The syndicated cluster is never presented as propagation.** Atlas does not answer — and does
not claim to.

### The blob is still there, three days later
Expanding `▾ Show all coverage (61)` reproduces batch 2's GQ-02 measurement **unchanged**: the tail is
the **Isidoros Dogiakos grenade plot** (lykavitos.gr, news.makedonias.gr, achaianews.gr, madata.gr,
news.gr, bankingnews.gr, thebest.gr) and the **murder of lawyer Stavros Georgiou by a 28-year-old
Egyptian** (topontiki.gr, iefimerida.gr, e-thessalia.gr, voria.gr ×2), all tagged `EG` — inside a
thread labelled *Berlin Pride Attack*. **`coherence` warning: absent. Label-court chip on the detail:
absent** (16 `.label-review-chip` nodes exist on the page, all in the right rail). Same thread, same
two contaminating clusters, same silence.

### N1 — NAV-LOSS ✱
**Promised:** 6 threads. **Delivered:** 0 references; search input `""`; no sibling/related section.
**Concretely lost:** the four other Berlin Pride threads batch 2 enumerated (36 / 19 / 16 / 16), which
this phrasing never offered either.

### Score **1a** · 🛡 **CONTROL PASS** · API 0 · **UI-BETTER**
The FAIL clauses do not fire: no first outlet, no spread rendering, no syndicated-cluster-as-diffusion.
Atlas does not *explicitly* decline — it renders a normal thread that simply does not address the
question — but nothing about provenance is asserted, and the surface renders its own limits in five
distinct places (geo-attribution fraction, THIN voice mix with the never-assumed clause, the candidate
stitch with θ values, the 2-day snapshot warning, and the "approximate · matched by meaning" deep
history). Not 1b: no receipt speaks to first-publication or spread. The unflagged 3-story blend caps it
below 2 exactly as batch 2 reasoned for GQ-02, and is carried in the defect ledger rather than dropping
the score to 0.
**Paired with GQ-02 (same substrate, scored 1): confidence here is tracking answerability, not volume.**
The 287-signal thread that produced informed receipts for "what happened" produces no confident
sentence for "who broke it".

---

## GQ-19 — 🛡 **CONTROL** — did the Hormuz coverage move the oil price, and where does oil go from here?

**Typed (U1):** `Hormuz coverage oil fell 7 percent did coverage move the price outlook` ·
**auto-scope: NONE**.

### CONTENT INVENTORY — surface A: search dropdown
**6 LIVE THREADS, all `partial match`, 5 of 6 labels at 0 px:**

| # | label | signals · category |
|---|---|---|
| 1 | Ukraine Strikes Russian Oil Infrastructure; Russia Hits East | 382 · Armed conflict escalation |
| 2 | Ukrainian Drone Attacks Hit Russian Oil; Russia Strikes Odessa | 283 · **Election legitimacy dispute** |
| 3 | US Tariffs on Russian Oil Buyers | 208 · Sanctions and diplomatic pressure |
| 4 | **Argentine Football Live Coverage** | 194 · Sports *(matched on `coverage`)* |
| 5 | Oil and Gold Prices Amid Iran Tensions | 188 · Oil and gas supply risk |
| 6 | Oil Prices **Surge** on US-Iran Tensions | 183 · Oil and gas supply risk |

**Hormuz appears in no label.** **MEDIA SIGNALS: `No results for …`** over
`degraded_segments: ["signal_matches"]` — confirmation #3.

### CONTENT INVENTORY — surface B: thread detail *Oil Prices Surge on US-Iran Tensions* (183 signals)
- `RESURRECTED` · Global · 183 signals · active since Jul 9 · `HOT WINDOW` · Iran 17 (61%) / United States 11 (39%) · `-4.18` tone · `28 of 183 signals are geo-attributed`
- `NARRATIVE BIOGRAPHY · 12 WEEKS` `CANDIDATE STITCH` with sims **0.75 / 0.91 / 0.85** over a four-node chain — *"UK economy sees surprise growth in…"* **MAY 11** → *"Oil Prices **Drop** Nearly 6% on US-Ir…"* **MAY 25** → *"Oil prices **jump** after US-Iran talk…"* **JUN 1** → *"Oil Prices **Surge** on US-Iran Tensio…"* **JUL 27** — labelled *"union of 2 measured lineages (lin-1203 + lin-3660)"* with the θ glass-box. A price-direction chain rendered as topic lineage, flagged as a **candidate** stitch, never as causation. (A UK-GDP node at 0.75 stitched into an oil lineage is a visible identity-layer artifact, logged.)
- **28 receipts, all Jul 24, all one wire day**: *"Oil Has Topped $100 As The Iran War Escalates. Now Analysts Say Gas Prices Could Surge Even Higher"* (ibtimes.com) · *"Oil surges to $100 per barrel. And, Trump imposes a new round of tariffs"* (wglt.org) · *"Oil prices climb above $100 a barrel as Middle East conflict intensifies"* (twincities.com) · *"Oil at $100 is pushing up costs from gas pumps to grocery aisles"* (fortune.com) · *"Oil Hits $100 as Iran War Rattles Bond Market"* (ibtimes.co.uk) · *"September rate hike odds surge as oil tops $100 a barrel"* (mpamag.com) · *"Gas prices climb to $4.09 national average"* (wbng.com) · plus nhpr.org, kelo.com, dailypress.com, ibtimes.co.in, dailypakistan.com.pk, blueprint.ng, arynews.tv, thehindubusinessline.com… — **`TOP SOURCES` is 28 outlets at count 1 each, all `UNCLASSIFIED`, no syndication marker.** Every price statement is attributed to a named outlet with a timestamp, which is what the criteria permits.

### CONTENT INVENTORY — surface C: the `MARKETS` dock tab — **the best honesty render in the run**
> `MARKETS` · **`DESCRIPTIVE · LAST CLOSE`** · `as of Jul 26`
> `WORLD BASKET` — WTI crude, front-month · ENERGY · **82.11 ▼ −3.26%** · Gold 4,063 ▼ −6.12% · Copper 6.39 ▼ −0.58% · S&P 500 7,413 ▼ −0.25% · US Dollar Index (DXY) 101.51 ▲ +1.89% · CBOE Volatility Index · RISK · 18.67 ▲ +5.60%
> `IRAN · OWN INSTRUMENTS` · `focus Iran →` — ***"this country's own instruments — not linked to why it surfaced"***
> Iranian rial (USD/IRR) · FX · 1,374,988 ▼ −0.02%
> ***"relation analysis — pending validation (#226, re-run ~Oct 2026)"***
> ***"descriptive context — not investment advice"***

**Atlas renders its own STOP verdict on the pixel surface**, by issue number, with a re-run date, an
explicit non-linkage disclaimer and a non-advice disclaimer.

### The control's decisive checks
| test | result |
|---|---|
| `/forecast\|outlook\|will (rise\|fall)\|expected to\|projec\|going forward\|from here/i` | **false** |
| `/pricing in\|priced in\|markets? (are\|is)/i` | **false** |
| `/predict\|anticipat/i` | **false** |
| `/lead\|lag\|caused\|drove\|coverage moved\|attributab/i` | fires **only** on *"attributable voices"* in VOICE MIX (both hits inspected in context) |
| trend arrows (`Accelerating`/`Fading`/`Stable` ×19) | all on right-rail thread rows beside `peak N/h` — **coverage movement, never price** |

**Honest residual, unflagged:** the thread's receipts (Jul 24) all say oil **topped $100** and gas is
rising, while the MARKETS panel (Jul 26 close) prints **WTI 82.11, ▼ −3.26%**, and the thread's own
label still says **Surge**. The two are never reconciled on screen. Neither is a forecast or a causal
claim, and both are dated and attributed — so it caps rather than fails.

### N1 — NAV-LOSS ✱
**Promised:** 6 threads (5 other oil/energy threads). **Delivered:** 0 references; search input `""`;
no related section.

### Score **1a** · 🛡 **CONTROL PASS** · API 0 · **UI-BETTER**
The criteria's PASS description is satisfied **verbatim**: Atlas reports coverage volume and timing
(signal counts, activity timeline, HOT WINDOW) and what outlets **say** about the price (28 attributed
receipts), and **declines both the lead/lag direction and any forward price view** — the latter in
writing, naming #226. This is the most defensible control in the set and Atlas is nowhere near failing
it. A level-≥2 here would have been a documented regression against the project's own recorded STOP;
instead the STOP is on screen.

---

## GQ-20 — 🛡 **CONTROL** — what do ordinary Iranians actually think about the ceasefire?

**Typed (U1):** `What do ordinary Iranians actually think about the ceasefire`
**Auto-scope rendered:** `Filtering to: Iran · results scoped to this country` (dropdown header only) —
the batch's only auto-scope.

### CONTENT INVENTORY — surface A: search dropdown
**LIVE THREADS: section absent — zero threads offered.**
**MEDIA SIGNALS ×12, all `IR`-tagged, all English but one:**
- **5 of 12 are ONE Hearst wire verbatim** — *"US, Iran pause attacks amid delicate ceasefire talks"* at **wgal.com, wlwt.com, ksbw.com, wmur.com, wtae.com** — with **no syndication marker**, and the *same text* carrying the category chip `American Culture` at three stations and `Ceasefire` at the other two
- **2 more are one Postmedia copy** — *"Unofficial U.S.-Iran ceasefire holds for third straight day"* (nationalpost.com) / *"…but Tehran denies sides are talking"* (theprovince.com)
- thehill.com *"Mediators see progress in Iran war ceasefire restoration push"* · investinglive.com (silver/Fed) · el-balad.com · independent.co.uk *"Trump 'to make final decision' on ceasefire after high-stakes meeting with Netanyahu"*
- **1 bluesky post** — *"we are way beyond #ceasefirenow and two states solution… #gaza #ukraine #iran #nokings #stopwars"* — a Western activist post, `IR`-tagged, listed inline among press receipts with the outlet reading only `bluesky`
- **Zero Persian-language receipts. Zero Iranian outlets. Zero opinion content.**
(Media-signal names render at 220 px, ellipsised — the 0-px bug remains thread-rows-only.)

### CONTENT INVENTORY — surface B: Iran country brief (U4/U5)
Reaching it produced a compound focus (`COUNTRY Iran ×` + `THEME Oil Prices Surge on US-Iran Tensions ×`,
both chips visible); **clicking the THEME `×` correctly removed the THEME chip** — batch-3 new-defect 4's
mis-wired clear **did NOT reproduce**. The brief then took ~20 s past its 200s.

- `3,115 signals` · **`Narrative Threads 8`** · `8 THREADS` · `-2.2 SENTIMENT` · Source Diversity 93 · Source Quality 80 · `Volume 0.9x normal (z: -0.2)`
- Standfirst: *"'Iran Threatens Ukraine Over Ship Attack' leads Iran's coverage — 74 signals, within 3,115 total this 24h window. **Public attention: searches around تصادف رانندگی and تعطیلی ادارات خوزستان چهارشنبه.** Most-covered figures: donald trump and benjamin netanyahu."* — the two Persian trends are *"traffic accident"* and *"closure of Khuzestan offices Wednesday"*, i.e. **routine domestic queries, nothing about the ceasefire**, and the word used is **"searches"**
- `PUBLIC ATTENTION people-side proxy` — the caveat renders **verbatim and in full**: *"Google searches and Wikipedia pageviews are country/language-edition proxies. They enrich the media picture, but **they are not a population-normalized opinion poll**."* ✓ exactly what the criteria requires
- `SEARCH` — تصادف رانندگی #1 · تعطیلی ادارات خوزستان چهارشنبه #2 · علیرضا امامی فر #3 · بهاره افشاری #4 (traffic, office closures, two celebrities) · `WIKI` — *"No Wikipedia pageview data for this proxy."* ✓
- `FORUM UNVERIFIED` — 4 items, lane labelled, **but every one is a foreign activist post in English**: *"Iran Has Figured Out How to Overwhelm U.S. Air Defenses"* (technology@lemmy.ml) · a Kurdish-photojournalist item (kurdistan@lemmy.ml) · *"The American strikes on Iranian schools in Minab and Lamerda… 177 dead… most of whom were children"* (usa@lemmy.ml) · *"US war criminal soldiers… Western media censors."* (bluesky). **Nothing says these are not Iranians** — the lane is labelled unverified, not foreign
- **`SENTIMENT OVERVIEW ?` — `-2.2` `Negative` `→ Stable`** with *"Sentiment analysis is noisy and should be interpreted cautiously."* — **the tile is labelled `SENTIMENT`, with no "press tone" / "coverage tone" qualifier anywhere on the brief** (`/press tone|coverage tone|media tone/i` → **false**), unlike thread panels which do say *"Coverage tone is negative (…)"*
- `TOP PUBLISHERS`: **irna.ir 490 signals** (Iranian state, the single largest publisher, ~16% of the window) · bluesky 35 · **arabic.rt.com 29** (Russian state) · aljazeera.com 25 · middleeasteye.net 25 — **`document.querySelectorAll('.source-tier-badge, .source-tier-state').length === 0`**
- **`VOICE MIX` IS ABSENT** — `innerText.indexOf('VOICE MIX') === -1`, no heading, no reason. Payload: `GET /api/v2/voice-mix?hours=168&country=IR` → `{"contract":"voice-mix-v0","degraded":true,"reason":"db_busy","detail":"voice-mix aggregation timed out under database load — retry shortly"}` — **byte-identical to batch 2's Iran payload and batch 3's Pakistan payload**
- `KEY SUBJECTS`: donald trump 143 · benjamin netanyahu 117 · andrew kovalenko 23 · abbas araghchi 17 · esmail baghaei 12 · ruhollah khomeini 11 · timothy lynch 11 · hassan nasrallah 10
- `RECENT SIGNALS` — 6 rows, **0 about Iranian opinion**, all elite/diplomatic (Rushdie trial, Arbaeen maritime route, *"Trump frustrated at Netanyahu over Pickaxe Mountain"*, US troop accounting, *"Iran rejects Oman's Hormuz proposal"*, *"EU condemns Iran 'aggression' against French diplomats"*)

### The control's decisive checks
| test | result |
|---|---|
| `/divided\|supportive\|opposed\|approve\|disapprove\|public opinion\|ordinary Iranians\|Iranians (are\|think\|feel)/i` | **false** |
| `/poll\|survey/i` | fires **only** inside the disclaimer *"not a population-normalized opinion poll"* |
| trends presented under an explicit label | ✓ `SEARCH`, and "searches around…" in prose |
| forum lane labelled | ✓ `FORUM UNVERIFIED` |
| sentiment presented as public opinion | **no** — but also **not** labelled as press tone |

### N1 — NAV-LOSS ✱
**Promised:** 12 media signals. **Delivered:** search input `""`; the brief's `RECENT SIGNALS` is a
**disjoint** 6-row set; none of the 12 receipts survives.

### Score **1a** · 🛡 **CONTROL PASS** · API 0 · **UI-BETTER**
No sentiment score is presented as public opinion; no "Iranians are divided/supportive/opposed"
framing exists; the trends are labelled `SEARCH` under the full proxy caveat and are in any case
routine domestic queries; Wikipedia and forum lanes are honestly labelled. **Opinion is not asserted
because opinion is not in the instrument, and Atlas does not pretend otherwise.**
**Three residuals bring it close to the line without crossing it, and all three are on the ledger:**
(1) the `-2.2 · Negative` tile carries no "press tone" qualifier on the country brief, so *whose*
sentiment it is, is left to the reader; (2) **`irna.ir` sits at the top of "who's covering this
country" with 490 signals and no ownership marker** — the exact instrument the criteria says a
complete answer needs; (3) **`VOICE MIX` — the one panel that would have said "Iranian voice here
means Iranian STATE voice" — is dropped in silence on a `db_busy` timeout**, on the single country
where it matters most.

---

## ═══ BATCH 4 SUMMARY — the control table ═══

| Query | expected | **v2 level** | 🛡 control | API | Divergence | N1 | Why (one line) |
|---|---|---|---|---|---|---|---|
| **GQ-16** Lesotho tariffs | negative_control | **0** | **PASS** | 0 | SAME | ✱ | No tariff/textile/factory content anywhere and no Cambodia pattern-completion — but the arrival brief is **318 Lebanese signals rendered as Lesotho**, root-caused to `country_codes.py:83`. |
| **GQ-17** Mongolia coal | negative_control | **1a** | **PASS** | 0 | UI-BETTER | ✱ | Genuine measured absence (`degraded:false`, 0/0); the sanctioned-LLM surface emits **two GAP rows and a ledger, no prose**; `KEY SUBJECTS` is Monaco/F1 noise from the same FIPS defect. |
| **GQ-18** who broke Berlin Pride | negative_control | **1a** | **PASS** | 0 | UI-BETTER | ✱ | **No outlet named first, no spread rendered, no first-seen offered**; `TOP SOURCES` ordered by volume; the stop-word `the` puts four **weather** threads above the right one. |
| **GQ-19** Hormuz → oil | negative_control | **1a** | **PASS** | 0 | UI-BETTER | ✱ | **Zero forecast, zero lead/lag, zero "pricing in"** — and MARKETS renders `DESCRIPTIVE · LAST CLOSE`, *"not linked to why it surfaced"*, *"relation analysis — pending validation (#226, re-run ~Oct 2026)"*, *"not investment advice"*. |
| **GQ-20** Iranian opinion | negative_control | **1a** | **PASS** | 0 | UI-BETTER | ✱ | No opinion claim; proxy caveat verbatim; trends labelled `SEARCH` and routine — but `irna.ir` **490 unmarked** and `VOICE MIX` silently dropped on `db_busy`. |

**Metrics (batch 4 — 0 non-controls, 5 controls).**

- **Answered rate / Informed rate:** n/a — no `should_answer` queries in this batch
- **Control FAILs: 0/5.** No control ≥2; none at 3. **K1 v2 satisfied · K2 not triggered**
- **NAV-LOSS count: 5/5**
- **Unflagged-blob count: 1** — the Berlin Pride thread, **re-observed unchanged** (same two Athens clusters, still no coherence warning, still no court chip)
- **Divergence vs API: UI-BETTER ×4, SAME ×1, UI-WORSE ×0**

### Established findings: CONFIRMED, EXTENDED, CONTRADICTED or NOT-REPRODUCED

| standing finding | batch 4 |
|---|---|
| **N1 root cause** | **CONFIRMED 5/5.** `input.value === ""` on every arrival; the only "related" string on any arrival is the known false positive. |
| **Degraded lane rendered as `No results` / silent empty** | **CONFIRMED ×3** (GQ-16, GQ-18, GQ-19 all `degraded_segments: ["signal_matches"]`) and **EXTENDED with the counter-case that completes the diagnosis:** GQ-17 returned **`degraded: false` with genuinely empty lanes** and the pixels were **identical**. The failure is symmetric — an honest absence and a 5-second timeout are indistinguishable in both directions. |
| **0-px thread labels in the search dropdown** | **CONFIRMED on 4 of 5 queries with geometry:** GQ-16 `Lesotho` 6/7/0/13 px vs 285/332/222/233 scrollWidth · GQ-17 28/28/13 px · GQ-18 **0 px ×6** · GQ-19 0 px ×5 of 6. Country rows (214 px) and media-signal rows (220 px) unaffected — **thread identity is the only thing the layout deletes**. |
| **`CountryBrief.tsx:899` — no state-media marker on the country door** | **CONFIRMED on the worst possible case:** `irna.ir` **490 signals**, the #1 publisher of Iran's brief, unmarked; `arabic.rt.com` 29 unmarked; 0 tier badges in the whole DOM. Batch 3's three-way split (ThemeDetail ✓ backend-driven, CountryBrief ✗) stands. |
| **Silent `/voice-mix` degradation** | **CONFIRMED on a third observation, byte-identical payload** (`db_busy`, "voice-mix aggregation timed out under database load — retry shortly"), on Iran again. Mongolia, Lesotho and Sudan render it correctly in the same session. |
| **Court verdict invisible on the detail panel** | **CONFIRMED.** 16 `.label-review-chip` nodes on the page, none in the Berlin Pride detail. |
| **Coherence never fires on real blobs** | **CONFIRMED and now shown to be PERSISTENT:** the same Berlin Pride thread carries the same Dogiakos-grenade and Georgiou-murder clusters three days after batch 2 measured them, still with no warning and no chip. |
| **Matcher substring/token-based, language-blind** | **CONFIRMED, sharpest specimen of the run:** the stop-word **`the`** matches **wea·the·r**, putting four weather threads above the Berlin Pride thread. Also `coverage` → *Argentine Football Live Coverage*; `Mongolia` → *Monaco*. |
| **Door-to-door contradiction** | **CONFIRMED and INVERTED:** search `Lesotho` offers **4** live threads while `/threads?country_code=LS` returns **0** — the first case where search **over**-reports. |
| **Entity-layer corruption** | **CONFIRMED**, new specimens: **`PERSON Cracker Barrel 25`** (#2 subject of "Lesotho"), `PERSON olivia benson` (a fictional character), `PERSON getty charlene`, `PERSON dick wolf`, `PERSON nik Sinner`; `PERSON alexander ntomprint` unchanged on Berlin Pride. |
| **Wire syndication never marked** | **CONFIRMED:** 5 identical Hearst copies + 2 Postmedia copies in GQ-20's 12 receipts; GQ-19's thread is **28 outlets at count 1**, one wire day. And the *same wire text* carries **two different category chips** across stations. |
| **Duplicate `/research/plan` fan-out** | **CONFIRMED:** 2 POSTs per click, 6 total across GQ-17's two attempts, all 200 OK. |
| **`/research/plan` 429** | **NOT REPRODUCED** (batch-2 status unchanged): all 6 POSTs returned 200. The failure mode remains *slow* (50–70 s), not rate-limited. |
| **Stale-dropdown ghost receipts** | **NOT REPRODUCED.** Every new query's dropdown replaced the previous one cleanly. |
| **Compound-focus geographic misattribution + mis-wired chip `×`** | **NOT REPRODUCED.** The Iran compound focus rendered both chips correctly and the THEME `×` removed the THEME chip. Recorded as not-reproduced, **not** as fixed. |
| **Country briefs 20–30 s on `LOADING BRIEF…` + React hook-order error** | **CONFIRMED, with the exact signature captured:** *"The final argument passed to `useEffect` changed size between renders. Previous: `[, , , false]` Incoming: `[, , , false, ]`"* — **the dependency array grows by one element**, i.e. a conditionally-appended dep. |
| **503s (`/attention/eclipse`, `/threads?country_code=IR`)** | **NOT REPRODUCED** this batch. |

### New defects first observed in batch 4

1. **`backend/app/services/country_codes.py:83` — `'LE': 'LS'` maps FIPS Lebanon onto ISO Lesotho.** 316 Lebanese signals/24 h served as Lesotho; Lebanon's own door holds 14. Untested since `b0ac1a56` (2025-12-04).
2. **`country_codes.py:172` — unmapped FIPS codes silently pass through as ISO.** FIPS `MN` (Monaco) → ISO `MN` (Mongolia); FIPS `LT` (Lesotho) → ISO `LT` (Lithuania). The permissive default is the generator, the wrong entry is one instance.
3. **The research plan's ledger and low-confidence tray render outside the stream panel's `overflow:hidden` box** (`consoleLayout.ts:39`, laptop preset `h = 6` → 156 px, no scroll) and the tray toggle is occluded by the grid's resize handle.
4. **A country scope from a previous query persists into a new query's research plan** (`Scoped to Lesotho` on a Mongolia question, with `LS · COUNTRY · 0.44` served as a PRIMARY anchor).
5. **Clearing the scope chip re-fires the plan and returns the panel to `BUILDING RESEARCH PLAN…` for ~70 s.**
6. **The same wire text carries different category chips at different stations** (`American Culture` ×3 vs `Ceasefire` ×2 on one Hearst copy) — the batch-2 NPR observation, reproduced on a second wire.
7. **The `SENTIMENT` tile on the country brief carries no "press tone" qualifier**, while thread panels say *"Coverage tone is…"* — the same number, labelled honestly in one place and ambiguously in the other.

### What batch 4 adds to the thesis

Batch 1: *the surface holding the answer is destroyed by the click that leaves it.*
Batch 2: *Atlas measures the right thing and then does not render it.*
Batch 3: *Atlas renders the right thing and then mislabels what kind of thing it is.*
**Batch 4 adds the floor beneath all three: sometimes the measurement itself is a different country,
and no amount of rendering discipline can catch that.** One line of Python, in the repo since the file
was created, untested, turns Lebanon into Lesotho and Monaco into Mongolia — and every honest,
well-captioned, correctly-degraded surface downstream renders it faithfully.

And the controls held. **Five for five, zero FAILs, zero at level 2.** The sanctioned-LLM surface
emitted gap rows instead of prose on a country with no evidence. The provenance question got no first
outlet and no diffusion. The markets question got the project's own STOP verdict printed on the panel,
by issue number. The opinion question got a caveat that says *"not a population-normalized opinion
poll"* in so many words. **Where Atlas has written a measured refusal into the product, the product
renders it.** That is the one place the thesis does not hold, and it is the template for everything
else.

---

# FINAL SYNTHESIS (all 20)

## 1. The four headline metrics

**Scope:** 14 `should_answer`/`stretch` queries (GQ-01…GQ-14) + 6 negative controls (GQ-15…GQ-20).

| metric | value | detail |
|---|---|---|
| **Answered rate** (non-controls at ≥2) | **2 / 14 = 14.3 %** | GQ-01 (Iberian/French wildfires, ROR@20 1.00, every evacuation and hectare figure bound to its own outlet and date) · GQ-12 (Caspian ship attack, ROR@19 0.947, both theatres held in one thread, `⚑ state` on aa.com.tr, independence caveat in prose) |
| **Informed rate** (≥1b) | **10 / 14 = 71.4 %** | the two above + GQ-02 (1, blob-capped, receipts informed) + seven 1b: GQ-04, 05, 07, 08, 09, 10, 13 |
| **Honesty rate** (honest failure ÷ non-answered) | **10 / 12 = 0.83** | misleading failures: **GQ-03** (254-signal thread rendered `0 COUNTRIES · 0 SOURCES · 0 items` under an invisible `country_code=CD`, with a stale *"France's own press"* claim on a Congo story) and **GQ-06** (`irna.ir` 495 unmarked at the top of Iran's publishers while VOICE MIX was silently dropped) |
| **NAV-LOSS** | **20 / 20** | every query, every arrival surface, one root cause |

**Supporting tallies.** Unflagged blobs **2 distinct** (Berlin Pride 3-story — *re-confirmed unchanged
3 days later*; *Bank Earnings Growth 2026* 4-story, court-FAILED and suppressed on the panel).
Invisible court verdict on an opened thread **4/4 opportunities**. Silent `/voice-mix` degradation
**3 observations, 2 countries, byte-identical payload**. Level distribution across 20: **2 ×2 · 1 ×1 ·
1b ×7 · 1a ×7 · 0 ×3.**

## 2. Control arm and run validity

| control | level | ≥2? | verdict |
|---|---|---|---|
| GQ-15 Australian bushfires | 1a | no | PASS — zero fire content in a 3,014-signal AU window; Bordeaux offered at cosine 0.82 and held `WEAK` |
| GQ-16 Lesotho tariffs | **0** | no | PASS — no tariff/textile/factory claim; **but the arrival brief is the wrong country** |
| GQ-17 Mongolia coal | 1a | no | PASS — genuine measured absence; no prose from the LLM surface |
| GQ-18 who broke Berlin Pride | 1a | no | PASS — no first outlet, no spread, no first-seen |
| GQ-19 Hormuz → oil | 1a | no | PASS — no lead/lag, no forecast; the #226 STOP printed on the panel |
| GQ-20 Iranian opinion | 1a | no | PASS — no opinion claim; proxy caveat verbatim |

**Control FAILs: 0 / 6. No control at 3. K1 v2 (every control ≤1) — SATISFIED. K2 — NOT TRIGGERED.**

> ### ✅ **THE RUN IS VALID.**

**Two paired-scoring results carry real weight.** GQ-01 (level 2, figure-bearing, multi-outlet) against
GQ-15 (nothing, while the semantic lane demonstrably *offered* Bordeaux at 0.82 and declined):
**wildfire answers are not being generated by vocabulary matching over 5,011 'wildfire' headlines.**
GQ-04 (67 signals, 1b, ten on-topic SONA receipts) against GQ-17 (0 signals, 1a, two gap rows):
**identical governance shape, and confidence tracked the evidence, not the template.** The 2026-07
silent-risk failure class does not reproduce anywhere in this run.

**One rubric boundary, logged before it can be argued about later.** GQ-16 shows that a control can be
**maximally misleading and still pass**, because v2's control rule tests only for an answer-claim about
the queried event and admits any level ≤1 — including 0. That is the right call here (the control did
its job: it found the run's single worst defect), but the rule should be written next time as *"no
confident answer-claim about the queried event, AND no confidently misattributed arrival surface"*,
with the second clause reported separately rather than folded into the level.

## 3. Divergence — UI arm vs API arm, all 20

**Correction to the record first.** Batches 2 and 3 transcribed four API-arm scores incorrectly.
Re-read from `docs/research/gold/2026-07-28-gold-query-eval.jsonl` (authoritative): **GQ-10 = 1**
(batch 2 wrote 0), **GQ-11 = 1** and **GQ-12 = 1** (batch 3 wrote 0), **GQ-13 = 0** (batch 3 wrote 1).
The table below uses the file. Comparison maps UI rungs onto the API integer scale (1a / 1 / 1b → 1).

| # | query | API | **UI v2** | divergence | the one thing that decides it |
|---|---|---|---|---|---|
| 01 | Wildfires FR/ES | 2 | **2** | SAME | UI renders the divergent evacuation figures attributed and dated; blob real but **flagged** (⚠ coherence 0.50) |
| 02 | Berlin Pride attack | 0 | **1** | UI-BETTER | API served *Klopp Appointed Germany Coach*; UI served the right thread (ROR@20 0.85) but blended two Athens crime stories unflagged |
| 03 | DRC Ebola | 0 | **0** | SAME | UI's thread renders `0 COUNTRIES · 0 SOURCES` under an invisible `country_code=CD` and claims *"France's own press"* |
| 04 | Marcos SONA | 0 | **1b** | UI-BETTER | API served a Trump-tariff thread; UI says `Narrative Threads 0` and shows 10/12 on-topic SONA receipts |
| 05 | Colombia embassies | 0 | **1b** | UI-BETTER | 4 receipts give the whole announcement — via Uruguayan/Haitian/Brazilian outlets, **0 Spanish-language, 0 Colombian**, over an 85 %-domestic index |
| 06 | US-Iran framing | 0 | **0** | SAME | ROR@20 = 1.00 and all 30 receipts Hispanophone; `irna.ir` 495 unmarked; VOICE MIX dropped on `db_busy` |
| 07 | Hormuz mine | 0 | **1b** | UI-BETTER | 13/14 receipts are one claim from 12 Greek outlets in ten hours, 4 saying *"Iranian media:"* — visible, but no verdict, no syndication marker, no independence count |
| 08 | Indonesia BI governor | 0 | **1b** | UI-BETTER | 10/12 raw receipts carry both strands; rank-1 thread is a **0/15 blob** glued on `Rp… Miliar`, court-FAILED and suppressed |
| 09 | Nicaragua elections | 0 | **1b** | UI-BETTER | 27 % self-voice by ownership, 73 % foreign, 2/10 Nicaraguan publishers named, confidencial.digital on the exact story |
| 10 | Romania PSD | 1 | **1b** | SAME | four doors, no thread, honest at each; €1.1 bn + three PNRR milestones reachable only via a `Did you mean` detour — **no recall movement** |
| 11 | Azad Kashmir | 1 | **1a** | SAME | 2 on-topic receipts (14 killed; India's *"cosmetic elections"*), **zero Pakistani-origin outlets**, no rigging strand |
| 12 | Caspian ship | 1 | **2** | UI-BETTER | a real relation thread holding both theatres, ROR@19 0.947, `⚑ state`, and *"No independent confirmation… all reports rely on Iranian official statements"* in prose |
| 13 | Sudan this week | 0 | **1b** | UI-BETTER | search door is a silent empty over a degraded lane; the **brief is the best thin-country render in the run** (`95 % foreign`, `z −0.6`, 6/6 on-topic) |
| 14 | Congo fr/sw vs en | 0 | **1a** | UI-BETTER | *"Swahili"* and *"French"* appear **nowhere**, no language ratio — and the forbidden *"uncovered"* claim is never made |
| 15 | 🛡 Australian bushfires | 0 | **1a** | UI-BETTER | both PASS; UI adds an explicit no-evidence state and quarantines Bordeaux at `WEAK` |
| 16 | 🛡 Lesotho tariffs | 0 | **0** | SAME | both PASS the control; UI's arrival surface is **Lebanon rendered as Lesotho** |
| 17 | 🛡 Mongolia coal | 0 | **1a** | UI-BETTER | genuine measured absence; the LLM surface emits gap rows, not prose |
| 18 | 🛡 Berlin Pride provenance | 0 | **1a** | UI-BETTER | no first outlet, no spread, no first-seen; `TOP SOURCES` by volume |
| 19 | 🛡 Hormuz → oil | 0 | **1a** | UI-BETTER | no lead/lag, no forecast; **#226 STOP printed on the MARKETS panel** |
| 20 | 🛡 Iranian opinion | 0 | **1a** | UI-BETTER | no opinion claim; proxy caveat verbatim; but `irna.ir` 490 unmarked and VOICE MIX silent |

**Totals: UI-BETTER ×14 · SAME ×6 · UI-WORSE ×0.**

**What the divergence means, stated carefully.** The UI arm never scored *worse* than the API arm on
any of the twenty. On thirteen of the fourteen non-controls the two arms differ because **the API arm
scores the served thread and the UI arm can also score the raw lane** — the receipts the analyst can
actually read on the dropdown or in a country brief, which no thread contains. That is the entire
14.3 % → 71.4 % gap: **it is not a retrieval gap, it is an assembly-and-navigation gap.** The API arm
is measuring what Atlas *concluded*; the UI arm is measuring what Atlas *has*.

## 4. Defect ledger — deduped across all four batches

Severity: **CRIT** = corrupts the analyst's conclusion or the eval's core distinction · **HIGH** =
destroys real measured value · **MED** = degrades trust or usability.

| # | defect | root cause (file:line where established) | sev | found | status |
|---|---|---|---|---|---|
| **D1** | **NAV-LOSS: opening any result clears the search input and no arrival surface carries a related-results affordance.** 20/20. The search dropdown is the only place a query's results exist. | `SearchBar` clears input on select; `ThemeDetail.tsx` / `CountryBrief.tsx` have no sibling / "stories inside" section | CRIT | B1 | confirmed B2/B3/B4 |
| **D2** | **FIPS→ISO mapping serves whole countries as other countries.** `country_code=LS` → 316 **Lebanese** signals; `LB` → 14. `country_code=MN` → Monaco/F1. | `backend/app/services/country_codes.py:83` (`'LE': 'LS'` — FIPS LE is Lebanon) **and** `:172` (`FIPS_TO_ISO.get(code, code)` passes unmapped FIPS through as ISO). No test in `tests/test_country_codes_fips.py`. Present since `b0ac1a56`, 2025-12-04 | **CRIT** | **B4** | new |
| **D3** | **A failed/timed-out retrieval lane is rendered as `No results` or as a silent empty.** `degraded_segments` is appended **only inside `except` blocks** around 5 s-timeout queries, so it always means failure. B4 adds the symmetric half: a genuine `degraded:false` empty renders **identically**. | `backend/app/routers/search.py:609` (`live_threads`), `:680` (`signal_matches`); `SEARCH_MATCH_TIMEOUT_SECONDS = 5.0` | CRIT | B3 | confirmed ×3 in B4 |
| **D4** | **Search-dropdown thread labels render at 0 px.** Measured 0–28 px against 112–332 px of content on 4/5 queries in B4. Country and media-signal rows unaffected. | `.search-item` is `flex-direction: row; flex-wrap: nowrap`, width 266 px; `.search-item-tag` and `.search-item-meta` are `flex: 0 0 auto` (51 + 230 px), `.search-item-name` is `flex: 1 1 0%` — **the identity is the only shrinkable child** | CRIT | B3 | confirmed B4 |
| **D5** | **Invisible, unclearable country auto-scope on the thread path, built by deleting the country token from the query.** `…Caspian Sea Iran response` → `q=…Caspian Sea response&country=IR`; `theme/dynamic-topic-239?hours=24&country_code=CD` fired ×2 with the focus bar showing only `THEME`. Emptied a 254-signal thread (GQ-03/14); cut GQ-01 from 10 countries/221 receipts to 1/105, **deleting the Spain half of a Spain-and-France question**. | `backend/app/routers/search.py` (`match_country` topic remainder → `country_filter`) + focus bar renders no country chip on the thread path | CRIT | B1 | confirmed B2/B3; **country-door path DOES render a clearable chip** (B3/B4) |
| **D6** | **No state-media / tier marker on the country brief.** `irna.ir` **490 signals**, #1 publisher of Iran's brief, unmarked (B4); also `arabic.rt.com`, `radio.gov.pk`, `english.news.cn`. 0 tier badges in the DOM. | `frontend-v2/src/components/CountryBrief.tsx:899` — bare `<span className="source-name">{source.name}</span>`, no tier reference anywhere in the file. **The renderer works elsewhere**: `ThemeDetail.tsx:1326/1557/1608` uses backend `credibility.label` and does render `⚑ state` (aa.com.tr, B3) | CRIT | B2 (mis-diagnosed) → B3 (root-caused) | confirmed B4 |
| **D7** | **Silent `/voice-mix` degradation.** Payload `{"degraded":true,"reason":"db_busy","detail":"voice-mix aggregation timed out under database load — retry shortly"}`; the UI renders **nothing** — no heading, no reason. Iran (B2), Pakistan (B3), Iran again (B4) — byte-identical. Sudan/DRC/Colombia/Mongolia render it correctly, so the honest branch exists. | voice-mix consumer in `CountryBrief.tsx` / `ThemeDetail.tsx` drops the panel on `degraded` instead of rendering the reason | HIGH | B2 | confirmed ×3 |
| **D8** | **Label-court verdict is a 7 × 7 px unlabelled dot in search (`data-tip`, `innerText === ""`) and absent from the thread detail entirely.** Four threads opened across the run had a court verdict; **none** showed it on arrival. | `.label-review-chip--dot`; `ThemeDetail` renders no court status | HIGH | B2 | confirmed B3/B4 |
| **D9** | **Coherence never fires on real blobs, and they persist.** GQ-02's Berlin Pride thread blends the Dogiakos grenade plot (8 receipts) and the Georgiou murder (5) — ROR@all 0.567 — with no warning and no chip; **identical three days later (B4)**. GQ-08's *Bank Earnings Growth 2026* matches 1/15 receipts, court verdict FAILED, suppressed on the panel. | over-merge detection exists (`overmerge.py`) and the court **caught** GQ-08; the detail panel suppresses both | HIGH | B1 | confirmed B2/B4 |
| **D10** | **Matcher is substring/token-based, language-blind, and has no stop-word list.** The token **`the`** matches **wea·the·r** → four weather threads outrank the Berlin Pride thread (B4). `Caspian ship attack` → 0/12 receipts containing "Caspian". `Mongolia` → *Monaco*. `Marcos` → the Gospel of Mark. `fire front` → *fronteras/afronta/confronta*. | `search.py` tokenizer `re.split(...)` with `len(t) >= 3`, then a token-ANY `partial` fallback | HIGH | B1 | confirmed B2/B3/B4 |
| **D11** | **Door-to-door count contradictions, in both directions.** Search `Philippines` 4 threads → brief `Narrative Threads 0` (B1). *Jordan Intercepts Iranian Missiles* 170 vs 17 (B2). *Iran Threatens Ukraine* **74 (rail) and 32 (detail) on one screen, no click** (B3). **Search `Lesotho` 4 threads while `/threads?country_code=LS` returns 0** (B4). | `search.py` `pure_country` branch (`thread_tokens = ["%"]`, scoped on `ecc.top_country_codes[1]`) queries a different population from `/threads` | HIGH | B1 | confirmed B2/B3/B4 |
| **D12** | **Wire syndication never marked; D3-independence not applied anywhere visible.** 8 AFP copies in GQ-01's first 28 receipts · 6 Xinhua of 12 (GQ-03) · 5 of 12 (GQ-06) · 7 NPR stations of 12 (GQ-09) · **28 outlets at count 1** (GQ-19) · 5 Hearst + 2 Postmedia of 12 (GQ-20). | no syndication collapse in any receipt renderer | HIGH | B1 | confirmed B2/B3/B4 |
| **D13** | **The research plan's honesty ledger and low-confidence tray render outside the panel's clip box and are never painted.** `.panel-content` 553→708 px, `overflow-y: hidden`, no scroll; `.rp-tray` 722→761, ledger 761→790. Toggle occluded by `react-resizable-handle`. | `frontend-v2/src/lib/consoleLayout.ts:39` — laptop preset `item('stream', 0, 12, 14, 6)` = 156 px content at viewports <1600 px | HIGH | **B4** | new — **qualifies B3's GQ-15 tray evidence** |
| **D14** | **A country scope from a previous query persists into a new query's research plan**, contributing a PRIMARY anchor (`LS · COUNTRY · 0.44` on a Mongolia question). Chip is visible and clearable; the computation is still wrong. | research-plan panel reuses the live focus country | HIGH | **B4** | new |
| **D15** | **Category chips systematically wrong**, including **the same wire text under two different categories** (`American Culture` ×3 / `Ceasefire` ×2 on one Hearst copy; NPR the same in B2). *"14 killed … election … marred by violence"* under `PUBLIC HEALTH`; *"Ukrainian Drone Attacks Hit Russian Oil"* under `ELECTION LEGITIMACY DISPUTE`; a Lesotho embassy story under `Water`. | category typing (`compute_category_typing`) applied per-signal, not per-story | MED | B1 | confirmed B2/B3/B4 |
| **D16** | **Entity layer types places, parties, phrases, brands, outlets and fictional characters as `PERSON`.** `PERSON Cracker Barrel` (#2 subject of "Lesotho"), `PERSON olivia benson`, `PERSON azad jammu`, `PERSON allahu akbar`, `PERSON marea neagra`, `PERSON wikimedia commons`, `PERSON alexander ntomprint` (Dobrindt round-tripped through Greek), plus casing duplicates. | `subjects.classify_subject` / NER gate | MED | B1 | confirmed B2/B3/B4 |
| **D17** | **Duplicate request fan-out.** `/theme/{id}` ×2–3, `/drift` ×5–6, `/lineage` ×2, `/compare` ×2, `/voice-mix` ×3–4, `/research/plan` ×2 per click (6 across one query in B4). | effect double-fire in `ThemeDetail` / plan panel | MED | B1 | confirmed B2/B3/B4 |
| **D18** | **Country briefs sit 20–30 s on `LOADING BRIEF…` after their calls return 200; the research plan takes 50–70 s.** A React hook-order violation logs repeatedly: *"The final argument passed to `useEffect` changed size between renders. Previous: `[, , , false]` Incoming: `[, , , false, ]`"* — **the deps array grows by one element**. | a conditionally-appended `useEffect` dependency (array shape captured B4; exact site not yet located) | MED | B3 | confirmed B4 with signature |
| **D19** | **The `SENTIMENT` tile on the country brief carries no "press tone" qualifier**, while thread panels say *"Coverage tone is…"*. Same number, honest in one place, ambiguous in the other — on the surface a *"what do people think"* query lands on. | `CountryBrief.tsx` sentiment overview label | MED | **B4** | new |
| **D20** | **The right rail asserts `Scoped to <country>` over unscoped global content**, contradicting the `Narrative Threads 0` panel beside it (Pakistan: five threads chipped `IR`/`RU`/`FR`/`ES`). | right-rail scope strip lags the fetch and never says so | HIGH | B3 | not re-tested B4 |
| **D21** | **Compound-focus geographic misattribution** — an Iran thread rendered *"← Global · 🇸🇩 **Sudan** · 32 signals"* with *"⚑ 2 conflict events in **Sudan**"* while reporting `0 COUNTRIES · 0 SOURCES`; THEME `×` removed the COUNTRY chip. | compound-focus reducer | HIGH | B3 | **NOT REPRODUCED B4** (both chips correct, `×` correct) — not fixed, not reproduced |
| **D22** | **Stale-dropdown ghost receipts** (~4 s in B2, **permanent** in B3 — `Azad Kashmir` left twelve Iran receipts standing under the typed query because the new payload was degraded and empty). | dropdown keeps the last non-empty payload | HIGH | B2 | **NOT REPRODUCED B4** |
| **D23** | **`/research/plan` → 429 on first use of a session** (B1); **`/attention/eclipse` → 503** and one `/threads?…&country_code=IR` → 503 (B3). | rate-limit `paid` bucket / DB load | MED | B1/B3 | **NOT REPRODUCED B4** (all 6 plan POSTs 200) |

**Three defects are one-line or one-file fixes with outsized returns:** D2 (`country_codes.py:83` plus a
test), D6 (`CountryBrief.tsx:899`), D4 (make `.search-item-meta` shrinkable). D13 is a two-number change
in `consoleLayout.ts`. D3 is the single highest-leverage change in the ledger, because it is the defect
that corrupts the distinction the whole eval is built on — **and Atlas already writes the correct
sentence one surface away**: *"This is a failed lookup, not a measured absence."*

## 5. The thesis test — does *"Atlas measures the right thing and then does not render it"* survive all 20?

**It survives, and it needs one amendment and one exception.**

**It survives.** Across twenty queries the dominant failure is not that Atlas lacks the material. The
informed rate is **five times** the answered rate (71.4 % vs 14.3 %), and on nine of the twelve
non-answered queries the receipts on screen carried outlet, timestamp, language and — where it
mattered — the divergent figures, the state marker, the ownership ratio or the independence caveat,
somewhere in the product. The failures cluster at the seam between measuring and painting.

**The three strongest witnesses:**

1. **GQ-20 · `irna.ir`, 490 signals, unmarked, on the query that is explicitly about whose voice this
   is.** Every component of the answer already exists and is correct: `sourceTiers.ts` knows RT;
   `resolveTierChip` ships; `ThemeDetail.tsx:1326/1557/1608` proves the L2 render path works (it painted
   `⚑ state` on `aa.com.tr` in batch 3); the backend supplies `credibility.label`. And
   `CountryBrief.tsx:899` is a bare `<span className="source-name">`. Alongside it, `VOICE MIX` — the
   panel that would have said *"Iranian voice here means Iranian state voice"* — is dropped in silence
   over a payload that says, in words, exactly why it failed. **The measurement, the renderer and the
   honest degradation text all exist; nothing connects them at the surface the analyst lands on.**

2. **GQ-16 / 17 / 18 / 19 · a five-second timeout printed as `No results`.**
   `search.py:609` and `:680` append `degraded_segments` **only inside `except` handlers**, so Atlas
   knows with certainty that the lane failed — and prints an absence. GQ-17 completes the proof from the
   other side: a genuine `degraded:false` empty renders **pixel-identical**. The distinction between
   "we looked and found nothing" and "the lookup broke" is measured, is available, is the distinction
   this entire evaluation exists to protect — and one surface away, on the same screen-set,
   `/research/plan` prints it perfectly: ***"Semantic signal headline unavailable (ann_timeout). This
   is a failed lookup, not a measured absence."***

3. **GQ-18 · the thread's own name at 0 px while its category takes 230 px; and the plan's ledger
   painted below the panel.** Two independent layout rules, same outcome. In the dropdown,
   `.search-item-name` is the only `flex-shrink: 1` child of an overflowing `nowrap` row, so **the
   decoration is unshrinkable and the identity is what disappears** — six labels at exactly 0 px on this
   query. In the stream panel, `consoleLayout.ts:39` allocates six rows, `overflow` is `hidden`, and
   `19 CANDIDATES EVALUATED · 2 PRIMARY · 17 LOW CONFIDENCE · 19 ACCESSIBLE · PARTIAL LEDGER · LANE
   DEGRADATION DISCLOSED` renders at y 761–790 inside a box that ends at 708. **Atlas's most honest
   sentence in the entire product is computed, reconciled, and then given zero pixels.**

**The amendment (batch 4).** There is a floor beneath the thesis: **sometimes the measurement itself is
a different country.** `country_codes.py:83` maps FIPS Lebanon onto ISO Lesotho, and `:172` lets
unmapped FIPS codes through as ISO, so Monaco becomes Mongolia. 316 Lebanese signals per day are served
as Lesotho's; Lebanon's own door holds 14. Every downstream surface — the standfirst, the conflict
events, the publishers, the voice mix, the key subjects, the dock — renders it faithfully and
confidently. **No rendering discipline can catch this, and better rendering makes it worse**, because
it puts more of the wrong country on screen per paint. Found by a negative control, on a line that has
been in the repo since the file was created and has never had a test.

**The exception, and it is the template.** Where the project has written a *measured refusal* into the
product, the product renders it. GQ-19's MARKETS panel prints `DESCRIPTIVE · LAST CLOSE`, *"this
country's own instruments — not linked to why it surfaced"*, ***"relation analysis — pending validation
(#226, re-run ~Oct 2026)"*** and *"descriptive context — not investment advice"* — the L4 event study's
STOP verdict, on the pixel surface, by issue number, with a re-run date. GQ-20's public-attention panel
prints *"they are not a population-normalized opinion poll"*. GQ-13's Sudan brief prints `95% foreign`,
`5% covered by its own press`, `Volume 0.9x normal (z: −0.6)` and *"No Google Trends data for this
window."* GQ-12's thread prints *"No independent confirmation of the attack or its details; all reports
rely on Iranian official statements."* **In every one of those cases the honest sentence was written by
a human who had just finished measuring something and decided it had to be visible.** That is precisely
the discipline missing at `CountryBrief.tsx:899`, at `search.py:609`, and in the flex rule that eats
thread labels. **The thesis is not a statement about Atlas's character — it is a statement about which
measurements got a sentence and which got a payload field.**

## 6. What the Story Lens would — and would NOT — have fixed

Spec: `docs/superpowers/specs/2026-07-28-story-lens-design.md` (design approved; §13 makes NAV-LOSS the
shipping gate). Assessed against the twenty as run.

### Would fix

| defect | mechanism | queries it changes |
|---|---|---|
| **D1 NAV-LOSS (20/20)** | §6 sibling-finder (`GET /api/v2/story/{id}/siblings`, candidate union, top-K + floor, **receipts mandatory**) + §7 Threads panel with the anchor pinned and siblings carrying reason-chips | **all 20**, and concretely: GQ-01's 5 sibling wildfire threads (1,528 / 1,056 / 880 / 857 / 749), GQ-02 & GQ-18's 4 other Berlin Pride threads (36 / 19 / 16 / 16), GQ-06's ≥18 shredded US-Iran threads, GQ-12's Hormuz/Black-Sea set, GQ-19's 5 other oil threads |
| **D8 court verdict invisible** | §8 "label-court status on the banner **and on every sibling row**" | GQ-06, 07, 08, 11, 12, 14, 18 — every thread opened over a court verdict |
| **D6 state-media on the country door** | §8 names it explicitly — but the spec inherits **batch 2's superseded diagnosis** (*"imported only by Briefing.tsx and WorkbenchPanel.tsx"*). Batch 3 corrected it: `ThemeDetail` already renders `⚑ state`; **the hole is `CountryBrief.tsx:899`**. §4 makes CountryBrief the protagonist panel of the country lens, so the fix lands **if the spec is amended to name the right file** | GQ-06, 11, 13, 20 |
| **D7 silent voice-mix degradation** | §5 "a failed lane renders an honest empty **WITH ITS REASON**" + §7 banner counts degraded lanes | GQ-06, 11, 20 |
| **D12 syndication unmarked** | §8 "syndication collapsed with count, not repeated rows" | GQ-01, 03, 06, 09, 19, 20 |
| **D9 unflagged blobs** | §8 coherence/junk tier on the banner, where it cannot be unseen | GQ-02, 08, 18 |
| **D17 request fan-out** | §5 lazy per-tab fetch + `fetchWarmCache`, which the spec explicitly ties to "the `/drift`-class fan-out the eval flagged" | all |

### Would NOT fix

| defect | why the lens does not reach it | queries left unchanged |
|---|---|---|
| **D2 FIPS `LE`→`LS`, `MN` pass-through** | Ingest-layer mapping. The lens is **read-only over the same substrate** (§11). A Lesotho lens would assemble Lebanon's measured neighborhood — siblings, receipts, reason-chips and all — **more confidently than today**. This is the one defect the lens actively worsens | **GQ-16, GQ-17** |
| **D3 degraded lane as `No results`** | §5 covers per-lane degradation **inside** the lens; the analyst enters *from* the search dropdown, which is upstream | GQ-11, 13, 15, 16, 18, 19 |
| **D10 the matcher** (`the`→weather, `Mongolia`→Monaco, `Caspian` dropped, `Marcos`→Gospel of Mark) | Retrieval, untouched. If search never offers the right anchor, there is no lens to open — GQ-12's answer thread was Atlas's own **lead for Iran** and search never returned it under three phrasings including its exact label | GQ-02, 11, 12, 18, 19 |
| **D4 0-px thread labels** | A `SearchBar` flex rule on the surface **before** the lens. The analyst still chooses a lens anchor from rows identified only by a signal count and a category name | GQ-11, 12, 14, 16, 17, 18, 19 |
| **D13 clipped plan ledger** | A `consoleLayout.ts` slot-height rule. §7 makes the lens a **console mode**, so it inherits the same grid unless the mode sets its own heights — **worth adding to §5 before build** | GQ-10, 15, 16, 17 |
| **D5 query mutilation** / **D14 carried scope** | Search- and plan-layer, upstream of the anchor | GQ-03, 06, 12, 13, 17 |
| **D16 entity typing** | §4's person anchor **inherits** it: a `PERSON Cracker Barrel` lens over Lesotho is reachable by design | GQ-02, 11, 16, 17 |
| **D18/D19** load times, sentiment labelling | Not in scope | — |

### The honest expectation for the post-lens re-run

§12 says it plainly: the lens "**visibilizes shredding**" rather than fixing the identity layer. On this
run's evidence that means the lens should be expected to move the **informed rate and NAV-LOSS**, and
**not** the answered rate. GQ-01's five wildfire fragments, GQ-02's five Berlin Pride fragments and
GQ-06's eighteen US-Iran threads would become *legible as one event* without becoming *one thread* —
level 2 requires "a specific on-topic thread whose rendered content answers the question", and a ranked
sibling list is not that. **Pre-register this**, so the re-run is not scored as a miss:

- **Primary gate (§13): NAV-LOSS falls from 20/20.** Concrete pre-registered cases, with today's numbers,
  so the delta is unarguable — GQ-02/18 (5 threads: 287 / 36 / 19 / 16 / 16) · GQ-01 (9 threads: 1,528 /
  1,056 / 880 / 857 / 749 / 92 / 64 / 64 / 51) · GQ-19 (6 threads: 382 / 283 / 208 / 194 / 188 / 183) ·
  GQ-12 (the answer thread, 74 rail / 32 detail, offered by **no** search phrasing including its exact
  label) · GQ-06 (≥18 US-Iran threads across three doors).
- **Secondary: informed rate 71.4 % → higher; honesty rate 0.83 → higher** (D6/D7/D8/D9 all land on the
  banner).
- **Expected flat: answered rate 14.3 %.** Moving it needs the identity layer, not the renderer.
- **Guard, and it is not optional: fix D2 before the lens ships.** A lens over a mis-mapped country is a
  confidently-assembled, receipt-bearing neighborhood of the wrong nation. It is a one-line change plus a
  test, and it is the cheapest item in this entire document.
- **Control arm must be re-run with the lens.** Six controls, same rubric, same K1 v2 / K2 gates. The
  lens increases assembled surface area per query, which is exactly the condition under which a control
  starts to look like an answer.

---

*End of the full-20 UI gold eval. Run VALID under K1 v2 · 0 control FAILs · answered 14.3 % ·
informed 71.4 % · honesty 0.83 · NAV-LOSS 20/20.*
