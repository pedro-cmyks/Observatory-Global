# Pre-registro: el trigger de condenación — cuándo re-corren los gates de landing

**2026-08-03 · Congelado (aprobado por Pedro: "congela el trigger en 15%").
Cierra el arco de labels (gates 7-9) con un número que se cruza solo en vez de
un "veremos". Movimiento post-resultados = inválido.**

## El instrumento

**Tasa de condenación** (nacida del KILL del 9º gate,
`2026-08-03-label-adoption.md` §Pedro-eyes-1): sobre una muestra de **60**
identidades vecinas-cercanas que PASAN los filtros de elegibilidad vigentes
(no blob-confirmado, no `failed`, no junk, no umbrella), juzgar con quote-gate
si los recibos PROPIOS de cada identidad soportan su PROPIO label.
Condenación = % que falla. **Baseline hoy: 39%** (medido por el 9º, semilla 42,
protocolo congelado en `measure_label_adoption.py`).

Es la métrica de salud del pool DESPUÉS de la maquinaria de limpieza — mide lo
que los filtros no alcanzan.

## Cadencia

Cada **3 noches** (costo: 60 juicios DeepSeek ≈ centavos), mismo protocolo y
mismo tamaño de muestra, semilla NUEVA por corrida (la salud del pool se mide
en población, no en las mismas 60 filas); cada corrida agrega una línea al
ledger `docs/research/recall-229/condemnation-ledger.jsonl`
(fecha, semilla, n, condenados, tasa, ids condenados).

## El trigger (congelado)

**Condenación ≤ 15%** en una corrida → se dispara el re-run MECÁNICO de los
harnesses fidelity-locked:
1. 8º gate (`measure_landing_predicate.py`, arms A y B-p8) contra el pool
   sanado — **mismas barras congeladas** (G-FOUNDING 15%, G-FALSE-BLOCK <20%,
   G-LANDING ≥⌈⅔⌉ y >prod, K2/784/falsos).
2. Si el 8º pasa: 9º (`measure_label_adoption.py`) — mismas barras
   (G-ADOPCIÓN ≤5%, etc.).
3. Lo que pase con barras intactas entra al pipeline flag-gateado → una noche
   medida → NAV-LOSS re-gate → `STORY_LENS_AUTO=on`.

Una corrida entre 15% y 25% dos veces seguidas = zona de interés: se reporta
la tendencia, NO se adelanta el trigger. El 15% no se negocia ni arriba ni
abajo después de ver datos — exactamente la lección de G-FOUNDING, que mató
dos gates y valió cada kill.

## Qué NO es esto

No es un gate nuevo de mecanismo — el arco de labels está CERRADO (síntesis en
`2026-08-03-label-adoption.md` §9). Es el reloj despertador del re-run.
