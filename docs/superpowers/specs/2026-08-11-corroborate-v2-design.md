# Corroborate-v2: independencia MEDIDA, no afirmada — DRAFT para el ojo de Pedro

**Status: DRAFT (Tren B del plan 2026-08-11). Build gateado en aprobación.
La materia prima son los casos MEDIDOS del council R4 — cada regla nueva
tiene su testigo y su kill rule antes de construir.**

## El problema, con testigos

R3 cerró: "draft yes, file no — la lane bloqueante es corroboración
independiente con recibos". R4 midió que los recibos llegaron y la
independencia sigue AFIRMADA: el conteo "N independently-operated outlets"
es falso en tres modos distintos, cada uno con caso vivo:

1. **Ownership-blind** (M-N18): ria.ru + interfax cuentan como 2 de "20
   independently-operated" mientras el resto del producto chipea ria como
   STATE RU. Las citations no cargan tier.
2. **Paraphrase-blind** (C-N18): crossread estampó "2 independent sources"
   sobre TRES re-escrituras de UN reporte de Haaretz cuyas propias citas
   dicen "According to Haaretz". El check byte-idéntico solo caza
   sindicación literal — la forma adversarial exacta que R3-2 nombró.
3. **Window-blind** (C-N22): un recibo de 6 semanas avala un veredicto
   fechado hoy, indistinguible.

Más dos fallas de precisión del mismo órgano: inversión por numerales de
locale (C-N17: "1.700" indonesio parseado 1.7 → el mejor match se volvió la
contradicción top) y template-matches contando como corroboración (T-N19/
DESK-N23: una emboscada en Mali avala un titular de Gaza).

## El diseño (tres reglas + dos fixes, todos apilados sobre lo que existe)

### R1 — Independencia por grupo de ownership+origin
El conteo de independencia agrupa citations por (ownership-tier del
clasificador backend post-N18 + source_origin_country). Regla: fuentes del
MISMO grupo estatal (tier 'state' + mismo origin) cuentan como UNA voz;
"established" (≥3 independientes) exige ≥3 GRUPOS, no 3 dominios. Las
citations cargan tier + origin visibles (la base backend ya existe — es
plumbing, no diseño nuevo).

### R2 — Detección de atribución-en-cita (paráfrasis, capa barata primero)
ANTES de cualquier embedding: si el cuerpo/quote de un recibo atribuye a
otro medio ("According to Haaretz", "informó Bild", "citando a Reuters" —
patrones multi-idioma acotados, lista medida sobre el corpus), el recibo se
marca `derivative_of: <outlet>` y NO cuenta como voz independiente del
hecho — cuenta como eco. Segunda señal (solo si la primera no decide):
quote-overlap normalizado entre recibos (dos "independientes" compartiendo
>60% de citas textuales = misma fuente primaria).

### R3 — Ventana temporal
Recibo con timestamp fuera de N días del veredicto (N=7 punto de partida,
congelar antes del run) se marca `aged_receipt` y no suma al conteo de
"corroborated" de hoy — puede mostrarse como contexto, etiquetado.

### F1 — Numerales de locale
Parser numérico locale-aware (1.700 indonesio = 1700; coma/punto por
idioma del recibo — `source_lang` ya viaja). El caso C-N17 congelado como
test: la misma cifra jamás vuelve a invertir un veredicto.

### F2 — Guard anti-template
Un match cuya similitud viene dominada por la PLANTILLA (mismo shape
"X killed in Y attack" con entidades disjuntas — chequeo de solape de
entidades/países entre claim y recibo) no corrobora: se degrada a
`template_match`, visible pero nunca contado. Testigos Mali→Gaza y
Yemen→Gaza congelados.

## Pre-registro del gate (congelar al aprobar)

- **G-HAARETZ**: los 3 re-writes del caso C-N18 → 1 voz, no 2+. 
- **G-STATE**: ria+interfax+tass en un mismo veredicto → 1 grupo.
- **G-LOCALE**: C-N17 re-corrido → el match top vuelve a ser corroboración.
- **G-TEMPLATE**: Mali/Yemen→Gaza → template_match, no corroborated.
- **G-NO-REGRESIÓN**: sobre un set de 20 corroboraciones HOY-correctas
  (muestreadas antes del build), el conteo no cae más de 15% — la
  independencia estricta no puede dejar el órgano mudo (si cae más, se
  reporta y se decide, no se relaja en silencio).
- Presupuesto: cero llamadas LLM nuevas en el hot path (R2 capa-1 es regex,
  capa-2 es string-overlap; R1/R3/F1/F2 puro cómputo).

## Qué NO es esto
No es re-ranking de recibos ni tocarle nada al retrieval; no es juez LLM
por par (refutación 3 del programa de identidad — muerto a volumen); no
cambia el dossier ni el crossread de claims (solo el CONTEO y el etiquetado
de independencia que ambos consumen).
