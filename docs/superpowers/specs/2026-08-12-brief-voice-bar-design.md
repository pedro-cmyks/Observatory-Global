# Brief "measured Ground News" — barra de voces + blindspot medido — DRAFT

**Status: DRAFT para el ojo de Pedro. Nada se construye sin su aprobación.**

## El diagnóstico que responde (sonda ciega, verbatim)
"No volvería a leer noticias aquí. El Brief es hermoso, pero es una versión
más lagging y noisy de cualquier portada de wire; su lead el día que visité
era un recall de jalapeños." Y a la vez: el momento estrella del mismo agente
fue East Timor — "explotó en noticias y nadie EN East Timor escribió nada de
eso. Ningún sitio de noticias te dice esto."

**La tesis del rediseño: el Brief no puede ganar contando QUÉ pasó (ahí
siempre será un wire lento). Gana contando QUIÉN te lo está contando — por
historia, de un vistazo.** Es exactamente lo que Ground News vende (barra de
sesgo por historia + blindspots), traducido a lo que Atlas MIDE de verdad.

## Qué hace Ground News, y la traducción honesta

| Ground News | Atlas puede (con datos que YA computa) | Atlas NO puede (y no finge) |
|---|---|---|
| Barra L/C/R por historia | **Barra de VOCES**: estado/wire/independiente/desconocido + nº países de origen + nº idiomas | Lean político — no lo medimos; afirmar sesgo violaría la doctrina |
| "Blindspot" (un lado no la ve) | **Blindspot GEOGRÁFICO medido**: self_voice ≈ 0 = "cubierto SOBRE ellos, no POR ellos" (el hallazgo East Timor, como chip por historia) | Factuality scores — no medidos |
| Ownership por outlet | Ya existe: tiers + ownership_group (corroborate-v2) | |
| Compare headlines | **Compare framings**: 2-3 titulares del MISMO hilo desde grupos de voz distintos, lado a lado, con idioma original + traducción (maquinaria TranslatableHeadline ya viva) | |

## Diseño (3 piezas, todas sobre datos servidos hoy)

### P1 — Barra de voces por historia (lead + watchlist)
Barra horizontal segmentada bajo cada titular del Brief:
`■■■■■□□ 14 outlets · 6 países · 4 idiomas · 2 STATE`
Segmentos por tier (color ya definido en la familia TierChip), tooltip con el
desglose. Fuente: los evidence_samples sellados ya cargan source + tier +
origin + lang — es agregación en render, cero llamadas nuevas.

### P2 — Chip BLINDSPOT medido (la joya)
Cuando la historia tiene país-sujeto y `self_voice < umbral` (medido en
voice_mix, umbral pre-registrado con histograma antes de fijar):
`◐ BLINDSPOT: 0% prensa propia de <país>` — click → la vista país.
Y la inversa cuando aplica: `● SOLO prensa estatal de <país>`.
Es la tesis del producto (WAVE-4 ownership) llegando por fin a la portada.

### P3 — Compare framings (disclosure en el lead)
En la historia lead, un `<details>` "Cómo se lee en otras voces": 2-3
titulares del mismo hilo elegidos por MAX diversidad de grupo de voz
(estado vs independiente vs wire; idiomas distintos), original + traducción,
cada uno con su TierChip. Regla de honestidad: solo miembros del hilo con
gate/court limpio; nunca inventar contraste que no existe (si el hilo es
mono-voz, el disclosure dice eso — que ES el dato).

## Qué NO cambia
La estructura del Brief (lead/watchlist/secciones/gaps) queda; esto es una
CAPA sobre cada fila, no un rediseño de la página. El anti-goal del wedge se
respeta: cero medición nueva, cero superficie nueva — solo servir en L1 lo
que L2/L3 ya miden.

## Aceptación (pre-registrada al aprobar)
- G-BAR: 10 historias del Brief muestran barra con conteos que cuadran con
  sus recibos visibles (spot-check a mano).
- G-BLINDSPOT: el chip dispara en un caso East-Timor-class real del día y NO
  dispara en historias con self_voice sano (falsos positivos < 1/10 a mano).
- G-FRAMING: el compare nunca muestra un titular fuera del hilo servido.
- Re-test frío: un agente ciego nuevo sobre /brief debe describir el Brief
  como algo DISTINTO de "portada de wire" sin que se le pregunte.
