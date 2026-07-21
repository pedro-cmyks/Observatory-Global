# Spec — Multi-hop transitive relationship chains ("the walked constellation")

**Date:** 2026-07-21 · **Status:** **v1 SHIPPED** on `v3-intel-layer @730787e2` (merged,
NOT deployed — awaiting Pedro's ok; reversible via `ATLAS_WALK_*` env). Validated
2026-07-21: core FAITHFUL, every LOCKED number exact (26 backend + 13 vitest green,
build clean). Remaining = 3 followups (blob-penalty multimodality, full-Dossier mount,
live §8 acceptance) — see `docs/superpowers/plans/2026-07-21-implementation-plan.md`.
Phase-0b LOCKED (REL_FLOOR 0.35 · HOP_CAP 3 · DEDUP_TAU 0.85 · rarity 0.30+0.68·norm_rarity) ·
**Wedge:** narrative analyst · **Discipline:** math-first, LLM only on sanctioned
surfaces, vanilla-CSS dashboard.

**References:** `docs/state/2026-07-21-analyst-journey-map.md` (§3.1 inert bridge
stars — this feature closes it) · `#234` (rarity-weighted relation) · `#226` (L4
markets, the parked endpoint) · probe script
`scratchpad/walk_probe.py` (read-only, reusable).

---

## 0. Intent — the reframe (read this first)

Pedro's motivating example is a **causal narrative**: Netanyahu → Gaza ceasefire →
Strait of Hormuz → oil transport → oil price, every arrow meaning *"affects / leads
to."* Atlas edges measure **none of that** — semantic cosine, shared country,
shared actor, co-occurrence are all **association: undirected, non-causal.** A chain
drawn over association edges and rendered as a chain silently imports causation and
direction the math never had, and each hop compounds it. That collision with the
honesty constraint (coverage ≠ corroboration, never assert) is *the* design problem —
not path-finding, which is trivial.

**The resolution (Pedro's own word): kinship.** The feature is **discovery, not
explanation.** It does not assert "A causes Z." It shows: *these two topics share a
distinctive, measured thing — here is the text — and to reach Z from your pin you
walk through B and C.* The analyst's mind supplies the causal reading; the app
supplies only the **honest measured walk with receipts.**

- **Hermano** = a *direct, measured* edge between two topics (with a receipt).
- **Primo** = an *indirect walk* — no direct edge, reached only by traversing
  intermediaries. **Degree = number of hops** (primo 1º / 2º / 3º…).
- The classifier that once said "oil price does not relate" is not wrong — it only
  had thin inputs. The walk **reaches** the oil-price story, but labels it honestly:
  *primo 2º–3º, no direct line, only this trail.* The thing the analyst's mind
  connected becomes **visible and honestly distanced**, never asserted.

---

## 1. The honesty model (what makes this shippable, not just clever)

1. **No causal arrow, ever — v1 is undirected.** A link = kinship (undirected). v1
   draws **no direction at all.** The tempting `▸` temporal-precedence marker is
   **dropped from v1**: Kalman lead/lag is measured on **coverage volume**, so it
   only says "attention on A rose before attention on B" — *not* event order, and a
   directional glyph on a causally-framed layout is a textbook post-hoc trigger.
   Temporal precedence is **one facet of the time axis** (§2.8 (c), #219) — NOT a
   markets thing; it feeds honest ordering/labels, gated behind an explicit "coverage
   order, not event order, not cause" affordance, but is **never** a direction glyph
   on the walk.
2. **The chain is never asserted.** Each *link* is measured; the *walk* is the
   analyst's. The **degree label** carries this by construction — "primo 3º" already
   says "indirect, 3 hops, they do not touch directly."
3. **Every hop carries a receipt.** basis (shared rare actor / theme-in-body /
   country / semantic) + the shared entity + the edge weight. Glass-box.
4. **Grounded themes only.** A "shared theme" is a term/entity/sub-cluster that
   *actually recurs* in the member signals, with measured frequency. An LLM may
   **label** a recurring cluster; it may **never invent** one. (Moving the theme
   extraction into free LLM prose would move the hallucination from the edge into
   the brief — forbidden.)
5. **Visual grammar — RADIAL constellation, never a linear chain (committed).** The
   §0 example is linear because that is the analyst's *mental* model; the **render is
   radial** — pin at center, kin arranged outward by degree. **Forbid any
   left-to-right / single-path "chain" layout** — a sequential row imports the very
   causation §0 exists to kill, and degree text labels do not defeat a spatial causal
   read (form beats label). Grammar:
   - node **size recedes** with distance-from-measured-ground (pin biggest → far
     primo smallest/faintest);
   - line **style**: solid = hermano (direct, measured) · dashed = primo (walked);
     more gaps / fainter = further cousin;
   - line **thickness** = accumulated weight (§2) — *honesty and brake, one number*;
   - line **color** = basis (why they relate), with a one-line legend.
   Validate the causal-read defeat with one quick user check before build.

---

## 2. The math (math-first, no LLM on the walk)

### 2.1 Substrate — reuse, do not rebuild
The walkable graph **already exists**. ~70% of this feature is wiring existing edges
to chain, not a new engine.

| Piece | Where | Detail |
|---|---|---|
| Sparse topic graph | `app/routers/universe.py:35,123-145` | top-k cosine neighbors, 768-dim e5 |
| Multi-basis edges + weights + shared-entity receipts | `app/routers/dossier.py:599-664` | semantic / country / shared-actor / text-mention / body-mention |
| Whitening (all-but-top-1) | `app/services/whitening.py:49,72` | `load_whitening()` / `apply_whitening()`; fit_n=99871 |
| Centroids | `dynamic_topics.centroid_vec REAL[]` | 768-dim; no pgvector → Python numpy cosine, ~1.6k topics = cheap |

### 2.2 Edge weight — ONE space (do not mix)
Per-hop weight = the per-basis dossier weight, in `[0,1]`. **Pick one vector space
and recompute in it** — the existing graphs live in **three incompatible spaces**
that must NOT be conflated: the Universe kNN graph is **raw** (`universe.py:132`,
`M @ M.T` on un-whitened centroids); pin↔pin edges use the **global** whitening
(`dossier.py:538`, threshold 0.50); neighbor edges use a **per-request refit**
(`dossier.py:746-754`, tau 0.40). So `0.50` and `0.40` are **not** interchangeable
and neither matches the raw Universe graph. **Commit to the global `whitening.py`
transform (`:49,72`), recompute the kNN graph in it, and re-measure a single walk
threshold there.** We reuse the *code/pattern*, not the raw Universe edge set — the
"~70% reuse" claim (§5) is adjusted accordingly.

### 2.3 The walk — from-pins, max-product
- **From-pins, not global.** The Universe is the map; an investigation is a *route*
  through it. Start from the analyst's pinned topics; expand outward. (Global
  all-pairs would need a pgvector index we don't have; from-pins is O(n) scan × few
  pins = cheap — confirmed in the probe.)
- **Accumulated weight = PRODUCT of the hop weights** along the path from the seed.
- **Depth brake:** expand a node's neighbors only while its accumulated weight ≥
  `FLOOR`. Depth follows the **real strength of the trail** — a strong trail reaches
  further, a weak one dies at 1º. The accumulated weight **is** the thickness of the
  far primo (§1.5) — one number, honesty + brake.
- **`FLOOR` — LOCKED (Phase-0b, 5 seeds, best-first-hop 0.544→0.863).** A fixed
  absolute floor is seed-sensitive: 0.20 self-terminates at 3º on a diffuse seed but
  **explodes to 5º+ on tight seeds** (confirmed). The **relative** floor alone does
  not hold either (REL 0.5 stabilizes depth but kills 3º primos; REL 0.35 keeps
  primos but leaks 4º on tight seeds). **The locked brake is RELATIVE + HOP-CAP, both
  required:**
  - **`REL_FLOOR = 0.35`** — expand while `(product-of-hops / seed_best_first_hop) ≥
    0.35` (a fraction of the strongest available trail, not an absolute);
  - **`HOP_CAP = 3`** — hard backstop, **load-bearing** (the relative floor leaks 4º
    on tight seeds without it).
  Measured: all 5 seeds then self-terminate at **3º (4º+ = 0)** AND the marquee
  cross-story primo survives — `dt-31 → Hormuz-fees (1º) → US-bombards-Iran (2º) →`
  **`[Oil & gas supply risk] "Iran Threatens Energy Exports" (3º, acc 0.249)`**.
  Expose `REL_FLOOR` as the "hasta dónde caminar" slider; `HOP_CAP` is fixed. 0.06
  absolute (19% of the graph) stays rejected.

### 2.4 Rarity — two levels (the #234 lesson, applied twice)
- **Actor/node level (fix the FORMULA, not just the gate).** The hard-cut on
  ubiquitous actors fires at `dossier.py:604-608` (df ≤ `_distinctive_df_max`,
  `:96-107`). **Removing the gate alone does NOT give a thin link** — the weight
  formula `max(w, min(0.98, 0.65 + 0.15·rarity))` (`dossier.py:629-633`) has a **0.65
  base**; a ubiquitous actor (df=14, rarity≈0.07) still scores **0.66**, above the
  0.50 semantic gate and 3× FLOOR, and that glue now **propagates transitively**
  through the walk — a *worse* #234 regression than the flat-view bug it cured. The
  fix is a **formula change (LOCKED, Phase-0b on real actor df)**: rarity scales the
  **base** — `weight = 0.30 + 0.68·norm_rarity`, with
  `norm_rarity = (1/df − 1/df_max)/(1 − 1/df_max)` (df_max = max actor
  document-frequency in view; df=1 → 1.0). Measured on dt-31's 229 actors: ubiquitous
  "donald trump" (df=29) drops **0.655 → 0.300** (below the 0.50 gate, barely
  propagates); a rare df=2 actor stays strong at **0.628**; crossover at the gate ≈
  df 3. *Apply the same formula to the existing #234 dossier code
  (`dossier.py:632-633`).*
- **Edge/connector level (NEW — Phase-0b sharpened).** Down-weight hops through
  **vague-blob connectors** (grab-bag topics like "Global Political Shifts…"), which
  glued the spurious cross-domain hops (dt-897 "Russian Cancer Therapy Drug" at 2º;
  dt-282/dt-863 in the dedup). **Blob ≠ hub, and neither degree nor cosine coherence
  separates them** (measured: a blob is coherent with its own under-merged fragments —
  all top-in-degree nodes scored 0.74–0.83). The measured discriminator is
  **membership multimodality** (the existing over-merge detector
  `app/services/overmerge.py` — 2-means over member embeddings → 2 substantial
  sub-clusters = fusion), with **2-hop neighborhood category-entropy** as a cheap
  first pass (genuine event-hubs `ent ≈ 0.0–0.6`; blobs `ent ≈ 2.0–2.9`). **Flag
  blob-ness UP FRONT** (intrinsic signal), *before* dedup and in-degree — the §2.6
  dedup is itself confounded by blobs, so do NOT derive blob-ness from post-dedup
  in-degree alone. Pipeline: **(1) flag blobs intrinsically → (2) dedup non-blob
  fragments (§2.6) → (3) edge penalty using the blob flag + merged-graph degree.**
  Genuine event-hubs (US-Iran, Russia-Ukraine) are preserved.

### 2.5 Promotion primo → hermano
If, at any point, a **direct measured edge** appears between the seed (or a pin) and
a topic previously reached only by walking, that topic **promotes** from primo to
hermano. Answers Pedro's *"a menos que lo pudiera probar"* — the proof upgrades the
relation.

### 2.6 Display dedup (Phase-0b) — after blob-flagging, before the §2.4 penalty
Fold same-event fragments in the reached set (greedy, whitened cos ≥ `DEDUP_TAU`) so
the walk shows one "US Strikes on Iran," not twelve near-duplicate centroids.
**`DEDUP_TAU = 0.85` (Phase-0b, raised from 0.75).** Characterized (no gold labels →
characterization, not gold-precision): 0.70–0.80 demonstrably over-merge distinct
stories (a blob folded "Messi & Lamine Yamal" with "New UK PM"); **0.85** folds
genuine same-event variants (WC-final variants 0.86; the US-Iran-strikes cluster
0.87–0.91) while distinct stories survive. Residual wrong-merges at 0.85 are **all
blob-driven** (dt-282/dt-863) — under-merge substrate debt handled by blob-flagging
(§2.4), not a lower tau (0.90 under-folds, losing same-event fragments). Order: **flag
blobs (§2.4) FIRST**, then this dedup, then the in-degree penalty. This is a *display*
mask over the substrate's under-merge debt — the real fix is engine merge-quality
(separate track), not the walk.

### 2.7 Typed-destination matching
Match energy/oil-price destinations by **category / word-boundary**, never substring
(the probe's "Ukraine political t**oil**" false positive). Use the topic `category`
(`Oil and gas supply risk`, `Fuel subsidy unrest`) + boundary term match.

### 2.8 Time is its own axis — versioned relationships (moved to its own spec)
Time is a first-class axis, orthogonal to markets (markets *uses* time, never owns it):
the constellation's edges are **versioned over time**, rendered in a **universal activity
timeline** (every focus type — thread / country / person / theme / anomaly / subject),
with a replay-vs-diff split on one shared time-state and a **two-layer anchor
(`identity_key` + entity)** that separates real narrative change from substrate churn.
This grew into its own surface — **full design in
`2026-07-21-time-axis-versioned-relationships.md`.** **DEFERRED from chains v1:** the
chains ship undirected + present-tense first, then become scrubbable / diffable on that
substrate. It reuses this spec's rarity formula (§2.4), the whitened edge substrate, and
#219 Kalman.

---

## 3. Phase 0 — the probe (DONE, measured on prod)

Read-only walk over **1,594 active topics**, whitening **loaded**
(`k=1, dim=768, fit_n=99871`). Seed `dt-31 [Armed conflict escalation]
"Trump Vows Continued Iran Strikes"` (n=488). Max-product walk.

**Floor sensitivity:**

| FLOOR | reached | 1º | 2º | 3º | 4º+ | behavior |
|---|---|---|---|---|---|---|
| **0.20** | 44 | 6 | 21 | 17 | **0** | dies naturally at 3º ✅ |
| 0.12 | 137 | 6 | 22 | 49 | 60 | explore; leaks into 4º+ |
| 0.06 | 303 | 6 | 22 | 52 | 223 | explodes (19% of graph) ❌ |

**The chain is real.** Hermanos (1º): Netanyahu Arrest Threat (0.544), Trump/Khamenei
(0.476), Iran+Russia Sanctions (0.471), Netanyahu Warns Iran (0.456), Trump Threatens
Strikes (0.442), Trump Backs Off Hormuz Fees (0.427). Genuine cross-story **primos**:
*Iran Threatens Energy Exports* `[Oil & gas supply risk]` at **3º / floor 0.20 (acc
0.249)**, *Iran Threatens Hormuz Closure*, *Trump Control Hormuz Strait*, *Russian
Fuel Crisis* (3º), *Oil and Gold Prices Amid Iran Tensions* (6º / floor 0.06). The
`Iran-strikes → Hormuz/energy-exports → oil-price` transitive primo **exists in
today's data**.

**Verdict: PARTIAL YES.** Meaningful primos surface, but genuine cross-story ones are
**diluted by same-event fragmentation** (→ §2.6) and a few **blob-glued spurious
hops** (→ §2.4 edge penalty). The three refinements above are the probe's forced
additions to the design. *(Phase-0b (§2.3) re-measured the brake across 5 seeds — the
single-seed 0.20 absolute is superseded by REL_FLOOR 0.35 + HOP_CAP 3.)*

---

## 4. Surface / UX

- **Lives in** `WorkbenchConstellation` (compact, where the analyst builds) +
  `DossierConnections` (full). The SVG boceto from the brainstorm is the visual
  language.
- **From-pins, analyst-walked.** Open with hermanos; a *"¿ver primos?"* control
  expands **one degree at a time**. The app never pushes the whole chain — the
  analyst walks it.
- **Every walked node is clickable + pinnable.** This is the fix for journey-map
  §3.1 (bridge stars that draw "look here" and disable the click): the bridges
  become **walkable and capturable**. Opening/pinning a primo grows the
  investigation — the flywheel turns.
- Honesty labels always visible: degree, *"sin línea directa,"* accumulated weight =
  thickness, basis = color, `▸` = measured precedence.
- Vanilla CSS + SVG. No Tailwind on the dashboard.

---

## 5. Build vs reuse

**Reuse (~70%):** Universe kNN graph, dossier 6-basis edges (weights + shared-entity
receipts), whitening, centroids.

**Build:**
1. From-pins weighted **max-product walk** + `FLOOR` brake (§2.3) — pure/testable.
2. Kinship labeling + degree + accumulated weight (§1).
3. **Blob-connector edge penalty** (§2.4) — in-degree from the kNN graph.
4. **Display dedup** of same-event fragments (§2.6).
5. Make constellation nodes **clickable/pinnable** (journey-map §3.1).
6. **Soften the #234 hard-exclude** (`dossier.py:96-107`) — applies to existing code.
7. Category/word-boundary typed-destination match (§2.7).

**No new engine. No LLM on the walk.** (LLM only if, later, we *label* a grounded
bridge theme — sanctioned, glass-box, deferred.)

---

## 6. Honest limits

- **Same-event fragmentation** dilutes primos (substrate under-merge debt). §2.6
  masks it at display; the real fix is engine merge-quality — separate track.
- **Blob connectors** — §2.4 penalty mitigates, does not eliminate.
- **Seed diffuseness** → weak hermanos (dt-31 first-hop weights only ~0.42–0.54 on a
  488-signal blob). A tighter, more specific pin gives higher-confidence chains.
- **Non-news endpoints** (the oil-price *instrument*, indices) are **not reachable
  today** — no market feed. Only the *news about* price variance is a node now.

---

## 7. Parked routes (future, not now)

- **L4 markets as a bidirectional, first-class LENS** — chip `task_23a4591b`. NOT a
  one-way destination. Three properties (Pedro, 2026-07-21):
  - **Bidirectional.** news→price AND **price→news**: from an index/commodity move,
    walk out to *which narratives moved in relation.* A market node is a valid
    **seed** of the walk, not only an endpoint. Market = a query/entry, never a
    *callejón.*
  - **Discovered, not mapped.** The market↔news edge is a **measured co-movement /
    lead-lag over time** (the scientific question = *do these relations exist?*),
    never a curated map that assumes the relation. This is the 2026-06-12
    relational-system thesis — "many things move in relation to each other" — and it
    is measure-first, same discipline as the Phase-0 probe.
  - **A new axis on the same rails.** Market becomes a first-class lens over ALL
    Atlas (like country / entity / time already are), mounted on the **same**
    infrastructure this spec uses: the walked constellation, the Universe field,
    focus-relation (#234), the Kalman movement feed (#219 — the natural home for
    lead-lag). **Time itself is a SEPARATE first-class axis (§2.8) — markets *uses*
    the temporal rails, it does not own them.** A market node is a *distinct kind*
    (measured series, never a news thread); every market↔news relation is
    honesty-labeled **correlation / precedence, never causation.**
- **Temporal lead-lag as a full first-class basis** (Kalman) — today only the `▸`
  label.
- **Global precompute** of the walk graph — needs a pgvector index; today from-pins
  O(n) is enough.

---

## 8. Acceptance

- Walk from a real pin surfaces ≥ 1 genuine **cross-story** primo at 2º–3º with
  visible receipt + degree (probe: Iran → energy-exports at 3º ✅).
- The brake self-terminates at the **hop-cap** on BOTH a diffuse and a **tight** seed
  (Phase-0b) — no primo-7º explosion.
- A ubiquitous-actor-only edge scores **thin** (~0.30) and does NOT glue unrelated
  pins across hops (#234 not regressed).
- Blob-connector spurious edges (the "Russian Cancer Therapy at 2º" class) are
  penalized out; genuine hubs are NOT.
- Same-event fragments fold at display (one "US Strikes on Iran," not twelve).
- **Honest negative:** a semantic-orphan pin returns an explicit "no measured kin"
  state, not a fabricated primo.
- Every node clickable + pinnable; pinning a primo grows the investigation.
- Render is **radial**, never a left-to-right chain; **no causal arrow anywhere**
  (v1 undirected).

---

## 9. Adversarial review (2026-07-21) — ledger

Full code-checked review folded in. Cited anchors verified accurate except the gate
citation (corrected to `dossier.py:604-608`).

**Blocking (fixed + Phase-0b LOCKED):**
- **S1 · depth brake seed-sensitive** → §2.3: **LOCKED** `REL_FLOOR 0.35 + HOP_CAP 3`
  (5 seeds, bfh 0.544→0.863: all self-terminate at 3º, marquee primo kept; relative
  floor alone insufficient — hop-cap is load-bearing).
- **S2 · "soften gate → thin link" is false** (0.65 base) → §2.4: **LOCKED** formula
  `0.30 + 0.68·norm_rarity` (trump df=29 → 0.300; rare df=2 → 0.628; crossover ≈ df 3).

**Honesty / correctness (fixed):**
- **A1 · `▸` least honest** (coverage ≠ event precedence; post-hoc glyph) → dropped
  from v1 (§1.1); returns only as a gated measured basis (§7 / #219).
- **A2 · three vector spaces** → §2.2: commit to the global whitening transform,
  recompute the kNN graph in it, re-measure one threshold; reuse pattern, not raw
  edges.
- **A3 · penalty vs dedup order + blob ≠ hub** → §2.4 / §2.6 (Phase-0b sharpened):
  **cosine coherence FAILS** to separate blob from hub; use **membership multimodality
  (`overmerge.py`) + category-entropy**, flag blobs **up front** (before the dedup that
  blobs confound), then dedup, then the in-degree penalty.
- **A4 · chain vs constellation fudged** → §1.5: committed radial, forbid linear
  layout, user-check acceptance.

**Pre-build hardening (open — track before/at build):**
- **B1** degree = hop-count of the **max-product** path, stated explicitly
  (max-product can prefer a longer strong path over a shorter weak one).
- **B2** measure `DEDUP_TAU` (§2.6, 0.75 unmeasured).
- **B3** honest **empty/orphan** state + the negative acceptance case (§8).
- **B4** incremental frontier cache keyed on seed-**set** + FLOOR; cap investigation
  size; define promotion semantics when a pinned primo becomes a seed.
- **B5** cross-language hops carry only semantic/shared-country basis (token-mention
  receipts are language-specific); label as such.
- **B6** real complexity is **O(n·frontier)**, not O(n); cap frontier, re-time on a
  tight seed.
- **B7** the edge receipt is the **raw recurring term**, never the LLM label; two
  clusters sharing an LLM label is not shared-theme evidence.

**Verdict:** not buildable as v1 was written; buildable after the S1/S2 math fix +
A1/A2/A4 resolution (all folded above) + the Phase-0b re-probe. B-list = normal
pre-build hardening.
