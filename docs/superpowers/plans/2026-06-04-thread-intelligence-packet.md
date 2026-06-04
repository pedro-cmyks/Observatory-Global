# Thread Intelligence Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach one server-side intelligence packet (country edges, source/social lanes, sentiment timeline, graph signals, related themes, public attention) to thread detail, then keep the visible product shell unified so Narrative Threads and Theme Detail do not behave like separate concepts.

**Architecture:** Extract the aggregation already in `themes.py` into a shared pure `build_thread_packet(rows)`. Thread detail and theme detail both call it (DRY). Thread sample-signals SQL gains `themes`. A best-effort `public_attention` (top GDELT theme → trends/wiki match) is attached, isolated so it can't fail the detail. Frontend correction after review: resolvable Narrative Threads open the existing `ThemeDetail` shell with the thread note embedded at the top; `ThreadFocusPanel` remains only as fallback for unresolved thread ids.

**Tech Stack:** Python 3.12 / FastAPI / asyncpg; React + TypeScript + Vite; vanilla CSS.

**Spec:** `docs/superpowers/specs/2026-06-04-thread-intelligence-packet-design.md`

---

## File Structure

- Create: `backend/app/services/thread_packet.py` — `build_thread_packet(rows)`.
- Create: `backend/tests/test_thread_packet.py` — builder unit tests.
- Modify: `backend/app/services/thread_intelligence.py` — add `themes` to sample SQL; attach `packet` in the three detail paths; `_thread_public_attention` helper.
- Modify: `backend/app/routers/themes.py` — refactor `_dynamic_topic_detail` / `_emergent_cluster_detail` to use the shared builder.
- Create: `backend/tests/test_thread_packet_contract.py` — thread detail returns `packet`.
- Modify: `frontend-v2/src/components/ThreadFocusPanel.tsx` (+ its CSS) — render packet.

---

## Task 1: build_thread_packet builder (TDD)

**Files:**
- Create: `backend/app/services/thread_packet.py`
- Test: `backend/tests/test_thread_packet.py`

The builder generalizes the aggregation in `themes.py` (lines ~315-380). Each input row is an asyncpg Record or dict with keys: `timestamp`, `country_code`, `source_name`, `source_url`, `sentiment`, `headline`, `themes`, `persons`. `source_family` is DERIVED via `classify_source(source_name)` — not a column.

- [ ] **Step 1: Write the failing test** at `backend/tests/test_thread_packet.py`:

```python
from datetime import datetime, timezone
from app.services.thread_packet import build_thread_packet


def _row(**kw):
    base = {"timestamp": datetime(2026, 6, 4, 10, tzinfo=timezone.utc),
            "country_code": "CO", "source_name": "reuters.com",
            "source_url": "http://reuters.com/x", "sentiment": -1.0,
            "headline": "h", "themes": ["PROTEST"], "persons": ["Petro"]}
    base.update(kw)
    return base


def test_empty_input_returns_empty_packet():
    p = build_thread_packet([])
    assert p["countryBreakdown"] == [] and p["topSources"] == []
    assert p["timeline"] == [] and p["graphSignals"] == []
    assert p["lanes"] == {"media": 0, "social": 0, "state": 0, "other": 0}


def test_country_breakdown_groups_and_sorts():
    rows = [_row(country_code="CO"), _row(country_code="CO"), _row(country_code="VE")]
    p = build_thread_packet(rows)
    assert p["countryBreakdown"][0]["code"] == "CO"
    assert p["countryBreakdown"][0]["count"] == 2


def test_top_sources_carry_family():
    p = build_thread_packet([_row(source_name="reddit.com/r/x")])
    assert "family" in p["topSources"][0]


def test_lanes_split_social():
    # reddit -> social lane
    p = build_thread_packet([_row(source_name="reddit.com/r/x")])
    assert p["lanes"]["social"] >= 1


def test_related_themes_excludes_own_topic():
    rows = [_row(themes=["PROTEST", "ECON"]), _row(themes=["PROTEST"])]
    p = build_thread_packet(rows, own_topic="PROTEST")
    themes = {t["theme"] for t in p["relatedThemes"]}
    assert "PROTEST" not in themes and "ECON" in themes


def test_timeline_buckets_by_hour():
    p = build_thread_packet([_row(), _row()])
    assert len(p["timeline"]) == 1 and p["timeline"][0]["count"] == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_packet.py -v`
Expected: FAIL `ModuleNotFoundError`.

- [ ] **Step 3: Implement** `backend/app/services/thread_packet.py`:

```python
"""Shared narrative intelligence packet builder. Aggregates a set of signal
rows (a thread's or topic's sample signals) into the descriptive structures the
reading panels render: country edges, source lanes, timeline, graph, related
themes. Pure function over rows — no DB, no metric weighting."""
from __future__ import annotations

import html
from typing import Any

from app.core.gdelt_taxonomy import classify_source
from app.utils import extract_domain, _is_valid_person

_SOCIAL_FAMILIES = {"reddit", "social", "mastodon"}
_STATE_FAMILIES = {"state"}
_MEDIA_FAMILIES = {"wire", "api", "independent", "ngo"}


def _lane_for(family: str) -> str:
    if family in _SOCIAL_FAMILIES:
        return "social"
    if family in _STATE_FAMILIES:
        return "state"
    if family in _MEDIA_FAMILIES:
        return "media"
    return "other"


def _val(row: Any, key: str):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def build_thread_packet(rows: list, own_topic: str | None = None) -> dict:
    country_counts: dict = {}
    source_counts: dict = {}
    timeline_counts: dict = {}
    person_counts: dict = {}
    theme_counts: dict = {}
    lanes = {"media": 0, "social": 0, "state": 0, "other": 0}

    for r in rows:
        sentiment = float(_val(r, "sentiment") or 0)
        cc = _val(r, "country_code")
        if cc:
            country_counts.setdefault(cc, []).append(sentiment)
        sn = _val(r, "source_name")
        if sn:
            source_counts.setdefault(sn, []).append(sentiment)
            lanes[_lane_for(classify_source(sn))] += 1
        ts = _val(r, "timestamp")
        if ts:
            bucket = ts.replace(minute=0, second=0, microsecond=0)
            timeline_counts.setdefault(bucket, []).append(sentiment)
        for p in (_val(r, "persons") or []):
            person_counts[p] = person_counts.get(p, 0) + 1
        for t in (_val(r, "themes") or []):
            if own_topic and t == own_topic:
                continue
            theme_counts[t] = theme_counts.get(t, 0) + 1

    country_breakdown = [
        {"code": cc, "count": len(vs), "sentiment": sum(vs) / len(vs)}
        for cc, vs in sorted(country_counts.items(), key=lambda x: len(x[1]), reverse=True)
    ][:15]
    top_sources = [
        {"name": extract_domain(sn), "count": len(vs),
         "sentiment": sum(vs) / len(vs), "family": classify_source(sn or "")}
        for sn, vs in sorted(source_counts.items(), key=lambda x: len(x[1]), reverse=True)
    ][:20]
    timeline = [
        {"hour": h.isoformat(), "count": len(vs), "sentiment": sum(vs) / len(vs)}
        for h, vs in sorted(timeline_counts.items())
    ]
    top_persons = [
        {"name": p, "count": c}
        for p, c in sorted(person_counts.items(), key=lambda x: x[1], reverse=True)
        if _is_valid_person(p)
    ][:10]
    related_themes = [
        {"theme": t, "count": c}
        for t, c in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
    ][:10]

    def _sig(r):
        ts = _val(r, "timestamp")
        hl = _val(r, "headline")
        return {
            "timestamp": ts.isoformat() if ts else None,
            "country": _val(r, "country_code"),
            "source": _val(r, "source_name"),
            "url": _val(r, "source_url"),
            "headline": html.unescape(hl) if hl else hl,
            "sentiment": float(_val(r, "sentiment") or 0),
            "otherThemes": (_val(r, "themes") or [])[:5],
            "persons": (_val(r, "persons") or [])[:5],
        }

    signal_rows = [_sig(r) for r in rows]

    return {
        "graphSignals": signal_rows,
        "countryBreakdown": country_breakdown,
        "topSources": top_sources,
        "topPersons": top_persons,
        "timeline": timeline,
        "lanes": lanes,
        "relatedThemes": related_themes,
        "public_attention": None,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_packet.py -v`
Expected: PASS (6).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/thread_packet.py backend/tests/test_thread_packet.py
git commit -m "feat(packet): shared build_thread_packet aggregation builder"
```

---

## Task 2: Add themes to thread sample SQL + attach packet in thread detail

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Test: `backend/tests/test_thread_packet_contract.py`

- [ ] **Step 1: Write the failing contract test** at `backend/tests/test_thread_packet_contract.py`:

```python
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "app" / "services" /
       "thread_intelligence.py").read_text(encoding="utf-8")


def test_sample_sql_selects_themes():
    # the sample-signals SQL must select themes so the packet builder can
    # compute relatedThemes
    assert "themes" in SRC
    assert "_EMERGENT_SAMPLE_SIGNALS_SQL" in SRC


def test_detail_paths_attach_packet():
    assert "build_thread_packet" in SRC
    assert SRC.count('"packet"') >= 1 or "['packet']" in SRC or '"packet"]' in SRC
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_packet_contract.py -v`
Expected: FAIL (`build_thread_packet`/packet not present).

- [ ] **Step 3: Edit `backend/app/services/thread_intelligence.py`**

1. Import at top:
```python
from app.services.thread_packet import build_thread_packet
```

2. Add `themes` to `_EMERGENT_SAMPLE_SIGNALS_SQL` (currently selects `id, headline, snippet, source_name, source_url, country_code, NULL country_name, timestamp, persons, sentiment AS nlp_sentiment, ...`). Add `themes,` to the column list. Do the same for any other sample-signals SELECT feeding a detail path (the atlas thread evidence query and the dynamic-topic sample query) if they don't already select `themes`.

3. In each detail builder that fetches sample rows — `_fetch_dynamic_thread_detail`, `_fetch_emergent_thread_detail`, and the atlas thread detail builder — after the `sample_signals`/evidence rows are fetched, attach the packet to the returned detail dict. The builder needs rows with a `sentiment` key; the sample SQL aliases sentiment as `nlp_sentiment`, so pass a key the builder reads. Build the packet from the raw rows by mapping `nlp_sentiment`→`sentiment` if needed, e.g.:

```python
packet_rows = [
    {**dict(r), "sentiment": r["nlp_sentiment"] if "nlp_sentiment" in r else r["sentiment"]}
    for r in sample_signals
]
detail["packet"] = build_thread_packet(packet_rows, own_topic=<the thread's primary theme or None>)
```

Use `None` for `own_topic` if no single GDELT theme identifies the thread. Insert this in all three detail paths so atlas/emergent/dynamic all return `packet`.

- [ ] **Step 4: Run tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_packet_contract.py tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py -v`
Expected: PASS (contract + no regressions). Also `.venv/bin/python -c "import app.services.thread_intelligence"`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/thread_intelligence.py backend/tests/test_thread_packet_contract.py
git commit -m "feat(packet): attach build_thread_packet to thread detail paths"
```

---

## Task 3: Public attention in the packet (best-effort, isolated)

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`

- [ ] **Step 1: Add `_thread_public_attention` helper**

Add a helper that, given a connection and the packet's `relatedThemes` (GDELT theme codes), picks the top theme and reuses the existing trends + wiki match logic to return `{"trends": [...], "wiki": [...]}` or `None`. The trends/wiki match logic lives in `backend/app/routers/trends.py` (`get_trends_theme_match`) and `backend/app/routers/wiki.py` (`get_wiki_theme_match`), keyed on a GDELT `theme` code. Extract or call their core query logic with the top theme code. Wrap the whole thing in try/except so any failure returns `None` — it must NEVER fail the thread detail:

```python
async def _thread_public_attention(conn, related_themes: list[dict]) -> dict | None:
    if not related_themes:
        return None
    theme = related_themes[0]["theme"]
    try:
        # reuse the same SQL the trends/wiki match endpoints run, keyed on `theme`
        ...
        return {"trends": trends_matches, "wiki": wiki_matches} or None
    except Exception:
        return None
```

If reusing the match logic cleanly is awkward (the handlers are route functions), keep `public_attention` as `None` for this pass and open a follow-up — do NOT block the packet on it. The packet already initializes `public_attention: None`.

- [ ] **Step 2: Wire it in the three detail paths**

After `detail["packet"] = build_thread_packet(...)`:

```python
detail["packet"]["public_attention"] = await _thread_public_attention(conn, detail["packet"]["relatedThemes"])
```

- [ ] **Step 3: Verify import + thread tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_intelligence.py tests/test_thread_packet_contract.py -v && .venv/bin/python -c "import app.services.thread_intelligence"`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/thread_intelligence.py
git commit -m "feat(packet): best-effort public attention (top theme trends/wiki match)"
```

---

## Task 4: DRY — themes.py uses the shared builder

**Files:**
- Modify: `backend/app/routers/themes.py`

- [ ] **Step 1: Refactor the two detail builders**

In `_dynamic_topic_detail` and `_emergent_cluster_detail`, replace the inline aggregation block (the `country_counts`/`source_counts`/`timeline_counts` loop and the `country_breakdown`/`top_sources`/`timeline`/`signal_rows` builders, ~lines 315-380) with:

```python
from app.services.thread_packet import build_thread_packet  # at top of file
...
packet = build_thread_packet(signals, own_topic=None)
```

Then map the packet keys into the existing response so the `ThemeDetail`
contract is unchanged:

```python
    return {
        **base_payload,
        "signalSample": sample,
        "avgSentiment": round(avg_sentiment, 3),
        "signals": packet["graphSignals"],
        "graphSignals": packet["graphSignals"],
        "countryBreakdown": packet["countryBreakdown"],
        "topSources": packet["topSources"],
        "topPersons": packet["topPersons"],
        "timeline": packet["timeline"],
        "warnings": ["emergent_cluster_preview_sample"],
    }
```

Keep `sample` and `avg_sentiment` computed as today (the builder does not return them). Do this for BOTH detail functions.

- [ ] **Step 2: Regression — theme detail contract unchanged**

Run: `cd backend && .venv/bin/python -m pytest tests/test_emergent_router_shape.py -v && .venv/bin/python -c "import app.routers.themes"`
Expected: PASS, no import error. Field names (`graphSignals`, `countryBreakdown`, `topSources`, `topPersons`, `timeline`) must be byte-identical to before.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/themes.py
git commit -m "refactor(packet): theme detail reuses shared build_thread_packet"
```

---

## Task 5: Frontend — ThreadFocusPanel renders the packet

**Files:**
- Modify: `frontend-v2/src/components/ThreadFocusPanel.tsx` (+ its CSS file)

- [ ] **Step 1: Extend the `ThreadDetail` type**

Add a `packet` field to the detail interface:

```tsx
interface ThreadPacket {
  graphSignals?: Array<{ headline: string; country: string | null; source: string; sentiment: number; url?: string }>
  countryBreakdown?: Array<{ code: string; count: number; sentiment: number }>
  topSources?: Array<{ name: string; count: number; sentiment: number; family?: string }>
  topPersons?: Array<{ name: string; count: number }>
  timeline?: Array<{ hour: string; count: number; sentiment: number }>
  lanes?: { media: number; social: number; state: number; other: number }
  relatedThemes?: Array<{ theme: string; count: number }>
  public_attention?: { trends?: unknown[]; wiki?: unknown[] } | null
}
```

and `packet?: ThreadPacket | null` on the thread detail interface.

- [ ] **Step 2: Render packet sections (null-safe, collapse empties)**

In the panel body, add sections that render only when their packet data is non-empty, reusing existing ThemeDetail render patterns:
- Country edges from `packet.countryBreakdown` (code + count + sentiment color), via the existing `resolveCountryName`.
- Source lanes: `packet.lanes` summary chips (media / social / state) + `packet.topSources` grouped/colored by `family`.
- Sentiment timeline: feed `packet.timeline` into the panel's existing timeline chart (the one already used for the thread; reuse the same chart component the file already imports).
- Related: render `packet.relatedThemes` (via `getThemeLabel`) alongside existing `related_threads`.
- Public attention: render `packet.public_attention` trends + wiki when present.

Each section guarded like `{!!detail?.packet?.countryBreakdown?.length && (...)}`.

- [ ] **Step 3: Styles**

Add vanilla CSS (no Tailwind) for the new sections/lane chips in the panel's CSS file, matching existing panel styling tokens (`var(--color-...)`).

- [ ] **Step 4: Build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds (Vite `tsc -b`). If the local Node env hangs, rely on the Vercel build.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/ThreadFocusPanel.tsx frontend-v2/src/components/ThreadFocusPanel.css
git commit -m "feat(packet): render thread intelligence packet in ThreadFocusPanel"
```

---

## Task 6: Deploy + smoke

- [ ] **Step 1: Backend sweep**

Run: `cd backend && .venv/bin/python -m pytest tests/test_thread_packet.py tests/test_thread_packet_contract.py tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py tests/test_emergent_router_shape.py -q`
Expected: PASS.

- [ ] **Step 2: Merge feature branch to v3-intel-layer + deploy API**

```bash
git checkout v3-intel-layer && git merge --no-ff <feature-branch>
bash scripts/deploy-fly-api.sh
curl -s https://atlas-api-pedro.fly.dev/health | python -m json.tool   # status healthy
```

- [ ] **Step 3: Smoke each thread type returns a populated packet**

```bash
curl -s "https://atlas-api-pedro.fly.dev/api/v2/threads?hours=24&limit=5" | python -m json.tool | grep thread_id
# pick a dynamic-topic-*, an emergent-cluster-*, and an atlas thread_id, then for each:
curl -s "https://atlas-api-pedro.fly.dev/api/v2/threads/<id>" | python -m json.tool | grep -E "countryBreakdown|topSources|timeline|lanes|packet"
```
Expected: each returns `packet` with non-empty `countryBreakdown` / `topSources` / `timeline` (subject to sample size).

- [ ] **Step 4: Frontend deploy + browser smoke**

```bash
git push origin v3-intel-layer   # Vercel
```
Open a thread in `ThreadFocusPanel`; confirm country edges, source lanes, timeline, related, (attention if present) render and empty sections collapse.

- [ ] **Step 5: Docs**

```bash
python3 scripts/project_inventory.py
git add docs/state/PROJECT_INVENTORY.md STATUS.md SESSION_LOG.md
git commit -m "docs(packet): log thread intelligence packet shipment + inventory"
git push origin v3-intel-layer
```
(Add STATUS + SESSION_LOG entries first.)

---

## Self-review notes

- **Spec coverage:** shared builder (T1), themes-in-SQL + packet attach across all
  three thread types (T2), public attention isolated/best-effort (T3), themes.py
  DRY refactor (T4), frontend render null-safe (T5), deploy + per-type smoke (T6).
  Sample-size caveat documented; no migration (correct).
- **Type consistency:** `build_thread_packet(rows, own_topic=None)` signature used
  in T1/T2/T4; packet keys (`graphSignals/countryBreakdown/topSources/topPersons/
  timeline/lanes/relatedThemes/public_attention`) identical across builder,
  contract test, themes mapping, and frontend `ThreadPacket` type. `sentiment`
  key normalization (`nlp_sentiment`→`sentiment`) handled in T2 before the builder.
- **Placeholders:** none — builder is full code; wiring points reference exact
  functions/SQL. The one genuinely conditional piece (public_attention internal
  reuse) is explicitly allowed to ship `None` with a follow-up, not left vague.
