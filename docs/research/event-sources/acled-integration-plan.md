# ACLED Integration Plan — precise conflict events for narrative threads

**Date:** 2026-07-01. **Issue:** #232 (threads have no connected conflict events).
**Root-cause problem:** Atlas narrative threads carry no *precise* real-world
events. The only event source wired today is **GDELT CAMEO** (`events_v2`, ~1M+
rows), which is **country-level and text-less** — too coarse to bind a specific
event to a specific thread. **ACLED** is the gold-standard conflict-event dataset
(typed event, dated, geolocated to lat/lon, named actors, source URLs, fatalities);
its table `acled_conflicts_v2` exists in prod but has **0 rows** because there is no
API key.

**This plan covers:** (1) the access path, (2) the field → schema mapping, (3) how
ACLED events bind to threads — including the Atlas finding that events can bind
**precisely** via `source_url → signal → topic`, with lat/lon + actor as a second
binding path.

---

## 0. What already exists (only the key is missing)

The ACLED path is **already wired end-to-end** in the codebase; it was built
optional and left dormant for lack of credentials:

| Piece | Location | State |
|---|---|---|
| Table schema | `backend/app/db/migrations/007_acled_conflicts.sql` | Applied to prod; 25 columns; PK `event_id_cnty`; indexed on date, country+date, type+date. RLS-locked (migration 030). **0 rows.** |
| Legacy ingest stub | `backend/app/services/ingest_acled.py` | Present but uses the **deprecated** `api.acleddata.com/acled/read` + `key`/`email` auth. Skips cleanly with no key. |
| **New ingest scaffold** | `backend/scripts/ingest_acled.py` | **Written this session.** 2026 OAuth (preferred) + legacy fallback, paginated, maps to the 007 schema, importable, no-key-safe, `py_compile` OK, arity-verified (25 cols == 25 placeholders). |
| Ingest-loop hook | `backend/app/services/ingest_loop.py` (~L81–88) | Calls `run_acled_ingestion()` in a try/except; failure is non-fatal. Currently points at the legacy service. |
| Consumer endpoints | `backend/app/routers/geo.py` | `/api/v2/conflict-markers` (ACLED-first, GDELT `quad_class=4 & goldstein<-3` fallback) and `/api/v2/acled`. Reads columns: `event_id_cnty, event_date, event_type, sub_event_type, actor1, actor2, country, region, location, latitude, longitude, fatalities, notes, source`. |

**Implication:** populating `acled_conflicts_v2` with a valid key lights up the
existing map/marker surfaces immediately, with **no serving changes required**. The
new scaffold preserves the exact column contract `geo.py` reads.

**Cutover note:** the new scaffold lives at `backend/scripts/ingest_acled.py`. When
a key lands, either (a) point the `ingest_loop` import at the scaffold, or (b) fold
the scaffold's OAuth+pagination into the existing `app/services/ingest_acled.py`.
The scaffold is the correct 2026 implementation; the old stub's auth is dead.

---

## 1. Access path (summary — full detail in `acled-access-request.md`)

- **Register** a myACLED account → accept Terms of Use & Attribution Policy →
  request the **Research (non-commercial)** access level (free; API is NOT in the
  free "Open" tier).
- **Auth (2026):** OAuth password grant → `POST https://acleddata.com/oauth/token`
  → bearer access token (24h) + refresh (14d). Legacy `key`+`email` query auth is
  a fallback for older accounts.
- **Read:** `GET https://acleddata.com/api/acled/read?_format=json` with
  `event_date=<from>|<to>&event_date_where=BETWEEN&limit=5000&page=N`. Paginate on
  `page` until a short page returns (~5000 row cap/call).
- **Attribution (mandatory):** `ACLED, accessed on [DATE]. www.acleddata.com.` on
  every surface/export that shows ACLED events, with filters + access date noted.
- **Config:** set `ACLED_USERNAME` + `ACLED_PASSWORD` (OAuth) **or** `ACLED_API_KEY`
  + `ACLED_EMAIL` (legacy) as env/Fly secrets. Absence = ingest skips, table stays
  empty, map layer hides — no breakage.

---

## 2. Field → schema mapping

ACLED read fields → `acled_conflicts_v2` columns (as implemented in
`backend/scripts/ingest_acled.py::_row_values`; all 25 columns fed):

| ACLED field | `acled_conflicts_v2` column | Type handling |
|---|---|---|
| `event_id_cnty` | `event_id_cnty` (PK) | str; `ON CONFLICT DO NOTHING` upsert |
| `event_date` | `event_date` | parsed `YYYY-MM-DD` → DATE |
| `year` | `year` | → int |
| `event_type` | `event_type` | str |
| `sub_event_type` | `sub_event_type` | str |
| `actor1` | `actor1` | str |
| `assoc_actor_1` | `assoc_actor_1` | str |
| `inter1` | `inter1` | → smallint |
| `actor2` | `actor2` | str |
| `assoc_actor_2` | `assoc_actor_2` | str |
| `inter2` | `inter2` | → smallint |
| `interaction` | `interaction` | → smallint |
| `region` | `region` | str |
| `country` | `country` | str |
| `admin1` / `admin2` / `admin3` | `admin1` / `admin2` / `admin3` | str |
| `location` | `location` | str |
| `latitude` / `longitude` | `latitude` / `longitude` | → float (EPSG:4326) |
| `geo_precision` | `geo_precision` | → smallint (default 1) |
| `source` | `source` | str; semicolon-separated source list — **the binding key**, see §3 |
| `source_scale` | `source_scale` | str |
| `notes` | `notes` | text (event description) |
| `fatalities` | `fatalities` | → int (default 0) |

**Fields ACLED returns that the current 007 schema does NOT store** (available if
we extend the table later; not required now): `time_precision`, `disorder_type`,
`civilian_targeting`, `iso` (numeric ISO), `tags`, `timestamp` (ACLED's own
last-updated unix ts), `population_best`. The scaffold requests only the 25 mapped
fields via `&fields=` to keep payloads lean; adding any of the above is a one-line
change to `ACLED_FIELDS` + the schema + `_row_values`.

**Schema note (non-blocking):** ACLED's own `source` is a semicolon-separated list
of the *articles/reports* underpinning the event. It is the highest-value field for
Atlas binding (§3) yet is stored today as a single `VARCHAR(255)` — long lists may
truncate. A future migration widening `source` to `TEXT` (or a normalized
`acled_event_sources` child table of individual URLs) would make the precise bind
more reliable. Not required for a first ingest.

---

## 3. How ACLED events bind to narrative threads (the Atlas finding)

The point of ACLED is not another map layer — it is to attach **verified, precise
events** to the narrative threads Atlas already builds. Two binding paths:

### Path A — PRECISE: `event.source_url → signal → topic` (the key finding)

An ACLED event's `source` field lists the **actual articles** that document the
event. Atlas has very likely **already ingested some of those same articles** as
`signals_v2` rows (via GDELT / RSS), and each such signal already has a **topic /
thread assignment** (`signal_topic_assignments` / `topic_members`). Therefore:

```
ACLED event ──(source URL)──▶ signals_v2 (match on source_url / canonical URL)
                                   │
                                   └─(existing assignment)─▶ topic / narrative thread
```

This binds a specific event to a specific thread **deterministically**, not by a
fuzzy country+actor guess. It is the same "bind by the underlying article" principle
the unified engine already uses to attach discussion (Lemmy/Bluesky) to topics via
`source_url`. Practically: normalize both sides' URLs (strip query junk, unify
scheme/host), then join ACLED `source` URLs against `signals_v2.source_url`. Where an
event's article is in Atlas, the event inherits that article's topic. Where it is
not, fall to Path B.

### Path B — GEOSPATIAL / ACTOR: lat-lon + typed actor → thread scope

Every ACLED event also carries **precise lat/lon**, `country`/`admin1`, and **named,
typed actors** (`actor1`/`actor2` + `inter*` interaction codes). This gives a second
bind for events whose article Atlas did not ingest:

- **Geo bind:** the event's country / admin1 (and lat-lon proximity) scopes it to
  threads active in that place — a real, coordinate-level anchor GDELT CAMEO cannot
  give, sharper than country-level.
- **Actor bind:** `actor1`/`actor2` match a thread's key subjects/entities
  (people/orgs/groups Atlas already types), tying the event to the thread about
  those actors.

Path B is fuzzier than A but always available (lat-lon + actor are mandatory ACLED
fields), so every event gets at least one binding; A upgrades it to precise when the
article overlaps.

### Why this closes #232

- Threads gain **connected, verified events** with type, actors, fatalities, date,
  and a coordinate — the concrete "what actually happened" spine that GDELT
  country-level counts never provided.
- The bind is **precise where it matters** (shared article → shared topic) and
  **degrades honestly** (geo/actor scope) where the article isn't in-corpus — the
  same honesty discipline as the rest of Atlas.
- ACLED is **displayed reference + a deterministic linking key**, never ML training
  data — keeping the integration on the permitted side of ACLED's terms (see the
  access-request doc's eligibility note).

---

## 4. Rollout steps (once a key is granted)

1. **Register + obtain credentials** (the one human action — see §1 and the
   access-request doc). Set the env/Fly secrets.
2. **First backfill (local, read from ACLED / write to `acled_conflicts_v2`):**
   run `python backend/scripts/ingest_acled.py` with a widened `ACLED_DAYS_BACK`
   for an initial window; confirm rows land and `geo.py` markers switch from GDELT
   fallback to `source: "acled"`.
3. **Schedule:** point the `ingest_loop` ACLED branch at the scaffold (or fold the
   scaffold's OAuth+pagination into `app/services/ingest_acled.py`); rolling ~3-day
   window on the existing cadence.
4. **(Optional schema)** widen `source` → TEXT / add `acled_event_sources` child +
   the extra ACLED fields (`iso`, `tags`, `civilian_targeting`, `disorder_type`) if
   Path A precision or richer display needs them.
5. **Binding (new, small service):** a `bind_acled_events.py` step that runs
   Path A (URL-join ACLED `source` ↔ `signals_v2.source_url` → inherit topic) then
   Path B (geo/actor scope), writing event↔topic links. Kept OUT of the ingest, the
   same separation as discussion-attach (ingest lands rows; binding is downstream).
6. **Attribution:** ensure the ACLED marker/timeline UI + any export carries
   "ACLED, accessed on [DATE]. www.acleddata.com." with filters noted.

---

## 5. Constraints honored

- **Read-only on prod this session:** no writes, no serving changes, no heavy
  compute. Only new files written (scaffold + these two docs). The scaffold does
  nothing without a key.
- **Not a hard dependency:** no key → ingest skips, table empty, map layer hides,
  GDELT fallback serves. Exactly the existing optional-source contract.
- **Terms:** display + deterministic bind, full attribution, no redistribution, no
  ML-training use of ACLED data.
