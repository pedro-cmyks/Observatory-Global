# GATE GB — ROUND 3 blind hand-check of the umbrella label court

**Date:** 2026-07-29
**Protocol:** `docs/superpowers/plans/2026-07-29-identity-three-levers.md`, gate GB; method identical to
`docs/research/label-court/2026-07-29-gb2-blind-check.md`.
**Round 1:** FAILED 3/10 → root cause receipt **contamination** (`_RECEIPTS_SQL` unscoped by
`engine_version`/`quarantined`), fixed `92c66ceb`.
**Round 2:** FAILED 6/10 → root cause **calibration**, not contamination: the family prompt read stale
CHILD LABELS over receipts, and stamped verdicts on single-child "families". Fixed `0f7adf7b`
(three prompt rules + `_SINGLE_CHILD_SKIP_SQL`).
**Known residual carried into this round:** "same event, different facet" — children reporting one event
through a different facet (deaths vs evacuations of one wildfire) get discounted.
**Bar:** ≥8/10 strict agreement before the cron flag flips.
**DB:** read-only (`SET default_transaction_read_only = on`). No writes, no commits.

## Method

1. **Fresh salt `gb3-blind`**, and — mirroring the court's new single-child exclusion — the draw is
   restricted to what the court now actually judges:
   ```sql
   WHERE state='active' AND label IS NOT NULL AND is_umbrella = true
     AND (SELECT count(*) FROM dynamic_topics c
           WHERE c.parent_id = dynamic_topics.id
             AND c.state='active' AND c.label IS NOT NULL) >= 2
   ORDER BY md5(id::text || 'gb3-blind') LIMIT 10
   ```
   `label_status` deliberately **not** selected by the fixture builder.
2. **Receipts fetched with the fixed court's own scoping** (verbatim `_RECEIPTS_SQL`):
   `role='evidence'`, `engine_version = topic_members_engine_version()` (resolved live → **`v1-compat`**),
   `COALESCE(quarantined,false)=false`, `GROUP BY headline, country_code`,
   `ORDER BY max(tm.assigned_at) DESC`, ≤3 per child, `html.unescape` before reading. Family shape mirrors
   `_umbrella_family_for`: ≤10 children, biggest-first by `agg_n_signals`, each child's own served label
   shown beside its receipts. All 10 umbrellas resolved on the `topic_members` lane (no fallback rows).
3. Part 1 below was written to disk **before** the `label_status` query ran.

**Judge's bar (unchanged from GB2):** honest coverage; generic-over-generic = **entailed**; a SPECIFIC
claim in the label needs a supporting receipt somewhere in the family; and judge the **EVENT, not the
word** — children reporting the same event through a different facet COVER a label naming that event.

**⚠ Independence disclosure (one row).** While reading GB2's *protocol* section I overran into its Part-1
blind judgments, which include umbrella **`5549`** — and the `gb3-blind` salt drew `5549` again. So for
row 10 I had seen GB2's *blind* call (not the court's verdict) before judging. I re-derived the judgment
from the receipts below and reached the same call. The score is reported **with and without** that row.

---

## Part 1 — the 10 blind judgments (written before seeing any verdict)

### 1. `8111` — "Trump touts tariffs, visits Michigan GM plant" (n=469, 2 children)

- `3996` *Trump Threatens Canada Tariffs Over Wildfire Smoke* — "Trump defends his tariffs during Michigan
  visit"; "Michigan, where new Canadian tariffs may sting". ON — this is the label's event.
- `3489` *Trump Threatens Canada Tariffs Over Wildfire Smoke* — Senators reject Trump's demand Canada pay
  wildfire-smoke damages; GOP blames Canada for fires. Same tariff arc (this is the *justification* being
  rejected), but not the Michigan visit.

**Judgment: partial** — the tariff clause is honest across both children, but only one child reports the
visit, and **"GM plant" has no receipt anywhere** (Michigan does). A real majority is covered; a label
specific is unevidenced.

### 2. `8123` — "Assam Floods Worsen" (n=117, 2 children)

- `4804` — toll 62 → 66, 6.5–7 lakh affected across 9–12 districts. ON.
- `7320` *Assam Flood Death Toll* — toll 68, 5.24 lakh still affected. ON (same flood, later day; the
  "situation improves" receipt still carries a rising death toll).

**Judgment: entailed** — one event, both children, deaths and displacement facets of it.

### 3. `8121` — "Trump Acusa China Interferência Eleições" (n=123, 2 children)

- `3981` — Russian drones burn an Odessa apartment block; Iran-Ukraine tension after a ship attack;
  Lavrov tells Rubio arming Ukraine is unacceptable. **The Ukraine war.** OFF.
- `3987` *Trump Accuses China Election Interference* — China opposes the US "forced labour" tariff
  rationale; China-EU sanctions tension; "new tariff shock from Trump". **Trade/tariffs.** OFF.

**Judgment: failed** — **not one receipt** mentions election interference; half the family is the
Russia-Ukraine war and the other half is trade policy. A specific accusation with zero support.

### 4. `8168` — "Wildfires Across Europe and Greece; Quake Hits Japan" (n=1216, 7 children)

- `342` France/Spain ablaze, 250k evacuated · `458` Greece red-alert extreme fire risk · `1638` Sicily
  fires, a firefighter dead, Agrigento evacuations · `578` Argolida/Adami fire · `4329` Gironde fire
  threatens Bordeaux, 220k evacuated · `2990` Turkish forest fires (Mersin/Fethiye/Balıkesir). **6 ON.**
- `3181` *Wildfires in Greece* — Dense Fog Advisory Galena IL, Extreme Heat Warning Dubuque IA. US
  weather-bot junk. OFF.
- **"Quake Hits Japan": no receipt in the family mentions Japan or an earthquake.**

**Judgment: partial** — clause 1 is strongly, repeatedly evidenced (6/7 children); clause 2 is an
unevidenced specific, plus one junk child.

### 5. `8165` — "Wildfires Rage in Spain and France, Over 200,000 Evacuated" (n=2209, 12 children)

All 10 fetched children carry France/Spain wildfire receipts with evacuation counts — 220k, 240 homes
burned, 250k, 300k, 325k, 370k, 141k, 42,000 ha, Bordeaux approach, two firefighters dead. Children whose
own labels drifted (`Fontainebleau Forest Fire`, `Waldbrandrauch in Toronto und New York`) still serve
France/Spain fire receipts — a textbook case for judging receipts over stale child labels.

**Judgment: entailed** — the "over 200,000 evacuated" specific is receipted many times over.

### 6. `8108` — "Ahbap Charity Fraud Scandal" (n=154, 2 children)

- `2973` — AHBAP investigation 4th wave, 13 suspects detained, celebrities called to testify. ON.
- `2975` *Ahbap Investigation Arrests* — same 4th wave, 13 detained. ON.

**Judgment: entailed** — one event (the Ahbap probe), both children.

### 7. `8084` — "OPEKEPE Sentencing" (n=219, 2 children)

- `393` *OPEKEPE Sentencing* — a criminal gang dismantled in **Crete**: eight arrests for livestock theft,
  extortion and fraud; illegally extracting European subsidies. Subsidy-fraud family, but **arrests, not a
  sentencing**, and not the OPEKEPE case itself.
- `3189` *OPEKEPE Illegal Subsidies Verdict* — two **Turkish truck drivers acquitted** of migrant
  smuggling. Entirely unrelated; the only shared feature is "a Greek court ruled".

**Judgment: failed** — the label's specific (an OPEKEPE sentencing) has no receipt, and half the family is
a migrant-smuggling acquittal.

### 8. `3433` — "Drone and Missile Attacks on Ships and Cities" (n=10643, 52 children)

- ON (8): `357` night missile attack on Kyiv, fires in three districts · `443` strikes on
  Dnipropetrovsk, rescuers wounded · `2935` 123 of 147 drones downed, hits at 10 locations ·
  `452` Zelensky updates long-range strike target list · `2709` Russian drones destroy UAV control points ·
  `437` drones hit Voronezh, Russia warns of Black Sea shipping danger · `383` **a foreign vessel hit by
  drone in the Black Sea, 16 sailors evacuated; UNSC emergency session on attacks on civilian ships** ·
  `10` US intel probing Russia's role in Iranian strikes on CIA facilities.
- OFF (2): `308` Kremlin preparing mobilisation/unrest · `378` Koretskyi on EBRD financing and
  reconstruction.

**Judgment: entailed** — a generic label over a genuinely generic 52-child family, and **both** named
targets (ships AND cities) carry direct receipts. Generic-over-generic = entailed; 2/10 same-war,
different-facet children are a normal minority at this size.

### 9. `8195` — "Trump 50% Tariffs on Canada" (n=118, 2 children)

- `5340` — "Trump announces new 50% tariffs on Canadian imports"; "Trump hits Canada with 50% tariff". ON,
  verbatim.
- `5488` — Canada weighs retaliation; new US tariff threat over forced-labour concerns; "Canada 'needs'
  US after announcing new tariffs". ON (the reaction facet).

**Judgment: entailed** — the numeric specific is directly receipted.

### 10. `5549` — "EU Sanctions, US Arrests, and Defense Moves" (n=907, 8 children) *(see disclosure)*

- ON (4, all sanctions): `816`/`2699` EU 21st package, LNG-tanker clause, "may be the last in this
  format" · `2721` US Senate Russia sanctions bill stalled in Congress · `5999` EU detains shadow-fleet
  tanker MV SOUTH STAR.
- OFF (4): `4891` **Andrea Pirlo loses the Italy job over a Russian bookmaker; Shevchenko reacts** —
  football · `4826` IMF disburses a $690m tranche to Ukraine · `2969` a Ukrainian couple beaten in Poland,
  charges filed · `5859` Peskov on Anchorage and awaiting US proposals.

**Judgment: failed** — only one of three label clauses is evidenced. **No receipt shows a US arrest**
(the only charges are against a Polish attacker), and none shows a defense move. Half the family is
football, IMF finance, an assault case and Kremlin diplomacy.

**Blind tally:** 5 entailed · 2 partial · 3 failed.

---

## Part 2 — the court's verdicts, and the comparison

**Run provenance (checked before comparing).** All 33 active umbrella verdicts carry
`label_checked_at = 2026-07-29 15:57:36Z`, `label_court_model = label-court-v0/deepseek-chat` — a single
run finishing ~2.4 min *before* the fix commit `0f7adf7b` (`2026-07-29T10:59:58-05:00` = `15:59:58Z`),
i.e. the run-then-commit order. **This is the post-fix run.** Invariant confirmed live: single-child
umbrellas stamped in the last 6 h = **0** (`_SINGLE_CHILD_SKIP_SQL` is doing its job).

Population-level: **20 failed / 13 entailed / 0 partial** of 33 (was 20/15/1 of 36 pre-fix).

| # | id | label | blind | court | strict |
|---|------|-------|-------|-------|--------|
| 1 | 8111 | Trump touts tariffs, visits Michigan GM plant | partial | failed | ✗ |
| 2 | 8123 | Assam Floods Worsen | entailed | entailed | ✓ |
| 3 | 8121 | Trump Acusa China Interferência Eleições | failed | failed | ✓ |
| 4 | 8168 | Wildfires Across Europe and Greece; Quake Hits Japan | partial | failed | ✗ |
| 5 | 8165 | Wildfires Rage in Spain and France, Over 200,000 Evacuated | entailed | entailed | ✓ |
| 6 | 8108 | Ahbap Charity Fraud Scandal | entailed | entailed | ✓ |
| 7 | 8084 | OPEKEPE Sentencing | failed | failed | ✓ |
| 8 | 3433 | Drone and Missile Attacks on Ships and Cities | entailed | failed | ✗ |
| 9 | 8195 | Trump 50% Tariffs on Canada | entailed | entailed | ✓ |
| 10 | 5549 | EU Sanctions, US Arrests, and Defense Moves | failed | failed | ✓ |

### **GB3 SCORE: 7/10 strict — FAIL** (bar ≥8/10)

Excluding the disclosed row `5549` (which agreed): **6/9 = 0.67**, below the equivalent 7.2/9 bar. The
disclosure does not rescue or change the outcome.

**Trajectory: GB1 3 → GB2 6 → GB3 7.** Monotonic, and each round's root cause was different and real
(contamination → calibration → the residual below). But 7 < 8.

### Disagreement classes — all three are ONE mechanism, and all three point the same way

Every disagreement is the court being **STRICTER** than the blind judge. There is not a single
false-entailment among them.

**Class A — stale child LABEL beaten over its own receipts (rule 1 under-applied): `8168`, `3433`.**
This is the pre-registered "facet gap", but the sharper description is that the facet gap is a *symptom*:
a child whose label names a different facet gets dismissed **by its label**, never read through its
receipts. The court's own reasons name the labels as the evidence:

- `8168` — *"Several child stories (Milano Incendi Edifici, Norway Wildfire Destroys Homes, Wildfires in
  Greece with US weather alerts) are unrelated…"*. Two of those three are honest: `1638` "Milano Incendi
  Edifici" serves **Sicily wildfire** receipts (a firefighter dead, Agrigento evacuations) and `4329`
  "Norway Wildfire Destroys Homes" serves **Gironde/Bordeaux, 220k evacuated**. Both are European
  wildfires — the label's own clause — dismissed on a stale label. (The court's Japan-quake catch is
  correct and is why I said partial, not entailed.)
- `3433` — *"Most child stories cover Ukraine war updates, diplomacy, mobilization, and unrelated topics
  like Poland and Romania, not drone and missile attacks on ships and cities."* `383` "Romania Demands
  Drone Reprogramming" serves **"Russians hit a foreign vessel with a drone in the Black Sea, 16 sailors
  evacuated"** and **"UNSC emergency session on Russian attacks on civilian ships"** — the label's *ships*
  clause verbatim. `437` "Poland Refuses MiG-29" serves **"drones attacked Russian cities (Voronezh)"** —
  the *cities* clause. The two receipts that most directly prove the label were counted against it.

**Class B — a fabricated absence (receipt-reading error): `8111`.** The court's reason states *"none of
the child story receipts mention a GM plant **or a Michigan visit**"*. The Michigan half is verifiably
false: child `3996` serves **"Trump defends his tariffs during Michigan visit"**. The court was right that
"GM plant" has no receipt (why I said partial) but reached it through a claim contradicted by the fixture
it was shown. This is the worst of the three — the verdict is defensible, the reasoning is not.

**Class C — the three-way scale has collapsed to binary.** `0 partial` across all 33 umbrellas, and both
Class-A/B partial↔failed rows are exactly the shape `partial` exists for: a **compound** label whose
dominant clause is strongly receipted and whose second clause is unsupported (`8168`: 6/7 children are
European wildfires + a fabricated "Quake Hits Japan"; `8111`: tariffs receipted + "GM plant" not). The
prompt offers `partial` but nothing steers the judge to it, so an unsupported clause takes the whole row
to `failed`. Two of my three disagreements would close on this alone.

### EXTRA — the false-entailment side (the `8193` class), checked explicitly

Four rows came back court-**entailed**: `8123`, `8165`, `8108`, `8195`. I independently entailed all four,
and re-checked each against the "specific claim needs a receipt" bar:

| id | label specific | receipt support |
|----|----------------|-----------------|
| 8123 | Assam · floods · *worsen* | toll 62 → 66 → 68, 5.24–7 lakh affected ✓ |
| 8165 | Spain + France · *over 200,000 evacuated* | 220k / 250k / 300k / 325k / 370k ✓ |
| 8108 | *Ahbap* · scandal | 4th-wave probe, 13 detained, minister named ✓ |
| 8195 | Canada · ***50%*** tariffs | "Trump announces new 50% tariffs on Canadian imports" ✓ |

**0 / 4 false entailments. The `8193` class does not reproduce in this sample.** The one wording worth
naming honestly: `8108`'s "charity fraud" is contextual (Ahbap *is* a charity; the receipts say
"soruşturma"/detentions, not "fraud") — but the named event is unambiguous and directly receipted, so it
is not a fabricated specific.

**This is the single most important safety result of the round: the court's residual error is entirely
one-directional and conservative. It over-fails honest umbrellas; it does not pass dishonest ones.**

### Cron-safety read — split by consumer, because the two consumers have opposite risk profiles

Quantifying the harm from this sample: of the **6** court-failed rows, **5** contain something genuinely
unsupported (`8111` GM plant · `8168` Japan quake · `8121` the entire claim · `8084` the sentencing ·
`5549` US arrests *and* defense moves). Only **`3433`** is, by my read, a fully honest label wrongly
failed. So the **unwarranted-chip rate on failed stamps ≈ 1/6 (~17%)** → roughly **3–4 of today's 20
active failed umbrellas** would wear an "under review" chip they don't deserve.

- **DISPLAY chips — acceptable, with the caveat stated.** The error direction is the safe one. An
  unwarranted "under review" chip *understates confidence* in an honest row; it does not assert a
  falsehood to the reader, and — critically — 0/4 entailed rows were false-entailed, so no dishonest label
  receives a clean bill of health. A conservative-but-explained failed verdict costs credibility on ~1 in
  6 flagged rows, and the chip is reversible on the next nightly run.
- **FETCH-GATE — not safe. Do not ship the flag on this verdict set for gating.** The same 17% becomes
  *suppression of honest front-page rows*, and the errors are concentrated exactly where the damage is
  largest: `3433` is the biggest umbrella in the population (**n=10,643, 52 children**) and it failed on a
  reason that misreads its two most on-target children. Gating it would blank a large slice of the front
  page on a false verdict. This is the same lesson as the `used_t` simulation — the detector goes blind
  precisely where the mass concentrates.

**Verdict on the gate itself: GB3 FAILS at 7/10 and the flag should not flip.** The plan puts enforcement
in the FETCH (Lever A), which is the consumer this verdict set is *not* safe for, so "safe enough for
chips" does not clear GB. The pre-registered bar was ≥8/10 before the run; it came back 7; the discipline
that killed four prior hypotheses says don't move the goalposts on a near miss.

**But the residual is narrowing and is now a single named mechanism** — GB1 was a contaminated instrument,
GB2 was three separate calibration faults, GB3 is *one*: **the judge still treats a child's LABEL as
evidence of non-membership**, and the scale has no working middle. That is a smaller, sharper target than
either previous round. Three cheap, testable changes before GB4:

1. **Demote the child label in the prompt block.** Rule 1 says receipts win, but the block still leads with
   `CHILD LABEL: "…"` — the most salient token the judge sees per child. Put receipts first and mark the
   label explicitly as *possibly stale, not evidence*.
2. **Constrain the reason to quote a RECEIPT, not a child label.** Two of three disagreements enumerate
   child labels as their proof; `8111` asserts an absence the fixture contradicts. Forcing the reason to
   cite receipt text makes both failure modes self-detecting in the ledger.
3. **Give `partial` a trigger for compound labels.** `0/33` partials is a measurement in its own right.
   State it: *if the label makes several claims and the majority of children support one of them, the
   verdict is `partial`, not `failed`.* This alone converts `8111` and `8168` → 9/10.

Re-run GB with a fresh salt (`gb4-blind`) on the same ≥2-child population after those land.

