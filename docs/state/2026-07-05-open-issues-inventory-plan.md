# 2026-07-05 — Inventario de issues abiertos + plan de cierre y verificación

**Fuente:** GitHub API en vivo, 2026-07-05 (30 issues OPEN). Cruzado contra el
estado real del repo al `83ad06b` (ships de julio: L1/L2/L3 deep reviews
ejecutados, semantic lane, gate v3, archivo completo embebido, time-as-dimension
S1-S4, #239 end-to-end) y contra el **clusterizado Stage B del archivo**
(`archive_story_units.py`, corriendo ahora, entrega estimada ~15:00) cuyo output
es `/Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl` → insumo directo de
`robot_categories_v1.py --units-jsonl`.

**Nota de entorno:** esta sesión corre en contenedor remoto sin acceso a la DB
de prod ni a `atlas-api-pedro.fly.dev` (proxy 403). Toda verificación marcada
`[M1]` se corre desde tu máquina / sesión local; `[browser]` es eyeball en
Vercel prod.

---

## Resumen ejecutivo

| Grupo | Issues | Acción |
|---|---|---|
| A. Cerrables YA (trabajo hecho, falta el cierre formal) | #239 #241 #243 | Verificar hoy → cerrar |
| B. Cerrables tras verificación con datos que ya corren | #168 #180 #154 #217 | 1 query/eyeball cada uno → cerrar o follow-up estrecho |
| C. Alimentados por el clusterizado de HOY (~15:00) | #204 #226 #238 | El run de Stage B es el próximo paso concreto de cada uno |
| D. Trabajo real pendiente (ordenado por esfuerzo/valor) | 15 issues | Quick wins S esta semana; M gated en decisiones |
| E. Bloqueados en Pedro / calendario | #46 #106 #140 #151 #236 | Decisión o fecha, no código |

Meta razonable de la semana: **30 → ~18-20 abiertos** sin cerrar nada a ciegas.

---

## A. Cerrables YA — verificar hoy y cerrar

### #239 perf(loadtimes) — programa de load-times
Todo el arco se entregó el 07-04: warm-cache (`ab964f0d`,
`lib/fetchWarmCache.ts`), MapLibre DEPRECATED −1MB (`1c99ded1`), keep-alive
shell App+Brief (`775fe945`), hidden-pane poll damp. Los propios comentarios del
issue documentan slice 1 y slice 2 SHIPPED; solo falta el acto de cierre.
- **Verificar [browser]:** Brief↔App round-trip instantáneo con estado intacto
  (el sentinel DOM sobrevive); Network tab: al volver al Brief no hay fetch
  storm; en dist no existe chunk `maplibre`.
- **Cerrar con:** resumen de los 4 commits + medición (re-entry 3ms, primer
  load −1MB).

### #241 perf(embed) — throughput del embed cron M1
Lever 2 (write-concurrency 10x) shipped 06-26; lever 1 (bulk-reindex) EJECUTADO
la noche 07-01→02: backlog de 196K limpiado (total 476K), HNSW reconstruido
(fix del pooler `9f204d5a`). El watchdog del 07-04 reporta embeddings frescos.
La condición de cierre del propio issue era "steady-state keeps up with inflow".
- **Verificar [M1]:**
  ```sql
  SELECT count(*) FROM signals_v2 s
  LEFT JOIN signal_embeddings e ON e.signal_id = s.id
  WHERE s.created_at > now() - interval '24 hours' AND e.signal_id IS NULL;
  ```
  y `launchctl list com.atlas.embed-hot-corpus` → exit 0 reciente. Si el
  pendiente de 24h se mantiene en el orden de un run nocturno (< ~60K), cierra.
- **Cerrar con:** número medido + nota de que el hazard del pooler quedó
  documentado en #243/playbooks (PB-1).

### #243 chore(ops) — checklist de follow-ups del 07-01
La mayoría del checklist ya se resolvió y está documentado en los comentarios:
fly re-auth ✓, deploys ✓, multilingual drain medido ✓, #241 lever 1 ✓,
scoped-snapshot fires ✓, theme-hint removal = mig 067 ✓ (07-04), watchdogs ✓.
- **Verificar [M1]:** repasar el checklist línea a línea. Vivos probables:
  burst=2, model-caching entre ciclos NER, feeds uk/bg, role_noise_rate,
  temporal-holdout window.
- **Acción:** cerrar #243 y abrir UN issue chico "NER throughput levers:
  model-caching + burst=2" con los 2-3 items genuinamente vivos (el lag NER de
  5.2 días medido el 07-01 sigue siendo el dato que les da urgencia). Un
  checklist perpetuo abierto es el mismo mecanismo de staleness que el issue
  critica.

---

## B. Cerrables tras UNA verificación (los datos ya corren)

### #168 feat(narratives) — attention threads + 5 tipos de relación
La mitad de serving está viva desde F0.4 (`/api/v2/topic/{id}/relationship`,
`classify_relationship`, 14 tests). La condición de cierre autodeclarada: los 5
tipos deben DIFERENCIARSE con datos reales de foro. F1 (Bluesky Jetstream +
Lemmy) ingesta desde 06-29 = ~6 días de drain, y el attach de discusión corre en
el cron de embed.
- **Verificar [M1]:**
  ```sql
  SELECT role, count(*) FROM topic_members
  WHERE assigned_at > now() - interval '72 hours' GROUP BY role;
  ```
  y para 5-10 topics con `discussion_count > 0`:
  `curl .../api/v2/topic/{id}/relationship` → ¿aparece algo ≠ media-led?
- **Decisión:** si diferencia → cerrar #168 (la agregación attention-thread
  desde trends/wiki queda explícitamente en el texto de cierre como no-goal
  actual: trends/wiki está flaco/#104 y el relationship endpoint ya entrega el
  producto). Si TODO sigue media-led con foro fluyendo, el residuo es umbral de
  attach (piso adaptativo por centroide, 07-03) — follow-up estrecho, no este
  umbrella.

### #180 fix(reliefweb) — ingest NGO en ~0
Reabierto 07-01 (2 filas ngo/7d; Fly recibe HTTP 202 vacío del RSS).
- **Verificar [M1]:**
  ```sql
  SELECT count(*), max(created_at) FROM signals_v2
  WHERE source_family='ngo' AND created_at > now() - interval '7 days';
  ```
- **Decisión:** si sigue ~0 (esperado), el fix es el camino API oficial de
  ReliefWeb (`https://api.reliefweb.int/v1/reports`) en vez de RSS-desde-Fly —
  trabajo S, entra a la cola D de esta semana. Si por alguna razón ya fluye,
  cerrar con el conteo.

### #154 data(audit) — auditoría de calidad de fuentes
~75% hecho según el pase del 07-01: `voice_mix_audit`, `self_coverage_report`,
funnel medido, NER lag medido. El 25% restante era "serving-integration"
(emparejado con #217).
- **Verificar:** releer el acceptance del issue contra los artefactos de
  `docs/research/voice-mix/` + los reports.
- **Decisión:** cerrar contra artefactos y dejar el residuo de serving en #217
  (un solo dueño para ese residuo, no dos issues).

### #217 feat(sources) — credibility tiers (capability G)
W3 (dossier v2, `e4d21759`, 07-05) shipped "tiers #217 mínimo" dentro del
who-says-what del dossier.
- **Verificar [browser]:** abrir un dossier L3 → ¿la evidencia lleva tier/voice
  labels (state-media, self-voice, dominant-outsider)? ¿Eso satisface el forcing
  case del spec (distinguir conspiracy vs agencia vs mainstream)?
- **Decisión:** probablemente NO cierra completo — el mínimo del dossier no es
  la clasificación de credibilidad por outlet del spec. Re-scope el issue al
  residuo concreto (tabla outlet→tier + surfacing en evidencia) y absorber ahí
  el residuo de #154. Si Pedro considera que el mínimo basta para el wedge,
  cerrar ambos.

---

## C. La ruta del clusterizado de HOY (~15:00) — #204, #226, #238

El run Stage B (`archive_story_units.py cluster`) está convirtiendo 6.9M
vectores del archivo (may-03 → jul-05) en story units por día. Al terminar:

**Paso 0 — verificar el run [M1]:**
```bash
wc -l /Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl
# días cubiertos vs esperados (~62):
python3 -c "import json,collections; c=collections.Counter(json.loads(l)['first_seen'] for l in open('/Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl')); print(len(c),'días; min',min(c),'max',max(c))"
```
Sanidad: unidades con n≥8, headline-medoid legible, top_cc poblado. Es
resumible — si un día falta, relanzar el subcomando `cluster` lo salta/completa.

### #204 taxonomía (issue VIVO, quarterly) — hoy avanza de verdad
El hallazgo del robot v1 (05-jul madrugada) fue: sobre la ventana hot, 0
inserts espurios — las 30 seeds cubren ESA ventana; categorías nuevas se
esperan de las unidades era-mayo. Eso es exactamente lo que entrega Stage B.
- **Plan post-run:** `robot_categories_v1.py --units-jsonl <output>` →
  revisar los guards medidos (intra≥0.80 SAME-STORY = work-list de dedup;
  token dominante ≥60% EVENT-LEVEL = material umbrella); el naming DeepSeek es
  por GRUPO. Reporte tipo `robot-v1-2026-07-05.md`, **manual hasta eyeball de
  Pedro** — el growth loop (`grow_atlas_categories.py`, cap 2/noche,
  origin='auto') sigue siendo el puente automático.
- **#204 NO se cierra** (es el ciclo vivo), pero el comentario post-run con las
  categorías candidatas era-mayo es el entregable de hoy.

### #226 research(markets) — M0 event study: AHORA es ejecutable
El bloqueo histórico era no tener series históricas de threads. Ya existen:
archivo 10.5M filas, story units por día (hoy), `historical_topic_country_daily`
(replay 30d real), `historical_evidence_samples` (60K muestras, 62 días).
- **Plan:** M0 offline sobre el archivo — eventos = spikes de unidades por
  categoría/país/día vs retornos de tickers/commodities públicos. Esfuerzo M,
  después del robot. Comentar el issue hoy con "sustrato listo" para que no
  siga leyéndose como bloqueado.

### #238 subject geography — vía medida nueva
Las story units traen `top_cc` calculado por miembro real (no volumen de
cobertura crudo). Sirve como baseline medido para el rediseño de chips/dedup por
subject-country. Sigue siendo trabajo M; comentar con la conexión para que la
próxima sesión de engine lo tome con el sustrato correcto.

---

## D. Trabajo real pendiente — orden propuesto

**Quick wins S (esta semana, cada uno cierra un issue):**
1. **#247** design WCAG — solo quedan C1/C2 (consolidación panel-headers +
   badges); el audit ya computó la lista exacta. Verificar: re-correr el audit
   de contraste → 0 fails en los grupos C1/C2 + eyeball.
2. **#251** GKG ORGANIZATIONS — añadir el campo al parse de ingest (el grep del
   issue muestra que nunca se ingirió); decisión chica: ¿backfill o solo
   forward? Verificar: filas nuevas con orgs pobladas.
3. **#156** NewsAPI quota budget — reserva + queries dinámicas de crisis; S.
   Verificar: consumo diario < presupuesto en el log de ingest.
4. **#233** paneles reordenables — RGL ^2.2.3 sigue en deps, el commit
   `e6fbecf` es la referencia de cómo era. S/M frontend. Verificar: drag
   funciona + layout persiste + no rompe el keep-alive shell del 07-04 (¡ojo:
   ese shell cambió el mounting — probar juntos!).

**M, con sustrato nuevo que los abarata:**
5. **#173** Evidence Route — post-W1 el workbench es UN store con snapshots en
   todo pin; la "ruta" es en gran parte el trail que ya se persiste. Re-scope
   sobre workbench.ts unificado.
6. **#220** funnel ledger — ya existen los reports parciales
   (`sem_assign_report`, `research_usage_report`, gate ledgers) y los playbooks
   PB-1..8 dan la cadencia semanal donde colgarlo. Definir el ledger mínimo
   stage-by-stage y emitirlo en el weekly read.
7. **#221** maturity contract — el two-tier verified/extended + snapshots
   congelados L3 ya cubren la mitad "provisional"; el sealed-hour floor para
   agregados sigue pendiente.
8. **#248** noise classes — bylines-as-subjects + entertainment-about-crisis;
   la clase fediverse ya cayó (`74488ffe`) y los orphans del universe son el
   detector no-supervisado que puede alimentar esto.
9. **#237** community layer (umbrella) — F1 entregado; el umbrella avanza solo
   con la verificación de #168. Mantener como umbrella, no trabajar directo.
10. **#235** domestic voice (programa) — verificar [M1]
    `self_coverage_report.py` → lista actual de países en 0% → siguiente wave
    de feeds. Continuo por diseño.

**Gated en decisión de Pedro (proponer, no ejecutar):**
11. **#185** lexicon mining — candidato a CERRAR-SUPERSEDED: el semantic lane
    OpenAI + gate v3 + growth loop hacen lo que el mining buscaba, y PR3-05
    midió que los theme-hints eran ruido neto. Propuesta: cerrar con ese
    razonamiento.
12. **#172** silent-risk — la investigación 06-29 lo aparcó honestamente
    (fuente attention no confiable); PERO el gap box B3 del 07-05
    (`briefing.coverage_gaps`) ya sirve "what is missing" en L1 por otra vía.
    Propuesta: re-scope #172 a "attention/coverage ratio cuando trends/wiki
    mejore" o cerrar apuntando a coverage_gaps como el sucesor.
13. **#159 / #161** GDELT research (Event Mentions / DOC 2.0) — investigación
    pura, nadie la ha tocado en un mes. Propuesta: mantener SOLO #161
    (query-time enrichment encaja con el research plan L3) y cerrar #159 como
    backlog-explícito (la trayectoria de historias hoy la dan las story units
    del archivo, no Event Mentions).
14. **#166** analyst correction loop — el sustrato llegó (W0 telemetry, pins
    con snapshot, disagreement queue del flywheel). Gate: la lectura de
    telemetría del 07-11; si hay uso real de pins, diseñar el loop sobre
    `research_pin_events`.

---

## E. Bloqueados en Pedro / calendario

| Issue | Bloqueo | Próximo paso |
|---|---|---|
| #46 ACLED | Registro institucional (email) | Pedro decide si registra o si se degrada a "Coming Soon" permanente y se cierra. `acled_conflicts_v2` = 0 filas — hoy es UI-honesty, no ingest. |
| #106 mascota | Sesión de diseño dedicada | Agendar o dejar en backlog; sin código pendiente. |
| #140 manual visual | Grabaciones de pantalla de Pedro | 1 caso de uso grabado desbloquea el primer capítulo. |
| #151 markets overlay | Track L4 (repo privado futuro) | Propuesta: cerrar como folded-into-#226/L4 — el issue vive mejor en el doc L4. |
| #236 mobile | X6 programado 07-11 tras telemetry read | Nada que hacer hoy; el scheduled task ya existe. |

---

## Secuencia concreta

**Hoy (post-15:00):**
1. Verificar Stage B (paso 0 arriba) → correr robot sobre las unidades →
   comentar #204 con las categorías candidatas era-mayo (eyeball Pedro antes de
   insertar nada).
2. Lote A: verificar y cerrar #239, #241, #243 (+ abrir el issue chico de NER
   levers desde #243).
3. Queries de B: #168 (relationship diff), #180 (ngo count) — cerrar o
   convertir en follow-up estrecho según el número.

**Mañana / semana:**
4. B restante: #217/#154 (un dueño para el residuo serving-tiers).
5. Quick wins D: #247 C1/C2 → #251 → #156 → #233 (en ese orden; #233 al final
   por el riesgo de interacción con el keep-alive shell).
6. Comentar #226 y #238 con el sustrato nuevo (sin ejecutar aún).

**Decisiones para Pedro (5 min, en cualquier momento):**
- Cerrar #185 como superseded? · Re-scope o cierre de #172? · Fold #151 en
  L4? · #159 a backlog explícito? · ¿El "tiers mínimo" del dossier basta para
  #217+#154 o se re-scopea?

**07-11 (ya programado):** telemetry read → gates #166 y #236 (X6).

---

## Reglas del pase (las mismas del sweep 07-01)

- Cada cierre lleva evidencia file:line/commit/query — nunca "creo que ya está".
- Verificar contra CÓDIGO y DATOS, no contra docs (los docs de 06-09/06-30
  demostraron estar stale dos veces).
- Cierre ≠ silencio: si un issue se cierra como superseded/folded, el
  comentario final apunta al sucesor concreto.
- Ningún INSERT de categorías del robot sin eyeball de Pedro (guard del 07-05).
