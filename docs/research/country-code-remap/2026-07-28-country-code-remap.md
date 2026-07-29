# Country-code remap backfill — verification, execution, blast radius

**Date:** 2026-07-28 · **Fix commit:** `b7ab7def` (branch `eclipse-dramatic-moment`,
**not yet merged/deployed** at run time) · **Script:**
`backend/scripts/backfill_country_code_remap.py` · **Ledgers:** `ledgers/` (this dir)
· **Read-time rules for archive-derived data:** `country-code-corrections-v1.json`

## What happened

`country_codes.py` mis-translated 5 FIPS entries and lacked ~89 divergent codes
since inception (2025-12-04, `b0ac1a56`), so GDELT-lane rows landed under
wrong-but-plausible ISO codes (Lebanon under LS=Lesotho, Serbia under raw GEC RB,
Paraguay under PA=Panama…). `b7ab7def` fixed the map; this pass fixed the stored
rows that are mechanically recoverable, and documented everything that is not.

## Verification before writing (per task requirement)

Method: 20 random headlines per bucket (8 for the low-volume extras), GDELT lane
only, plus lane/attribution breakdowns and a programmatic diff of the old map vs
the fixed map to enumerate ALL candidate buckets — not just the 12 from the 7d
measurement.

Five discoveries changed the plan; each would have corrupted data if skipped:

1. **Lane split.** Buckets are only wrong in the GDELT lane
   (`source_family='gdelt'`). The MN bucket holds 182 `rss_feed` rows (ikon.mn —
   genuine **Mongolia**) and PA holds 431 (tvn-2.com — genuine **Panama**).
   A whole-bucket remap would have shredded them. Scope: gdelt lane only.
2. **The outlet-origin override path writes ISO codes inside the GDELT lane.**
   `ingest_v2._select_primary_country` falls back to the outlet's home country
   (ccTLD/domain, ISO space) for non-English single-mention scatter, at
   `geo_confidence = 0.35` exactly. The 82 conf-0.35 rows in the PA bucket are
   genuine Panama (.pa outlets); the whole CR bucket (9 rows) is genuine Costa
   Rica (.cr outlets). Scope: `geo_confidence != 0.35`; CR bucket dropped.
3. **The map-diff surfaced 38 more pure buckets** (GG=Georgia 501 rows,
   AN=Andorra 185, RQ=Puerto Rico 160, BH=Belize 158, TI=Tajikistan 146 … down
   to SB=St-Pierre 1). All sampled; 36 confirmed and included. The naive diff
   also mislabels PL/CN/GB/ZA as pure — identity-FIPS feeders (FIPS PL = Poland
   feeds bucket PL) had to be added by hand; that correction is what keeps the
   contaminated list honest.
4. **TK bucket excluded:** 24 rows GDELT-geocoded (0.85 + coordinates) whose
   content is **Turkey** — a GDELT geocoder pathology, not our translation bug.
   Neither TK (Tokelau) nor TC (Turks & Caicos) is honest; left untouched.
5. **LS bucket split:** FIPS LS = Liechtenstein passed through into the Lebanon
   bucket. 5 rows match /liechtenstein|vaduz/i (hand-verified: Vaduz police
   blotter, Liechtenstein heatwave…) → remapped to **LI**; the other 1,870 → LB.
   Residual risk (a keyword-less Liechtenstein row riding to LB) accepted at
   ~375:1 volume odds, documented here.

Bucket verdicts (samples on file in the session transcript):

| Bucket → target | 7d rows (gdelt) | Verdict |
|---|---|---|
| LS→LB (+5→LI) | 1,875 | Lebanon (incl. "Cracker Barrel"-class Lebanon-Tennessee GDELT geocodes — faithful to GDELT's stated country) |
| RB→RS | 1,914 | Serbia (incl. Republika-Srpska-entity stories GDELT codes as Serbia) |
| KV→XK | 1,443 | Kosovo |
| PM→PA | 595 | Panama (incl. Panama-City-FL geocode noise) |
| PA→PY | 505 | Paraguay (after excluding 82 override rows = real Panama) |
| GG→GE | 501 | Georgia the country |
| CS→CR | 279 | Costa Rica (incl. Malcolm-Jamal-Warner syndication GDELT coded to CR) |
| MG→MN / MN→MC / MC→MO | 237/199/189 | Mongolia / Monaco / Macau |
| AN, RQ, BH, TI, NS, AY, GJ, GK, BP, TX, VQ, CJ, GQ, TT, MF, ST, AC, TP, MB, NH, CW, VT, MH, AA, AQ, RM, VI, FP, WI, EK, AV, CQ, WQ, FG, TL, RN, SB, GA, OD, PP | 1–185 each | all confirmed (Andorra, Puerto Rico, Belize, Tajikistan, Suriname, Antarctica, Grenada, Guernsey, Solomon Is., Turkmenistan, USVI, Cayman, Guam, Timor-Leste, Mayotte, St Lucia, Antigua, São Tomé, Martinique, Vanuatu, Cook Is., Vatican, Montserrat, Aruba, American Samoa, Marshall Is., BVI, Fr. Polynesia, W. Sahara, Eq. Guinea, Anguilla, N. Mariana, Wake, Fr. Guiana, Tokelau, St-Martin, St-Pierre, Gambia, South Sudan, PNG) |

A caveat that holds for every bucket: the remap restores **GDELT's stated
country**, not per-row geographic truth. GDELT gazetteer noise rides along
unchanged (Bathurst NSW → Banjul-né-Bathurst Gambia, "Montserrat" the Catalan
mountain → Montserrat island, Marshalls-the-retailer → Marshall Islands). That
noise existed before and after; it is upstream of the translation layer.

## Task 4 — OS and YI identified

- **OS (571 rows/7d): GDELT GEC "Oceans" pseudo-code.** Samples are ALL bodies
  of water: Caspian-war, Black Sea, Baltic wreck, Adriatic storms, Odesa port.
  No ISO equivalent exists; correctly left unmapped. (Product follow-up worth
  considering: exclude OS from country surfaces explicitly.)
- **YI (30 rows/7d): GEC Serbia-and-Montenegro** (defunct 2006). Content is
  pan-Yugoslav retrospective (Olivera Katarina obituaries, Bosnia war-crimes
  probes, Yugonostalgia). No honest successor mapping; left unmapped.

## Task 2 — window decision

- **Hot `signals_v2` (~7d retention): mutate**, ledgered and reversible. Done.
- **External archive (/Volumes/Ext/Atlas gzip): never mutate.** It is the
  immutable source of truth; a re-ETL would resurrect wrong codes into any
  "corrected" derived table anyway. Instead:
  `country-code-corrections-v1.json` is the machine-readable correction layer
  archive READERS and historical ETLs must apply (single-hop remap + conf-0.35
  exclusion + LS split + contaminated-bucket list). Wiring it into
  `historical_sync.py` / archive readers is a follow-up chip.
- **Cutoff invariant (critical):** the fix is NOT yet deployed; wrong codes keep
  flowing. The script requires `--max-created-at` and every run must keep it at
  or before the fix's deploy moment, because the NEW map legitimately emits
  several bucket codes for other countries (post-fix Lesotho=LS, Guernsey→GG,
  Monaco→MC, Costa Rica→CR). After `b7ab7def` deploys, run ONE final sweep with
  the cutoff set to the deploy timestamp; then the job is closed.

## Task 3 — execution

Design points that earned their keep:

- **Id-keyed, single-hop, ledger-excluded.** Chains (BP→SB→PM→PA→PY,
  MG→MN→MC→MO, GK→GG→GE, AY→AQ→AS…) make a code-keyed re-run double-hop
  previously fixed rows; the committed ledgers in `ledgers/` are the exclusion
  set that makes re-runs idempotent. Frozen by
  `backend/tests/test_backfill_country_code_remap.py` (9 tests).
- **Guarded, skip-locked, chunked.** signals_v2 is hot (NLP fleet + ingest hold
  row locks in long batch transactions — the first attempt sat >300 s on a
  19-row UPDATE) and the DB's storage was IO-crawling during the run (measured
  ~0.5 s/row: country_code is in 3 indexes so no HOT updates; ~28 index
  insertions/row over ~40 ms cold reads). Final shape: per-(old,new) groups in
  200-id chunks, `FOR UPDATE SKIP LOCKED`, `lock_timeout 15s`, per-chunk
  commits, ledger appended per chunk (applied rows only).
- **Reversal:** `--revert <ledger.jsonl>` swaps each ledgered row back, guarded
  on the current value.

Run record (2026-07-28/29, cutoff `2026-07-28T22:11:17+00:00`): plan was
**10,111 rows across 51 pairs** (82 override rows excluded). Applied over five
passes (7,564 + 1,587 + 650 + 256 + 35 — repeated passes because chunks kept
timing out under the degraded IO; each pass re-planned only unledgered rows) —
**pass 5 planned 0 = dry. Ledger total = 10,111 = 100% of plan.** Target-bucket
verification (gdelt lane): XK 1,443 · GE 501 · MN 238 · MC 202 · MO 189 ·
AD 185 · PR 160 · BZ 158 · SS 151 · GM 148 · TJ 146 · SR 129 · PG 113 · LI 5 ·
LB 1,895 · CR 293 (279 ex-CS + 9 overrides) · PY 777 · RS 6,607 (pre-existing
Serbia via GEC RI rode alongside the 1,914 ex-RB). Source buckets now hold only
correct chain-target residents, the 82 Panama overrides, and post-cutoff
arrivals (KV 3, LS 4, … — the ingest bug still writes until the fix deploys).
`country_hourly_v2` refreshed CONCURRENTLY post-run.

## Task 5 — downstream aggregates

| Surface | Kind | Verdict |
|---|---|---|
| `country_hourly_v2` | matview over signals_v2 | Full refresh re-derives from corrected rows; refreshed after the run (also refreshed periodically by `backfill_runner`). Healed for the hot window. |
| `country_heat_v2` | matview | Refreshed every ingest cycle (`ingest_loop`, CONCURRENTLY) — self-heals within ~30 min of the remap. |
| `historical_topic_country_daily` | table, archive-fed ETL | **NOT mutated** — 2026-05-05..07-21, substantial volume under wrong codes (LS 42,312 signals · RB 38,613 · KV 16,756 · PA 12,113 · PM 9,700 · GG 5,033 …). Mutation would need PK-collision merges AND would be undone by re-ETL from the uncorrected archive. Correct fix = apply `country-code-corrections-v1.json` in the ETL/readers (follow-up). |
| `theme_country_hourly_v2` | table, incremental upsert | Old hours keep wrong codes (no full re-derivation exists). Accepted residue: consumers read recent windows; new hours are correct post-remap/post-deploy. |
| `historical_evidence_samples` | table, archive-fed | Same class as historical_topic_country_daily → correction-at-read. |

## Frontend workaround (countryCodeBoundary.ts:29)

**KEEP — not yet redundant.** `LEGACY_GDELT_TO_ISO` (KV→XK, RB→RS, GZ, KS, RI,
EI, UK) still catches: (a) new KV/RB rows arriving until `b7ab7def` deploys,
(b) `historical_topic_country_daily` / archive-derived payloads that still carry
raw codes. Removal conditions: fix deployed + final sweep run + historical
readers apply the corrections artifact. Until all three, the client remap is the
last line of defense and costs nothing (ISO-first design means it can never
misfire on valid ISO codes).

## Still-wrong data (honest residue)

- **Contaminated buckets** (~117k rows/7d + the whole archive): CN, GB, PL, ZA —
  plus MA (Madagascar inside Morocco), LT (Lesotho inside Lithuania), TD
  (Trinidad inside Chad), PS (Palau inside Palestine) found this pass. Splitting
  them needs re-derivation from raw GDELT V2ENHANCEDLOCATIONS in the archive.
  Until then: Comoros, Gabon, Zambia, Madagascar, Lesotho, Trinidad and Palau
  have no clean GDELT lane presence, and their "host" buckets are inflated.
- **TK pathology** (24 rows, Turkey content), **OS**, **YI** — see above.
- Post-cutoff arrivals in all 50 buckets until the fix deploys.

## Follow-ups (ordered)

1. Merge + deploy `b7ab7def` (Fly) — stops the bleeding.
2. Final `--execute` sweep with `--max-created-at` = deploy timestamp.
3. Wire `country-code-corrections-v1.json` into `historical_sync.py` and any
   archive reader; then re-run affected day slices of
   `historical_topic_country_daily` if replay fidelity matters.
4. Contaminated-bucket re-derivation from archive raw locations (separate,
   larger job).
5. Consider excluding GEC pseudo-codes (OS, and post-fix TC-from-TK noise) from
   country surfaces.
