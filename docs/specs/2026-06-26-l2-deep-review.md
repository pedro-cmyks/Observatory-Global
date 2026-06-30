# L2 Console Deep Review — Connections, Critical→Evidence, Public Attention

Date: 2026-06-26
Scope: the `/app` L2 console (map · stream · threads · drill-in panels ·
public-attention dock · workbench), desktop + the new mobile tabbed IA.
Method: code inspection (file:line) + live production API probes
(`atlas-api-pedro.fly.dev`, read-only) on the exact failing case the user
hit (Côte d'Ivoire / CI). Predecessors: `2026-06-11-surfaces-editorial-review.md`
(L1) and `2026-06-12-l2-l3-deep-review.md` (first L2 pass). This is the
current, adversarial, paper-aligned L2 review.
Status: review judgment + prioritized action plan. **No product code changed.**

---

## Verdict in one paragraph

L2's bones are still right — the focus-driven stream-slot state machine and
the threads spine speak the correct contracts — but the surface has one
structural dishonesty that the CI case exposes end to end: **the alert layer
and the evidence layer are computed by different pipelines that never
reconcile, so the console can route a user from a real 26×-baseline volume
spike straight into a single-source, gate-failed, positive, irrelevant
"critical" thread and present it as the country's lead story.** Verified live:
CI shows 238 signals at 26.4× baseline (real local-press surge, mostly
French/`xx`), but every one of its 4 country threads is 1–2 raw assignments,
the "Flood and landslide disaster" thread resolves to `total:0 / rawTotal:1`,
served below-gate as one euronews **beach-tourism** article (sentiment +0.385)
with a fake KEY SUBJECT "ocean atlantic" typed PERSON. Nothing in this chain
is a single bug; it is four correct-in-isolation components — country anomaly,
raw-assignment thread list, scope gate, and GDELT-NER persons — wired so their
disagreements surface as product. Layered on top are two legibility gaps the
user named directly: **there is no visible way to deselect a country** (only
Escape / edge-swipe / the stream back-arrow know how), and **a map click gives
no stream-level feedback** that anything changed. And the area "que más falta
trabajo" — Public Attention — is, for CI, empty search + global-football wiki +
**invisible forums** (Reddit is ingested as `source_family='social'` but no
endpoint or panel exposes it). The fix is not more panels; it is making the
alert→evidence connection honest, giving deselect a button, and rebuilding
Public Attention as one combined, per-country **and** per-thread signal that
finally surfaces the social layer Atlas already collects.

---

## 1. Connection audit — every click path, honest vs broken

The console is three desktop slots: **Panel 1 Map**, **Panel 2 Stream-slot**
(swaps to CountryBrief / ThemeDetail / EntityPanel / PublicAttentionPanel /
ChokepointPanel by focus), **Panel 3 NarrativeThreads** (always mounted),
plus **Panel 4 CorrelationMatrix** and a **tabbed bottom dock**
(ANOMALY ALERT | SOURCE INTEGRITY). `App.tsx:1644–1939`.

| # | Click path | Routes to | Honest? | Evidence |
|---|---|---|---|---|
| 1 | Map country fill → CountryBrief | `setFocus('country', gdelt)` + `handleCountryClick` + fly | **Mostly.** Map heat re-scopes (focusCode branch), stream slot becomes CountryBrief. But see §2 (no deselect, no stream feedback) and §3 (the brief's own internals lie). | `App.tsx:1601–1610`, `:838–924` |
| 2 | CountryBrief thread chip → ThemeDetail (country-scoped) | `onThemeSelect(thread.name)` → `handleThemeSelect(slug, CI)` | **BROKEN (the headline failure).** The "critical" chip (spike marker on row 0) drills into a gate-failed single-source thread. §4. | `CountryBrief.tsx:646–659`, `App.tsx:1772` |
| 3 | NarrativeThreads row → ThemeDetail | `resolveThreadThemeTarget` → theme-detail contract | Sound (suffix-parsed since `0b9ab4a`). Panel-3 silently re-scopes (siblings/dim) with no header note of why. | `App.tsx:1829–1863` |
| 4 | CountryBrief Key Subject (person) → person focus | `setPerson(name)` | **Leaky.** Only `type==='person'` chips are clickable, but typing is gazetteer-only, so "ocean atlantic"-class noise can still be typed person. §4.4. | `CountryBrief.tsx:668–685`, `countryBriefSubjects.ts:60–78` |
| 5 | ThemeDetail country card → right-panel theme-country | `onCountryCardClick` → `rightPanelThemeCountry` | Sound. | `App.tsx:1790` |
| 6 | ThemeDetail person chip → person focus | `onPersonClick` → `setFocus('person')` + map re-scope | Sound mechanism; same garbage-in as #4 (topPersons uses bare `_is_valid_person`, not `rank_key_people`). §4.4. | `ThemeDetail.tsx:945–980`, `thread_packet.py:147–153` |
| 7 | Source name → SourceProfile | `onSourceClick` → `selectedSourceProfile` | Sound. | `App.tsx:1773–1776` |
| 8 | Stream country chip → country scope | `setCountry(c, 'stream')` (sets `filter.country`) | Sound — and notably the ONLY country path that sets the global filter directly. | `SignalStream.tsx:329,509` |
| 9 | Anomaly row → country focus | `setFocus('country', cc)` + fly | Sound. The dock's clearest path; arguably should be the country-selection model everywhere. | `AnomalyPanel.tsx:79–82` |
| 10 | Public-attention item (wiki/search) → PublicAttentionPanel | `handlePublicAttentionSelect` → `/search/unified` bridge | Sound bridge, but the inputs are thin (§5): CI search = 0 rows, global wiki = football. | `App.tsx:506–520`, `PublicAttentionPanel.tsx` |
| 11 | Correlation cell → two-country focus | `setCountry(e1)` | Sound; niche. | `CorrelationMatrix.tsx:70` |
| 12 | Deselect country / "back to whole map" | **No button.** Escape (`popPanel`), left-edge swipe, or the stream `← STREAM` back-arrow only. | **BROKEN — §2.1.** | `App.tsx:665–709`, `:1719–1722` |

### The split-brain on country selection (root of #2 and §3)

Two different mechanisms set "the active country" and they are **not kept in
sync**:

- **`filter.country`** (FocusContext) — drives the SignalStream scope
  (`SignalStream.tsx:175,257`), the dock re-scope, the legend, `useFocusRelation`.
- **`selectedCountry` / `selectedCountryCode`** (App local state) — drives the
  CountryBrief panel, the map highlight (`focusCode`), the flows.

`handleCountryClick` (`App.tsx:442–455`) sets **only the local state** — never
`filter.country`. The map-fill click works because it *additionally* calls
`setFocus('country', gdelt)` (`:1608`), but every *other* country entry point
that goes through `handleCountryClick` alone (CountryBrief cards, ThreadFocus
country select, ChokepointPanel, research-plan open-country) opens the brief
**without** scoping the stream or the dock. So "click a country" means
different things from different surfaces — sometimes the stream follows,
sometimes it doesn't. That inconsistency is the substrate for both legibility
complaints in §2.

---

## 2. Legibility / interaction model

### 2.1 "¿Cómo me des-miro un país?" — deselect has no button

There is **no visible deselect affordance**. Country selection can only be
undone by:
- **Escape** → `popPanel()` (`App.tsx:665–686`), which pops the topmost panel;
- **swipe-right from the left edge** (mobile, `:688–709`);
- the **`← STREAM` back-arrow** inside the stream-slot header when CountryBrief
  is showing (`:1719–1722`, `handleStreamBack`);
- the CountryBrief **`✕`** (which calls `handleStreamBack`, i.e. "back", not a
  clean global clear — and on the desktop it lives inside the brief, not on the
  map).

A new user looking at a selected, half-lit map has no on-screen control that
says "show me the whole world again." `clearFilter()`/`clearFocus()` exist in
FocusContext (`FocusContext.tsx:198–211`) but are not wired to any persistent
chrome element. There is a `FocusIndicator.tsx` component in the tree — **it is
not mounted** in the L2 console (no import in `App.tsx`), so the one component
literally built to show "you are focused on X · clear" is dead.

**Proposed model:** mount a persistent **focus chip / breadcrumb** in the
command bar (or a floating top-left pill over the map) whenever
`isActive` — `"CÔTE D'IVOIRE ✕"` — whose `✕` calls a single unified
`clearAll()` that resets BOTH the local panel state AND `clearFilter()`. The
chip is the always-present answer to "des-mirarme." Reuse/repair
`FocusIndicator.tsx` rather than inventing a new component. Clicking the map
background (a non-country click) should also clear — there is currently no
`map.on('click')` (non-feature) handler at all.

### 2.2 "Click a country, nothing tells me what happened"

A map click on a country swaps the **stream slot** to CountryBrief — that *is*
a change, but it's a panel swap the eye can miss, and the **always-visible
SignalStream is the very panel that got replaced**, so the live feed the user
was watching disappears rather than visibly *re-scoping*. The feedback the user
expects — "the stream is now showing CI" — never happens, because country
selection replaces the stream instead of tinting it, and (per §1) most country
paths don't even set `filter.country`.

**Proposed feedback model (cheapest → richest):**
1. **Focus chip** (§2.1) — the persistent, unambiguous "you selected CI" signal.
2. **Stream scope banner** — when a country is active, the stream-slot header
   (even while showing CountryBrief) and Panel-3 NarrativeThreads should carry a
   one-line `"Scoped to Côte d'Ivoire"` strip with the `✕`. Panel-3 already
   re-scopes silently; label it.
3. **Map ↔ panel handshake** — make `handleCountryClick` *always* call
   `setCountry(code)` so a single source of truth drives stream + dock + map
   highlight together (collapses the §1 split-brain). Then a country click
   visibly re-scopes the stream, dock public-attention, and legend at once.
4. **Walkthrough** — a 2-step coachmark on first country click ("You selected
   a country → its brief opens here, the map dims to its relations, click the
   ✕ to return") reusing the existing `OnboardingCoachmark` pattern.

---

## 3. The critical→empty-thread failure (the most important finding)

Traced end to end on **CI**, every number confirmed against production
2026-06-26.

### 3.1 What the user sees, and where each number comes from

| Surface number | Value (CI) | Source | File:line / API |
|---|---|---|---|
| "240 signals" | 238 | `/api/v2/nodes` `signalCount` (or `signals.length`) | `CountryBrief.tsx:339`; `nodes?focus_value=CI` → `signalCount:238` |
| "sentiment +0.2" | +0.02 ×10 | `/nodes` `sentiment` | `CountryBrief.tsx:330,463`; node `sentiment:0.0216` |
| "4 threads" | 4 | `/api/v2/threads?country_code=CI` row count | `CountryBrief.tsx:258`, `countryBriefThreads.ts:24–41` |
| "20× / 34.3× / CRITICAL" | 26.4× z:3.0 | `/api/indicators/country/CI` `volume` AND/OR CrisisContext `/anomalies` | `indicators` → `multiplier:26.44, baseline:9`; **but CI is NOT in live `/anomalies`** |
| "source diversity 91 / quality 20" | 91 / 20 | `/indicators` | confirmed live |
| "Voice Mix 69%" | — | `/api/v2/voice-mix?country=CI` | `CountryBrief.tsx:259` |
| Thread "Flood and landslide disaster" | `total:0 rawTotal:1` | `/api/v2/theme/flood-landslide-disaster?country_code=CI` | confirmed `warnings:[atlas_topic_gated, below_gate_evidence]` |
| → 1 source euronews.com | 1 | `build_thread_packet` topSources | `thread_packet.py:130–140` |
| → sentiment +0.39 positive | 0.385 | mean of the 1 below-gate signal | `themes.py` atlas detail; live `avgSentiment:0.385` |
| → KEY SUBJECT "ocean atlantic" PERSON | 1 | GDELT `persons[]` → `_is_valid_person` → frontend `buildKeySubjects` | `thread_packet.py:147–153`, `countryBriefSubjects.ts:60–78` |

**Live proof of the broken leaf:**
```
GET /api/v2/theme/flood-landslide-disaster?hours=24&country_code=CI
→ total:0 rawTotal:1 gated:0  signalSample:1  avgSentiment:0.385
  warnings:[atlas_topic_gated, below_gate_evidence]
  topSources:[(euronews.com,1)]  topPersons:[(ocean atlantic,1)]
  signals[0]: euronews.com | "Costa de Marfil, el nuevo destino de playas y
              cultura en África Occidental" | sent +0.385 | persons:[ocean atlantic]
```
The "flood and landslide disaster" thread is, in reality, a single Spanish
**beach-tourism** article ("Ivory Coast, the new beach-and-culture
destination"). "ocean atlantic" is GDELT NER mangling "Atlantic Ocean" from a
beach story into a person.

### 3.2 The four independent failures, pinpointed

**F1 — Alert baseline and evidence are computed by unrelated pipelines.**
The country volume anomaly (`/indicators`: 238 vs baseline 9 = 26.4×, and the
separate CrisisContext `/anomalies` z-score) is pure **signal volume**. It says
nothing about whether any *thread* cleared the gate. The thread layer
(`/threads?country_code=CI`) returns 4 rows of 1–2 raw assignments. **Nobody
joins these.** A country can be "26× critical" and have zero gate-passing
narrative, and the UI never says so. The anomaly badge and the thread chips sit
in the same brief with no shared truth.

**F2 — The "critical" marker is positional, not semantic.**
`CountryBrief.tsx:651` paints the spike bars on `anomaly && i === 0` — the
**first** thread row, whatever it is. `buildCountryBriefThreadSummary` orders
rows by raw assignment count (`countryBriefThreads.ts:28–34`); the backend
country thread list orders by `signal_count DESC` (`thread_intelligence.py:256`),
which is **raw `COUNT(*)` of assignments, pre-gate** (`:66`). So "critical" =
"the thread with the most *raw* assignments," not the one driving the spike and
not one that passed the gate. For CI that happened to be a 1-signal tourism
false-positive.

**F3 — List counts are raw assignments; detail counts are gate-kept. They
never reconcile (#214, concretely).** The list `signal_count` does **not**
filter `gate_kept` (`thread_intelligence.py:62–66`), so the chip reads "1." The
detail applies the gate (`themes.py:536` `COUNT(*) FILTER (WHERE a.gate_kept)`),
so it reads `total:0`, then the **below-gate fallback** (`themes.py:552`
`below_gate_fallback = (not gate_pending) and gated_n == 0 and raw_n > 0`)
serves the raw signal labeled UNVERIFIED. The fallback is doing the serving the
gate refused — exactly the §2.2 finding of the 2026-06-12 review, now visible
as "the critical thread is the empty thread."

**F4 — Persons in the thread packet bypass the syndication-hardened ranker.**
`get_focus_data` uses `rank_key_people` (corroboration floor, syndication
dedup, `themes.py:146`, `utils.py:61–84`). `build_thread_packet.top_persons`
uses **bare `_is_valid_person`** (`thread_packet.py:147–153`) — no floor, no
corroboration. "ocean atlantic" (2 distinct tokens, not in the 40-entry
blocklist) passes, and the frontend gazetteer (`countryBriefSubjects.ts`) has
no entry for it either, so it is typed **person** and rendered as a clickable
KEY SUBJECT. The typed-subjects model (#176) is only as good as a hand-mirrored
gazetteer because `nlp_persons` is throughput-starved (#184) → everything stays
`unverified`.

### 3.3 Why the spike is real but the narrative is empty (the deeper truth)

The 238 CI signals are genuine: `aip.ci` (national agency, 65), `allafrica`,
`abidjan.net`, `fratmat.info` — plus a football story (Côte d'Ivoire advancing
in a tournament). Languages: `xx` 122, `fr` 65, `en` 51. The spike is a **real
local-press + sport surge against a tiny 9-signal baseline.** It produces no
gate-passing thread because (a) the lexical theme gate (`theme-hint-lex-v2`) is
English-biased and can't score French/`xx`, and (b) the one assignment it *did*
make was a mis-hint (beach → flood). This is the same **gate-recall-on-
non-English** finding from 2026-06-12 (Peru 0/43 Spanish), now compounded by a
**low baseline making ordinary local news read as "critical."** The honest
product statement CI should show is: *"Volume spike (26× a very low base),
driven by local-language press and sport; no verified narrative thread cleared
the relevance gate."* Instead it shows a fake disaster.

### 3.4 The connection that is broken

`alert → evidence` has no contract. The brief should never present a thread as
"critical" unless that thread (not the country's volume) is the thing that is
elevated, and it should never lead with a below-gate single-source thread
dressed in spike bars. The fix is a **reconciliation step** (§6) that (a) marks
"critical" from movement/coherence of the thread itself, (b) shows one honest
count semantics across list and detail, and (c) demotes below-gate threads out
of the lead/critical slot into a clearly-labeled UNVERIFIED tray.

---

## 4. Public Attention redesign (search + wiki + forums; per-country + per-thread)

### 4.1 What exists today, measured

- **Search (Google Trends):** shown only when a country is active
  (`AnomalyPanel.tsx:226`). **CI returns 0 trend rows** live; a global trends
  call returns **0 distinct trend countries** — coverage is thin/stale
  (Google rate-limits cloud IPs, the known #104 issue; the panel even has a
  "searches from Nh ago" staleness badge).
- **Wiki (pageviews):** always shown. Global top is currently **football**
  (2026 FIFA World Cup, Beccacece, Ochoa) and `language:null` — the wiki
  edition isn't even surfaced. Per-country wiki exists (`wiki/top?country_code`)
  but is language-edition-shaped, not population-normalized.
- **Forums / social:** **ingested but invisible.** `ingest_reddit.py` pulls 14
  subreddits as `source_family='social'` (`:73–86`), fired from `ingest_loop.py`
  (`:126–128`). **No router exposes a social lane** — `/api/v2/signals` doesn't
  even return `source_family` (live sample: all `?`), has no `source_family`
  filter (`signals.py`), and `build_thread_packet` *can* lane social
  (`thread_packet.py:48–63`) but nothing queries it. So Reddit is dark weight in
  the corpus.

Today the two sources are **stacked, not combined**: `[S]` rows then `[W]` rows
(`AnomalyPanel.tsx:235–285`), country-gated for search, global-or-country for
wiki. For CI the whole section is empty search + global football = **no value.**

### 4.2 Design — one combined Public Attention signal

**Principle:** Public Attention is a *people-side proxy* that should corroborate
or contradict the *press-side* narrative. It must be honest about coverage
(many places have neither trends nor a country wiki edition) and must finally
use the **forum layer Atlas already collects.**

**Backend (one new service + endpoint):** `app/services/public_attention.py`
+ `GET /api/v2/public-attention?country=CC&thread=ID&hours=`, returning a
single ranked list of **attention items** with provenance:
```
{ items: [
  { label, kind: 'search'|'wiki'|'forum', score, provenance,
    country?, lang?, url?, signal_ids?[], thread_overlap? } ],
  coverage: { has_search, has_wiki, has_forum, note } }
```
- **search** = trends rows (when present), provenance `google_trends`.
- **wiki** = pageviews, provenance `wikipedia:<edition-lang>` (surface the
  language — a `de` edition spike about a country is a *German-audience* signal,
  not local attention; that distinction is the honesty).
- **forum** = aggregate the existing `source_family='social'` signals: per
  country (subreddit→country map already exists, `ingest_reddit.py:73–86`) and,
  for a thread, the social signals whose embeddings are semantic neighbors of
  the thread (signal_embeddings exist). Provenance `reddit:r/<sub>`.
- **coverage** is explicit: `has_forum:false` for a country with no mapped
  subreddit, `note:"no local search/wiki edition; forum-only"` etc. — the panel
  renders a labeled gap, never a silent blank (the L1 honesty thesis).

**Combination rule (honest, not a fake blend):** do **not** average across
kinds (they aren't commensurable). **Interleave** by within-kind rank with kind
badges, and add a **corroboration flag** when an item appears in ≥2 kinds (a
search term that is also a forum topic that is also a press thread = a real
cross-surface story). The value is the *agreement*, surfaced as a chip
("searched + discussed + reported"), not a blended number.

**Per-thread Public Attention (the new capability the user asked for):** a
thread should be able to pull related public attention *into the narrative it is
building*. In ThemeDetail, add a "Public Attention for this thread" section fed
by `?thread=ID`: (a) forum signals that are semantic neighbors of the thread
centroid (label UNVERIFIED, social lane — never folded into gated evidence),
(b) trends/wiki items whose text matches the thread label **semantically**
(reuse the embed service) rather than the current lexical `LIKE '%word%'`
(`themes.py` trends/wiki match) which is language-blind and unlabeled. This
makes the thread the unit that aggregates press + search + wiki + forum, which
is the product's whole thesis at the thread grain.

**Frontend:** replace the stacked `[S]`/`[W]` lists in `AnomalyPanel` with the
combined ranked list (badges `search`/`wiki`/`forum`, corroboration chip,
coverage note). Add the per-thread section in `ThemeDetail`. The
`PublicAttentionPanel` drill (item → `/search/unified` → signals/themes) already
exists and stays the leaf.

**Sequencing caveat:** the forum lane is the highest-value, lowest-risk add
because the data is already in the DB — surfacing `source_family='social'` is a
query + a badge, not new ingestion. Do that first; semantic per-thread matching
depends on the embed service being healthy (it is, post-#184 machine
restructure).

---

## 5. Paper alignment

Each L2 surface is evidence for a paper in
`docs/research/atlas-paper/2026-05-27-atlas-papers-master-plan.md`. Where the
surface currently violates the thesis, it weakens the paper's own claim.

| L2 surface | Paper / RQ | Serves the claim? | Violation today |
|---|---|---|---|
| Map country heat (composite, #231) | **P3 Atlas heat** (composite ≠ volume) | Yes — fill uses `/heat/countries`, not volume-rank | None major; volume still drives glow width (intended) |
| Country anomaly badge / indicators | **P3** + **P6** (temporal baseline) | Partly | **F1:** baseline spike presented as narrative criticality with no thread reconciliation → "volume-as-importance" leaks back in |
| NarrativeThreads list + ThemeDetail | **P4 Thread aggregation/evidence sampling** | The spine is the paper's product face | **F2/F3:** raw-count "critical," list/detail count disagreement = the exact evidence-sampling honesty P4 must defend |
| Quality gate / below-gate fallback | **P1 Evidence-role classification** | Gate is P1's result | **F3 + gate-recall:** English-biased gate + fallback-as-server undermines P1's precision claim; non-English recall is unmeasured here |
| CountryBrief / ThemeDetail Key Subjects | **P4** (entities) + **P5** (multilingual NLP) | Aspires to typed NER | **F4:** gazetteer-typed, `nlp_persons` empty (#184) → "ocean atlantic" person; P5's multilingual NER not yet feeding it |
| Sentiment (node + thread mean) | **P5 Sentiment fusion** | Yes | A 1-signal +0.385 presented as a thread's sentiment is a sampling artifact, not fusion — same F3 root |
| Voice Mix panel | **P2/P5** (source provenance, diversity) | Yes — self-coverage by ownership | Sound; honest about `attributable_voices` |
| SourceIntegrity dock | **P2 Source-quality scoring** | Yes (entity-scoped via `/focus`) | Fine |
| Public Attention (trends+wiki) | **P7 Visualization/workflow** + discovery | Weakly | Thin coverage + **forum layer absent** = the people-side proxy is mostly empty; the combined-honest design (§4) is the P7 method |
| Focus propagation (#234) / EntityPanel | **P7** (analyst workflow, relation re-scope) | Yes — the rarity-weighted relation is a P7 method | Deselect gap (§2.1) is a P7 legibility hole |
| Forums/social (dark) | **P8 Open-set discovery** | Not surfaced | Ingested, unqueryable — a discovery input thrown away |

**The cross-cutting violation:** P1, P3, P4, P5 all rest on the claim *Atlas
shows verified, gated, importance-ranked narrative, not GDELT volume.* The CI
chain shows L2 doing the opposite at the leaf — volume spike → raw-count
"critical" → below-gate single source → GDELT-NER person. Fixing §3 is fixing
the papers' product evidence, not just a UI bug.

---

## 6. Prioritized action plan

Three tiers. Items inside a tier are roughly parallelizable.

### Tier A — Cheap legibility wins (frontend-only, days)

**A1. Persistent focus chip + unified deselect.** Mount/repair
`FocusIndicator.tsx` in the command bar (or a floating map pill) whenever
`isActive`; its `✕` calls a new `clearAll()` that resets local panel state AND
`clearFilter()`. Add a `map.on('click')` background handler that clears.
*Files:* `App.tsx` (mount + `clearAll`), `FocusIndicator.tsx`,
`FocusContext.tsx` (expose a combined clear if helpful).
*Payoff:* answers "¿cómo me des-miro un país?" directly; removes the worst
new-user dead end. *Deps:* none.

**A2. Country selection = one source of truth.** Make `handleCountryClick`
always call `setCountry(code)` so every country entry point scopes the stream,
dock, legend, and map highlight together. *Files:* `App.tsx:442–455` and the
`useEffect` at `:626–660` (avoid the double-set loop).
*Payoff:* the §2.2 "nothing happened" feedback (stream + dock visibly
re-scope); collapses the §1 split-brain. *Deps:* A1 helps (chip shows the
result). *Risk:* medium — touch the focus/country effects carefully; verify no
refetch loop.

**A3. Scope strips / labels.** Add a `"Scoped to <country>"` strip with `✕` to
Panel-3 NarrativeThreads (it already re-scopes silently) and to the stream-slot
header. Add sibling/dim **reason chips** are already in NarrativeThreads — keep.
*Files:* `NarrativeThreads.tsx`, `App.tsx` stream header.
*Payoff:* makes silent re-scopes legible. *Deps:* A2.

**A4. First-country-click walkthrough.** 2-step `OnboardingCoachmark` on first
country selection. *Files:* `App.tsx`, `OnboardingCoachmark.tsx`.
*Payoff:* teaches the select/deselect model once. *Deps:* A1/A2.

### Tier B — Deeper data-flow fixes (the critical→evidence honesty)

**B1. Reconcile alert ↔ evidence; kill positional "critical."** (a) Stop
painting spike bars on `i===0`; mark a thread "critical/elevated" only from the
thread's **own** movement/coherence (`changed_10h`, `avg_confidence`), not the
country volume. (b) When the country is anomalous but **no thread clears the
gate**, render the honest standfirst: *"Volume spike (Nx low base); no verified
thread cleared the gate."* *Files:* `CountryBrief.tsx:646–659`,
`buildCountryBriefThreadSummary` (`countryBriefThreads.ts`), and a small backend
field (`is_below_gate`/`gate_pending`) per country thread row in
`thread_intelligence.py`. *Payoff:* the headline failure stops happening.
*Deps:* B2 for the per-thread gate flag.

**B2. One count semantics across list and detail (#214).** Either expose
`gated_signal_count` alongside `signal_count` in the country thread list and
render the **gated** number as the chip count (with raw on hover), or label the
chip "N assigned (unverified)" when `gated=0`. Move below-gate threads out of
the lead/critical slot into a labeled **UNVERIFIED tray** (the L3 honesty model
L2 should copy). *Files:* `thread_intelligence.py` (add gate-kept count to the
country list CTE — the `scoped`/`topic_agg` blocks at `:62–93`), `themes.py`
(already has gated/raw), `CountryBrief.tsx` rendering. *Payoff:* list and detail
stop disagreeing; below-gate stops masquerading as critical. *Deps:* none hard.

**B3. Thread persons use the syndication-hardened ranker.** Replace bare
`_is_valid_person` in `build_thread_packet.top_persons` with `rank_key_people`
(corroboration floor + syndication dedup), passing distinct-headline/outlet
counts. *Files:* `thread_packet.py:147–153`, `utils.py:61–84` (already exists).
*Payoff:* "ocean atlantic"-class single-signal noise drops out of KEY SUBJECTS;
unifies with the focus path. *Deps:* none. *Note:* the real fix is NER
throughput (#184) flipping `unverified→verified`; this is the cheap floor.

**B4. Gate-recall by language (measurement → re-prioritize #162).** Run/extend
`scripts/gate_recall_by_language.py` over the current corpus; if non-English
keep-rate is near-zero (CI/Peru evidence), the gate is a language gate and #162
(multilingual scoring) moves up. *Files:* the existing script.
*Payoff:* data to justify the gate rebuild that B1/B2 are working around.
*Deps:* none.

### Tier C — New capability: Public Attention + forums (§4)

**C1. Surface the forum lane (highest value, lowest risk — data already exists).**
Add `source_family` to `/api/v2/signals` output + a `source_family` filter; add
a `GET /api/v2/public-attention` forum aggregation per country (subreddit→country
map exists). *Files:* `signals.py`, new `public_attention.py` service + router.
*Payoff:* Reddit stops being dark weight; CI-class countries with empty
search/wiki get *some* people-side signal. *Deps:* none.

**C2. Combined, honest Public Attention panel.** Replace stacked `[S]`/`[W]`
with one ranked, badged, coverage-noted list (search/wiki/forum + corroboration
chip + explicit gaps). Surface wiki **edition language**. *Files:*
`AnomalyPanel.tsx`, the new service. *Payoff:* the section stops being empty
noise; agreement across surfaces becomes the signal. *Deps:* C1.

**C3. Per-thread Public Attention.** Add a "Public Attention for this thread"
section in ThemeDetail fed by `?thread=ID`: semantic-neighbor forum signals
(UNVERIFIED, social lane) + semantically-matched (not lexical) trends/wiki.
*Files:* `ThemeDetail.tsx`, `public_attention.py` (embed-service match), replace
the lexical `/trends/match`+`/wiki/match` joins. *Payoff:* the thread becomes
the press+search+wiki+forum aggregator — the product thesis at thread grain
(P7). *Deps:* C1/C2 + healthy embed service (currently healthy).

### Recommended order

1. **A1 + A2** (deselect chip + single-source-of-truth country) — fixes both
   named legibility complaints; unblocks A3/A4.
2. **B2 + B1** (count semantics + reconcile critical) — fixes the headline
   CI failure; B3 rides along cheaply.
3. **C1** (surface forums) — unlocks the public-attention rebuild with data
   that already exists.
4. **A3/A4**, **B4**, then **C2 → C3**.

A-tier is independent of B/C and should not wait on them. B1 depends on B2's
per-thread gate flag. C2/C3 depend on C1.

---

## 7. Mobile L2 (tabbed IA) note

The mobile IA collapses the console to one full-screen surface via a bottom tab
bar **Map · Threads · Stream** (`App.tsx:295`, `:1943–1960`), and
auto-forwards to the Stream tab when any drill-in opens (`:714–723`). This
**serves** the connections better than a shrunk desktop — one surface at a time,
native back via edge-swipe (`:688–709`). But it inherits every §2/§3 fault and
adds one: with the dock (anomaly/public-attention/sources) **not in the tab
set**, mobile users lose Public Attention and Source Integrity entirely. When
§4's combined Public Attention ships, add it as a 4th mobile tab (or fold it
into the Threads/Stream surface) so the people-side proxy isn't desktop-only.
The deselect chip (A1) is *more* important on mobile, where there's no Escape
key — today only edge-swipe deselects.

---

## 8. What is genuinely fine (don't touch)

- The focus stream-slot state machine and the `popPanel` back model (just needs
  a visible front-door, §2.1).
- Map composite heat (#231) and the #234 focus propagation / rarity-weighted
  sibling relation — sound and paper-aligned (P3/P7).
- SourceIntegrity entity-scoping, Voice Mix self-coverage honesty (P2).
- The L3 Workbench honesty model — L2's below-gate tray (B2) should copy it.

---

## Execution status (2026-06-26, spec-driven sync)

The action plan (§6) was executed this session. Tier status:

- **A1 + A2** ✅ — focus chip + unified deselect + single-source-of-truth country
  select (chip later redesigned compact).
- **A3 scope strips** ✅ — shipped `6dfa6a0` (NarrativeThreads "Scoped to X ✕"
  for country+person, blank-stream-slot strip, sibling reason chips). Was
  mislabeled remaining; verified rendering live 2026-06-30.
- **A4 first-country-click walkthrough** ✅ — shipped 2026-06-30
  (`CountryFocusWalkthrough.tsx`, own `atlas_country_walkthrough_v1` key, fires
  once on the first `handleCountryClick`, guarded against stacking on the
  first-session tour; step 2 highlights the focus-chip ✕ on desktop). On mobile
  it is a vertically-centered card (`CountryFocusWalkthrough.css`
  `cfw-card-mobile`), NOT the shared bottom sheet — the bottom sheet's
  `bottom:16px !important` collided with the mobile tab bar + the floating focus
  chip and clipped the buttons (Pedro caught this). Copy is position-accurate
  per platform ("Click"/"top-left" vs "Tap"/"above the tabs"). Browser-verified
  desktop (1440) + mobile (375).
- **B1** ✅ killed the positional "critical" spike. **B2 (#214)** ✅ gated count +
  UNVERIFIED tray (list/detail reconciled; #214 closed). **B3** ✅ thread subjects
  via `rank_key_people`. **B4 gate-recall-by-language** — script shipped earlier
  (`gate_recall_by_language.py`), not re-run on the current corpus (measurement
  pending).
- **C1** ✅ forum lane (`/api/v2/public-attention` + `source_family`). **C2** ✅
  combined Public Attention (Trends+Wiki+Forum) + mobile **Pulse** tab.
  **C3 per-thread Public Attention** — forum part ✅ shipped
  (`public_attention.fetch_forum_thread_attention` = social signals that are
  semantic neighbors of the thread centroid; ThemeDetail "DISCUSSION ·
  UNVERIFIED" section, data-dependent render). **C3(b) semantic trends/wiki**
  ⏳ DEFERRED (Pedro 2026-06-30): the per-thread trends/wiki match is still
  lexical (`/trends/match`+`/wiki/match`, GDELT-theme-code → ~dead for
  dynamic-topic threads). Deferred because (1) trends/wiki coverage is
  thin/stale (Google rate-limits cloud IPs, #104) → low ROI today; (2) the live
  path embeds ~100 trends/wiki candidates per ThemeDetail open on the shared Fly
  embed box, and the cheaper pre-embed-in-cron path touches the reserved
  AtlasLocalWorker tree. **Impl note for when it's worth doing:** pre-embed
  trends/wiki text in the M1 embed cron (off-peak) so per-open is a cheap ANN vs
  the thread centroid, mirroring `signal_embeddings`; OR live-embed behind a
  short Redis cache. Render honestly with a coverage note when empty.
- **Spun out:** the item→thread connection direction became the truncated-thread
  spec (`2026-06-26-truncated-narrative-thread.md`), which also delivered the
  forums-in-inference work referenced in §4.

Remaining: B4 (gate-recall re-run — reserved/gate-adjacent), C3(b) semantic
trends/wiki (deferred, see above). A3/A4/C3-forum all ✅ as of 2026-06-30.

## Live connectivity verification (2026-06-30, click-by-click in the browser)

§1's connection audit was re-verified LIVE (not from the doc, which had proven
stale). **Spine confirmed wired:** NarrativeThreads→ThemeDetail; ThemeDetail
source→expand(headlines)→"Full source profile ↗"→SourceProfile; ThemeDetail
per-thread forum + Key Subjects; Anomaly row→country→CountryBrief; CountryBrief
Key Subject(person)→EntityPanel; #234 person propagation (threads "Scoped to X"
+ dim, dock "PERSON→country"); public-attention item→PublicAttentionPanel;
signal headline→SignalDetail "Where this fits" (connected_threads RELATED 86% +
Semantic Neighbors, GDELT collapsed) = truncados wired. **Two leaf bugs found +
FIXED:** (A) country nav (anomaly/map) did NOT swap the stream slot when a
ThemeDetail was open — `handleCountryClick` didn't clear `selectedTheme` so
`isTheme` kept the slot (chip updated, content stale); now clears it. (B)
CountryBrief "Top Publishers" jumped to the bare SourceProfile (inconsistent
with ThemeDetail) → now the same expand pattern. **Data-quality (NOT wiring,
logged):** global Public Attention = football/celebrity/`fr`-wiki-mainpage noise
(§4.1, #104 rate-limit); Anomaly `A-001 = "XX"` (invalid geo code, 65.7× — bad
subject-country tag surfacing as a top anomaly). Not re-verified (minor): stream
country chip, correlation cell, map-background deselect.

## The unified-engine connection — attention + anomaly are the missing roles (Pedro, 2026-06-30)

→ **For the engine track** (`2026-06-29-atlas-unified-engine.md`). Written here,
not there, to avoid colliding with that session's in-flight edits; the user is
the bridge — fold it in when the tracks meet.

Pedro's insight, reached from the D/E fixes: **the Unified Engine should also
consider Wiki, Trends and the Anomaly layer — and today it does not.** Verified
against the spec: `topic_members.role` is a 4-value enum
`('evidence','discussion','mood','movement')` = press / forum-social / forum-mood
/ events. Its "attention" (§9.2 `public-led` / `uncoupled-attention`) is
**forum-only**. §14 "Deferred" lists only causal cross-vocab linking — so wiki/
trends/anomaly are **not deferred-on-purpose, just unscoped.** Two real gaps:

1. **No `attention` role (Wiki + Google Trends).** The people-side *reading* and
   *searching* proxy lives in `wiki_pageviews_v2` / `trends_v2`, surfaced by a
   SEPARATE bolted-on pipeline (`public_attention.py`, AnomalyPanel) — never a
   typed member of a topic. A thread cannot say "N people read my Wikipedia
   article / searched my terms." This is exactly **C3(b)**: an `attention` role
   subsumes it. The #168 types (`public-led`, `uncoupled-attention`) can only
   fire on forum today because that is the only attention the engine sees.

2. **Anomaly / volume-baseline is not reconciled into the topic.** The country-
   volume anomaly (CrisisContext `/anomalies`, z-scores) and the thread/evidence
   layer are different pipelines that never meet — **the §3 split-brain, proven
   harmful** (CI: 26× spike → no gate-passing thread → fake "Flood disaster"
   lead). Finding **E** ("XX" anomaly) is the same family: the volume layer
   emits un-attributable spikes with no topic to anchor them. A topic should
   carry its OWN volume-vs-baseline as `movement` (or a topic property), so
   "critical/elevated" is a property of the *thread's* elevation, not orphaned
   country volume. The L2 **B1** serving fix (mark critical from the thread's own
   movement) is the down payment; this is the construction-side root fix.

**Why they're absent:** the engine's substrate is "embeddable signal → nearest
topic centroid." Wiki/trends are *aggregates* (title/keyword + country, not
signal text); anomaly is a *country statistic*. Neither fits "embed a row,
assign it" — so both were left as side pipelines, which is the structural cause
of the split-brain the L2 audit keeps hitting.

**Proposal (additive, A/B-gated like the rest of the engine):**
- Add `attention` to the role enum. Bind wiki-title / trend-keyword to a topic by
  the SAME semantic match C3(b) needs (embed the text, cosine vs centroid) OR
  country+time co-occurrence. `verified=false`, never evidence — same honesty
  invariant as discussion. Now `public-led` / `uncoupled-attention` differentiate
  on REAL reading/searching data, not forum-only.
- Compute per-topic volume-vs-baseline → a `movement`-class signal (or a topic
  field), so the alert layer becomes a topic property. Closes §3 split-brain;
  retires the orphaned country-anomaly-as-lead path that produced the CI failure
  and the "XX" noise.

Net: it makes the engine actually *unified* — one substrate for press + forum +
events + **attention** + **alert/movement** — instead of leaving the two
people-side/volume layers as the bolt-ons that generate L2's worst dishonesty.
Cross-refs: §3 (split-brain), §4 (public attention / C3 forum + C3b trends/wiki),
finding E (volume-layer noise), #168 (relationship types), #172 (silent-risk),
#104 (trends coverage that an attention role would baseline-normalize).
