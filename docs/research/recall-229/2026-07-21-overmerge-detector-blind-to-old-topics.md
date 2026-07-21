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
