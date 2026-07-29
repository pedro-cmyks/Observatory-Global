# GATE GB — ROUND 2 blind hand-check of the umbrella label court (post-contamination-fix)

**Date:** 2026-07-29
**Protocol:** `docs/superpowers/plans/2026-07-29-identity-three-levers.md`, gate GB
**Round 1:** `docs/research/label-court/2026-07-29-gb-blind-check.md` — **FAILED 3/10**, root-caused to
receipt contamination (`_RECEIPTS_SQL` unscoped by `engine_version`/`quarantined`). Fixed in
`92c66ceb`; all 36 first-run umbrella verdicts void and reverted; re-run gave 15 entailed / 1 partial
/ 20 failed (was 2/5/29).
**Bar:** ≥8/10 agreement between an independent blind judgment and the court's verdict before the
cron flag flips.
**DB:** read-only (`SET default_transaction_read_only = on`). No writes, no commits.

## Method (identical to round 1, two changes)

1. **Fresh salt** (round-1 sample is burned): deterministic draw, 10 of the active umbrellas —
   `WHERE state='active' AND label IS NOT NULL AND is_umbrella = true
    ORDER BY md5(id::text || 'gb2-blind') LIMIT 10`. `label_status` deliberately **not** selected.
   Zero overlap with the round-1 draw.
2. **Receipts fetched with the FIXED court's own scoping**, so judge and court see the same lane:
   `topic_members`, `role='evidence'`, `engine_version = topic_members_engine_version()`
   (resolved live → **`'v1-compat'`**, printed by the fixture builder), `COALESCE(quarantined,false)=false`,
   `GROUP BY headline, country_code`, `ORDER BY max(tm.assigned_at) DESC`, ≤3 per child,
   `html.unescape` before reading. Family shape mirrors `_umbrella_family_for`: ≤10 children,
   biggest-first by `agg_n_signals`, each child's own served label shown beside its receipts.
3. Judgments written below **before** any court verdict was read (this file's Part 1 was committed to
   disk before the `label_status` query ran).
4. Only then `label_status` was fetched and compared.

Judgment scale (the court's own bar):
- **entailed** — the family coherently IS what the label says.
- **partial** — the label covers a real majority; a material minority is other stories.
- **failed** — the family is substantially other stories than the label claims.

**Explicit calibration instruction carried into this round** (from the blind-spot audit): a GENERIC
label honestly covering a GENERIC bucket counts as **entailed** — e.g. "Daily Earthquake Updates"
over a multi-quake roundup family is honest. The known residual is that the court's family prompt
frames umbrellas as *one event*, which may reject honest roundup labels; that bias must **not** be
imported into the blind judgment.

---

## Part 1 — the 10 blind judgments (written before seeing any verdict)

### 1. `8172` — "Wildfires in France and Spain Force Evacuations" (n=971, 4 children)

- `407` *Gironde wildfires…* — Gironde fire "contained", firefighters killed, fire 300 m from homes. ON.
- `405` *June Heatwave Death Toll* — ~5,700–6,000 excess deaths in the June canicule; one receipt is
  Normandy **drownings**. Adjacent summer-crisis, not wildfires/evacuations. OFF.
- `400` *France Heat Wave Deaths* — "España y Francia bajo fuego… miles de evacuados", "incendios
  históricos: más de 300 mil evacuados". Literally the umbrella label. ON.
- `1228` *France Heatwave Deaths* — 116,000 ha burned in France this year (az/tr wires). ON.

**Judgment: entailed** — 3 of 4 children (9 of 12 receipts) are exactly France+Spain wildfires with
mass evacuations; the one off child is heatwave mortality from the same summer.

### 2. `8182` — "Wangchuk Hunger Strike" (n=288, 2 children)

- `1743` *Wangchuk Hunger Strike* — Sonam Wangchuk ends 26-day hunger strike, "cockroach" protests. ON.
- `3575` *Support for Sonam Wangchuk* — Wangchuk on Dharmendra Pradhan's resignation, "victory of
  democracy". The direct political outcome of the same strike. ON.

**Judgment: entailed** — both children are the hunger strike and its immediate consequence.

### 3. `6543` — "European Heatwave Crisis" (n=557, 1 child)

- `696` *Europe Heatwave Crisis* — "France braces for fresh heatwave as fires rage on", "France, Spain
  battle 'monster' wildfires", Europe wildfire pictures. ON.

**Judgment: entailed** — the single child is the European heatwave/fire crisis the label names.

### 4. `5549` — "EU Sanctions, US Arrests, and Defense Moves" (n=907, 8 children)

- `816` / `2699` *EU Fails to Agree 21st Sanctions Package* — EU 21st package, LNG tankers. ON.
- `2721` *US Sanctions Bill Against Russia* — Senate sanctions bill stalling. ON (sanctions).
- `5999` *EU Targets Russian Shadow Fleet* — EU detains shadow-fleet tanker, Kallas. ON.
- `4891` *EU Sanctions Support Waning* — **Andrea Pirlo loses the Italy job over a Russian bookmaker;
  Shevchenko reacts.** Football. OFF.
- `4826` *UK Joins EU Ukraine Aid* — IMF disburses $690m to Ukraine. OFF (multilateral finance).
- `2969` *EU Sanctions for Torture of Prisoners* — a Ukrainian couple beaten in Poland; charges against
  the attacker. OFF (assault).
- `5859` *American Companies Want to Return to Russia* — Peskov on Anchorage / awaiting US proposals. OFF.

**Judgment: failed** — 4 of 8 children are football, IMF aid, a Polish assault and Kremlin diplomacy.
Only the sanctions clause of a three-clause label is evidenced; **no receipt shows a US arrest**.

### 5. `8131` — "Pralhad Joshi Appointed Education Minister" (n=67, 2 children)

- `6932` — "Pralhad Joshi replaces Dharmendra Pradhan as Education Minister"; takes charge. ON.
- `7672` — "Prahlad Joshi takes charge as Education Minister". ON.

**Judgment: entailed** — 6 of 6 receipts are the named appointment.

### 6. `8170` — "Global heatwaves, wildfires, and power outages" (n=848, 4 children)

- `367` *Italy heatwave…* — fourth tropical heat wave, 40 °C forecasts. ON.
- `668` *World Cup 2026 and Heatwave* — child label is off, but its receipts are FR/ES wildfires out of
  control, hundreds of thousands evacuated, "impossible to extinguish". ON by receipts.
- `2694` *Heatwave End Predictions* — UK Met Office next-heatwave forecasts. ON.
- `6523` *Summer Heat and Weather* — routine Vladivostok/Primorye daily forecasts (+28…+30 °C, showers).
  Ordinary weather, not a heat crisis. OFF-ish.

**Judgment: entailed** — this is a generic global heat/fire roundup label over a genuine global heat/fire
roundup family: 3 of 4 children (9 of 12 receipts) are heatwaves or wildfires. Noted over-claim: the
"power outages" clause has no receipt, and one child is routine daily weather.

### 7. `8070` — "Iran Strikes US Facilities in Bahrain, Jordan" (n=14,734, 10 children)

US–Iran children: `121` (Trump halts strikes for diplomacy), `577`, `2843`, `747` (US-Iran escalation),
`817`, `106` (US strikes on Iran) = 6.
Russia–Ukraine children: `37` (Ukrainian drones hit Wildberries warehouses), `1772` (Russia missile
strike near Kyiv), `440` (Zelensky meets UK PM; Moscow drones), `448` (Ukrainian drones near St
Petersburg) = 4.

**Judgment: failed** — two defects. (a) 4 of 10 children are a *different war*; this is the two-theatre
fusion. (b) Not one receipt shows the named event — Iran striking US facilities **in Bahrain or
Jordan**; the on-topic majority is the reverse direction (US striking Iran). The specific label is
unsupported and the family is a blend.

### 8. `8104` — "Health Myths and Facts" (n=123, 1 child)

- `3937` — "Does bleaching body hair cause spots?", "Is chimarrão on an empty stomach bad?", "Do skin
  diseases worsen in winter?" Brazilian health-explainer service journalism. ON.

**Judgment: entailed** — a generic label honestly describing a generic health-myth explainer bucket.

### 9. `8193` — "Heat Wave in Valencia" (n=229, 1 child)

- `4983` *Heat Wave Alert Spain* — AEMET announces a new heat wave from Wednesday affecting several
  zones; the fourth of the year; highs to 42 °C. Nationwide alerts.

**Judgment: partial** — the heat-wave family is real and the child is squarely on it, but **"in
Valencia" is not carried by a single receipt**; these are Spain-wide AEMET alerts. Right subject,
unevidenced locus.

### 10. `8186` — "US Blockade Iran Strait" (n=238, 2 children)

- `2817` *US Blockade Iran Strait* — Trump: US will destroy a bridge or power plant for each Iranian
  attack in the Strait of Hormuz. ON.
- `4713` *US Control of Strait of Hormuz* — Trump: Iranian funds will pay for ship damage; threatens to
  seize Iranian assets. ON.

**Judgment: entailed** — both children are the same US–Iran Strait of Hormuz coercion story. "Blockade"
is loose phrasing for a real, single, coherent confrontation.

### Blind distribution

**7 entailed · 1 partial · 2 failed.**

---

## Part 2 — the court comparison

Court output read only after Part 1 was written to disk. Post-fix re-run:
`label_court_model = label-court-v0/deepseek-chat`, `label_checked_at = 2026-07-29 15:34:54.719041+00`
(one batch, 36/36 umbrellas, 20 failure rows in
`docs/research/label-court/2026-07-29-label-court-failures.jsonl`).

**Verdict retrieval note (important).** Four of the ten now read `label_status = NULL`. They were
**not** unjudged: all four appear in the 15:34:54 failure ledger, and a relabel pass at
`label_updated_at = 2026-07-29 15:38:00` (`label_model = relabel-court-v1/deepseek-chat`) NULLed the
stamp afterwards. The court verdict for those rows is taken from the ledger. Their label text is
byte-identical to the `served_label` the court judged, except `8070` ("US **Sites**" → "US
**Facilities**") — semantically identical for judging. So all ten comparisons are like-for-like.

| # | id | label (truncated) | children | blind | court | agree? |
|---|----|-------------------|----------|-------|-------|--------|
| 1 | 8172 | Wildfires in France and Spain Force Evacuations | 4 | **entailed** | failed | ❌ two steps |
| 2 | 8182 | Wangchuk Hunger Strike | 2 | **entailed** | entailed | ✅ exact |
| 3 | 6543 | European Heatwave Crisis | 1 | **entailed** | entailed | ✅ exact |
| 4 | 5549 | EU Sanctions, US Arrests, and Defense Moves | 8 | **failed** | failed | ✅ exact |
| 5 | 8131 | Pralhad Joshi Appointed Education Minister | 2 | **entailed** | entailed | ✅ exact |
| 6 | 8170 | Global heatwaves, wildfires, and power outages | 4 | **entailed** | failed | ❌ two steps |
| 7 | 8070 | Iran Strikes US Facilities in Bahrain, Jordan | 10 | **failed** | failed | ✅ exact |
| 8 | 8104 | Health Myths and Facts | 1 | **entailed** | entailed | ✅ exact |
| 9 | 8193 | Heat Wave in Valencia | 1 | **partial** | entailed | ❌ adjacent, reason not borderline |
| 10 | 8186 | US Blockade Iran Strait | 2 | **entailed** | failed | ❌ two steps |

Scoring is strict per the round-1 protocol: agreement = exact match, or `entailed↔partial` adjacency
**only** where the written reason says borderline. `failed↔partial` adjacency is disagreement by
explicit rule. Row 9 is adjacent, but my written reason argued a specific defect ("'in Valencia' is not
carried by a single receipt") and never said borderline — so it scores as a disagreement, the same way
rows 6–7 did in round 1.

### **GB2 SCORE: 6 / 10 — FAIL** (bar: ≥8/10)

Distribution comparison, this sample: blind 7 entailed / 1 partial / 2 failed; court 5 entailed /
0 partial / 5 failed. Court over all 36 active umbrellas at the 15:34:54 run: **15 entailed /
1 partial / 20 failed**.

**This is a materially different failure from round 1.** Round 1 scored 3/10 and the two distributions
were irreconcilable (court 81% failed vs blind 60% entailed), which correctly pointed at a defect in
the instrument's *inputs*. Round 2 scores 6/10 with distributions in the same neighbourhood (56%
failed vs 20% failed on a 10-draw). The contamination fix moved the court from broken to
**arguably-calibrated-but-still-short**. Every round-2 disagreement is a judgment-call gap that can be
argued from the same receipts — none is the court reasoning about evidence users never saw.

---

## Part 3 — disagreement dissection

Direct answer to the pre-registered question: **the disagreements do NOT cluster on the roundup-label
class.** Exactly one of four (`8170`) is cleanly that class. The dominant shared mechanism across two
of the three court-stricter disagreements is different and, as far as I can tell, previously unnamed.

### The court reasons from CHILD LABELS over served RECEIPTS (2 of 4 disagreements)

The family prompt hands the judge each child's own label beside its receipts, and instructs that
"a child's own label can reveal it does not belong". In this sample **7 of 35 child labels (20%) are
stale relative to their own served receipts** — and in both discriminating disagreements the court's
verbatim reason cites exactly those stale labels.

`8172` — court reason: *"Most child stories focus on heatwave deaths or unrelated wildfire events in
Spain, not the specific France-Spain evacuation event named in the umbrella label."*

| child | its label | its actual served receipts |
|---|---|---|
| `400` | "France Heat **Wave Deaths**" | "España y Francia bajo fuego… **miles de evacuados**" · "incendios históricos: **más de 300 mil evacuados**" |
| `1228` | "France Heat**wave Deaths**" | "116,000 ha in France turned to ash this year" (×3, az/tr) |

Both children's receipts are *literally the umbrella label* — France/Spain wildfires with mass
evacuations — while their frozen labels say "heatwave deaths". The court read the labels and failed the
umbrella. Second defect in the same reason: it treats "unrelated wildfire events **in Spain**" as
disqualifying for a label that says "in France **and Spain**".

`8170` — court reason: *"…one child is about **World Cup 2026** with unrelated wildfire headlines."*
Child `668`'s label is "World Cup 2026 and Heatwave"; its three served receipts are Arabic wires on
uncontrollable France/Spain wildfires and mass evacuation. The court explicitly saw that the headlines
were wildfires and still discounted them because the child label said World Cup — i.e. it named the
conflict and resolved it the wrong way.

This is a labels-over-receipts inversion, and it is self-reinforcing: label-court failures feed
`relabel_court_failed.py`, so stale child labels degrade parent verdicts, which trigger relabels of
parents rather than the children that caused the misread.

### The roundup / "one event" framing (1 of 4, plus a contributing half)

`8170` is also the pure roundup case: label "Global heatwaves, wildfires, and power outages" over a
family of Italy + UK + Russia heat and FR/ES fires. Court reason: *"child stories cover **regional**
heatwaves in Italy, UK, and Russia, **not global** heatwaves…"* — it refuses to accept that a set of
regional heatwaves constitutes "global heatwaves". That is the pre-registered residual (the family
prompt's single-event framing rejecting an honest roundup label), reproduced exactly.

`8172` is roundup-adjacent in a weaker sense — a multi-facet single crisis (fires + heat deaths +
burned area) under a label naming one facet — but its reason is dominated by the stale-label mechanism
above, so I do not count it as roundup.

### Label literalism — arguably a fair court catch (1 of 4)

`8186` "US Blockade Iran Strait". Court reason: *"describes a blockade, but the child stories focus on
threats and asset seizure, not an actual blockade."* On re-reading, the court is right on the merits:
no receipt shows a blockade; they show Trump threatening to destroy a bridge or power plant per Iranian
attack and to seize Iranian assets. My "entailed" accepted "blockade" as loose phrasing for a coherent
confrontation. **I concede this one to the court** — it is a real over-claim in a served label. The
strict protocol still counts it as disagreement, and it should: a hand-check that quietly re-scores
itself after seeing the answer is not a gate.

### One disagreement runs the OTHER way — the court was lenient (1 of 4)

`8193` "Heat Wave in Valencia" — court **entailed**, blind **partial**. The single child serves
Spain-wide AEMET alerts ("varias zonas", "cuarta ola de calor", 42 °C); no receipt mentions Valencia.
The court accepted an unevidenced geographic narrowing. This matters for the follow-up: the residual is
**not a monotone strictness bias** that a single "be more lenient" prompt tweak would fix. Tightening
the roundup framing alone would move `8170`, leave `8172` and `8186` where they are, and could push
`8193` further into false-entailment.

### Structural note: degenerate one-child "families"

3 of the 10 drawn umbrellas (`6543`, `8104`, `8193`) have exactly **one** active child. The family
question — "do the children belong to the family the label names?" — is vacuous with one child, yet
these rows still consume a judgment and a stamp. The court said entailed on all three; I disagreed on
one. Routing single-child umbrellas to the story lane (headline-identity question) rather than the
family lane looks like a cheap, separable improvement.

### Incidental operational finding (outside GB's scope, worth a chip)

The relabel pass at 15:38 stamped `label_model = relabel-court-v1` and NULLed `label_status` on 12 of
the 20 failures — but for `8172`, `5549`, `8170` the rewritten label is **byte-identical** to the one
that just failed, and for `8070` it changed only "Sites"→"Facilities". Net effect: the front page lost
its honesty stamp without the label improving, and the next court pass will re-judge and re-fail the
same strings. A relabel that reproduces the failing label should leave the `failed` stamp in place
rather than clearing it.

---

## Part 4 — verdict

**GATE GB2: FAIL — 6/10 (bar ≥8/10). Do not flip `ATLAS_COURT_UMBRELLAS`.**

The contamination fix (`92c66ceb`) is confirmed effective and should stand: the court is now reasoning
about the receipts the product actually serves (`engine_version='v1-compat'`, unquarantined,
`assigned_at`-ordered), and the round-1 pathology — verdicts driven by evidence no user ever saw — does
not appear anywhere in this sample. Score moved 3/10 → 6/10 and the distributions converged.

What remains is genuine calibration, in **three separable pieces**, only one of which is the
pre-registered roundup hypothesis:

1. **Labels-over-receipts inversion (new, largest).** 20% of child labels in this sample are stale
   against their own served receipts, and the court cites them to fail umbrellas whose receipts
   support the label. Candidate fix: instruct the family prompt to prefer receipts when a child's
   label and its receipts conflict — or drop child labels from the prompt entirely and A/B the two
   prompts against this same 10-umbrella fixture.
2. **Roundup / single-event framing (pre-registered, confirmed once).** A generic label over a
   genuinely generic family must be able to reach `entailed`; "regional heatwaves in Italy, UK and
   Russia" *is* "global heatwaves".
3. **Single-child umbrellas** should not be tried by the family question at all.

Note that fixes 1 and 2 both push toward leniency while `8193` shows the court is already too lenient
on unevidenced specificity — so the next round must re-measure the false-entailed side, not only the
false-failed side, or it will trade one error for the other.

Suggested next gate: apply fix 1 (+2, +3), re-run `--only-umbrellas` against prod, and re-blind on a
**third** salt — this sample is now burned. Round-1's sample (`gb-blind`) and round-2's (`gb2-blind`)
are both spent.

**DB:** read-only throughout; no writes, no commits, one artifact (this file).
