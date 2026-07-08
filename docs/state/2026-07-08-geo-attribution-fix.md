# Geo-attribution fix — subject-country over spurious GKG locations (#238/#150)

**2026-07-08.** Signals were tagged the WRONG subject country, corrupting the
country buckets, the map heat, and thread↔place relations. Evidence: the LatAm
dossier's touched-countries came back `PE 20 · PS 15 · ES 12 · MX 9 · CO 9` —
Palestine (PS) and Spain outranking Colombia in a Colombia/Peru/Argentina
investigation.

## Diagnosis (real data, prod DB)

### 1. `espriella` (Abelardo de la Espriella, Colombian politician), 537 signals
The already-merged #238 subject-geography selection is working here:

| country_code | count | avg geo_conf |
|---|---|---|
| **CO** | **513 (95.5%)** | 0.84 |
| VE | 6 | 0.78 |
| ES / AR | 3 / 3 | 0.85 |
| rest (FR/US/BR/IL/MX/PE/…) | ~12 scattered | — |

So espriella is **not** the problem — the prominence pick already lands it on CO.

### 2. The PS flood — root cause found
GDELT `signals_v2`, `country_code='PS'`, `source_family='gdelt'`, 7d window
(the whole hot table — older rows are pruned):

- **522 rows total; 352 (67%) are keyword-negative** (no
  palestin/gaza/hamas/israel/… token) = the mistag class.
- Cause: **"Belén"** (a Peru district in Loreto + a common first name),
  **"Belém"** (the major Brazilian city in Pará), and **"Bethlehem, PA"**
  (USA) all resolve to **Bethlehem, West Bank** in GDELT's gazetteer →
  **FIPS `WE` → ISO `PS`**. A Peruvian *farándula* story (Austin Palao, Willax
  Noticias), a Brazilian city-hall notice, or a Pennsylvania council story gets
  stamped onto Palestine.

Why the merged #238 override didn't catch them (352 keyword-negative rows):

| blocker | count | reason |
|---|---|---|
| empty `source_origin_country` | 221 (65%) | outlet-origin override has no fallback country when the URL doesn't resolve |
| `max_count ≥ 2` | 74 (22%) | repeated "Belém" tokens give PS count ≥ 2 → the `max_count==1` scatter guard blocks the override |
| English feed | 39 (12%) | override skips English by design; "Bethlehem, PA" is English |

RSS-path PS signals (geo_conf 0.5–0.6) were checked and are **genuinely** about
Gaza/West Bank — the flood is GDELT-only, so the fix is GDELT-only.

## Fix — ambiguous-geo demotion (`ingest_v2._select_primary_country`)

Extends the sound #238 base (prominence + outlet-override, both kept). New
lever, precision-first, damp-not-break, reversible:

> When the prominence winner is an **ambiguous-geo** country (`PS` —
> Bethlehem/Gaza colliding with Belén/Belém) **and** the article gives **no
> Palestine corroboration** (headline + GDELT themes carry no
> palestin/gaza/israel/… token, incl. Arabic) **and** the same article geocodes
> a **real non-PS subject**, reassign to that non-PS subject:
> - a **repeated** (count ≥ 2) alternative is trusted → `geo_confidence 0.6`, method `ambiguous_geo_demote`;
> - a **single-mention** alternative is only taken when the outlet-origin override won't fire → `geo_confidence 0.4`, method `ambiguous_geo_demote_weak` (damped).
>
> Genuine Palestine coverage names its subject (**corroborated → untouched**);
> a PS-only article with no alternative is **left as-is** (no over-correction
> without evidence).

Corroboration text = `headline + V2ENHANCEDTHEMES`, passed into the selector.
Kill-switch: `ATLAS_GEO_AMBIGUOUS_DEMOTE=off` (restores prior behaviour). The
existing `ATLAS_GEO_SUBJECT_GATE=off` still restores the naive first-pick.

Also confirmed already present in current `v3-intel-layer` (from the earlier
#238 merge `8a067d45` + sweet-bose extras): `WE→PS`, `GZ→PS` FIPS mappings and
the national-ccTLD expansion of `_extract_source_country`.

## Verification

- `pytest tests/test_geo_subject_selection.py` — **17 passed** (10 original +
  7 new labeled cases: Belém→BR, Peru farándula→PE, Bethlehem-PA→US, genuine
  Gaza→PS, themes-corroborated→PS, PS-only-kept, kill-switch).
- `pytest tests/test_geo_tagging_native.py tests/test_person_hygiene.py` — green
  (155 passed across the three suites). Import check green.
- **End-to-end** through `parse_gkg_row`:
  - Brazilian "Belém" row → **BR** (0.6), not PS ✓
  - "Hamas disuelve gobierno en Gaza" → **PS** (0.85) kept ✓
  - "De la Espriella … en Colombia" → **CO** ✓

Pre-existing broken collector `tests/test_llm_annotator.py` (missing `anthropic`
pkg, `sys.exit(2)` at import — documented excluded file) is unrelated.

## Post-deploy prod verification (2026-07-08, Fly)

First ~12.3k GDELT rows after deploy: demotion **fired** — e.g. *"El Palau de la
Música de Valencia acoge…"* reassigned **PS → ES** at `geo_confidence 0.6` (the
0.6/0.4 markers are impossible pre-deploy, confirming the new path is live). The
5 residual keyword-negative PS rows turned out to be **genuine** Palestine —
HTML-entity-encoded Arabic headlines (`&#x641;&#x644;&#x633;…` = فلسطين,
حماس) — correctly kept (PS-only, no alternative). This also means the diagnostic
"67% keyword-negative" **over-counted** the true mistag rate: some were
encoded-Arabic genuine Palestine the ASCII keyword regex couldn't see.

**Hardening** (follow-up commit `0fb543c4`): `parse_gkg_row` now `html.unescape`s
the corroboration text so an encoded non-Latin Palestine headline with a
co-geocoded neighbour is protected on the headline path too (previously only the
ASCII GDELT-themes path caught it). +1 test → **120 geo tests green**.

## Deploy / backfill

- **Ingest-side, runs on Fly `app`** (`ingest_loop.py` → `parse_gkg_row`, not an
  M1 cron) → deploy with `./scripts/deploy-fly-api.sh`. No M1 runner sync
  needed (GDELT ingest is not on the M1).
- **Forward-fixing**: corrects NEW signals from the next ingest cycles onward.
- **Backfill: NOT worth a full pass.** The hot table only holds ~7d, so the 352
  mis-tagged rows **self-heal within a week** as they age out. Of them, only
  ~56 have a confidently-wrong non-PS/non-`IL` known outlet (271 have no
  resolvable origin — unfixable from stored data since raw
  V2ENHANCEDLOCATIONS isn't persisted; 25 are `IL`-origin = likely genuine
  West Bank coverage). A narrow, reversible outlet-floor backfill is available
  if the dossier needs immediate cleaning, but given self-heal + the small,
  partly-ambiguous population it isn't recommended.

  Optional narrow backfill (save pre-image first, reversible):
  ```sql
  -- dump revert set, then:
  UPDATE signals_v2 SET country_code = source_origin_country, geo_confidence = 0.35
  WHERE country_code='PS' AND source_family='gdelt'
    AND source_origin_country IS NOT NULL AND source_origin_country NOT IN ('','PS','IL')
    AND source_lang <> 'en'
    AND headline !~* '(palestin|gaza|hamas|israel|cisjord|ramallah|rafah|jenin|nablus|hebron|west bank|بيت لحم|فلسط|غزة)';
  ```

## Files
- `backend/app/services/ingest_v2.py` — module `import re`; `_GEO_AMBIGUOUS_*`
  constants + `_PALESTINE_CORROBORATION`; demotion block in
  `_select_primary_country`; `corroboration_text` wired from `parse_gkg_row`.
- `backend/tests/test_geo_subject_selection.py` — +7 labeled tests.
