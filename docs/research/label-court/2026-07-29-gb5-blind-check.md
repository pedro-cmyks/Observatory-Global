# GATE GB — ROUND 5 blind hand-check of the umbrella label court

**Date:** 2026-07-30 (artifact filed in the GB series' 07-29 sequence)
**Protocol:** inherited from `docs/research/label-court/2026-07-29-gb4-blind-check.md` (**protocol section only**);
gate GB of `docs/superpowers/plans/2026-07-29-identity-three-levers.md`.
**Trajectory into this round:** GB1 **3/10** (receipt *contamination*) → GB2 **6/10** (*calibration*) →
GB3 **7/10** (*one* mechanism, scale collapsed to binary) → GB4 **7/10** (*plateau* — the first round where
the error stopped being one-directional; fixes traded one class for another).
**Round-4 fixes under test here (`520bbf5d`):**
1. **Withhold is display-safe and non-destructive** — `_WITHHOLD_MARK_SQL` only touches rows where
   `label_status IS NULL`, and stamps a distinguishing `label_court_model` (`…#withheld`) so
   "attempted, ungrounded" is a durable DB state.
2. **Every lane ledgered** — `entailed`/`partial`/`failed`/`withheld` all append with `lane`, `verdict`,
   `reason`, and (withheld) `withhold_reason` + `judge_verdict`.
3. **Rule 4 numeric majority** — the prompt demands an "N/M children" count; `_rule4_majority_satisfied`
   parses it and withholds a `partial` whose own count is a tie/minority/absent.
4. **Absence claims checked** — `_absence_claim_contradicted` extracts NUMERIC targets near an
   absence-trigger phrase and checks them against every receipt (script-invariant: catches the Arabic-script
   `$91` witness).

**New this round (per brief):** for every disagreement, retrieve the court's own **ledgered reason** (all
lanes are ledgered now) and classify the failure mechanism against GB4's named classes — the round-4 fixes
each targeted a named class, so the report must say which are **dead** and which **persist**.

**Bar:** ≥8/10 strict agreement.
**DB:** read-only (`SET default_transaction_read_only = on`). No writes, no commits.

## Method

1. **Fresh salt `gb5-blind`**, drawn over the population the court actually judges (single-child exclusion
   mirrored):
   ```sql
   WHERE state='active' AND label IS NOT NULL AND is_umbrella = true
     AND (SELECT count(*) FROM dynamic_topics c
           WHERE c.parent_id = dynamic_topics.id
             AND c.state='active' AND c.label IS NOT NULL) >= 2
   ORDER BY md5(id::text || 'gb5-blind') LIMIT 10
   ```
   Population = **45** umbrellas (GB4's was 33 — the field grew by 12 eligible rows).
   `label_status` / `label_checked_at` / `label_court_model` / `label_proposed` were deliberately **not
   selected** by the fixture builder.
2. **Receipts fetched with the court's current scoping, verbatim** (`_RECEIPTS_SQL`): `role='evidence'`,
   `engine_version = topic_members_engine_version()` (resolved live → **`v1-compat`**),
   `COALESCE(quarantined,false)=false`, `GROUP BY headline, country_code`,
   `ORDER BY max(tm.assigned_at) DESC`, ≤3 per child, `html.unescape` before reading. Family shape mirrors
   `_umbrella_family_for`: ≤10 children, biggest-first by `agg_n_signals`, **receipts printed first, the
   child's own label last**. All 10 umbrellas resolved on the `topic_members` lane — **no fallback rows**.
3. Part 1 below was written to disk **before** the `label_status` / ledger queries ran.

**Judge's bar (unchanged):** honest family coverage; generic-over-generic = **entailed**; a SPECIFIC claim
in the label needs a supporting receipt somewhere in the family; judge the **EVENT, not the word**
(same-event-different-facet children COVER a label naming that event); a **compound** label whose secondary
clause has no receipt anywhere, where a strict majority supports the dominant clause = **partial**.

**Withheld rows (protocol item 4):** judged blind anyway and scored as **neither agreement nor
disagreement** — excluded from the denominator, with the score reported both ways.

**⚠ Independence disclosure (one row).** The GB5 brief instructed me to read GB4's *protocol* only. GB4's
protocol section is not separable from its body in that file, and I read it in full, so I had seen GB4's
blind calls and court verdicts for its ten ids **plus** the supplementary ids it discussed
(`8165`, `8084`, `8070`, `8111`, `8193`, `3433`), and the round-4 commit message (`520bbf5d`) names
`3433`, `5549`, `8168`, `8175`, `8084`, `8070`, `8108`, `8121`, `8132`, `8185`, `8186`.
The `gb5-blind` salt re-drew exactly one of these: **`3433`**. Prior knowledge carried in for it: GB3
blind-judged it not-failed while the court failed it (its "marquee blocker"), GB4 recorded it moving
`failed → partial`, and the commit records it now stating "6/10 children". **Its family has since changed
shape entirely** (GB4 cites n=10,643 / 10 children; today it is n=2,962 / **2** children), so the fixture
below is not the one those rounds discussed. Per the standing discipline I re-derived it from the receipts
alone. **The score is reported with and without that row.** The other nine ids are fresh.

---

## Part 1 — the 10 blind judgments (written before seeing any verdict, ledger, or stamp)

### 1. `8170` — "Italy heatwave: record temperatures, drought, climate warnings" (n=762, 4 children)

- `367` **IT** — "È in arrivo la quarta ondata di caldo tropicale: ecco quando si sfioreranno nuovamente i
  40 gradi" · "l'anticiclone africano con temperature fino a 40°C" · "Da mercoledì arriva la quarta ondata
  di caldo". **ON** — Italy, heatwave, verbatim.
- `2757` **IT** — "Caldo feroce dagli ultimi giorni di luglio, si torna verso i 40 gradi e più" · "punte
  fino a 39 gradi a Trento". **ON** — Italy.
- `4971` **ES** — AEMET yellow warning in the Canary Islands for 35 ºC; the coming escalation of
  temperatures. **Heat, but Spain.**
- `2694` **GB** — "When will the next heatwave hit the UK? Met Office forecast" · "When will it next rain in
  the UK?". **Heat, but the UK.**

Four clauses. **"Italy heatwave"** is verbatim-receipted in 2 of 4 children; **"climate warnings"** is
receipted by the AEMET *aviso amarillo*; **"record temperatures"** is thin (the receipts say *approaching*
40°C, never "record"); **"drought" has no receipt anywhere** — and the receipts point the other way, naming
*temporali* and asking when it will next rain.

Rule 4's shape exactly: taking the dominant clause as **heatwave**, a strict majority — **4/4 children** —
are heatwave stories, while the *drought* clause has no supporting receipt anywhere in the family.
Rule 3 is satisfied for the "Italy" specific (two children carry Italian heat receipts verbatim), so the
over-narrow geography is a coverage complaint, not a fabrication.

**Judgment: partial.**

### 2. `8223` — "Ukrainian Drone Strikes on Russia" (n=762, 3 children)

- `37` — "Ukraine drone strikes on Wildberries warehouses hit Russian sellers, consumers" · "'Russia's
  Amazon' says Ukrainian drones hit more of its warehouses". ON, verbatim.
- `2708` — "Двенадцать человек пострадали при атаке беспилотников ВСУ на Белгород" — twelve injured in an
  AFU **drone** attack on **Belgorod**. ON.
- `4920` — "Δύο νεκροί και 17 τραυματίες σε επιδρομές της Ουκρανίας στη νοτιοδυτική Ρωσία" — two dead, 17
  injured in Ukrainian raids on **southwestern Russia**; a second receipt adds Crimea. ON.

3/3 children; every specific in the label (Ukrainian · drone · strikes · on Russia) carries a verbatim
receipt, across three languages and both sides' press.

**Judgment: entailed.**

### 3. `8257` — "Russian Military Losses July 2026" (n=173, 2 children)

- `4913` — "Втрати ворога станом на **27 липня 2026**: свіжі дані Генштабу та ціна розбитої техніки" —
  enemy losses as of 27 July 2026, General Staff data. Its other two receipts count Russian missiles/drones
  shot down on 26 and 23 July — materiel losses, same family, same month.
- `3740` — "Сили оборони знешкодили ще 1 590 окупантів – Генштаб" · "Армія Росії втратила понад 1400
  військових за добу" · "ще 1440 російських окупантів". ON, verbatim.

Both the subject (Russian military losses) and the date specific (**July 2026**) are verbatim receipted.
A running-tally label over a running-tally family — rule 2's honest generic.

**Judgment: entailed.**

### 4. `8237` — "Putin Blames Lenin, War Continues; Ukraine Aid Delayed" (n=950, 4 children)

- `439` — "Putin cere rușilor să înțeleagă importanța războiului și **dă vina pe Lenin** pentru conflictul
  din Donbas". **Clause 1, verbatim.**
- `5980` — "Вашингтон отказался передавать Киеву военную помощь на **$400 млн**" · "Сенатор Дурбин: США не
  передадут Киеву военную помощь на 400 млн долларов". **Clause 3, verbatim** (blocked rather than delayed
  — the same event, a harder facet).
- `2966` — a munitions depot exploding in a residential district in Ukraine; Russian forces striking a drone
  exhibition near Kyiv. **Clause 2** ("war continues"), live war events.
- `1351` — Poland and Hungary opposing Ukraine's EU accession; Peskov on the US not breaking Ukrainians;
  Usyk not running for president. War-adjacent politics; the Usyk line is junk.

A stitched three-clause label, and an ugly one — but **every clause carries a receipt**, and 4/4 children
sit inside the Russia-Ukraine war family the label names. Rule 4's `partial` trigger requires a clause with
**no** receipt anywhere; none of the three qualifies. Judged by the rules as written rather than by distaste
for the stitching, this is coverage, not fabrication. *(Softest of my entailments alongside `8245`; noted as
close.)*

**Judgment: entailed.**

### 5. `3433` — "US Probes Russian Role in Iran CIA Attacks" (n=2962, 2 children) *(collision — re-derived)*

- `10` — "Reuters: разведка США выясняет, причастна ли РФ к ударам Ирана по объектам ЦРУ" — US intelligence
  is establishing whether Russia was involved in Iran's strikes on CIA facilities. The label, verbatim.
  Also Trump on Russia passing Iran satellite imagery of American bases.
- `2724` — "Iran strikes on CIA facilities prompt questions about Russian role" · "Iran's Drones Hit CIA
  Sites With 'Unusual Precision'; Did Russia Help?". ON, verbatim.

2/2 children; every specific (US probe · Russian role · Iran · CIA attacks) receipted independently on two
sides of the story, in two languages.

**Judgment: entailed.**

### 6. `8261` — "Quarterly Earnings Previews" (n=194, 2 children)

- `4497` — "Avista (AVA) to Announce Earnings on Monday" · "Capital Bancorp (CBNK) Expected to Announce
  Earnings on Monday" · "Chain Bridge Bancorp (CBNA) Expected to Post Earnings on Monday".
- `4576` — "Acadia Healthcare (ACHC) Expected to Announce **Quarterly Earnings** on Tuesday" · "BrightSpire
  Capital (BRSP) Expected to Release Quarterly Earnings on Tuesday" · "Brown & Brown (BRO) Expected to
  Release Earnings on Monday".

A generic label over a genuinely generic family — rule 2's textbook case. Every one of the six receipts is
an earnings-announcement preview; "Quarterly" is verbatim. *(This is low-value financial-wire bot content;
the court judges label truth, not content worth, and the label is exactly true.)*

**Judgment: entailed.**

### 7. `8254` — "Wildberries Warehouse Drone Attacks" (n=181, 2 children)

- `4912` — "Дроны атаковали логистический хаб **Wildberries** под Воронежем" · "Атака ВСУ на склады
  Wildberries в Краснодаре и Невинномысске". ON, verbatim.
- `3469` — "Украина ударила по складам Wildberries в Краснодаре и Невинномысске. Восемь человек
  пострадали" · "В Петербурге и Ленинградской области горят склады Wildberries". ON. Its Odessa receipt
  ("Россия нанесла удар возмездия за Wildberries") is the retaliation facet of the same chain —
  same-event-different-facet, covered.

**Judgment: entailed.**

### 8. `8131` — "Pralhad Joshi Appointed Education Minister" (n=67, 2 children)

- `6932` — "Pralhad Joshi replaces Dharmendra Pradhan as Education Minister" · "takes charge as education
  minister a day after Pradhan's exit".
- `7672` — "Prahlad Joshi takes charge as Education Minister" · "Pralhad Joshi Appointed Education
  Minister" (the label itself, verbatim) · "New Union Education Minister Prahlad Joshi takes charge".

**Judgment: entailed.** One event, both children, the named person and the named appointment both receipted.

### 9. `8252` — "Russian Aerial Attacks on Ukraine" (n=440, 4 children)

- `2935` — "Нічна атака російських дронів: ППО знешкодила **123 цілі**" · "збили над Україною одну ракету
  та **127 дронів**". ON — the *aerial* specific, verbatim, twice.
- `2970` — "Россия ударила по Запорожью и Изюму: есть погибшие и пострадавшие" · "Запорожье: армия РФ
  нанесла удар по городу". ON (2/3; its third receipt, drones over Krasnodar Krai, runs the other
  direction).
- `3798` — BlackSeaNews operational bulletins on the Russian invasion. On-family.
- `3781` — BlokNotRU commentary on continuing strikes on Ukrainian ports. On-family, low quality.

Every specific (Russian · aerial · on Ukraine) is verbatim receipted; 4/4 children sit in the named family.

**Judgment: entailed.**

### 10. `8245` — "Russia Faces Escalating Crises Amid War Pressures" (n=323, 2 children)

- `1237` — "Paniczne ruchy Moskwy. Tak Kreml szuka pieniędzy na wojnę Putina" (panicked moves; the Kremlin
  hunting money for Putin's war) · "Následky v Rusku sú vážnejšie, než sa zdalo" (the consequences in Russia
  are more serious than they seemed) · "Rosja szykuje się na najgorszy scenariusz".
- `4900` — "'Losing his magic': Putin's grip on Russia tested by public unhappiness" · "Andy Burnham issued
  chilling Russia warning as Putin edges towards WW3".

An interpretive, generic label — but it names **no** specific place, actor, figure or count that could be
fabricated, and both children are Russia-under-strain stories: war financing, strike consequences, domestic
unhappiness. Rule 2 protects generic-over-generic. Note the stale-label trap: `4900` is labeled "Russian
Fuel Crisis" and not one of its receipts mentions fuel — judged by receipts (rule 1), it still belongs.

**Judgment: entailed.** *(The softest entailment of the ten, alongside `8237` — vague, but not dishonest.)*

**Blind tally: 9 entailed · 1 partial · 0 failed.**

---
## Part 2 — the court's verdicts, and the comparison

**Run provenance (checked before comparing).** The umbrella lane is **live in the 30-min cron**
(`ATLAS_COURT_UMBRELLAS=on` in the ALW `.env`). Seven of the ten rows were stamped by 07-30 cron cycles
(08:08–10:22 UTC), three by the post-fix manual run of 07-29 17:02 UTC. Every stamp in the sample is
post-`520bbf5d` — the verdicts under test come from the fixed instrument running unattended, as the brief
states. Population of 45 eligible umbrellas: **27 entailed / 9 partial / 3 failed / 4 withheld(`#withheld`)
/ 2 relabel-reset(NULL)**.

**One row drawn carries no verdict** (`8245`, `label_status IS NULL`). It is not quote-gate-withheld — it is
**relabel-reset**: `relabel_court_failed.py` rewrites a `failed` row's label and sets
`label_status=NULL, label_checked_at=NULL`, leaving `label_court_model` stale. Protocol item 4 applies the
same way (neither agreement nor disagreement), so the score is reported on both denominators.

| # | id | served label | blind | court (DB) | strict |
|---|------|-------|-------|-------|--------|
| 1 | 8170 | Italy heatwave: record temperatures, drought, climate warnings | partial | **partial** | ✓ ⚠stale |
| 2 | 8223 | Ukrainian Drone Strikes on Russia | entailed | entailed | ✓ |
| 3 | 8257 | Russian Military Losses July 2026 | entailed | entailed | ✓ |
| 4 | 8237 | Putin Blames Lenin, War Continues; Ukraine Aid Delayed | entailed | **partial** | ✗ |
| 5 | 3433 | US Probes Russian Role in Iran CIA Attacks | entailed | **partial** | ✗ ⚠stale |
| 6 | 8261 | Quarterly Earnings Previews | entailed | entailed | ✓ |
| 7 | 8254 | Wildberries Warehouse Drone Attacks | entailed | entailed | ✓ |
| 8 | 8131 | Pralhad Joshi Appointed Education Minister | entailed | entailed | ✓ |
| 9 | 8252 | Russian Aerial Attacks on Ukraine | entailed | entailed | ✓ |
| 10 | 8245 | Russia Faces Escalating Crises Amid War Pressures | entailed | *(unstamped)* | — |

### **GB5 SCORE: 7/10 strict — FAIL** (bar ≥8/10)

- **Unstamped-adjusted (protocol item 4, /9):** **7/9 = 0.778** against an equivalent bar of 7.2/9.
  **Still FAIL.**
- **Excluding the one disclosed collision** (`3433` ✗) **and the unstamped row: 7/8 = 0.875.** Reported for
  completeness, **not adopted**: the disclosure cannot have manufactured this disagreement — my prior
  knowledge was that the court had moved `3433` to `partial`, which is what it says, so contamination would
  have pushed me *toward* agreement and I diverged anyway. Dropping the row drops a real defect from the
  measurement, not a leak.

**Trajectory: GB1 3 → GB2 6 → GB3 7 → GB4 7 → GB5 7.** Third consecutive round at 7. But the ⚠stale marks
carry the round's finding, and the decomposition is the diagnosis:

> On the **7 rows where the court judged the same label I judged**, agreement is **6/7 = 0.857** — above
> bar. The two rows that drag the score down are rows where **the court's stamp was earned on a different
> label than the one now being served.** The *judging* is calibrating; the *stamps* are decoupling from the
> labels they were earned on.

---

## Disagreement classes — retrieved from the ledger, and classified

The round-4 ledger fix earned its keep immediately: every disagreement below is diagnosed from the court's
**own recorded reason**, which GB4 could not retrieve for its `partial` rows at all.

### DEAD — four GB4 classes, verified closed in production

1. **Withhold erases a valid stamp (GB4 fix 1, DB half) — DEAD.** Ten rows this session show a graded stamp
   followed by a withhold; **none lost its stamp** (`8232` `failed→withheld→entailed`; `8175`
   `failed,failed,failed→withheld→failed`; `8222` `failed→withheld ×11`). `_WITHHOLD_MARK_SQL`'s
   `WHERE label_status IS NULL` holds under real cron traffic. GB4's `dt-8084` erasure cannot recur.
2. **Ledger records only failures (GB4 fix 2) — DEAD.** 154 umbrella entries today carry `lane`, `verdict`,
   `withhold_reason` and `judge_verdict`. **This is the fix that made every other GB5 finding possible**;
   without it Classes D′, E and F below would all have been invisible.
3. **Rule 4 fires on a stated TIE (GB4 class D, the tie case) — DEAD by construction.**
   `rule4-majority-not-met` withheld **10** verdicts today. GB4's `5549`-on-a-4/8-tie shape can no longer be
   stamped.
4. **Class B in NUMERIC form — DEAD.** `absence-contradicted` fired **22** times today. The detector works
   on exactly the shape it was built for.

*(Withhold-reason distribution today: `ungrounded` 36 · `absence-contradicted` 22 ·
`rule4-majority-not-met` 10. Both new detectors are load-bearing, not decorative.)*

### PERSISTS — Class B, textual form (fourth round)

The round-4 fix documented its own limitation — "a purely textual absence claim about a phrase inside a
non-Latin-script receipt is NOT verified here". That limitation now has a named, live victim.

**`dt-8241` (n=1,091), currently `failed`.** The court's ledgered reason at 12:00 UTC:

> *"**No receipt mentions 'drone attacks' or 'threats'** by Iran that escalate tensions; the receipts
> describe AI-generated images of Trump, a war cost figure, and unrelated claims about Ukraine and a naval
> blockade, e.g., 'Аракчи пообещал Зеленскому ответ за удар по иранскому судну' — none support the umbrella
> label's specific claim of drone attacks and threats."*

Child `582` serves, verbatim, **three** receipts:
- "Ιράν: Ο στρατός επιτέθηκε στο Μπαχρέιν και στην Ιορδανία με **drones**"
- "Ο στρατός του Ιράν ανακοίνωσε πως επιτέθηκε σε Μπαχρέιν και Ιορδανία με **drones**"
- "Στην... αντεπίθεση περνά το Ιράν - Έπληξε σημαντικές Αμερικανικές εγκαταστάσεις σε Μπαχρέιν και Ιορδανία"

Iran's army announcing it struck Bahrain and Jordan **with drones** — the exact clause declared absent. And
the very receipt the reason quotes to ground itself, *"Аракчи пообещал Зеленскому ответ"* (Araghchi promised
Zelensky a response), **is** the "threats" clause it declares absent in the same sentence. Both clauses are
receipted; both are called missing.

Two aggravating details:
- The court **quoted that same drone receipt itself** 3h15m earlier (08:43 UTC) *while still asserting the
  drone claim was unsupported* — self-contradiction inside one day's ledger.
- The target word **"drones" is Latin-script inside Greek prose** — a literal substring check, the same
  mechanism `_absence_claim_contradicted` already uses for numbers, would have caught it. The gap is not
  script; it is that the check only extracts *numeric* targets.

The grounding gate passes (a real receipt is quoted), the numeric absence check sees no number, and a
`failed` stamp ships on an honest label. **Class B survives its third dedicated fix.**

### PERSISTS, MUTATED — Class D′: rule 4's number is now stated and parsed, but never *verified*

**`dt-8237`** — my one label-matched disagreement, and the cleanest specimen. The ledgered reason:

> *"**3/4 children support the 'Ukraine Aid Delayed' clause** (receipt: 'Сенатор Дурбин: США не передадут
> Киеву военную помощь на 400 млн долларов'), but the 'Putin Blames Lenin, War Continues' clause is
> supported by only 1/4 children …, so no strict majority for both claims."*

Two faults, both structural:

**(a) The count is fabricated.** Exactly **one** of the four children (`5980`) carries aid receipts; `439`
is Putin/Lenin, `1351` is EU-accession politics, `2966` is a munitions-depot explosion. The true count is
1/4, not 3/4. `_rule4_majority_satisfied` parses the stated fraction and checks it is a strict majority —
**it never checks the fraction is true.** GB4 closed the tie case; a model can now clear the same gate
simply by writing a larger numerator. The number went from absent to unfalsifiable.

**(b) The rule was misapplied.** The reason demands "a strict majority for **both** claims". Rule 4 requires
a majority for **one** dominant clause *while another clause has no supporting receipt anywhere*. Here every
clause is receipted (Lenin verbatim in `439`, the $400m aid verbatim in `5980`, live war events in `2966`),
so rule 4's `partial` trigger should not fire at all — which is why I read it entailed.

*Direction of the error:* the court is **stricter** than the blind judge here, so the chip is in the safe
direction. But the mechanism is the same one GB4 named as looser-than-blind: rule 4 still is not tracking
its own text, and the number added to discipline it is not checked against the fixture.

### PERSISTS — withhold is still not display-safe (GB4 blocker 6, display half)

The DB half shipped and works (class 1 above). The **display half is dead code**, exactly as the commit
message predicted it would be until a serializer catches up:

- `backend/app/services/thread_intelligence.py` selects **`label_status` only**; `label_checked_at` and
  `label_court_model` are never served, so nothing can set `courtWithheld`, so `'awaiting-verification'`
  never derives.
- `labelReviewReason` therefore falls to the confidence floor, and umbrella `avg_confidence` measures
  **0.968–0.991** against `LEAD_CONFIDENCE_FLOOR = 0.70` — the fallback can still never fire for an umbrella.

**6 of 45 eligible umbrellas (13%) render with no chip today** while carrying no verdict:

| id | n | state | avg_conf | chip | served label |
|----|---|-------|----------|------|--------------|
| 8241 | 1,091 | relabel-reset | 0.987 | **none** | Iran Tensions Escalate After Drone Attacks and Threats |
| 8222 | 694 | `#withheld` | 0.985 | **none** | Multiple shootings, plane crashes across regions |
| 8245 | 323 | relabel-reset | 0.976 | **none** | Russia Faces Escalating Crises Amid War and Unrest |
| 8228 | 261 | `#withheld` | 0.968 | **none** | Proof of Citizenship Blocked |
| 8259 | 219 | `#withheld` | 0.986 | **none** | Kyiv Attacks July **2024** |
| 8258 | 175 | `#withheld` | 0.991 | **none** | Russian Ballistic Attack on Kyiv July 19 |

**57 of today's 68 withholds were suppressing a `failed` verdict** (`judge_verdict` distribution: failed 57
· partial 10 · entailed 1). Every one of those is a warning the reader never sees. GB4's structural finding
— *the withhold path issues clean bills of health without a verdict* — is **unchanged at the consumer**,
even though the DB-level erasure it was paired with is fixed.

### NEW — Class E: a stale stamp riding a rewritten label

`build_umbrella_topics.py` upserts umbrellas with
`ON CONFLICT (identity_key) DO UPDATE SET label=EXCLUDED.label, …` — it **rewrites an umbrella's label and
re-parents its children**, and touches **none** of `label_status`, `label_checked_at`, `label_court_model`,
`label_proposed`. It does not set `label_updated_at` either, which is why the obvious detector is blind:

```
label_updated_at > label_checked_at  →  0 of 39 stamped umbrellas
```

Measuring it honestly — joining each live stamp to the ledger row that produced it and comparing
`served_label` against today's `label`:

> **5 of 39 stamped umbrellas (12.8%) serve a label the court never judged.**
> Two of them landed in this draw (`8170`, `3433` = **20% of the sample**).

| id | verdict | n | judged | now serves |
|----|---------|---|--------|------------|
| 3433 | partial | 2962 | Drone and Missile Attacks on Ships and Cities | US Probes Russian Role in Iran CIA Attacks |
| 8170 | partial | 762 | Global heatwaves, wildfires, and power outages | Italy heatwave: record temperatures, drought, climate warnings |
| 5549 | partial | 454 | EU Sanctions, US Arrests, and Defense Moves | EU May Shift from Sanction Packages After Greek Demands |
| 8182 | **entailed** | 452 | Sonam Wangchuk Ends Hunger Strike Amid Protests | Wangchuk Hunger Strike |
| 8105 | **entailed** | 167 | Typhoon **Noul** Ravages Southern China | Typhoon **Bavi** Landfall |

`3433` is the sharpest illustration: the stamp was earned on a **10-child** family about ship and city
strikes ("6/10 children", per its own ledgered reason); today the row has **2 children** and is about a US
intelligence probe into Russia's role in Iranian attacks on CIA sites. Neither the label nor the family
survives, and the verdict does.

**The dangerous instance is `dt-8105`.** It serves **"Typhoon Bavi Landfall"** carrying an **`entailed`**
stamp — **no chip** — while all six of its receipts name a *different storm*:

> "More than 700,000 evacuated as **Typhoon Noul** makes landfall in southern China" ·
> "**Typhoon Noul** Kills 10 In China, Triggers Widespread Flooding & Travel Chaos" ·
> "Southern China faces torrential rain, floods after **Typhoon Noul** makes landfall"

"Bavi" appears in **zero** receipts. The `entailed` verdict was *correct* when issued — for
"Typhoon Noul Ravages Southern China" — and it survived a rename to a storm the receipts never mention.
Rule 3 (a named specific needs a receipt) would fail this label instantly; the court will simply never be
asked, because the row is already stamped and the cron judges `--only-unchecked`.

**This is the GB5 analogue of GB4's withhold finding: the false clean bill of health now arrives by
staleness rather than by a wrong verdict.** GB4's entailed lane was clean *through verdicts* and leaked
*through withholds*; GB5's entailed lane is still clean through verdicts and now leaks *through stamps that
outlive their labels*. (`8182` is the benign case — "Wangchuk Hunger Strike" is narrower but still true.)

### NEW — Class F: the relabel↔court livelock

The 30-min runner pairs two steps that feed each other:

- **Step 5** `label_court --write --only-unchecked` → judges rows with `label_status IS NULL`.
- **Step 5b** `relabel_court_failed --write` → rewrites the label of every `failed` row **and resets
  `label_status=NULL`** so the next cycle re-judges it.

For an umbrella whose family is genuinely incoherent, **no regenerated label can pass**, so the pair never
converges. Measured over today's ledger:

> **154 umbrella judgments over 43 distinct rows. 23 rows judged more than once. 20 rows had their served
> label rewritten between judgments.**

- `dt-8235` cycled **5 distinct labels** across 7 judgments ("Trump Threatens Military Action if Iran Talks
  Fail" → "US Strikes on Iran End; New Threats Emerge" → "US-Iran Tensions Escalate After CENTCOM Strikes" →
  "US Ends Iran Strikes; Trump Threatens New Military Action" → "US Ends Iran Strikes; Trump Threatens
  Military Action").
- `dt-8222` was judged **12 times**, withheld 11 of them.
- `dt-8245` — the unstamped row in this sample — was judged **7 times**, failed every time, oscillating
  between "…Amid War Pressures", "…Amid War and Unrest" and "Russian Economy Under Pressure from War and
  Sanctions". **Its label changed again during this session**: the fixture I judged blind reads "…Amid War
  Pressures"; by the time the chip query ran it read "…Amid War and Unrest".

Three costs: DeepSeek calls burned on rows that cannot converge; **the label a reader sees on the front page
changes every ~30–60 minutes** for ~20 umbrellas a day; and every relabel opens a fresh `label_status IS
NULL` window in which no chip renders at all (Class 6 above). Class F is also the *generator* of Class E's
`partial` cases and of the two relabel-reset NULLs in the sample.

### Both-directions duty — the entailed lane, checked explicitly

Six rows came back court-**entailed**. I independently entailed all six, and re-checked each against the
"a specific claim needs a receipt" bar:

| id | label specifics | receipt support |
|----|-----------------|-----------------|
| 8223 | *Ukrainian* · *drone* · *strikes on Russia* | "Ukraine drone strikes on Wildberries warehouses…" · "атаке беспилотников ВСУ на Белгород" ✓ |
| 8257 | *Russian military losses* · *July 2026* | "Армія Росії втратила понад 1400 військових за добу" · "станом на 27 липня 2026" ✓ |
| 8261 | *quarterly* · *earnings* · *previews* | "Expected to Announce **Quarterly Earnings** on Tuesday" ✓ |
| 8254 | *Wildberries* · *warehouse* · *drone attacks* | "Дроны атаковали логистический хаб Wildberries под Воронежем" ✓ |
| 8131 | *Pralhad Joshi* · *Education Minister* | "Pralhad Joshi replaces Dharmendra Pradhan as Education Minister" ✓ |
| 8252 | *Russian* · *aerial* · *on Ukraine* | "Нічна атака російських дронів: ППО знешкодила 123 цілі" ✓ |

**0 / 6 false entailments through a verdict. The entailed lane remains clean where the court actually
answered the question.** The leak is Class E: `8105`'s entailed stamp is a false clean bill of health that
no verdict ever issued.

---

## Cron-safety re-read — the chips consumer is LIVE

**Scope check first.** `ATLAS_COURT_UMBRELLAS=on` (umbrella lane judging on the 30-min cron).
`ATLAS_THREADS_FETCH_MULT` **unset → default 1 → the fetch-gate is inert**; `ATLAS_LABEL_COURT_APPLY`
**unset → off**, so the court never replaces a served label. **The only live consumer is the additive
chip** — it never hides a thread and never changes ranking. Nothing is being suppressed today.

**Chip-level re-scoring of the same 10 rows.** `labelReviewReason` maps `failed`→chip, `partial`→chip,
`entailed`→**no chip**, NULL→confidence floor (structurally unreachable for umbrellas), so the three-way
scale collapses to a binary:

| row | blind → chip? | court → chip? | agree |
|-----|---------------|---------------|-------|
| 8170 | chip | chip | ✓ |
| 8223 | no chip | no chip | ✓ |
| 8257 | no chip | no chip | ✓ |
| 8237 | **no chip** | **chip** | ✗ *(safe direction)* |
| 3433 | **no chip** | **chip** | ✗ *(safe direction)* |
| 8261 | no chip | no chip | ✓ |
| 8254 | no chip | no chip | ✓ |
| 8131 | no chip | no chip | ✓ |
| 8252 | no chip | no chip | ✓ |
| 8245 | no chip | no chip | ✓ |

**Chip-level agreement: 8/10, and both disagreements are in the safe direction** — an unwarranted "under
review" understates confidence in an honest label; it never asserts a falsehood. On the drawn sample,
**nothing dishonest displays clean.**

### Is anything now visible on the front page that shouldn't be? — YES, three things

1. **`dt-8105` "Typhoon Bavi Landfall" — a fabricated specific displaying as trusted.** `entailed`, no chip,
   and not one receipt mentions Bavi; all six name Typhoon Noul. This is the single clearest live falsehood
   wearing a clean bill of health, and it is exactly the failure mode the court exists to prevent. It is
   **not** a calibration error — the court never judged this label. Class E. *(`dt-8182` is the same
   mechanism with a harmless outcome.)*
2. **Six unstamped umbrellas render with no chip**, headed by **`dt-8241` (n=1,091)** — which the court
   `failed` **five separate times today**, each stamp erased by the next relabel — and including
   **`dt-8259` "Kyiv Attacks July 2024"**, a 2024 date over a 2026 corpus. The reader cannot tell these from
   verified labels. GB4's blocker 6 is closed at the database and open at the screen.
3. **The displayed label itself churns.** ~20 umbrellas/day have their front-page label rewritten between
   30-min cycles (up to 5 distinct labels in one day for `dt-8235`), each rewrite followed by a chip-less
   window. A reader returning to the same story sees it renamed with no indication that anything is under
   review.

**Severity.** The chip is additive, the fetch-gate is inert, and on the sample the chip errs safe — so this
is not an emergency. But Class E is a regression *in kind*: for the first time a dishonest label is
displaying clean **without any withhold and without any wrong verdict**, purely because a stamp outlived the
label it was earned on. Items 1 and 2 are both small, well-localized fixes; neither is a re-calibration.

---

## Verdict and what remains

### **GB5: 7/10 strict (7/9 unstamped-adjusted) — FAIL.** The flag should not flip.

The pre-registered bar was ≥8/10 before the run; it came back 7. **Fifth consecutive miss**, and the same
discipline that killed the five prior hypotheses applies: do not move the goalposts on a near miss — even
though the label-matched subset (6/7 = 0.857) and the chip-level binary (8/10, both errors safe) would both
clear it.

**Trajectory: 3 → 6 → 7 → 7 → 7.** Read the composition, not the number:

- GB1 = a contaminated instrument. GB2 = three calibration faults. GB3 = one mechanism + a collapsed scale.
  GB4 = fixes trading one error class for another. **GB5 = the judging is finally calibrating — and the
  defects have migrated out of the judge and into the plumbing around it.**
- Four GB4 classes are **verifiably dead in production** (stamp erasure, ledger blindness, the rule-4 tie,
  numeric absence) — the most any round has closed. The instrument's *reasoning* now agrees with a blind
  human 6 of 7 times on the rows it actually judges.
- Both surviving classes and both new ones are **write-path and lifecycle defects, not judgment defects**:
  a stamp that outlives its label (E), a loop that never converges (F), a display that cannot express
  "unverified" (blocker 6), and a number the gate parses but never checks (D′). Only Class B is still a
  reasoning defect, and it is now confined to the exact form its own fix documented as out of scope.

### What remains for the bar

1. **Invalidate the stamp when the label changes (Class E) — the new blocker, and the cheapest fix here.**
   `build_umbrella_topics.py`'s upsert must clear the four court columns whenever `EXCLUDED.label IS
   DISTINCT FROM dynamic_topics.label` (and equally when the child set changes — `3433` kept a verdict
   through a 10→2 child collapse). `label_updated_at` must be set by the same statement, so the staleness
   query stops silently returning 0. **Treat a stale `entailed` stamp on a renamed label as a blocking
   condition, not a neutral one** — `8105` is shipping a false clean bill of health today.
2. **Break the relabel↔court livelock (Class F).** A row whose regenerated label has already been failed
   N times (2 is enough) must stop being relabeled and be routed to the over-merge/demote path instead —
   a family that no label can describe is an over-merge, not a labeling problem. Today those rows burn
   ~110 redundant DeepSeek judgments a day and rename themselves on the front page.
3. **Make the absence check literal, not numeric (Class B, fourth attempt).** The `8241` witness needs no
   second LLM call and no per-language normalization: extract the **quoted or capitalized target phrase**
   after an absence trigger and substring-check it against every receipt, exactly as the numeric path
   already does. "drones" sits in Latin script inside a Greek headline; the existing mechanism would have
   caught it if it looked at words as well as digits.
4. **Verify rule 4's count instead of parsing it (Class D′).** The denominator `M` is known to the caller
   (`len(family_children)`); the numerator is not, but a cheap floor is available — require the reason to
   quote **one receipt per supporting child it claims**, and withhold when the number of distinct receipt-
   grounded children is less than the stated `N`. `8237` claimed 3/4 with one child's receipts.
5. **Serve the withhold signal (GB4 blocker 6, display half).** `thread_intelligence.py` must select
   `label_checked_at` / `label_court_model` and set `courtWithheld` so `'awaiting-verification'` can
   derive. The frontend has been ready since `520bbf5d`; the payload is the missing half. Until then 13% of
   the umbrella lane — including its largest unstamped row — displays as trusted.

Re-run GB with a fresh salt (`gb6-blind`) on the same ≥2-child population after items 1 and 2 land. **Item 1
first**: while stamps outlive their labels, no blind sample can measure the judge, because two rows in ten
are answering a question the court was never asked.
