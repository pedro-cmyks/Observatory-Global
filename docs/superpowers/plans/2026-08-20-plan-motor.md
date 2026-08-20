# Plan de acción — mover el motor (2026-08-20)

**Origen: la evaluación honesta del 2026-08-20 (52/100; hace 5 semanas 50).
Diagnóstico: la forma le lleva kilómetros al motor — «more honest than it is
right» (juez run-4). La nota solo se mueve moviendo IDENTIDAD (40) y OPS (40).
La forma (80) ESPERA.**

Evidencia que ordena este plan: censo Z4
(`docs/research/recall-229/2026-08-18-z4-unassigned-census.md`), dev
click-parity (`docs/research/gold/2026-08-19-dev-click-parity.md`), juez run-4
(`docs/research/gold/2026-08-19-brief-rejudge-run4.md`).

---

## M1 · LA PALANCA — la assignment lane (arranca HOY)

**El hecho medido**: 92.2% del corpus servible no se vuelve historia, y la
clase clustering-recall está VACÍA — el 88% de las no-asignadas tienen una
historia activa a ≥0.88 (la distancia de «misma identidad» del motor). **Las
historias existen; el pipeline no adjunta.**

**Sospechoso #1 (medir antes de tocar)**: el serving lee `topic_members`
`engine_version='v1-compat'`; el build unified-v2 (nocturno, ≥0.82) adjunta
MÁS y **nunca se sirvió** — el cutover F4 lleva parametrizado desde julio
(`ATLAS_TOPIC_MEMBERS_ENGINE_VERSION`), gated en gold que nunca corrió.
Si unified-v2 ya cubre a los huérfanos del Z4, el fix es un flip con gate,
no código nuevo.

- **M1-A0 (hoy, read-only)**: sobre el set congelado del Z4 (81 testigos OR +
  la muestra de 1,050): ¿qué fracción tiene membresía unified-v2? ¿Qué
  fracción del corpus servible queda sin historia BAJO unified-v2? ¿Los dos
  modos (historia-exacta-fuera / vecino-falso) cómo se reparten allí?
- **M1-GATE (pre-registro aparte, barras congeladas antes de cualquier
  cambio)**: `docs/superpowers/specs/2026-08-20-assignment-lane-preregistration.md`.
- **M1-FIX**: lo que A0 diga — flip F4 con su gate, o extensión de lane con
  el suyo. Nunca los dos frentes a la vez.

## M2 · Z1 — el predicado de etiquetas (el bloqueador de fusiones)

Ya diagnosticado (dt-242↔dt-12927 pasó coseno, lo mató SeqMatcher 0.7111).
Corre DESPUÉS de M1 (regla del arco: un frente de motor a la vez). El 8º gate
ya está pre-registrado.

## M3 · Los vagones del dev (chicos, paralelos seguros — no tocan motor)

- **F3-c**: el sello congeló coherencia ANTES de la pasada → ordenar pipeline
  (la pasada de coherencia precede al sello, o el sello mide en caliente).
- **F3-b**: retry del daily-pub 12s vs latencia real 7-23s en noche enferma.
- **Registro del tile WHY**: `surprise=2.5787` crudo en slot de lector →
  prosa (la regla del banco R1).
- **F3-d (decisión de diseño, no hot-fix)**: BACK desde console deja
  `?country=` en /brief — acarreo de foco vs sensación de no-elegido.

## M4 · El churn de índices, estructural (no otro reindex manual)

El bloat VOLVIÓ en 5 semanas y volverá: 130K señales/día con retención 7d
infla índices por diseño. Opciones a medir (EXPLAIN + tamaño, no opinión):
REINDEX CONCURRENTLY programado (mensual, nocturno, el script ya existe) ·
fillfactor · partición por día de signals_v2 (drop de partición = cero bloat,
pero cirugía mayor). Decisión con números; mientras tanto el reindex
programado semanal/mensual como control conocido. También: los DOS índices
trigram de headline (~630MB c/u) — chequeo EXPLAIN diurno para decidir si uno
sobra.

## M5 · Lectores reales (la única cura del 15 de mercado)

2-3 design partners humanos leyendo el Brief a diario una semana. Sin esto,
toda validación sigue siendo sintética y mi sesgo no tiene contrapeso. Los
instrumentos (juez, panel, dev-parity) quedan para regresión, no como
sustituto de humanos. **Decisión y reclutamiento: Pedro.**

## Lo que NO se hace ahora (la forma espera)

Banco R3, P2 mundo-céntrico, P3 página de historia, vagón de vocabulario,
autoUpdate del SW. Todo vivo en sus specs; nada avanza hasta que M1 mueva.

## Secuencia

**HOY**: M1-A0 (medición) + M3 en paralelo (no-motor) + cierre mecánico
pendiente (suite post-iCloud → F3-a commit → pushes).
**Tras A0**: pre-registro M1-GATE → veredicto de Pedro → M1-FIX.
**Luego**: M2 (Z1) → M4 con números → re-evaluación honesta (la meta:
identidad 40→60 en un mes; si no se mueve, el plan estaba mal y se dice).
