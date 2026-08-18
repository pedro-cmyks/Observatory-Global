# Z4 — Censo de lo no-asignado: qué fracción del corpus servible no se vuelve historia

**Medido**: 2026-08-18 18:56Z (el snapshot nocturno del 18 ya había corrido:
el día 17 tuvo su pasada de clustering). **Mandato**: plan de identidad Z4
(`docs/superpowers/plans/2026-08-14-plan-identidad.md`) — la DISTRIBUCIÓN,
no los casos; atribución clustering-recall vs assignment-lane; los 3
testigos del 14 re-medidos. **Cero fixes propuestos** — números y
atribución; la decisión es de Pedro.
**Script**: `backend/scripts/z4_unassigned_census.py` (READ-ONLY,
`statement_cache_size=0`, `SET LOCAL statement_timeout='110s'` por
transacción, walk por chunks de id reanudable — el plan por índice de
timestamp midió >110s por statement ese mismo día y fue descartado; los
joins corren del lado del cliente: `topic_members` completo son ~300k
filas). **Datos**: `2026-08-18-z4-unassigned-census.json` (companion).

---

## 0 · Números de cabecera

1. **92.2% del corpus servible de 7 días no se vuelve historia** — 717,874
   de 778,518 señales servibles (Aug 11–17 UTC) sin membresía a ningún
   `dynamic-topic-%`. Sin topic ALGUNO (paridad exacta con el protocolo del
   14, incluye categorías atlas): 87.5%.
2. **Política: 91.1% sin historia** — 21,417 de 23,508 señales asignadas
   por el propio motor a 28 categorías políticas. En el subconjunto
   `gate_kept` (verificado ~90% precisión): 4,385 de 5,033 = **87.1%**.
3. **Por país el piso es 80.9% y el techo 98.8%** (GR el mejor, RS el
   peor de los top-30). CO: **87.9% sin historia** pero 58.2% sin topic —
   la brecha más grande del top-30: ~30% del corpus servible de CO vive en
   una categoría atlas sin pertenecer a ninguna historia. US 94.1%.
4. **Atribución con las taus del propio motor: el patrón es
   assignment-lane, no clustering-recall** — de 1,050 no-asignadas
   muestreadas (con embedding), **0 (0.0%)** carecen de historia activa a
   distancia asignable (<0.82) y **88%** tienen una historia activa a
   ≥0.88, la distancia a la que el motor declara "misma identidad". El
   bucket ≥0.88 contiene DOS modos (receipts en §4): la historia exacta
   existe y la señal quedó fuera, y el vecino-más-cercano es una historia
   incorrecta (la dispersión argmax otra vez). Caveat de compresión e5
   declarado en §8.
5. **Los testigos reproducen**: espriella frozen 67/71 sin historia (ruta C:
   60/72), golán 5/5 (ruta C: 10/10 — dirección exacta, ventana corta
   distinto), ungrd 10/11. El OR protocolario: 81/86 = **94% sin historia**
   (protocolo del 14: 77/84 = 92%). Espriella sigue vivo 4 días después:
   65/66 sin historia en las últimas 24h del censo.

---

## 1 · Poblaciones declaradas (disciplina ingest_basis)

Ventana: **7 días UTC completos, 2026-08-11 → 2026-08-17** sobre
`signals_v2.timestamp` (la base del protocolo del 14; NO `created_at`, NO
`assigned_at`). Retención medida: `MIN(timestamp) = 2026-08-05T10:10Z` — la
ventana entera está dentro de la base caliente. Existen filas con timestamp
FUTURO (max 2026-09-04, pubdates RSS rotos); quedan fuera por construcción.

| población | definición |
|---|---|
| **P0 total** | filas de `signals_v2` con `timestamp` en `[día, día+1)` UTC |
| **P1 servable** | P0 ∧ `headline IS NOT NULL` ∧ no-junk según el filtro del propio motor (`is_junk_headline`, `app/services/research_semantic.py:381` — `.shtml`/`^doc `/`^untitled`, plantilla bot "Digit:/In words:", ≥3 tokens con letra — traducido a regex SQL; paridad SQL↔Python verificada: 0 desacuerdos en 1,997 muestreadas) ∧ `source_family <> 'social'` (guarda F2: social nunca siembra clusters) |
| **P2 política** | P1 ∧ ∃ fila en `signal_topic_assignments` (cualquier `method`, cualquier gate) hacia una de las 28 categorías políticas declaradas (§5) |

**"Asignado" (paridad con el protocolo del 14)** — `topic_members` con el
MISMO filtro de serving de `query_verbs.py` (`_MEMBER_FILTER`):
`role='evidence' AND engine_version='v1-compat' AND quarantined IS NOT
TRUE` (env `ATLAS_TOPIC_MEMBERS_ENGINE_VERSION` ausente → default
v1-compat, verificado). Dos niveles:

- **`assigned_any`** = CUALQUIER membresía (dynamic o atlas) — la
  definición exacta del "sin topic" del protocolo.
- **`assigned_story`** = membresía a `dynamic-topic-%` — **"se vuelve
  historia"**. Solo-categoría NO cuenta como historia.

`gate_kept` NO se filtra en la membresía (paridad exacta con el protocolo).

Población de `topic_members` al momento del censo (censo propio, tabla
completa): v1-compat/evidence 252,785 filas (172,236 dynamic) ·
unified-v2/evidence 37,709 (coexiste, NO servido, NO contado) ·
movement/discussion/mood aparte.

## 2 · Taus vigentes (del motor, con cita — no inventadas)

| tau | valor | fuente | qué decide |
|---|---|---|---|
| `MATCH_THRESHOLD` | **0.88** | `backend/scripts/project_dynamic_topics.py:42` | centroide de cluster ↔ identidad existente (misma historia) |
| `DEFAULT_ASSIGN_THRESHOLD` | **0.82** | `backend/scripts/build_unified_topics.py:62` | señal ↔ centroide de topic (la única tau señal-nivel del motor) |
| `CENTROID_MATCH_THRESHOLD` | **0.85** | `backend/scripts/snapshot_emergent_topics.py:57` | resurrección por match de centroide |
| `ANCHOR_THRESHOLD` | **0.93** | `backend/scripts/project_dynamic_topics.py:55` | guarda de ancla (no usada aquí) |

**Buckets de atribución** sobre `max cos(vec e5 de la señal, centroide)` —
espacio e5 crudo (multilingual-e5-base, verificado en `signal_embeddings.
model`), el mismo de `dynamic_topics.centroid_vec`:

- **≥ 0.88** → clase **assignment-lane**: existe una historia activa que el
  propio motor llamaría la misma identidad; el pipeline no adjuntó.
- **[0.82, 0.88)** → banda asignable (sobre la tau señal-nivel).
- **< 0.82** → clase **clustering-recall**: ninguna historia activa a
  distancia asignable; habría tenido que FORMARSE una nueva.
- **sin embedding** → inanición del embed-lane (medida aparte).

Matiz declarado: en v1-compat una señal nunca se compara individualmente a
0.88 — entra por clustering y el CLUSTER matchea identidad. El bucket ≥0.88
es la operacionalización señal-nivel más cercana. Universo de centroides:
**3,607 historias activas no-umbrella no-junk** (primario); secundario
activas+candidatas no-junk = 7,103.

## 3 · Por día (UTC)

| día | total | servable | sin historia | % sin historia | sin topic (parity) | % | embedded % | política | pol. sin historia | % |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-11 | 132,403 | 121,290 | 110,225 | 90.9% | 104,244 | 85.9% | 59.1% | 3,818 | 3,462 | 90.7% |
| 2026-08-12 | 106,742 | 97,898 | 89,331 | 91.2% | 84,623 | 86.4% | 97.7% | 2,958 | 2,662 | 90.0% |
| 2026-08-13 | 129,484 | 120,572 | 110,800 | 91.9% | 105,884 | 87.8% | 96.5% | 3,289 | 2,996 | 91.1% |
| 2026-08-14 | 147,045 | 135,514 | 124,977 | 92.2% | 118,008 | 87.1% | 95.6% | 5,041 | 4,593 | 91.1% |
| 2026-08-15 | 95,985 | 86,652 | 79,680 | 92.0% | 74,979 | 86.5% | 94.9% | 2,234 | 2,012 | 90.1% |
| 2026-08-16 | 90,777 | 81,944 | 75,541 | 92.2% | 71,850 | 87.7% | 93.0% | 2,092 | 1,905 | 91.1% |
| 2026-08-17 | 147,448 | 134,648 | 127,320 | 94.6% | 121,684 | 90.4% | 92.3% | 4,076 | 3,787 | 92.9% |
| **7d** | **849,884** | **778,518** | **717,874** | **92.2%** | **681,272** | **87.5%** | 89.4% | **23,508** | **21,417** | **91.1%** |

- La fracción es **estable día a día (90.9–94.6%)** — no es un artefacto de
  un día malo ni del lag de la última noche (el 17 ya tuvo su pasada
  nocturna; su 94.6% es apenas +2.4pp sobre la media).
- Política `gate_kept` 7d: 5,033 señales, 4,385 sin historia = **87.1%** —
  ni siquiera la relevancia verificada al 90% de precisión cambia el orden
  del número.
- Embedded del día 11 = 59.1% (vs 92–98% después): la poda de
  `signal_embeddings` alcanza al día más viejo de la ventana. Afecta el
  muestreo de atribución (exige embedding), no los conteos.

## 4 · Por país (top 30 por volumen servable 7d + CO)

| país | servable 7d | sin historia | % sin historia | sin topic (parity) % | embedded % | política | pol. sin historia % |
|---|---|---|---|---|---|---|---|
| US | 115,260 | 108,466 | 94.1% | 87.9% | 86.4% | 4,180 | 94.3% |
| GB | 44,196 | 41,404 | 93.7% | 85.5% | 75.0% | 1,221 | 95.4% |
| IN | 40,826 | 37,864 | 92.7% | 88.0% | 91.4% | 1,554 | 90.6% |
| RU | 35,865 | 32,009 | 89.2% | 86.7% | 91.6% | 1,130 | 86.8% |
| DE | 30,866 | 29,498 | 95.6% | 93.8% | 92.3% | 463 | 93.3% |
| IT | 26,697 | 24,929 | 93.4% | 89.9% | 92.0% | 387 | 92.0% |
| TR | 24,140 | 22,778 | 94.4% | 92.0% | 92.8% | 458 | 90.4% |
| ES | 23,603 | 21,592 | 91.5% | 87.1% | 93.4% | 663 | 86.0% |
| ID | 22,852 | 20,328 | 89.0% | 81.5% | 88.7% | 225 | 92.4% |
| BR | 18,359 | 17,040 | 92.8% | 90.2% | 95.0% | 451 | 94.7% |
| UA | 18,036 | 15,464 | 85.7% | 82.4% | 91.8% | 858 | 87.2% |
| CN | 17,089 | 16,464 | 96.3% | 93.1% | 87.3% | 322 | 96.0% |
| AU | 16,380 | 15,143 | 92.4% | 87.0% | 73.3% | 829 | 97.7% |
| IR | 16,333 | 14,906 | 91.3% | 86.4% | 88.5% | 1,362 | 93.0% |
| CA | 15,623 | 14,531 | 93.0% | 82.4% | 89.7% | 472 | 93.9% |
| FR | 15,189 | 13,829 | 91.0% | 88.3% | 94.2% | 302 | 90.1% |
| MX | 14,229 | 13,523 | 95.0% | 91.0% | 92.4% | 294 | 93.9% |
| GR | 13,320 | 10,771 | **80.9%** | 78.2% | 94.3% | 120 | 82.5% |
| **CO** | 12,125 | 10,656 | **87.9%** | **58.2%** | 83.4% | 215 | **94.9%** |
| KR | 12,075 | 11,640 | 96.4% | 95.3% | 82.5% | 189 | 98.4% |
| AR | 11,649 | 10,569 | 90.7% | 88.3% | 94.9% | 112 | 93.8% |
| IL | 10,866 | 9,929 | 91.4% | 85.6% | 91.2% | 891 | 91.2% |
| VN | 9,257 | 8,668 | 93.6% | 92.6% | 88.0% | 56 | 98.2% |
| RO | 8,590 | 7,749 | 90.2% | 88.8% | 94.0% | 105 | 89.5% |
| JP | 7,951 | 7,230 | 90.9% | 87.2% | 88.7% | 104 | 94.2% |
| NG | 7,201 | 6,254 | 86.8% | 81.3% | 93.6% | 819 | 81.6% |
| SE | 6,813 | 6,505 | 95.5% | 92.0% | 93.1% | 120 | 95.0% |
| RS | 6,621 | 6,544 | **98.8%** | 96.4% | 95.2% | 114 | 98.2% |
| PL | 6,531 | 6,249 | 95.7% | 94.2% | 92.5% | 105 | 84.8% |
| EG | 6,445 | 5,580 | 86.6% | 85.4% | 96.0% | 99 | 82.8% |

- El rango es estrecho: **todos los top-30 entre 80.9% y 98.8%** sin
  historia. No hay ningún país donde la mayoría del corpus servible se
  vuelva historia.
- **CO es el outlier de la BRECHA parity↔story**: 58.2% sin topic vs 87.9%
  sin historia — 29.7pp de señales que viven en una categoría atlas
  (terremoto → `earthquake-volcano-disaster`) sin pertenecer a ninguna
  historia. El siguiente en brecha es CA (10.6pp). El terremoto hizo que la
  lane léxica capturara masivamente PARA LA CATEGORÍA lo que el clustering
  no convirtió en membresía de historia.
- La política de CO: **94.9% sin historia** — peor que su corpus general
  (87.9%), consistente con "el 83% de la política de un país no se vuelve
  historia" del plan (aquél era otro corte; la dirección se confirma y es
  peor).

## 5 · Criterio "política" (declarado)

`P2` = señal con fila en `signal_topic_assignments` hacia cualquiera de
estas 28 categorías (`atlas_topics.slug`, resueltas a ids en vivo):

armed-attacks-security-incidents · armed-conflict-escalation ·
bangladesh-domestic-affairs · constitutional-institutional-crisis ·
corruption-investigation · disinformation-influence-operation ·
election-administration-voting · election-legitimacy-dispute ·
elections-and-political-campaigns · elections-and-voting ·
elections-political-campaigns · forced-displacement · fuel-subsidy-unrest ·
german-domestic-politics · greek-politics · humanitarian-access-conflict ·
india-diplomacy · international-diplomacy · labor-strike-disruption ·
migration-border-pressure · press-freedom-crackdown ·
romanian-politics-and-governance · sanctions-diplomatic-pressure ·
student-youth-protest · telecom-internet-shutdown · turkish-politics ·
us-redistricting-and-voting-rights · vietnam-politics-governance

Es el criterio del PROPIO motor (lane léxica: 25,925 asignaciones/6,235
gate-kept · lane embedding: 24,012/4,717 — sobre estos topic_ids, tabla
completa). Advertencia: el "77/84 políticas" del protocolo del 14 NO usó
clasificador — "políticas" era la glosa de los tres needles. Aquí ambas
cosas van por separado: testigos con needles exactos (§6), P2 con este
criterio.

## 6 · Atribución: ¿recall del clustering o assignment lane?

Muestreo con seed 229 sobre no-asignadas-a-historia servibles CON embedding
(sesgo declarado en §8.3). Max cos señal↔centroide, espacio e5 crudo.

| frame | n | ≥0.88 (lane) | 0.82–0.88 (banda) | <0.82 (recall) | p50 | p90 | vs activas+candidatas: ≥0.88 / banda / <0.82 |
|---|---|---|---|---|---|---|---|
| global no-asignadas | 1,050 | 923 (**88%**) | 127 (12%) | **0 (0%)** | 0.9064 | 0.9415 | 1018 / 32 / 0 |
| CO no-asignadas | 300 | 295 (**98%**) | 4 (1%) | 1 (0%) | 0.9305 | 0.9558 | 298 / 2 / 0 |
| política no-asignadas | 400 | 355 (**89%**) | 45 (11%) | 0 (0%) | 0.9058 | 0.9403 | 390 / 10 / 0 |
| **control: asignadas** | 250 | 247 (99%) | 3 (1%) | 0 (0%) | **0.9401** | 0.9818 | 250 / 0 / 0 |

**Lectura (por las definiciones del propio motor):**

- **La clase clustering-recall es virtualmente vacía**: 0 de 1,050 señales
  no-asignadas carecen de una historia activa a distancia asignable
  (<0.82). Con candidatas incluidas, también 0. Por las taus vigentes, "no
  existe historia cerca" casi nunca es verdad.
- **El 88% cae en la clase assignment-lane**: una historia activa existe a
  la distancia (≥0.88) que el motor mismo usa para declarar "misma
  identidad", y la señal no está dentro.
- **El control separa poco**: asignadas p50 0.9401 vs no-asignadas p50
  0.9064 — 99% vs 88% en ≥0.88. La distancia al centroide más cercano NO
  distingue asignadas de no-asignadas; lo que difiere es si el pipeline
  las adjuntó.
- **El bucket ≥0.88 tiene dos modos** (receipts abajo): (i) la historia
  EXACTA existe y la señal quedó fuera; (ii) el vecino más cercano es una
  historia INCORRECTA — la dispersión argmax documentada el 07-30, visible
  de nuevo. Separar (i) de (ii) requiere juicio de labels (court /
  hand-check), fuera del alcance de Z4; ambos modos son fallas de
  identidad, no ausencia de historia formable.

**Receipts (top max-cos de cada frame, sin curar):**

Global no-asignadas:
- 0.9897 [VN] "Tổng Bí thư… hội đàm với Thủ tướng New Zealand" → dt-11782 "State Visit to Australia and New Zealand" *(modo i: historia exacta)*
- 0.9854 [RU] "Putin threatens retaliation for western seizures…" → dt-12876 "Putin Threatens Retaliation" *(modo i)*
- 0.9821 [CO] "Terremoto en Colombia: ascienden a 265 los muertos…" → dt-529 "Ceuta Migrant Crisis" *(modo ii: vecino falso)*
- 0.9748 [GB] "Lucy Davis… diagnosticada con cáncer terminal…" → dt-12886 "Lucy Davis Cancer Announcement" *(modo i)*
- 0.9740 [CO] "Suben a más de 280 los muertos por el terremoto de Colombia…" → dt-523 "Venezuela Earthquake Death Toll" *(modo ii: historia gemela mal geografiada)*

CO no-asignadas — las cinco son el terremoto, y el argmax se dispersa en
CUATRO identidades distintas (la enfermedad del plan, medida en vivo):
- 0.9900 → dt-12742 "Colombia Earthquake Death Toll" *(la historia correcta existe)*
- 0.9822 / 0.9812 → dt-248 "Venezuela Earthquake Death Toll"
- 0.9821 → dt-529 "Ceuta Migrant Crisis"
- 0.9805 → dt-8603 "Kumamoto Earthquake Death Toll"

Política no-asignadas:
- 0.9894 [NE] "American missionary released from captivity…" → dt-13104 "US Missionary Freed in Niger" *(modo i)*
- 0.9868 [KP] "South Korea fired warning shots…" → dt-1619 "North Korea Missile Launch" *(vecino same-theatre)*
- 0.9766 [KR] "Trump'tan Güney Kore'ye sert tepki…" → dt-2843 "US Iran Tensions" *(vecino same-theatre)*

**Embed-lane**: 89.4% del corpus servible 7d tiene embedding (§3). La
inanición del embed-lane NO es el cuello: el 10.6% restante se concentra en
el día más viejo (poda) y en AU/GB (73–75%).

## 7 · Testigos del 14 re-medidos

Needles con paridad exacta `query_verbs.like_needle`: `%espriella%`,
`%golán%`, `%ungrd%` sobre `lower(headline) LIKE` (acentos preservados).
Ventanas: **frozen** `[2026-08-13T15:00Z, 2026-08-14T15:00Z)` (aproximación
declarada de la corrida de ruta C, commit 2026-08-14T14:46Z) y **last24h**
(24h antes del censo, Aug 17 18:56Z → Aug 18 18:56Z).

| testigo · ventana | matched | sin topic (parity) | sin historia | ruta C / protocolo (14-ago) | ¿reproduce? |
|---|---|---|---|---|---|
| espriella · frozen | 71 | 57 (80%) | **67 (94%)** | 72 matched, 60 sin topic (83%) | **sí** (Δ1 matched, Δ3pp parity — corte de ventana + asignaciones posteriores) |
| golán · frozen | 5 | 5 (100%) | 5 (100%) | 10 de 10 sin topic | **sí en dirección exacta** (matched 5 vs 10: el corte de 24h de ruta C difiere; el 100% sin topic reproduce) |
| ungrd · frozen | 11 | 5 (45%) | 10 (91%) | 9 señales (sin split medido) | n/a — primer split; la asignación es a CATEGORÍA (earthquake-volcano n=5), no a historia |
| OR · frozen | 86 | 66 (77%) | **81 (94%)** | protocolo: 84 matched, 77 sin topic (92%) | **sí a nivel historia** (94% vs 92%); parity bajó 92%→77% — ver nota |
| espriella · last24h | 66 | 37 (56%) | **65 (98%)** | — | el patrón PERSISTE 4 días después |
| golán · last24h | 1 | 1 | 1 | — | el tema se apagó en el corpus |
| ungrd · last24h | 5 | 3 | 5 | — | ídem |

**Nota sobre la caída de parity (92%→77% en el OR congelado)**: las
landing de hoy muestran a `earthquake-volcano-disaster` (17 membresías),
`dynamic-topic-522` "ONU Estima Afectados Terremotos Venezuela" (candidate,
4) y `dynamic-topic-4249` "Barrio Lindo Fire" (candidate, 1) — asignaciones
que llegaron DESPUÉS de la corrida del protocolo (el classifier corre cada
30 min y las pasadas nocturnas siguieron tocando el 13–14). Lo que el
tiempo extra compró fue membresía de CATEGORÍA y candidatas, casi nada de
historia: **el número a nivel historia (94%) es igual o peor que el del
14**. Donde aterrizó la Espriella congelada: 12 en la categoría terremoto,
4 en una candidata de terremoto de VENEZUELA, 1 en armed-conflict — el modo
"aterriza en la historia equivocada" de ruta C, reproducido.

**Atribución de los testigos**: los 81 no-asignados-a-historia del OR
congelado con embedding: **81/81 (100%) a ≥0.88 de una historia activa**
(p50 0.9176). Espriella last24h: 58/58 a ≥0.88. Ninguno en la clase
clustering-recall.

## 8 · Caveats (todos declarados, ninguno cosmético)

1. **Compresión del coseno e5 crudo**: medido antes en esta casa — la
   recalibración de taus (2026-07-05, `docs/research/l3-research-lane/
   2026-07-05-tau-recalibration.md`) encontró junk p50 0.865–0.887 POR
   ENCIMA de taus 0.80–0.84, y el bakeoff (2026-07-31) documentó la escala
   comprimida del espacio. A 0.82, "hay algo cerca" es casi siempre verdad;
   por eso este artefacto reporta percentiles + control + receipts, y la
   clase "lane" se define por las taus DEL MOTOR (el mandato), no por una
   tau discriminativa nueva. La conclusión robusta al caveat: **la
   distancia no separa asignadas de no-asignadas** (0.9401 vs 0.9064 p50) —
   el cuello no es "no existe historia formable cerca" bajo ninguna de las
   taus que el motor usa hoy.
2. **Ventana congelada aproximada**: ruta C no registró su ventana exacta;
   uso 24h terminando 15:00Z del 14 (commit 14:46Z). Los deltas de matched
   (71 vs 72; 5 vs 10) son consistentes con ese corte.
3. **El muestreo de atribución exige embedding** (sesgo declarado): cubre
   el 89.4% del corpus servible; el día 11 cae a 59.1% por la poda de
   `signal_embeddings`. Los conteos de §3–§4 NO tienen este sesgo.
4. **Membresías ≠ señales** en las landing (una señal puede ser evidencia
   de varios topics) — la nota del protocolo, vigente aquí.
5. **Borde de población del walk**: el scan arranca en el primer id con
   `created_at ≥ 2026-08-09` (holgura de 2 días bajo el inicio de ventana).
   Filas creadas antes del 9 con timestamp en ventana quedarían fuera —
   clase acotada por la holgura, esperada ~0 (GDELT ingesta near-realtime).
6. **Señales creadas durante el censo** (id > max al inicio) no entran en
   los sets de embedding/tm de los testigos last24h — subconteo posible de
   "embedded" en ese frame, no de matched.
7. **unified-v2 coexiste en `topic_members`** (37,709 filas evidence) y NO
   se cuenta — solo v1-compat sirve (paridad con serving y con el
   protocolo).
8. **Día 17**: su pasada nocturna (02:30 del 18) ya había corrido al
   momento del censo; su 94.6% no es lag puro, aunque las señales tardías
   del 17 llevan una sola pasada.

---

*Método completo y estado intermedio en el script (reanudable; el walk de
849,884 filas corrió en chunks de 60–202k ids, cada statement < 110s).
Companion de datos: `2026-08-18-z4-unassigned-census.json` (tablas
completas día×país de 240 países, breakdowns, testigos, atribución).*
