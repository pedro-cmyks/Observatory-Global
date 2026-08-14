# Atlas Query Protocol — preguntarle al sustrato, no a la pantalla — DRAFT

**Status: DRAFT para el ojo de Pedro (idea suya, 2026-08-14). Nada se
construye sin aprobación. Nace de la investigación de tres rutas
(`docs/research/investigations/2026-08-14-colombia-ruta-*`): la ruta C —yo
consultando la base directamente— encontró en minutos lo que la ruta A (la UI)
no pudo, y el mismo hallazgo probó por qué.**

## La idea de Pedro, en sus términos

> "Que hubiera como un API y que el API expusiera prácticamente la base de
> datos... no literal exponerla, sino un protocolo: si tengo una pregunta
> compuesta, poder acceder a la información que tiene Atlas y a la manera en
> que se clusteriza, sin ir al UI manual. Y eso tendría que ser lo mismo que
> yo encontraría buscando de manera visual — como un doble cheque."

Dos cosas en una: **una puerta de consulta** y **un test de consistencia**.

## Por qué ahora (la evidencia ya existe)

La ruta C respondió en ~6 consultas lo que la UI no pudo en 22 minutos:
un evento en 9 identidades, fragmentos con recibos bielorrusos, 60 de 72
señales políticas sin clusterizar. Ninguna de esas preguntas es exótica: son
"¿qué identidades cubren este evento?", "¿de qué países son los recibos de
este hilo?", "¿dónde aterrizaron las señales que mencionan X?".

**El sustrato responde preguntas que la UI no sabe formular.** El protocolo es
la forma de preguntar sin pedirle a la pantalla que invente una vista.

## Qué NO es

- **No es SQL expuesto.** Ni superficie de ataque, ni contrato que se rompe
  cuando migra una tabla, ni una forma de leer PII o el corpus crudo completo.
- **No es un chat que "consulta la base".** Un lenguaje natural sin verbos
  medidos vuelve a poner un modelo entre el analista y el dato — exactamente
  lo que el proyecto lleva un mes sacando del camino.
- **No es una segunda verdad.** Si el protocolo y la UI difieren, uno de los
  dos está mal y el sistema debe DECIR cuál — esa es la mitad "doble cheque".

## Qué SÍ es: verbos medidos sobre el sustrato

Un endpoint (`POST /api/v3/query`) que acepta una **composición de verbos**,
cada uno correspondiendo a una medición que Atlas ya hace. Boceto:

```
{ "ask": [
    { "identities_covering": { "event_terms": ["terremoto","earthquake"],
                               "country": "CO", "window_days": 14 } },
    { "receipt_geography": { "of": "$1" } },
    { "unclustered_signals": { "terms": ["espriella","golán"], "window_hours": 24 } }
] }
```

Verbos candidatos (todos = mediciones existentes, ninguno nuevo):
`identities_covering` · `receipt_geography` · `voice_mix` ·
`unclustered_signals` (¿qué se ingirió y no se volvió historia?) ·
`identity_timeline` · `siblings` · `label_court_state` · `coverage_gaps`.

**Cada respuesta carga su base**: la ventana medida, la población, el conteo
de lo que NO pudo medir. La disciplina de ingest_basis y de reason-codes que
ya rige la UI, aplicada al contrato.

## La mitad que hace la idea grande: el doble cheque

Un test que corre las mismas N preguntas por los dos caminos —protocolo y
serving de la UI— y **falla cuando divergen**. Es el instrumento que habría
cazado, sin que un humano mirara:

- el conteo de fuentes topado en 20 mientras la muestra traía 36 dominios,
- "18 · last 7d" contra 323 de por vida,
- una historia servida como única cuando la base tiene nueve,
- el chip VE sobre una historia colombiana.

Es decir: **el protocolo no es solo una puerta nueva, es el detector de que la
puerta vieja miente.**

## Preguntas abiertas (para la sesión de diseño)

1. ¿Autenticación? Hoy la API está abierta con rate-limit por IP. Un verbo que
   barre el sustrato pesa más que una lectura de artefacto — bucket propio, y
   quizá token, es decisión de Pedro.
2. ¿Hasta dónde llega la composición? Encadenar `$1` es potente y es también
   por dónde se cuelan las consultas caras. Presupuesto por verbo, medido antes
   de fijar (la disciplina de siempre).
3. ¿Es también la puerta para agentes? Sería el camino natural para que una
   investigación como la de hoy corra sin browser — y para que Atlas sea
   consultable por otras herramientas.
4. ¿El "doble cheque" es test de CI o cron nocturno con ledger? Mi inclinación:
   cron, junto al sello, escribiendo divergencias al ledger de confiabilidad.

## Gate pre-registrado (al aprobar, antes de construir)

- **G-PARIDAD**: 10 preguntas cuyas respuestas existen en ambos caminos →
  coinciden al dígito, o el reporte nombra la divergencia y su causa.
- **G-INVESTIGACIÓN**: la investigación Colombia re-corrida SOLO por protocolo
  responde ≥ lo que respondió la ruta A por UI, en menos tiempo.
- **G-COSTO**: ninguna consulta compuesta del set excede el presupuesto medido
  (fijar tras medir, nunca antes).
- **G-HONESTIDAD**: toda respuesta carga base y ventana; una lane caída se
  reporta como no-medida, jamás como cero.
