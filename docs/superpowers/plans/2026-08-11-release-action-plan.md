# Plan de acción del release — 2026-08-11

**Compañero de `docs/specs/2026-08-11-release-roadmap.md`. Secuencia, dueños
y triggers. Tres trenes; el A arranca HOY.**

## Tren A — Confiabilidad (§2a del roadmap) — AGENTES HOY, disjuntos

| Item | Fix | Dueño | Verificación |
|---|---|---|---|
| **A1 · N26** puerta país fría 503 en día de noticia | Warm-build como la daily edition / universe (patrón mig-091 artifacts): build nocturno + handler lectura pura + cache-fill post-seal; el cold-path actual queda de fallback | agente | curl frío de CO/JP/US < 3s tras deploy; el guard de slots sobrevive |
| **A2 · N19** "24h" estampado sobre conteos lifetime (88→3,659) | MEDIR primero qué cuesta el conteo window-scoped en detail; si barato → servirlo; si caro → etiquetar honesto ("lifetime · N este período") — decisión documentada en el commit | agente | el mismo hilo lee igual en fila y detalle, o el detalle declara su ventana |
| **A3** lanes que cuelgan mudos (persona /focus 45-120s skeleton) | Per-lane statement_timeout + skeleton con estado honesto ("midiendo… / lane degradado") — el patrón timeline C4a aplicado al /focus | agente | persona pesada (trump) degrada visible < 10s, nunca skeleton infinito |
| **A4 · N23** timeline fabrica ausencia | Reason codes: `lane_starved` ≠ `measured_zero` ≠ `invalid_ref` — el render distingue "no hay actividad" de "no pude mirar" | agente | trump/putin muestran lane-starved honesto; ref malformado da invalid_ref |

Regla del tren: pathspec-only, TDD, browser/curl-verify por item, yo integro
+ gate + deploy único al final.

## Tren B — Corroborate-v2 (§2b) — SPEC PRIMERO (yo), build tras aprobación

Brainstorm→spec con las tres piezas medidas por el council:
1. **Ownership**: tiers en citations (la base backend ya existe post-N18) —
   ria/interfax no cuentan como "independently-operated" entre sí ni junto a
   TASS; el conteo de independencia agrupa por ownership+origin.
2. **Paráfrasis**: el caso Haaretz×3 — atribución-en-cita ("According to
   Haaretz") detectable barato ANTES de cualquier embedding; quote-overlap
   como segunda señal. Pre-registrar precisión sobre los casos del council.
3. **Ventana**: un recibo fuera de ventana N días no avala un veredicto de
   hoy sin marcarse (`aged_receipt`).
KILL rules antes del build, como siempre. Spec → ojo de Pedro → build.

## Tren C — Programas (corren en sus relojes, NO en este plan)
Chip 5-issues (corriendo) · chip #236 móvil (corriendo) · condenación ~08-14
→ gates landing → lens · relabel-de-stock (espera: es pariente del re-run de
landing; no abrir dos frentes de motor) · maturity contract #221 (diseño,
cola tras Tren B).

## Orden de fuego
HOY: Tren A lanzado (4 agentes) + Tren B spec draft. Al aterrizar A: gate,
deploy, y §2a del roadmap se tacha. Tren B build tras aprobación del spec.
Release-beta gate: §2a ✓ + §2b ✓ + una semana de sellos limpios.
