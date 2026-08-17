# Perfil de /api/v2/briefing — dónde vivían los 21.7 segundos

**2026-08-17.** Tranche 1 del plan del lector diario
(`docs/superpowers/plans/2026-08-17-daily-reader-t1-t2.md`, spec §9).
Instrumento: cronómetro por sección en `_fetch_section` + brackets manuales,
`?profile=1` esquiva el caché en lectura y escritura (commit `4b3e3ce5`).
Regla de la tajada: **medir antes de elegir fix.** La medición encontró un fix
que no era elección sino reparación — ver §3.

## 1 · Las corridas frías (profile=1, 3×, prod)

| sección | run 1 | run 2 | run 3 | mediana |
|---|---|---|---|---|
| top_atlas_topics | 5759.8 | 6724.6 | 5638.2 | **5759.8** |
| top_themes | 1897.5 | 2743.4 | 1883.7 | 1897.5 |
| category_counts | 2356.3 | 1299.9 | 1135.6 | 1299.9 |
| top_threads | 1917.3 | 1589.9 | 1449.9 | 1589.9 |
| theme_country | 1502.0 | 1503.7 | 1503.1 | **1503.1 ← timeout** |
| top_sources | 1500.1 | 1500.9 | 1501.4 | **1500.9 ← timeout** |
| rising | 1034.6 | 861.6 | 860.0 | 861.6 |
| schema_probes | 508.9 | 315.7 | 307.0 | 315.7 |
| (11 secciones más) | — | — | — | 20–280 c/u |
| **Σ secciones** | **17674** | **17228** | **14886** | |
| **wall** | 32803 | 18178 | 16122 | |

- **La ejecución es 100% serial**: Σ secciones ≈ wall en runs 2–3 (gap ~1s =
  red + JSON). ~19 consultas, una tras otra, sobre UNA conexión.
- **Run 1 wall−Σ = 15.1s fuera de las secciones**: primer hit a máquina fría
  (spin-up + pool). El instrumento no bracketea el `pool.acquire` — residuo
  conocido.
- **top_atlas_topics sola = ~5.8s (35–38% del total).**

## 2 · Hallazgo 1 — dos secciones degradan en CADA fill

`theme_country` y `top_sources` clavan **~1500ms exactos las tres veces** =
timeout de 1.5s (call sites con `timeout_seconds` explícito), y las tres
corridas confirman: `degraded_segments = ['top_sources', 'theme_country']`.

**Cada vez que el caché se rellena, la edición que todos reciben nace con dos
secciones degradadas.** Invisible hasta hoy porque nada miraba el fill.

Amplificación medida post-fix: un fill bajo contención congeló **cuatro**
degradadas (`category_counts`, `top_themes`, `top_sources`,
`top_atlas_topics`) en el payload cacheado 900s. **El fill es una lotería: el
request que lo paga congela SUS fallas para todos los lectores siguientes.**

## 3 · Hallazgo 2 — el caché llevaba muerto quién sabe cuánto (la causa del 21.7s)

Tres corridas "calientes" consecutivas sin `profile` tomaron 16–19s **cada
una** e imprimieron breakdown completo = recomputo total. El caché de 900s no
servía nada.

Causa raíz, visible tras convertir el `except Exception: pass` en warning
logueado (la clase exacta del apagón L1):

```
briefing cache WRITE failed (briefing_data:24):
Object of type Decimal is not JSON serializable
```

Un `SUM()` de Postgres llega como `Decimal`; FastAPI lo codifica bien en la
respuesta, `json.dumps` a secas no — **cada escritura fallaba y el `pass` se
lo comía. Todos los lectores pagaban el recomputo serializado completo en
cada apertura del Brief.** Ese es el 21.7s medido el viernes.

**Fix** (dos commits, desplegados y verificados):
- lectura y escritura del caché **loguean** su fallo, nunca `pass` (también en
  el caché del insight, mismo patrón);
- la escritura codifica con `jsonable_encoder` — el caché guarda EXACTAMENTE
  lo que FastAPI serviría fresco (Decimal→float, datetime→isoformat): un
  cache-hit sirve paridad con un serve fresco, no una variante.

## 4 · Después del fix (prod, medido)

| camino | antes | después |
|---|---|---|
| lector (cache-hit) | **16–22s, siempre** | **0.67–0.85s** |
| fill (una vez por TTL) | 16–22s | 15–18s (sin cambio) |

Sanity del payload cacheado: 10 hilos, tipos numéricos nativos (`int`, no
strings), mismas claves.

## 5 · Lo que queda — y la recomendación para la decisión (Task 3)

**G-VELOCIDAD (<3s en frío) NO está cumplida.** El fill sigue costando
15–18s, se lo come un lector real cada expiración de TTL, y congela sus
degradaciones (§2) para los 15 minutos siguientes.

**Recomendación: precalcular-y-servir** — el patrón mig-091 que ya salvó
`/universe` (84s de build → 2.8s de lectura):

1. El lector diario es un **sello nocturno por diseño** (spec §7): la edición
   es precalculable por construcción.
2. Un build sin usuario esperando puede darse timeouts completos (8s por
   sección en vez de 1.5), **reintentar** las degradadas, y publicar solo una
   edición completa — mata §2 de raíz.
3. El dominante (`top_atlas_topics`, 5.8s) no es un índice perdido: son
   subconsultas de arrays sobre el estado vivo. Optimizarlo compraría ~6s de
   los ~16; el build lo saca entero del camino del lector.
4. La alternativa índice-por-índice ataca 4 consultas distintas para, en el
   mejor caso, dejar el fill en ~8s — aún 2.7× sobre la barra.

Costo honesto del artefacto-precalculado: frescura acotada por la cadencia
del build (el sello + refresco periódico — coherente con «medianamente
actualizado, no siempre vivo» de Pedro), y una pieza más de infraestructura
nocturna que el watchdog debe vigilar (la pata de sello ya existe).

**Nada de esto se construye sin el ojo de Pedro** — es la decisión Task 3 del
plan, con estos números como base.
