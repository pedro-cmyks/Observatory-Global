# Auditoría de salud 2026-08-24 — una raíz, cuatro síntomas

**Medido**: 2026-08-24 ~06:30-07:00 local (5 auditores paralelos: ingesta ·
NLP/embeddings · motor+G-SALUD-PREVIA · serving prod · ops/reliability).
Contexto: primera revisión tras la mudanza del repo (08-20) y el reindex
(5.0→3.4GB, 08-20). Pedro preguntó: ¿la recolección está sana? ¿los datos se
procesan y clasifican bien?

---

## 0 · Veredicto en una línea

**El motor está sano (G-SALUD-PREVIA cumplida 4/4 noches) y el serving está
sano (edición sellada HOY), pero una sola raíz — el runner nocturno retiene
el heavy lock ~9h — mató de hambre al catchup de archivo/poda 4 noches
seguidas, la base engordó a 13GB con 46% de backlog sin podar, y eso ralentizó
los INSERTs de ingesta hasta tirar el volumen GDELT al ~30% del baseline.**

## 1 · La cascada (una raíz, cuatro síntomas)

```
runner nocturno 22:00→~07:15 (~9h; owner_ttl 240m excedido ×2.3)
  │  (R1 en sí COMPLETA en 1.6-2.5h — el lock lo retienen las fases de cola:
  │   subject-coherence, country-edition warm, goldgrowth-window…)
  ├─► hot-cold-catchup: SKIPPED las 6 ventanas × 4 noches (última corrida 08-20)
  │     └─► 502,684 filas >7d sin archivar/podar (46% de signals_v2, oldest 08-05)
  │           └─► base 13GB (signals_v2 3.8GB + embeddings 3.4GB + matviews)
  │                 └─► INSERTs de ingesta a 12-16 filas/s (medido en el log de Fly:
  │                     806 en 67s, 2,946 en 184s) → el loop de ingesta se estira
  │                     → se saltan buckets GDELT de 15min → volumen al 30-38%
  ├─► embed-hot-corpus: GAVE UP 90m en los slots nocturnos, 3 noches → ~23K
  │     señales frescas sin embed cada mañana (watchdog kickstartea 2×/día)
  ├─► goldgrowth: GAVE UP 120m × 4 noches (acumulador de gold congelado)
  └─► matview-refresh: starved toda la noche (refresca bien de día)
```

**Feedback loop**: más filas → snapshot más lento → lock más tiempo → menos
poda → más filas. Sin intervención esto diverge.

### Números de ingesta (el síntoma visible)

| día | señales | gdelt en | gdelt non-en |
|---|---|---|---|
| 08-17 | ~131K | 46,439 | 84,198 |
| 08-20 | ~96K | 46,966 | 49,448 |
| 08-21 | 52K | 44,640 | 7,471 |
| 08-22 | 24K | 24,121 | **0** |
| 08-23 | 25K | 22,682 | 2,243 |
| 08-24 (parcial) | 19K | 14,655 | 5,291 |

La lane de traducción GDELT es la más golpeada (funciona a ráfagas: la mayoría
de ciclos no la aterrizan). El mecanismo está VIVO — el ciclo de las 11:33 bajó
y escribió ambas lanes sin errores — pero lento: el cuello es el INSERT, no el
fetch. La correlación temporal es exacta: la caída empieza 08-21, la primera
mañana después de la primera noche sin poda.

## 2 · Lo que está sano (verificado, no asumido)

- **G-SALUD-PREVIA (gate M1): CUMPLIDA** — 4/4 nocturnas post-reindex con R1
  sin timeout (9029s→8070s→5973s→5660s, 0 QueryCanceledError, snapshots en DB
  con conteos exactos). El reindex funcionó: R1 bajó de 2.5h a 1.6h.
- **NLP al día**: nlp_sentiment 100% / nlp_persons 99.6% en 24h y 72h (la meta
  #184 output==input, cumplida); fleet estable, 0 kickstarts, watchdog limpio.
- **Clasificación en banda**: gate 24.9% kept/24h; court 63.9% entailed /
  20.4% failed en 4,245 activos; 0 junk activo; headline NULL 0.18%.
- **Serving prod 5/5**: /threads 10 historias dynamic (5.9s frío), /briefing
  artefacto de HOY con 3 coverage_gaps, **edición sellada HOY 11:25Z**
  (sealed_partial por readiness who/where — honesto, no fallo) con state-media
  flag fluyendo en citations, /universe 3,986 nodos en 3.2s.
- **Cero SEAL_FAILED / PROVIDER_EXHAUSTED desde 08-20.** /Volumes/Ext montado,
  1.7Ti libres.

## 3 · Acciones tomadas EN esta sesión

1. **Fixture de testigos congelado ANTES de destrabar la poda**:
   `docs/research/recall-229/fixtures/2026-08-24-m1-shadow-fixture.json.gz`
   (86 testigos + muestra A0 con sus 40 embeddings). La poda parada los había
   preservado; destrabarla los mata; G-TESTIGOS queda medible por replay.
2. **Catchup lanzado** (waiter en fondo: espera a que el nocturno suelte el
   lock → `taskpolicy -b run-local-hot-cold-catchup.sh`). Archiva y poda el
   backlog de 502K — el fix inmediato de TODA la cascada.
3. **Falsa alarma descartada con evidencia**: el "segundo runner" (pid 87234)
   es subshell del mismo nocturno (PPID 31267) corriendo
   `compute_subject_coherence` — no se tocó nada.
4. M1 familia ① decidida + calibrada (ver addendum del spec M1-GATE).

## 4 · Abierto, en orden de urgencia

1. **M4 estructural — el lock nocturno** (el plan motor ya lo nombraba; hoy
   tiene números): R1 termina a las ~03:00 pero el lock se retiene hasta
   ~07:15 por las fases de cola. Palancas concretas: (a) soltar el heavy lock
   tras R1+writes y correr las fases de cola (coherence, country-edition warm)
   SIN lock o con lock propio de baja prioridad; (b) ventana protegida para el
   catchup (p.ej. el runner nocturno cede el lock 00:30-01:30); (c) el
   owner_ttl 240m está siendo pura decoración — o se honra o se re-dimensiona.
   **Decisión con números, no otro reindex manual**: tras el catchup de hoy,
   re-medir tamaño real y velocidad de INSERT antes de decidir REINDEX.
2. **Volumen GDELT**: vigilar 24-48h post-poda. Si el INSERT vuelve a >40/s y
   el volumen no se recupera, el problema es otro (upstream/loop) y se
   investiga aparte. No tocar el ingest hoy: el mecanismo está vivo.
3. **threevendor-calibration**: el anotador anthropic (claude-CLI leg) escribe
   113 filas/día con los campos gold_* en null → overlap 0 con deepseek/openai.
   El leg está roto silenciosamente desde hace días (chip aparte).
4. **Feed rot**: ~25 feeds RSS flagged/día (10 UNREACHABLE, 10 STALE crónicos
   — chinadaily 3,176d, corriere 832d). Erosiona #235 en silencio.
5. Menores: 1 señal con timestamp futuro (2026-09-04, clase parseo-fecha);
   /stats `unique_sources` degradado (null honesto); disco raíz M1 con 14Gi
   libres (vigilar en pases pesados).

---

*Auditores: workflow `atlas-health-audit` (5 agentes, ~925K tokens). Logs
fuente: `/Users/pedro/AtlasLocalWorker/logs/{scoped-snapshot,embed-hot-corpus,
local-hot-cold-catchup,goldgrowth,matview-refresh,reliability-alerts,
cron-freshness-watchdog,heavy-lock}.log` + Fly `atlas-api-pedro` + Supabase.*
