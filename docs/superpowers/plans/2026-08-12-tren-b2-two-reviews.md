# Tren B2 — fixes de los dos reportes (Frank fresco + sonda ciega) — 2026-08-12

**Fuentes**: `docs/research/gold/2026-08-12-frank-test-fresh.md` (DRAFT-ONLY) +
`docs/research/ux-council/2026-08-12-cold-user-probe.md`. Regla del tren:
pathspec-only, TDD, verificación viva por item, yo integro + gate + deploy.

## Vagones (agentes HOY, disjuntos)

| # | Item (reporte) | Fix | Verificación |
|---|---|---|---|
| **V1** | v2 a la página (Frank gap-3): verdict fields sin consumidor, tier chips ausentes en recibos de evidencia, citations sin fecha | Cablear `CorroborationVerdict` (template_matches/aged/window_days/official) al render del pin; TierChip en recibos de evidencia del dossier; fecha visible en cada citation | dossier vivo muestra los 4 campos + chips + fechas |
| **V2** | Breaks de copy del dossier (Frank d): fecha parseada como figura ("2026⚠-08⚠-10⚠"), splice agramatical en lane-502, síntesis contradiciendo la tensión medida del cross-read, HOW listando `language:en`/`bluesky` como outlets | Guard de fecha en isFigureClaim; copy de degradación gramatical; la síntesis nunca afirma lo que el cross-read marcó en tensión; HOW filtra no-outlets | los 4 testigos re-renderizados limpios |
| **V3** | Brief honesto (ciego): "116 SIGNALS · 0 sources" (estado imposible), deltas de mercado 30d leyendo como diarios | Fila sin recibos no puede afirmar conteo de sources — estado degradado honesto; `· 30d` visible en la card resumen | testigos re-renderizados |
| **V4** | Coherencia de números (ciego, "el golpe más serio"): DE 4,840 vs 3,836 misma pantalla; 175 vs 218 países; 12σ vs z=71.2; FROM 9 AUG desktop vs 5 AUG móvil; Diversity 98 junto a Quality 30; scope fantasma a Eslovenia | MEDIR PRIMERO: trazar cada par divergente a su base real; unificar donde es una sola cantidad, ETIQUETAR la base inline donde son cantidades distintas (el patrón N19); diagnóstico del scope fantasma | cada par: o un número, o dos números con base nombrada |
| **V5** | Lane de corroboración no sobrevive investigación real (Frank gap-2, 1-éxito-en-4): pins→31.4s > techo Vercel rewrite → 502; DOC 2.0 concurrente vs su 1-req/5s → 429 | Serializar doc20 ≥5s entre queries; parciales siempre (nunca todo-o-nada); status `throttled` visible; si el total excede el techo del proxy → patrón job+poll (universe) | 4 corridas seguidas en prod: 0 × 502-mudo; parciales honestos |
| **V6** | Puerta país bajo carga (ciego + diseño): orden fresco→vivo→viejo cuelga al lector en el paso "vivo" | Servir artefacto viejo INMEDIATO (etiquetado) + refresh en background; el build vivo jamás bloquea el request | curl bajo carga sintética < 3s siempre |
| **V7** | Console resize shatter (ciego): RGL colapsa en resize de viewport, solo reload lo arregla | Re-medir buckets al resize + revalidar layout persistido | resize vivo 1440↔900↔1440 sin shatter |

## Pista de diseño (yo, spec para el ojo de Pedro — NO se construye sin aprobación)

**D1 — same_primary_actor (addendum a corroborate-v2)**: el caso ministerio-
sirio — 6 "corroboraciones" = 3 outlets recontando UNA declaración oficial.
`attributed_to` ya se captura y se bota; la regla nueva la carga al finding,
deja de contar pares dobles, y degrada a "N pares corroborantes de M fuentes,
primario único: <actor>". Fixture pre-registrado antes del build.

**D2 — Brief "measured Ground News"**: spec de la barra de voces por historia
+ blindspot medido (diseño aparte, `2026-08-12-brief-voice-bar-design.md`).

## Fuera de este tren (con dueño)
- Móvil console inerte a 375px + stat strip clipped → **chip #236 de Pedro
  (corriendo)** — no duplicar.
- SOURCE HEALTH id crudo, focus-clear 18px → filed R4 §2c.
- Cold console 20-30s → programa de warm-caches, post-tren.
- Clustering visible-mal (IMF-Siria bajo titular de bombardeo) → programa de
  landing/identidad (reloj de condenación, run-4 ~08-14).

## Orden de fuego
HOY: V1-V7 lanzados (7 agentes) + D1/D2 specs míos. Al aterrizar: gate
integrado (suites + browser), deploy único Fly+Vercel, artefacto de cierre.
