# Story Lens — the unified focus super-umbrella

**Date:** 2026-07-28 · **Status:** DESIGN APPROVED (Pedro, section-by-section) — plan next
**Owner conversation:** eclipse-dramatic-moment session (post gold-eval batches 1-2)
**Sibling patterns:** Eclipse Lens (`docs/superpowers/specs/2026-07-22-eclipse-dramatic-moment-design.md`),
focus propagation #234, Workbench pin-snapshot #227, country edition enrichment
(`2026-07-21-country-edition-enrichment-design.md`).

---

## 1. The idea (Pedro, verbatim intent)

> "cuando uno le hace open story, eso debería de abrir una super umbrella que cubre los
> trends, los eventos, las media signals, los anomalies, todo lo que se pueda meter ahí
> debajo."

Opening a story should open its **measured neighborhood** — everything Atlas already
knows that relates to that story, assembled live, every relation carrying a receipt.

**The motivating measurement.** The gold UI eval (batches 1-2, `docs/research/gold/
2026-07-30-ui-eval-v2-run.md`) scored **1/10 answered · 8/10 informed · NAV-LOSS
10/10**. The thesis it produced: *Atlas measures the right thing and then does not
render it.* Search offers 5 Berlin-Pride threads; the analyst opens one; the other 4
evaporate. Court verdicts, state-media flags, voice-mix, degradations — all measured,
all invisible at the surface the analyst actually lands on. The Story Lens is, in large
part, **the renderer those measurements already earned**.

## 2. Core decisions (each approved explicitly)

| # | Decision | Choice |
|---|---|---|
| D1 | Assembly | **Read-time** — the lens assembles live from measured relations; nothing persisted by browsing. |
| D2 | + Pinnable | **Yes** — pinning freezes the assembly as a snapshot into the EXISTING investigation machinery (#227). No parallel pin system. |
| D3 | Scope | **Everything** — siblings, signals, timeline, public attention, anomalies, voice-mix, physical events, markets. Build order staged; vision not trimmed. |
| D4 | Placement | **C — the console reconfigures** (Eclipse Lens pattern generalized), with ThemeDetail as protagonist panel inside (A-within-C). |
| D5 | Unification | **One lens for every focus type** — story, country, person/entity share one shell parametrized by anchor. "Irán the story" and "Irán the country chip" are the SAME lens. Search offers one door per subject, never two. |
| D6 | Capture verb | Inside the lens, "Start investigation" collapses into **Pin story** — one verb, existing machinery. |
| D7 | Entry | **Universal** — thread row, search result, universe body, Brief, stream signal, public-attention item, country chip, person chip: all enter the same lens. |

## 3. Non-redundancy with Start Investigation (Pedro's challenge, resolved)

- **Start Investigation**: anchor = free-text QUERY → a research plan + an EMPTY
  workspace curated pin by pin. Manual, persistent (L3).
- **Story Lens**: anchor = a CONCRETE subject → automatic assembly of its measured
  neighborhood. Zero work, ephemeral until pinned.

The lens is what Start Investigation makes you build by hand, pre-assembled. The
bridge is D2/D6: pinning the lens lands in the existing investigation store. The
redundancy risk materializes only if a THIRD assembly system is built — forbidden by
§5 (the lens composes existing endpoints; it does not duplicate them).

## 4. Anchor types (D5 — one shell, parametrized)

| Anchor | Example | Lanes resolved as |
|---|---|---|
| **Story/thread** | "Caspian ship attack" | siblings (new endpoint §6) · `signals?topic=` · `focus/{ref}/timeline` · public attention · anomalies of its countries · `voice-mix?country=` (dominant) · physical events · markets of its countries |
| **Country** | Irán chip | its stories (`threads?country_code=`) · country signals · country timeline (live channel) · attention · anomalies · voice-mix (exists) · country index (markets) |
| **Person/entity** | Netanyahu | stories where they appear (`threads?person=`, exists) · person timeline (mig-090 channel) · dominant countries → their lanes |

Country lens does not replace CountryBrief/country-edition/#234 — it CONVERGES them:
the #234 re-scope stays the mechanism, CountryBrief becomes the protagonist panel of
the country lens, and the dock gains the umbrella lanes. Convergence, not a fourth
country surface.

## 5. Architecture — zero fat endpoint in v1

**Client composes existing endpoints, one per lane, lazily** (only the visible dock
tab fetches; `fetchWarmCache` shim already exists — this avoids the `/drift`-class
fan-out the eval flagged):

- signals → `GET /api/v2/signals?topic=` (built this session; materialized member-set shape)
- timeline → `GET /api/v2/focus/{ref}/timeline` (person/country channels live on mig-090)
- attention → public-attention endpoints (trends [S] / wiki [W] / forum [F])
- voice-mix → `GET /api/v2/voice-mix?country=`
- anomalies → AnomalyPanel already self-scopes via `useFocusRelation`
- edges → `GET /api/v2/focus/{ref}/edge-diff` + replay
- markets → markets lane (country indices via the anchor's countries)
- country/person stories → `threads?country_code=` / `threads?person=`

**Frontend:** the lens is a focus MODE in App (EclipseMode pattern, but user-initiated).
URL `?lens=<anchor>` deep-linkable; exit = the existing focus-chip ✕. State machine
pure in `lib/` (vitest), context provider mounts once.

**Error handling:** a failed lane renders an honest empty WITH ITS REASON — never a
blank console (the mig-087-class lesson), never a silently missing tab. The lens
banner counts degraded lanes ("2 lanes degraded") so degradation is unmissable.

## 6. The one new backend piece: the sibling-finder

`GET /api/v2/story/{thread_id}/siblings` — **ranking-with-receipts, never merging.**

The measurement gift from the five NO-GOs: every signal that died as a MERGE gate
(entity-overlap → transitive collapse to a 96.2% component; whitening → kills
cross-lingual; used_t removal → false absorption) is **safe as a ranked list**,
because ranking writes nothing and has no transitive closure. The analyst's judgment
replaces the fixpoint.

- Candidate union (no single-signal argmax — the argmax-dispersion disease means
  cosine alone misses same-event fragments): centroid cosine ∪ rarity-weighted
  entity overlap ∪ shared-country + time proximity.
- Top-K with a floor, NOT a hard truth threshold; every sibling carries its WHY
  (`{basis, value}` → rendered as the #234 reason-chip: "↔ Caspian Sea · cos 0.91").
- Read-only, cached, paid bucket. No engine writes, ever.

## 7. UX — entering a story

**Entry = opening the story** (D7). Opening a thread no longer opens just a panel —
it opens the mode. Public-attention items resolve to a story via the existing
thread-pool match; honest absence when no mapping exists (the semantic-neighbor
identity-only lesson — never fabricate the bridge).

**Lens banner** (eclipse-ribbon pattern, no drama):
`◉ STORY: <label> · 4 hermanos · 12 países · ✕` — and **the verdicts live on the
banner**: court chip, coherence tier, degraded-lane count. Measured things, painted
where they cannot be unseen.

**Console mapping (C):**
- Map → flies + recolors to the anchor's countries (#234 mechanism)
- Threads → anchor pinned on top (eclipse pattern) + siblings with reason-chips
- Stream → `Story | All` tabs backed by `topic=`
- ThemeDetail → protagonist panel inside the lens
- Dock → lane tabs: Atención · Anomalías · Voice · Eventos · Mercados · Timeline

**Visual identity:** the story lens is CALM (scoping cyan). **Eclipse = the dramatic
special case of the same machinery** (tier total auto-enters with the takeover); one
"console as mode" architecture, two themes. v1 reuses the pattern without refactoring
eclipse internals.

**Mobile v1:** banner + scoped tabs over the existing IA (FrameSheet exists). No new IA.

## 8. Honesty rendering (the eval's direct fix)

Rendered ALWAYS, not carried silently in payloads:
- label-court status on the banner and on every sibling row;
- coherence/junk tier;
- ⚑ state-media on every receipt — **includes wiring `resolveTierChip` into the L2
  receipt renderers** (the eval's root-caused defect: it is imported only by
  Briefing.tsx and WorkbenchPanel.tsx today, so irna.ir/rt.com render unmarked in the
  console);
- per-lane degradation with reason;
- syndication collapsed with count, not repeated rows.

## 9. Pin story (D2/D6)

One button in the banner. Creates/extends an investigation via the existing store;
the pin snapshot (#227 pattern) freezes: anchor identity, sibling list WITH their
reason receipts, per-lane top items, verdict states, timestamps. Reopening a pinned
story shows frozen-vs-live separation exactly like the dossier does (frozen never
silently mixed with measured-now).

## 10. Staging

**V1 (build order):**
1. Sibling-finder + tests (union candidates, top-K + floor, receipts mandatory).
2. Lens shell — URL state, banner with verdicts, exit, threads anchor-pin + siblings.
3. Stream `topic=` tabs + dock lanes (Atención · Anomalías · Voice · Timeline), lazy.
4. Honesty rendering — banner verdicts + `resolveTierChip` wired into L2 receipts.
5. Pin story → #227 snapshot extension.

**V1.1:** physical-events + markets lanes (thinner data) · country/person anchors on
the same shell.

**V2 (Pedro, this session):** **article-body enrichment** — the Brief's scraping
machinery (`article_states` warm-read → fire-and-forget `enqueue_fetches` → client
polls the fill; excerpts under the SAME receipt identity via `renderReceipt`) feeds
the lens lanes. Not just headlines: fetched bodies, excerpts, coverage cross-read.
Zero new fetch machinery — the cache-first, never-blocking country-edition pattern
reused verbatim.

## 11. Hard boundaries

- The lens **never writes to the engine** — no merges, no topic mutation, no
  membership changes. Read-only + investigation pins only.
- No paid LLM in v1 (all lanes are math/already-measured; enrichment V2 reuses the
  existing sanctioned fetch surface, which is not LLM).
- ThemeDetail's contract untouched inside the lens.
- Eclipse machinery untouched in v1 (pattern reuse, not refactor; folding eclipse
  onto the shared shell is a later, separate decision).
- No third pin/assembly system (D2, §3).

## 12. Honest risks

- **Sibling quality on shredded events** — argmax dispersion can hide siblings from
  cosine. Mitigated by the candidate union + receipts (the analyst sees WHY and can
  discount). And the lens *visibilizes* shredding (≥18 US-Iran threads side by side
  = pressure to fix the identity layer, not makeup over it).
- **Fan-out** — lazy tabs + warm cache; watch request counts in the browser gate.
- **Mobile density** — v1 mobile deliberately minimal.
- **PA→story mapping coverage** — many attention items will have no story; honest
  absence is the designed outcome, not a defect.

## 13. Acceptance — measured, not asserted

- Build + vitest + backend tests green; browser-verified desktop + 375px.
- **The NAV-LOSS gate:** re-run ≥5 gold UI queries post-lens. Opening one
  Berlin-Pride-class thread must leave the sibling threads reachable with receipts.
  **The lens is shipped when NAV-LOSS falls, not when it compiles.**
- Honesty spot-checks: a court-failed anchor shows its chip on the banner; a
  state-media receipt shows ⚑ in L2; killing one lane's endpoint shows the reason,
  not a blank.

## 14. Open questions (deferred, not blockers)

- Stable story identity for deep-links when threads re-found (identity_key vs
  ephemeral id — the time-axis lesson suggests identity_key).
- Whether eclipse internals later fold onto the shared shell (v1: no).
- Sibling-finder tau calibration cadence (initial floor from existing measurement
  artifacts; recalibrate after the identity-layer work moves).
