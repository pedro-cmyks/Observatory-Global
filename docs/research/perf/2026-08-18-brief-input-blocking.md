# Brief móvil — bloqueo de input durante la carga (2026-08-18)

Contexto: dos paneles ciegos independientes (2026-08-18, panel-ciego-daily-reader §4)
reportaron taps sin respuesta y scroll muerto en los primeros segundos del Brief
móvil. Diagnóstico abierto: la hidratación bloquea el main thread. Este artefacto
congela la medición ANTES, la atribución medida, el fix y el DESPUÉS.

## Entorno de medición

- Preview local `frontend-v2` (Vite dev server, puerto 3000) + build de
  producción (`npm run preview`, puerto 3200 — proxy `/api` agregado al bloque
  `preview` de vite.config para que sirva data real). Viewport 375×812 (preset
  móvil del Browser pane), API = prod vía proxy.
- Máquina: M1 sin CPU throttle → **cota INFERIOR**; un teléfono medio corre
  4-6× más lento. El banco DEV (React dev + StrictMode double-render + módulos
  Vite) infla ~3-6× sobre el build prod y funciona como multiplicador de CPU
  que aproxima el costo en teléfono; el banco DIST en M1 casi no discrimina
  (0-2 long tasks en TODA la carga, incluso antes del fix).
- Carga FRÍA de datos: `sessionStorage` limpiado antes de cada corrida
  (sin `atlas_brief_prefetch`), full page load de `/brief`.
- Instrumentación: `PerformanceObserver {type:'longtask', buffered:true}`
  (cubre desde navigation start), React `<Profiler>` + huella de estado por
  render (temporal, retirada antes del commit), y sonda de tap sintético
  in-page `?perftap=1` (timers a offsets fijos 0.8-5s midiendo
  retraso-de-cola + `focus()` sobre `.brief-place-select` — el retraso de un
  timer es el mismo que sufriría un tap real: ambos esperan a la tarea en
  curso).
- ⚠ CAVEAT de las dos primeras corridas: el tab del pane estaba en BACKGROUND
  (Chrome clampa timers a 1Hz y desprioriza; descubierto porque la sonda daba
  drifts de ~1s con long tasks de 70ms). Las corridas comparables
  antes/después de abajo son todas con tab en FOREGROUND (`visibilityState:
  'visible'` verificado en cada colección).

## ANTES

### Corrida A — dev FRÍO (server recién arrancado; tab en background — el registro histórico del reporte del panel)

Navigation timing: DCL 840ms · load 846ms. El masthead forma parte del primer
commit ≈ t≈0.9s; todo lo listado desde t=1647 es **después del primer paint
del masthead**.

| # | start (ms) | dur (ms) | fase |
|---|-----------|----------|------|
| 1 | 60 | 63 | eval de módulos inicial |
| 2 | 870 | 53 | mount inicial (masthead + loading) |
| 3 | 1647 | **189** | llegada del payload → render |
| 4 | 1869 | 92 | cluster de render |
| 5 | 1983 | 68 | ídem |
| 6 | 2110 | **176** | ídem |
| 7 | 2725 | 121 | ídem |
| 8 | 2928 | **398** | ídem — el peor |
| 9 | 4130 | **342** | segundo pico |
| 10 | 4511 | 64 | cola del cluster |
| 11 | 16607 | **212** | respuesta tardía (insight/enrichment) |

**Total: ~1.86s bloqueados**, concentrados en t=1.6-4.6s (~1.45s en una
ventana de 3s). Cuatro tareas >200ms tras el masthead. En teléfono 4-6×:
ventana de 6-18s esencialmente sorda — reproduce el reporte del panel ciego.

### Corrida B — dev tibio FOREGROUND (banco comparable)

Long tasks: 127, 145, 86, 106 → **total 464ms, máx 145ms**.

### Corrida C — dist (build prod) FOREGROUND

**0 long tasks** (>50ms) en M1; 8 renders. El banco prod-M1 está saturado de
headroom — la sordera del teléfono hay que leerla en el banco dev multiplicado.

## Atribución (medida con Profiler + huella por commit, no estimada)

1. **El parse NO es**: `/api/v2/briefing` = 196KB, `JSON.parse` = **2ms**.
2. **El DOM NO es gigante**: 1,660 nodos, 387 recibos, 72 cards.
3. **La causa es una CASCADA de re-renders completos de un solo componente de
   3,604 líneas** (BriefNewspaper renderiza toda la página). La huella por
   render la nombra llegada por llegada (dev tibio, misma corrida):
   mount → `readHoursAgo` → **payload** (t≈1.2s) → **eclipse** (1.5s) →
   **insight** (2.0s) → **poll de article-enrichment #1** (2.1s, `gArt 0→27`)
   → **daily edition** (2.3s) → **near edition** (2.5s) → **poll #2** (3.4s,
   27→36) → … **20 renders en 3.5s** (StrictMode duplica pares en dev; en el
   build prod la misma cascada son 6-8 commits).
4. Dos agravantes medidos dentro de la cascada:
   - `useArticleStates` (×2 instancias) pollea cada 4s hasta 8 veces y hacía
     `setStates(new Map())` INCONDICIONAL — un poll idéntico re-renderizaba
     las 3,604 líneas igual (renders con huella idéntica, medidos).
   - Cada render era SÍNCRONO (urgente para React): un tap que aterrizara
     dentro esperaba la tarea completa — hasta 398ms en dev-frío (×4-6 en
     teléfono).
5. La cascada de red confirma el multiplicador: tras el briefing llegan
   country-edition, eclipse, insight, delight, articles fetch/state, y una
   ráfaga de translate/batch + ~12 translate/text (estos últimos re-renderizan
   solo sus componentes suscritos, no la página — lane ya bien aislada).

## El fix (catálogo honesto: diferir + memoizar identidad; cero contenido quitado)

1. **`startTransition` en TODAS las llegadas de red de BriefNewspaper.tsx**
   (payload/caché, insight, eclipse, daily edition, country detail/threads,
   country edition, near edition, watchCounts): los mismos renders ocurren,
   pero como transiciones React 19 los renderiza por unidades interrumpibles —
   un tap se procesa entre fibras en milisegundos en vez de esperar el render
   completo. Nada se difiere para siempre y nada deja de renderizarse.
2. **`useArticleStates` (lib/articleEnrichment.ts)**: bail-out por identidad —
   un poll cuyo resultado es render-equivalente al anterior (`sameStates`:
   mismas urls, mismo status/via/excerpt/word_count) devuelve la referencia
   previa y NO re-renderiza; un poll con cambios reales entra por
   `startTransition`. Beneficia también a WorkbenchPanel y DossierView
   (mismos consumidores del hook).

## DESPUÉS (mismas condiciones, foreground, sesión fría)

### dev FRÍO (server reiniciado — el espejo de la corrida A, ahora foreground)

| start (ms) | dur (ms) |
|-----------|----------|
| 1101 | 90 |
| 1258 | 63 |
| 1560 | 70 |
| 2481 | 62 |

**Total 285ms (antes 1,858ms) — ni una tarea >100ms, mucho menos >200ms.**

### dev tibio foreground: 74, 73, 69, 70, 61, 65 → total 412ms, **máx 74ms**
(antes en el mismo banco: máx 145ms; los renders con transición se trocean).

### Sonda de tap `?perftap=1` durante la ventana de carga (dev frío, 10 probes 0.8-5s)

| offset (ms) | espera de cola (ms) | focus (ms) | total (ms) | ¿focus OK? |
|------------|--------------------:|-----------:|-----------:|------------|
| 800 | 70 | 0 | **70** | ✓ |
| 1200 | 1 | 0 | 1 | ✓ |
| 1600 | 2 | 0 | 2 | ✓ |
| 2000 | 55 | 0 | 56 | ✓ |
| 2400-5000 (6 probes) | 1-2 | 0-1 | **1-2** | ✓ |

**Peor caso 70ms < 150ms; mediana ~2ms.** Un tap CDP real al selector durante
la carga abrió el dropdown nativo (verificado por `activeElement =
SELECT.brief-place-select` + el popup bloqueando CDP — es decir, ABRIÓ).

### dist (build prod) después: 1 long task de 67ms (eval del bundle), 387
recibos renderizados — mismo contenido, cero pérdida. Desktop verificado en
pantalla (masthead/sealed band/vitals/markets/desks intactos); consola sin
errores JS (solo 503s best-effort del API prod, degrade diseñado).

### Barra de aceptación (congelada en el encargo)

- Ningún long task >200ms tras el primer paint del masthead: **PASA** en los
  tres bancos (dev-frío máx 90ms, dev-tibio máx 74ms, dist máx 67ms y ese es
  pre-masthead).
- Tap sintético al selector durante la carga <150ms: **PASA, medido** (peor
  70ms, mediana 2ms, 10/10 focus).
- vitest completo: 1976/1976 verde. `npm run build`: verde.

## Residuo honesto + recomendación (fuera del alcance de este cambio)

- **El chunk JS es UNO y pesa 1.9MB (598KB gz)**: `main.tsx` importa `App`
  (la consola entera: mapas, paneles, d3) estáticamente, así que abrir /brief
  en un teléfono parsea+evalúa también la consola que no va a montar (el
  keep-alive la monta recién al primer /app). Ese eval es el bloqueo ANTES
  del masthead (~150-240ms M1 ≈ 0.6-1.5s teléfono) y este cambio no lo toca —
  partir el bundle (React.lazy sobre App en main.tsx o manualChunks) es un
  chip aparte, territorio compartido con quien posea main.tsx.
- El costo por-render del componente único sigue existiendo (transición ≠
  gratis: se troceó, no se achicó). Si el panel ciego vuelve a reportar
  lentitud (no sordera), el siguiente lever es React.memo por sección.
- El `?perftap` y el Profiler eran instrumentación temporal y fueron retirados
  antes del commit; el protocolo de este doc los re-crea en minutos.
