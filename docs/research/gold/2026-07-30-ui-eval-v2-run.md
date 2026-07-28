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

*Batch 4 appends below this line.*
