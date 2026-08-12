# Corte-con-cuerpos — pre-registro (2026-08-12, ANTES de toda corrida)

**Pregunta**: cuando el juicio por titulares no clara (el letrero "does not
clear / likely conflates"), ¿el TEXTO COMPLETO de los recibos cambia el
veredicto en la dirección correcta? Base medida que lo motiva: body-embeds
separan mejor que titulares (F3b: AUC 0.9983 vs 0.9208). Frontera vigente
que este experimento respeta: lo scrapeado NO escribe sustrato — corrida
offline a ledger; cablear solo tras gate PASS + palabra de Pedro.

## Diseño

**Población**: topics activos con `label_status='failed'` o court-withheld
de la última pasada nocturna (la zona gris real, no muestreo inventado).
Cap N=40 para la corrida. El testigo de conflación conocido (clase
"US Bombards Iran Over Ormuz" con IMF-Siria adentro) entra forzado si
sigue vivo — es el caso que Pedro señaló.

**Intervención**: por topic, fetch de cuerpos de sus recibos congelados
(maquinaria article_fetch existente: trafilatura, gates SSRF/dominio,
≤4 recibos/topic) → el MISMO prompt de corte pero con evidencia = excerpts
de cuerpo (cap de chars fijado antes de correr) en vez de titular-solo.
Juez: mismo modelo/cadena que la corte nocturna (paridad).

**Brazo opcional "buscar en internet"** (medido aparte, mismas barras): la
lane DOC 2.0 existente busca los términos del label; los top títulos
externos entran como TERCERA evidencia. Honesto sobre su flakiness (429s
medidos) — un brazo que no responde se reporta, no se rellena.

## Medidas y barras (congeladas AQUÍ)

1. **Precisión de flips**: de los veredictos que CAMBIAN
   (failed→entailed o entailed→failed), hand-check de 20 muestreados.
   **Barra: ≥80% de flips correctos a mano. <80% = KILL** (los cuerpos
   añaden ruido, no señal).
2. **Detección de conflación**: sobre los testigos-fusión conocidos, el
   cuerpo debe hacer que la corte RECHACE el label fusionado más
   (nunca menos). **Un solo testigo-fusión que pase a entailed con
   cuerpos = hallazgo bloqueante a reportar.**
3. **Cobertura**: yield de fetch sobre la zona gris. **<30% fetchable =
   KILL** (no puede cubrir la población que pretende juzgar).
4. **Costo**: $/topic y min/noche extrapolados a la zona gris completa —
   se REPORTA antes de cualquier cableado; no hay barra porque el
   presupuesto es decisión de Pedro.

## Qué NO es
No re-clusteriza, no re-etiqueta, no toca serving. Un solo output: el
ledger de juicios pareados (titular-solo vs con-cuerpo vs +búsqueda) +
el reporte con las 4 medidas. Si pasa: el cableado propuesto sería
corte-con-cuerpos SOLO en zona gris, con su propio kill-switch.

## Cuándo corre
Con espacio de motor — después del reloj de condenación (~08-14) para no
abrir dos frentes de motor a la vez (la regla del arco de landing).
