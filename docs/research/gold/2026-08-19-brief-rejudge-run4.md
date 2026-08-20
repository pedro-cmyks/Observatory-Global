# Re-juez ciego del Brief — run 4 (2026-08-19) — G-LECTURA: PASS

**Protocolo idéntico a runs 1-3. Condiciones: prod con el dial P1.5 recién
desplegado (en sitio), SW desregistrado antes de leer; noche/madrugada DENTRO
de la ventana degradada del bloat de índices (reindex agendado corría después)
— la salud del serving de este run está contaminada y así se lee.**

## Veredicto contra las barras

- **(a) Distinto de un wire, sin preguntarle → PASS.** «The seal... that's an
  epistemic boundary I've never seen a news product draw.» Recibos como
  unidad de primera clase, ausencia honesta («no blindspot is claimed»),
  auto-acusación (LABEL UNDER REVIEW, «1 story cleared the bar but could not
  be printed»).
- **(b) Lectura completa + razón de volver → PASS.** **La página país de
  Irán** — diez minutos cruzando tankers de Hormuz + bloqueo naval + drones
  perdidos contra el WTI +14.9% del strip y el tono −9.4: «assembled a
  picture of a live Gulf escalation that my usual front page would have given
  me as one headline». Vuelve por las páginas país y las etiquetas de
  honestidad — «tentatively yes».

## La frase del run

> «Genuinely the most interesting news interface I've cold-read... but today
> it's an instrument that's **more honest than it is right**: the honesty
> machinery works; the story-making underneath it wobbles, and the plumbing
> dropped me three times in one sitting.»

## Qué cambió respecto al run-3

- **La mejor lectura migró**: run-3 fue Near You; run-4 es la **página país**
  — la puerta país madura como el lugar donde el día cohere.
- **El dial: CERO menciones.** El lector frío no lo descubrió ni lo tocó.
  Dato de descubribilidad para el banco R3 (la forma del dial), no un fallo
  del mecanismo (los gates de P1/P1.5 pasaron; la invitación a deslizar no
  existe aún).
- La traducción en sitio («See original» flip sin reload) citada como novedad.

## Lo consistente (4 runs): la identidad

El ejemplo más nítido de la serie: **los mismos misiles con dos países** —
portada «UAE Detects Iranian Missiles» SIN marca (y sus recibos ni mencionan
UAE) vs página país «Jordan Intercepts Iranian Missiles — LABEL UNDER
REVIEW». Solo uno marcado. Más: vidente de fútbol como recibo de «Domestic
Violence Arrests» (3.4σ rising); NABU (27,883 señales, 3× el lead) recibida
por propaganda de TASS; «India Tragedies» = 882 señales resumidas por dos
titulares de un solo tabloide griego («nothing editorialized, but nothing
sanity-checked either»).

## Lo operativo del run (cruzado con el dev-click-parity del mismo día)

| El ciego sintió | El dev midió (2026-08-19-dev-click-parity.md) |
|---|---|
| Masthead «PARTIAL» | **F3-a**: sello `sealed_full` pleno impreso como PARTIAL — el frontend solo conocía `ready`. Fix de una línea (aplicado) |
| Primera carga muerta ~20s | **F3-b**: daily-pub 500 vía proxy + retry abortado a 12s con latencia real 7-23s (noche de bloat) |
| «WHY» sellado con `surprise=2.5787` crudo | Residuo de máquina en slot de lector — vagón de registro pendiente |
| Console re-escopó su Brief a Irán «sin elegirlo» | **F3-d**: BACK desde el console deja `?theme&country=` en /brief — mergeFocusIntoParams sobrevive el popstate. Pregunta de diseño: el acarreo del foco (invariante 4) vs la sensación de no-elegido |
| 502/503s en muro, console a 40s | La ventana del bloat (signals_v2 3.9GB de índices) — reindex agendado 04:35 |

**El par de instrumentos triangula**: el extraño SIENTE exactamente donde el
dev MIDE. El dev además certificó lo contrario: **los 8 clicks del contrato,
verdes al dígito** («la UI sirve lo que la base dice») — las mentiras de
pantalla del 14 están muertas; lo que queda es identidad (Z1), orden de
pipeline (F3-c: el sello congeló coherencia 8 min ANTES de la pasada — NABU
grab-bag en base, servida sin ◈) y la salud nocturna de la base.

## Serie G-LECTURA

| Run | Fecha | Veredicto | La crítica que quedó |
|---|---|---|---|
| 1 | 08-12 | PASS | — |
| 2 | 08-13 | PASS | volumen ≠ importancia (el lead jalapeño) |
| 3 | 08-18 | PASS | «labels roughly a coin flip» + puerta a cuarto oscuro |
| 4 | 08-19 | **PASS** | «more honest than it is right» + la plomería de la noche enferma |

La crítica sigue migrando hacia adentro: superficie (r2) → motor (r3) →
motor + infraestructura (r4). La forma ya no es el problema.
