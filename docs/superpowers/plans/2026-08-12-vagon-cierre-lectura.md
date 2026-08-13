# Vagón de cierre — los hallazgos del juez ciego, implementados — 2026-08-12

**Fuente**: `docs/research/gold/2026-08-12-brief-blind-judge.md` (T3.4 PARTIAL).
El concepto pasó; estos son los defectos que la lectura encontró. Regla:
pathspec-only, TDD, browser-verify; al aterrizar todo → deploy → **re-juez en
día SANO** (tras la noche autónoma limpia — jamás juzgar durante brownout).

## C1 · La última guarida de la clase N23 — el Brief viste outages de veredicto
*"'No story cleared the quality gate' junto a un console lleno de historias =
la copy de honestidad vistiendo un outage de principio editorial."*
Secciones 01/03 + tile "Coverage gaps: 0": distinguir **gate-juzgó-vacío**
(dato servido, cero filas) de **lane-no-respondió** (fetch falló/timeout) —
el segundo dice "la lane no respondió; el veredicto del gate es desconocido"
y el tile sirve "—" + razón, jamás un 0 fabricado. Testigo congelado: fetch
que falla → jamás la frase "cleared the quality gate".

## C2 · Coherencia de sentimiento (medir primero)
Tres escalas en una pantalla sin puente: header "−0.49 ±1" · panels "GDELT
tone −10..+10" (Yemen −10.0 exacto = olor a clipping, "Jordan −0.0" como
positivo) · Editor's Analysis (−0.20/+0.06) contradiciendo la tabla de al
lado. + chip "NLP 100%" bajo footer "GDELT tone". TRAZA cada número a su
fuente (V4-style), luego: una escala nombrada por superficie con puente
visible ("−4.9 en la escala del panel"), provenance chip que diga la verdad,
clipping declarado ("saturado al piso de la escala"), y el Analysis citando
la MISMA base que los panels o nombrando la suya.

## C3 · Editor's Analysis honesto
*"La única pieza editorializando, y sin etiquetar como opinión."* Etiqueta
visible (AI-interpretación sobre agregados nombrados) + constrain del prompt:
solo claims con número citable del payload (la disciplina glass-box ya
existente, endurecida) + fix del flicker entre reloads (race de caché).

## C4 · La puerta país no eyecta
*"Click en un tile → terminal oscura sin camino de vuelta. Whiplash total."*
Tiles de Heating Up + búsqueda de país abren la CARPETA país con breadcrumb
puesto (la maquinaria P2 existe — es cambiar el destino del click), no el
console crudo. El breadcrumb ES el camino de vuelta.

## C5 · Móvil: Lens/Live muertos + freeze
Reproducir a 375px contra prod: tabs resaltan pero el contenido no cambia y
la página se congela (clase tormenta-429 — los chips de trail/WorkbenchPanel
cerraron parientes; verificar si esto ya murió con ellos o tiene causa
propia). Fix + browser-verify.

## Fuera del vagón (dueño asignado)
Mobiliario vacío bajo outage (MOST ACTIVE/SOURCES/BY THEME headers sin nada,
mapa gris) → cae con C1 (la misma distinción). Country editions eternas bajo
brownout → V6 ya deployado, re-verificar en día sano. Re-juez = C7, tras la
noche limpia.
