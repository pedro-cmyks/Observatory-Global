# Over-merge detector is BLIND to old topics (no embeddings) — the Natalia gap

**2026-07-21.** Pedro caught it live in the Brief: a Colombia country-edition
thread **"Natalia Villalba Murder Case"** (dt-726, born 2026-07-01) whose
receipts were unrelated diverse crimes — a Bogotá theft, a woman threatened with
a knife, and a **Chilean carabinero killed in Valdivia**. Classic over-merge +
label-stale + cross-country geo.

## What the pipeline did right

- **Court**: marked dt-726 `failed` (label ≠ receipts). Detection works.
- **Relabel** (now on the 30-min cadence, this session): **refused** it — the
  receipts are too diverse for DeepSeek to produce one honest label. Correctly
  identifies it as irreparable.
- **Member country signal** (correct `dynamic-topic-726` key): CO 24 · CL 13 ·
  ES 4 · EC 2 · AR 1 — 5 countries, none dominant. Unambiguous fusion.

## The gap: the over-merge detector never evaluated it

`detect_overmerge.py` reads `engine_version='v1-compat'` members **JOINed to
`signal_embeddings`** and runs 2-means over the member embedding matrix. But
dt-726's signals are **20 days old** (born 07-01), and embeddings are pruned at
**7-day retention** — so its old members have **no embeddings**, the JOIN drops
them below `min_members`, and the topic is **skipped** (1599/1660 evaluated;
726 not in the audit artifact). Every persistent old topic that keeps absorbing
fresh drift is invisible to the structural detector for the same reason.

So: the topic serves in the Brief (via the count over all members), the court
flags it, but the two tools that would FIX it — relabel (refuses) and
over-merge demote (blind) — both miss, and it survives with a lying title.

## Interim fix (this session)

dt-726 demoted active→candidate by the **country-diversity signal** (which needs
no embeddings): CO 24 + CL 13 with no dominant country = fusion. Reversible
(ledger `docs/research/overmerge/2026-07-21-orphan-country-demotes.jsonl`;
`UPDATE dynamic_topics SET state='active' WHERE id=726`).

## The real lane (next session)

Add an **embedding-free over-merge signal** to `detect_overmerge.py` so old
topics aren't invisible: for a topic the embedding path can't evaluate (members
below `min_members`-with-embeddings), fall back to **member country/entity
multimodality** — if the members split across ≥N countries with no dominant one
(and the court already failed it + the relabel refused it), demote. This closes
the "court-failed + relabel-refused + detector-blind" hole that Natalia exposed,
which affects every persistent old topic, not just this one.

Also worth measuring: how many active topics are in this state (old, failed,
detector-unevaluable). The Natalia case is one visible instance of a class.

## IMPLEMENTED + MEASURED (2026-07-21, commits `0c8e3657`→`65e86aaf`)

Built the embedding-free country-multimodality signal — but the measure-first pass
**overturned the premise above** and the lane was retargeted to the class the data
actually shows.

**Pure math (TDD):** `app/services/overmerge.country_multimodality(counts)` →
`{distinct, dominant_share, total, is_multimodal}` where `is_multimodal =
distinct >= TAU_COUNTRIES(3) AND dominant_share < TAU_DOMINANCE(0.60)`, env-tunable
via `OverMergeParams`. 12 new tests in `test_overmerge.py` (Natalia `{CO:24,CL:13,
ES:4}` → multimodal; `{CO:50,CL:1}`/`{CO:50,CL:1,ES:1}`/`{CO:20}`/`{}` → not).
`TAU_DOMINANCE` seeded at 0.60 (not 0.55) so Natalia's top share CO 24/41 = 0.585
clears it.

**The premise was wrong (measured):** `topic_members(v1-compat)` and
`signal_embeddings` **CO-PRUNE** for active topics — **0 of 518** active
court-failed topics are large-yet-embedding-blind (≥12 members, <12 embedded). The
174 embedding-unevaluable court-failed topics are all genuinely SMALL (≤11 members).
And dt-726 itself, re-inspected, has **37 members ALL embedded**, country dist
`{CO:18, CL:11, ES:8}` — it is an old BUCKET absorbing **fresh** cross-country
drift, not an old topic with pruned embeddings. So the as-written "embedding-
unevaluable fallback" catches **0**.

**The real blind spot:** a fusion of **3+** distinct stories has no clean *bimodal*
split, so the 2-means `gap_ratio` stays narrow and `decide()` **KEEPs** it — while
the country distribution fans across countries with no dominant one. So the lane was
retargeted: **court-failed AND embedding-lane KEPT AND country-multimodal** (a
superset of the spec's embedding-unevaluable case, which lands here as KEEP "too few
embedded"). 540 court-failed KEPTs → 178 too-few-located, 336 not-multimodal, **26
country-multimodal**. Survivors are flagged **BORDERLINE, never a direct DEMOTE**:
the raw country signal hand-checks ~73–87% (a World Cup, one war theatre are the FP
mode), so the DeepSeek "one story or two?" judge is the **required** confirmer.

**Judge-gated result + hand-check:** the judge confirmed **22** (kept 3, incl. 2
World-Cup single-stories it correctly spared). Hand-checking the 22 by *receipts*
(not the stale labels): ~20 are genuine fusions — dt-2451 (NL shooting + US rape
fugitive + MY fraud), dt-371 (IT healthcare + PL football + RU cyber), dt-1365
(SY/DE/NI), dt-551 (Iran war + Honduras + Mexico crash), dt-1994 (multi-conflict
ROUNDUPs), dt-320 (7-country Greek blob), dt-1668 (Ukraine + Iran = two wars) …;
**2 judge FPs** (dt-1190, dt-848) are pure World Cup, but both are court-FAILED
(labels ≠ their receipts), so demoting the mislabeled bucket is low-harm +
reversible. **Precision ≈ 91%** (20/22), above the 85 bar.

**Written (reversible):** run `m4-20260721-s42` demoted **23** topics active→
candidate (22 country-lane + 1 embedding-lane dt-842), ledger
`docs/research/overmerge/m4-20260721-s42-demotions.jsonl`, artifact
`2026-07-21-overmerge-audit.json`. Reversal:
`python -m scripts.detect_overmerge --revert m4-20260721-s42`.

**Residual / follow-ups:** (1) the 2 World-Cup FPs are a **sports-tournament FP
mode** the judge is inconsistent on (it kept dt-1543/dt-3048, demoted dt-1190/
dt-848) — a category-aware guard (a single tournament is inherently multi-country)
would spare them. (2) the person-overlap cross-country veto rarely fires
(`nlp_persons` sparse) so the judge carries the precision; richer NER would let the
veto pre-empt more FPs. (3) the genuinely embedding-unevaluable fallback still
exists (KEEP "too few embedded") and future-proofs the case if retention ever
prunes ahead of `topic_members`. Nightly Step 3.5c already runs `--judge` then
`--write`, so this lane is live continuously; `ATLAS_OVERMERGE_COUNTRY_FALLBACK=off`
disables just this lane.
