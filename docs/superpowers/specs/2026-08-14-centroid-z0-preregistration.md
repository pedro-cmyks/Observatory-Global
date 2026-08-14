# Z0 — el centroide roto: verificación y gate — PRE-REGISTRO

**Congelado ANTES de correr nada. Aprobado por Pedro 2026-08-14.**
Diagnóstico origen: `docs/research/recall-229/2026-08-14-centroid-not-a-running-mean.md`.

## La hipótesis, falsable

`hydrate_topics()` limpia `Topic.members` tras el replay, lo que también pone
`k = 0`; el primer `attach()` de cada pasada calcula `(viejo·0 + nuevo)/1` y
**borra el centroide acumulado**. Consecuencia: `centroid_vec` ≡ centroide del
último cluster absorbido, en 99.3% de los activos.

**Predicción que la prueba o la mata**: `--rebuild` salta `hydrate_topics`, así
que produce la media corrida VERDADERA. Rebuild e incremental, sobre la MISMA
historia, deben **discrepar sistemáticamente** — y la discrepancia debe ser
exactamente "el incremental está pegado al último cluster".

## FASE 1 — Verificación (read-only, sin escrituras)

Correr `project_dynamic_topics --rebuild` en modo **dry-run / a tabla sombra**
(nunca sobre prod) para una muestra de ≥200 topics activos con ≥3 pasadas, y
comparar por topic:

| Medida | Predicción si la hipótesis es CIERTA | Si es FALSA |
|---|---|---|
| cos(centroide_incremental, centroide_rebuild) | **bajo y disperso** | ≈1.0 |
| cos(centroide_incremental, último cluster) | **≈1.0 en ~99%** | disperso |
| cos(centroide_rebuild, último cluster) | disperso | ≈1.0 |

**KILL de la hipótesis**: si cos(incremental, rebuild) ≥0.98 mediano, el
diagnóstico está mal y este arco se cierra sin tocar código.

## FASE 2 — El fix (solo si Fase 1 confirma)

Separar las dos responsabilidades de `Topic.members`: la cola de INSERT y el
peso `k` del promedio. `k` pasa a ser su propio campo persistido/derivado
(`n_member_clusters` real), y limpiar la cola deja de tocarlo.

## GATE Z0 (barras congeladas AQUÍ)

Corrida en sombra de una noche completa con el fix, contra la misma noche sin
él:

- **G-ANCLA**: cos(centroide_nuevo, último cluster) mediano **cae por debajo de
  0.95** — el centroide deja de ser una copia. Si no cae, el fix no funcionó.
- **G-IDENTIDAD**: la tasa de re-fundación (identidades nuevas creadas cuando
  existía una activa compatible) **no sube**, y el conteo de identidades
  activas **no crece**. Un fix de anclaje que fragmenta más es un KILL.
- **G-DISPERSIÓN (la que importa)**: sobre los testigos del terremoto de
  Colombia (dt-242, dt-248, dt-244, dt-510, dt-517, dt-12910, dt-12928), el
  **acuerdo de argmax top-12 sube** respecto al baseline medido hoy. Es la
  métrica que el 2026-07-30 nombró como la enfermedad real.
- **G-SIN-DAÑO**: cohesión media de los topics activos no cae; junk activo
  sigue en 0; el corte no reprueba más etiquetas que el baseline.
- **Reversibilidad**: flag propio + ledger de estados previos, como tick-v2.

**Nada se escribe en prod hasta que las cuatro pasen.** Un KILL con evidencia
limpia vale más que un pase de cortesía — nueve veces ya.

## Orden

Z0 Fase 1 (hoy) → veredicto → Fase 2 + gate → recién ahí Z1 (8º gate del
predicado), que sobre anclas sanas mide otra cosa.
