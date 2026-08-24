# M1-A2 — la lane sombra construida + 4 iteraciones de calibración: el bloqueador tiene nombre

**2026-08-24 (tarde). Mandato**: prereg M1-GATE (familia ① elegida AM) →
"fix en sombra → las 6 barras". **Qué pasó**: la lane sombra existe
(`backend/scripts/m1_shadow_attach.py`, 13 tests, dry-run default,
escritura aislada `engine_version='m1-shadow-v0'`, ledger reversible) y su
calibración de 4 iteraciones (n=50/50/50/100, ~$0.05 DeepSeek total,
ledgers en `shadow-ledger/`) produjo un veredicto que cambia el orden del
plan motor.

## Las 4 iteraciones (misma mecánica: top-5 cos≥0.80 sobre active∪candidate → vetos → juez)

| v | cambio | adjunta | mi lectura de precisión* | aprendizaje |
|---|---|---|---|---|
| 0.1 | (bug de paridad: población contra CUALQUIER motor) | — | — | "con historia" DEBE medirse contra v1-compat (el serving); sin eso la muestra se sesga a señales sin embedding |
| 0.2 | paridad v1 + veto persona-amplio + bucket-DF | 18% | ~2/9 estricto | el juez elige al hermano listado PRIMERO (sesgo de posición); veto persona-amplio mató 27% de candidatos incl. hogares correctos |
| 0.3 | shuffle seedeado + veto persona-en-label + prompt anti-hermano + veto coherencia-país post-juez | 22% (proy. G-RECALL 23.3%, CI 14-36) | ~50-65% criterio A0 | el veto-país mata gemelos ENTRE países (bus NL→"Peru Plane Crash"); quedan gemelos DENTRO de entidad/país y buckets que se cuelan por DF |
| 0.4 | doble voto (binario confirma el pick) | **9%** (proy. 10.5% < barra 20%) | 1-2/9 | **el binario confirma los MISMOS gemelos** (Air India bird-hit→"Hydraulic Failure"; Titans-Seahawks→"Vikings-Giants") — recall desplomado, precisión igual |

\* un lector, muestras chicas, ledger completo para re-juicio. No es gold;
es la dirección.

## El hallazgo que manda

En cada fallo persistente el candidato correcto O no existe O **existe
VARIAS VECES**: 5 topics marítimos-Hormuz (el correcto "Iran, Qatar, Oman
Clash Over Hormuz Strait" estaba en el top-5 y el juez eligió al hermano),
4 topics-Panettiere, DOS topics con label idéntico "Neutrogena Backlash
Response". **Con el espacio de identidades fragmentado, "la historia
correcta" no es un destino bien definido — ningún juez barato (ni caro)
puede elegirla de forma estable.** La dispersión de argmax que el Z4 midió
en las señales es la MISMA fragmentación vista desde los topics.

**Consecuencia para el plan motor**: la última milla de G-PRECISIÓN de M1
depende de M2 (Z1 predicado de labels + consolidación de gemelos — el 8º
gate YA pre-registrado) o de cambiar el DESTINO del adjunto a la FAMILIA
(familia ② del prereg, "argmax-familia… requiere Z1/Z3 maduros" — el
prereg nombró esta dependencia; hoy quedó demostrada con datos).

## Lo que SÍ quedó ganado

- La lane sombra completa y reversible, con población en paridad exacta
  con el serving, sample seedeado con CI, y ledger por decisión.
- G-RECALL es alcanzable: 20-23% proyectado (barra 20%) ANTES del doble
  voto — el conteo no es el problema.
- Vetos medidos que se quedan: bucket-vago por DF (772 topics fuera del
  pool + junk 2,273 + too_broad 50), persona-en-label, coherencia-país.
- El costo nunca fue barrera: ~$0.0001-0.0002/señal.
- Bono del día: "Guinea Landfill Landslide" — la señal que era el recibo
  FALSO del card de Colombia — hoy la sombra la adjunta a su topic exacto.

## Decisión para Pedro (el arco espera esto)

1. **(mi voto) M2 primero**: correr el Z1/consolidación (8º gate
   pre-registrado) para des-fragmentar el espacio de destino, y volver a
   M1-sombra sobre un espacio limpio. El plan motor decía "M2 después de
   M1"; la evidencia de hoy invierte el orden de la última milla.
2. Familia ② ya (adjuntar a FAMILIA/umbrella en vez de topic exacto) —
   sidesteps los gemelos sin esperar Z1, pero cambia el contrato de
   serving (¿qué historia abre el lector?).
3. Seguir iterando prompts/contexto en ① — desaconsejado: 4 iteraciones
   muestran rendimientos decrecientes contra un espacio fragmentado.

*Script: `m1_shadow_attach.py` (--sample/--hours/--execute; dry-run
default). Los runs del gate real, cuando toquen, van con --hours 168 (la
ventana del prereg). Ledgers: shadow-ledger/shadow-20260824T*.jsonl.*
