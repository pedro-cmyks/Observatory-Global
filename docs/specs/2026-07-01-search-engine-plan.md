# Search Engine Plan — the hard core (Pedro, 2026-07-01)

Status: EXECUTING (P1 shipped same-day). Owner: single track.
Source: L0-L3 deep review (#245) + Pedro's framing: *"lo más duro es el
buscador… hacerle queries a nuestros propios datos… quiero ver quién está
hablando de qué está pasando en Burkina Faso"*. Search must let a user arrive
WITH a question and reach Atlas's answer — not just browse.

**Diagnosis (measured):** `/api/v2/search/unified` queries taxonomy, concepts,
regions, wiki attention, raw signals — but **never `dynamic_topics`**. The
LIVING THREADS (the product's own processed answer) are invisible to search.
Searching "Lebanon Israel agreement" while "Lebanon-Israel Framework
Agreement" is a top-10 served thread returns nothing thread-shaped. The
research plan (L3) DOES find them — the gap is the quick-search surface, not
recall.

## Phases

- **P1 — live threads in unified search (SHIPPED 2026-07-01).** Backend:
  `live_threads` segment — token-AND ILIKE over active `dynamic_topics`
  labels (fallback token-ANY marked `match:'partial'`), optional country scope
  via member top_country_codes, umbrellas included. Frontend: "Live Threads"
  section FIRST in the dropdown → `onThemeSelect('dynamic-topic-<id>')` (the
  existing contract). Cache key v8→v9.
- **P2 — country-scoped search (the Burkina Faso case). MOSTLY SHIPPED
  2026-07-01** (`44b7580e`+`4116f038`): +129 country aliases (full UN coverage,
  en + principal es forms — the base ~70 missed "burkina faso", Pedro's literal
  example); pure-country queries surface the country's live threads inline,
  scoped to PRIMARY country (compound queries keep the looser ANY scope);
  alias display-name wins over bare-code DB entries. Prod: 'burkina faso' →
  (BF, Burkina Faso) + 'Burkina Faso Cuts Ties With France'.
  **REMAINING:** search WITHIN a focused country — when FocusContext has a
  country, the SearchBar passes it and labels the scope ("in Burkina Faso ✕").
- **P3 — semantic on-submit.** Lexical misses ≠ no answer: on Enter with zero
  thread hits, embed the query (existing embed service, ~0.5s warm) → cosine
  vs active topic centroids → serve above-threshold as `semantic_threads`
  (labeled, never silently mixed with lexical). Degrade to the existing
  "Start investigation" path. Reuses `research_semantic.py` machinery — this
  is a projection of the L3 lane into quick search, not new ML.
- **P4 — measure + order.** `search_result_click` telemetry (which section
  wins per query class) + result ordering informed by it. Search is T5.1's
  natural funnel entry; today we have zero search telemetry.

## L3 track (the other "never worked deeply" — sequenced AFTER P2)
The review verdict: L3 plumbing is SOUND (ledger reconciles, scores real).
Depth items, in order: (1) T1.1 who-says-what in the dossier (PinSnapshot
evidence → framed source rows; DossierView sections populate); (2) per-pin
notes + pin-snapshot exercise under real use; (3) investigation history UX
(multiple investigations exist — sidebar polish + rename/delete); (4) T1.2
evidence-role quality bound to Paper 1 (the Phase-4 benchmark). P3 semantic
above also lifts L3 (same lane).

## Review-actions mapping (Pedro approved the spec)
Order: P1 search (done) → #244 landing seam (S) → #246 damp-by-category (S)
→ P2 → #247 design batch A (contrast) → P3 → #247 B/C → #248 noise classes →
L3 depth track. ACLED (#46): explicitly NOT a blocker (Pedro 2026-07-01) —
alternates (USGS/GDACS/CAMEO) already carry the event layer; discard if never
granted.

## P4 SHIPPED (2026-07-02)
Events: `search_query` (q_len, country_scoped, per-segment counts, zero) on
each settled query; `search_result_click` (segment, q_len) on live_thread/
theme/person selects. Verified end-to-end (preview → 202 → prod row:
'burkina faso' → live_threads:1, themes:4, zero:false).

**Weekly reading (run with the telemetry read, T5.1 discipline):**
```sql
-- Do searchers FIND? zero-rate + click-through by segment, last 7d
SELECT
  count(*) FILTER (WHERE event='search_query')                          AS queries,
  count(*) FILTER (WHERE event='search_query'
                     AND (props->>'zero')::bool)                        AS zero_result,
  count(*) FILTER (WHERE event='search_result_click')                   AS clicks,
  mode() WITHIN GROUP (ORDER BY props->>'segment')
    FILTER (WHERE event='search_result_click')                          AS top_segment
FROM telemetry_events
WHERE event LIKE 'search%' AND created_at > NOW() - INTERVAL '7 days';
-- zero_result queries = the recall gap list; pull their q_len distribution
-- before touching ranking.
```
Remaining: P3 semantic-on-submit (prompt in docs/prompts/).
