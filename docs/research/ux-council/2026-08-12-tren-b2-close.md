# Tren B2 — cierre (2026-08-12)

**7/7 vagones + merge del chip #236, deployado Fly + Vercel (fb45bcfb).**
Fuentes: Frank-test fresco (DRAFT-ONLY) + sonda ciega. Plan:
`docs/superpowers/plans/2026-08-12-tren-b2-two-reviews.md`.

| Vagón | Veredicto | Commits |
|---|---|---|
| V1 v2-a-la-página | chips de tier en recibos de evidencia (tass→STATE vivo), fechas en citations, aged atenuado, verdictFacets set-aside | 280f2cbe |
| V2 copy dossier | fechas nunca cifras; la sustitución de honestidad ya no INVIERTE negaciones; síntesis degradada al contradecir tensión medida (con la cuenta contraria citada); HOW solo outlets | 7e48458c 635261b7 6cfd00cc c4e5cb5c |
| V3 Brief imposible | "116·0 sources" = starvation del slice sin ORDER BY (24 ids todos muertos por retención con 80 vivos) — misma enfermedad e55cb08e en el camino de LISTA; markets "· 30 sessions" medido de la serie | ea485e3d e00cd167 |
| V4 coherencia | 6 pares trazados: header contaba solo países DIBUJABLES (216/101,557 al dígito ahora); "12σ" era ratio (12×) con ventana mal declarada + σ escalaba lineal no √t; Diversity/Quality legibles + "unclassified" neutro (el rojo era nuestro hueco de allowlist como veredicto); fantasma Eslovenia = tie-break sembrado en nodes[0] ordenado por calor de anomalía; + test AST de paridad de placeholders en 37 routers | f615c8a8..014f5e7e |
| V5 lane sobrevive | MI diagnóstico estaba mal (throttle vivía desde c7e69832): la causa = 5.75s/query + 12s fijos vs techo ~30s Vercel → job+poll construido; 80 requests, CERO 502; parciales con estado por pin | dfac2370 36d21e28 |
| V6 puerta país | artefacto viejo se sirve YA + refresh background single-flight (el orden viejo ponía CO 264s delante del lector) | 851e52f8 |
| V7 resize shatter | el console se medía INVISIBLE (keep-alive display:none → caja 0px → clamp 320 congelado); medición-ausente + ResizeObserver | b2a852fe |

Gate integrado: **2,972 backend + 1,462 vitest + build limpio**, merge #236
con árbitro (que además corrigió mi resolución Frankenstein del lensSections:
un 'timeout' sin productor habría permitido lane en blanco y mudo).

**Chips nuevos de los hallazgos**: WorkbenchPanel crash-to-blank bajo 429 ·
Investigation.trail sin guard · timeout-as-zero en themes (previo).

**Pendiente con dueño**: D1 same_primary_actor (addendum spec, ojo de Pedro) ·
D2 Brief voice-bar (spec DRAFT esperando ojo) · verdict en /dossier/corroborate
(clasificar articles del pin contra su claim — semántico, no el 3-liner que
parecía) · país sin artefacto sigue en build vivo (clase cubierta por N puertas).
