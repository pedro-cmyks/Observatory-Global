# Plan de acción — la capa de identidad — 2026-08-14

**Origen**: la investigación de tres rutas
(`docs/research/investigations/2026-08-14-colombia-ruta-{a,b,c}-*`) y los dos
diagnósticos que salieron de la pantalla de Pedro
(`docs/research/recall-229/2026-08-14-duplicate-live-stories.md`).

**Tesis del plan, medida no supuesta**: la ingesta está sana, el serving ya no
miente, y **la identidad es el cuello de botella del producto**. Un evento
existe como nueve identidades; el 83% de la política de un país no se vuelve
historia; el predicado de etiquetas bloquea fusiones que el coseno ya aprobó.

---

## Ya cerrado hoy (no vuelve al plan)

| Defecto | Fix | Commit |
|---|---|---|
| "323 lifetime" era una suma corrida sobre 17 pasadas que doble-cuenta | `countBasis: cumulative_snapshots` + `snapshotCount`; "18 · last 7d" → "latest pass Aug 12" | `d0b5a678` `26a1d9d1` |
| "20 sources" era la longitud de un slice `[:20]` | conteo real de dominios distintos (36 en 37 recibos) + base declarada | idem |
| `source_count` de la lista satura en 24 y se queda viejo tras merge | recuento sobre la evidencia unida; base por lane | idem |
| El título "Earthquake" era una historia mutilada por `stripCountrySuffix` | tres reglas de rechazo del corte + badge `◫ CATEGORY` con conteo declarado | `7387ff44` |

Desplegado y verificado en vivo sobre dt-242.

---

## Z1 · El 8º gate (el predicado) — **es la palanca, y ya está en vuelo**

La fusión `dt-242 ↔ dt-12927` **pasó el gate de coseno** y la bloqueó el
predicado de etiquetas: *"7.4-Magnitude Earthquake Kills Dozens in Colombia"*
vs *"Magnitude 7.4 Earthquake Strikes Colombia"* → SeqMatcher **0.7111 =
incompatibles**. Es exactamente el defecto que el 7º gate nombró y que el 8º
(Unicode-norm + contención de tokens de sujeto) fue pre-registrado para curar.

**Acción**: correr el 8º gate contra este caso como testigo congelado antes de
su veredicto. Si pasa su barra, este par es la primera fusión que gana.
Dueño: el reloj de condenación / programa de landing. **No abrir frente nuevo.**

## Z2 · Regla B (consenso de hijos) — detect-only, con gate propio

De Y2, pre-registrada: si ≥2 hermanos medidos de una historia son hijos
activos del mismo umbrella, es candidata a pertenecer a ese umbrella.
**Habría cazado este caso** (3 de 11 hermanos de dt-242 son hijos de
dt-12927). Cero embeddings nuevos, cero LLM, esquiva el centroide diluido.

- Barra: ≥80% de aciertos sobre 20 candidatos aleatorios hand-check. Debajo:
  KILL.
- **Detect-only aun pasando** — escribir membresía exige su propio gate.
- Corre DESPUÉS de Z1 (dos frentes de motor a la vez está prohibido por la
  regla del arco).

## Z3 · Los umbrellas son invisibles para los hermanos — decisión de diseño

`story.py:73-77` excluye `is_umbrella` del universo de candidatos: un umbrella
no puede sembrar ni ser devuelto. Por eso dt-12927 y dt-242 nunca se
encontraron pese a superar (0.6489) al hermano #1 vigente (0.6360).

**Pregunta a decidir (Pedro)**: ¿un umbrella debe poder ser hermano? Mi
lectura: sí, pero **etiquetado como lo que es** ("familia de N historias"),
nunca presentado como una historia par. Es cambio de contrato de serving, no
de motor — vagón propio, tras Z1.

## Z4 · La política que no se vuelve historia — MEDIR primero

60 de 72 señales de "Espriella" sin topic; 10 de 10 del Golán sin topic; las
que aterrizan caen en "Earthquakes in Mexico" y en una reforma de pensiones
alemana. **Antes de tocar nada**: medir qué fracción del corpus servible queda
sin asignar por día y por país, y si el patrón es de recall del clustering o
de la lane de asignación. Artefacto medido → luego decidir.

## Z5 · Geografía del sujeto — el conjunct ya existe, falta cablearlo

Chip VE sobre historia colombiana; "doméstico" calculado contra Israel en una
decisión colombiana; recibos bielorrusos dentro de un hilo de Colombia. El
detector `label_geography_conflict` ya vive (agente B del arco de labels).
Acción: extender su uso del court al **serving de chips de país** y al cálculo
de self-voice por sujeto. Vagón de superficie, sin gate de motor.

---

## Orden de fuego

**Z1 (en vuelo, reloj propio) → Z2 (gate propio) → Z5 (superficie, paralelo
seguro) → Z4 (medición) → Z3 (decisión de Pedro).**

Nada de esto toca lifecycle sin su gate pre-registrado. La regla que ya nos
salvó nueve veces: la barra se congela antes de correr, y un KILL con
evidencia limpia vale más que un pase de cortesía.
