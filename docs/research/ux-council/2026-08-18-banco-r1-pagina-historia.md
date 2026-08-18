# Banco de pruebas — Ronda 1: la página de historia — VEREDICTO

**Protocolo del spec del dial (§8, 2026-08-18): mockups dummy (colapso de
puente, 23 muertos, 4 recibos, chip de advertencia en AMBAS), dos ciegos sin
contexto con 4 TAREAS medibles, orden cruzado (lectora móvil A→B · analista
pro-dashboards desktop B→A).**

## Veredicto: V-A (página de periódico) gana — unánime

| Tarea | Lectora móvil (A→B) | Analista dashboards (B→A) |
|---|---|---|
| T1 cifra clave | **A por mucho** (titular, 0 scrolls; en B "el susto de confundir 412 señales con víctimas es real") | **A por paliza** (en B ignoró 4 números gigantes que no eran el que buscaba) |
| T2 quién la cuenta | **A** (caja + nombres juntos) | **A por poco** (B obliga a ensamblarlo) |
| T3 confianza | **A** (mismas evidencias, "en lenguaje de persona") | **A** (la nota del denominador = la razón más concreta de las dos páginas) |
| T4 volver | empate, leve A (idioma consistente) | empate, micro-punto A |

Ambos abrirían la A ante una noticia urgente. **El orden no contaminó: el que
vio B primero también eligió A.**

## Las reglas de diseño que salen (transferibles, no solo del mockup)

1. **La cifra vital va en el TITULAR.** El pecado capital de la variante
   instrumentos: jerarquía visual máxima a telemetría del sistema, cero al
   único número que importa en una tragedia.
2. **Métrica en prosa > métrica en tile.** «▲ +38/10h» comunicó lo mismo que
   `velocity +0.72 log-vol/6h`, verificable y en un segundo. La regla del
   analista: *«si tu métrica traducida a prosa es mejor que tu métrica en
   tile, el tile era decoración»*. Los tiles sobreviven solo para magnitud y
   pluralidad (412 señales · 14 medios · 2 idiomas — ambos los entendieron al
   vistazo).
3. **La honestidad ES el argumento de confianza.** Para ambos, la razón
   número uno de confiar fue la convergencia visible de recibos en la misma
   cifra + la nota del denominador («contado sobre lo que Atlas ingiere, no
   sobre toda la prensa»). Ningún sigma compró confianza; el denominador sí.
4. **Sigma y velocity crudos: solo posición Developer.** Incluso el analista:
   «4.1σ parece riguroso sin dejarme verificar nada». En LEER/OBSERVAR, la
   forma es prosa con el dato verificable.

## El punch-list de vocabulario (aplica al PRODUCTO REAL hoy, no al mockup)

Confusiones idénticas en ambos ciegos, todas presentes en prod:

- **«señales»** — jerga nunca definida; el peor caso: 412 como primer número
  de la página se leyó como posibles víctimas.
- **«recibos»** — «me suena a factura de la tienda» (evaluar: ¿"fuentes"?
  ¿tooltip primera-vez? decisión de copy, no de estructura).
- **chip `MAYOR`** — ambos preguntaron «¿mayor que qué?»; nunca se define.
- **«etiqueta bajo revisión»** — ambos: «¿revisión de QUÉ? ¿el titular está
  malo?» — el chip necesita decir qué es una etiqueta.
- **códigos país pelados** («RG», y en prod CD·IR·LR·MU — ya lo dijo el juez
  run-3) — expandir al nombre.
- **mezcla de idiomas** en una misma página — desorienta (en prod: el punch
  de huérfanos i18n ya listado el viernes).
- **«firehose»** — jerga en inglés dentro de la explicación honesta.

## Decisión que alimenta el spec del dial

La página de historia (§4) se construye **narrativa-primero**: titular con la
cifra → quién la cuenta (prosa con denominador) → recibos → instrumentos
después. Los instrumentos profundos (sigma, velocity, timelines crudos) son
vestuario de las posiciones hondas, no de la entrada. Ronda 2 (mundo en LEER)
y Ronda 3 (la forma del dial) siguen el mismo protocolo.
