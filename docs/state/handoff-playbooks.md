# Handoff playbooks — mechanical runbooks (2026-07-04, Day 3 of the 3-day route)

Purpose: everything judgment-heavy landed in Days 1-2. These are the
MECHANICAL recipes a smaller model (or Codex headless, or Pedro at 2am) can
execute without judgment calls. Each playbook states: trigger, commands,
success check, reversal.

Conventions used everywhere below:

```bash
REPO=/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
ALW=/Users/pedro/AtlasLocalWorker
PY=$ALW/mlvenv/bin/python           # ML venv (torch, asyncpg, openai)
# env: set -a && source $ALW/.env && set +a   (DATABASE_URL, OPENAI_API_KEY, DEEPSEEK_API_KEY)
```

Rule of thumb: if a step's output contradicts its success check, STOP and
leave a note — do not improvise fixes to the engine or thresholds.

---

## PB-1 · Cron health check (run when anything looks stale)

```bash
launchctl list | grep atlas          # every job: last exit 0 (nlp-fleet has a PID, that's normal)
ls -lt $ALW/logs/ | head             # log mtimes recent?
```

Key crons: `atlas-topic-classifier` (30 min — assignments + gate + semantic
lane + typing), `scoped-snapshot` (02:30), `embed-hot-corpus` (17:30/23:30/
05:30), `goldgrowth` (03:30), `cron-freshness-watchdog` (30 min — auto-
kickstarts stale crons by DB freshness; it is the safety net).

Manual kickstart (idempotent, safe):
```bash
launchctl kickstart -k gui/501/com.atlas.atlas-topic-classifier
# then: tail -30 $ALW/logs/atlas-topic-classifier.err.log
```
Success: `LastExitStatus = 0`; err.log shows Step 1→4 output.
NEVER run two heavy ML jobs at once (embed + clustering) — load 16 on the
8-core M1 is the kernel-panic zone. The watchdog already serializes; don't
hand-fire a second heavy job while one runs.

---

## PB-2 · Semantic lane: monitor / recalibrate / disable

Monitor (any time; healthy = sem keep-rate 0.10-0.25, lex ~0.30):
```bash
cd $REPO && set -a && source $ALW/.env && set +a
$PY backend/scripts/sem_assign_report.py --window-hours 48
```
Red flags → disable (see below) and leave a note:
- sem keep-rate < 0.05 sustained (lane feeding junk; gate rejecting almost all)
- a single topic adding hundreds/cycle (tau broken for it)

Disable (instant, reversible; existing rows stay, distinguishable by
`model_version='sem-assign-v0'`):
```bash
# in $ALW/.env add:  ATLAS_SEM_LANE_ENABLED=false
# next 30-min cycle skips Step 2b. Re-enable: remove the line.
```

Recalibrate taus (monthly, or when taxonomy text changes, or on red flag):
```bash
cd $REPO && set -a && source $ALW/.env && set +a
$PY backend/scripts/calibrate_tau_wild.py \
  --corpus /Volumes/Ext/Atlas/Gold/mega2-corpus-2026-07-04.jsonl \
  --taxonomy docs/research/taxonomy-revision/candidate-v2.json \
  --sample 2000 --hours 48 --max-wild-fp 1 \
  --out docs/research/semantic-lane/$(date +%F)-tau-sem-wild
# success check: "lanes on" >= 20/30 and election-legitimacy-dispute among them
cp docs/research/semantic-lane/$(date +%F)-tau-sem-wild.json $ALW/config/2026-07-04-tau-sem-wild.json
# (cron reads that fixed path; overwrite it, keep the dated repo copy as record)
```
Use a NEWER gold corpus if one exists (the flywheel accumulates); never
delete the old calibration files.

---

## PB-3 · Gate retrain (when accumulated gold grows: +2k labeled rows or monthly)

1. Build/refresh corpus (the goldgrowth cron accumulates candidates+labels;
   merge scripts live in `backend/scripts/build_goldgrowth_corpus.py` — see
   its --help; output = one jsonl in the mega2 schema).
2. Embed for training (OpenAI, 'headline | label'):
```bash
$PY backend/scripts/embed_corpus_openai.py --corpus /tmp/new-corpus.jsonl \
  --out /tmp/new-embeddings.jsonl        # ~$0.01 per 10k rows
```
3. Train at BOTH targets with variance-aware calibration:
```bash
$PY backend/scripts/train_scope_gate.py --corpus /tmp/new-corpus.jsonl \
  --embeddings /tmp/new-embeddings.jsonl --embed-model text-embedding-3-small \
  --target-precision 0.90 --bootstrap-thresholds 300 \
  --out $ALW/models/$(date +%F)-scope-gate-vNEXT.json \
  --report $ALW/models/$(date +%F)-scope-gate-vNEXT.calibration.json
$PY backend/scripts/train_scope_gate.py --corpus /tmp/new-corpus.jsonl \
  --embeddings /tmp/new-embeddings.jsonl --embed-model text-embedding-3-small \
  --target-precision 0.75 --bootstrap-thresholds 300 \
  --out /tmp/gate75.json --report /tmp/gate75.calibration.json
```
4. DEPLOY GATE (hard rule — no judgment): deploy vNEXT ONLY if, vs the
   current calibration json, on the same corpus: overall OOF AUC does not
   drop AND >= half the hard topics (election-legitimacy-dispute,
   telecom-internet-shutdown, sanctions-diplomatic-pressure,
   currency-debt-stress) improve recall at held precision. Otherwise stop
   and leave both calibration jsons for review.
5. Flip cron to the new gate:
```bash
# $ALW/.env:  ATLAS_GATE_JSON=$ALW/models/<new>.json
#             ATLAS_GATE_ID=atlas-scope-gate-vNEXT
```
6. Re-emit extended thresholds + deploy API:
```bash
python backend/scripts/emit_extended_thresholds.py \
  --calibration /tmp/gate75.calibration.json --gate-id atlas-scope-gate-vNEXT
./scripts/deploy-fly-api.sh
```
7. Re-score recent window under the new gate id:
```bash
$PY backend/scripts/score_assignments_gate.py --gate $ALW/models/<new>.json \
  --gate-id atlas-scope-gate-vNEXT --window-hours 48 --rescore
$PY backend/scripts/score_assignments_gate.py --lane semantic --gate ... --gate-id ... \
  --window-hours 48 --rescore
```
REVERSAL: set ATLAS_GATE_JSON/ATLAS_GATE_ID back; old gate_score rows keep
their gate_model tag, nothing is destroyed.

---

## PB-4 · Two-tier serving check (after any gate/threshold change)

```bash
curl -s "https://atlas-api-pedro.fly.dev/api/v2/theme/election-legitimacy-dispute?hours=48" \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['total'],d['rawTotal'],d['gated'],d['verified'],d['extended'])"
```
Success: total >= verified+extended > 0; extendedThreshold present; the
gate_id in `backend/app/data/scope_gate_extended_thresholds.json` equals the
cron's ATLAS_GATE_ID (mismatch = extended tier silently empty).

---

## PB-5 · F4 A/B re-run (substrate must be healthy first)

PRECONDITION (from the 2026-07-04 verdict,
`docs/research/engine-ab/2026-07-04-f4-ab-rerun.md`): active dynamic_topics
pool >= ~80 centroids. Check:
```bash
$PY -c "import asyncio,asyncpg,os;print(asyncio.run(asyncpg.connect(os.environ['DATABASE_URL'],statement_cache_size=0).fetchval(\"SELECT count(*) FROM dynamic_topics WHERE state='active' AND centroid_vec IS NOT NULL\")))"
```
If < 80: substrate still thin — do NOT run the A/B, wait for scoped-snapshot
nights to rebuild. If >= 80:
```bash
cd $REPO/backend && $PY -m scripts.build_unified_topics --hours 48   # fresh v2 build
$PY -m scripts.engine_ab_report | tee /tmp/ab-$(date +%F).txt
```
Read ONLY the VERDICT line. PASS → tell Pedro; the flip itself
(ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS=on + ATLAS_TOPIC_MEMBERS_ENGINE_VERSION=unified-v2
on Fly) is PEDRO'S CALL, never automatic. NOT YET → save the output, done.

---

## PB-6 · Substrate collapse recovery (universe suddenly thin / few threads)

Symptoms: universe nodes < 30, /threads mostly atlas, movement flat.
1. PB-1 first (usually dead crons — the 2026-07-04 incident was exactly this).
2. Check pool: PB-5's count query. Thin pool + healthy crons = wait for the
   02:30 scoped-snapshot; identities now SURVIVE wipes (hydrate fallback fix
   `backend/scripts/project_dynamic_topics.py`, 2026-07-04) — do NOT
   hand-restore rows.
3. Verify ingest is alive:
```bash
$PY -c "import asyncio,asyncpg,os;print(asyncio.run(asyncpg.connect(os.environ['DATABASE_URL'],statement_cache_size=0).fetchval('SELECT count(*) FROM signals_v2 WHERE created_at > NOW()-INTERVAL \'24 hours\'')))"
# healthy: 100k-200k
```

---

## PB-7 · Deploys + reversals (reference card)

| what | command | reverse |
|---|---|---|
| API (Fly) | `./scripts/deploy-fly-api.sh` | redeploy previous commit |
| Frontend | push to `v3-intel-layer` (Vercel auto) | revert commit + push |
| Gate | ATLAS_GATE_JSON/ATLAS_GATE_ID in $ALW/.env | set back to previous |
| Semantic lane | ATLAS_SEM_LANE_ENABLED=false | =true |
| F4 read path | ATLAS_TOPIC_MEMBERS_ENGINE_VERSION (Fly secret) | unset (=v1-compat) |
| v2 gate reject | ATLAS_V2_GATE_ENABLED | UPDATE signal_topic_assignments SET gate_kept=true WHERE gate_model='v2-gate-e5-lr-1' |

Fly deploy needs `fly auth` alive; if it errors 'missing third-party
discharge' → Pedro must `fly auth login` (interactive, cannot be automated).

---

## PB-8 · Weekly telemetry read (Fridays; recipe from the telemetry doc)

Value moments + brief_open counts; see
`docs/state/2026-07-04-alignment.md` §telemetry for the SQL. Write one line
into CLAUDE.md: value moments/wk, top surface, any zero-event surface.
Anti-goal check: no new surface until value moments trend up.

---

## Known-state notes for whoever picks this up

- Corpus of record: `/Volumes/Ext/Atlas/Gold/mega2-corpus-2026-07-04.jsonl`
  (13,663 rows; gz twin in repo docs/research/gate-recall/goldgrowth-0704/).
- Lane config the cron actually reads: `$ALW/config/2026-07-04-tau-sem-wild.json`
  + `$ALW/config/candidate-v2.json` (re-sync from repo on change).
- Runner canonical copy: `scripts/run-atlas-topic-classifier.sh` (repo) ↔
  `$ALW/run-atlas-topic-classifier.sh` (executed) — keep byte-identical.
- unified-v2 new topics persist as dynamic_topics candidates
  (identity_key `u2-*`); junk guard rejects template spam. Spam-source
  cleanup is an open chip (number-spelling feed).
- F4 flip = TWO env vars but gated on PB-5 precondition + Pedro.
