# Atlas UX Video Review — 2026-05-16

## Fuentes revisadas

Transcripts generados localmente desde los tres videos compartidos:

- Landing: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.40.47.txt`
- Brief: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-14 at 21.53.02.txt`
- App: `docs/research/ux-video-evaluation/transcripts/Screen Recording 2026-05-16 at 09.25.31.txt`

También se usaron frames/contact sheets extraídos en `/tmp/atlas-video-review/` para validar los momentos visuales mencionados en los transcripts.

## Lectura ejecutiva

El flujo correcto sigue siendo `Landing -> Brief -> App`, pero la experiencia muestra una brecha clara entre capacidad analítica y legibilidad. Atlas ya produce momentos de valor, especialmente cuando el usuario logra seguir una investigación como cobre, China, Israel o Vietnam. El problema es que ese valor aparece por exploración accidental, no por un flujo guiado, persistente y explicable.

La prioridad del roadmap cambia de "cerrar features sueltas" a "hacer Atlas enseñable, persistente y exportable":

1. Enseñable: el producto debe explicar qué se está viendo, cómo leerlo y para qué sirve.
2. Persistente: una investigación no debe perder contexto al pivotar entre tema, país, fuente, Public Attention o Workspace.
3. Exportable: cuando el usuario encuentra valor, Atlas debe convertir evidencia y señales en un dossier legible.

## Video 1 — Landing

Hallazgos principales:

- Los CTAs verdes llaman la atención antes de que el usuario lea el contenido. Funcionan visualmente.
- El radar/hero se ve atractivo, pero no es interactivo y puede complicar el contraste del texto.
- La métrica `1.3M signals` debería venir de datos vivos o al menos estar sincronizada con `/api/v2/stats`.
- `Multi` es ambiguo; si significa multilingual, debe decirlo con claridad.
- La explicación de Atlas gratis/donaciones es útil y debe mantenerse visible.
- Las tarjetas de `What you see` y `Data sources` hacen hover, pero no son clicables. El usuario espera poder abrir ejemplos, docs o casos de uso.
- Docs debe ser una parte central del producto, con retorno claro hacia Landing, Brief y App.
- La documentación actual puede estar desalineada con el estado real del producto.

Issues relacionados:

- #135 `ux(landing): live stats and clickable product cards linked to visual docs`
- #134 `docs: document real-world analytical use cases`
- #140 `docs(product): build visual use-case manual with real Atlas screenshots and annotated flows`

## Video 2 — Brief

Hallazgos principales:

- El Brief se percibe lento. El usuario espera que se precargue mientras está en Landing.
- En pantallas widescreen/laptop, parte de la información se corta y a veces solo se ve el mapa.
- `Global Mood Neutral` no se entiende sin explicación metodológica.
- El click por país es valioso: filtra y orienta.
- Falta el análisis editorial/IA que antes generaba una lectura del momento global. Su ausencia se percibe como regresión.
- `Narrative Thread`, línea verde, `Tone`, `Mood`, `Drift` y `Coverage Analysis` no tienen suficiente explicación.
- Cuando el usuario hace click en una noticia/publicación desde un thread, espera llegar a esa evidencia específica, no solo a un filtro temático amplio.
- El mapa carga arcos, colores y puntos sin explicar qué significan ni cómo leerlos.
- El tour gusta, pero no reemplaza documentación metodológica y casos de uso.
- La parte inferior del Brief gusta, pero pierde información en widescreen.
- `Watch` debería estar incluido en el walkthrough.
- `Coverage Analysis unavailable` y análisis genéricos rompen confianza.
- Al entrar a una combinación tema-país, el usuario llega a un roadblock: no queda claro qué hacer después.
- Public Attention muestra términos poco claros y no siempre accionables.
- La diferencia entre `Activity timeline` y `Narrative Drift` no queda clara.

Issues relacionados:

- #136 `perf(brief,app): prefetch data and clarify slow loading states across Landing -> Brief -> App`
- #137 `ux(methodology): restore editorial analysis and explain mood, tone, sentiment, drift, and baseline`
- #138 `ux(investigation): preserve context across theme, country, source, and public-attention pivots`
- #124 `feat(workspace): saved searches / persistent alerts for investigative patterns`
- #143 `ux(map): explain and declutter live map layers, ships, geo alerts, arcs, and colors`

## Video 3 — App

Hallazgos principales:

- La App debería estar precargada al venir del Brief.
- La búsqueda `conflicto en Colombia` tarda demasiado y no lleva claramente a Colombia/conflicto.
- El stream muestra timestamps que no corresponden con la entrada progresiva de eventos.
- El pool de conceptos se siente demasiado pequeño y estático. Una búsqueda natural debería crear o sugerir conceptos dinámicos.
- Las búsquedas no preservan claramente el texto original ni el contexto de país.
- Etiquetas como `Crisis Event`, `Crisis Death` y sentimientos `-42` o `21` no son legibles para usuarios normales.
- `Coverage Analysis unavailable` aparece repetidamente y sugiere fallo del componente de IA/editorial.
- Las menciones de personas parecen aleatorias si no se explica por qué están relacionadas con el tema.
- La navegación pierde contexto: volver atrás no reconstruye la investigación.
- Workspace/Trail:
  - El panel puede salirse de pantalla.
  - Trail y Pinned graph no se entienden.
  - Los nodos no explican la historia de investigación.
  - Los toggles muestran tipos ausentes o no cambian de forma evidente.
  - El graph pierde balance al moverlo.
- El mapa con China, puertos, barcos y alertas tiene potencial, pero está saturado y poco explicado.
- Google Trends parece no estar llenando datos o no aparece donde el usuario lo espera.
- Public Attention no está suficientemente scopiado al país/tema activo y contiene ruido como entradas de Wikipedia poco útiles.
- Al hacer click en un país desde un tema, debería abrir ese país dentro del mismo tema; hoy se pierde el hilo.
- La búsqueda debe funcionar en español y otros idiomas; `semiconductors` no debería ser el único camino.
- La investigación sobre cobre muestra el valor real de Atlas: países, sentimiento, fuentes y evolución. Pero faltan traducción, explicación de fuentes, precio del commodity y una forma de volver al estado global del tema.
- Falta o se sobrepone el botón `Watch`.
- El rango temporal llega solo a 12/24h; el usuario pide al menos una semana.
- El terminador day/night se ve demasiado brusco y Settings no explica su valor.

Issues relacionados:

- #69 `feat(search): Spanish-language routing + multilingual query expansion`
- #104 `bug: Google Trends badge missing for US/GB/IN/MX/BR`
- #128 `ux(workspace): keep board in viewport and separate Trail graph from Pinned graph`
- #139 `ux(time-range): extend console range beyond 24h and clarify Live/Pause semantics`
- #142 `ux(public-attention): scope Trends/Wikipedia to active country/topic and make items actionable`
- #133 `feat(workspace): export consolidated signal dossier from graph nodes`
- #141 `feat(reading-mode): generate an Atlas investigation newspaper from pinned evidence`
- #56 `ux(settings): Day/Night overlay terminator is harsh — Settings panel utility unclear`

## Issues creados o reabiertos desde esta revisión

Reabiertos con evidencia nueva:

- #56 Day/Night overlay + Settings utility
- #69 Spanish-language routing + multilingual query expansion
- #104 Google Trends missing/stale data
- #124 Saved watches / persistent alerts
- #128 Workspace viewport + Trail vs Pinned graph

Creados:

- #135 Landing live stats + clickable docs/use-case cards
- #136 Landing -> Brief -> App prefetch/loading states
- #137 Methodology/editorial explanation
- #138 Investigation context persistence
- #139 Time range beyond 24h + Live/Pause semantics
- #140 Visual use-case manual with real Atlas screenshots
- #141 Reading Mode / investigation newspaper from pinned evidence
- #142 Public Attention scoping and actionability
- #143 Map layer explanation and decluttering

Expandidos:

- #133 Dossier export from Workspace should become the evidence foundation for Reading Mode.
- #134 Use cases should be visual and product-grounded, not text-only.

## Ejecución recomendada

P0 — Confianza y continuidad:

1. #136: prefetch + loading states for Landing -> Brief -> App.
2. #137: restore/replace editorial analysis and explain methodology.
3. #138: preserve investigation context across pivots.
4. #128: make Workspace usable before adding more Workspace features.
5. #104 + #142: fix Trends/Public Attention data and scope.
6. #69: multilingual search and Spanish query routing.

P1 — Onboarding con producto real:

1. #140: visual manual with annotated screenshots and persona-specific flows.
2. #134: use-case docs backed by screenshots and live product states.
3. #135: Landing cards link into docs/use cases and back to product.

P2 — Exportable investigation:

1. #133: consolidated signal dossier from pinned nodes.
2. #141: Reading Mode / Atlas investigation newspaper built on top of dossier export.
3. #124: persistent watches become a source for repeated dossiers/editions.

P3 — Visual polish and advanced context:

1. #139: one-week range and clearer Live/Pause semantics.
2. #143: map layer explanation and decluttering.
3. #56: softer day/night overlay and useful Settings copy/control.
4. #46 and #106 stay blocked until external credentials/assets exist.
