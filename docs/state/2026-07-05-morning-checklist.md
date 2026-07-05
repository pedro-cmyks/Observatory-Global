# Morning checklist — 2026-07-05 (continuar, no re-decidir)

Estado al cierre (~00:40): todo commiteado + pusheado en `v3-intel-layer`
(HEAD `9f821864` + este cierre). Rama limpia; branches mergeadas borradas.

## 1. Archivo — ¿terminó el pipeline overnight?

```bash
tail -5 ~/AtlasLocalWorker/logs/archive-embed-full.log
python3 -c "import json; m=json.load(open('/Volumes/Ext/Atlas/Embeddings/openai-3-small/manifest.json')); print({k:m[k] for k in ('n_rows_seen','n_vectors','n_junk','n_dup')}, len(m['done_partitions']),'partitions')"
```
Éxito: done_partitions = 772, n_vectors ~2.5-4M. Si murió a mitad: relanzar
el MISMO comando (resumible, no re-paga embeddings):
```bash
set -a; source ~/AtlasLocalWorker/.env; set +a
nohup ~/AtlasLocalWorker/mlvenv/bin/python backend/scripts/archive_embed_pipeline.py \
  --shard-size 50000 >> ~/AtlasLocalWorker/logs/archive-embed-full.log 2>&1 &
```

## 2. Robot — SPEC CERRADO ANOCHE, ejecutar sin re-discutir

**`docs/specs/2026-07-05-category-robot.md`** = la ruta completa acordada
con Pedro (00:30-01:00). Resumen: producto sigue DOS columnas (fila=historia
/evento · tag=categoría); el robot emite TRES salidas internas — categoría →
atlas_topics auto (tag derecho) · **evento canónico → umbrella PERSISTENTE
is_umbrella=true, UNA fila padre** (Venezuela Earthquake = 1 fila, no 25) ·
misma-historia → fusión de identidades. Orden: Stage B
(`archive_story_units.py`, clustering semanal de shards) → robot con
`--units-jsonl` → salida-evento a umbrellas → fusión → eyeball Pedro →
armar cron. Guards y umbrales medidos ya implementados.

## 3. Label-bug WIP (rama aparte, NO mergeada)

`claude/heuristic-brahmagupta-38dd7f` = fix resolveThreadLabel (dynamic-topic
raw id en Legend/paneles), 7 archivos, commiteado WIP `9f740e82`, **sin
verificación browser**. Mañana: `npm run build` + eyeball → merge o descartar.

## 4. Chequeos rápidos (5 min)

- `launchctl list | grep atlas` — todo exit 0 (PB-1).
- Sem-lane: `sem_assign_report.py --window-hours 24` — keep sem 0.10-0.25 (PB-2).
- Growth loop v0: ¿el scoped-snapshot 02:30 corrió Step 5? `grep "category growth" ~/AtlasLocalWorker/logs/scoped-snapshot*.log` — ledger en docs/research/taxonomy-revision/auto-growth-ledger.md.
- Hot window creciendo: `SELECT min(created_at) FROM signals_v2` — debe retroceder hacia 7d con los días.
- Pool: `SELECT count(*) FROM dynamic_topics WHERE state='active'` — ≥80 → correr PB-5 (A/B F4).
- Chip spam Bluesky (task_9e296e6b) — ¿terminó su sesión? revisar/mergear.

## 5. Cola después (orden)

1. Stage B + robot con historia profunda (arriba).
2. Country-view stories-only (migrar el merge R1 — contrato CountryBrief).
3. A/B F4 cuando pool ≥80 (PB-5; flip = decisión Pedro).
4. Archivo→identidades (time-as-dimension serving; el spec de Pedro).
5. Robot recursión temas→dominios (hoy report-only).
