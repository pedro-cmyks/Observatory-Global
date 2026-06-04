# Signal Snippet Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist source-provided body text (Reddit selftext, NewsAPI/RSS/NewsData/Mediastack descriptions, ReliefWeb body) into a new `signals_v2.snippet` column and surface it under the headline in thread/theme evidence so Atlas reads as sentences, not only counts.

**Architecture:** Additive nullable column `signals_v2.snippet`. A shared `clean_snippet` helper normalizes (strip, cap 500, empty→None). Six ingests already compute a `snippet`/`selftext` local — wire each into its signal dict + `INSERT INTO signals_v2`. GDELT (`ingest_v2`) stays NULL. Evidence serializers in `thread_intelligence.py` and `themes.py` add `snippet` (their SELECTs add the column); `ThemeDetail` + `ThreadFocusPanel` render it when present.

**Tech Stack:** Python 3.12 / FastAPI / asyncpg / Postgres (Supabase); React + TypeScript + Vite; vanilla CSS.

**Spec:** `docs/superpowers/specs/2026-06-04-signal-snippet-enrichment-design.md`

---

## File Structure

- Create: `backend/migrations/052_signals_v2_snippet.sql` — additive column.
- Create: `backend/app/services/signal_text.py` — `clean_snippet` helper.
- Create: `backend/tests/test_signal_text.py` — helper unit test.
- Create: `backend/tests/test_ingest_snippet_wiring.py` — source-string guardrails that each text ingest INSERT includes `snippet`.
- Modify (ingests, each: dict + INSERT): `ingest_reddit.py`, `ingest_newsapi.py`, `ingest_rss.py`, `ingest_newsdata.py`, `ingest_mediastack.py`, `ingest_reliefweb.py`.
- Modify (backend exposure): `backend/app/services/thread_intelligence.py`, `backend/app/routers/themes.py`.
- Create: `backend/tests/test_snippet_evidence_contract.py` — serializer includes `snippet`.
- Modify (frontend): `frontend-v2/src/components/ThemeDetail.tsx`, `frontend-v2/src/components/ThreadFocusPanel.tsx`.

---

## Task 1: Migration

**Files:**
- Create: `backend/migrations/052_signals_v2_snippet.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration 052: signals_v2.snippet — persist source-provided body text
--
-- Several ingestion sources (Reddit selftext, NewsAPI/RSS/NewsData/Mediastack
-- description, ReliefWeb body) already extract text beyond the headline but it
-- was never persisted. This column captures up to ~500 chars so the reading
-- panels (threads, theme detail) can show real sentences, not only counts.
-- GDELT brings no body text, so GDELT signals leave this NULL. Additive,
-- nullable, no backfill.

ALTER TABLE signals_v2 ADD COLUMN IF NOT EXISTS snippet TEXT;
```

- [ ] **Step 2: Apply via Supabase MCP**

Load schema: ToolSearch `select:mcp__supabase__apply_migration,mcp__supabase__execute_sql`. Apply with `apply_migration` name `052_signals_v2_snippet`. Verify:

```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'signals_v2' AND column_name = 'snippet';
```
Expected: one row `snippet | text`.

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/052_signals_v2_snippet.sql
git commit -m "feat(snippet): add signals_v2.snippet column (migration 052)"
```

---

## Task 2: clean_snippet helper (TDD)

**Files:**
- Create: `backend/app/services/signal_text.py`
- Test: `backend/tests/test_signal_text.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_signal_text.py
from app.services.signal_text import clean_snippet


def test_strips_whitespace():
    assert clean_snippet("  hello  ") == "hello"


def test_caps_at_500():
    out = clean_snippet("a" * 800)
    assert out is not None and len(out) == 500


def test_empty_to_none():
    assert clean_snippet("") is None
    assert clean_snippet("   ") is None


def test_none_to_none():
    assert clean_snippet(None) is None


def test_normal_passthrough():
    assert clean_snippet("Russia warns on the Baltic.") == "Russia warns on the Baltic."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_signal_text.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'app.services.signal_text'`.

- [ ] **Step 3: Implement**

```python
# backend/app/services/signal_text.py
"""Shared normalization for source-provided body text persisted into
signals_v2.snippet. Strip, cap to a bounded length, and coerce empty to None
so the column stores either real text or NULL (never '')."""
from __future__ import annotations

_MAX_SNIPPET_LEN = 500


def clean_snippet(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    return cleaned[:_MAX_SNIPPET_LEN]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_signal_text.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/signal_text.py backend/tests/test_signal_text.py
git commit -m "feat(snippet): clean_snippet helper (strip/cap/empty-to-null)"
```

---

## Task 3: Wire snippet into the six text ingests

All six ingests share an identical `INSERT INTO signals_v2` shape: 21 columns
(`timestamp ... signal_class`), placeholders `$1..$21`, args passed from a signal
dict `s` (e.g. `s["timestamp"], s["country_code"], ...`). Each already computes a
local snippet value. Wire each so the snippet lands in the dict and the INSERT.

Per-ingest local snippet variable (already present in the file):

| File | Local var | Notes |
|------|-----------|-------|
| `ingest_reddit.py` | `selftext` | already `[:300]` |
| `ingest_newsapi.py` | `snippet` | already `[:500]` |
| `ingest_rss.py` | `snippet` | already `[:500]` |
| `ingest_newsdata.py` | `snippet` | already `[:500]` |
| `ingest_mediastack.py` | `snippet` | already `[:500]` |
| `ingest_reliefweb.py` | `snippet` | already `[:500]` |

**Files:**
- Modify: all six `backend/app/services/ingest_*.py` above
- Test: `backend/tests/test_ingest_snippet_wiring.py`

- [ ] **Step 1: Write the failing source-guardrail test**

```python
# backend/tests/test_ingest_snippet_wiring.py
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"
TEXT_INGESTS = [
    "ingest_reddit.py",
    "ingest_newsapi.py",
    "ingest_rss.py",
    "ingest_newsdata.py",
    "ingest_mediastack.py",
    "ingest_reliefweb.py",
]


def test_each_text_ingest_inserts_snippet():
    for name in TEXT_INGESTS:
        src = (SERVICES / name).read_text(encoding="utf-8")
        assert "snippet" in src, f"{name} missing snippet"
        # snippet must be in the INSERT column list and carried as a 22nd value
        assert "signal_class,\n" in src or "signal_class," in src
        assert "$22" in src, f"{name} INSERT not extended to $22"


def test_gdelt_ingest_does_not_persist_snippet():
    # ingest_v2 (GDELT) brings no body text. Its INSERT already has its own
    # 22-column set (incl. source_origin_country); it must NOT reference a
    # snippet column, leaving snippet NULL by omission.
    src = (SERVICES / "ingest_v2.py").read_text(encoding="utf-8")
    assert "snippet" not in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ingest_snippet_wiring.py -v`
Expected: FAIL (no `$22` / no snippet in the ingests yet).

- [ ] **Step 3: Edit each ingest (same 3 changes per file)**

For EACH of the six files, find the signal dict construction and the
`INSERT INTO signals_v2 (...) VALUES ($1..$21)` block, then:

1. Import the helper at the top of the file (with the other `from app...` imports):

```python
from app.services.signal_text import clean_snippet
```

2. Add the snippet to the signal dict where the dict `s` is built. Use the
   per-file local var from the table above. Example for `ingest_newsapi.py`,
   `ingest_rss.py`, `ingest_newsdata.py`, `ingest_mediastack.py`,
   `ingest_reliefweb.py` (local var is `snippet`):

```python
        "snippet": clean_snippet(snippet),
```

   For `ingest_reddit.py` the local var is `selftext`:

```python
        "snippet": clean_snippet(selftext),
```

3. Extend the INSERT: add `snippet` to the column list, `$22` to the VALUES, and
   `s["snippet"]` to the args tuple. The column block becomes:

```python
                        source_family, source_lang, geo_confidence, attribution_method, is_state_media,
                        signal_class, snippet
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                            $16,$17,$18,$19,$20,$21,$22)
```

   and add `s["snippet"]` as the final argument after the existing
   `s["signal_class"]` argument. (Indentation varies per file — match the file's
   existing indentation. `ingest_reliefweb.py` uses `ON CONFLICT ... DO UPDATE`;
   leave its UPDATE branch as-is — snippet is only set on insert.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ingest_snippet_wiring.py -v`
Expected: PASS.

- [ ] **Step 5: Verify each ingest imports cleanly**

Run: `cd backend && python -c "import app.services.ingest_reddit, app.services.ingest_newsapi, app.services.ingest_rss, app.services.ingest_newsdata, app.services.ingest_mediastack, app.services.ingest_reliefweb"`
Expected: no ImportError / SyntaxError.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ingest_reddit.py backend/app/services/ingest_newsapi.py backend/app/services/ingest_rss.py backend/app/services/ingest_newsdata.py backend/app/services/ingest_mediastack.py backend/app/services/ingest_reliefweb.py backend/tests/test_ingest_snippet_wiring.py
git commit -m "feat(snippet): persist source body text into signals_v2.snippet across ingests"
```

---

## Task 4: Expose snippet in thread evidence

**Files:**
- Modify: `backend/app/services/thread_intelligence.py`
- Test: `backend/tests/test_snippet_evidence_contract.py`

- [ ] **Step 1: Write the failing contract test**

```python
# backend/tests/test_snippet_evidence_contract.py
from app.services import thread_intelligence as ti


def test_serialize_evidence_includes_snippet():
    row = {
        "id": 1, "headline": "Russia warns on the Baltic", "source_name": "Reuters",
        "source_url": "http://x", "country_code": "RU", "country_name": "Russia",
        "timestamp": None, "nlp_sentiment": None, "confidence": None,
        "syndication_count": 1, "snippet": "Moscow said it would respond.",
    }
    out = ti._serialize_evidence(row)
    assert out["snippet"] == "Moscow said it would respond."


def test_serialize_evidence_snippet_nullsafe():
    row = {"id": 2, "headline": "h", "source_name": None, "source_url": None,
           "country_code": None, "country_name": None, "timestamp": None,
           "nlp_sentiment": None, "confidence": None, "syndication_count": 1}
    out = ti._serialize_evidence(row)
    assert out["snippet"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_snippet_evidence_contract.py -v`
Expected: FAIL `KeyError`/`AssertionError` (snippet not in serialized dict).

- [ ] **Step 3: Add snippet to `_serialize_evidence`**

In `backend/app/services/thread_intelligence.py`, in `_serialize_evidence`
(around line 517), add to the returned dict (after the `"headline": headline,`
line):

```python
        "snippet": _record_get(row, "snippet"),
```

Then add `snippet` to the evidence SELECT column lists so the row carries it.
There are evidence SELECTs in this module (e.g. `_EMERGENT_SAMPLE_SIGNALS_SQL`
near line 661, the dynamic-topic sample SQL near line 675, and the atlas thread
evidence query near lines 43 and 280). For each `SELECT ... FROM signals_v2`
(aliased `s` where applicable) that feeds `_serialize_evidence`, add `snippet`
(or `s.snippet`) to its column list. Leave non-signals SELECTs untouched.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_snippet_evidence_contract.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Verify import + thread tests still pass**

Run: `cd backend && python -m pytest tests/test_thread_intelligence.py tests/test_threads_emergent_augment_shape.py -v`
Expected: PASS (no contract regressions).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/thread_intelligence.py backend/tests/test_snippet_evidence_contract.py
git commit -m "feat(snippet): expose snippet in thread evidence serialization"
```

---

## Task 5: Expose snippet in theme/topic detail evidence

**Files:**
- Modify: `backend/app/routers/themes.py`

- [ ] **Step 1: Add snippet to the theme headlines fetch + serialization**

In `backend/app/routers/themes.py`:

1. The recent-headlines fetch (around line 98) selects `headline` among other
   columns. Add `snippet` to that SELECT column list.
2. The serialized headline dict (around line 175-182, `"headline": r['headline']`)
   — add:

```python
                    "snippet": r["snippet"] if "snippet" in r else None,
```

3. The emergent/dynamic cluster detail SELECT (around line 304,
   `s.sentiment, s.headline, s.themes, s.persons`) — add `s.snippet`. Its
   serialized row (around line 363, `"headline": html.unescape(...)`) — add:

```python
            "snippet": r["snippet"] if r["snippet"] else None,
```

- [ ] **Step 2: Verify theme tests + import**

Run: `cd backend && python -m pytest tests/test_emergent_router_shape.py -v && python -c "import app.routers.themes"`
Expected: PASS, no import error.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/themes.py
git commit -m "feat(snippet): expose snippet in theme/topic detail evidence"
```

---

## Task 6: Render snippet in the reading panels

**Files:**
- Modify: `frontend-v2/src/components/ThreadFocusPanel.tsx`
- Modify: `frontend-v2/src/components/ThemeDetail.tsx`

- [ ] **Step 1: ThreadFocusPanel — render snippet under each evidence headline**

In `frontend-v2/src/components/ThreadFocusPanel.tsx`, where each evidence sample
renders its `headline`, add directly below the headline element:

```tsx
{ev.snippet && (
  <p className="evidence-snippet">{ev.snippet}</p>
)}
```

Use the actual evidence variable name in the file (e.g. `ev`, `sample`,
`s`) — match the existing map callback. Add `snippet?: string | null` to the
evidence TypeScript type/interface used there so it typechecks.

- [ ] **Step 2: ThemeDetail — render snippet under each headline**

In `frontend-v2/src/components/ThemeDetail.tsx`, where each headline row renders,
add below the headline:

```tsx
{h.snippet && (
  <p className="theme-evidence-snippet">{h.snippet}</p>
)}
```

Match the actual headline item variable and add `snippet?: string | null` to its
type.

- [ ] **Step 3: Add minimal styles**

In the CSS the two components use (vanilla CSS — no Tailwind), add a muted,
2-line-clamped style. Append to `ThreadFocusPanel`'s and `ThemeDetail`'s CSS
files (or their existing style blocks):

```css
.evidence-snippet,
.theme-evidence-snippet {
    margin: 2px 0 0;
    font-size: 12px;
    line-height: 1.45;
    color: var(--color-text-muted, #94a3b8);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
```

- [ ] **Step 4: Build**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds (Vite `tsc -b`). If the local Node env hangs (known
issue, see STATUS.md), rely on the Vercel build.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/ThreadFocusPanel.tsx frontend-v2/src/components/ThemeDetail.tsx
git commit -m "feat(snippet): render evidence snippet under headlines in reading panels"
```

---

## Task 7: Deploy + smoke

**Files:** none (verification + deploy)

- [ ] **Step 1: Full backend test sweep**

Run: `cd backend && python -m pytest tests/test_signal_text.py tests/test_ingest_snippet_wiring.py tests/test_snippet_evidence_contract.py tests/test_thread_intelligence.py tests/test_emergent_router_shape.py -v`
Expected: PASS.

- [ ] **Step 2: Deploy API + ingestion (this ships the ingests)**

Per `fly.toml`, the `app` process group runs **API + ingestion** (the
`nlp_worker` group is NLP enrichment only). So `deploy-fly-api.sh` deploys both
the evidence-serialization changes AND the ingest snippet wiring. No separate
worker deploy is needed for snippet to start being written.

Run: `bash scripts/deploy-fly-api.sh`
Then: `curl -s https://atlas-api-pedro.fly.dev/health | python -m json.tool` → `"status": "healthy"`.

- [ ] **Step 3: Smoke — new signals carry snippet**

Wait for one ingest cycle, then via Supabase MCP `execute_sql`:

```sql
SELECT source_family, COUNT(*) FILTER (WHERE snippet IS NOT NULL) AS with_snippet,
       COUNT(*) AS total
FROM signals_v2
WHERE created_at > NOW() - INTERVAL '30 minutes'
GROUP BY source_family ORDER BY total DESC;
```
Expected: non-GDELT families (reddit/rss/newsapi/etc.) show `with_snippet > 0`;
GDELT stays 0 (NULL).

- [ ] **Step 4: Smoke — evidence returns snippet**

```bash
curl -s "https://atlas-api-pedro.fly.dev/api/v2/threads?hours=24&limit=1"
# take a thread_id, then:
curl -s "https://atlas-api-pedro.fly.dev/api/v2/threads/<thread_id>" | python -m json.tool | grep -i snippet
```
Expected: evidence samples include a `snippet` key (value may be null for older
or GDELT-only rows).

- [ ] **Step 5: Frontend deploy + docs**

```bash
git push origin v3-intel-layer   # Vercel auto-deploys frontend
python3 scripts/project_inventory.py
git add docs/state/PROJECT_INVENTORY.md STATUS.md SESSION_LOG.md
git commit -m "docs(snippet): log snippet enrichment shipment + regenerate inventory"
git push origin v3-intel-layer
```
(Add a STATUS.md handoff entry + SESSION_LOG.md entry before committing.)

---

## Self-review notes

- **Spec coverage:** migration (T1), clean_snippet (T2), 6-ingest wiring with
  GDELT NULL (T3), thread evidence exposure (T4), theme evidence exposure (T5),
  frontend render with null-omit (T6), deploy incl. **worker** + smoke (T7). No
  backfill (correctly absent). Out-of-scope items (F2/F4/F5/F1) have no tasks.
- **Type consistency:** `clean_snippet` defined T2, used T3; `snippet` key
  carried from ingest INSERT → SELECT → `_serialize_evidence`/theme serializer →
  frontend `snippet?: string | null`. 500-cap consistent (helper + spec).
- **Placeholders:** none — every step has concrete SQL/code/commands. The only
  per-file variance (indentation, exact dict location, evidence var name) is
  called out explicitly for the implementer to match.
