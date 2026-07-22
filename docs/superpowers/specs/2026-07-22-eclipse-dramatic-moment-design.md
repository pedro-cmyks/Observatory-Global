# Eclipse — the dramatic moment + the Eclipse Lens (design)

**Date:** 2026-07-22
**Status:** DRAFT — awaiting Pedro's review (brainstormed with the visual companion)
**Owner track:** global app chrome (L1 Brief + L2 console) + the attention-eclipse measurement
**Sibling spec (do NOT touch):** `docs/superpowers/specs/2026-07-22-under-the-radar-rescoped-coverage-gaps-design.md`
(the dock "Under the Radar" tab → coverage-gaps; may be in flight).

---

## 1 · Problem & intent

An **attention eclipse** fires when the window's coverage concentrates on one dominant
story (`attention_eclipse.py:66`, `GET /api/v2/attention/eclipse`). It is genuinely
**rare by design**, and today it renders as a bland dock tab (`EclipseLens.tsx`) that is
empty most of the time. Per the sibling spec, that dock tab is being **retired to
coverage-gaps**, and the eclipse "under the radar" list leaves it.

Pedro's decision (2026-07-22): the eclipse should become a **rare, spectacle-grade
MOMENT** — *"la pantalla se vuelve negra o cambia algo, estilo el Eclipse de Berserk"* —
that **replaces the retired "crisis mode" in spirit**. When a genuine world-eclipsing
event happens, the app **transforms**: a one-time cinematic takeover, then the whole
console becomes an **Eclipse Lens** that reframes every surface around the eclipse and,
crucially, **its shadow** — the consequential stories being drowned out.

This is a **visual design task**. It reuses the existing `/api/v2/attention/eclipse`
read (with measurement hardening, §4) and repurposes the now-freed `EclipseLens`
component. It does **not** touch the coverage-gaps/under-the-radar work.

## 2 · Measured frequency (why the trigger must be guarded)

Per-day coverage concentration, last 8 days (measured 2026-07-22 from `topic_members`
evidence counts):

| Day | Field size | Top-1 share | Would fire? |
|---|---|---|---|
| 07-22 | 2503 topics | 3.0% | no |
| 07-21 | 1218 | 6.5% | no |
| 07-20 | 2875 | 3.9% | no |
| 07-19 | 788 | **26.7%** (one topic = 4,325 members) | yes — but likely a **black-hole/over-merge artifact** |
| 07-17 | 1194 | 13.5% | no |
| 07-15/16/18 | 31–53 (mid-ETL thin days) | 16–35% | **false** — thin substrate, not a real event |

**Findings that shape the design:**
- On **healthy full-field days** the top story sits at **3–13%** — well under the 20%
  gate. A real eclipse is a once-in-a-few-weeks event.
- The bare 20% gate has **false-positive modes**: thin-substrate ETL days, and a single
  over-merged mega-topic. An **auto-firing full-screen moment must guard against these**
  or it burns trust.

## 3 · Concepts, tiers & naming

**Two orthogonal measurement axes** (they are *not* opposites — they complement, and
requiring both is a built-in artifact filter):
- **Country-dominance (spread):** fraction of countries whose #1 story is the dominant
  one. "One story on everyone's front page." Spatial.
- **Entropy-collapse (field went dark):** the field's coverage-diversity (Shannon
  entropy) drops sharply vs its trailing 7-day norm. Temporal.

A black-hole inflates volume + collapses entropy but stays **low** on country-dominance
(it isn't genuinely #1 in each country independently) → requiring both axes catches it.

**Tiers:**
| Tier | Condition | Treatment |
|---|---|---|
| **none** | guards fail, or neither axis lit | nothing (normal app) |
| **partial** | guards pass, one axis lit (or moderate composite) | a row in the **Anomaly panel**. No chrome change. |
| **total** | guards pass, **both axes lit** | the **spectacle** — takeover → Eclipse Lens. Also appears as an anomaly row. |

**Naming (avoid collision with existing code):** the codebase already has
`EclipseLens.tsx` / `EclipseStrip.tsx` / `lib/attentionEclipse.ts` (the under-radar
surfaces). To avoid confusion:
- The new **global mode** context = **`EclipseModeContext` / `useEclipseMode`** (the
  takeover + ambient chrome + lens state machine).
- The reconfigured console = **"Eclipse Lens (mode)"** — a *state*, not a new component.
- The existing `EclipseLens.tsx` (the under-radar list) is **repurposed** as the
  **"stories in its shadow"** list (`selected[]` from the endpoint). The eclipse
  `selected` set = **the shadow**.

## 4 · Measurement v2 (backend)

Extend the existing service + endpoint; keep the pure-logic separation
(`app/services/attention_eclipse.py` stays pure; the router runs SQL and calls it).
Bump the contract to **`attention-eclipse-v1`** (additive — existing consumers keep
working; `eclipse: bool` stays for back-compat).

### 4.1 SQL additions (`attention_eclipse.py` router `_ECLIPSE_SQL`, :31-60)
- Add `dt.identity_key` to the `SELECT` (:49-52) → carry into `dominant` + `selected`
  payloads for **churn-resistant episode dedup** of the takeover. (`identity_key` exists,
  `migrations/048_dynamic_topics.sql:23`, UNIQUE.)
- Add `array_agg(DISTINCT s.country_code)` per topic → **country footprint** for the
  dominant and each shadow item (needed to color the map; today only a scalar
  `COUNT(DISTINCT country_code)` breadth is returned).
- **Country-dominance query (new CTE / second query):** per country (with ≥ `MIN_CC_SIGNALS`,
  e.g. 5), argmax topic by volume; `country_dominance = (# countries whose top topic ==
  the global dominant) / (# qualifying countries)`.
- **Entropy now:** `H_now = -Σ share_i·ln(share_i)` over the window's topic-share
  distribution (already have shares).

### 4.2 Entropy baseline (7-day)
- Compute `H` per day for the trailing 7 days (same member-count basis) → `H_baseline =
  median`. `entropy_collapse = clamp((H_baseline − H_now) / H_baseline, 0, 1)`.
- Cheap daily aggregate; storable in a tiny table or computed on the fly (7-day
  `topic_members` reach is within hot retention). **Cold-start honesty:** if <3 baseline
  days exist, mark `entropy_collapse: null` and fall back to country-dominance + top1/HHI
  (never fabricate a baseline).

### 4.3 Guards (kill artifacts) — pure, in `select_under_radar`/a new `classify_tier`
- `field_size ≥ MIN_TOPICS` (kills thin-ETL days).
- `total_coverage ≥ MIN_TOTAL`.
- dominant is **non-junk, non-roundup**, `mean_cohesion ≥ COHESION_FLOOR` (kills the
  07-19 black-hole).
- dominant breadth floor: `language_breadth ≥ 3` AND `country_breadth ≥ 8` (a local
  mega-topic can't be a "world eclipse").

### 4.4 Tier decision (pure)
```
if not guards_pass:            tier = "none"
elif dom_high and coll_high:   tier = "total"     # both axes
elif dom_high or coll_high:    tier = "partial"   # one axis
else:                          tier = "none"
```
`dom_high = country_dominance ≥ DOM_TAU`; `coll_high = entropy_collapse ≥ COLL_TAU`.
Also expose a continuous `intensity` (blend of `top1_share`, `hhi`, dominant breadth,
`country_dominance`, `entropy_collapse`) for future tuning.

**All thresholds are MEASURE-FIRST calibration constants** (`DOM_TAU`, `COLL_TAU`,
`MIN_TOPICS`, `MIN_TOTAL`, `COHESION_FLOOR`, `eclipse_top1`). Start conservative;
calibrate on history. Guards already neutralize the two measured false-positive modes.

### 4.5 Response additions (`attention-eclipse-v1`)
Add to the top-level object: `tier: "none"|"partial"|"total"`, `intensity: float`,
`axes: {country_dominance, entropy_collapse, top1_share, hhi}`. Add to `dominant`:
`identity_key`, `countries: [cc,…]`. Add to each `selected[]` item: `countries: [cc,…]`.
Keep `eclipse: bool` = `tier == "total"` for back-compat with the Brief `EclipseStrip`.

### 4.6 Tests (`test_attention_eclipse.py`, extend)
Guard rejects thin field / low-cohesion dominant; tier logic (both/one/neither);
entropy-collapse cold-start → null + graceful fallback; country footprint shape;
back-compat `eclipse == (tier=='total')`.

## 5 · Frontend architecture

### 5.1 `EclipseModeContext` (new — mirror `CrisisContext.tsx:42-134`)
- **Poll** `/api/v2/attention/eclipse` on mount + `setInterval(~4 min)` (reuse
  `lib/attentionEclipse.ts` helpers; do **not** add a competing fetch — this becomes the
  single eclipse read; `EclipseStrip`/AnomalyPanel consume the context).
- **Derives** `tier`, `dominant` (+`identity_key`,`countries`), `shadow = selected[]`,
  `axes`, `window`.
- **Mode state machine** (localStorage-backed, key `atlas.eclipse.v1`):
  `normal → takeover → ambient ⇄ muted`, plus `auto-exit`. Exposes
  `{tier, dominant, shadow, mode, engage(), mute(), restore(), dismissTakeover()}`.
- **Episode dedup:** takeover fires **once per episode**, keyed on
  `dominant.identity_key` + an episode id (first-seen timestamp). Re-arms when tier
  drops below `total` then returns, or when `identity_key` changes.
- **Auto-exit:** when polled `tier !== 'total'`, clear ambient/muted → `normal` (the
  world un-darkens itself). Next total eclipse re-arms the takeover.
- **Mount** high in the tree so it wraps App **and** Brief: in `main.tsx` (around the
  `AuthProvider`/`AppBriefKeepAlive` region, `main.tsx:94-122`) or as the outermost of
  the `App()` provider stack (`App.tsx:2555-2568`). It also toggles a **body-level**
  class (`document.body.classList.toggle('eclipsed', …)`) so global desaturation covers
  the whole document, not just the `.app` div.

### 5.2 Takeover overlay (Phase A) — new component, `createPortal(document.body)`
- No top-level overlay host exists today (grep clean) → portal to `document.body` from
  the provider so it sits above console **and** Brief and survives route hops.
- Content: eyebrow "TOTAL ECLIPSE OF ATTENTION", the dominant story label, honest stats
  (`#1 in N countries · X% of coverage · L languages`), the honesty line
  ("coverage-volume proxy, not audience eyeballs — ranked, not certified"), and two
  actions: **"Enter the eclipse ▸"** (`engage()` → ambient + Eclipse Lens) and **"The
  stories in its shadow →"** (engage + focus the shadow list).
- Animation: darkness veil in → eclipse disc + corona → text. **`prefers-reduced-motion`
  → static dark state, no sweep/corona/pulse, instant.**

### 5.3 Ambient chrome (Phase C) + Muted
- `.eclipsed` global desaturation (`filter: grayscale(...)` on body/app root). **Note:**
  existing `backdrop-filter: blur()` on header/panels (App.css 67/279/357) can interact
  with an ancestor `filter` — verify in-browser; if it misbehaves, desaturate the console
  container rather than `body`, and toggle a `.eclipsed` class on `.app` (`App.tsx:1461`,
  next to `crisis-mode`).
- **Ribbon** under the command bar (`App.tsx:1464-1511`, styled like
  `.app.crisis-mode .command-bar`, `App.css:485`): "◑ Eclipsed · «dominant» is eclipsing
  the world — #1 in N countries · X%". Carries **✕ exit eclipse** → `mute()`.
- **Muted:** normal chrome + a small **eclipse sigil** pinned on the **map corner** →
  click `restore()` to re-enter the lens. Still flags the fact; auto-clears with the data.

### 5.4 Entry flow (Brief → L2)
- **Brief masthead symbol** (`BriefNewspaper.tsx:1137-1169`): a small eclipse marker in
  `brief-masthead-right` near the live chip (:1149), gated on `shouldShowEclipse(eclipse)`
  / `tier==='total'`. (The `EclipseStrip` at :1703-1708 stays — coverage-gaps §4.)
- **"Open Console"** (`BriefNewspaper.tsx:1153-1158`, `goToAtlas`): when a total eclipse
  is active, branch to add `entry=eclipse` (today `goToAtlas` always sets `entry='brief'`,
  :596-603 — needs a distinct value).
- **App side:** `entrySource` (`App.tsx:367`, reactive on `location.search`) — add an
  `entry === 'eclipse'` branch that fires the takeover **once** via the established
  run-once pattern (`deepLinkProcessedRef`, `App.tsx:267/738`). App is **not remounted**
  crossing Brief→console (keep-alive, `main.tsx:38-60`), so this is an effect on
  `location.search`, not mount.
- Independent of entry: if the poll observes `tier==='total'` while already in L2 and the
  episode hasn't been seen, fire the takeover there too.

### 5.5 Partial eclipse → Anomaly panel row
- `AnomalyPanel` **consumes `useEclipseMode()`** (no new fetch — reuse the shared poll).
  Render an **"ATTENTION ECLIPSE"** section (right column, between THEME SPIKES ends
  `AnomalyPanel.tsx:239` and PUBLIC ATTENTION `:242`), mirroring the theme-spike row
  markup (`:227-236`), **only when `tier !== 'none'`**. The row names the dominant story +
  its share; when `tier==='total'` the row doubles as an "Enter the eclipse" shortcut.
  Eclipse is window-global → this row is **global** (does not re-scope on focus).

## 6 · The Eclipse Lens (the reconfigured console) — per surface

Engaged when `mode ∈ {ambient, (re-entered)}` and `tier==='total'`. Each surface reads
`useEclipseMode()` for the **eclipse-set** (dominant `topic_id` + its universe neighbors)
and the **shadow-set** (`selected[]` `topic_id`s), plus share.

### 6.1 Narrative threads — shadow-first reframe
- Ordering hook (`NarrativeThreads.tsx:336-344`, the relational sort + `freezeThreadOrder`):
  in eclipse mode, **eclipse thread pinned on top**; **shadow threads foregrounded** next;
  the rest dimmed. Compose with the existing dim/relate block (`:443-449`).
- Attach eclipse fields in `normalizeThread` (`:129-174`): match thread → eclipse/shadow
  by `thread_id`/`anchor_topics` ↔ eclipse `topic_id`s; attach `share_vs_dominant` from
  `EclipseItem.attention_share`.
- Render (`:509-533` count block): show the shadow story's tiny share **next to** the
  eclipse's — the relation made physical (e.g. a 0.4%-vs-100% bar). Section labels:
  "◤ The eclipse" / "◢ In its shadow".

### 6.2 Universe — recolor by membership
- Build the **eclipse-set** with the existing edge-walk (`UniverseView.tsx:189-198`
  `neighborIds`), seeded by the dominant `topic_id` instead of `hoveredId`.
- Override fill at `UniverseView.tsx:653` (`fill = eclipseSet.has(n.id) ? RED : CYAN`;
  `n.id` **is** the topic_id). Keep opacity/visibility so the shadow **stays visible**
  (don't use the 0.08 ghost path). Edges echo membership at `:580`.

### 6.3 Map — recolor eclipse vs shadow
- A single 0..1 `heat` scalar can't carry two hues → add a `lens: 'eclipse'|'shadow'`
  discriminator to each country's state in `heatStates` (`App.tsx:1177` /
  `lib/countryHeatStates.ts:78-92`), derived from a `Set<countryCode>` built by mapping
  the eclipse topic-set → each node's `countries[]` (universe payload,
  `universe.py:353`; now also on the eclipse `dominant.countries`/`selected[].countries`).
- Render branch at `EqualEarthMap.tsx:591` (`heatEls` fill) + `:604` (border): if `lens`
  present, use red/cyan; keep `heat`/`intensity` for **opacity** so both stay visible.
  This is a sibling of the existing `entityFocus` re-scope (`App.tsx:1185`).

### 6.4 Signal stream — Eclipse / Shadow / All tabs
- Tabs (`SignalStream.tsx:436-459`): in eclipse mode, collapse the category tabs to
  **Eclipse / Shadow / All** (default **Shadow**); filter branch at `:388-411`; per-row
  styling at `:486`.
- **GOTCHA (build-order consequence):** `/api/v2/signals` carries **no topic_id** — a
  signal can't be cleanly classed eclipse/shadow client-side. This tab needs a **small
  backend addition** (a `topic=`/`eclipse` filter on `/api/v2/signals`, or a dedicated
  eclipse-signals endpoint returning the shadow topics' member signals). → **Stage 4**,
  after the cleaner surfaces.

### 6.5 Bottom dock (markets / sources / anomaly)
- v1: leave as-is (aside from the AnomalyPanel partial row §5.5). Optional subtle
  desaturation only. Explicit non-goal for the first pass.

## 7 · State machine (reference)

```
☀ normal ──[poll: tier=total, episode unseen]──▶ 🌑 takeover (once/episode)
🌑 takeover ──[Enter / shadow action]──▶ 🌘 ambient (Eclipse Lens, desaturated + ribbon + sigil)
🌘 ambient ──[✕ exit]──▶ ◑ muted (normal chrome + map sigil)   ◑ muted ──[click sigil]──▶ 🌘 ambient
🌘 ambient / ◑ muted ──[poll: tier≠total]──▶ ☀ normal   (auto-exit; re-arms next episode)
```
Takeover dedup key = `dominant.identity_key` + episode id (localStorage). Partial tier
never enters this machine — it only lights the AnomalyPanel row.

## 8 · Accessibility, performance, honesty
- **`prefers-reduced-motion`:** no veil sweep / corona / pulse; static dark end-state +
  instant transitions.
- **Never traps:** takeover is dismissible (Enter / shadow / Esc); ambient has ✕; muted
  has a re-enter sigil; everything auto-clears when the data says the eclipse passed.
- **Honesty preserved:** the takeover + ribbon carry the coverage-volume-proxy caveat
  ("proxy for attention, not audience eyeballs; ranked, not certified"), consistent with
  the endpoint's `method.certifies_individual_story: false`.
- **Perf:** watch the `filter: grayscale` × `backdrop-filter` interaction (§5.3); the
  takeover is a single portal; the lens recolors reuse existing memoized layers.
- **Mobile:** Brief = symbol only; L2 lens is **desktop-first** — mobile L2 gets ambient
  + threads reframe + shadow list; heavy universe/map recolor degrades gracefully.

## 9 · Boundary with the coverage-gaps spec
- The dock tab rename `'eclipse' → 'radar'` and `UnderRadarLens` are **owned by the
  coverage-gaps spec** — this spec does **not** touch them.
- The eclipse `selected[]` "shadow" list is a **different concept** from coverage-gaps
  (categories with 0 gate-kept). No overlap; both may cite "under the radar" language but
  mean different things.
- Both specs edit `BriefNewspaper.tsx` and the `App.tsx` dock region — **coordinate
  merges**; scopes are distinct (coverage-gaps = dock tab content; eclipse = global
  chrome + takeover + lens surfaces + a Brief masthead symbol). `EclipseStrip` and
  `attentionEclipse.ts` stay; `EclipseLens.tsx` is repurposed here as the shadow list.

## 10 · Components & boundaries

| Unit | Purpose | Depends on |
|---|---|---|
| `services/attention_eclipse.py` (extend) | pure tier/guards/composite from axes | axes inputs |
| `routers/attention_eclipse.py` (extend) | SQL: identity_key, country footprint, country-dominance, entropy baseline; `attention-eclipse-v1` | db |
| `contexts/EclipseModeContext.tsx` (new) | poll + tier + mode state machine + episode dedup | `lib/attentionEclipse.ts` |
| `components/EclipseTakeover.tsx` (new, portal) | Phase A cinematic | `useEclipseMode` |
| eclipse ambient CSS + ribbon + map sigil | Phase C chrome | `.eclipsed` class |
| `AnomalyPanel.tsx` (edit) | partial/total eclipse row | `useEclipseMode` |
| `NarrativeThreads.tsx` (edit) | shadow-first reframe | eclipse/shadow sets + share |
| `UniverseView.tsx` (edit) | recolor by eclipse-set | edge-walk set |
| `App.tsx` + `countryHeatStates.ts` + `EqualEarthMap.tsx` (edit) | map recolor via `lens` | country sets |
| `SignalStream.tsx` (edit) + `/api/v2/signals` filter (new) | Eclipse/Shadow tabs | topic filter |
| `BriefNewspaper.tsx` + `App.tsx` entry (edit) | Brief symbol + `entry=eclipse` takeover | `useEclipseMode` |
| `EclipseLens.tsx` (repurpose) | "stories in its shadow" list | `selected[]` |

## 11 · Build order (one feature, staged)

1. **Measurement v2 (backend)** — §4. Tier + guards + country-dominance + entropy-collapse
   + identity_key + country footprints; `attention-eclipse-v1`; tests. *Ships nothing
   visible yet; everything downstream keys off `tier`.*
2. **The moment core (frontend)** — §5. `EclipseModeContext` + takeover + ambient/muted +
   auto-exit + Brief symbol + `entry=eclipse` + episode dedup; **partial → AnomalyPanel
   row**. *This alone delivers "replace crisis mode": the world goes dark on a real total
   eclipse.*
3. **The Eclipse Lens surfaces** — §6.1→6.3, incremental: threads reframe → universe
   recolor → map recolor. *The "lo grande" reframe, shadow-first.*
4. **Signal-stream Eclipse/Shadow** — §6.4, gated on the `/api/v2/signals` topic filter.

## 12 · Open decisions / risks
- **Threshold calibration** (`DOM_TAU`, `COLL_TAU`, guards): measure-first on history
  before shipping the takeover; start conservative. The 07-19 black-hole + thin-ETL days
  are the calibration targets.
- **Entropy baseline storage:** on-the-fly vs a tiny daily-`H` table. Start on-the-fly
  (7-day hot reach); promote to a table if the query is heavy.
- **`filter: grayscale` × `backdrop-filter`** interaction — verify in-browser; fallback
  = desaturate `.app` not `body`.
- **Signal topic-filter contract** (`/api/v2/signals?topic=`) — small but real backend
  work; deferred to Stage 4 so it doesn't block the drama.
