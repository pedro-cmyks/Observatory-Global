# Pre-registro (9º gate): estabilidad de label en LABELING-time — adopción

**2026-08-03 · Congelado ANTES de cualquier build (aprobado por Pedro). Sucesor
del 8º (`2026-08-03-landing-predicate.md`), cuyo KILL midió la escalera del
predicado agotada en la capa del join: la clase mayoritaria de bloqueo falso es
DIVERGENCIA DE FACETA ('Jens Spahn Leihmutterschaft' ↔ 'Jens Spahn Becomes
Father', cos 0.9995) — los labels no cargan la información del join. Este gate
mueve la palanca río arriba: que los labels de una misma historia NAZCAN
iguales. Movimiento post-resultados = inválido.**

## El mecanismo bajo prueba

**Adopción en labeling-time**: cuando el labeller etiqueta un cluster del
snapshot y existe un topic candidato cercano (cos ≥ TAU_ADOPT, congelado en el
harness ANTES del run, punto de partida el MATCH_THRESHOLD de producción), el
prompt de labeling — LA MISMA llamada que ya ocurre, cero llamadas extra —
recibe el label existente del candidato y decide: **ADOPTAR** (same-story) o
**NUEVO** (historia distinta). Un cluster que adopta lleva el label del topic
verbatim → los pares same-story quedan `compatible` por identidad de string →
la consolidación y el landing dejan de fallar por re-fraseo.

**Exclusión por construcción (la advertencia §6 del 8º)**: candidatos con
`blob_confirmed_at` fresco, `label_status='failed'`, o `is_junk` NUNCA se
ofrecen para adopción — un blob adopta-todo porque sus recibos contienen todo;
la adopción solo puede heredar de identidades sanas.

## Medición (offline, replay — el pipeline no se toca hasta un GO)

Sobre las noches congeladas del programa: re-etiquetar con
adopción simulada (una llamada DeepSeek por cluster-con-candidato — costo de
MEDICIÓN one-time, no recurrente; en producción el costo extra es CERO por
diseño), luego re-correr el harness del 8º (arms A y B-p8) con los labels
adoptados. Fidelidad del harness debe reproducir o STOP.

## Gates congelados

| Gate | Barra |
|---|---|
| **G-ADOPCIÓN (nueva primaria-1)** | precisión de adopción: sobre una muestra juzgada de ≥60 adopciones (quote-gate, evidencia inline), falsa-adopción (unió historias distintas) ≤ **5%** — la semilla de black-hole es lo único peor que el statu quo |
| **G-BLOB-ADOPCIÓN (nueva)** | 0 adopciones desde topics blob-confirmados/failed/junk (verificado, no asumido) |
| **G-FALSE-BLOCK (heredada del 8º, ahora alcanzable)** | bloqueo-falso en pares same-story conocidos < **20%** con labels adoptados |
| **G-FOUNDING** | fundaciones de B-p8-adoptado ≤ **15%** de picks decidibles — tercera vez, no se mueve |
| **G-LANDING (primaria-2)** | ≥ ⌈⅔·scorables⌉ familias correctas Y estrictamente > producción, regla de auto-fundados del 8º |
| G-K2 / G-784 / G-FALSOS | heredadas idénticas (≥14/15 ≤2% · 0 · 0/1200) |
| **G-COSTO (diseño)** | el prompt de producción propuesto se incluye en el artefacto y demuestra cero llamadas adicionales por noche (la adopción vive dentro de la llamada de labeling existente) |

KILL = cualquiera falla → documentar y parar. GO = adopción entra al labeling
del snapshot nocturno flag-gateado (`ATLAS_LABEL_ADOPTION`) + consolidación+
landing entra flag-gateado → una noche medida → NAV-LOSS re-gate → lens.

## Herencias de método

Mindful M1 SIEMPRE (taskpolicy -b, secuencial, abort <15% RAM), read-only prod,
familias testigo + juez con quote-gate + spot-check humano, noches blackout
no-scorables, artefacto `2026-08-03-label-adoption.{md,json}` con juicios
inline. Lo ya refutado no se re-visita (predicados join-time, df-distintivo,
court-a-volumen, whitening, espacios).
