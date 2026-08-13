# Vagón veracidad + colegio — 2026-08-13

**Fuentes**: `docs/research/gold/2026-08-13-veracidad-scorecard.md` (7/4/1) +
`docs/research/ux-council/2026-08-13-colegio-ciego.md` (top accionables).
Regla: pathspec, TDD, browser-verify, integro + deploy único.

| # | Hallazgo | Fix |
|---|---|---|
| **X1** | LA CLASE SISTÉMICA (refutación + 2 divergencias): "0% voces colombianas"/"EE.UU. ausente" = forma de LA INGESTA presentada como forma del MUNDO — mientras El Tiempo/CNN gritaban | Todo claim de cobertura/voz declara su base: "de lo que Atlas ingiere" — VoiceMix, EL VACÍO/blindspot, dock, standfirst, coverage-shape en dossier. Copy + meta, sitio por sitio, con inventario |
| **X2** | "600 de răniți" (heridos) servido como "600 dead" — severidad máxima en producto de recibos | Guard de términos-de-víctimas en el camino de traducción: lexicón bilingüe acotado (muertos/heridos/desaparecidos + variantes ru/ro/uk/es/ar...); flip detectado → servir original + "translation unverified", jamás la cifra volteada |
| **X3** | "acciones al alza" = LO CONTRARIO de lo medible (síntesis inventó dirección de mercado); "epicentro cerca de Bogotá" (capital-como-proxy, Chocó real) | Extensión del prose-validator: claims de dirección de mercado sin recibo → downgrade; geografía degradada dice el PAÍS, nunca inventa la capital |
| **X4** | C5 colegio (4/8 no-analistas): "surprise 2.6σ", "velocity +0.59 (log-volume per 6h)", "sealed edition carried no stories" ilegibles — "enseñé escuela 40 años y no puedo parsear eso" | Capa de frases humanas: cada stat técnico gana su frase llana al lado ("subió mucho más rápido que su propio ritmo normal"), el número queda para quien lo quiera; tras X1 (comparten archivos) |
| **X5** | Estudiante: "citable sin botón" · usuario-perdido: "what is happening in israel" → silencio | Botón copy-citation en recibos (outlet+fecha+URL, formato citable) + búsqueda sin hits re-rutea por la lane semántica existente con label honesto |
| **X6** | C9 (terminó 2 sesiones móviles): "LIVE DATA" + "0 sig/min · No signals found" a la vez | El header LIVE no puede afirmar vivo sobre lane muda (la clase N23, en el stream) + verificar que los fixes móviles del vagón W SÍ llegaron a prod post-panel |

**Pista aparte (spec, ojo de Pedro)**: chrome en español — la lectora-es
encontró la paradoja ("traduce la prensa del mundo al inglés pero no se
traduce a sí mismo"); P1 midió que no existe chrome bilingüe. Es programa,
no vagón.

Secuencia: X1/X2/X3/X5/X6 ya; X4 tras X1. Gate integrado + deploy al final.
