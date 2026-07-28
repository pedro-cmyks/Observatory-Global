# Whitened identity thresholds — measurement (T1)

**Generated:** 2026-07-28T12:47:27.563533+00:00 · read-only · harness `backend/scripts/measure_identity_whitening.py`  
**Plan:** `docs/superpowers/plans/2026-07-28-identity-whitening.md` (T1) · **Diagnosis:** `docs/research/recall-229/2026-07-28-identity-layer-raw-cosine.md`  
**Whitening:** `backend/app/data/e5_whitening.npz` k=1 dim=768 fit_n=99871 fit_at=2026-07-07T19:39:16.028594+00:00

## VERDICT: **STOP**

At least one gate fails the pre-registered kill rule (`p5(true) <= p95(false)` in whitened space). Per-gate verdicts: **match: PROCEED**, **anchor: STOP**, **merge: STOP**.

| gate | raw gate today | whitened p5(true) | whitened p95(false) | gap | AUC (whitened) | AUC (raw) | tau |
|---|---|---|---|---|---|---|---|
| `match` | 0.88 | 0.6184 | 0.2261 | **0.3923** | 0.9995 | 0.9997 | 0.4223 |
| `anchor` | 0.93 | 0.2528 | 0.7999 | **-0.5471** | 0.7264 | 0.6166 | None |
| `merge` | 0.9 | 0.0923 | 0.2097 | **-0.1173** | 0.9628 | 0.9093 | None |

**No thresholds are handed to T2.** Whitening's RANKING separation is strong (AUC above) and materially better than raw at every gate — but ranking is not what an identity gate needs. A gate is a hard cut, and at the tails the two populations overlap: §5 shows label-identical same-snapshot same-country fragments scoring ~0.0 whitened while unambiguously different stories score 0.89-0.92. §6 gives the mechanism.

**The collision, in one line.** §3: the absorptions the diagnosis names — an unrelated Bolivian/Colombian cluster on a New Zealand anchor — read whitened **0.387-0.452**. §7: the 22 clusters of ONE event (the Berlin Pride attack, one day, all tagged DE) read whitened **median 0.390, min -0.060**. A cut high enough to reject the first rejects most of the second. The two populations do not merely overlap — over much of the range they are interleaved.

`match` reads PROCEED under v1, and that is an ARTIFACT, not a pass: its only TRUE source is `lineage`, i.e. pairs the raw 0.88/0.93 gates already admitted. There is no engine-independent same-story set at the running-centroid geometry, so `match` is untested here — it must not be read as validated.


**Kill rule (pre-registered, frozen before the run):** if `p5(true) <= p95(false)` in whitened space the verdict is STOP for that gate. No threshold is tuned after seeing any downstream outcome — this measurement is upstream of GQ-05.

## 1. Pair collection

Window: last **21 days** · seed `42` · 31636 clusters (16129 labelled) · 6291 topics · 10987 cluster + 3385 topic centroids fetched.

| gate | geometry | true pairs | true stories | false pairs | false groups |
|---|---|---|---|---|---|
| `match` | cluster ↔ topic running centroid | 1099 | 482 | 1500 | 1500 |
| `anchor` | cluster ↔ topic founding anchor (a cluster centroid) | 5254 | 2314 | 3296 | 1959 |
| `merge` | topic ↔ topic running centroid | 1455 | 590 | 1500 | 1499 |

Sources per gate (`truth:source`):

- **match** — `false:false_match` 1500, `true:lineage` 1099
- **anchor** — `false:false_cluster` 1500, `false:false_lineage` 1796, `true:fragment` 2871, `true:fragment_loose` 1284, `true:lineage` 1099
- **merge** — `false:false_merge` 1500, `true:topic_dup` 1455

Rules (all mechanical, pre-registered — see the harness docstring):

- **TRUE `lineage`** — attaches onto a topic whose label court returned `entailed`, member label non-NULL. *Selection caveat:* these pairs were admitted BY the raw gates, so the true RAW distribution is truncated below 0.88/0.93. `fragment` carries the engine-independent ground truth.
- **TRUE `fragment`** — same-snapshot clusters with near-identical labels (SequenceMatcher ≥ 0.80, the engine's own `MERGE_LABEL_MIN`): one event the engine shredded and never reconverged. Ground truth independent of the gates.
- **TRUE `topic_dup`** — live non-roundup, non-umbrella topics with near-identical labels: duplicate identities that SHOULD merge.
- **FALSE `false_lineage`** — attaches onto court-FAILED topics where the absorbed cluster's countries are disjoint from the anchor's AND labels are dissimilar (ratio < 0.35 and zero shared distinctive tokens). This is the measured failure mode; the diagnosis's named witnesses fall out of it.
- **FALSE `false_cluster` / `false_match` / `false_merge`** — random picks under the same disjoint-country + dissimilar-label rule (plus different typed `category` for `false_merge`), at each gate's own geometry.
- Every rule requires **both labels non-NULL**: during the 07-23→07-27 DeepSeek-402 blackout `emergent_clusters.label` was 100% NULL, and an unlabelled cluster cannot be mechanically called a different story.

## 2. Distributions

### `match` — cluster ↔ topic running centroid

| space | truth | n | p1 | p5 | p25 | p50 | p75 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|
| raw | true | 1061 | 0.9326 | 0.9469 | 0.9842 | 0.9955 | 0.9994 | 1.0 | 1.0 |
| raw | false | 1500 | 0.7747 | 0.7933 | 0.8198 | 0.8394 | 0.8614 | 0.8978 | 0.9242 |
| whitened | true | 1061 | 0.4931 | 0.6184 | 0.8915 | 0.9714 | 0.9966 | 1.0 | 1.0 |
| whitened | false | 1500 | -0.1843 | -0.1276 | -0.0382 | 0.0203 | 0.0854 | 0.2261 | 0.3873 |

- **raw**: p5(true) 0.9469 vs p95(false) 0.8978 → gap **0.0492** · AUC 0.9997 · 0.0007 of false pairs sit above p5(true) · verdict **PROCEED**
- **whitened**: p5(true) 0.6184 vs p95(false) 0.2261 → gap **0.3923** · AUC 0.9995 · 0.0007 of false pairs sit above p5(true) · verdict **PROCEED**

### `anchor` — cluster ↔ topic founding anchor (a cluster centroid)

| space | truth | n | p1 | p5 | p25 | p50 | p75 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|
| raw | true | 3932 | 0.8437 | 0.8625 | 0.8971 | 0.9271 | 0.9661 | 0.9996 | 1.0 |
| raw | false | 3296 | 0.7886 | 0.8083 | 0.8476 | 0.9318 | 0.9499 | 0.9779 | 0.9862 |
| whitened | true | 3932 | 0.1282 | 0.2528 | 0.4512 | 0.5983 | 0.7993 | 0.9978 | 1.0 |
| whitened | false | 3296 | -0.16 | -0.0788 | 0.037 | 0.4257 | 0.6163 | 0.7999 | 0.8656 |

- **raw**: p5(true) 0.8625 vs p95(false) 0.9779 → gap **-0.1154** · AUC 0.6166 · 0.679 of false pairs sit above p5(true) · verdict **STOP**
- **whitened**: p5(true) 0.2528 vs p95(false) 0.7999 → gap **-0.5471** · AUC 0.7264 · 0.5558 of false pairs sit above p5(true) · verdict **STOP**

### `merge` — topic ↔ topic running centroid

| space | truth | n | p1 | p5 | p25 | p50 | p75 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|
| raw | true | 1455 | 0.824 | 0.8434 | 0.878 | 0.9053 | 0.9345 | 0.9767 | 0.9916 |
| raw | false | 1500 | 0.7739 | 0.7901 | 0.8172 | 0.8391 | 0.8599 | 0.8914 | 0.9145 |
| whitened | true | 1455 | -0.0225 | 0.0923 | 0.3119 | 0.4726 | 0.6466 | 0.8612 | 0.9405 |
| whitened | false | 1500 | -0.1931 | -0.1286 | -0.0404 | 0.0134 | 0.0787 | 0.2097 | 0.3508 |

- **raw**: p5(true) 0.8434 vs p95(false) 0.8914 → gap **-0.048** · AUC 0.9093 · 0.4413 of false pairs sit above p5(true) · verdict **STOP**
- **whitened**: p5(true) 0.0923 vs p95(false) 0.2097 → gap **-0.1173** · AUC 0.9628 · 0.2013 of false pairs sit above p5(true) · verdict **STOP**

## 3. Named witnesses (the diagnosis's exhibits)

Every member cluster of the named topics against that topic's TRUE founding anchor (first-ever member, not window-truncated) — `gate=anchor` geometry, i.e. exactly the 0.93 comparison the engine makes.

| topic | day | cc | n | raw | **whitened** | in FALSE set | cluster label |
|---|---|---|---|---|---|---|---|
| 52 | 2026-06-03 | CO,MX | 35 | 1.0 | **1.0** | anchor | Trump Endorses De la Espriella |
| 52 | 2026-06-04 | ES,LS | 25 | 0.9335 | **0.3994** | no | Attack on UN Peacekeepers in Lebanon |
| 52 | 2026-06-08 | PE,AR | 17 | 0.9431 | **0.4987** | no | Peru Presidential Election Deadlock |
| 52 | 2026-06-08 | PE,ES | 18 | 0.94 | **0.4877** | no | Peru Presidential Election |
| 52 | 2026-06-09 | IR,US | 23 | 0.9356 | **0.4861** | no | Trump Threatens Iran Over Helicopter Downing |
| 52 | 2026-06-14 | MX,SE | 10 | 0.9305 | **0.3051** | no | Cadáver Cerca de Sede de Irán |
| 52 | 2026-06-22 | CO,ES | 18 | 0.9741 | **0.7527** | no | Political Turmoil in Spain and Colombia |
| 52 | 2026-06-25 | CO,VE | 38 | 0.9647 | **0.7074** | no | Cepeda Concedes to De la Espriella |
| 52 | 2026-06-25 | CO,VE | 15 | 0.9712 | **0.7664** | no | Cepeda Concedes to De la Espriella |
| 52 | 2026-06-25 | CO,VE | 18 | 0.9687 | **0.7463** | no | Cepeda Concedes to De la Espriella |
| 52 | 2026-07-01 | MU | 16 | 0.9522 | **0.5262** | yes | Adorni Resignation and PRO Crisis |
| 52 | 2026-07-02 | PE | 13 | 0.9481 | **0.5184** | no | Roberto Sánchez Election Fraud Claims |
| 52 | 2026-07-04 | ES | 12 | 0.9365 | **0.362** | no | Mixed News Headlines |
| 52 | 2026-07-05 | ES | 10 | 0.9358 | **0.3613** | no | Spanish Political News |
| 52 | 2026-07-06 | MX | 9 | 0.9422 | **0.4665** | no | Sheinbaum and Mexico Events |
| 52 | 2026-07-06 | WE | 15 | 0.9498 | **0.4841** | yes | Corruption Scandals Surrounding PSOE |
| 52 | 2026-07-07 | MX | 9 | 0.9422 | **0.4665** | no | Sheinbaum on Independence |
| 52 | 2026-07-09 | SE | 9 | 0.945 | **0.4409** | yes | Agostina Vega Femicidio |
| 52 | 2026-07-12 | PM | 12 | 0.9466 | **0.4299** | yes | Panamá News Roundup |
| 52 | 2026-07-13 | PM | 9 | 0.9443 | **0.4056** | yes | Panamá: Corrupción, Salud y Clima |
| 52 | 2026-07-17 | ES | 8 | 0.9326 | **0.3421** | no | Healthcare and Tourism Policies |
| 52 | 2026-07-20 | LR | 12 | 0.9481 | **0.4157** | yes | Costa Rica News Mix |
| 52 | 2026-07-21 | MX | 10 | 0.9402 | **0.4706** | no | Mexican Ex-Officials Legal Cases |
| 52 | 2026-07-22 | JP | 10 | 0.9384 | **0.3805** | yes | Japanese Culture in Dominican Republic |
| 52 | 2026-07-23 | US | 15 | 0.9309 | **0.5092** | no | *(null)* |
| 52 | 2026-07-24 | HN | 16 | 0.9487 | **0.4619** | no | *(null)* |
| 52 | 2026-07-25 | VE | 8 | 0.9429 | **0.4761** | no | *(null)* |
| 52 | 2026-07-26 | AR | 12 | 0.9331 | **0.3856** | no | *(null)* |
| 52 | 2026-07-27 | IS | 9 | 0.9335 | **0.2865** | no | *(null)* |
| 52 | 2026-07-27 | SV | 8 | 0.939 | **0.4505** | no | *(null)* |
| 784 | 2026-07-01 | NZ | 10 | 1.0 | **1.0** | anchor | Cabo Verde Captain Rape Allegations |
| 784 | 2026-07-02 | NZ | 11 | 0.9971 | **0.9751** | no | Cape Verde Captain Sexual Assault Allegations |
| 784 | 2026-07-17 | BO | 14 | 0.9318 | **0.3873** | no | Bolivian Recruitment for Russia-Ukraine War |
| 784 | 2026-07-22 | CO | 9 | 0.9391 | **0.4501** | no | Assassination Plot Allegations |
| 784 | 2026-07-24 | CO | 10 | 0.9406 | **0.4524** | no | *(null)* |
| 784 | 2026-07-25 | CO | 13 | 0.937 | **0.4374** | no | *(null)* |
| 784 | 2026-07-26 | CO | 11 | 0.9361 | **0.4315** | no | *(null)* |
| 784 | 2026-07-27 | CO | 9 | 0.9382 | **0.4384** | no | *(null)* |

`in FALSE set` = the row also cleared the conservative mechanical rule (disjoint countries + dissimilar same-script labels). Rows marked `no` are still real absorptions — they are simply not counted as evidence here, which keeps the FALSE distribution free of judgement calls.

## 4. Sensitivity

Whitened tau under alternative pair-set compositions. The primary fit uses the overmerge exclusion; every variant is reported so the fit's dependence on that rule is visible.

| variant | gate | n true | n false | p5(true) | p95(false) | gap | tau | verdict |
|---|---|---|---|---|---|---|---|---|
| `no_overmerge_exclusion` | match | 1099 | 1500 | 0.6141 | 0.2261 | 0.388 | 0.4201 | PROCEED |
| `no_overmerge_exclusion` | anchor | 5254 | 3296 | 0.2281 | 0.7999 | -0.5719 | None | STOP |
| `no_overmerge_exclusion` | merge | 1455 | 1500 | 0.0923 | 0.2097 | -0.1173 | None | STOP |
| `with_overmerge_exclusion` | match | 1061 | 1500 | 0.6184 | 0.2261 | 0.3923 | 0.4223 | PROCEED |
| `with_overmerge_exclusion` | anchor | 5216 | 3296 | 0.2276 | 0.7999 | -0.5723 | None | STOP |
| `with_overmerge_exclusion` | merge | 1455 | 1500 | 0.0923 | 0.2097 | -0.1173 | None | STOP |
| `lineage_only` | match | 1061 | 1500 | 0.6184 | 0.2261 | 0.3923 | 0.4223 | PROCEED |
| `lineage_only` | anchor | 1061 | 3296 | 0.5453 | 0.7999 | -0.2547 | None | STOP |
| `lineage_only` | merge | 0 | 1500 | None | None | None | None | INSUFFICIENT |
| `fragment_only` | match | 0 | 0 | None | None | None | None | INSUFFICIENT |
| `fragment_only` | anchor | 2871 | 3296 | 0.2287 | 0.7999 | -0.5713 | None | STOP |
| `fragment_only` | merge | 0 | 0 | None | None | None | None | INSUFFICIENT |
| `fragment_plus_loose` | match | 0 | 0 | None | None | None | None | INSUFFICIENT |
| `fragment_plus_loose` | anchor | 4155 | 3296 | 0.2101 | 0.7999 | -0.5898 | None | STOP |
| `fragment_plus_loose` | merge | 0 | 0 | None | None | None | None | INSUFFICIENT |
| `false_lineage_only` | match | 1061 | 0 | None | None | None | None | INSUFFICIENT |
| `false_lineage_only` | anchor | 3932 | 1796 | 0.2528 | 0.8328 | -0.58 | None | STOP |
| `false_lineage_only` | merge | 0 | 0 | None | None | None | None | INSUFFICIENT |
| `false_random_only` | match | 1061 | 1500 | 0.6184 | 0.2261 | 0.3923 | 0.4223 | PROCEED |
| `false_random_only` | anchor | 3932 | 1500 | 0.2528 | 0.2352 | 0.0176 | 0.244 | PROCEED |
| `false_random_only` | merge | 0 | 1500 | None | None | None | None | INSUFFICIENT |
| `no_witnesses` | match | 1061 | 1500 | 0.6184 | 0.2261 | 0.3923 | 0.4223 | PROCEED |
| `no_witnesses` | anchor | 5216 | 3289 | 0.2276 | 0.8 | -0.5724 | None | STOP |
| `no_witnesses` | merge | 1455 | 1500 | 0.0923 | 0.2097 | -0.1173 | None | STOP |

Overmerge exclusion set: **406** topic ids from 6 `detect_overmerge` demotion ledger(s).

## 5. Tails (contamination audit)

The lowest-whitened TRUE pairs and the highest-whitened FALSE pairs per gate. A same-story pair reported under disjoint countries with disjoint label tokens would land in the false right tail; a fused blob that passed the court would land in the true left tail. Read these before trusting the taus.

### `match` — TRUE left tail (lowest whitened)

| whitened | raw | source | A | B |
|---|---|---|---|---|
| 0.081 | 0.9018 | `lineage` | Marokko WK Zege Onrust | US Strikes on Iran |
| 0.1977 | 0.9206 | `lineage` | Marokko WK Zege Onrust | US Strikes on Iran |
| 0.3257 | 0.9309 | `lineage` | Amitabh Bachchan Health Update | UFC Fighter Reactions and Rivalries |
| 0.3514 | 0.9165 | `lineage` | Spain World Cup Victory | Greece Wins World Cup Polo Gold Over Hungary |
| 0.3851 | 0.9511 | `lineage` | Yemen Conflict Escalation | US Strikes on Iran |
| 0.4039 | 0.9331 | `lineage` | Sinner Wins Wimbledon | Antonelli Wins Belgian GP |
| 0.4091 | 0.9339 | `lineage` | Iran Assassination Plot | US Strikes on Iran |
| 0.4463 | 0.9295 | `lineage` | Spain World Cup Victory | Greece Wins World Cup Polo Gold Over Hungary |
| 0.4542 | 0.9359 | `lineage` | Greece Wins Water Polo World Cup | Greece Wins World Cup Polo Gold Over Hungary |
| 0.4565 | 0.9347 | `lineage` | PV Sindhu Wins Japan Open | Wimbledon Quarterfinalists |
| 0.4907 | 0.9473 | `lineage` | Isaac Del Toro Wins Tour de France Stage | Greece Wins World Cup Polo Gold Over Hungary |
| 0.4947 | 0.935 | `lineage` | Lukman Quits ADC Over El-Rufai | El-Rufai Doctor Arrest |
| 0.4992 | 0.9437 | `lineage` | Iran Assassination Plot | US Strikes on Iran |
| 0.5022 | 0.9308 | `lineage` | Trump Blasts Netanyahu Over Lebanon | Israel Lebanon Withdrawal Dispute |
| 0.5159 | 0.9304 | `lineage` | Russia Plans Fall Mobilization | Russia Plans Fall Mobilization |

### `match` — FALSE right tail (highest whitened)

| whitened | raw | source | A | B |
|---|---|---|---|---|
| 0.76 | 0.9694 | `false_match` | Trump Threatens Iran Attack | 2026 World Cup Updates |
| 0.601 | 0.9403 | `false_match` | Argentina World Cup 2026 | Olympia Odos Toll Change |
| 0.5583 | 0.9406 | `false_match` | Russian Fuel Crisis | France Assisted Suicide Law |
| 0.5322 | 0.9453 | `false_match` | Local Crime and Bail Cases | Bombay HC on Protest Rights |
| 0.5276 | 0.9298 | `false_match` | Qatar Denies Military Role Against Iran | Islamic Fatwas on Marriage |
| 0.4861 | 0.9133 | `false_match` | Health and Heat Risks | Oil Prices Rise Amid US-Iran Tensions |
| 0.4842 | 0.9306 | `false_match` | West Nile Virus Outbreak in Glyfada | Giannis Antetokounmpo Miami Heat Presentation |
| 0.4829 | 0.9118 | `false_match` | Oil Prices Rise Amid US-Iran Tensions | Israeli Military Activity in Syria |
| 0.463 | 0.9262 | `false_match` | Russia Threatens Foreign Troops | Greece Leads EU Debt Reduction |
| 0.4165 | 0.9218 | `false_match` | Milei's Reform Agenda | Yolanda Díaz OIT Candidacy |
| 0.415 | 0.9327 | `false_match` | Violent Attacks and Homicides | Noruega Elimina a Brasil |
| 0.4129 | 0.9221 | `false_match` | Wanda Nara Milan Robbery | Terremotos en Venezuela |
| 0.4068 | 0.9306 | `false_match` | Dudamel World Cup Tribute | Avian Flu Safety |
| 0.3938 | 0.9262 | `false_match` | TikTok Child Safety Probe | Bengaluru Daycare Abuse Case |
| 0.3938 | 0.9157 | `false_match` | Tentato Omicidio a Ivrea | Norway Wildfire Destroys Homes |

### `anchor` — TRUE left tail (lowest whitened)

| whitened | raw | source | A | B |
|---|---|---|---|---|
| -0.0604 | 0.8028 | `fragment_loose` | Berlin Pride Vehicle Attack | Berlin Pride Attack Suspect |
| -0.0363 | 0.8663 | `fragment_loose` | Russian Drone Attacks Across Ukraine | Russian Missile Attacks on Ukraine |
| -0.0327 | 0.8789 | `fragment` | 2026 World Cup Final | 2026 World Cup Final |
| -0.0174 | 0.8068 | `fragment_loose` | Berlin Pride Vehicle Attack | Berlin Pride Terror Attack |
| -0.0132 | 0.8515 | `fragment_loose` | France Spain Wildfires | Wildfires in France and Spain |
| -0.0111 | 0.8638 | `fragment_loose` | Wildfires in France and Spain | France Spain Wildfires |
| -0.0056 | 0.8835 | `fragment_loose` | Bolivian Recruitment for Russia-Ukraine War | Russia Ukraine War Prospects |
| -0.0042 | 0.8479 | `fragment_loose` | Spain Reaches World Cup Final | Spain vs Argentina World Cup Final |
| -0.002 | 0.811 | `fragment_loose` | Berlin Pride Vehicle Attack | Berlin Pride Attack Suspect Killed |
| -0.0015 | 0.8414 | `fragment` | Berlin Pride Attack | Berlin Pride Attack Suspect |
| 0.0095 | 0.835 | `fragment` | Berlin Pride Attack | Berlin Pride Attack |
| 0.0116 | 0.8384 | `fragment` | Russian Missile Strikes on Ukraine | Russian Missile Strikes on Ukraine |
| 0.016 | 0.828 | `fragment` | Berlin Pride Attack Suspect | Berlin Pride Attack Suspect |
| 0.0188 | 0.8371 | `fragment` | Ukrainian Drone Attacks on Russia | Ukrainian Drone Strikes in Russia |
| 0.0231 | 0.8518 | `fragment_loose` | Russian Drone Attacks Across Ukraine | Russian Missile Attacks on Ukraine |

### `anchor` — FALSE right tail (highest whitened)

| whitened | raw | source | A | B |
|---|---|---|---|---|
| 0.9229 | 0.9902 | `false_lineage` | FIFA Trump Balogun Red Card | World Cup 2026 Updates |
| 0.9108 | 0.9876 | `false_lineage` | Congo Governance and Development | Ebola Outbreak and Security Issues |
| 0.9104 | 0.9888 | `false_lineage` | France Team Controversy | World Cup 2026 Updates |
| 0.9097 | 0.9886 | `false_lineage` | Ucrânia-Rússia Conflito Ataques | EU-Ukraine Defense Cooperation |
| 0.9091 | 0.9865 | `false_lineage` | Escalation in Ukraine War | Russian Ballistic Missile Attack on Kyiv |
| 0.9083 | 0.9898 | `false_lineage` | Drone Incident in Moldova | Russia's Crises and War |
| 0.9076 | 0.9906 | `false_lineage` | Heatwave and Climate Warnings | Diverse News Headlines |
| 0.9072 | 0.9914 | `false_lineage` | Germany News Roundup | EU Budget and Politics |
| 0.9032 | 0.9882 | `false_lineage` | Houthi Maritime Blockade Threat | Yaman Konflik Memanas |
| 0.899 | 0.9898 | `false_lineage` | European Heatwave Impacts | Russia's Crises and War |
| 0.892 | 0.9877 | `false_lineage` | Turcia și Grecia în Vacanțe | Roma and Romania |
| 0.8899 | 0.986 | `false_lineage` | Romanian Political Turmoil | PSD vs PNL Coalition Crisis |
| 0.8882 | 0.9873 | `false_lineage` | Crime and Violence in Cyprus | Trump Warns Netanyahu on Iran |
| 0.8858 | 0.9864 | `false_lineage` | Greek Basketball Team Reactions | Olympiacos Transfers and World Cup 2026 |
| 0.8858 | 0.9864 | `false_lineage` | Greek Basketball Coach Outburst | Olympiacos Transfers and World Cup 2026 |

### `merge` — TRUE left tail (lowest whitened)

| whitened | raw | source | A | B |
|---|---|---|---|---|
| -0.1449 | 0.829 | `topic_dup` | Dua Lipa Supports Protests | Dua Lipa Supports Albanian Protests |
| -0.1407 | 0.8115 | `topic_dup` | Ukrainian Drone Attacks on Russia | Ukrainian Drone Attacks on Russia |
| -0.0999 | 0.848 | `topic_dup` | Elon Musk Supports Le Pen | Musk Supports Le Pen |
| -0.0983 | 0.863 | `topic_dup` | US-Iran Military Escalation | US Iran Conflict Escalation |
| -0.0813 | 0.8475 | `topic_dup` | Ebola Outbreak Congo | Ebola Outbreak Congo |
| -0.0693 | 0.7942 | `topic_dup` | Mass Drone Attack on Moscow | Ukrainian Drone Attacks on Moscow |
| -0.0647 | 0.8308 | `topic_dup` | Ukrainian Drone Attacks | Ukrainian Drone Attacks on Russia |
| -0.0592 | 0.8333 | `topic_dup` | Ukraine Drone Attacks Russia | Ukrainian Drone Attacks on Russia |
| -0.058 | 0.859 | `topic_dup` | Venezuela Earthquake Death Toll | Venezuela Earthquake Death Toll |
| -0.0487 | 0.8578 | `topic_dup` | Macedonia-Germany Defense Cooperation | France-Germany Defense Cooperation |
| -0.0462 | 0.8588 | `topic_dup` | Venezuela Earthquake Death Toll | Venezuela Earthquake Death Toll |
| -0.0423 | 0.8662 | `topic_dup` | Venezuela Earthquake Death Toll | Venezuela Earthquake Death Toll |
| -0.0374 | 0.8123 | `topic_dup` | Andy Burnham Prime Minister | Andy Burnham Prime Minister |
| -0.0334 | 0.8551 | `topic_dup` | US-Iran Military Escalation | US-Iran Military Escalation |
| -0.0253 | 0.8736 | `topic_dup` | Ukraine War Escalation | Ukraine War Escalation |

### `merge` — FALSE right tail (highest whitened)

| whitened | raw | source | A | B |
|---|---|---|---|---|
| 0.6343 | 0.9405 | `false_merge` | Haaland Eliminates Brazil | Spain Wins Second World Cup |
| 0.5496 | 0.9295 | `false_merge` | Iran Attacks Bahrain | Arrests and Fines for Wildfires |
| 0.543 | 0.9298 | `false_merge` | July Holiday Exodus | Iran Suspends US Agreement |
| 0.5162 | 0.9467 | `false_merge` | Scaloni Future Doubts | El Chapo Lawsuit Dismissed |
| 0.4577 | 0.9458 | `false_merge` | FIFA Suspends Balogun Red Card | Copa do Mundo 2026 Semifinal e Final |
| 0.4553 | 0.9379 | `false_merge` | Iraq Anti-Corruption Crackdown | Tasoulas Letter to Trump |
| 0.4547 | 0.9166 | `false_merge` | Severe Weather and Smoke | Météo Sénégal Pluies Orages |
| 0.4404 | 0.9133 | `false_merge` | Strait of Hormuz De-mining | Police Checks and Arrests |
| 0.4324 | 0.8993 | `false_merge` | Russian Strikes on Ukrainian Ports | Modric Extends Milan Contract |
| 0.419 | 0.8938 | `false_merge` | Explosions in Southern Iran | Tate Brothers Arrested in US |
| 0.3798 | 0.8974 | `false_merge` | Venezuela Earthquake Death Toll | DR Congo Ebola Outbreak |
| 0.3734 | 0.8991 | `false_merge` | World Cup 2026 Final | Pakistan Gold and Currency Rates |
| 0.3688 | 0.9173 | `false_merge` | Kueider Sentenced in Paraguay | Moreno Investiture Failure |
| 0.3674 | 0.9392 | `false_merge` | Crime and Corruption Investigations | World Cup 2026 Updates |
| 0.3535 | 0.8762 | `false_merge` | Terremotos en Venezuela | Myanmar Shipwreck Deaths |

## 6. Is whitened cosine measuring STORY or LANGUAGE?

Whitened cosine, split by whether the two sides share a dominant language key (`signals_v2.source_lang` where known — ~45% — else the dominant Unicode script of the headlines). If whitening were a story detector, TRUE pairs would score high in both columns.

| gate | truth | relation | n | whitened p5 | p50 | p95 | raw p50 |
|---|---|---|---|---|---|---|---|
| match | true | same_lang | 151 | 0.7452 | 0.9656 | 1.0 | 0.9946 |
| match | true | cross_lang | 7 | 0.5251 | 0.7438 | 0.9423 | 0.9523 |
| match | false | same_lang | 37 | -0.0862 | 0.0482 | 0.3053 | 0.8531 |
| match | false | cross_lang | 126 | -0.1394 | 0.0142 | 0.1717 | 0.8348 |
| anchor | true | same_lang | 350 | 0.2385 | 0.6774 | 1.0 | 0.9476 |
| anchor | true | cross_lang | 636 | 0.1576 | 0.437 | 0.6958 | 0.8913 |
| anchor | false | same_lang | 37 | -0.1052 | 0.0074 | 0.3767 | 0.8487 |
| anchor | false | cross_lang | 90 | -0.1447 | -0.0029 | 0.1183 | 0.8297 |
| merge | true | same_lang | 145 | 0.2359 | 0.6142 | 0.9147 | 0.9428 |
| merge | true | cross_lang | 266 | 0.0883 | 0.3935 | 0.7187 | 0.8945 |
| merge | false | same_lang | 108 | -0.1529 | 0.0214 | 0.243 | 0.8576 |
| merge | false | cross_lang | 369 | -0.123 | 0.0149 | 0.1829 | 0.8373 |

Pair language coverage: {'same_lang': 834, 'unknown': 11776, 'cross_lang': 1494}

**Limitation (biases the effect DOWNWARD):** Latin-script rows whose `source_lang` is unknown all collapse to `script:latin`, so Romanian-vs-English counts as *same* language. The measured cross-language penalty is therefore a lower bound.

## 7. Shredded-event families (the primary metric's own exhibits)

Every pair inside a family is the SAME event by construction. This is the direct read on whether whitened space can RECONVERGE a shredded story.

| family | day | clusters | pairs | countries | raw min/p50/max | **whitened min/p50/max** |
|---|---|---|---|---|---|---|
| `%caspian%` | 2026-07-28 | 3 | 3 | IR,UA | 0.9108/0.9137/0.9932 | **0.6349/0.6678/0.9578** |
| `%iran%ukrain%` | 2026-07-28 | 9 | 36 | IR,UA | 0.8578/0.9078/0.9932 | **0.1774/0.5273/0.9578** |
| `%berlin pride%` | 2026-07-28 | 22 | 231 | DE | 0.8028/0.8837/0.9802 | **-0.0604/0.3901/0.8741** |
| `%espriella%` | 2026-06-25 | 3 | 3 | CO,EC,GZ,VE | 0.9945/0.9966/0.9991 | **0.9572/0.9739/0.993** |

## 8. Construction v0 vs v1

v0 = the first pass; v1 repairs the four ground-truth defects its tail audit exposed (D1-D4, see the harness docstring). Verdicts under both:

| construction | match | anchor | merge | overall |
|---|---|---|---|---|
| `v0` | STOP | STOP | STOP | **STOP** |
| `v1` | PROCEED | STOP | STOP | **STOP** |

v1's D3 (a TRUE fragment pair must share a country) drops exactly the cross-country/cross-language fragments that whitening scores LOWEST, so v1's true set is biased in whitening's FAVOUR. The STOP survives that bias.

## 9. Honest limits

- The TRUE `lineage` set is engine-selected (admitted by the raw gates); its raw distribution is truncated from below and must not be read as "raw works". The `fragment_only` sensitivity row is the engine-independent read.
- The FALSE rules can misfile a genuinely-shared story told with disjoint vocabulary in disjoint countries. That error is CONSERVATIVE — it raises p95(false) and narrows the gap — so a PROCEED verdict survives it. The false right tail above is the audit surface for it.
- `topic_dup` true-merge pairs are duplicate LABELS, not adjudicated duplicates; a recurring label form ("X Presidential Election") across genuinely different events would contaminate them. Within a short window this is unlikely but not impossible.
- Blocking (≥2 shared distinctive tokens, token doc-freq ≤ 5% of the block, blocks >400 members skipped) bounds RECALL of the same-event search; it does not affect precision, and the pairs it finds are a fair sample of same-event pairs.
- Percentile estimates carry sampling error; the reported gap should be read with the n column beside it, not as an exact constant.
- The §6 language split resolves only pairs whose sample signals still exist in `signals_v2` (7-day hot retention), so it covers a recent subset of the pairs; the `unknown` bucket in the coverage line is that retention gap, not a failure of the rule.
- `different_story` requires SequenceMatcher < 0.35 on the whole label string. Two unrelated English labels often score above that by character coincidence, so the FALSE sets are smaller than the true rate of different-story pairs. Conservative: it can only shrink evidence, never manufacture it (§3 shows real absorptions marked `no`).
