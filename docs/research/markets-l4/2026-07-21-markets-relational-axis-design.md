# Atlas Markets — the bidirectional co-movement axis (master design route, 2026-07-21)

**Status: design / brainstorm only — NOT a build.** Descriptive presentation is
design-ready (#151 product-overlay territory). **No relation is claimed to exist:**
every causal / lead-lag claim is GATED on the #226 event-study re-run at ~150 trading
days (~Oct 2026), which found **0 exploitable leads at n≈44** (an underpowered null,
not a disproof). What could ship now is the surface, the measurement machine, and the
two accumulating panels that make the re-run physically possible — nothing on it reads
as a forecast, a direction, or a trade signal.

**Supersedes** the sink framing of
`docs/research/markets-l4/2026-07-21-markets-as-chain-endpoint-design.md` (a market as a
one-way chain terminus with a hand-mapped relation). Synthesized from two multi-agent
explorations: the relational core (§1–4, §6, §8–9) and the surface placement (§7, still
in flight at write time — deepened on completion).

**References:** #226 (M0 event study, gate = STOP — `markets/m0_event_study.py`,
`docs/research/markets-l4/2026-07-06-m0-event-study.md`); L4 plan
(`docs/research/2026-06-12-atlas-markets-layer-l4.md`); #151 (product market overlay);
#219 (Kalman movement feed); #234 (`useFocusRelation`); the walked-constellation
flywheel (`docs/state/2026-07-21-analyst-journey-map.md`); edge model
(`backend/app/routers/dossier.py`), universe (`backend/app/routers/universe.py`). Wedge
= narrative analyst; math-first; evidence-gated; **no employer IP; not investment
advice.**

---

## 1. The reframe — market is not a sink, it is a relational axis

The first draft made a market series a **sink**: a news chain walked hermano/primo hops
and *terminated* at a price via a hand-authored `INSTRUMENT_MAP`. One-way, and the
relation was *assumed* by the map. Pedro's correction (2026-07-21):

1. **A different TYPE of information** — numbers, movement of numbers, historical trends
   — that **clashes** with narrative (headline/thread/coverage) data. It needs its own
   container and its own grooming on every surface (§7).
2. **Bidirectional and DISCOVERED, not mapped.** The object is not "a thread ends at
   oil." It is *how* market and news **connect** — "whether the variance / the change of
   an index can be related to the change in some news, and **whether those relations
   exist at all**." From an index MOVE you must be able to ask "which narratives could
   relate?" (market → news), so the market is an **entry** and a first-class relatable
   node, a new **axis over all of Atlas** (like country / entity / time). This keeps the
   analyst wedge central: value = honest situational awareness — *"this narrative and
   this instrument's volatility co-moved, n=4, unproven"* — never advice.

Pedro's 2026-06-12 thesis names the object: *"muchas cosas afectan muchas cosas, y esas
cosas se mueven en relación entre sí"* — relational co-movement of narratives, countries
and instruments **as a system**.

---

## 2. The scientific object: do these relations exist?

Answered by a **measured co-movement / lead-lag STRUCTURE over time**, in both
directions, **with its null as a first-class result** — never by a map. Substrate exists
in `markets/m0_event_study.py`: a daily category-day intensity series (from
`archive_story_units`, argmax anchor-cosine assignment) vs Yahoo daily `|log-return|`.

The news-side variance term must be a **durable, differenceable daily series**. The
correct vocabulary is the Kalman feed (`topic_movement`: velocity / **surprise** =
variance-normalized innovation) — but the correct **substrate is NOT** the stored
latest-row `topic_movement` (a single window_end snapshot, a MAX over 7d); it is a daily
intensity series with its change term derived stepwise (intensity log-return, or surprise
recomputed over the daily series). A prior negative result disciplines this: **Kalman
velocity mean-reverts and does not lead volume within news** (h1 ≈ −0.477), so prefer
intensity log-returns, and treat any market lead-lag as *discovery to be measured, not
assumed*.

**Power is the honest ceiling.** #226 = 0 leads at n≈44 (single May–Jul 2026 regime) =
underpowered null. A non-fragile permutation p needs ~15 independent events; a claim
~25–30 (~1.5–3 yr/instrument). The ~Oct re-run reaches only ~8–10 events/pair — enough
to firm a fragile read, never to settle one. **Most cells will honestly stay "unproven"
— that is a correct answer to "do these relations exist," not a failure of the surface.**

---

## 3. Bidirectional model

Two symmetric permutation event-studies over the **same magnitude-only** co-variance
object (`|log-return| ↔ |intensity|` — Atlas has no stance model, `m0:188-190`; **never**
backfill signed direction from LLM sentiment).

- **News → market (forward, = m0 unchanged).** Event = a topic/category-day whose
  intensity z-score ≥ 2 vs a strictly backward-looking trailing 21-**calendar**-day window
  (≥10 days history). Statistic = mean instrument `|log-return|` at trading-day lag {0,1,2}
  from `next_trading(D)`. Inference = 10k without-replacement permutation. **Leakage rule:**
  the Atlas day is the UTC *news* day → same-day close already contains the reaction →
  **t0 = REACTION; a LEAD rests only on t+1/t+2.**
- **Market → news (reverse, the new half Pedro named).** Event = an instrument-day whose
  `|log-return|` z-score ≥ Z_m vs its trailing 21-**trading**-day window. Response =
  standardized strictly-trailing daily intensity of the instrument's pre-registered
  categories at **calendar** offset δ ∈ {−2,−1,0,+1,+2}. **Sharper leakage rule:** a price
  move is public and near-instant, so intensity at δ ≥ 0 is trivially reactive/amplifying
  — **never a lead**; a "news led this move" claim requires elevated intensity at **δ =
  −1/−2** (news while price was still flat). The lead window is **calendar days, not
  `shift_trading`** — a Monday gap can be led by weekend news; trading-day shift silently
  drops exactly the weekend news that most plausibly leads it. **Shared-shock** pairs (a
  war spiking oil AND armed-conflict at once) are auto-flagged "precedence unresolvable at
  UTC-day granularity" and can **never** receive a lead annotation.

The honest verb everywhere is **"relates to / moves with / leads-lags,"** never "causes,"
never signed "up/down."

---

## 4. Market as an axis over all of Atlas

A market instrument becomes node `market-<SYMBOL>` (e.g. `market-CL=F`). It has **no e5
centroid**, so it relates through exactly three rails, none geometric — **shared_country**,
**text_mention** (ticker/name in a headline), and the new **co_movement** basis (the
measured lead-lag). Structural honesty: *the market axis cannot be added without doing the
measurement — the hand map can never draw the co_movement edge.*

- **Movement feed (load-bearing):** write a thin `engine_version='market-v1'` row into
  `topic_movement` and relax the hard-coded `dynamic-topic-%` filters
  (`universe.py:203/231/299/307`) to admit `market-%`. Price return-variance is the one
  substrate where a market series and a narrative series are the same shape. **But** render
  market velocity in a *visually distinct* affordance — a DB tag is not separation; price
  volatility must never read as attention "surging."
- **Dossier graph:** the 3-basis builder already tolerates a centroid-less node (skips
  `semantic`; `shared_country` + `text_mention` still fire, survival gate `dossier.py:484`).
  The walked chain reaches it via an **additive co_movement neighbor lane** copied from the
  F3b body-lane pattern (`dossier.py:776-814`) — lane failure never costs centroid neighbors.
- **Focus #234 (market-move → related narratives):** a market focus can't be a `signals_v2`
  WHERE-clause (`workspace.py:185-210`); its relation set comes from the discovered
  co-movement endpoint. This needs a **compound focus** (instrument AND narrative) —
  journey-map open Q1 — or the mutually-exclusive setters null everything and re-trigger the
  frame-clear fracture. **Compound focus is a prerequisite, not a freebie.**
- **Universe PCA cloud — the honest boundary:** a price series is **inadmissible**
  (`universe.py:172` hard-filters `centroid_vec IS NOT NULL`). So "axis over ALL of Atlas"
  is precisely **an axis over the dossier / movement / focus rails, NOT the PCA field** —
  state this on the surface. Optional: an off-cloud "instrument satellite" positioned *from
  its co-movement neighbors*, explicitly labeled "position from co-movement, not meaning."

**`INSTRUMENT_MAP` is demoted to a PRIOR, never the relation.** It (a) bounds multiple
comparisons as the pre-registered *confirmatory* set, and (b) is itself falsifiable — a
mapped pair with no measured co-movement is a *wrong prior*, reported as such.

---

## 5. The per-country instrument universe (the descriptive backbone)

Every country carries a small set of **descriptive-by-definition** instruments — true by
identity, needing **no discovery and no gate** (COP *is* Colombia's currency). This is the
backbone that feeds the Brief country card (§7) and the dock re-scope; it is the concrete
content of the `shared_country` rail (§4) and is strictly separate from the discovered
co_movement rail.

Four per-country slots:

| slot | what | examples | Yahoo |
|---|---|---|---|
| **Currency (FX)** | the country's own currency pair | `COP=X`, `MXN=X`, `BRL=X` | yes |
| **Benchmark index / country ETF** | its bourse benchmark (ETF when the raw index isn't on the free feed) | US `^GSPC`/`^DJI`, Brazil `EWZ`, Mexico `EWW`, Colombia `GXG` / COLCAP | yes |
| **National champion(s)** | 1–2 dominant listed firms of its bolsa (esp. the state energy/commodity champion) | Colombia → Ecopetrol `EC`, Bancolombia `CIB`; Saudi → Aramco | ADRs yes |
| **Top export commodity** | its key raw material (a global commodity, *tagged* as this country's export — a customs fact) | Colombia → oil + coffee (`CL=F`,`KC=F`); Chile → copper (`HG=F`); Saudi → oil | yes |

**Global set (world edition, not per-country):** oil `CL=F`, gold `GC=F`, copper `HG=F`,
a broad equity gauge (`^GSPC`), the dollar index (`DXY`), a risk gauge (`^VIX`).

**Placement nuance (from §7):** the export-commodity slot stays in this descriptive DATA
(a customs fact) but is **NOT rendered as a tile on the Brief country card** — a
globally-moving commodity price beside country news is the strongest post-hoc causal trap.
The clean country-card core is currency + own index; the export commodity surfaces only in
the world strip / dock, where it reads as a global instrument, not a country claim.

**The honesty knife in Pedro's own words.** He said commodities *"afectan a todos los
países."* "Affects" is the DISCOVERED/causal claim — **gated**. Descriptive:
- Definitional fact: "oil is Colombia's top export commodity" (customs data) → showable now.
- Gated: "Colombian news variance moves with oil" → only after the #226 re-run.

**Ecopetrol is the instructive node** — it *bridges* country (Colombia's largest listed
firm) and commodity (an oil producer). Descriptive = "Ecopetrol, Colombia's state oil
champion"; gated = "Colombian oil news moves Ecopetrol." The UI shows the first, never the
second, until measured.

**Honest gaps (shown, not hidden):** the Eurozone shares `EUR` (no own FX); dollarized
economies (Ecuador, Panama, El Salvador) have no own currency; small bourses aren't on
Yahoo — those countries show only FX + an export proxy and say so.

A config table (§6), authored once, inspectable, `basis='descriptive'` on every row.

---

## 6. Data & schema

`markets/` stays a **separate consumer** (own credentials, consumes Atlas over its PUBLIC
API). Only THIN, DESCRIPTIVE tables land in Atlas's DB (#151-legitimate); no trading
signal ever does. Source = the existing Yahoo daily-close puller (`yahoo_daily()`), run as
a **nightly off-peak cron** (17:30+); daily grain (intraday invites the leakage/backtest-
theater failure the L4 doc warns of).

**Markets side — the power-accumulation + result home (the PRIMARY ship-now work):**
```
market_price_daily(symbol, date, close, log_return, source, fetched_at, PK(symbol,date))
  -- persisted, append-only, GROWING. m0 today re-fetches a rolling range=4mo and lets
  -- history age out; without this the re-run is PHYSICALLY IMPOSSIBLE. Start the cron NOW.

news_daily_intensity(day, axis_kind∈{category,topic,country}, axis_id, intensity,
                     z_trailing21, computed_pit BOOL, PK(day,axis_kind,axis_id))
  -- one LIVE, point-in-time daily panel unifying archive_story_units + the hot corpus.
  -- computed_pit asserts day-D uses only <= D data. THIS IS THE CRUX AND DOES NOT EXIST:
  -- Atlas clustering is retrospective, so a naive t-1 value LEAKS future structure. Must
  -- be an append-only EOD log; the reverse study emits NO lead row until verified leak-free.

comovement_result(axis_id, symbol, study_direction, lag, stat, n_events, n_effective,
                  perm_p, fdr_q, hypothesis_lane∈{confirmatory,exploratory}, regime_span,
                  tier, method_version, PK(...))
  -- ledger of positives AND nulls. n_effective is block/cluster-adjusted (correlated
  -- instruments co-spike; raw n is never used).
```

**Descriptive / product side (thin, lands in Atlas DB; ships for #151 + the Brief §7):**
```
market_series(symbol PK, label, asset_class, last_close, last_close_at, spark_30d[], updated_at)
  -- the descriptive price node for the Brief strip / dock tab. No forward value, no signal.

country_instrument_universe(country_code, symbol, role∈{currency,index,champion,
                            export-commodity}, basis='descriptive', note)   -- §5 backbone

category_instrument_map(category_slug, symbol, basis='domain-prior', note)  -- the PRIOR (§4)

market_relation_public(atlas_axis_id, symbol, tier, label_text, measured_window, perm_p,
                       n_events, is_directional DEFAULT false,
                       disclaimer DEFAULT 'descriptive co-variance, not investment advice')
  -- EMPTY until a relation reaches product. No price, no forward value, no signed field.
```
`market-<SYMBOL>` ids thread through `dossier.py:86`, `focus_filters.py`, and a
`?instrument=` deep-link.

---

## 7. Surfaces & placement — markets is a different data TYPE

Everything else in Atlas is *narrative*: headlines, threads, coverage, who-says-what,
sentiment. Market data is a **different type** — levels, movement of numbers, delayed/EOD
series — and it clashes with that vocabulary. Every existing number in the Brief already
carries a lineage tooltip (`BriefNewspaper.tsx:1190` vitals, `:233` trend lineage, `:213`
sentiment badges); a price dropped into that grammar would inherit an authority it hasn't
earned and read as *news-moved* the moment it sits beside a headline. So markets gets **its
own container + own grooming** on every surface. The load-bearing invariant is
**structural, not editorial:** *a market number always appears with its instrument
identity + an as-of stamp inside its own box, and never fuses into or sits adjacent to a
narrative claim, arrow, or headline.* That rule is what makes the descriptive-vs-#226 split
unbreakable instead of a caption someone forgets.

### L1 Brief — accompanying the daily edition (world + country)
- **World.** A `<section className="brief-markets-strip">` sibling of the "Heating Up"
  `brief-heat-strip`, INSIDE PANEL 1 · THE WORLD before the section close
  (`BriefNewspaper.tsx:1559`), reusing the small-tile layout (`:1533-1558`): four tiles for
  a fixed world basket (broad equity / dollar index / Brent / gold, optional vol gauge) —
  last-close + net-change glyph + spark. Keep it in the World panel, NOT `brief-bottom-row`
  (`:1824`, back-matter that renders under country editions and would fight the country
  card).
- **Country.** A compact `brief-markets-country` card after the country instrument block
  (`:1677-1693`), grooming copied from the Voice Mix card (`CountryBrief.tsx:804-833`):
  figure + thin spark + one honest caption + `?` tooltip. Shows the country's **own
  instruments by definition** — currency (COP) + main index/ETF (COLCAP/GXG) as level +
  trend.
- **Critique fix — drop the export-commodity TILE from the country card.** Its price moves
  globally, so juxtaposing it beside country news is the strongest post-hoc causal trap of
  the three. It stays in the descriptive `country_instrument_universe` DATA (§5, a customs
  fact) but is NOT rendered as a country-card tile. Clean core = currency + own index.
- **The honesty split (structural):** currency + own-index are descriptive-by-definition
  (n=0, #151-allowed) — the country's measurable pulse, NOT a claim news moved them. The
  country-news→price RELATION appears **nowhere** in the UI (no correlation, no lead-lag,
  no story→tick arrow) until #226; the no-causal-claim statement is a persistent chip +
  always-visible footer, never hover-only.
- **Sealed-edition vs live-number — resolved:** the edition is frozen 02:30 Bogotá
  (`seal_schedule.py`; served point-in-time `investigation.py:238`) and the sealed
  `PublicationPackage` (`investigation_graph.py:108`) has **no markets field, by design.**
  Markets ride the LIVE path only — a best-effort `/api/v2/markets` fetch copying the
  eclipse idiom (`BriefNewspaper.tsx:454-463`: AbortController + 12s + silent-degrade),
  with their OWN as-of stamp, a "LIVE OVERLAY — not part of the sealed edition" divider,
  and footer *"Markets update live; today's stories are sealed as of 02:30."* Edge rules: a
  reopened PAST edition pins markets to the edition-date last-close or suppresses the strip
  (the citable record never mutates); weekend/after-hours shows "Last close · Fri" (EOD
  tier); a feed outage renders "Markets unavailable — retrying" (error-state ≠ empty-state),
  never a flat line or 0.00 — verified under PWA offline cache.

### L2 Console — a Markets dock tab
- The bottom dock is already a numbers-and-lens quarantine (Anomaly / Source Integrity /
  Under the Radar) that never contaminates the threads spine — the ideal home. A 4th
  **MARKETS** tab follows the eclipse-tab recipe (commit `86af9027`): three edits in
  `App.tsx` — the `dockTab` union (`:331`), a `.dock-tab` button (`:2101-2123`, fires
  `track('dock_tab',{tab:'markets'})`), a render branch (`:2130-2166`) wrapping
  `<MarketsPanel/>` in `PanelErrorBoundary`. Authored once in `dockPanel` (`:2098`) → shows
  on desktop grid (`:2198`) + mobile Pulse (`:2179`) with no extra wiring.
- **Re-scoping:** `MarketsPanel` self-subscribes to `useFocus()` + `useFocusRelation()`,
  copying the AnomalyPanel idiom (`AnomalyPanel.tsx:35-44`): direct country focus → that
  country's own instruments; no focus → neutral world board (never blank); person/thread
  focus → a *discovered* dominant country's instruments only under a re-scope chip reworded
  "this country's own instruments — not linked to why it surfaced," gated hard on
  `relationActive` + a confidence floor. **Critique fix — the category→bellwether row is
  dropped entirely** (conflict-category → Brent juxtaposes a moving price with a thread =
  the causal read #226 forbids; a label doesn't neutralize the juxtaposition). L2 is
  always-live → no seal conflict here.
- **Interaction:** hover expands the spark to 30d + as-of + "shape only — compare by the
  printed last-close, not amplitude"; click drills IN-CONTAINER to a fuller chart with a
  basis-labeled scrubber (reusing the globe scrubber thumb `App.tsx:1728-1738`; prints basis
  `close` + tier live/EOD/archive). Click **never** jumps to a narrative panel — that
  crossing is exactly what the container prevents. Only outbound affordance = an explicit
  "focus this country →" `setCountry()` link; the price itself stays inert.

### The grooming — one Markets presentation system (the "Instrument Skin")
One namespaced component family `.atlas-instrument`: boxed container, **mono tabular
numerals**, a market-specific diverging up/down ramp, a two-state honesty chip, and a shared
`<InstrumentSpark>`. There is **no shared `<Sparkline>` today** (duplicated
`NarrativeThreads.tsx:78` + `BriefNewspaper.tsx:268`) → **extract one shared component**
(markets mode: self-normalize to price range, non-zero baseline) rather than a third copy.
The same skin renders the Brief world strip, country card, dock tab, **and the companion-doc
relational chain node** — so a market node in the graph is visibly an instrument, not a
narrative node. **Enforce the quarantine by TYPE, not discipline:** ship the shared
primitive (ideally a lint rule) so a market number *refuses to render outside
`.atlas-instrument`* — else a future dev drops a market delta into a thread row and the
invariant erodes silently. Reuse verbatim: the honesty-chip pill (`App.css:143-165`), the
UniverseView one-line split footer (`UniverseView.tsx:848`), the DayEvidence live/archive +
error≠empty labels (`DayEvidencePanel.tsx:62-96`), and the map/replay contract shape
(`geo.py:1097` — basis field + contract version + degraded flag + honesty note) as the
template for the thin `/api/v2/markets` series over the #151 descriptive price table.

### Surface honesty rules (UI — complements the §8 measurement tiers)
- **Descriptive shows now:** own currency/index + world basket, level + trend only, chip
  `DESCRIPTIVE · LAST CLOSE` (#151).
- **The relation stays gated:** no correlation, no lead-lag, no "news moved this," no
  story→price path. The absence is made honest — a greyed "relation analysis — pending
  validation (#226, re-run ~Oct 2026)"; the chip's RELATION state is a **reserved-but-dark
  slot**, lit only as a *separately labeled* element if #226 proves a lead/lag, never
  retrofitted onto a price.
- **Never a trade signal:** "descriptive context — not investment advice" microcopy on the
  country card + dock tab.
- **Color discipline:** a market diverging ramp provably distinct from sentiment green/red
  (`BriefNewspaper.tsx:609`) and the crisis-red heat ramp (`countryHeatStates.ts`), CVD-safe
  in **both** reader themes (`data-rtheme`), so a falling price never reads as an alarm nor
  an up-tick as positive sentiment.
- **Unit + clamp + secondary weight:** every number states its unit inline (currency/%/
  index pts) + as-of, clamped to its axis; the L1 strip stays clearly below the lead story
  (collapsed disclosure on mobile) — protecting the wedge, honoring L1=the-day /
  L2=time-as-dimension (Brief is 24h-pinned).

---

## 8. Honesty tiers & the #226 gate

- **Tier 0 (structural, ships):** the node relates via `shared_country` + `text_mention`
  only; co_movement renders "no measured relation / underpowered."
- **Tier 1 (candidate):** `perm_p < 0.10` in its lane, excludes the reactive offset,
  `n_effective ≥ 3`, **and passes multiple-testing correction across the FULL confirmatory
  family** (the ~54 mapped tests + CL=F/GC=F cross-pair dependence — correcting only the
  exploratory lane manufactures noise). Band-labeled "CANDIDATE — underpowered, single
  regime, unproven."
- **Tier 2 (established):** `n_effective ≥ 15`, FDR-q < 0.05, replicated in **both**
  studies **and** across ≥ 2 regimes. **Structurally unreachable today** → the product
  table's max tier is 0; **tier-1 candidates live in the internal ledger only**, never
  drawn as edges in the primary dossier/universe surfaces (a drawn line is a visual claim
  the "unproven" chip cannot retract).

**Invariants:** magnitude-only (no up/down, no target — unrepresentable by construction);
permutation not asymptotic; nulls rendered equal to positives; every relation past-tense
with its window visible; a Sharpe/ratio > ~2 is a **leakage alarm**, not a target; **not
investment advice; no employer IP.** Even a green re-run yields "collect more / consider,"
never "trade."

---

## 9. Chain integration — bidirectional, not a sink

The walked constellation (hermano = direct edge, primo = indirect walk, weight-product
decay) now passes **through** a market node in both directions instead of terminating at
it. **Inbound** (narrative → instrument): a chain reaches `market-CL=F` via the additive
co_movement neighbor lane; edge weight = the *measured* co-movement statistic × existing
decay, drawn dotted/candidate, never solid until tier 2. **Outbound** (instrument →
narrative): the market node is a walk *origin* — from an index move the chain expands to
co-moving thread-families, each carrying `direction ∈ {news-earlier, price-earlier,
same-day}` (renamed from "news_leads" to kill the causal read), `lag`, `perm_p`,
`n_events`. Below tier 1 the instrument still participates via `shared_country` +
`text_mention`, kept **visually separate** from the empty co_movement rail so a curated
geographic proxy is never mistaken for a measured relation — so the chain is traversable
now while co_movement honestly reads "unproven." The one honest onward turn from a market
node is **reverse co-mapping** ("which other domains carry this instrument"), handing the
analyst back into the news graph — a real flywheel turn.

---

## 10. Open questions for the creative session

1. **Empty vs. anchoring:** does the product surface show *nothing* below tier 2 (safe but
   empty for a year+, un-dogfoodable), or expose tier-1 candidates in an explicit internal
   "measurement-in-progress" view? Salience beats disclaimers.
2. **Point-in-time reconstruction:** can we actually compute day-D intensity from ≤ D data
   given retrospective clustering — and how do we *prove* the reverse δ=−1/−2 window is
   leak-free before trusting a single lead row?
3. **Compound focus (journey Q1):** the primitive for "focused on instrument AND narrative"
   that doesn't null the other focus dims.
4. **Discovery breadth vs. forking paths:** do we ever promote the corrected/labeled
   *exploratory* scan to a first-class discovery output (the real "discovered-not-mapped"
   promise), or does only the confirmatory lane surface — which is the sink in a new costume?
5. **Instrument→country exposure:** derive from measured country-tagged co-occurrence, or
   hand-author (re-importing a curated map, just geographic)?
6. **Seal/freshness & off-cloud placement:** is a live number beside a frozen edition OK
   with an explicit "as of," or should the Brief strip freeze at seal time? Is a co-movement
   pseudo-position worth the risk of reading as semantic meaning, or does the market node
   stay out of the universe field entirely?
7. **Champion selection & mapping curation:** 1–2 firms per country by index weight, or
   only the state commodity champion? `country_instrument_universe` is a curated, versioned
   editorial file — for illiquid/no-index economies, degrade to currency-only or show a "no
   liquid instrument" empty card (never fabricate, never blank)? Who audits it, how often?
8. **World strip under a country edition:** suppress the global basket entirely (country
   card only, current route), or keep a slim global-context row?
9. **Past-edition markets:** pin-to-edition-date last-close vs. full suppression on a
   reopened sealed edition — which better preserves the citable record without looking
   broken?
10. **Dock tab-bar crowding:** four all-caps labels (ANOMALY / SOURCE INTEGRITY / UNDER THE
    RADAR / MARKETS) won't fit the 16:9 dock slot or 375px Pulse tab — icon-only or
    abbreviated at small widths?
11. **Backend freshness ownership:** the `markets/` folder is a separate consumer (own
    creds); only the thin descriptive table lands in Atlas DB (#151). Where does vendor-
    latency / EOD-vs-delayed freshness get owned so the honesty labels stay true?

---

## Return summary

Route replaces the sink with a **bidirectional, discovered, unproven-by-default
co-movement axis.** Core: co_movement as one symmetric measured object on the movement
rail (centroid-free, both directions, magnitude-only); a tiered ledger with **nulls
first-class** and an "established" tier defined-but-empty until #226 clears;
`INSTRUMENT_MAP` demoted to a pre-registered, falsifiable prior. **Primary ship-now =
the two accumulating panels** (`market_price_daily` + point-in-time `news_daily_intensity`)
— the gate prerequisite — plus the forward+reverse event-study machine writing positives
AND nulls, and the market node as a dossier/focus/entry object. Per-country descriptive
backbone (§5): FX + index/ETF + champion + top-export commodity, `basis='descriptive'`;
global strip = oil/gold/copper/equity/dollar/risk; "affects" is gated, identity facts show
now. Surfaces (§7): Brief world strip + country card, an L2 Markets dock tab, one shared
`MEASURED MARKET DATA` grooming system. Hard fixes: correct the confirmatory lane for
multiple testing; block/cluster `n_effective`; block reverse lead rows until PIT is
verified; keep tier-1 candidates off primary surfaces; separate curated geo/mention edges
from the measured co_movement rail; solve compound focus first. **Honest boundary: this is
an axis over the dossier/movement/focus rails, NOT the universe PCA cloud.** #226 STOP
holds — the surface is design-ready; the claim that any specific relation exists stays
gated to ~Oct 2026, and even then yields "consider," never "trade." Not investment advice;
no employer IP.
