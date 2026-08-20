# M1-A0 — ¿unified-v2 ya cubre a los huérfanos del Z4? (medición read-only)

**Medido**: 2026-08-20 19:01Z. **Mandato**: plan motor M1-A0
(`docs/superpowers/plans/2026-08-20-plan-motor.md`) — medir ANTES de tocar;
cero recomendaciones de fix (la decisión es del gate pre-registrado M1-GATE +
Pedro). **Script**: `backend/scripts/m1a0_unified_v2_coverage.py` (READ-ONLY,
`statement_cache_size=0`, `SET LOCAL statement_timeout='110s'` por
transacción, walk por chunks de id, joins del lado del cliente — el patrón
exacto del Z4). **Datos**: `2026-08-20-m1a0-unified-v2-coverage.json`
(companion). **Referencia**: censo Z4
(`docs/research/recall-229/2026-08-18-z4-unassigned-census.md`).

---

## 0 · Números de cabecera

1. **unified-v2 está vivo pero no es un acumulado: es una FOTO de ~16 horas.**
   37,681 filas evidence, TODAS con el mismo `assigned_at`
   (2026-08-20 05:26:49Z — una sola corrida), señales con timestamp
   **2026-08-19 12:51Z → 2026-08-20 04:31Z**. Cada corrida hace
   `DELETE FROM topic_members WHERE engine_version='unified-v2'` y reescribe
   (`build_unified_topics.py:374`) sobre las **40,000 embedded más nuevas**
   (`ORDER BY s.timestamp DESC LIMIT max_n`, `:123-124`). El build corre ~3×/día
   dentro de `embed-hot-corpus` — no murió — pero **nunca retiene más de la
   última foto**.
2. **El delta que decide el arco: −4.8pp sobre la ventana de 7 días.**
   Sin-historia bajo v1-compat: **93.0%** (686,440 de 738,172 servibles,
   Aug 13–19 UTC; reproduce el 92.2% del Z4). Bajo v1-compat ∪ unified-v2:
   **88.2%**. Bajo unified-v2 solo: 95.2% sin historia. El delta entero vive
   en el ÚNICO día que la foto cubre (Aug 19: v1 1.2% con historia vs union
   43.9%); en los días Aug 13–18 el delta es **0.0pp** por construcción.
3. **En el slice que el build sí vio, la cobertura mecánica es 86.2%**:
   de 43,703 señales servibles en su span exacto, 41,289 tienen embedding
   (94.5%) y 37,681 quedaron adjuntadas (**91.3% de las embedded**, tau prod
   0.88). La mecánica de adjuntar existe; lo que no existe es la retención
   temporal ni —ver 4— la calidad del destino.
4. **Calidad del destino (muestra 40, seed 229, juicio a mano): el label del
   topic NO describe el headline en 26/40 = 65%.** Sí: 7 (17.5% — y solo 3
   son historia específica correcta; los otros 4 son buckets genéricos tipo
   "Price Target Changes"). Dudoso: 7 (17.5%, mayormente mismo-teatro/
   historia-gemela). En el subset `gate_kept` (confianza ≥0.90): 17/29 = 59%
   no. **El olfato dice: el flip adjuntaría volumen con mayoría de vecinos
   falsos** — la dispersión argmax del Z4 §6, vista ahora en lo que unified-v2
   efectivamente escribe.
5. **Testigos congelados: 0 de 80 sin-historia tienen membresía unified-v2**
   (espriella 0/66, golán 0/5, ungrd 0/10). Estructural, no probabilístico:
   sus señales (Aug 13–14) son ~5 días más viejas que la señal más vieja que
   la foto retiene (Aug 19 12:51Z). El modo i-vs-ii no es medible ahí: no hay
   adjuntos que juzgar.
6. **Política: 91.8% → 86.4% sin historia bajo el union (−5.4pp)**; en el
   subset `gate_kept`: 88.5% → 83.2%. La misma concentración: todo el delta
   es del día que la foto cubre.
7. **Contexto que contamina el día 19 (medido, no opinión): la lane v1
   también está enferma.** Las DOS últimas nocturnas del scoped-snapshot
   fallaron en el write R1 (`QueryCanceledError: statement timeout` — corridas
   locales Aug 18 22:00 y Aug 19 22:05) y **ninguna corrida ha arrancado desde
   Aug 19 22:48 local**. Por eso v1 en Aug 19 = 1.2% con historia vs 8.5–8.8%
   en días sanos: el "u2 gana 42.8pp el día 19" se mide contra un v1
   enfermo. Contra un v1 sano (~8.7%), el delta de u2 en su día sería ~35pp
   menos el solape que hoy es cero por accidente (ver §5).

---

## 1 · Q1: vitalidad de unified-v2

| medida | valor |
|---|---|
| filas evidence (`role='evidence'`, no-quarantined) | **37,681** (1 fila/señal — argmax único) |
| `assigned_at` min = max | **2026-08-20 05:26:49Z** (una sola corrida sobrevive) |
| topics distintos | **2,823** (2,422 active · 401 candidate u2-born) |
| span de timestamp de señal | 2026-08-19 12:51Z → 2026-08-20 04:31Z (**~15.7h**) |
| señales por día UTC | Aug 19: 35,663 · Aug 20: 2,018 |
| roles acompañantes | discussion 539 · mood 539 (mismas corrida) |

**¿El build corre o murió?** Corre, ~3×/día como Step 4 de
`run-embed-hot-corpus.sh` (launchd `com.atlas.embed-hot-corpus`): 96 corridas
exitosas en la historia del log, 9 fallidas (4 en jul-early, 07-16, 07-19,
07-27, 07-29, y **hoy 2026-08-20 10:30Z** — `ConnectionDoesNotExistError` en
`_load_signals`, ANTES del DELETE, así que la foto del 05:26Z sobrevivió).
Última exitosa: 2026-08-20 05:26Z (`wrote 38759 topic_members(unified-v2)`,
coverage 95.5% de las 40k consideradas).

**Dos hechos del prod que difieren del plan escrito:**

- **La tau de prod es 0.88, no 0.82**: el runner fija
  `UNIFIED_ASSIGN_T="${ATLAS_UNIFIED_ASSIGN_THRESHOLD:-0.88}"`
  (`scripts/run-embed-hot-corpus.sh:108`) y el env no está seteado; el 0.82
  es el default del SCRIPT (`build_unified_topics.py:62`), nunca la corrida
  nocturna. El gate v2-nativo (`gate_kept`) corre a 0.90.
- **El cap efectivo es 40,000, no 60,000**: `.env` tiene
  `ATLAS_UNIFIED_MAX_SIGNALS=60000` pero el receipt de la última corrida dice
  `signals=40000` (el default del script) — el env no llega a ese paso
  (medido por el log; root-cause fuera de alcance).

**Por qué la foto es de ~16h**: 40,000 señales más nuevas ÷ ~60k embedded/día
≈ 16 horas de corpus. El `--hours 336` del runner es el TECHO de la ventana,
no el piso; el `LIMIT` con `ORDER BY timestamp DESC` es lo que muerde.

## 2 · Poblaciones y método (paridad Z4)

- **Ventana**: 7 días UTC completos **2026-08-13 → 2026-08-19** sobre
  `signals_v2.timestamp` (la retención medida hoy arranca en
  2026-08-13T10:10Z — la ventana cabe justa; ver caveat §7.2). Walk por
  chunks de id: 805,591 filas en ventana.
- **Servible**: el filtro del Z4 verbatim (headline no-NULL + no-junk según
  `is_junk_headline` traducido a SQL + `source_family <> 'social'`). Total
  servible: **738,172**.
- **"Con historia"**: `topic_members` `role='evidence' AND quarantined IS NOT
  TRUE AND topic_id LIKE 'dynamic-topic-%'`, con `engine_version` ∈
  {'v1-compat'} / {'unified-v2'} / union. Serving default verificado
  v1-compat (`thread_intelligence.py:42`).
- **Política**: los mismos 28 slugs del Z4 §5 vía `signal_topic_assignments`
  (cualquier method/gate; subset `gate_kept` aparte).
- Muestreos seed 229. Sanity checks en transacciones read-only aparte.

## 3 · Q2: cobertura de los huérfanos, por día

| día UTC | servible | v1 historia | % | u2 historia | union | % union | delta pp |
|---|---|---|---|---|---|---|---|
| 2026-08-13 | 103,873 | 9,058 | 8.7% | 0 | 9,058 | 8.7% | 0.0 |
| 2026-08-14 | 135,514 | 11,470 | 8.5% | 0 | 11,470 | 8.5% | 0.0 |
| 2026-08-15 | 86,652 | 7,593 | 8.8% | 0 | 7,593 | 8.8% | 0.0 |
| 2026-08-16 | 81,944 | 7,165 | 8.7% | 0 | 7,165 | 8.7% | 0.0 |
| 2026-08-17 | 134,648 | 9,552 | 7.1% | 0 | 9,552 | 7.1% | 0.0 |
| 2026-08-18 | 112,157 | 5,933 | 5.3% | 0 | 5,933 | 5.3% | 0.0 |
| 2026-08-19 | 83,384 | 961 | **1.2%** | 35,663 | 36,624 | **43.9%** | +42.8 |
| **7d** | **738,172** | **51,732** | **7.0%** | **35,663** | **87,395** | **11.8%** | **+4.8** |

- Sin historia: v1 **93.0%** → union **88.2%** → u2-solo 95.2%.
- **v1 ∩ u2 = 0 señales** (verificado aparte: 0 miembros-de-historia
  v1-compat con timestamp de señal dentro del span de u2). El union se
  descompone exacto en v1 + u2. No es una propiedad de los motores: es la
  combinación foto-de-16h (u2) + nocturnas caídas (v1) — hoy ningún motor
  pisa el terreno del otro.
- La caída v1 día a día (8.7% → 5.3% → 1.2%) es el rastro de las nocturnas
  fallidas (§0.7), no una propiedad de la ventana.

**El slice que u2 sí vio** (span exacto Aug 19 12:51Z → Aug 20 04:31Z,
medido directo): 46,665 señales → 43,703 servibles → 41,289 con embedding
(94.5%) → **37,681 adjuntadas = 86.2% de las servibles / 91.3% de las
embedded**. Ese es el techo mecánico observado si la foto cubriera los 7
días — techo de CONTEO, no de calidad (§4).

## 4 · Q4: calidad gruesa de lo que unified-v2 añade (muestra a mano)

Muestra seed 229, n=40, del pool de 35,663 señales servibles-en-ventana que
u2 adjunta y v1 no (como v1∩u2=0, el pool ≡ todo lo que u2 adjunta en la
ventana — no es un residuo raro). Juicio de UN lector (yo), criterio: ¿el
label del topic describe el headline? Conteo honesto:

| veredicto | n | % | nota |
|---|---|---|---|
| **sí** | 7 | 17.5% | solo 3 específicos (protesta AL dt-9844 · juicio Hernández dt-7817 · Sifnos dt-12191); 4 son buckets genéricos que "describen" por amplitud (Price Target Changes, Fire Incidents and Losses, Earnings Beat, Murder Convictions) |
| **dudoso** | 7 | 17.5% | mismo-teatro / historia-gemela: Sudan displacement→"Sudan Child Soldiers", Lake Powell→"Lake Mead Record Low", Dürre-Taskforce→"Waldbrandrisiko Südeuropa" |
| **no** | 26 | **65.0%** | vecinos falsos limpios: "Terremoto…"-clase del Z4 reproducida — p.ej. POW ucranianos→"Ukrainian Drone Attacks", Il-76 a Serbia→"Russia Ukraine Strikes", Messi retiro→"Neymar Retires", deuda US $40T (KR)→"Q2 Earnings Reports", educación vial MX→"Jared Leto Sexual Assault Allegations" |

- En el subset `gate_kept=true` (confianza ≥0.90, el gate v2-nativo que el
  cutover F4 serviría como "verificado"): 29 filas → sí 6 · dudoso 6 · **no
  17 (59%)**. El gate de confianza coseno NO filtra el vecino falso (las
  confianzas de los "no" llegan a 0.92–0.94).
- El patrón dominante de los "no" es exactamente la dispersión argmax del Z4
  §6 modo ii: existe una historia plausible cerca, y el argmax cae en una
  identidad hermana/gemela/ajena. Caso ilustrativo: la señal coreana "deuda
  US supera $40T" cayó en "Q2 Earnings Reports" — mientras la MISMA corrida
  formó `dynamic-topic-15350` "Emerging: US national debt exceeds US$40
  trillion" (receipt del log del build).
- Las 40 filas con headline, topic, confianza y veredicto están en el
  companion JSON (`u2_only_sample`) para re-juicio.

## 5 · Q3: testigos congelados

Needles y ventana frozen del Z4 verbatim (`%espriella%`/`%golán%`/`%ungrd%`,
[2026-08-13T15:00Z, 2026-08-14T15:00Z)):

| testigo | matched | sin historia v1 (hoy) | Z4 (18-ago) | con membresía u2 (cualquiera) |
|---|---|---|---|---|
| espriella | 71 | 66 | 67 | **0** |
| golán | 5 | 5 | 5 | **0** |
| ungrd | 11 | 10 | 10 | **0** |
| OR | 86 | **80 (93%)** | 81 (94%) | **0** |

- El Δ1 vs Z4 (81→80) es la clase "asignaciones que llegan después" que Z4
  §7 ya nombró; la dirección no cambia.
- **El 0 es estructural**: unified-v2 no retiene nada anterior a
  Aug 19 12:51Z; los testigos son de Aug 13–14. La pregunta "¿la historia
  correcta o un vecino falso?" no tiene adjuntos que juzgar en este set —
  la respuesta de calidad más cercana es la muestra de §4 (misma lane,
  ventana viva).
- Donde los 6 con-historia aterrizaron bajo v1 (referencia): dt-3967
  "Colombia Earthquake: De la Espriella Declares Economic Emergency" (4),
  dt-522 "ONU Estima Afectados Terremotos Venezuela" (candidate, 4), más
  categoría `earthquake-volcano-disaster` (17 membresías, no cuentan como
  historia).

## 6 · Q5: política

| corte | n | sin historia v1 | sin historia union | delta |
|---|---|---|---|---|
| política 7d (28 slugs Z4) | 23,152 | 21,246 = **91.8%** | 19,993 = **86.4%** | −5.4pp |
| política `gate_kept` | 5,242 | 4,641 = **88.5%** | 4,359 = **83.2%** | −5.3pp |

Reproduce el orden del Z4 (91.1%/87.1% en su ventana). El delta político es
apenas mayor que el global (5.4 vs 4.8pp) y tiene la misma anatomía: todo
del día que la foto cubre.

## 7 · Caveats (declarados, ninguno cosmético)

1. **Ventana distinta al Z4** (Aug 13–19 vs Aug 11–17): el sin-historia v1
   reproduce 93.0% vs 92.2% — el fenómeno es estable; los números por-día de
   los días compartidos no son comparables 1:1 porque la base v1 cambió (ver 2).
2. **La tabla v1-compat se encogió entre censos**: 252,785 filas evidence
   (Z4, Aug 18) → 113,957 (hoy). Dos causas medidas: (a)
   `topic_members.signal_id REFERENCES signals_v2 ON DELETE CASCADE`
   (migración 057:8) — la poda de retención de señales arrastra membresías
   (la base caliente pasó de min-timestamp Aug 5 en el Z4 a Aug 13 hoy: la
   poda alcanzó); (b) las dos nocturnas fallidas no repusieron filas nuevas.
   El min `assigned_at` v1 (Aug 13 10:14Z) coincide con el min timestamp de
   retención (Aug 13 10:10Z) — consistente con (a).
3. **El delta del día 19 se mide contra un v1 enfermo** (nocturnas caídas,
   §0.7). No leer "+42.8pp" como el edge de u2 contra el motor sano; contra
   un v1 a su tasa típica (~8.7%) el union del día 19 seguiría ≈43.9% pero
   el solape dejaría de ser 0.
4. **El juicio de §4 es olfato, no gold**: n=40, un juez, sin court, sin
   segundo anotador. El mandato de M1-A0 lo declara así; el gold es del
   M1-GATE pre-registrado.
5. **matched del OR hoy = 86 = el del Z4** — pero los conteos sin-historia
   difieren en 1 por asignaciones posteriores al censo del 18 (clase Z4 §7).
6. **`assigned_at` de unified-v2 no es historia de corridas**: el
   DELETE+rebuild borra el rastro; la vitalidad de corridas viene del log del
   runner (96 éxitos / 9 fallas), no de la tabla.
7. **Los conteos u2 dentro de la ventana excluyen sus 2,018 señales de
   Aug 20** (fuera de los 7 días declarados); están contadas en §1 y en el
   slice de §3.

---

*Companion de datos: `2026-08-20-m1a0-unified-v2-coverage.json` (tablas
por-día, breakdown de `topic_members` por engine/rol, muestra de 40 con
headlines/labels/confianzas, testigos, sanity checks). Script:
`backend/scripts/m1a0_unified_v2_coverage.py`. Cero escrituras a la base;
cero recomendaciones — el arco lo decide el M1-GATE + Pedro.*
