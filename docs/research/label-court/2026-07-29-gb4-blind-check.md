# GATE GB — ROUND 4 blind hand-check of the umbrella label court

**Date:** 2026-07-29
**Protocol:** `docs/superpowers/plans/2026-07-29-identity-three-levers.md`, gate GB; method inherited from
`docs/research/label-court/2026-07-29-gb3-blind-check.md` (protocol section).
**Trajectory into this round:** GB1 **3/10** (receipt *contamination* — `_RECEIPTS_SQL` unscoped by
`engine_version`/`quarantined`, fixed `92c66ceb`) → GB2 **6/10** (*calibration* — stale child labels beaten
over receipts, single-child "families" stamped; fixed `0f7adf7b`) → GB3 **7/10** (*one* mechanism — the
child LABEL still led each block and the three-way scale had collapsed to binary, `0/33` partials).
**Round-3 fixes under test here (`3a946bc1`):**
1. **Receipts physically lead** each child block; the label prints last, marked *"may be stale — do not
   treat as evidence"*.
2. **QUOTE-GATE** — a family reason must ground itself in a verbatim receipt excerpt
   (`_reason_quotes_a_receipt`); an ungrounded verdict is **withheld**, and `_WITHHOLD_CLEAR_SQL` actively
   clears any stale stamp rather than merely skipping the write.
3. **Rule 4** — a compound label whose dominant clause is receipted and whose secondary clause is not now
   has an explicit `partial` trigger.

**New distribution after the fixes:** 12 entailed / 6 partial / 10 failed / **5 withheld** over 28 grounded.
**Known named residual carried in:** an attention gap across ~30 receipt lines — dt-3433's "cities" clause
has a receipt in the prompt that the judge misses.
**Bar:** ≥8/10 strict agreement before the cron flag flips.
**DB:** read-only (`SET default_transaction_read_only = on`). No writes, no commits.

## Method

1. **Fresh salt `gb4-blind`**, drawn over the population the court now actually judges (the single-child
   exclusion mirrored):
   ```sql
   WHERE state='active' AND label IS NOT NULL AND is_umbrella = true
     AND (SELECT count(*) FROM dynamic_topics c
           WHERE c.parent_id = dynamic_topics.id
             AND c.state='active' AND c.label IS NOT NULL) >= 2
   ORDER BY md5(id::text || 'gb4-blind') LIMIT 10
   ```
   Population = **33** umbrellas. `label_status` deliberately **not** selected by the fixture builder.
2. **Receipts fetched with the court's current scoping, verbatim** (`_RECEIPTS_SQL`): `role='evidence'`,
   `engine_version = topic_members_engine_version()` (resolved live → **`v1-compat`**),
   `COALESCE(quarantined,false)=false`, `GROUP BY headline, country_code`,
   `ORDER BY max(tm.assigned_at) DESC`, ≤3 per child, `html.unescape` before reading. Family shape mirrors
   `_umbrella_family_for`: ≤10 children, biggest-first by `agg_n_signals`, **receipts printed first, the
   child's own label last** — the same ordering the judge now sees. All 10 umbrellas resolved on the
   `topic_members` lane (no fallback rows).
3. Part 1 below was written to disk **before** the `label_status` query ran.

**Judge's bar (unchanged):** honest family coverage; generic-over-generic = **entailed**; a SPECIFIC claim
in the label needs a supporting receipt somewhere in the family; judge the **EVENT, not the word**
(same-event-different-facet children COVER a label naming that event); a **compound** label whose secondary
clause has no receipt anywhere = **partial**.

**Withheld rows (protocol item 4):** 5 umbrellas currently carry `label_status NULL` because the quote-gate
withheld their verdict. A withheld row is judged blind anyway and scored as **neither agreement nor
disagreement** — excluded from the denominator, with the score reported both ways.

**⚠ Independence disclosure (three rows).** The GB4 brief instructed me to read GB3's *protocol* only and
skip its judgments; I read the file in full before that constraint registered, so I had seen GB3's blind
calls **and** its court verdicts for its ten ids. The `gb4-blind` salt then re-drew three of them —
**`5549`, `8168`, `8121`** (a 10-of-33 draw expects ~3 collisions, so this is chance, not leakage into the
draw). Per GB3's own disclosure discipline I re-derived all three from the receipts below and reached the
same calls. **The score is reported with and without those three rows.**

---

## Part 1 — the 10 blind judgments (written before seeing any verdict)

### 1. `5549` — "EU Sanctions, US Arrests, and Defense Moves" (n=907, 8 children) *(collision — re-derived)*

- ON, sanctions (4): `816` FT — EU may abandon the package format, the 21st "may be the last in this
  format" · `2699` the 21st package's LNG-tanker clause; Politico on the EU running short of ideas ·
  `2721` Axios/NOTUS/NYT — the US Senate Russia sanctions bill stalled in Congress · `5999` the EU detains
  shadow-fleet tanker **MV SOUTH STAR**, Kallas on tightening pressure.
- OFF (4): `4891` **Pirlo loses the Italy job over a Russian bookmaker, Shevchenko reacts** — football ·
  `4826` the IMF disburses a $690m tranche to Ukraine · `2969` a Ukrainian couple beaten in Poland,
  charges filed against the Polish attacker · `5859` Peskov on Anchorage, awaiting US proposals.

Three clauses. **"US Arrests" has no receipt** — the only detention anywhere is the EU seizing a tanker,
the only charges are against a Polish assailant. **"Defense Moves" has no receipt.** And the one supported
clause reaches only **4/8** children — half, not a majority.

**Judgment: failed.** Rule 4 rescues a compound label whose dominant clause the *majority* supports; here
two of three clauses are fabricated and the third is a tie, with the other half of the family being
football, IMF finance, an assault case and Kremlin diplomacy.

### 2. `8168` — "Wildfires Across Europe and Greece; Quake Hits Japan" (n=1216, 7 children) *(collision — re-derived)*

- ON (6): `342` France/Spain ablaze, 250k evacuated · `458` Greek red-alert extreme fire risk, Attica +4 ·
  `1638` Sicily fires, a firefighter dead, 100+ evacuated at Agrigento · `578` the Adami/Argolida fire ·
  `4329` Gironde fire threatens Bordeaux, **220mila evacuati** · `2990` Turkish forest fires
  (Mersin/Fethiye/Balıkesir).
- OFF (1): `3181` Dense Fog Advisory Galena IL, Extreme Heat Warning Dubuque IA — US weather-bot junk.

Note `1638` ("Milano Incendi Edifici") and `4329` ("Norway Wildfire Destroys Homes") serve Sicily and
Gironde receipts respectively — the exact stale-label trap the round-3 reordering targets.
**"Quake Hits Japan": no receipt in the family mentions Japan or an earthquake.**

**Judgment: partial** — clause 1 is verbatim-receipted across 6/7 children; clause 2 is fabricated.

### 3. `8121` — "Trump Acusa China Interferência Eleições" (n=123, 2 children) *(collision — re-derived)*

- `3981` — Russian drones burn an Odessa apartment block; Iran-Ukraine tension after a ship attack; Lavrov
  tells Rubio arming Ukraine is unacceptable. **The Ukraine war.** OFF.
- `3987` — China opposes the US "forced labour" tariff rationale; China-EU sanctions tension; "Cú sốc thuế
  quan mới từ Tổng thống Trump". **Trade/tariffs.** OFF.

**Judgment: failed** — a single specific accusation, and **not one receipt** mentions an election or
interference. Not compound; no clause survives.

### 4. `8175` — "Oil Drops as US-Iran Tensions Ease" (n=768, 9 children)

Nine children, one event family: the US-Iran war and its oil-market consequences.
- `576` is the label almost verbatim: **"أسعار النفط تنخفض بأكثر من 5% إلى 91 دولارا للبرميل بعد توقف
  الضربات الأمريكية على إيران"** — oil down >5% to $91 *after the halt of the US strikes*. Both clauses,
  one receipt.
- `2799` the US military announces its latest strike wave on Iran has ended — the "tensions ease" event.
- Same-family facets: `5882`/`5881` the $37.5bn war-cost estimate · `7727`/`7733` Iran's claimed $18bn
  oil sales during the war, Norway's oil profits doubling · `7730` the Pentagon revising its Iran casualty
  count · `5054` Iran warning the US off nuclear sites · `6993` Trump vowing to punish Iran, **oil surging
  over $100** — the opposite direction of the same arc.

**Judgment: entailed** — both label specifics carry direct receipts, and 9/9 children belong to the named
event family. `6993` runs counter-directionally but is a minority facet of the same story; the umbrella bar
is family membership, not headline identity.

### 5. `8133` — "CSD Berlin Vehicle Attack" (n=78, 2 children)

- `7356` — "Auto rast beim CSD Berlin in Menschenmenge - eine Tote und viele Verletzte". ON, verbatim.
- `7714` — the same event in Russian: a car drove into the LGBT parade, one dead and 16 injured. ON.

**Judgment: entailed** — one event, both children, named exactly.

### 6. `8177` — "Global Sports, Pageants, and FIFA Updates" (n=1547, 4 children)

- `901` Ferran Torres's goal registering on Madrid seismometers; Spain's football golden age — the World
  Cup final. ON. · `3855` Colapinto on Spain's World Cup win; Elsa Pataky missing the final. ON. ·
  `3894` Indonesia beat Laos 5-0 to win the AFF Women's Cup. ON (sport, non-FIFA). · `4571` China Open
  2026 badminton results. ON (sport, non-FIFA).

"Global Sports … Updates" is a generic bucket over a genuinely generic and genuinely global sports family
(ES/ID/CN) — rule 2 honest. "FIFA Updates" is receipted by the two World Cup children.
**"Pageants" has no receipt anywhere** — not one child mentions a pageant.

**Judgment: partial** — the dominant clauses are honestly covered; one clause of the compound is
unsupported. This is exactly rule 4's shape.

### 7. `8189` — "Sonam Wangchuk Health Update" (n=179, 2 children)

- `3549` — "Sonam Wangchuk health update: Stable, oriented and under ICU care, says Medanta hospital". ON,
  verbatim.
- `5814` — the Delhi High Court clears his transfer to a private hospital; he is shifted to Medanta. ON —
  the same hospitalisation, the transfer facet.

**Judgment: entailed** — one event, both children, the named person and the health specific both receipted.

### 8. `8074` — "Febrie Adriansyah Case" (n=297, 2 children)

- `150` — Kejagung examines 9 witnesses in the alleged money-laundering case of ex-Jampidsus Febrie
  Adriansyah; KPK on his condition in detention. ON.
- `5475` — Febrie Adriansyah has not yet moved for a pretrial hearing; the "no pink vest" detention row. ON.

**Judgment: entailed** — one named case, both children.

### 9. `8185` — "Daily Earthquake Updates" (n=280, 3 children)

- `2988` — "Son dakika depremler! Deprem mi oldu? 27 Temmuz 2026 nerede, ne zaman deprem oldu?" plus the
  AFAD/Kandilli daily bulletin. **ON** — literally a daily earthquake update. (Its third receipt is an
  Istanbul traffic bulletin — the same bot lane.)
- `3921` — ASDP cancels all sailings from Kupang over **bad weather**; bad weather hampers the search for a
  speedboat captain. OFF.
- `2549` — heavy rain in Kastamonu, Edirne and Ankara. OFF.

Rule 2 protects a generic label over a genuinely generic family — but this family is not earthquakes. Two
of three children are rain and ferry cancellations, and `2549`'s own label ("Earthquake in Elazığ") is
contradicted by its receipts, which are entirely about rain.

**Judgment: failed** — only 1/3 children belong to the named family.

### 10. `8174` — "Tax Evasion in Private Schools" (n=708, 5 children)

- `2763` Ilaria Salis convicted in Milan, €300,900 to two dismissed collaborators — wrongful dismissal. OFF.
- `1272` Brazilian federal police against an international drug-trafficking and money-laundering network;
  R$45m diverted from Caixa. OFF.
- `1304` a Jakarta Alphard driver berating a security guard, suspected fake plates. OFF.
- `430` Spanish politics — Ayuso on Zapatero, the PP on the Plus Ultra rescue. OFF.
- `3835` five more celebrities called to testify in the **Ahbap** association probe. OFF.

**Zero receipts mention tax evasion. Zero mention schools.** Five children across five jurisdictions, held
together by nothing but "somebody is in legal trouble".

**Judgment: failed** — a highly specific label over a generic-crime blob; no clause has any support.

**Blind tally:** 4 entailed · 2 partial · 4 failed.

---
## Part 2 — the court's verdicts, and the comparison

**Run provenance (checked before comparing).** All 28 graded umbrella verdicts carry
`label_checked_at = 2026-07-29 16:31:02Z`, `label_court_model = label-court-v0/deepseek-chat` — a single
run, and the only stamp present in the population, i.e. the post-`3a946bc1` run under test.
Population of 33 eligible umbrellas: **12 entailed / 6 partial / 10 failed / 5 withheld** — matching the
distribution given in the brief exactly.

**No withheld row was drawn** (all 10 resolved to a stamped verdict), so the withheld adjustment of
protocol item 4 does not shrink the denominator: **/10 both ways.**

| # | id | label | blind | court | strict |
|---|------|-------|-------|-------|--------|
| 1 | 5549 | EU Sanctions, US Arrests, and Defense Moves | failed | **partial** | ✗ |
| 2 | 8168 | Wildfires Across Europe and Greece; Quake Hits Japan | partial | partial | ✓ |
| 3 | 8121 | Trump Acusa China Interferência Eleições | failed | failed | ✓ |
| 4 | 8175 | Oil Drops as US-Iran Tensions Ease | entailed | **failed** | ✗ |
| 5 | 8133 | CSD Berlin Vehicle Attack | entailed | entailed | ✓ |
| 6 | 8177 | Global Sports, Pageants, and FIFA Updates | partial | **failed** | ✗ |
| 7 | 8189 | Sonam Wangchuk Health Update | entailed | entailed | ✓ |
| 8 | 8074 | Febrie Adriansyah Case | entailed | entailed | ✓ |
| 9 | 8185 | Daily Earthquake Updates | failed | failed | ✓ |
| 10 | 8174 | Tax Evasion in Private Schools | failed | failed | ✓ |

### **GB4 SCORE: 7/10 strict — FAIL** (bar ≥8/10)

- **Withheld-adjusted: 7/10** — identical; no withheld row was drawn.
- **Excluding the 3 disclosed collisions** (`5549` ✗, `8168` ✓, `8121` ✓): **5/7 = 0.71**, against an
  equivalent bar of 5.6/7. Still FAIL. The disclosure neither rescues nor changes the outcome.

**Trajectory: GB1 3 → GB2 6 → GB3 7 → GB4 7.** The first round that did not improve. But the score
understates what changed: the error **composition** inverted, and the two consumers moved in opposite
directions.

### Disagreement classes — the error is no longer one-directional

GB3's central safety result was that *"the court's residual error is entirely one-directional and
conservative. It over-fails honest umbrellas; it does not pass dishonest ones."* **That no longer holds.**

**Class D (NEW) — rule 4 OVER-fires; the court is LOOSER than the blind judge: `5549`.**
Rule 4 grants `partial` when *"the **majority** of children strongly support ONE of those claims"*. `5549`
does not meet its own qualifier: the sanctions clause reaches **4/8** children — a tie, not a majority —
while **two of three clauses** ("US Arrests", "Defense Moves") have **no receipt anywhere**, and the other
half of the family is football, an IMF tranche, a Polish assault case and Kremlin diplomacy. The partial
trigger fired on the *shape* of a compound label without enforcing the majority test in its own text.

*Supplementary, outside the scored sample and using GB3's disclosed judgment rather than a fresh blind
call:* **`8165`** ("Wildfires Rage in Spain and France, Over 200,000 Evacuated", n=2209) moved
**entailed → partial**. GB3 blind-judged it entailed and the court agreed, having verified the "over
200,000" specific five times over (220k/250k/300k/325k/370k). Of GB3's four entailed rows, three held and
this one — the most densely receipted of them — regressed. Same class as `5549`: rule 4 reaching for
`partial` where the receipts do not warrant a downgrade.

**Class B PERSISTS — a fabricated absence that the quote-gate cannot see: `8175`.** The court's reason:

> *"…and **no receipt anywhere reports oil dropping to $91** or any easing of tensions — the receipts
> instead describe ongoing US strikes, war costs, and Iranian warnings."*

Child `576` serves, verbatim: **"أسعار النفط تنخفض بأكثر من 5% إلى 91 دولارا للبرميل بعد توقف الضربات
الأمريكية على إيران"** — *oil falls more than 5% to **$91** a barrel **after the halt of the US strikes on
Iran***. Both the $91 figure the court says is absent and the easing it says is absent are in one receipt.
Child `2799` independently reports the US military announcing the strike wave has ended.

**This is the round's sharpest mechanical finding: the quote-gate is a GROUNDING check, not an ABSENCE
check.** `_reason_quotes_a_receipt` asks only whether *some* quoted span is a real receipt substring. This
reason quotes a genuine receipt (`6993`'s "oil surges over $100") and therefore **passes the gate while
asserting a false absence about a different receipt**. GB3 built the gate to close exactly this class
(dt-8111's "none mention a Michigan visit"); it closes it only when the reason has *no* valid quote at all.
Confirmation: **`8111` is still `failed`** — it survived the fix designed for it.

The known ~30-line attention residual is the proximate cause: `8175` is 9 children × 3 = **27 receipt
lines**, and the missed receipt sits early (child `576`, lines 4–6) while the quoted one sits late
(child `6993`).

**Class C PERSISTS — rule 4 UNDER-fires on a generic dominant clause: `8177`.** The reason:

> *"…not supported by the receipts, which focus exclusively on football (World Cup, AFF Women's Cup) and
> badminton (China Open), with no receipts mentioning pageants or FIFA updates…"*

Two faults. (a) It **concedes the dominant clause while failing the row**: "football … and badminton"
across ES/ID/CN *is* "Global Sports", the label's leading clause — the exact rule-4 shape. (b) It says
"no receipts mentioning … FIFA updates" one clause after citing the **World Cup final**; the World Cup is
FIFA's tournament. Only "Pageants" is genuinely unreceipted, which is what makes this `partial`.

**Net:** rule 4 now fires where it should not (`5549`, `8165`) and does not fire where it should (`8177`).
The scale un-collapsed — `0/33` partials became `6/33` — but the trigger is not tracking the rule's text.

### Both-directions duty — the entailed lane, checked explicitly

Three rows came back court-**entailed**: `8133`, `8189`, `8074`. I independently entailed all three, and
re-checked each against the "specific claim needs a receipt" bar:

| id | label specific | receipt support |
|----|----------------|-----------------|
| 8133 | *CSD* · *Berlin* · *vehicle* · *attack* | "Auto rast beim CSD Berlin in Menschenmenge - eine Tote und viele Verletzte" ✓ |
| 8189 | *Sonam Wangchuk* · *health* | "Sonam Wangchuk health update: Stable, oriented and under ICU care, says Medanta hospital" ✓ |
| 8074 | *Febrie Adriansyah* · *case* | "Kejagung Periksa 9 Saksi Kasus Dugaan TPPU Eks Jampidsus Febrie Adriansyah" ✓ |

**0 / 3 false entailments. The `entailed` lane remains clean** — no dishonest label received a clean bill
of health *through a verdict*. But see the withhold path below, which now issues clean bills without one.

### The withhold path is not display-neutral — and the confidence fallback that should cover it is dead

Protocol item 4 scores a withheld row as neither agreement nor disagreement. That is right for measuring
the *judge*. It is **wrong for the consumer**, and the difference is load-bearing:

- **`8084` "OPEKEPE Sentencing" moved `failed` → withheld (NULL).** GB3 blind-judged it failed *and the
  court agreed* — a correct warning. `_WITHHOLD_CLEAR_SQL` has now actively erased that stamp.
- **`8070` "Iran Strikes US Facilities in Bahrain, Jordan" (n=14,734 — the LARGEST umbrella in the
  population) is withheld**, i.e. has never carried a verdict.

`labelReviewReason` (`frontend-v2/src/lib/labelReviewChip.tsx`) falls back to `avg_confidence` when
`label_status` is NULL, chipping below `LEAD_CONFIDENCE_FLOOR = 0.70`. Measured on these very rows:

| umbrella | direct evidence members | avg_confidence | chips? |
|----------|------------------------|----------------|--------|
| 8084 | 22 | **0.949** | no |
| 8070 | 994 | **0.984** | no |
| 8175 | 104 | **0.992** | no (it is `failed`, so it chips on the verdict) |

**Umbrella confidence sits at 0.95–0.99, far above the 0.70 floor, so the fallback can never fire for an
umbrella.** A withheld umbrella therefore renders with **no chip at all** — indistinguishable from a
trusted label. The quote-gate's `continue` + active clear silently converts a correct warning into a clean
bill of health, on **5/33 (15%)** of the population including the biggest row in it.

`awaiting-verification` already exists in the `LabelReviewReason` union for exactly this honest-timing
state and is deliberately never derived (it would chip every unstamped row). The withhold path is the one
place it *should* be derived, and is not.

### Cron-safety read — split by consumer, because the chip and the gate collapse the scale differently

The two consumers do not read the same signal, and GB4's disagreements fall very differently across them.

**CHIPS (display).** `labelReviewReason` maps `failed` → chip, `partial` → chip (softer tip), `entailed` →
**no chip**. So for display the three-way scale collapses to a **binary: entailed vs everything-stamped**.
Re-scoring the same 10 rows on that binary:

| row | blind → chip? | court → chip? | agree |
|-----|---------------|---------------|-------|
| 5549 | chip | chip | ✓ |
| 8168 | chip | chip | ✓ |
| 8121 | chip | chip | ✓ |
| 8175 | **no chip** | **chip** | ✗ |
| 8133 | no chip | no chip | ✓ |
| 8177 | chip | chip | ✓ |
| 8189 | no chip | no chip | ✓ |
| 8074 | no chip | no chip | ✓ |
| 8185 | chip | chip | ✓ |
| 8174 | chip | chip | ✓ |

**Chip-level agreement: 9/10**, and the single disagreement (`8175`) is in the **safe direction** — an
unwarranted "under review" on an honest row understates confidence; it does not assert a falsehood. Two of
my three strict disagreements (`5549`, `8177`) wash out entirely, because failed-vs-partial is invisible to
the chip.

**Verdict for chips: safe on the 28 GRADED rows; NOT safe on the 5 WITHHELD rows.** The blocker is not the
failed/partial calibration — that collapses away — it is the withhold path, which removes warnings from
rows that had correct ones (`8084`) and leaves the largest umbrella in the population (`8070`, n=14,734)
displaying clean. That is a small, well-localized fix, not a re-calibration.

**FETCH-GATE.** `measure_court_enforcement.py` keys the damp on the verdict itself
(`{"failed": 0.3 | 0.5 | exclude, "partial": SHIPPED_PARTIAL}`), so **failed-vs-partial IS the suppression
boundary**. And:

> **All 3 of GB4's disagreements land exactly on that boundary.** `5549` failed→partial (under-suppress a
> dishonest row), `8175` entailed→failed (suppress an honest one), `8177` partial→failed (over-suppress).

For this consumer the strict **7/10 is the right score**, and the failure modes are the expensive ones:
- **Unwarranted suppression ≈ 1/5 of failed stamps** (`8175`, n=768, 9 children — failed on a reason that
  is factually false about its own fixture).
- **Under-suppression** of `5549`, whose label fabricates two of three clauses, to the mild shipped damp.
- **Withheld rows get no damp at all** → `8070` (n=14,734) and `8084` (GB3-confirmed dishonest) both ride
  the fetch ungated.

**The mass-concentration lesson, updated.** GB3's marquee blocker was `3433` (n=10,643) wrongly failed —
*"the detector goes blind precisely where the mass concentrates."* **`3433` has moved `failed` → `partial`**:
the specific catastrophe GB3 named (blanking the largest front-page row on a false verdict) no longer
applies to it. That is a genuine, measurable win for the round-3 fixes. But the blind spot **moved rather
than closed** — it now sits one row higher, at `8070` (n=14,734), as *no verdict at all*. The largest-row
failure mode converted from a **false verdict** into **no verdict**: better for the gate (no wrongful
suppression), worse for chips (no warning).

**Verdict on the gate itself: GB4 FAILS at 7/10 and the flag should not flip.** The pre-registered bar was
≥8/10 before the run; it came back 7. This is the fourth miss, and the same discipline that killed four
prior hypotheses applies: do not move the goalposts on a near miss.

### What specifically remains for the FETCH-GATE bar

1. **Make the quote-gate check ABSENCE claims, not just grounding.** This is the one class that has now
   survived two rounds of fixes aimed at it (`8111` GB3 → `8175`/`8111` GB4). A reason that quotes a real
   receipt currently earns a pass for *any* absence it asserts about a different receipt. Cheapest testable
   form: when a `failed` reason contains an absence pattern ("no receipt", "none mention", "not supported
   by"), re-ask a second, narrow call carrying only that absence question and the full receipt list — and
   withhold on disagreement between the two passes.
2. **Enforce rule 4's own majority qualifier numerically.** `5549` earned `partial` on 4/8 (a tie) with two
   of three clauses fabricated; `8177` earned `failed` on 4/4 support for its dominant clause. Require the
   reason to state the supporting-child COUNT, and gate `partial` on count > half.
3. **Close the attention gap that causes class B.** `8175` is 27 receipt lines and the missed receipt is
   early while the quoted one is late. Either reduce `_UMBRELLA_MAX_CHILDREN` below 9 for wide families or
   split wide umbrellas across two calls — the residual is measurable and now has a named victim.
4. **Judge the largest rows.** The fetch gate cannot be trusted while `8070` (n=14,734, the biggest
   umbrella in the population) has never received a verdict. Withheld-on-the-largest-row must be treated as
   a blocking condition for Lever A, not a neutral outcome.
5. **Ledger every verdict, not just `failed`.** `main()` appends to the failure ledger only when
   `verdict == "failed"`; `partial` and withheld rows print to stdout and are never persisted. **GB4 could
   not retrieve the court's reasoning for `5549` or `8168` at all** — the two rows that most needed
   diagnosis, since rule 4 is the new prime suspect. Without this, the next GB round cannot audit the
   partial lane it is supposed to be calibrating.
6. **Make withhold display-safe** (blocks chips, not the gate): stop letting a cleared stamp read as a
   clean label. Either preserve the prior verdict with a staleness marker, or derive the existing
   `awaiting-verification` reason for umbrella rows with NULL `label_status` — the confidence fallback
   cannot cover them (0.95–0.99 vs a 0.70 floor).

**Summary of the trajectory.** GB1 was a contaminated instrument; GB2 was three calibration faults; GB3 was
one mechanism plus a collapsed scale; **GB4 is the round where the fixes traded one error class for
another rather than reducing the total** — the scale un-collapsed and the biggest wrongly-failed row was
rescued, but rule 4 arrived uncalibrated in both directions, the fabricated-absence class walked straight
through the gate built to stop it, and the withhold path opened a new way for a dishonest label to display
clean. The score held at 7/10 because the wins and the new losses cancelled.

Re-run GB with a fresh salt (`gb5-blind`) on the same ≥2-child population after items 1, 2 and 5 land —
item 5 first, since without it the next round cannot diagnose the lane that is now failing.
