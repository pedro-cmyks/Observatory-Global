# Investigación Colombia — RUTA C: la base de datos vs lo que Atlas sirve

**Método**: consultas directas a prod (dynamic_topics, topic_members, signals_v2),
sin pasar por la UI ni por la búsqueda. Pregunta: ¿lo que Atlas MIDE difiere de
lo que Atlas MUESTRA?

**Respuesta corta: sí, y por un factor de ~150.**

---

## 1. Una sola noticia, NUEVE identidades vivas

El terremoto de Colombia existe en la base como nueve topics activos separados,
sin hermanarse, cada uno con su etiqueta congelada en un momento distinto de la
MISMA historia:

| topic | señales | corte | etiqueta |
|---|---|---|---|
| dt-12927 | **2,257** | entailed | Colombia Declares Disaster After Deadly Earthquake |
| dt-12928 | **1,799** | **failed** | Colombia Earthquake Kills 111, Injures Thousands |
| dt-12910 | **1,277** | entailed | Colombia Earthquake Death Toll Rises to 132 |
| dt-248 | 778 | entailed | Colombia Earthquake Death Toll Rises Past 130 |
| dt-244 | 499 | partial | Colombia Earthquake Death Toll Rises Past 132 |
| dt-510 | 410 | entailed | Magnitude 7.4 Earthquake Strikes Colombia |
| dt-4959 | 368 | entailed | EU Activates Satellite Aid for Colombia Earthquake |
| dt-517 | 331 | entailed | Colombia Earthquake Death Toll Rises to 132 |
| dt-242 | 323 | entailed | 7.4-Magnitude Earthquake Kills Dozens in Colombia |

**~8,000 señales** de un evento, partidas en nueve. Tres etiquetas dicen
literalmente lo mismo ("Death Toll Rises to/Past 130/132"). La UI le mostró a
Pedro **18** (el último snapshot de UNO de los nueve). El evento completo es
~450 veces eso.

Es **dispersión de argmax** — la enfermedad nombrada el 2026-07-30 — a escala
completa, sobre la historia más grande de la semana en el país del usuario.

## 2. Los fragmentos están contaminados

Los miembros reales, por país e idioma:

| topic | países de sus recibos | idiomas |
|---|---|---|
| dt-12928 "Colombia Earthquake Kills 111" | **RU:14** CO:8 JP:3 CN:3 | en:15 **ru:12** |
| dt-12910 "Colombia Death Toll 132" | **BY:8 (solo Bielorrusia)** | **ru:8** |
| dt-244 "Colombia Death Toll Past 132" | CO:14 **BY:9 VE:8** | xx:24 ru:11 |
| dt-12927 (el insignia) | CO:33 DE:24 **VE:24** ES:2 | xx:68 de:18 |
| dt-242 (el que abrió Pedro) | **CO:21 — limpio** | en:21 |

`dt-12910` es una etiqueta colombiana sobre recibos **exclusivamente bielorrusos
en ruso**. `dt-12928` — 1,799 señales, la segunda más grande — lidera en RUSIA.
El corte ya reprobó a esa (`failed`) y sigue activa y sirviéndose.

Y el chip **VE** que Pedro vio en la historia insignia sale de aquí: VE es el
tercer país de sus miembros (24 de 83), casi empatado con Alemania. Los recibos
en sí son buenos — pulzo, La FM, El Informador, La Jornada, con la cifra
correcta de 281 muertos.

## 3. La política SÍ está en los datos — y es invisible

En 24 horas de datos crudos:

| tema | señales | fuentes |
|---|---|---|
| **De la Espriella** | **72** | 38 |
| emergencia económica | 13 | 13 |
| Golán | 10 | 8 |
| UNGRD | 9 | 6 |

Dónde aterrizan:

- **Espriella: 60 de 72 sin topic asignado.** Las que aterrizan: 2 en
  "Earthquakes in Mexico", 1 en "Merz Rentenreform Kritik" (¡reforma de
  pensiones alemana!), 1 en "SEP Closes Militarized Schools", 2 en la historia
  del terremoto, 2 en "Milei in Colombia".
- **Golán: 10 de 10 sin topic.** Cero.

Atlas ingirió la posesión, el Golán, la emergencia económica y la UNGRD. Nada
de eso se volvió historia. El hilo político que Pedro pidió **existe en la
base y no existe en el producto**.

## 4. La corrección honesta sobre los números de dt-242

Antes le dije a Pedro que las 323 señales eran de la ventana de 7 días. La base
lo corrige: `agg_n_signals = 323` **es un agregado de por vida** — la etiqueta
"lifetime" era correcta. Lo que sigue mal:

- **"18 · last 7d"**: 18 es el `recent_n` del ÚLTIMO SNAPSHOT (una pasada de
  clustering), no una cuenta de 7 días.
- **`first_seen = 2026-06-25`** — la identidad es de junio, el terremoto fue
  el 10 de agosto. Ese topic **existía antes del evento** y fue re-etiquetado
  cuando la cobertura lo absorbió. Sus 323 "lifetime" incluyen señales que no
  tienen nada que ver con el sismo.

## 5. Qué prueba esto

| Capa | Veredicto |
|---|---|
| **Ingesta** | SANA. Los datos están: 8,000 señales del sismo, 72 de Espriella, el Golán, la UNGRD, prensa colombiana real con cifras correctas. |
| **Clusterización / identidad** | **ROTA para eventos grandes.** Un evento → 9 identidades; señales rusas y bielorrusas dentro de historias colombianas; 83% de la política sin asignar. |
| **Serving** | Muestra un fragmento de una identidad fragmentada, con la etiqueta congelada en una cifra vieja ("Kills Dozens" cuando ya van 281). |

**El cuello de botella no es la data. Es la identidad.** Exactamente lo que el
programa de landing (gates 8-9, reloj de condenación) fue creado para atacar —
y esta es la evidencia más nítida que ha producido el proyecto de por qué
importa: no es un caso de laboratorio, es la portada del país del usuario.
