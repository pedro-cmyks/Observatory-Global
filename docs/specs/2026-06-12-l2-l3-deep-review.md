# L2/L3 Deep Review — Connection Map, Click-Path Audit, Layout

Date: 2026-06-12
Issue: #228 (follow-up to #225, which fixed L1)
Status: review judgment — recommendations, not yet implemented
Evidence: production API probes + code inspection this session; Pedro's
2026-06-12 screenshots (PE election thread, SignalDetail, person panel)

---

## Verdict in one paragraph

L2's skeleton is right — the stream-slot state machine (person → thread →
theme → country → chokepoint) is a sound working-surface design, and the
canonical paths (threads list → thread detail, country → CountryBrief) now
speak the right contracts. The rot is at the edges: **every path that exits
the Narrative-Threads spine lands on raw GDELT material presented as
product** — SignalDetail's theme chips, related-signals-by-GDELT-overlap
(with a dead click handler), persons fields full of non-persons ("el nino",
"america latin", "dar una patada"), and a top-persons list for Peru led by
David Hockney because a syndicated obituary outranks local actors. L2 is a
two-tier surface pretending to be one: a curated spine and an uncurated
fringe, with no visual marking of the boundary. L3 (Workbench) earns its
position and mostly needs #227. The layout has one structural fault: on
16:9 laptops the entire bottom row — three interactive sections — gets
~132px. The deepest data finding of this review: the quality gate kept
**0 of 43** clearly-relevant Spanish headlines on Peru's biggest story;
the below-gate fallback is doing the serving work the gate should be doing.
The fringe problem and the gate problem are the same problem at two layers:
**the product's curated layer is too thin, and the seams show.**

---

## 1. Connection map — what feeds what

### L2 App panels

| Surface | Endpoint(s) | Feeds from | Verdict |
|---|---|---|---|
| Map nodes/heat/flows | `/v2/nodes`, `/v2/flows`, `/v2/conflict-markers` (FocusDataContext) | signals_v2 aggregates | Sound; hover gap on anomaly rings (§2.6) |
| SignalStream | `/v2/signals` | signals_v2 raw + lanes | Sound after #177 lanes |
| NarrativeThreads panel | `/v2/threads` | dynamic_topics → atlas → emergent | Canonical spine ✓ |
| ThemeDetail | `/v2/theme/<id>`, `/insight`, `/trends/match`, `/wiki/match`, `/v2/threads/<id>?llm=1` | gated assignments (+below-gate fallback) | Fixed this session (`0b9ab4a`); trends/wiki joins are lexical-by-label (weak, unlabeled) |
| CountryBrief | `/v2/threads?country_code`, `/v2/nodes`, `/v2/signals`, `/api/indicators` | thread contract ✓ | Sound after #174/#207 |
| EntityPanel (person) | `/v2/focus?focus_type=person` | signals_v2 `persons[]` (GDELT NER) | **Weakest surface** — garbage-in (§2.4) |
| SignalDetailPanel | props from stream (no fetch) | GDELT themes + stream-local overlap | **Two guardrail leaks** (§2.3) |
| AnomalyPanel (bottom) | CrisisContext `/v2/anomalies`, trends/wiki attention URLs | z-score anomalies + trends_v2 | Content fine; crushed by layout (§3) |
| SourceIntegrityPanel (bottom) | `/v2/briefing` (reuses) | top_sources | Fine; crushed by layout (§3) |
| CorrelationMatrix | `/v2/correlation` | theme co-occurrence | Fine |
| SearchBar | `/v2/search/unified`, `/v2/search/thread` | taxonomy+concepts+DB, query-thread builder | Sound after #175 |
| Vessels/Aircraft | `/v2/vessels`, `/v2/aircraft` | AISStream / ADS-B | PLANE dead (known), SHIPS by-design sparse (§2.7) |

**Dead components:** `DiscoveryPanel` (former default stream slot) and
`AtlasHeatList` (a heat-countries panel — i.e., **half of #183 already
exists, unmounted**). Delete or mount; dead code in a 36-component tree is
map-noise for every future session.

### L3 Workbench

| Surface | Endpoint(s) | Verdict |
|---|---|---|
| WorkbenchPanel (investigations, pins, trail) | localStorage (`lib/workbench.ts`) + JSON export | Earns position; needs #227 (pin snapshot + note) before Phase 3 |
| ResearchPlanPanel | `POST /v2/research/plan`, `POST /v2/research/events` | Sound; ledger/tray/semantic-evidence all render |
| Pin open paths | thread → theme-detail contract; country → CountryBrief | Sound (and now suffix-proof after `0b9ab4a`) |

L3 has no fringe problem: everything it shows carries its label
(direct_evidence/context/weak_support/gap, UNVERIFIED/ASSIGNED). **L3 is
the honesty model L2's fringe should copy.**

---

## 2. Click-path audit

### 2.1 Thread list → thread detail — FIXED, remainder #214
`slug--cc` ids never parsed in theme detail → atlas lookup missed → GDELT
path → "0 signals" gate message on Peru's live vote-count dispute while
the list said 48. Fixed (`0b9ab4a`): parse suffix, single-country scopes,
multi-country stays global. Remaining under #214: list 48 vs rawTotal 43
(list counts `assigned_at` window, detail joins `s.timestamp` window —
pick one anchor and use it in both); and §4's gate-recall finding.

### 2.2 Gate recall on non-English — the data finding
Gate kept **0/43** Spanish election headlines (recuento, ONPE, JEE,
Fujimori) — every one obviously on-topic. The biggest live story in the
country was 100% below-gate; users only see it because the #214 fallback
ships raw material with an UNVERIFIED banner. The gate is currently a
**language gate wearing a quality-gate costume**. Action: measure gate
keep-rate by language across topics (one SQL pass); if confirmed, this
re-prioritizes #162 (multilingual models) from tier-B to the top of the
data queue. The fallback bought time; it is not the fix.

### 2.3 Signal → SignalDetail — two guardrail leaks, one dead control
- **Theme chips are GDELT** (Kill, Public Sector, Child…), clicking one
  opens the GDELT theme view — at L2 the taxonomy is acting as the story
  model, violating the Narrative-Threads guardrail in the product's most
  granular surface. Fix: show the thread(s) this signal belongs to
  (assignments exist) as primary chips; demote GDELT chips to a "taxonomy"
  row visually distinct (same demotion L1 got).
- **RELATED SIGNALS = any-GDELT-theme overlap within current stream items**
  (`s.themes.some(t => selected.themes.includes(t))`) — Pakistan mosque
  blast relates to an Illinois tornado via "Disaster Fire". Counterfeit
  relatedness. Fix: same-thread signals first; semantic neighbors
  (signal_embeddings exist since #223!) second, labeled; drop the
  theme-overlap heuristic.
- **Related rows have a dead onClick** (`/* do nothing, just style */`) —
  a control that looks interactive and isn't. Wire to SignalDetail swap or
  remove affordance.

### 2.4 Person/entity → EntityPanel — weakest surface, garbage-in
`persons[]` is raw GDELT NER: "el nino", "america latin", "jesus marie",
"dar una patada", "bafana bafana" surface as people; Peru's top person is
David Hockney (syndicated obituary volume beats local actors). Three
compounding faults: (a) extraction garbage — `_GEO_NAME_BLOCKLIST` exists
but is 40 hand-entries deep and can't keep up; (b) no entity typing
(person/org/team/phenomenon); (c) ranking by raw count rewards syndication.
This is **#176 verbatim** — fold it here, raise its priority. Cheap wins
first: blocklist += known offenders; syndication-dedup before counting
(`syndication_count` already computed in evidence serialization); person
chips hidden when below a confidence floor. The full fix is typed entities
(#176's scope).

### 2.5 Theme → public attention joins — weak link, unlabeled
`/trends/match` + `/wiki/match` join by theme-label words (LIKE '%word%').
Lexical, language-blind, presented without a confidence label. Honest
minimum: label the section "keyword match" until #168 (semantic links)
lands.

### 2.6 Map yellow dots — no hover
Anomaly rings (and country centroids) have no tooltip; the legend now
names them (#179) but hover-identity is the expectation on a map. Add
tooltip: country, signal count, spike ratio, "click to open country".

### 2.7 PLANE / SHIPS
PLANE: dead toggle (ADS-B feed broken) — a button that does nothing is
worse than no button; hide or badge it "feed down" (degraded-provider
pattern, same family as #196). SHIPS: sparse by design (AISStream
subscribes chokepoint boxes only) — fine, but say so in the legend
("coverage: strategic chokepoints"), don't let it read as "few ships exist".
Pedro's bigger direction — vessel behavior as narrative input (unusual
movements, chokepoint dwell anomalies feeding threads) — is real but it's
a data-layer research item (#159/#226 family, paper-adjacent), not an L2
rendering fix. Recorded, not folded.

---

## 3. Layout — the 16:9 fault

`terminal-layout` bottom row: `minmax(140px, 20%)`, and on short screens
(`max-height: 820px` — i.e., **every 16:9 laptop**) `minmax(132px, 18vh)`.
AnomalyPanel (geo alerts + public attention + conflict events — all
interactive) and SourceIntegrityPanel get ~132px of height. On Pedro's
near-square monitor the same row gets 200px+ and works. The panels aren't
wrong; the row is.

Options, in preference order:
1. **Tabbed bottom dock** — one row, tabs (ALERTS / ATTENTION / CONFLICT /
   SOURCES), each tab gets the full ~160px instead of three sections
   sharing it. Cheapest honest fix.
2. Collapsible dock with header-strip summary (alert count + top item)
   that expands over the map on demand.
3. Move public attention into the stream as a lane (it already has lane
   infrastructure) and shrink the dock's job.

Not acceptable: status quo (interactive content at 132px) or hiding the
panels entirely on short screens.

---

## 4. Graphic slots vs #225 §3

| Slot | L2 state | Gap |
|---|---|---|
| Timeline | ThemeDetail has it | Thread rows in NarrativeThreads have sparklines ✓ |
| Frame comparison | EntityPanel framing split exists; per-thread who-says-what absent | The §3 L2 centerpiece is still unbuilt — needs #217 tiers + #178; unchanged judgment |
| Heat/movement | `AtlasHeatList` BUILT but UNMOUNTED | Mount it = most of #183's panel |
| Drift/geography | Map ✓ | Drift overlay still future (needs drift detection) |

---

## 5. Issue fold

| Issue | Disposition |
|---|---|
| #176 entity hygiene | **Fold into §2.4** — it is the person-panel fix; raise priority (worst surface) |
| #178 stream item inspection | Fold into §2.3 — SignalDetail rebuild is its natural vehicle |
| #183 heat panel | §4 — mount `AtlasHeatList` in the dock/tab, add sentiment_source badge; mostly assembly |
| #214 count semantics | §2.1 remainder — one window anchor for list and detail |
| #162 multilingual NLP | **Re-prioritized by §2.2** — gate recall is the live argument |
| #173 evidence route | Unchanged; pairs with frame-comparison slot |
| #196 degraded provider | Same pattern family as PLANE handling (§2.7) |
| #168 attention↔threads semantic links | §2.5's real fix |

## 6. Execution order

1. **SignalDetail rebuild** (§2.3, folds #178): thread chips primary,
   GDELT demoted, related = same-thread + semantic neighbors, fix dead
   click. Highest leverage: it's the most-clicked leaf surface and
   currently the most dishonest.
2. **Bottom dock tabs** (§3) + mount `AtlasHeatList` (#183) in the same
   pass — one layout change, two issues.
3. **Person hygiene cheap wins** (§2.4, part of #176): blocklist,
   syndication-dedup ranking, confidence floor. Typed entities stay #176.
4. **Gate-recall measurement** (§2.2): one SQL report by language → decides
   #162's priority with data.
5. Map hover tooltips (§2.6) + PLANE degraded-state (§2.7) — small.
6. Trends/wiki "keyword match" labels (§2.5) — trivial copy change.

Items 1–3 are independent and parallelizable. L3 needs only #227 (already
queued) — no new L3 work from this review.

---

## Execution status (2026-06-26, spec-driven sync)

The "not yet implemented" header is stale. Execution-order items shipped:
SignalDetail rebuild w/ semantic neighbors (#228 §6 item 1, `c6470cf`), dock
tabs + AtlasHeatList → HEAT/anomaly/sources then corrected to anomaly|sources
(#183 closed; #231 heat-as-map-property), person→subject hygiene (#176,
`96fef18`/`2ae494d`/`cb52730`), gate-recall-by-language script (`4911051`). The
deeper L2 re-review continued in `2026-06-26-l2-deep-review.md` (Tier A/B/C). L3
verdict (sound, needs only #227) — **#227 closed 2026-06-26**. This note is the
delivery record; the body is the original judgment.
