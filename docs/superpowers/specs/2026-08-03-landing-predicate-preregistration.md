# Pre-registro (8º gate): el predicado de join del landing — Unicode + contención de sujeto

**2026-08-03 · Congelado ANTES de cualquier build (aprobado por Pedro).
Sucesor directo del 7º gate (`2026-08-03-consolidation-landing.md`), cuyo
KILL en G-FOUNDING dejó el diagnóstico: el PRINCIPIO del landing funciona
(2/6→6/6), el PREDICADO `labels_compatible` es el defecto — 50% de bloqueo
falso en pares misma-historia + auto-bloqueo estructural fuera de ASCII.
Este run reemplaza el predicado. Movimiento post-resultados = inválido.**

## Lo que se hereda intacto del 7º (no se re-decide)

Regla de consolidación primaria (cos≥0.90 AND predicado AND countries_share),
arm B (join solo con predicado compatible, si no funda), familias testigo con
sus definiciones, juez de landing con quote-gate + spot-check humano, replay
sobre las 15 noches congeladas + pool de HOY, mindfulness M1, read-only.

## El predicado bajo prueba (recomendación adoptada)

**P-nuevo** = `unicode_label_norm` + contención de tokens de sujeto:
1. Normalizador Unicode (casefold + NFKC + strip diacríticos donde aplique;
   NUNCA el `[^a-z0-9]+` ASCII — mata el auto-bloqueo cirílico de raíz).
2. Compatible si los TOKENS DE SUJETO de un label están contenidos en los del
   otro (tras normalizar; stopwords/genéricos del df-alto de la noche fuera
   del set de sujeto SOLO para el requisito de contención mínima, nunca como
   veto — la lección anti-df del run 5 §11.1 se respeta: la contención no
   exige rareza, exige solape).
   Definición exacta de "token de sujeto" la fija el harness ANTES del run y
   se congela en el artefacto; el criterio: "US Citizen Released by Iran" ↔
   "American Released from Iran" debe pasar, "Berlin Pride Van Attack" ↔
   "Drone Attacks on Moscow" debe fallar — 10 pares de calibración se
   escriben ANTES de medir y se reportan como tabla de sanidad del predicado
   (fallar la tabla = arreglar el predicado ANTES del run, permitido; tocar
   los gates después del run, prohibido).

## Arms

- **Arm A**: producción (baseline, sin cambios).
- **Arm B-p7**: el arm B del 7º con `labels_compatible` viejo (comparabilidad).
- **Arm B-p8 (el candidato)**: arm B con P-nuevo.
- **Arm B-court (tercer arm comparativo)**: P-nuevo, y SOLO en banda gris
  (predicado falla pero cos ≥ 0.93) consulta entailment estilo court sobre
  recibos — con contador de llamadas reportado; si el volumen proyectado a
  nocturno excede el cap de 150 llamadas/noche, ese arm se reporta como
  inviable-a-volumen por más bonito que mida (la lección de la refutación 3).

## Gates congelados (idénticos al 7º salvo el sujeto del veredicto = B-p8)

| Gate | Barra |
|---|---|
| G-K2 | ≥14/15 noches ≤2% |
| G-784 | 0 componentes país-span+label-clash |
| **G-LANDING (primaria)** | B-p8 ≥ ⌈⅔·scorables⌉ familias correctas Y estrictamente > arm A |
| **G-FOUNDING (la que mató al 7º)** | fundaciones de B-p8 ≤ **15%** de los picks decidibles — la barra probó su valor y no se mueve |
| G-COBERTURA | ≥ RAW, secundaria, nunca sola |
| G-FALSOS | 0/1200 por noche |
| **G-PREDICADO (nueva)** | la tabla de calibración de 10 pares pasa 10/10 ANTES del run; y sobre los pares misma-historia conocidos del programa, bloqueo falso < 20% (vs ~50% medido del viejo) |

KILL = cualquier gate falla → documentar y parar. GO = consolidación+landing
con P-nuevo entra al pipeline nocturno flag-gateado → NAV-LOSS re-gate del
lens.

## Costos ya conocidos (se reportan, no sorprenden)

Historias bilaterales sin países compartidos siguen sin merge (Caspian 4→5 —
costo estructural aceptado del conjunct de país). Los 2 auto-fundados del 7º:
en este run un landing auto-fundado cuenta para G-LANDING solo si ninguna
identidad correcta EXISTÍA en el pool esa noche (lo decide el juez con los
recibos del pool — cierra el cuasi-tautológico que Pedro debía mirar).
