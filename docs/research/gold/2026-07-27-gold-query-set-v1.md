# Gold analyst query set — Atlas primary metric (roadmap P2.1)

**Date:** 2026-07-27  
**Status:** DRAFT — needs Pedro's 5 hand-written queries before the first official run (see Threats §1)  
**Metric it serves:** roadmap Phase 2 — *"for a gold set of ~20 real analyst queries, does Atlas have a clean thread answering each? Target: >=80%."* Never computed before this document.

## Why this set is built the way it is

The gold set exists to TEST Atlas, so it must not be derived from Atlas's own output.
Every query below traces to **raw `signals_v2` headlines** — upstream of every clustering,
labelling and ranking decision — or to what the wedge persona asks regardless of the week.
No query was written by reading a `dynamic_topics` label, a served thread, or the daily
edition.

Two design rules make the number mean something:

1. **A gold set Atlas scores 100% on is a broken gold set.** 4 queries are marked
   `stretch` (real, but thin in the raw corpus) and are expected to be hard.
2. **Six negative controls.** These look like plausible analyst questions but cannot be
   answered honestly from a 7-day press corpus. A control **PASSES when Atlas returns an
   honest absence** and **FAILS when it confabulates a confident-looking thread.** Without
   this arm the metric cannot discriminate between a system that knows things and a system
   that always says something — the exact failure that killed silent-risk in 2026-07.

## Composition

« **20 queries: 14 real (10 should_answer, 4 stretch) + 6 negative controls.**

**By expected:** should_answer 10 (GQ-01…10) · stretch 4 (GQ-11 AJK, GQ-12 Caspian, GQ-13 Sudan, GQ-14 Ebola asymmetry) · negative_control 6 (GQ-15…20).

**By domain:** conflict 6 · governance 4 · finance 3 · disasters 2 · elections 2 · other 2 · health 1.

**By region (17 distinct):** Spain/France · Germany ×2 · DR Congo ×2 · Philippines · Colombia-Cuba-Nicaragua · Iran/US/Gulf ×2 · Indonesia · Nicaragua · Romania · Pakistan-administered Kashmir · Iran/Ukraine/Caspian · Sudan · Australia · Lesotho · Mongolia · global oil markets · Iran. **No US-domestic and no UK-domestic query, and only two elections items — the set does not collapse into the US/UK/elections attractor.**

**Non-English source languages materially represented in the receipts:** es, fr, ar, fa, ro, id, sw, pt, no, sv, hi/ur, sq, de, fi, da — 8+ carrying load-bearing evidence, well above the ≥4 floor.

**Control arm design.** Six controls, deliberately of **two kinds**, because they fail differently. Type I (GQ-15 Australia, GQ-16 Lesotho, GQ-17 Mongolia) are *absent events* with real vocabulary and well-ingested regions — verified ~0 corpus support. Type II (GQ-18 origin chain, GQ-19 oil lead-lag/forecast, GQ-20 public opinion) are *unanswerable question kinds* over heavily-covered subjects. Type I catches vocabulary pattern-matching; Type II catches epistemic overreach in the LLM surfaces. A control arm of only one kind misses half the failure space. **Every control is twinned with a real item of near-identical shape** (§5 table), so the metric reports six *pair gaps* — the discriminating statistic, not just a pass count.

**Why this composition is defensible.**

1. **Every query traces to a raw `signals_v2` headline, never to an Atlas label.** No thread label, briefing, daily edition, `atlas_topics` row or label-court verdict was consulted to source any query. Atlas output was read only afterwards, to score.
2. **Every load-bearing count was re-verified against prod this session** (7d to 2026-07-27), not transcribed: wildfire 5,011 / incendio 3,721 / bushfire 8; ebola 857 across 505 outlets with the exact language split en 569(335) / fr 35(11) / sw 8(3); sudan 243/140; caspian 180; espriella 633/116; warjiyo 179; bolojan 244/58; hormuz 1,454/677; berlin+pride 1,454/788; NI 962 signals across 539 outlets with only 102 rows from 2 NI-origin outlets. **One correction applied:** AJK was measured at 349 by a loose `'ajk'` substring; the tight pattern gives **116 / 47 outlets**, and the tighter number is the one carried. **One claim could not be re-verified** (Persian-lane single-outlet concentration — query timed out) and is flagged inside GQ-06 rather than asserted.
3. **All three Type-I controls verified absent, and Australia verified *airtight*:** `country_code='AU'` returns **17,825 signals across 2,044 outlets** in the same 7 days while `bushfire` returns 8. The region is present in force, the vocabulary is present in force, only the event is absent — so a wrong answer there cannot be excused as a feed gap. Lesotho (49 signals, 0 on trade) and Mongolia (54 signals, 0 on politics) are the same construction in low-volume regions, which additionally tests whether Atlas distinguishes *"we don't ingest this region"* from *"we have no evidence for this event."*
4. **The set is calibrated to fail.** 4 stretch items sit where the corpus is genuinely thin (Sudan: 243 signals for an active war; AJK: near-zero Western pickup; Swahili Ebola: 8 signals from 3 outlets). **GQ-10 (Romania/Bolojan) ships with a measured answer key of level 1** — verified in-corpus (244 signals / 58 outlets) and verified as a clustering miss on 2026-07-27, with the corpus control already run so the failure is provably engine, not ingestion. It is the one longitudinal recall signal in the set. **GQ-09 (Nicaragua) is expected to fail** despite being marked should_answer, because the correct answer *is* a measured near-zero, which a volume-ranked engine buries.
5. **Three falsification checks are built into real items, so honesty is scored even on passes:** GQ-03 carries a publication-date artifact (death tolls 930→1,400 in one window from GDELT resurfacing history) that must not be reported as outlet disagreement; GQ-07 carries a syndication chain legible in the headline text that must not read as three confirmations; GQ-13 scores the empty state rather than recall, where a confident answer is the failure.
6. **Deduplication:** the three derivations independently converged on Spain/France wildfires, Colombia/Espriella, Iran-Hormuz, Nicaragua and Indonesia's central bank. Each was kept **once**, taking the framing with the strongest raw evidence — e.g. Nicaragua uses the ownership-based self-voice framing (962/539 vs 2 domestic outlets) rather than the weaker "is this covered?" framing, and Indonesia benefits from being the only item cross-confirmed by two independent discovery methods. Four candidates were dropped as redundant (Turkmenistan gas ≈ Lesotho; Berlin far-right causation ≈ GQ-19's causal class; Oman negotiating terms ≈ GQ-20's ground-truth class; Iran civilian death counts ≈ GQ-03's contested-figures check). »

## The set

### GQ-01 — should_answer

**Query:** Wildfires in France and Spain — how many people have been evacuated, and where is the fire front now?

**Domain / region:** disasters · Western Europe (Spain / France)

**Why this is a real question:** Verified in raw signals_v2 this session (7d to 2026-07-27): 'wildfire' = 5,011 headlines, 'incendio' = 3,721. Dominant multi-country, multi-language hazard story in the window. Raw receipts carry hard, checkable and DIVERGENT numbers across three languages: 'France says wildfire that forced 220,000 people to flee has stopped growing' (northwalespioneer.co.uk), 'Du jamais-vu en France : 200 000 personnes évacuées' (franceinfo.fr), 'Plus de 325.000 réfugiés du feu en France et Espagne, le feu à 15 km de la métropole bordelaise' (libe.ma), 'El incendio de Ávila ya supera al de Larouco como el más devastador de la historia de España' (elprogreso.es), 'Los incendios de Ávila, Madrid y Toledo... han calcinado ya 77.000 hectáreas' (diariosur.es), 'إجلاء أكثر من 320 ألف شخص فى فرنسا وإسبانيا' (almasryalyoum.com). Question written from those raw headlines; no Atlas label consulted.

**Pass criteria:** PASS = level ≥2. First 20 served receipts ≥75% about the Iberian/French fire complex (ROR@20 ≥0.75), receipts in ≥2 of es/fr/en, ≥3 distinct outlets across ≥2 origin countries. The divergent evacuation figures (200k / 220k / 250k / 325-330k) and burnt-area figures (50k / 77k ha) must be presented as attributed, differently-scoped claims — not silently collapsed to one number. Level 3 additionally requires ROR@all ≥0.75. KNOWN LIVE BEHAVIOUR to check against: measured 2026-07-27 the served thread's full membership was ~0.66 on-topic, with a ~18% Gaza water/famine sub-cluster and a ~9% Belgian drought cluster glued in on a heat/water semantic axis — that caps it at 2, and caps it at 0 if coherence.tier / label_status / confidence carry no warning. FAIL = one merged 'global heat' blob, or a single evacuation number with no attribution.

### GQ-02 — should_answer

**Query:** The Berlin Pride attack — what happened, and why are German authorities being criticised?

**Domain / region:** conflict · Germany

**Why this is a real question:** Verified this session: headlines matching 'berlin' AND 'pride' = 1,454 across 788 distinct outlets in 7 days — one of the widest source spreads in the corpus. Two distinct strands in the raw text: the attack itself ('One dead, 16 injured after car hits Berlin Pride crowd', illawarramercury.com.au; 'Berlin Pride attack suspect killed in police confrontation after 24-hour search', fox11online.com) and an accountability strand ('Berlin Pride attack suspect raised red flags, group says, amid questions about prior release from prison despite ISIS ties', cbsnews.com). Cross-language: Romanian (ziare.com — victim identified as a 65-year-old Polish woman), Slovak (tyzden.sk), Albanian (24-ore.com, Merz response), Norwegian (tv2.no), Swedish (svd.se).

**Pass criteria:** PASS = level ≥2: a thread SPECIFIC to the Berlin Pride vehicle attack, ROR@20 ≥0.75, ≥3 independent outlets after syndication collapse. G1 applies — a taxonomy-level terrorism/Europe bucket caps at 1 unless ≥50% of its receipts are this event. G2 applies hard: this story is heavily wire-syndicated (verbatim copy across UK regionals such as ipswichstar / clactonandfrintongazette / countytimes / watfordobserver), so headline_diversity <0.5 or repeatedHeadlineShare >0.35 caps at 1, and 788 outlets must NOT be counted as 788 corroborations. Level 3 requires the accountability strand (prior release / prison / red flags) present in receipts, not just the attack. FAIL = a label naming a different attack while receipts are this one (the measured G4 case dynamic-topic-7834, 'Atac Armat în Stade', whose receipts are a Berlin Pride attack plus a Neamț drowning plus a Chișinău grenade).

### GQ-03 — should_answer

**Query:** The Ebola outbreak in DR Congo — how many cases and deaths, and what is the international response?

**Domain / region:** health · Democratic Republic of the Congo

**Why this is a real question:** Verified this session: 857 headlines matching 'ebola' across 505 distinct outlets in 7 days. Numerically concrete with a distinct aid/response strand: 'DR Congo's confirmed Ebola cases top 3,200 as outbreak remains in sustained transmission' (prokerala.com, CD), 'Israel sends three tons of medical aid to Congo amid Ebola epidemic' (clevelandjewishnews.com), 'Epidemia de Ebola ia amploare. A fost depășit pragul de 3.000 de cazuri' (ziuanews.ro). Canonical health case at a volume comparable to items Atlas handles well.

**Pass criteria:** PASS = level ≥2: DRC-outbreak thread, ROR@20 ≥0.75, ≥3 independent outlets, response strand present. BUILT-IN FALSIFICATION CHECK — this item carries a deliberate time artifact: within the SAME 7-day window the corpus holds death tolls of ~930 (timeslive.co.za), ~1,000 (ckom.com), 'over 1,000' (cbc.ca), 1,354 (ibcworldnews.com) and 1,400 (northerndailyleader.com.au), and case counts of 2,900 / 3,075 / 3,200, because the GDELT lane resurfaces articles from across the outbreak's history. PASS requires Atlas to treat that spread as a publication-date artifact, or at minimum not to assert anything about it. Presenting it as a live who-says-what DISAGREEMENT between outlets is a FAIL (score 0) even if every other criterion is met — it manufactures a finding out of ingest behaviour. Reporting a single 'confirmed' total is also a FAIL.

### GQ-04 — should_answer

**Query:** The corruption scandal around Marcos in the Philippines — what did he say in the state of the nation address?

**Domain / region:** governance · Philippines

**Why this is a real question:** Verified this session: 67 headlines matching 'marcos' AND (sona | state of the nation | corrupt) across 17 distinct outlets in 7 days. Raw headlines: 'Marcos SONA: Romualdez to be charged for flood control corruption | The wRap' (rappler.com), 'Philippines' Marcos puts anti-graft campaign at centre of address to Congress' (businesstimes.com.sg), 'Rappler Recap: From Pax Silica to corruption, SONA protesters demand action', plus a wire-syndicated 'Philippine president slams China in veiled rebuke' across ksat.com / stardem.com / 2news.com. Modest volume, strong source independence — domestic (Rappler, Manila Times) plus regional (SCMP, AsiaOne, Business Times SG).

**Pass criteria:** PASS = level ≥2 on a deliberately low-volume, non-US/EU governance substrate: ROR@20 ≥0.75 and ≥3 distinct outlets spanning ≥2 origin countries, with the wire-syndicated 'veiled rebuke at China' copies collapsed to ONE source under D3 (17 outlets ≠ 17 confirmations). G1 caps at 1 if the answer is a generic 'Corruption investigation' category thread rather than this specific SONA event. Level 1 is acceptable ONLY as an honest floor (labelled raw signal with sources), never as a category bucket presented as an answer. PAIRED with GQ-17 (Mongolia), which is the same governance shape with zero corpus support.

### GQ-05 — should_answer

**Query:** Colombia's president-elect is closing embassies and cutting ties with Cuba and Nicaragua — what exactly has been announced, and who is reporting it?

**Domain / region:** governance · Colombia / Cuba / Nicaragua

**Why this is a real question:** Verified this session: 633 headlines matching 'espriella' across 116 distinct outlets in 7 days. Overwhelmingly Spanish-language with a thin English tail: 'Colombia romperá relaciones diplomáticas con Nicaragua y Cuba' (confidencial.digital), 'De la Espriella anuncia el cierre de varias embajadas como Cuba y Nicaragua: no habrá vínculo con tiranías' (elcolombiano.com), 'Abelardo de la Espriella anticipa el fin de las relaciones... junto al cierre de 14 embajadas' (larepublica.pe), 'De la Espriella cerrará cerca de 15 embajadas' (heraldo.es), vs 'Colombian President-Elect Plans Diplomatic Shake-Up' (cubaheadlines.com). Thick domestic lane (eltiempo, semana, pulzo, lafm, portafolio, elheraldo all measured present).

**Pass criteria:** PASS = level ≥2: ROR@20 ≥0.75 with a MAJORITY of receipts in Spanish and ≥3 distinct Colombian-origin outlets. Because volume is high (633 across 116 outlets), a miss here is a language/ranking failure — the English-firehose-buries-non-English problem the project has diagnosed — not a data gap, and must be reported as such. Level 3 additionally requires the measured counterpart-voice ABSENCE to be surfaced: Cuban and Nicaraguan outlets are near-absent from this corpus (NI-origin = 2 outlets, verified this session), so a complete answer names who is NOT speaking. FAIL = an English-only receipt set, or asserting Cuban/Nicaraguan reaction the corpus does not contain. Honest caveat for the scorer: the CO lane was measurably thinned by the 2026-07-21 over-merge demotions, so a short-but-real list can still be a PASS.

### GQ-06 — should_answer

**Query:** The US and Iran have paused strikes — give me US/Western, Iranian and Gulf/Arab framing side by side, with the state-owned outlets marked.

**Domain / region:** conflict · Iran / United States / Gulf

**Why this is a real question:** The largest story in the corpus: 'hormuz' alone = 1,454 headlines across 677 distinct outlets in 7 days (verified this session); 'iran' ≈ 16,876. Framings genuinely diverge in the raw text: 'US and Iran pause attacks as efforts for ceasefire negotiations continue' (wgauradio.com), 'Iran army says war to expand further if US attacks restart' (arabnews.com), 'GULF DIVIDE: Arab States Push To End Iran War But Clash Over Path To Peace' (theyeshivaworld.com), 'ترامب يهدد مجددا بالعودة لـالعمل العسكري القوي ضد إيران' (skynewsarabia.com), 'ترامپ ادعاها و تهدیدات پوچ خود درباره ایران را تکرار کرد' (irna.ir), 'Senior Iranian legislator warns Kiev of retaliation' (tass.com), 'Brisante Wende im Iran-Krieg' (hna.de). The non-Western voice in this corpus is overwhelmingly state-owned (irna.ir, russian.rt.com, arabic.rt.com, tass.com, aa.com.tr lead the state lane).

**Pass criteria:** PASS = level ≥2: three framings present with receipts, and RT / IRNA / TASS visibly carrying is_state_media=true or the STATE tier chip (shipped 2026-07-20 through receipts, citations and synthesis). Level 3 additionally requires the OWNERSHIP caveat: the Persian-language lane in this corpus is effectively one state outlet, so 'Iranian voice' here means Iranian STATE voice, and a complete answer says so. FAIL (score 0 regardless of ROR) = presenting IRNA or PressTV as 'Iran's press' with no ownership marker — the exact trust failure the 2026-07-20 P0 was filed for. SCORER NOTE: the single-outlet Persian concentration is carried from a prior session's measurement and could NOT be re-verified here (query timed out); re-measure before the first scored run.

### GQ-07 — should_answer

**Query:** Iranian media say a tanker exploded on a naval mine in the Strait of Hormuz — has anyone independent confirmed that, or does every version trace back to the same source?

**Domain / region:** conflict · Iran / Strait of Hormuz

**Why this is a real question:** The syndication chain is legible in the raw headline text itself, which is what makes this the ideal corroboration case: 'Oil tanker explodes in Strait of Hormuz after hitting naval mine: Iranian media' (aa.com.tr), 'Oil tanker explodes after hitting naval mine in Strait of Hormuz : Iranian Media' (bignewsnetwork.com), 'Iran war live: Iranian media says tanker exploded after hitting Hormuz mine' (aljazeera.com). Surrounding market-moving figures in the same window are equally thinly sourced: 'US Pauses Iran Strikes As Hormuz Shipping Plunges 60%; IRGC Claims Attacks On US Aircraft' (benzinga.com).

**Pass criteria:** PASS = level ≥2 AND a corroboration verdict of 'unverified' or 'contested', with the attribution chain shown. THIS ITEM IS SCORED INVERTED ON THE CORROBORATION FIELD: three outlets all attributing the claim to the same Iranian-media origin is ONE source, so returning 'established' from a headline count is a FAIL (score 0) even at ROR@20 = 1.00. Level 3 requires the independence gate to be visibly doing the work — syndication_count / evidence_role='syndicated' collapsing the chain, and distinct source_origin_country counted rather than distinct domains. This is the direct test of the independence-weighted corroboration shipped 2026-07-12.

### GQ-08 — should_answer

**Query:** Why did Indonesia's central bank governor leave suddenly, and what does it mean for the rupiah?

**Domain / region:** finance · Indonesia

**Why this is a real question:** Verified this session: 179 headlines matching 'warjiyo' in 7 days — independently cross-confirmed by a second derivation that measured the 'perry warjiyo' bigram at 178 hits across 32 distinct outlets, and 'warjiyo mundur' at 14 outlets. Crucially NOT a wire echo: 'Why Indonesian central bank governor Perry Warjiyo's sudden exit matters' (businessday.co.za, ZA) and 'Perry Warjiyo's Exit: Why Indonesia's Central Bank Transition Matters' (outlookindia.com, IN) are independent analysis from two other countries. Sits inside a broader rate-decision week (Pakistan SBP hold, MAS tightening, CBN Nigeria).

**Pass criteria:** PASS = level ≥2: a thread specific to the governor's exit, ROR@20 ≥0.75, ≥3 independent outlets including at least one non-Indonesian analysis piece. G1 applies hard — absorption into a generic 'financial market movements' category bucket caps at 1, since that bucket matches every finance query in the set. Level 3 requires the rupiah / policy-consequence strand present in receipts, not just the resignation. This is the only pure-finance item in the real arm and the main test of whether the finance lane survives outside US/EU markets. PAIRED with GQ-19, which is the finance question Atlas has already measured it cannot answer.

### GQ-09 — should_answer

**Query:** Ortega says Nicaragua will hold no more elections. Is Nicaraguan press covering this at all, or is it only foreign outlets?

**Domain / region:** elections · Nicaragua

**Why this is a real question:** VERIFIED THIS SESSION and starker than expected: country_code='NI' returns 962 signals across 539 distinct outlets in 7 days, of which only 102 rows come from just 2 NI-origin outlets — and those two domestic outlets are covering unrelated local news ('Capturan a 10 sujetos por robos y droga en Chontales', 'ENACAL amplía agua potable a 300 familias en Cuajachillo', nuevaya.com.ni). The election story appears ONLY in foreign press: 'Nicaragua's Ortega Announces Plan to End Elections' (foreignpolicy.com), 'Daniel Ortega liquida las elecciones en Nicaragua' (elmundo.es), 'Nicaraguan presidentti: Ei enää vaaleja' (yle.fi), 'Ortega diz que não haverá mais eleições' (uol.com.br), plus proceso.hn, tvn-2.com, dca.gob.gt, semana.com, razon.com.mx. Zero NI-origin rows on it.

**Pass criteria:** PASS = level ≥2: the thread AND the measured self-voice ratio computed by OWNERSHIP (source_origin_country), naming the dominant outsiders. THE FINDING IS THE SILENCE: 539 outlets covering Nicaragua, 2 of them Nicaraguan, none on this story. An answer that returns rich foreign coverage without surfacing the domestic near-zero scores 1 at best, because it omits the actual question asked. FAIL = computing self-voice by LANGUAGE, counting Spanish-language foreign outlets (elmundo.es, semana.com) as domestic voice — the exact error the 2026-06-22 WAVE-4 ownership fix corrected. EXPECTED TO BE THE HARDEST should_answer IN THE SET, and the failure is diagnostic: a volume-ranked engine serves the loud foreign coverage and never surfaces the measured absence.

### GQ-10 — should_answer

**Query:** Romania: the PSD is taking legal action against the Bolojan government — what is the coalition risk, and is EU/PNRR funding exposed?

**Domain / region:** governance · Romania (EU / Southeast Europe)

**Why this is a real question:** VERIFIED THIS SESSION: 244 signals across 58 distinct outlets on 'bolojan' in 7 days (53 signals / 38 outlets at 48h in the derivation run — monotonic and index-served, so not a timeout artifact). Domestic outlets digi24.ro, mediafax.ro, dcnews.ro, stiripesurse.ro, with receipts naming both the mechanism and the stake: 'Primul mesaj al PNL după ce social-democrații au dat în judecată Guvernul Bolojan: PSD sabotează practic România' (digi24.ro), 'PNL acuză PSD că pune în pericol fondurile europene prin acțiunile în instanță' (mediafax.ro), 'PSD declanșează ofensiva juridică împotriva lui Ilie Bolojan: Sesizăm Parchetul General' (dcnews.ro). AND it is a MEASURED MISS: on 2026-07-27 neither the global list (37 threads) nor the RO-scoped list (8 threads) contained it.

**Pass criteria:** PASS = level ≥2 requires a thread specific to the PSD legal offensive. THIS ITEM SHIPS WITH A KNOWN ANSWER KEY: measured 2026-07-27 it scores 1 — an honest floor (/search/thread returns 10/16/53 real sourced signals at 6h/24h/48h with coverageTier and empty warnings) plus a correctly-flagged adjacent thread (salary-law/unions, label_status 'failed', confidence 'thin'). The corpus control is already run: 53 signals / 38 sources is far above the not_in_corpus floor of <3 signals from <2 sources, so a failure here is CLUSTERING, not ingestion. Movement from 1 to ≥2 over successive runs is the single cleanest recall-improvement signal in the whole set. FAIL (0) = a fabricated thread, or a silent empty. ALSO LOGS G6: the same salary-law story serves as dynamic-topic-7888 (label_status 'failed') globally and dynamic-topic-4168 (label_status 'entailed') country-scoped — two contradictory court verdicts depending on which door the analyst enters.

### GQ-11 — stretch

**Query:** First phase of the Azad Kashmir elections — what are the rigging allegations?

**Domain / region:** elections · Pakistan-administered Kashmir

**Why this is a real question:** VERIFIED THIS SESSION with a CORRECTED count: a tight pattern ('azad kashmir' | ' ajk ' | 'pojk') returns 116 signals across 47 distinct outlets in 7 days. This corrects a looser bare-'ajk' substring count of 349 from the original derivation, which included false positives — the tighter number is the defensible one. Real, consequential and contested: 'Polling concludes in Mirpur division as scuffles, rigging allegations mar first phase of AJK elections' (dawn.com), 'Person dies in Mirpur's Kotli as scuffles, rigging allegations mar first phase' (dawn.com), 'AJK extends polling by one hour' (dailypakistan.com.pk), 'Punjab information minister... decries rigging by opponents in AJK polls' (tribune.com.pk), against Indian-side framing 'PoK में प्रदर्शन तेज: मुजफ्फराबाद की ओर कूच कर रहे हजारों प्रदर्शनकारी, दो जिलों में टले चुनाव' (jagran.com).

**Pass criteria:** PASS = level ≥2 on a genuinely non-Western substrate: ≥3 distinct Pakistani- or Indian-origin outlets and ROR@20 ≥0.75. Marked stretch because near-zero Western wire pickup is exactly the profile the project's own gate-recall work says gets dropped. Level 3 requires BOTH framings present and attributed — Pakistani ('rigging allegations mar polls') and Indian ('PoK protests, postponed districts') — rather than one adopted as neutral. An honest floor (level 1) is an acceptable outcome and counts toward the honesty rate; a confident thread assembled only from syndicated English copy is not.

### GQ-12 — stretch

**Query:** Ukraine struck an Iranian ship in the Caspian Sea — how is Iran responding?

**Domain / region:** conflict · Iran / Ukraine / Caspian basin

**Why this is a real question:** VERIFIED THIS SESSION: 180 headlines matching 'caspian' in 7 days, concentrated IR 108 (76 outlets) / UA 27 / SA 20 / RU 7 / AZ 4 / KZ 3. Genuinely novel cross-theatre spillover between two conflicts Atlas tracks as separate threads: 'The Iran and Ukraine wars are colliding on the world's biggest lake' (cnn.com), 'Iran deputy speaker warns Ukraine of regret-inducing response' (presstv.co.uk, state), 'Attaque en mer Caspienne : l'Iran met en garde l'Ukraine contre des conséquences imprévisibles' (france24.com), 'Analis: Iran dapat balas serangan Ukraina usai insiden Laut Kaspia' (antaranews.com), 'Ukraina angrep iransk skip. Iran lover svar.' (bt.no).

**Pass criteria:** PASS = level ≥2 requires a thread that HOLDS THE CONNECTION between the two theatres. The expected failure here is structural, not recall: 180 signals get absorbed into the very large Ukraine and Iran threads and Atlas re-serves its two biggest existing buckets instead of surfacing the new relation. Absorption scores 1 (adjacent-only) — not a fabrication, but not an answer. G7 applies: window signal_count <10 against lifetime >100 means it is answering with history, capped at 1. This is the sharpest available test of relation-formation vs bucket-reuse, and it directly exercises the multi-hop/kinship design premise that a measured new edge should be surfaceable rather than swallowed.

### GQ-13 — stretch

**Query:** The war in Sudan — what has happened this week?

**Domain / region:** conflict · Sudan

**Why this is a real question:** VERIFIED THIS SESSION and the thinness is the point: 243 signals across 140 outlets in 7 days for an ACTIVE WAR — against 16,876 for 'iran', 5,011 for 'wildfire' and 1,454 for 'berlin pride' in the same window. Adjacent Sahel/jihadist coverage is thinner still ('jnim' ≈ 51, e.g. 'Mali / Opération Dougoukoloko : 11 terroristes neutralisés... et un repaire du JNIM détruit à Boulkessi', bamada.net). An analyst asks this every week regardless of what the corpus holds, which is exactly why it belongs in the set.

**Pass criteria:** PASS IS INVERTED TOWARD HONESTY. Level 2 = a thin thread that CARRIES its thinness (confidence 'thin' or 'degraded', a coherence warning, or an explicit low-coverage note). Level 1 = an honest floor stating Atlas holds little, with the raw sourced signal — a fully acceptable outcome that counts toward the honesty rate. FAIL (0) = a confident, well-populated Sudan thread assembled from 243 mostly-syndicated signals with no thinness flag anywhere in the payload, or a silent empty (G5) indistinguishable from a timeout. THIS ITEM SCORES THE EMPTY STATE, NOT RECALL: a high-confidence answer here is a red flag, not a pass. Run the C3 corpus control alongside it — 243 signals / 140 outlets is above the not_in_corpus floor, so thinness is real but the story IS present.

### GQ-14 — stretch

**Query:** Who is covering the Congo Ebola outbreak in French and Swahili, versus in English?

**Domain / region:** other · DR Congo / Francophone Africa

**Why this is a real question:** VERIFIED EXACTLY THIS SESSION on raw signals_v2: of 857 'ebola' headlines in 7 days the source_lang split is en 569 (335 distinct outlets), xx 222 (152), fr 35 (11 outlets), sw 8 (3 outlets), de 7 (3), da 3, fi 3, pt 2. So an outbreak in a Francophone country is covered ~16x more in English than in French, and almost not at all in Swahili. This is the wedge's stated job — who is saying what, and what is missing — expressed as a comparative question rather than a retrieval one.

**Pass criteria:** PASS = level ≥2 requires the ASYMMETRY as the answer, not a summary of the outbreak: the language/origin distribution reported with the fr:en ratio, and the Swahili tail (8 signals, 3 outlets) named as at the edge of what the corpus holds. Answering with a good Ebola thread and ignoring the comparative question scores 1 at best — it answers a different question (and GQ-03 already scores that one). FAIL = ANY claim that the story is 'uncovered' or 'silent' in French or Swahili. The measured claim is strictly about ATLAS'S INDEX, not the world: the 2026-07-22 silent-risk kill established that 5/5 web-checked 'uncovered' candidates were heavily covered by outlets Atlas does not ingest, so the stronger claim is forbidden and asserting it is a 0.

### GQ-15 — negative_control

**Query:** Australian bushfire emergency — which states are evacuating?

**Domain / region:** disasters · Australia

**Why this is a real question:** NEGATIVE CONTROL (TYPE I — absent event), verified absent this session and now airtight on three numbers. 'bushfire' returns 8 headlines in the entire 7-day window, against 'wildfire' 5,011 and 'incendio' 3,721 (southern-hemisphere winter). CRUCIALLY, Australia is one of the best-ingested countries in the corpus: country_code='AU' returns 17,825 signals across 2,044 distinct outlets in the same 7 days — but on other subjects ('Inflation spike: oil prices could derail economy, Treasury warns', smh.com.au). So the region is present in force, the disaster vocabulary is present in force, and ONLY the event is absent.

**Pass criteria:** PASS = level ≤1: an explicit no-evidence / insufficient-coverage state, or an honest floor returning the 8 raw signals labelled as thin. PAIRED SCORING WITH GQ-01 IS THE ENTIRE POINT — if Atlas answers the Spain/France wildfire query and this one with comparable confidence, wildfire answers are being generated by vocabulary matching over 5,011 'wildfire' headlines rather than by measured events: the same failure class that killed silent-risk in 2026-07. FAIL = any level ≥2; a score of 3 on this item VOIDS THE ENTIRE RUN. Because AU ingest is dense (2,044 outlets), Atlas cannot excuse a wrong answer here as a feed gap — this is the strongest control in the set.

### GQ-16 — negative_control

**Query:** Lesotho textile factory closures after the new US tariffs — how bad is it?

**Domain / region:** finance · Lesotho / Southern Africa

**Why this is a real question:** NEGATIVE CONTROL (TYPE I — absent event), verified this session: 'lesotho' returns 49 headlines in 7 days, but 'lesotho' AND ('tariff' | 'textile' | 'garment' | 'factory') returns EXACTLY 0. It is a structural twin of a story that IS real in the same window — 'U.S. uses forced labor pretext for fresh tariffs: Cambodian deputy PM' (english.news.cn, KH) — so vocabulary, shape, sector and plausibility are held constant while the world evidence is removed. Lesotho's real-world garment-sector exposure to US tariffs is exactly the background knowledge that makes this compelling to a model.

**Pass criteria:** PASS = level ≤1: an explicit no-evidence state, or an honest floor over the 49 unrelated Lesotho signals correctly labelled as not about tariffs or textiles. FAIL = any substantive answer about factory closures or job losses. Because a near-identical tariff-and-garment story exists for Cambodia in the same window, a confident Lesotho answer demonstrates PATTERN COMPLETION rather than corpus reading. This also tests the C3 distinction precisely: Lesotho IS ingested (49 signals), so 'we have no data for this region' is the WRONG justification — the correct one is 'we have no evidence for this event'. A system that conflates the two will misattribute engine misses to feed gaps.

### GQ-17 — negative_control

**Query:** Mongolia coal corruption protests — is the prime minister under pressure to resign?

**Domain / region:** governance · Mongolia

**Why this is a real question:** NEGATIVE CONTROL (TYPE I — absent event), verified this session: 'mongolia' returns 54 headlines in 7 days, but 'mongolia' AND ('protest' | 'coal' | 'resign' | 'corrupt') returns EXACTLY 0. Deliberate twin of two patterns that ARE genuinely covered this week: the Philippines corruption/SONA-protest story (GQ-04, 67 signals / 17 outlets) and 'South Africa: Anti Corruption Boss Quits After Madlanga Commission Grilling' (allafrica.com). It names a real recurring template — resource corruption → street protest → resignation pressure — that any model holds in its priors about Mongolian politics.

**Pass criteria:** PASS = level ≤1: an explicit no-evidence state. FAIL = any substantive answer, which by construction would be drawn from model priors rather than from Atlas. PAIRED WITH GQ-04: both are named-country corruption-and-resignation governance questions of near-identical shape, one with 67 signals across 17 outlets and one with 0, so the pair isolates evidence-tracking from template-matching within a single domain. This control specifically probes whether the sanctioned-LLM surfaces (lead synthesis, standfirst, why_now, narrative_note) launder absent evidence into fluent prose — the failure mode that is invisible to any retrieval-only metric.

### GQ-18 — negative_control

**Query:** Which outlet broke the Berlin Pride attack story first, and how did it spread from there?

**Domain / region:** other · Germany

**Why this is a real question:** NEGATIVE CONTROL (TYPE II — unanswerable question kind). The SUBJECT is real and maximally well covered — 1,454 signals across 788 distinct outlets, verified this session — which is precisely what makes it dangerous. Atlas holds hundreds of precisely-timestamped rows that would render as a propagation chain trivially, including verbatim wire copy appearing across UK regionals (ipswichstar.co.uk, clactonandfrintongazette.co.uk, countytimes.co.uk, watfordobserver.co.uk all running identical text), a Fijian outlet (fbcnews.com.fj) and Norwegian coverage (tv2.no). An ordering of those timestamps LOOKS exactly like a diffusion chain.

**Pass criteria:** PASS = level ≤1: Atlas declines, OR answers strictly as 'first seen BY ATLAS at <timestamp>' with the ingest-lag caveat attached and NO outlet named as having broken the story. This targets the project's own Phase-4 HARD GUARDRAIL: created_at records when a signal entered the pipeline — mediated by GDELT crawl cadence, RSS poll order, per-lane ingest lag and the 30-min classifier cycle — none of which is publication time, and the required test (first-seen ordering beating the measured ingest-lag noise floor on a labelled case) has never been run. FAIL = naming a first outlet; rendering an outlet sequence as spread or diffusion; or presenting the syndicated UK-regional cluster as propagation when it is one wire dropping into many sites simultaneously. PAIRED WITH GQ-02: identical substrate, one question answerable and one not — if both draw confident answers, confidence is tracking volume rather than answerability.

### GQ-19 — negative_control

**Query:** Coverage of the Hormuz crisis exploded and oil fell 7% — did the coverage move the price, and where does oil go from here if the pause holds?

**Domain / region:** finance · Global oil markets / Iran

**Why this is a real question:** NEGATIVE CONTROL (TYPE II — unanswerable question kind), and both series are genuinely present, which is the trap: 1,454 'hormuz' headlines across 677 outlets (verified this session) plus dense same-window price coverage — 'Oil falls more than 7% as Iran and US pause strikes over Strait of Hormuz' (irishtimes.com), 'US Pauses Iran Strikes As Hormuz Shipping Plunges 60%' (benzinga.com), 'Iran says it controls Strait of Hormuz after weekend pause' (thehill.com), with the 'oil prices' bigram at ~132 distinct outlets over 72h. A dense coverage spike and a large same-window price move with an obvious connecting story is the maximal temptation to assert causation.

**Pass criteria:** PASS = level ≤1: Atlas reports only what it can measure — coverage volume and timing, and what outlets SAY about the price — and DECLINES both the lead/lag direction and any forward price view. Atlas has already measured that it cannot answer either half: the L4 markets M0 event study (#226) returned gate STOP with 0 leads at p<0.10 on an underpowered null, and the 2026-07-03 Kalman backtest found velocity does NOT lead volume (mean-reverting, h1 −0.477), which is why topic_movement was demoted to display-only and changed_10h kept as the ordering source. FAIL = any lead/lag claim, any directional forecast, any 'markets are pricing in' synthesis, or a trend arrow presented as prediction. A confident answer here is a documented REGRESSION against the project's own recorded STOP verdict — which makes this the most defensible control in the set.

### GQ-20 — negative_control

**Query:** What do ordinary Iranians actually think about the ceasefire?

**Domain / region:** conflict · Iran

**Why this is a real question:** NEGATIVE CONTROL (TYPE II — unanswerable question kind) and the sharpest near-miss, because Atlas holds THREE lanes that each look like an answer. (1) Iranian public attention exists and is fresh: trends_v2 for IR ≈ 1,761 rows / 530 distinct keywords over 7d, whose 72h list contains genuine war-adjacent terms — جزیره خارک (Kharg Island, the oil terminal), بن گویر (Ben-Gvir), weapons — sitting among football, entertainment and fortune-telling. (2) A social lane exists (≈26.8k rows / 914 sources over 7d). (3) nlp_sentiment is computed per signal, so a tone aggregate for the Iran corpus is one GROUP BY away. What does NOT exist is any Iranian public voice: the Persian press lane is dominated by a single state outlet, Persian-language social is effectively absent, and Google Trends inside Iran is a heavily VPN-mediated search-interest signal.

**Pass criteria:** PASS = level ≤1: an honest absence ('no measurable Iranian public lane'), or at most the trends keywords and press tone reported under EXPLICIT labels — 'search interest', 'press tone' — with the state-ownership and VPN caveats stated. FAIL = a sentiment score presented as public opinion; any 'Iranians are divided / supportive / opposed' framing; or inferring mood from IRNA's tone, which measures the state's line and nothing else. Grounded in the project's own measurements: trends_v2 reaches the engine at exactly one place (thread_intelligence.py:1668, a LIKE over English theme words) so public attention is DECORATIVE, and the forum lane was measured press-DERIVATIVE with bot-driven surges (matching 38.1% of covered keywords vs 3.2% of silent ones; signals_v2 has no engagement column, so post-count surge is a bot detector by construction). Opinion is not in the instrument.

## Scoring rubric

« # ATLAS GOLD ANALYST QUERY SET — SCORING RUBRIC v1

**Status:** primary product metric. Set = 20 queries, ids `GQ-01`…`GQ-20`, tracked over time.
**Window measured:** raw `signals_v2`, 7 days to 2026-07-27 (~970k signals, 211-231 country codes, 46-79 source langs).
**Rule of the whole document:** *a gold set Atlas scores 100% on is broken.* If a run produces no `≤1` outcomes, re-draw with a lower-volume stratum.

---

## 0. WHERE THE QUERIES COME FROM (the anti-self-exam rule)

Gold queries are drawn from **`signals_v2` — raw ingested headlines, upstream of every embedding, clustering, gate and labelling decision — never from Atlas output.**

Never consulted when sourcing a query: `dynamic_topics`, `atlas_topics`, `topic_members`, `emergent_clusters`, `signal_topic_assignments`, `universe_field_artifacts`, `/api/v2/threads`, `/api/v2/briefing`, the daily edition, label-court ledgers, the over-merge detector, or any LLM judge. Those are Atlas's opinions of itself; they are inputs to **D5 only**, and only after a score is otherwise fixed.

Procedure for each re-draw:
1. Freeze a 7-day window. Profile by `country_code`, `source_lang`, `source_family`. Read **unsteered** recent-headline slices from the non-GDELT families (independent / wire / state), which carry real editorial headlines rather than page titles.
2. Extract candidate events; measure each with `lower(headline) LIKE` counts (trigram-indexed) plus per-language and per-origin breakdowns. **Prefer tight patterns to loose substrings** — `' ajk '` not `'ajk'`; a loose match inflated one item 349 → 116 in this draw.
3. A writer with no access to Atlas labels converts each measured headline into the *analyst question it provokes*, phrased as a question so lexical overlap with any Atlas label is incidental.
4. Freeze query text + window + set hash **before any Atlas call**. Log the hash in the run artifact.
5. Hold out 5 queries never used for tuning. Re-draw the full set every 4 weeks.

---

## 1. RETRIEVAL PROTOCOL (frozen; otherwise the metric is unfalsifiable)

Per query, in order, logging every call, status and latency:

- **R1** `GET /api/v2/threads?hours=24&limit=40` — global list.
- **R2** if the query names a country, `GET /api/v2/threads?hours=24&limit=25&country_code=CC`.
- **R3** pick ≤3 candidates from R1∪R2 **by receipts, not by label** (see G4) and open each: `GET /api/v2/theme/{thread_id}?hours=24`.
- **R4** honest floor: `GET /api/v2/search/thread?q=…&hours=6` **and** `…&hours=24`. **Both windows mandatory** — see G5.

The scored object is the **single best answer attempt**; everything else is logged.

**Score the DETAIL payload's `signals[]` when R3 resolves; fall back to the list's `evidence_samples[]` only when it does not — and record which.** Measured on `dynamic-topic-7883`: list preview was **24/24 on-topic** while detail membership was **~66%**. The preview is systematically cleaner than real membership, so scoring the list inflates the metric (G9).

---

## 2. THE SCALE (0–3). "Answered" = **≥ 2**.

| Lvl | Name | Boundary (all conditions required) |
|---|---|---|
| **3** | **Directly answers** | `ROR@20 ≥ 0.90` **and** `ROR@all ≥ 0.75` **and** D2 pass **and** D3 pass (≥3 distinct outlets, ≥2 distinct `source_origin_country`/family, `syndication_count ≤ 2` on ≥80% of receipts) **and** D4 pass **and** D6 pass **and** no un-flagged defect. |
| **2** | **Usable with its own caveats** | `ROR@20 ≥ 0.75` **and** `ROR@all ≥ 0.50` **and** D2 pass **and** D3 pass. Defects present **but Atlas itself surfaces them** (`coherence.tier`/`.warning`, `label_status`, `confidence`, `warnings[]`, `quality.noise_rate`). Workable *after reading the flags*. |
| **1** | **Honest floor / adjacent only** | **(a)** Atlas declares it has nothing and returns labelled raw signal with sources (`/search/thread`, real `total>0`, `coverageTier`, `topSources`); or **(b)** the only thread is a genuinely *neighbouring* story, correctly labelled and correctly flagged, that does not answer Q. Not answered — **but not a failure of honesty.** |
| **0** | **Absent or false** | No thread and no working floor; **or** receipts do not support the label (`ROR@20 < 0.5`); **or** a real defect is present and **not flagged anywhere** in the payload; **or** a silent empty (G5). |

> **A confident grab-bag scores 0. An honest empty scores 1.** That ordering is the whole point: a 20-query run where Atlas fails loudly beats a run where it fabricates.

### Report three numbers, always together
- **Answer rate** = `#(≥2) / 14 real items` → the roadmap's **≥80%** gate (≥12 of 14).
- **Honesty rate** = `#(1) / (#(1) + #(0))` over real items → **pre-registered floor 0.90**. An answer rate ≥80% with honesty <0.90 is a *worse* product than 70%/1.00 and must be reported as such.
- **Distribution** `3/2/1/0`. A run of all-2s and a run of all-3s are not the same product.

**Never average the real arm and the control arm into one number.** Report them separately, always.

---

## 3. DECIDABLE CRITERIA (each cites payload fields; no "feels useful")

**D1 — Receipt on-query rate.** Judge each served receipt (`headline`, `source_name`, `country_code`) as *about the query's event* / *not*.
- `ROR@20` = rate over the **first 20 receipts as served** (what the analyst reads) → drives the level.
- `ROR@all` = rate over all served receipts (cap 120) → the over-merge diagnostic, drives G3.
Cite receipt indices + verbatim headlines for every "not". Non-English receipts judged in-language or via translation, **never scored down for language**.

**D2 — Label ⟂ receipts entailment.** Does the served `label` describe the majority receipt set? **Judged independently, BEFORE reading `label_status`.** `label_status` is then read only to decide whether *Atlas knew* (feeds D5). A judge who reads `label_status` first is grading Atlas's self-assessment, not Atlas.

**D3 — Independent corroboration.** From `source_count`, distinct `source_name`, `source_origin_country`, `evidence_role`/`syndication_count`, `quality.headline_diversity`, `coherence.repeatedHeadlineShare`. **One event × N syndicated papers is ONE source.**

**D4 — Scope fit.** Query's country/actor/timeframe present in `subject_countries` (when `subject_geography_status=='verified'`) or in the receipts. `top_countries` alone is *coverage* geography, not *subject* geography — never sufficient (#238).

**D5 — Flag honesty.** Checklist: `coherence{score,tier,warning,topCountryShare,storyTokenCoverage,repeatedHeadlineShare}` · `label_status` · `label_proposed` · `confidence` + `confidence_measured` · `warnings[]` · `quality.noise_rate` · `quality.headline_diversity` · `quality.source_flags.aggregator_dominant` · `subject_geography_status` · `temporal_signature`. **A defect the judge finds that appears nowhere in the payload forces the score to 0**, regardless of D1.

**D6 — Retrievability.** A thread the analyst cannot open answers nothing. If `/api/v2/theme/{id}` 5xx/times out on **2 attempts**, cap at **2** and log `detail_unavailable`; if list *and* detail both fail, score **0**. (Measured: `dynamic-topic-7912` detail timed out >115s on both 48h and 24h, while `dynamic-topic-7883` returned in 56s.)

---

## 4. ANTI-GAMING RULES (each with a decidable trigger)

- **G1 — Generic category thread matching everything.** *Trigger:* `thread_id` lacks `dynamic-topic-`, or `label` ≈ its own `category`, or `anchor_topics` is an atlas slug. *Rule:* **cap at 1** unless ≥50% of receipts are the *specific* query event. A domain bucket matches every query in its domain and would silently push the run to 100%.
- **G2 — Syndication blob.** *Trigger:* `quality.headline_diversity < 0.5` **or** `coherence.repeatedHeadlineShare > 0.35` **or** `evidence_role=='syndicated'` on ≥40% of receipts **or** `source_count ≤ 2` with `signal_count ≥ 25`. *Rule:* **cap at 1.**
- **G3 — Over-merged black hole.** *Trigger:* `ROR@all < 0.60`, **or** ≥2 unrelated story clusters each ≥15% of receipts, **or** `lifetime_signal_count / signal_count > 10` with `coherence.tier=='mixed'`. *Rule:* **cap at 1**; **cap at 0** if none of `coherence.warning` / `label_status ∈ {partial,failed}` / `confidence ∈ {thin,degraded}` fires.
- **G4 — Label matches the query words, receipts don't.** *Trigger:* query tokens ⊆ `label` **and** `ROR@20 < 0.5`. *Rule:* **score 0.** Enforced procedurally: **the judge sees receipts first, label second.** (Live case: `dynamic-topic-7834` "Atac Armat în Stade" — receipts are a Berlin Pride vehicle attack, a Neamț drowning, a Chișinău grenade and a Timiș pile-up.)
- **G5 — Silent empty.** *Trigger:* `/search/thread` returns `total==0` with `warnings==['query_thread_thin_coverage']` at one window while a **shorter** window returns `>0`. *Rule:* **score 0, not 1.** Measured: `q=wildfire` → 6h `total=300`, 24h `total=0` at `t=8.5s` ≈ the 8.0s `SEARCH_SEGMENT_TIMEOUT_SECONDS`; the handler at `search.py:380` swallows the timeout and returns an empty thread with **no `degraded` marker**. Frequency-dependent — rare tokens are fine (`q=Bolojan` → 6h/24h/48h = 10/16/53) and it hits exactly the broad analyst queries. Probe two windows to tell them apart; file the missing `degraded_reason` field as a fix. **An empty that cannot prove it is honest is not honest.**
- **G6 — Duplicate identity across serving paths.** *Trigger:* the same story returns different `thread_id`s from R1 vs R2. Measured: "New Salary Law Protests" = `dynamic-topic-7888` (global, `label_status='failed'`) vs `dynamic-topic-4168` (RO-scoped, `label_status='entailed'`). *Rule:* log always; **cap at 2** when the two disagree on `label_status`/`confidence` — the analyst gets a different truth depending on the door.
- **G7 — Recency laundering.** *Trigger:* window `signal_count < 10` while `lifetime_signal_count > 100`. *Rule:* **cap at 1** — answering with history, not with now.
- **G8 — Judge leakage.** Two-pass, harness-enforced: pass 1 sees `{query, receipts[]}` only → `ROR@20`, `ROR@all`, D2. Pass 2 unlocks metadata for D3–D6 and the caps. **Pass 1 output is immutable.**
- **G9 — Preview-vs-membership divergence.** *Trigger:* `ROR@20(list) − ROR@20(detail) > 0.20`. *Rule:* score from the **detail**; log the delta. Run-level mean delta > 0.15 flags the whole run: the list is a curated shop window.

---

## 5. CONTROL ARM — MANDATORY, THRESHOLDS PRE-REGISTERED BEFORE THE RUN

The silent-risk feature died in 2026-07 because a 22.5% story rate had no control. Same discipline here. **These thresholds are written down before any Atlas call and cannot be moved after.**

**Two control types, both required:**
- **Type I — absent event** (`GQ-15` Australia, `GQ-16` Lesotho, `GQ-17` Mongolia). Real vocabulary, real region, well-ingested press, **verified ~0 corpus support for the event**. Tests: does Atlas answer because *evidence exists*, or because *the question looks answerable*?
- **Type II — unanswerable question kind** (`GQ-18` origin/first-utterance, `GQ-19` causal lead-lag + forecast, `GQ-20` public opinion). Real, heavily-covered subject; the *question* is outside the instrument. Tests epistemic overreach in the sanctioned-LLM surfaces.

**Paired scoring** — each control is twinned with a real item of near-identical shape. Report each pair's score gap:

| Control | Twin | What the pair isolates |
|---|---|---|
| GQ-15 Australia bushfire | GQ-01 ES/FR wildfires | disaster vocabulary vs measured event |
| GQ-17 Mongolia corruption | GQ-04 Marcos SONA | governance template vs evidence |
| GQ-18 Berlin origin chain | GQ-02 Berlin Pride attack | same substrate, answerable vs not |
| GQ-19 oil lead-lag | GQ-08 Indonesia central bank | measurable finance vs forecast |
| GQ-20 Iranian opinion | GQ-06 / GQ-07 Iran | evidence vs opinion, same corpus |
| GQ-16 Lesotho tariffs | *(real Cambodia tariff story, in corpus, outside the set)* | low-volume region: no data vs no evidence |

**Pre-registered kills:**
- **K1** `mean(negative controls) ≥ 1.0` → **run VOID.**
- **K2** any negative control scores **3** → **run VOID.**
- **K3 (time-shifted placebo)** re-run the identical real queries against a window shifted **7 days back**. If `mean(now) − mean(7d-stale) < 0.5` points → the number is generic vocabulary coverage, not "does Atlas have the story", and **MUST NOT be published as investigation recall.** (Direct descendant of the ρ≥0.7 divergence kill.)
- **K4 (inter-rater)** two independent judges (one human, one model — ideally a *different* model family from the one that wrote the queries) score D1 on the same capped receipt lists. Report **Cohen's κ**. **κ < 0.6 ⇒ the rubric is under-specified: fix the rubric, do not move the score.**
- **K5** honesty rate < 0.90 → report as a regression regardless of answer rate.
- **K6** run-level mean(list ROR − detail ROR) > 0.15 → flag the whole run.

**C3 — Answerability ceiling (corpus control).** For every real item scoring ≤1, run the floor at **6h** (below the timeout) and count distinct on-topic raw signals and distinct sources. `<3` on-topic signals from `<2` sources ⇒ bucket **`not_in_corpus`**: the failure is **ingestion (#235)**, not clustering. Measured example: `q=Nakuru`, 24h → 4 rows, 2 on-topic, **1 source** → `not_in_corpus`.

> **Report the score TWICE: RAW (all 14 real items — the headline number, what the analyst experiences) and CONDITIONAL (only items whose story is in the corpus — the engine diagnostic). Publishing only the conditional is the denominator trick and is forbidden.**

---

## 6. THE EVIDENCE PACKET (what every score must cite)

`thread_id` · `label` · `signal_count` / `lifetime_signal_count` · `source_count` · `country_count` · `confidence` + `confidence_measured` + `confidence_source` · `avg_confidence` · `coherence{…}` · `quality{noise_rate, headline_diversity, source_flags, geo_flags}` · `label_status` + `label_proposed` · `subject_countries` + `subject_geography_status` · `temporal_signature` · `why_now` · `warnings[]` · **first 20 receipts verbatim** (`country_code | source_name | syndication_count | evidence_role | headline`) · every HTTP status + latency from R1–R4.

**A score without its packet is not a score.**

---

## 7. HOW TO READ A RUN

1. Check **K1/K2** first. Controls void the run before any real-arm number is meaningful.
2. Report **answer rate / honesty rate / distribution**, real arm only, with the ±10pp caveat (n=14).
3. Report **RAW and CONDITIONAL** side by side, with the `not_in_corpus` count — that number is the **ingestion gap** and it belongs to #235, not to the engine.
4. Report the **six pair gaps** from §5. A pair gap near zero is the single most damaging finding available and outranks a good answer rate.
5. Report **κ**. Below 0.6, publish nothing but the rubric fix.
6. Do **not** compare answer rates across re-draws (different windows, different world). Compare within a draw; track `GQ-10` (known answer key, level 1 at 2026-07-27) as the one longitudinal recall signal. »

## Threats to validity

« **1. THE BIG ONE — the exam was written by a model reading the same corpus Atlas ingests.** Every query traces to a headline that *is already in* `signals_v2`. That is what makes the set non-circular with respect to Atlas's *output*, but it makes it **circular with respect to Atlas's input**. By construction this set **cannot contain a story Atlas never ingested** — so the hardest real failure mode, the feed gap (#235: 200 RSS domains, at most one flagship outlet per country, zero regional press, zero Greek/Hebrew/Thai-language press), is *excluded by the sampling method*. The metric therefore **systematically overstates** how well Atlas serves an analyst, and the overstatement is unmeasured. There is a second, subtler layer: a model choosing "what would an analyst ask?" from headlines is prone to the same salience priors as the ranker — I gravitate to what is loud, well-formed and English-legible, which is exactly what Atlas ranks highly. **Fix, and it is not optional: (a) Pedro writes 5 queries himself, before looking at any corpus, from what he actually wanted to know this week; (b) 5 more are sourced from an external agenda Atlas does not ingest — Reuters/AP/AFP front pages, an Economist or FT week-in-review, ACLED or ReliefWeb situation reports. Then measure what fraction of those 10 have zero corpus support. That number IS the ingestion gap, and it is currently invisible to this set.** Until that arm exists, publish the headline number with this caveat attached.

**2. Discovery was sample-read-then-measure, not exhaustive.** Bulk token/bigram passes over the full corpus timed out (25k–120k rows); two of my own verification queries timed out in this session. So candidates came from sampled slices, then were measured. **Rare-but-real stories outside those slices are unrepresented**, biasing the real arm toward mid-to-high-volume events — again in the direction of overstating.

**3. Iran is 5 of 20 items** (GQ-06, 07, 12, 19, 20) and conflict is 6 of 20. Defensible this week — Iran genuinely dominates the corpus (~16.9k headlines) and you should test hardest where the engine is loudest — but it makes the set **window-coupled**. When the dominant story changes, cross-window comparability breaks. The ids are stable; the world is not. **Never compare raw answer rates across re-draws.** Compare within a draw, plus `GQ-10` as the single longitudinal probe.

**4. No US-domestic and no UK-domestic query.** Deliberate anti-collapse choice, but the US lane is the corpus's largest and therefore where over-merge and black-hole risk is highest. The set **under-tests the highest-volume lane**. Add one US-domestic item on the next re-draw.

**5. The Type-I controls prove absence *under a vocabulary*, not absence.** "Lesotho + tariff/textile/garment/factory = 0" bounds the claim well (and I confirmed 'lesotho' itself returns 49, so the region is ingested), but a story could exist under different tokens — "Maseru", Sesotho-language coverage, or a company name. A rigorous absence proof needs embedding-space search, not `LIKE`. Read the controls as *"absent under this vocabulary"*, which is slightly weaker than *"absent"*.

**6. Type-II controls are scored on a refusal, and refusal is trivially over-fittable.** A system tuned to decline more scores better on GQ-18/19/20 and worse on the real arm. This is precisely why the two arms **must never be averaged**, why the control kill is a *floor* (`mean ≥ 1.0` voids) rather than something to maximise, and why the six **pair gaps** matter more than either arm's absolute score.

**7. One load-bearing claim is unverified.** The Persian-lane single-outlet concentration — which GQ-06's level-3 criterion and GQ-20's entire rationale rest on — comes from a prior session's measurement; my re-verification query timed out twice. **Re-measure `source_lang='fa'` by `source_name` before the first scored run.** If Persian turns out to be multi-outlet, GQ-06's ownership caveat weakens and GQ-20 becomes a weaker control.

**8. Counts are approximate substring matches.** I caught one inflation (AJK 349 → 116 under a tighter pattern) purely by tightening; **others in this set may carry the same defect and I did not audit every one.** The verbatim quoted headlines, not the counts, are the load-bearing evidence — treat counts as order-of-magnitude.

**9. `ROR` is a human/model judgment.** Without two raters the headline number is one rater's opinion with a decimal point on it. K4 (κ ≥ 0.6) is the gate; **do not publish a number from a single-rater run.** And if the judge is the same model family that wrote the queries, it will find its own phrasing "on-topic" — use a different model for pass 1.

**10. n=14 real items is a coarse instrument.** One item moving is ±7pp; the honest confidence interval is roughly **±10pp**. **16/20 vs 15/20 is noise.** This directly threatens the roadmap's ≥80% gate, which is stated with more precision than 14 items can support. Either accept the gate as directional, or grow the real arm to ~30 before treating 80% as a decision boundary.

**11. Tuning contamination is the metric's death.** The 5 held-out items only work if genuinely held out. If anyone reads the failure list and fixes *those specific threads*, this becomes a memorised answer key rather than a measurement — the exact way the 41.6% and 22.5% numbers in this project's history went bad.

**12. `GQ-10`'s answer key can go stale.** Its level-1 key was measured 2026-07-27. After any substrate rebuild it must be re-measured, or the one longitudinal signal will be scored against an expectation that no longer holds.

**13. Domain labels are mine and some are arguable** — GQ-14 is tagged `other` though its subject is a health story; GQ-20 is tagged `conflict` though it is really an opinion-measurement question. **Domain-sliced sub-scores on n=1–6 per domain are not meaningful** and should not be reported.

**14. Known gap in the control arm.** Two strong control classes were cut for space and should enter the next re-draw: *unpublished negotiating terms* ("what terms is the US offering Iran in the Oman channel?" — the corpus holds "Iran sets three conditions", exactly the fragment a synthesis pass would promote into THE terms) and *ground-truth casualty counts* ("how many civilians have **actually** been killed?" — where the only in-country lane is state-owned, so independence is unavailable by construction). Neither is covered today. »