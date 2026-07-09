# Where we are — dossier/investigation product state (2026-07-07)

A re-contextualization checkpoint. Read this first to get grounded.

## The frame (why any of this)
Atlas's product wedge = the **narrative analyst**. The proof that it's a product
= **investigations as use cases**. This session ran ONE flagship investigation
end-to-end as a dogfood, found real defects only a cold user surfaces, and fixed
the trust-critical ones.

## PRINCIPLE — math first, LLM only for the brief (Pedro 2026-07-07)
Reasoning-AI (LLM) is reserved for ONE surface: the **brief / synthesis prose**
(and only there, as the eventual paid-product report). Everything else —
connection edges, coherence/black-hole detection, assignment, clustering,
de-noising — must be solved with **mathematical + data-processing rigor** so the
data comes CLEAN BY ITSELF. Do NOT throw an LLM at a data problem because we
couldn't solve it with rigor. Embeddings + cosine + metric learning + whitening =
math/data (allowed everywhere). An LLM judging "are these connected?" = the
crutch (NOT allowed IN the product data path outside the brief).

**When the LLM IS used (the brief), it must be a GLASS BOX, not a black box**
(Pedro 2026-07-07). Math is inherently traceable; the one AI surface must EARN
trust by showing its work: the LLM never introduces a fact — it only connects /
rephrases things already shown by the math + the frozen receipts, and every claim
traces back to a specific pin/headline or a measured fact. Show the inputs the AI
was given; cite each claim; flag anything ungrounded. Atlas's whole thesis is
"honest situational awareness WITH THE RECEIPTS" — the AI surface follows the same
rule. This is a differentiator vs competitors' opaque "AI summary".

**But the LLM IS the reference ceiling.** Use it as the gold-label generator /
target during development (same pattern as the taxonomy κ benchmark and the recall
judge): the LLM says which edges are really connected → we GRADE each math
approach by agreement with it → we ship the math that best matches the AI ceiling,
knowing it's as good as the maximum referent without any AI in production. So the
LLM edge-verifier (task_28717ddd) is NOT shipped — its per-edge verdicts become
the REFERENCE labels; the math approaches (whitening task_60b7d395, OpenAI-space
task_ba1d0cbb) are scored against them. Grading is done here in the main thread
when all three report.

## The flagship investigation (the loop, working)
Thesis: *"Is Latin America undergoing a COORDINATED right-ward realignment
(driver = US assertiveness), or separate national stories that merely RHYME?"*
- Dogfooded live in prod: search → thread → pin → dossier. Pinned Colombia
  (De la Espriella), Peru (Keiko Fujimori), Argentina axis (Milei attends both
  inaugurations). The US-driver (Maduro/Venezuela intervention) has **no thread**
  — un-pinnable, a real gap.
- Answer: **qualified yes** — the Milei-attends-both-inaugurations thread carries
  the real, self-declared coordination (+ Fujimori pitching Peru into Trump's
  "Escudo de las Américas"); the rest connect by semantic proximity, which for
  same-language election news is largely a language artifact.
- Journey + verdict: `docs/research/flagship/2026-07-07-realignment-investigation-journey.md`.

## What shipped today (all live on prod)
1. **#1 basis-weighted connection verdict** (`a12a1ef8`): edges typed strong
   (shared actor/place, solid green) vs weak (semantic-only, dashed slate, NO
   weight-scaling). Verdict = CONFIRMED / SIMILAR-ONLY(caution) / split / isolated.
   Kills the "one connected narrative" over-claim. Viz spec from the
   visualization-engineer subagent.
2. **#2 standalone synthesis** (`a12a1ef8` + hardened `11cb3141`): `POST
   /api/v2/dossier/synthesize` — one grounded LLM pass (Anthropic→DeepSeek) →
   {headline, synthesis, gap}, leads the report + export. Hardened: per-node
   connectedness, off-topic-evidence self-check, undated-claims hedging.
3. **Dossier title** (`a7c75e1c`): leads with the synthesis headline + inline rename.
4. **#224 black-hole guard** (`33954739`): measured thread-coherence warning at
   pin time. Signal = avg member-to-centroid cosine (NOT country spread);
   loose/mixed/tight tiers. dt-52 (conflated "Colombia" thread = Spanish politics
   + a football fan-fest) → amber "mixed origin" badge; clean threads → nothing.

## The Frank test (the method that found the defects)
A cold editor read ONLY the generated report, zero context → **"I'd spike this."**
Precise blockers: (a) the conflated node's evidence is off-topic junk → discredits
the graph; (b) election outcomes asserted undated/unsourced; (c) `PS 15`
(Palestine) polluting the geography; (d) synthesis prose over-claimed coherence.
Lesson: **honesty labels ≠ standalone**; the DATA (conflation + dates) is the real
blocker. #1/#2/black-hole address (a)(c)(d); dates still open.

## The e5-compression problem (the root technical constraint)
e5 embeddings are anisotropic/compressed — cosines squished into ~0.88–0.97, so
semantic edges and coherence barely separate (measured: same/diff centroid gap
only 0.04 raw). This is WHY: 3 same-language stories auto-connect; raw coherence
can't cleanly flag the black-hole. Everything above works AROUND it.

### Options to fix it — MATH ONLY (per the principle above)
- **OpenAI embedding space** — measured to separate ~0.35 better than e5 (junk
  p50 0.542 vs e5 0.887). Already funded + used for the gate/archive. Recompute
  connection edges + coherence over OpenAI centroids (on-demand, small N = pennies)
  = a genuinely better space, pure cosine. **The real cure for the root cause.**
  IN FLIGHT (task_ba1d0cbb) for edges + coherence, head-to-head vs whitening.
- **Whitening (all-but-top-k)** — unsupervised de-compression, zero cost. Already
  used for neighbor discovery (gap 0.04→0.31, AUC 0.80→0.87). IN FLIGHT for edges
  (task_60b7d395). A hack on a compressed space — cheap win, not the cure.
- **Supervised metric (Mahalanobis)** — learn a linear transform from
  topic_members same/diff pairs (weak labels we already have). More robust than
  unsupervised whitening; a scoped training job. Candidate if OpenAI-space + whitening
  aren't enough.
- **Rank/percentile normalization** — relative nearest-neighbor rank not absolute
  cosine. Robust to compression, cheap. Neighbors already lean this way.
- **LLM pairwise "same-story?" judge** — NOT shipped (would be a data crutch),
  but KEPT as the **reference ceiling**: its verdicts are the gold labels the math
  approaches (OpenAI-space, whitening) are graded against. The AI defines the
  target; the math achieves it in production.

## In flight / queued
- **task_60b7d395 whiten-e5 edges** — RUNNING (separate chat). Will push + notify.
- Dates in the synthesis/evidence — open (bigger data lift).
- Robust alternatives above — not started (candidates for new chats).

## Workflow in play
Fixes/bugs get spawned to their own chats (one-click, isolated worktrees) so this
main thread stays on investigation/product-level work. Main thread = dogfood,
Frank test, decide direction.
