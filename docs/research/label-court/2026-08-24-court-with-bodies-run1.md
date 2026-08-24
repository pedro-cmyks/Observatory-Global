# Corte-con-cuerpos — run 1 contra el prereg 2026-08-12

**2026-08-24. Harness**: `backend/scripts/measure_court_with_bodies.py`
(brazo H = `_ds_judge` de la corte nocturna importado verbatim, 8 recibos;
brazo B = mismo prompt con titular+excerpt de cuerpo cap-500 pre-fijado,
≤4 cuerpos/topic vía la maquinaria article_fetch; brazo internet declarado
no-corrido). **Población**: zona gris real = 533 activos failed/withheld;
corrida n=40 seed 42 + 6 testigos-Ormuz vivos FORZADOS. **Cohorte extra
declarada sin gate**: los 15 condenados del ledger Z1 de hoy.
**Artefactos**: `2026-08-24-court-bodies-20260824T190303Z.{json,jsonl}`
(cada juicio pareado + fetch outcomes). Wall 578s · 43K tokens · ~$0.02.

## VEREDICTO contra las barras congeladas

| medida (barra) | medido | veredicto |
|---|---|---|
| 3 · Cobertura (≥30% fetchable o KILL) | **65%** gris (26/40 pareados) · 73% condenados | **PASS** |
| 1 · Precisión de flips (≥80% a mano o KILL) | 6 flips, juicio a mano abajo: **4/6 = 66.7%** | **FAIL → KILL en la forma simétrica** |
| 2 · Testigos-fusión (MÁS rechazo, jamás menos; un fusión→entailed = bloqueante) | el testigo-fusión vivo (dt-16167, EL que sirve portada) fue MÁS rechazado (partial→failed) ✓ · **ningún fusión pasó a entailed** · PERO 2 mislabels de la misma familia Ormuz fliparon HACIA entailed (abajo) | **PASS estricto · hallazgo reportado** |
| 4 · Costo (reportar) | ~1.1K tokens/topic ≈ $0.0004/topic juzgado · ~10.5s/topic (fetch domina) → zona gris completa (533): ~$0.25 + ~1.5h/noche | reportado |

## El juicio a mano de los 6 flips (la medida que mata — y lo que revela)

| topic | flip | ¿correcto? | por qué |
|---|---|---|---|
| dt-4852 "Russian Strikes Kill Civilians" | partial→failed | ✓ | los cuerpos muestran ataques MUTUOS RU↔UA; el label unilateral no describe la mayoría |
| dt-16167 "Trump Threatens Iran Over Hormuz" | partial→failed | ✓ | **el testigo**: los cuerpos son guerra RU-UA — la fusión queda expuesta y el court la rechaza MÁS (la tesis del prereg, cumplida) |
| dt-1747 "Serena Williams Wimbledon…" | partial→failed | ✓ | cuerpos = resultados de Cincinnati; label rancio |
| dt-8482 "Iran Rejects Hormuz Proposal" | failed→**entailed** | **✗** | contenido cohesivo = Irán rechaza claim de misil de UAE; el brazo H tenía razón ("different story"); el B pegó por zona+tema ("Gulf ≈ Hormuz") |
| dt-2614 "Strait of Hormuz Tanker Incidents" | partial→**entailed** | **✗** | misiles UAE-Irán ≠ "tanker incidents"; mismo pegamento geo-temático |
| dt-16192 "Russia Threatens UK Over Drones" | partial→failed | ✓ | cuerpos = ataques a Ucrania, no amenaza a UK |

**La asimetría ES el hallazgo**: los flips hacia RECHAZO son 4/4 correctos;
los flips hacia ACEPTACIÓN son 0/2 — ambos por el mismo mecanismo (cuerpos
que comparten región+tema hacen que el juez perdone el label). Los cuerpos
hacen al court más estricto CORRECTAMENTE; cuando lo ablandan, se equivoca.

## Cohorte condenados (observación, sin gate)

11/15 pareados. El brazo titular de HOY ya falla 9/11 — la maquinaria
nocturna viene alcanzando a la clase condenada desde la medición Z1 de esta
mañana (muestras de recibos distintas). Flips: dt-445 partial→failed ✓
(dirección correcta) · dt-2726 failed→partial (hacia aceptación —
consistente con el patrón sospechoso de arriba).

## Caveats declarados

- **Confound de set de evidencia**: H ve 8 titulares, B ve ≤4 cuerpos (los
  fetchables) — un flip puede reflejar composición de muestra, no solo
  profundidad. Mitigación en un v2: B judga sobre los MISMOS recibos que H
  con cuerpo donde lo haya y titular donde no.
- n=6 flips — dirección clara, magnitud imprecisa.
- Un solo juez (DeepSeek temp-0), mi lectura única de los flips; ledger
  completo para re-juicio.

## Qué deja el KILL (la forma que sí sirve, pre-registrable)

El prereg preguntaba si los cuerpos cambian veredictos "en la dirección
correcta". Respuesta medida: **solo en una dirección**. La forma cableable
que la evidencia soporta es **corte-con-cuerpos MONÓTONO**: en zona gris,
el veredicto con cuerpos solo puede CONFIRMAR o ENDURECER (failed/
too_broad), jamás ablandar hacia entailed. Bajo esa regla, los 6 flips de
esta corrida quedan 4/4 correctos y 2 ignorados — 100% sobre lo usable, con
el testigo-fusión de portada correctamente derribado. Cableado propuesto
(NO ejecutado — palabra de Pedro): paso nocturno zona-gris-only, regla
monótona, kill-switch propio, mismo cap de costo (~$0.25/noche); su
mini-prereg hereda las barras 2-4 intactas y re-congela la 1 sobre flips
monótonos.
