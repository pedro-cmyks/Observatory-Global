# Banco de pruebas — Ronda 2: ¿dónde vive el mundo en LEER? — VEREDICTO

**Protocolo §8 del spec del dial: dos portadas dummy idénticas salvo la
posición del mundo (arriba «poco pintado» vs abajo como hoy), dos ciegos con
4 tareas de orientación, orden cruzado (lectora móvil TOP→BOTTOM · profesor
de geografía desktop BOTTOM→TOP).**

## Veredicto: el mundo va ABAJO en LEER — unánime como portada diaria

| Tarea | Lectora móvil | Profesor de geografía |
|---|---|---|
| T1 noticia local | **bottom** (es LO PRIMERO; arriba el mapa la empuja) | **bottom** («la noticia local ES la portada») |
| T2 dónde se concentra | **top** (respuesta regalada; abajo «no sabía que existía un mapa») | **top con trampa** (ganó la LEYENDA, no el gráfico) |
| T3 noticia global | **bottom** | empate, leve bottom |
| T4 el mapa | «arriba se ve pero estorba; abajo no estorba pero es invisible» | «un mapa decorativo arriba es un peaje que cobra todos los días» |

Ambos eligen **bottom** como SU portada. La única tarea que top gana (T2) la
gana por la **frase de la leyenda**, no por el dibujo — en ambas versiones,
ambos revisores supieron la respuesta leyendo texto.

## La síntesis (resuelve la tensión con la visión, no la contradice)

**La posición del mundo es FUNCIÓN del dial.** En LEER el mundo vive abajo
(colofón consultable — 3 de 4 tareas se resuelven sin él); al deslizar a
OBSERVAR **el mundo asciende al centro** y gana sus capas. El dial no solo
viste la habitación: **promueve el mundo**. La visión mundo-columna queda
intacta — la columna no está siempre en el lobby.

Corolario barato para LEER: la respuesta de T2 («dónde se concentra hoy») es
UNA FRASE — puede vivir arriba como línea de texto del masthead sin pagar el
peaje del gráfico. La prosa ya demostró (R1 y R2) que carga el dato mejor
que el dibujo.

## Reglas nuevas para el producto (fallas vistas por ambos)

1. **Jamás doble codificación sin definir ambas**: tamaño y oscuridad
   compitieron y «mi ojo le cree al tamaño». Una codificación, definida; la
   segunda solo si su leyenda existe.
2. **Un claim del mapa no puede contradecir el ranking**: «Riogrande
   concentra el día» vs «Europa lidera la edición global» — ambos lo
   marcaron como contradicción de apertura. Si «concentra» y «lidera» son
   métricas distintas, se DICE cuál es cuál, o el claim no se imprime.
3. **La leyenda es el producto**: dos rondas seguidas en que el texto
   responde y el gráfico decora. El gráfico debe ganarse su lugar con
   interactividad real (volar, filtrar) — que es exactamente lo que tiene en
   OBSERVAR y no en un thumbnail.

## Marginalia real (fuera del mockup, aplica a prod)

- «¿El periódico se llama ATLAS o THE DAILY INSTRUMENT?» — dos marcas en el
  masthead sin jerarquía (está así en prod).
- «señales» sigue sin definirse (tercera vez en dos rondas — refuerza el
  punch-list de vocabulario de R1).
- «resucitó tras 9 días quieta» — la firma temporal en verbo de máquina;
  candidata a registro de LEER («vuelve a moverse tras 9 días»).

## Estado del banco

R1 ✅ (página de historia: periódico) · **R2 ✅ (mundo abajo en LEER; el dial
lo promueve)** · R3 pendiente (la forma del dial: slider vs paradas
nombradas). ABIERTA-1 del spec queda RESUELTA por este veredicto.
