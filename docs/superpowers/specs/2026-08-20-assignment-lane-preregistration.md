# M1-GATE — la assignment lane: barras congeladas ANTES de diseñar el fix

**Pre-registrado 2026-08-20, tras M1-A0
(`docs/research/recall-229/2026-08-20-m1a0-unified-v2-coverage.md`). El fix
NO está elegido; estas barras las debe pasar CUALQUIER fix que se proponga.
Regla de la casa, 11 veredictos honrados: la barra se congela antes, y un
KILL con evidencia limpia vale más que un pase de cortesía.**

## Lo que el A0 dejó probado (la premisa del gate)

- Las historias existen y el pipeline no adjunta: 93.0% del corpus servible
  7d sin historia (reproduce Z4), con historias activas a ≥0.88 para el 88%
  de las no-asignadas.
- **PERO adjuntar por distancia sola pone la historia equivocada**: 65%
  vecino falso en muestra a mano (n=40, seed 229); 59% incluso a confianza
  ≥0.90. El coseno no separa la historia correcta del vecino falso — la
  dispersión de argmax en vivo (la deuda US → "Q2 Earnings" mientras la
  misma corrida creaba la historia correcta).
- unified-v2 tal como corre hoy NO es el fix: foto de ~16h (DELETE+rebuild,
  40K señales), delta 7d −4.8pp. El flip F4 queda **KILL por medición**.

## Las barras (congeladas AQUÍ)

- **G-SALUD-PREVIA (precondición, no barra del fix)**: el gate solo se corre
  sobre una lane v1 SANA — ≥2 nocturnas consecutivas escribiendo R1 sin
  timeout (post-reindex 2026-08-20: 5,074→3,360 MB). Medir contra una lane
  enferma contamina todo (la lección del día-19 del A0).
- **G-PRECISIÓN (la barra que manda)**: muestra ciega a mano, n≥50, seed
  pre-declarada, de adjuntos NUEVOS del fix → **≥90% historia correcta**
  (sí; "dudoso" NO cuenta como sí). El A0 midió 17.5% con distancia sola:
  cualquier fix que no cambie el mecanismo de confirmación está muerto de
  entrada.
- **G-RECALL**: la fracción servible CON historia sube de 7.0% a **≥20%**
  (≈3×) en la ventana de 7 días, sin violar G-PRECISIÓN. Un fix que compra
  recall vendiendo precisión es el producto empeorando con mejores números.
- **G-RETENCIÓN**: lo adjuntado PERSISTE — un adjunto sobrevive hasta la
  poda de su señal, jamás una foto que se borra en la siguiente corrida.
- **G-TESTIGOS**: de los 80 huérfanos congelados (espriella 66 · golán 5 ·
  ungrd 10, ids en el JSON del Z4), **≥40 adjuntados a su historia
  CORRECTA** (juicio a mano contra headline). Son los casos que la
  investigación del 14 nombró; si el fix no los cura, no cura lo que
  importa.
- **G-NO-DAÑO**: cohesión media de topics activos no cae; junk activo sigue
  0; el court no reprueba más etiquetas que el baseline; blob-rate no sube;
  los counts servidos declaran su base (countBasis) sin regresión del
  contrato del 14.
- **Reversibilidad**: flag propio + ledger de estados previos (patrón
  tick-v2). Nada escribe en prod sin pasar TODAS las barras en sombra.

## Familias candidatas de fix (nombradas, NO elegidas — decisión de Pedro)

1. **Coseno + confirmación barata**: el candidato por distancia se CONFIRMA
   con señal ortogonal antes de adjuntar — entidades compartidas raras,
   contención de tokens de sujeto (el predicado del 8º gate/Z1), o el juez
   DeepSeek "¿misma historia?" acotado (el patrón que compró 91-93% de
   precisión en el over-merge). Costo por señal a medir ANTES.
2. **Argmax-familia**: el candidato no es el topic más cercano sino la
   FAMILIA (umbrella + hijos + hermanos del walk) — ataca la dispersión de
   argmax de raíz; requiere Z1/Z3 maduros.
3. **Retención de unified-v2 + confirmación**: convertir la foto en
   acumulado (INSERT incremental, no DELETE+rebuild) y pasar sus candidatos
   por la confirmación de (1). Reusa el build existente.

Cada familia, si se elige, corre en SOMBRA sobre la misma ventana y muestra
del A0 antes de tocar serving.

## Orden

1. G-SALUD-PREVIA (esta noche + mañana: ¿la nocturna escribió?).
2. Veredicto de Pedro sobre la familia.
3. Fix en sombra → las 6 barras → solo entonces serving.

---

## Addendum 2026-08-24 — familia elegida, precondición cumplida, calibración previa

Las barras de arriba quedan CONGELADAS como están; esto registra estado, no
las mueve.

- **Familia elegida: ① coseno + confirmación barata** (veredicto de Pedro,
  2026-08-24 — "empecemos con el voto de la familia del coseno").
- **G-SALUD-PREVIA: CUMPLIDA con margen** — 4/4 nocturnas post-reindex
  escribieron R1 sin timeout (snapshots 2026-08-21..24 verificados en
  `emergent_clusters` con conteos idénticos a los `R1 DONE` del log; 0
  QueryCanceledError; duración R1 9029s→5660s). Auditoría
  `docs/state/2026-08-24-health-audit.md`.
- **Calibración previa del confirmador** (el "costo por señal a medir ANTES"
  que la familia exigía): `backend/scripts/m1_confirmation_calibration.py`
  sobre la muestra A0 (n=40, seed 229, juicios a mano del 08-20) →
  - el juez DeepSeek "¿misma historia específica?" **no aceptó NINGÚN
    vecino falso** (0 de los 26 "no" a mano) y confirmó 3/40 del argmax
    único (2 sí + 1 dudoso);
  - las señales léxicas (P-NUEVO headline↔label, cobertura de tokens,
    entidades compartidas) casi no disparan solas — labels cortos y
    cross-language;
  - costo: 40 juicios en 8.7s, ~194 tokens/juicio ≈ **$0.0001/señal** —
    el costo NO es la barrera.
  Artefacto: `2026-08-24-m1-confirmation-calibration.json`.
- **La variante de la familia que va a sombra: top-K propone, el juez
  elige** (K=5, floor cos 0.80 sobre centroides activos — la mecánica del
  build u2). El confirmador sobre argmax-único hereda la dispersión de
  argmax (el juez rechaza correctamente al vecino falso y el adjunto se
  pierde); ofrecerle los K vecinos ataca la dispersión de raíz. Sonda:
  `backend/scripts/m1_topk_judge_probe.py`, artefacto
  `2026-08-24-m1-topk-judge-probe.json`.
- **G-TESTIGOS — nota de medibilidad (la barra no cambia)**: la poda de
  retención estuvo parada 08-20..24 (cascada del lock nocturno, ver
  auditoría) y eso PRESERVÓ a los 86 testigos; sus filas quedaron
  congeladas en `fixtures/2026-08-24-m1-shadow-fixture.json.gz` ANTES de
  destrabar el catchup que los podará. La barra se mide en sombra por
  replay del fixture (re-embed e5 del headline, determinístico; los
  testigos ya no tienen fila en `signal_embeddings`). El fixture también
  congela la muestra A0 con sus 40 embeddings.
