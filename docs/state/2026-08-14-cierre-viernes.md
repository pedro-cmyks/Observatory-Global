# Cierre viernes 2026-08-14 — tres frentes, un deploy, y un instrumento que se vigila solo

**Commits**: `3fd1f059` `ca117b19` (Z3) · `1e7420d5` (chrome-ES) · `0f7930f0` `994dfefb`
(query protocol). Fly desplegado, ambos refs empujados
(`eclipse-dramatic-moment` + `v3-intel-layer` → Vercel).

**Gate integrado**: backend **3490 passed / 17 skipped** · frontend **1939 tests /
155 files** · build limpio (node@24).

---

## 1 · Z3 — un umbrella ya puede ser hermano, servido como FAMILIA

`story.py` excluía `is_umbrella` del universo de candidatos. Por eso dt-242 y
dt-12927 nunca se encontraron **pese a que la matemática ya los había aprobado**
(0.6489 > 0.6360 del hermano #1 vigente).

Hermanos de dt-242, antes → después (prod, verificado en vivo):

| # | ANTES | AHORA |
|---|---|---|
| 1 | Venezuela EQ Death Toll .6360 | **Colombia Earthquake Kills 111** · familia 17 · .6686 |
| 2 | Earthquake Reports .6299 | **Colombia Declares Disaster** · familia 8 · **.6489** |
| 3 | **Incendio a Bruxelles** .5895 | Venezuela EQ .6360 |
| 5-6 | Japan / Peru | Earthquake in Colombia · Death Toll → 132 |

Efecto lateral que vale: **el hermano falso "Incendio a Bruxelles" se cayó**.

La honestidad quedó donde corresponde. El chip declara que la relación se midió
contra el **centroide agregado** de la familia — un claim más débil que un match
hoja-a-hoja — y el caveat va DESPUÉS del coseno, para que el recibo de cabecera
siga siendo el número que el ranker usó.

Control sin regresión: dt-2209 y dt-407 **byte-idénticos**; dt-385 cambió una
fila porque entró un umbrella a .7917 — eso es la función.

Decisión conservada: el **ancla** de un umbrella sigue resolviéndose vía su hijo
representante. Sembrarla en el centroide agregado habría borrado en silencio la
nota medida `umbrella_resolved_via_child`. Z3 cambia quién puede ser
**encontrado**, no quién ancla.

## 2 · Chrome en español — la puerta del lector

`lib/uiCopy.ts` sobre el store `pageLanguage` que ya existía (no una segunda
fuente de verdad). Los tests del catálogo imponen tres reglas de honestidad
mecánicamente sobre TODA llave: mismos placeholders, **mismos dígitos** (una
etiqueta en español no puede afirmar una medición que la inglesa no hizo), y
ningún `es` que sea copia del `en` — un cognado omite `es` en vez de duplicar,
así "tiene traducción" sigue significando algo.

El control vive en el **masthead del Brief**, no en Settings: Settings está
dentro del console, que un lector que no puede leer la página nunca alcanza.

Traducido completo: masthead + dateline · banners de frescura/mercados/caché/
offline · las seis tiles · tabs y encabezados de las tres secciones · lead y
todos sus estados vacíos · The Gap / What Is Rising · back-matter · puerta país
y edición país · método, colofón, error y carga · las tres tabs del teléfono.

**Dejado en inglés a propósito**: todo el console L2. Una terminal de analista a
medio traducir es peor que una honestamente en inglés.

Huérfanos declarados (no hechos a medias): `staleBanner`, `statPhrases`,
`briefVoices`, prosa de razones en `briefSections`, `sectionTranslation`,
`countryChips`, `PrintersMarks`, `BriefMarkets`. El patrón de parámetro `lang`
usado en `briefLanes`/`sentimentScale` es la plantilla para cerrarlos.

Riesgo de layout MEDIDO: el español crece la tira de instrumentos **+6.4%**
(881→937px) — ya es `overflow-x:auto`, la absorbe. **Cero** overflow horizontal
de página en ambos idiomas, a 375px y desktop. Cambio de idioma sin reload, el
scroll se sostiene (1400→1376→1400).

## 3 · Query Protocol v1 — preguntarle al sustrato

`POST /api/v3/query`. Cuatro verbos, **todos mediciones que Atlas ya hace**:
`identities_covering` (dos bases: miembros y etiqueta, cada identidad marcada
con cuál la encontró) · `receipt_geography` (país-sujeto / idioma / origen del
medio, **tres dimensiones separadas** — confundirlas ES el error de
ingest_basis) · `unclustered_signals` · `voice_mix` (reusa `services/voice_mix`
y `thread_voice` VERBATIM, así no pueden divergir del producto).

Las cuatro reglas del contrato, cada una con mecanismo:

- **ventana medida contra la retención REAL** (sondeo `MIN(timestamp)` por
  request). Prod, verificado: pedir 336h sobre ~9 días de corpus caliente
  responde `fully_covered: false · shortfall_hours: 110.3` y nombra el faltante.
  Es la misma mentira que "18 · last 7d", ahora **imposible por contrato**;
- base y población en toda respuesta;
- lane caída = razón NOMBRADA, y `degraded_result` **omite la llave `data`** —
  un verbo degradado es estructuralmente ilegible como cero medido;
- lo no medible se declara: `dynamic_topics` no tiene columna de país, así que
  la base-por-etiqueta es global y solo la de miembros está scoped.

### El doble cheque — corrido contra PRODUCCIÓN

`scripts/query_parity_check.py`. Ambos caminos van por HTTP contra el MISMO
deployment: se compara lo que se sirve, no dos rutas de código en un proceso que
podrían coincidir y estar ambas mal.

| | Defecto vigilado | Veredicto |
|---|---|---|
| C1, C2 | controles | **PASS** — coinciden campo por campo; el arnés es sano |
| D1 | fuentes topadas en 20 | **PASS** — 30 vs 75, base `receipt_sample`/97 recibos DECLARADA |
| D2 | "18 · last 7d" vs 323 | **PASS** — 12 `latest_snapshot` · 208 `cumulative_snapshots` · 32 miembros |
| D3 | una historia, nueve identidades | **FAIL** — 7 identidades vivas con la etiqueta *"venezuela earthquake death toll"*; el producto sirve 0 |
| D4 | chip VE sobre historia CO | **FAIL** — encabeza con **JP** un tópico cuyos recibos son 62% CO; **JP no aparece en ni un recibo** |

4 pass / 2 FAIL. Los dos que pasan son los que arreglamos esta semana. Los dos
que fallan son **Z1 (identidad)** y **Z5 (geografía del sujeto)** — y ya no
dependen de que alguien los note en una pantalla.

`exit 2` cuando NADA se midió: el instrumento aplicándose su propia regla. Un
chequeo que no midió no es un chequeo que pasó.

---

## Estado para el lunes

**Vivo y corriendo solo el fin de semana**: pipeline nocturno, reloj de
condenación (trigger 15% congelado, cada 3 noches), country-clock, poda +
recibos archivados, watchdog de sello (la pata nueva que vigila el PRODUCTO,
no el proceso).

**Abierto, con dueño y barra**:
- **Z1** — 8º gate del predicado de etiquetas. Es LA palanca: la fusión
  dt-242 ↔ dt-12927 pasó el coseno y la bloqueó SeqMatcher 0.7111. Reloj propio.
- **Z2** — regla de consenso de hijos, detect-only, gate propio. Corre DESPUÉS
  de Z1 (dos frentes de motor a la vez está prohibido).
- **Z5** — `label_geography_conflict` ya existe en el court; falta cablearlo al
  serving de chips de país. Es D4.
- **Z4** — medir qué fracción del corpus servible no se vuelve historia, por día
  y por país, antes de tocar nada.
- **Z0** — REFUTADO en su propia barra (mediana 0.9916 vs kill 0.98). Cerrado.

**Cuando vuelvas**: el juez ciego se suelta sobre un producto que ya carga
chrome en español, familias visibles, y un instrumento que grita cuando la
puerta miente. Los datos van a ser mejores porque el producto es mejor — no
porque le bajamos la barra.

**Residuo honesto**: `backend/app/services/brief_sections 2.py` sigue sin
trackear (copia de iCloud del 13 ago, DIFIERE del archivo real — no la borré sin
tu ojo). Y el bug pre-existente que el arco de i18n encontró de paso: el Brief
anida el toggle "Ver original" dentro del `<button>` del titular, que React marca
como error de hidratación. Chip abierto.
