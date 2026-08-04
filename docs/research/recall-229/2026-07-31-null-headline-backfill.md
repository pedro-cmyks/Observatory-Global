# NULL-headline backfill — recovering the translingual lane's history from the GDELT archive

**Date:** 2026-07-31 · **Script:** `backend/scripts/backfill_null_headlines.py`
(+ `backend/tests/test_backfill_null_headlines.py`, 18 tests) · **Parser fix
this repairs behind:** `ff55d6b0` · **Diagnosis:**
`2026-07-30-gdelt-null-headline-diagnosis.md`

## 0. Verdict

The historical NULL headlines are recoverable at **~90%** by replaying the
GDELT translation archive against the NULL set, and the recovery is now
mechanized, ledgered, resumable, and reversible. The parser fix is confirmed
live in prod (translated-lane NULL rate 7.2% → ~0.9% residual on fresh
ingest hours). Downstream re-derivation needs **no re-enqueue**: both
embedding and NER select on `headline IS NOT NULL` + not-yet-processed, so
backfilled rows become eligible on the next cron by predicate.

## 1. Measured scope (2026-07-31)

| Where | NULL `gdelt_gkg_translated` rows | Span |
|---|---:|---|
| External archive (`/Volumes/Ext/Atlas/Archive`, 882 partitions) | **458,442 unique ids** (504,490 occurrences — 23,115 ids live in >1 partition via incremental-run overlap; 279 partitions carry NULLs) | 2026-05-09 → 2026-07-24 (77 days, 6.9% of the lane) |
| Prod `signals_v2` (7-day window) | **29,670** | 2026-07-24 → 2026-07-31 |
| Out of scope: English `gdelt_gkg` lane in archive | 44,811 | different residual class (mostly no-`PAGE_TITLE` + short titles at ~0.3% incidence — not this mechanism's hole) |

Independent cross-check: a from-scratch scan (json.loads per line) and the
script's fast-filtered index (`'"headline":null' in line` pre-filter) agree
exactly — 504,490 occurrences / 77 days / 279 partitions.

## 2. Why the titles are recoverable mechanically

- GDELT keeps every 15-minute `…translation.gkg.csv.zip` forever.
- A signal's `timestamp` **is** the GKG DATE field (col 0) = the file bucket
  (`parse_gkg_row`, ingest_v2.py:422-423), so one UTC day of NULL rows maps
  exactly to that day's 96 archive files (~1.2 GB/day).
- Rows match by `source_url` = GKG col 4 DocumentIdentifier — UNIQUE in
  `signals_v2` (`ON CONFLICT (source_url)`), so matches are unambiguous.
- A recovered title is only written if it passes the **same fixed
  validation** as the live parser (lockstep duplicate of ff55d6b0: not
  `^\d{6,}`, and ≥4 words OR CJK-dominant >50% over the script_floor ranges
  AND ≥10 chars). Parity pinned by tests on the same fixture titles as
  `test_gkg_cjk_title_validation.py`.

## 3. Live one-day validation (dry-run, 2026-07-28)

96/96 buckets fetched, 224,087 titled URLs extracted → prod 5,005 NULL rows,
**4,507 matched+validated = 90.0%**. Residual = rows whose GKG record ships
no `PAGE_TITLE` (~0.2% of lane) + titles the current parser also rejects
(short non-CJK). Samples are real recovered headlines
(`"IMF总裁访阿根廷 赞米莱经济改革成果"`, …).

## 4. Prod pass (EXECUTED)

Per-day, batched `UPDATE … FROM unnest` guarded `AND s.headline IS NULL`
(idempotent; can never clobber a parser-written headline). Verified after the
first four days:

| day | NULL before | written | recovered |
|---|---:|---:|---:|
| 07-24 | 3,226 | 2,839 | 88.0% |
| 07-25 | 3,891 | 3,540 | 91.0% |
| 07-26 | 3,669 | 3,341 | 91.1% |
| 07-27 | 6,824 | 6,224 | 91.2% |
| 07-28 | 5,005 | 4,507 | 90.0% |
| 07-29 | 3,658 | 3,203 | 87.6% |
| 07-30 | 2,999 | 2,525 | 84.2% |
| 07-31 | 450 | 0 | 0% — expected: post-fix rows, so today's NULLs ARE the unrecoverable residual class (no PAGE_TITLE / short non-CJK); the parser fix being live makes this the control day |

**Prod total: 26,179 / 29,722 = 88.1% recovered.** (Per-day "written" for
07-24..27 derived from the ledger; NULL-after spot-check 387/351/328/600
reconciles exactly with written = before − after on every day.)

Ordering is deliberate: **prod first**, so the nightly archive-then-prune job
exports these rows WITH headlines — no new NULL rows enter the external
archive behind the already-built index.

Embedding/NER pickup is by predicate — `embed_hot_corpus` selects
`headline IS NOT NULL` where no embedding exists (embed_hot_corpus.py:260);
`nlp_pipeline` selects `{target} IS NULL AND headline IS NOT NULL AND
LENGTH(headline) > 10`. A NULL-headline row was never embedded/NER'd, so the
backfilled rows enter both queues automatically on the next cron cycles.

## 5. Archive pass (EXECUTED)

**Final totals (77 days, ~3h wall):** 504,490 NULL occurrences → **443,614
written = 87.9%**, 279 partitions rewritten across 192 incremental run dirs +
the 2026-05-20 cutover; 15,623,403 titled GDELT URLs replayed; 2 missing
GDELT buckets in the whole span. The ledger reconciles exactly:
26,179 prod + 443,614 archive = 469,793 lines.

**Verification: `archive_verify` PASSES on all 193 touched run dirs, 0
failures** — every rewritten partition's sha256 (uncompressed-line digest),
row_count and byte size agree with its updated manifest. A full
post-backfill rescan of all 882 partitions counts **60,876 residual NULL
occurrences = exactly 504,490 − 443,614** — every matched row was written,
every write is accounted for.

Matched partitions are rewritten in place with three invariants:

1. **Untouched lines stay byte-identical** — only matched NULL rows are
   re-serialized (`json.dumps(…, ensure_ascii=False, sort_keys=True,
   separators=(",", ":"))`, the exact `archive_export.py` form).
2. **Manifests stay true** — the manifest `sha256` is the digest of the
   UNCOMPRESSED lines exactly as `archive_export.py` computes it; the rewrite
   recomputes it the same way and updates `sha256` + `bytes` in the owning
   `manifest.jsonl` (root or incremental-run dir), so `archive_verify.py`
   keeps passing. `row_count` is unchanged by construction.
3. **Originals survive** — partition + manifest are copied to
   `/Volumes/Ext/Atlas/Backups/null-headline-backfill/` before the first
   rewrite (first copy wins; a second rewrite never overwrites the true
   original). `--revert-archive <backup-dir>` restores them.

Ids living in multiple partitions (23,115) are fixed in every occurrence.

## 6. Safety / ops properties

- Dry-run default; `--execute` required to write.
- JSONL ledger (`~/AtlasLocalWorker/logs/null-headline-backfill-ledger.jsonl`)
  written+flushed BEFORE each batch; `--revert-prod <ledger>` restores NULL
  only where the current value is exactly what we wrote.
- Per-day resumable state with separate `prod:`/`arch:` keys
  (`~/AtlasLocalWorker/null-headline-backfill/backfill-state.json`) — a
  prod-only pass never masks the later archive pass over the same day. A
  killed run redoes at most one day (proven live: the first prod run died
  after day 4; the relaunch resumed at day 5 with zero duplication).
- Archive NULL index cached; invalidated on any partition set/mtime/size
  change, `--rebuild-index` forces.
- Downloads on a 6-thread pool (~3 min/day vs ~11 sequential), cache dir
  `/Volumes/Ext/Atlas/GdeltCache/<day>/`, deleted after the day unless
  `--keep-downloads`.

## 7. Honest residuals

- **~9-12% of NULL rows stay NULL**: no `PAGE_TITLE` in GDELT's own record,
  or a title the CURRENT parser would also reject (short non-CJK — fixing
  those is the parser's open §5 residual, not the backfill's).
- **English-lane NULLs (44,811 archive) not touched** — same machinery could
  replay `…gkg.csv.zip` (non-translation) files, but that hole is mostly
  no-PAGE_TITLE, so expected yield is low; measure before spending the
  ~77 × 96 downloads.
- **Archive embeddings**: the archive embed shards
  (`/Volumes/Ext/Atlas/Embeddings`) skipped NULL-headline rows; backfilled
  archive rows are absent there. Re-running `archive_embed_pipeline.py` over
  the recovered ids is a separate, costed decision (~460k OpenAI 3-small
  embeds ≈ $1-2) — only worth it before the next archive-wide measurement
  (bake-offs read those shards).
- Rows archived by incremental runs AFTER the index was built are not in
  this pass — but prod was backfilled first, so post-fix exports carry
  headlines; the residue is only the handful of pre-fix rows archived
  between index build and prod completion. A later `--rebuild-index` re-run
  is idempotent and sweeps them.

## 8. Reproduction

```bash
set -a; source /Users/pedro/AtlasLocalWorker/.env; set +a
cd backend
# dry-run, one day
python scripts/backfill_null_headlines.py --target prod --days 2026-07-28
# full passes
python scripts/backfill_null_headlines.py --target prod --execute
python scripts/backfill_null_headlines.py --target archive --execute
# verify a touched run dir afterwards
python scripts/archive_verify.py --archive-dir /Volumes/Ext/Atlas/Archive/incremental/<run>
```
