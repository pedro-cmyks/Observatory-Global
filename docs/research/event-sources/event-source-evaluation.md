# Event-source evaluation — precise event→topic binding (#232)

**Date:** 2026-06-30 · **Issue:** #232 (narrative threads carry no precise connected events)
· **Principle (Pedro):** add a source ONLY to fix an identified root-cause gap, never for
novelty. Every recommendation below names the exact gap it closes.

## Execution status — 2026-07-01 (SHIPPED)

Both tracks built, verified, deployed:
- **§1 source_url binding — PERSISTED + CRON'D.** `compute_event_movement --write` runs in the
  scoped-snapshot runner Step 4 (M1). 520 movement members live (Iran/Sudan precise, zero
  country fan-out).
- **§2 disaster sources — BUILT + DEPLOYED.** `disaster_events_v2` (mig 062); `ingest_disasters.py`
  (USGS FDSN + GDACS GeoRSS, no key) wired into `ingest_loop` every 8th cycle — live-verified 248
  events (23 USGS quakes @max M6.0 + 225 GDACS hazards). `bind_disaster_movement.py` binds
  geo-temporally (type→category + dominant-evidence-country + window overlap) in runner Step 4b —
  verified zero fan-out: 6 JP quakes→"Japan Earthquakes", PH quake→"Philippines 7.8 Tsunami",
  BR flood→"Heavy Rains in Pernambuco", GB storm→"Orkney Stormy Summer".
- **Latent bug fixed (surfaced by §2):** the #168 relationship endpoint's role-count SQL filtered
  ALL roles by the v1-compat engine_version, so movement (movement-v1 + disaster-v1) was NEVER
  counted. Movement is the event layer, engine-version-independent → now counted for any
  `member_kind='event'`. Japan Earthquakes: evidence 17, movement 8.
- **REMAINING (unchanged):** EM-DAT stays offline-only; Event Mentions #159 widens §1 recall;
  unified-v2 F3 swaps the `dyn_sig` CTE to full membership; GDACS magnitude parse is best-effort
  (alert_level carries severity meanwhile).

---

## 0. The root-cause gap

Narrative threads have no *precise* connected events. The engine already ingests GDELT CAMEO
into `events_v2` (~470K rows / 168h, columns: `global_event_id`, `timestamp`,
`actor1_name`/`actor2_name` (noisy CAMEO codes), `action_country_code`, `event_root_code`,
`quad_class` (4 = material conflict), `goldstein_scale`, `latitude`/`longitude`, `num_articles`,
`source_url`, …). But CAMEO events are **country-level and text-less**, so the only shared key
with a thread was `action_country_code` + time. Binding on country **over-binds**: every crisis
thread in a country receives that country's events indiscriminately — "Sudan Conflict Escalation"
and "Sudan Election Dispute" both get the same Darfur rows. That is the coarse
`compute_event_movement` v1 this evaluation replaces.

Two sub-gaps, addressed in two independent tracks:

| Gap | Category where it bites | Fix |
|---|---|---|
| **A. Conflict/political events not bound to the *specific* thread** | conflict, protest, politics, legal | **`source_url` binding** (built, §1) — no new source |
| **B. Natural-hazard events absent from CAMEO entirely** | earthquake, volcano, flood, storm, wildfire | **structured disaster APIs** (USGS, GDACS) — §2 |

---

## 1. The `source_url` binding (BUILT + dry-run verified)

### Mechanism

`events_v2.source_url` is **100% populated** (470,105 / 470,105 over 168h). ~**82%** of recent
events (24h: 59,481/72,323 = 82.2%; 48h: 82.6%) share their `source_url` with an
already-ingested `signals_v2` row. That signal is already embedded + clustered into a dynamic
topic. So an event binds to the **one topic of the article it was extracted from** — no new
source, no permissions, no country-level fan-out:

```
events_v2.source_url ── = ── signals_v2.source_url
                                    │  (that signal is a member of…)
                                    ▼
                dynamic_topic_members → emergent_clusters.sample_signal_ids
                                    │
                                    ▼
                          dynamic_topics.id → 'dynamic-topic-<id>'
```

Implemented in `backend/scripts/compute_event_movement.py` (rewritten). Writes:

```
topic_members(
    signal_id      = NULL,                 -- non-signal member (mig 060)
    member_kind    = 'event',
    member_ref     = global_event_id::text,
    topic_id       = 'dynamic-topic-<id>',
    role           = 'movement',
    source_family  = 'event',
    basis          = 'co_occurrence',
    confidence     = min(1.0, num_articles/50),
    gate_kept      = false,                 -- verified=false: context, never evidence
    engine_version = 'movement-v1'
)
```

Recomputed each pass (`DELETE … WHERE role='movement' AND member_kind='event' AND
engine_version='movement-v1'` then re-insert) — a rolling-window snapshot. Per-topic cap of 8
(highest `num_articles` first) via `ROW_NUMBER()`, because one `source_url` averages **4.67**
CAMEO event rows (max 220) — a single article spawns many event rows and must not flood a topic.

### Precision — VERIFIED (the Iran test passes)

Dry-run, 168h, quad 3/4:

```
BIND (source_url) 168h quad 3/4: 342 event->topic pairs · 301 distinct events · 64 topics touched
  fan-out (topics per event): 1→260ev, 2→41ev          ← NO country-level fan-out

  ev 1311176730  q3 BA  Bahrain      ( 8 arts) -> dynamic-topic-49 [US Iran Exchange Strikes]
  ev 1311176729  q3 IR  Iran         ( 2 arts) -> dynamic-topic-49 [US Iran Exchange Strikes]
  ev 1311405585  q4 US  Denver, CO   ( 6 arts) -> dynamic-topic-54 [Democratic Primary Results]
  ev 1311345166  q4 CA  Metchosin BC ( 8 arts) -> dynamic-topic-43 [Escaped Inmate Found Dead]
```

**The Iran conflict event binds to the Iran-conflict thread (`dynamic-topic-49 "US Iran Exchange
Strikes"`), NOT to every Iran or US thread.** 260 events bind to exactly 1 topic, 41 to 2
(genuine co-membership — the article is in two clusters). **Zero events fan out across country
threads** — the exact defect of the v1 country binding, eliminated.

Coverage scales with the window (all-quad): 48h → 37 topics / 174 events; 72h → 55 / 277;
168h → 83 / 470. 24h returns 0 because the currently-active topics' `sample_signal_ids`
reference their last-snapshot signals, which skew slightly older than 24h — **168h is the
correct default**.

### Precision inheritance (honest caveat)

The binding is precise *to the article*: it faithfully propagates whatever topic that article was
clustered into. One observed row — a Kenya police story (`ghanamma.com/…kenya-police-chief…`,
correctly 1 signal + 4 KE events) → `dynamic-topic-17 "TMC MPs Attacked in Bengal"` — is a
**pre-existing clustering error** (#224 black-hole), NOT a binding defect. The event→signal→topic
chain is exact; it inherits cluster quality. This is the correct behaviour: events ride the same
identity the article already has.

### Coverage constraint + the swap-point (spec §10)

Today, dynamic-topic membership is reachable only through the **capped**
`emergent_clusters.sample_signal_ids` (~24 signals/topic; 6,229 distinct sampled signals across
373 active topics). So the binding currently reaches the ~1.6K events / ~83 topics whose article
lands in a topic's *sample*, not the full ~82% match rate. **Full per-signal dynamic membership
arrives with unified-v2 (F3)** — when `topic_members(role='evidence', engine_version='unified-v2')`
carries the complete dynamic membership. The `dyn_sig` CTE in the script is the single seam to
swap: replace its body with a read of that table and coverage jumps to the full match rate with
no other change. Documented in the script docstring.

### Status: READY TO WRITE (precision confirmed, not yet persisted)

Per the dry-run-only constraint, nothing was written to serving. The INSERT path was validated
inside a **rolled-back transaction** (50 rows inserted with the correct shape — `signal_id=NULL`,
`member_kind='event'`, `member_ref`, `source_family='event'`, `basis='co_occurrence'`,
`gate_kept=false` — then rolled back; post-rollback serving count = 0). The mig-060 default-ref
trigger + nullable `signal_id` handle the non-signal member correctly. Run
`python -m backend.scripts.compute_event_movement --write` to persist once greenlit; the natural
home is the 30-min classifier cron (fresh evidence) or the M1 embed cron beside the ETL
projection.

---

## 2. Structured disaster event sources (Gap B — natural hazards CAMEO can't provide)

**Why CAMEO fails here.** GDELT CAMEO codes *political/verbal actions between actors* (protests,
statements, strikes, aid). A physical M7.8 earthquake, a Category-4 cyclone, or a volcanic
eruption has **no CAMEO event representation** — there is no "actor" and no "action code" for the
Earth moving. Yet these are live, high-volume threads in the engine right now:

```
active disaster dynamic topics (sample):
  dynamic-topic-83   Philippines 7.8 Earthquake Tsunami
  dynamic-topic-247  Venezuela Earthquakes Kill 32     (+ ~11 sibling VE-quake threads)
  dynamic-topic-680  Japan Earthquakes
  dynamic-topic-185  Tropical Storm Arthur Forms
  dynamic-topic-845  Accra Flood Crisis Response
atlas_topics disaster category:  flood-landslide-disaster
#204 candidate-v2 adds:          earthquake-volcano, wildfire-storm
```

A disaster thread today can only carry the *articles about* the quake, never the **authoritative
physical event** (epicentre, magnitude, depth, tsunami flag). That is the precise gap the two
structured feeds below fill — and both bind the same precise way as §1 once ingested, *plus* a
geospatial fallback (lat/lon + time + magnitude → the disaster topic) that CAMEO can't offer.

### 2.1 USGS Earthquake API (FDSN `event/1/query`) — **RECOMMEND (ingest)**

- **Free / no application:** yes. Public USGS FDSN web service, **no API key**, no registration.
- **Data:** GeoJSON with per-event `mag`, `latitude`, `longitude`, `depth`, `time` (epoch ms),
  `place` (human string), `tsunami` flag, `url`, `sig` (significance). Query params
  `starttime`/`endtime`, `minmagnitude`, `limit` (≤20,000), bbox/radius, `orderby`.
- **Root-cause it fixes:** the *only* authoritative, real-time, machine-readable global
  earthquake feed with magnitude + epicentre. A USGS M≥4.5 event binds to the
  **`earthquake-volcano`** topics (candidate-v2) and to live threads like *Philippines 7.8
  Earthquake Tsunami* / *Venezuela Earthquakes Kill 32* / *Japan Earthquakes* — which CAMEO
  cannot represent at all. Precision path: the earthquake's own `place`/country + time window +
  magnitude → the matching disaster topic (geospatial + temporal), and where a signal already
  cites the USGS event page, the exact §1 `source_url` binding applies.
- **Cost:** trivial — one polled GeoJSON pull (e.g. M≥4.5, last N hours) per ingest cycle.
- **Recommendation:** **ingest.** Highest-value, lowest-friction disaster source; it directly
  lights up threads that are already live and currently event-less.

### 2.2 GDACS (Global Disaster Alert & Coordination System) — **RECOMMEND (ingest)**

- **Free / no application:** yes. RSS/GeoRSS + CAP from the EU JRC; **CC-BY-4.0** (credit GDACS).
  No key.
- **Data:** per-alert `eventtype` (**EQ / TC / FL / WF** = earthquake / tropical cyclone / flood /
  wildfire), `latitude`/`longitude`, country + ISO3, event time, **alert level** (Green/Orange/Red)
  + alert score, and type-specific severity (magnitude, wind speed, area burned, deaths/displaced),
  population affected.
- **Root-cause it fixes:** extends structured coverage to the **non-earthquake** hazards CAMEO
  also misses — **floods, cyclones/storms, wildfires** — binding to `flood-landslide-disaster`,
  `wildfire-storm` (candidate-v2), and live threads like *Tropical Storm Arthur Forms* / *Accra
  Flood Crisis Response* / *Twin Storms Pound Japan*. GDACS adds an **alert-severity** dimension
  (Green/Orange/Red) that is a natural `confidence`/priority input for the movement member.
- **Cost:** one RSS pull per cycle; complements USGS (GDACS covers floods/cyclones/wildfires;
  USGS is deeper + faster on earthquakes specifically).
- **Recommendation:** **ingest**, second after USGS. Together they cover the full natural-hazard
  set (quake / volcano-proxy / flood / cyclone / wildfire) that CAMEO structurally cannot.

### 2.3 EM-DAT (CRED international disaster database) — **DO NOT ingest (no gap fixed)**

- **Free:** open portal (public.emdat.be), non-commercial, but **download/account-gated, no
  real-time API.** Retrospective: records 1900→present, curated for disaster-risk-reduction and
  historical analysis, updated on a lag.
- **Root-cause check:** the engine's gap is *live* event binding to *current* threads. EM-DAT is a
  historical/analytical corpus with an embargo, not a real-time feed — it fixes **no live gap**.
- **Recommendation:** **do not ingest for movement binding.** Reserve for offline analysis /
  paper-track ground-truth (e.g. validating that Atlas surfaced a disaster EM-DAT later confirmed)
  — a research artifact, not an engine input.

**Disaster-source verdict:** ingest **USGS + GDACS** (free, no application, real-time, lat/lon +
time + type + magnitude/severity), each binding to the disaster topics CAMEO can't represent.
Skip EM-DAT (retrospective, no live gap).

---

## 3. GDELT DOC 2.0 (#161) + Event Mentions (#159) — richer for binding?

- **GDELT DOC 2.0 (#161):** an *article/document* search API (ArtList/ToneChart/etc.), not an
  event stream. It returns matching news URLs + tone/theme. For *binding events to threads* it
  adds little the engine doesn't already have — Atlas already ingests the article corpus into
  `signals_v2` and embeds it. DOC 2.0 is a **recall lever for the article side** (surfacing more
  URLs to embed), overlapping #229, **not** an event-binding improvement. Not needed for #232.
- **GDELT Event Mentions (#159):** the **directly relevant** upgrade. The Mentions table records,
  per event, **each individual article that mentioned it** (with its own URL + timestamp), instead
  of CAMEO's single representative `source_url`. That means an event could bind through **any** of
  its mentioning articles, not just the one `source_url` — materially **raising the §1 match rate
  and coverage** (recall of the precise binding), using the exact same
  `mention_url → signals_v2 → topic` mechanism. It is the natural follow-up to widen §1 before
  unified-v2 lands.

**Assessment:** DOC 2.0 (#161) does not improve event→thread binding (it's an article-recall
tool). **Event Mentions (#159) does** — it multiplies the precise `source_url` join across every
mentioning article and is the recommended recall extension of §1, complementary to the unified-v2
full-membership swap. Neither changes the *binding mechanism*; #159 changes its *coverage*.

---

## 4. How events serve in the engine (the `movement` role)

**Construction (unify) → serving (separate).** Events enter the one typed `topic_members` table
with `role='movement'`, `member_kind='event'`, `verified=false` (`gate_kept=false`,
`source_family='event'`). They are **never evidence** — an event is provenance/context that a
thread's story corresponds to a real-world action or hazard, not a source that proves a claim.

- **Relationship endpoint** (`GET /api/v2/topic/{id}/relationship`,
  `app/services/topic_relationship.py`): already counts `movement_count` as a **distinct** role,
  deliberately kept OUT of the evidence/discussion/mood press-vs-public ratio (movement is context,
  not an attention signal). Verified in `classify_relationship(movement=…)` → `movement_count` in
  the response; an uncoupled topic reports "N movement signal(s) only".
- **ConflictEventPanel** (`frontend-v2/src/components/ConflictEventPanel.tsx`): the surface that
  renders a thread's connected events. With movement members populated, it reads **"this thread
  has N connected events"** and lists them (location, magnitude/quad, num_articles), each labeled
  context (verified=false), never mixed into the evidence/coverage headlines.
- **Independence:** a movement member carries `signal_id=NULL` and is keyed by
  `member_ref=global_event_id` (mig 060 PK `(member_kind, member_ref, topic_id, role,
  engine_version)`), so the event stays independently addressable and **never dissolves the
  topic**.

**End state.** `source_url` binding (§1, built) gives precise conflict/political event context
today; USGS + GDACS (§2) extend precise context to natural hazards CAMEO can't represent;
Event Mentions #159 (§3) widens §1's recall; unified-v2 F3 swaps the `dyn_sig` CTE to full
membership for full coverage. Every step is grounded in the one root-cause gap — threads with no
precise connected events — and nothing is added for novelty.

---

## Appendix — verification commands

```bash
# precision dry-run (the Iran test): conflict-only, 168h
python -m backend.scripts.compute_event_movement --dry-run --conflict-only --hours 168

# coverage by window
python -m backend.scripts.compute_event_movement --dry-run --hours 168   # all quad
python -m backend.scripts.compute_event_movement --dry-run --hours 48

# persist (ONLY once greenlit — writes movement members to serving)
python -m backend.scripts.compute_event_movement --write
```

Facts measured (168h, prod via `/Users/pedro/AtlasLocalWorker/.env`): `events_v2` source_url
100% populated; 82.2% match at 24h; 4.67 events/source_url (max 220); binding fan-out 260×1-topic
+ 41×2-topic (quad 3/4), zero country fan-out; INSERT path validated in a rolled-back transaction.
