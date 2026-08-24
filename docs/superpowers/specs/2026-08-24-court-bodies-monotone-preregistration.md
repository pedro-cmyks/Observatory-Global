# Mini-prereg: corte-con-cuerpos MONÓTONO en zona gris (congelado ANTES del cableado)

**2026-08-24. Origen**: run 1 del prereg 08-12
(`docs/research/label-court/2026-08-24-court-with-bodies-run1.md`) — KILL en
la forma simétrica (flips 4/6) con asimetría limpia: hacia RECHAZO 4/4
correctos, hacia ACEPTACIÓN 0/2 (pegamento geo-temático). Pedro aprobó
cablear la forma monótona. Este documento congela reglas y barras ANTES de
que el paso corra su primera noche.

## Mecanismo (congelado)

- **Población nocturna**: topics ACTIVOS con `label_status` ∈
  {'partial','failed'} o NULL (withheld), no-junk. Rotación por
  `label_checked_at ASC NULLS FIRST`, **cap 120/noche** (la zona ~533 cicla
  en ~4-5 noches). Los `entailed` NO entran JAMÁS — intocables por
  construcción.
- **Evidencia**: ≤4 cuerpos de recibos congelados del topic (maquinaria
  article_fetch; gate SSRF; excerpt cap 500 chars — todos los parámetros
  del run 1, sin movimiento). Topic sin cuerpo fetchable = no-op contado.
- **Juez**: mismo prompt plano de la corte (paridad run 1), DeepSeek temp 0.
- **REGLA MONÓTONA (el corazón)**: escala entailed(0) < partial(1) <
  failed(2) ≤ too_broad(2). El veredicto-con-cuerpos SE APLICA solo si
  ENDURECE estrictamente el `label_status` vigente (partial→failed,
  partial→too_broad, failed→too_broad). NULL/withheld: solo puede estampar
  failed/too_broad (primer sello jamás ablanda). **Un veredicto B más
  blando que el vigente NUNCA escribe** — se ledgerea como
  `softening_ignored`.
- **Escritura**: `label_status` + `label_court_model='court-bodies-mono-v1'`
  + `label_checked_at`; ledger JSONL append-only con el estado PREVIO por
  fila (reversión = `--revert <ledger>`). Kill-switch:
  `ATLAS_COURT_BODIES_MONOTONE` (default on; off = paso entero fuera).
- **Dónde corre**: Step 2.7 del nocturno (tras la corte titular 2.6, ya sin
  heavy-lock post-M4). Costo cap: ~$0.06 + ~20 min/noche a cap 120.

## Barras (congeladas AQUÍ — chequeo a las 3 noches, ~2026-08-27)

1. **G-FLIPS-MONO**: muestra a mano de 20 endurecimientos aplicados (seed
   42) → **≥80% correctos, o kill-switch OFF + reporte** (la barra del
   prereg padre, re-congelada sobre la población que sí funciona).
2. **G-TESTIGO**: la clase fusión-de-portada (dt-16167 y equivalentes
   vivos) debe quedar endurecida, nunca re-ablandada por esta lane.
3. **G-CHURN (nuevo, el riesgo propio del cableado)**: la corte TITULAR de
   la noche siguiente puede re-ablandar lo endurecido (ping-pong). Se mide
   en el chequeo: **>30% de los endurecidos re-ablandados a las 3 noches =
   el cableado necesita la regla de precedencia en label_court (fase 2) y
   esta lane se apaga hasta tenerla.**
4. **G-NO-DAÑO**: `entailed` activos no caen por esta lane (imposible por
   construcción — se verifica igual contra el ledger); blob-rate y junk no
   suben.
5. **G-COSTO**: si una noche excede 2× el cap de costo/tiempo, el paso se
   auto-reporta y no bloquea el runner (non-fatal siempre).

## Qué NO es

No re-etiqueta (no propone labels), no toca serving directamente (escribe
el MISMO campo que la corte ya escribe), no scrapea hacia el sustrato (los
cuerpos viven y mueren en el juicio; solo el veredicto persiste). El
harness del run 1 queda congelado como instrumento del gate padre.
