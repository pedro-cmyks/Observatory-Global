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
