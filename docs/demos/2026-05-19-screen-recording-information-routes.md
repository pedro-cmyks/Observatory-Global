# Screen Recording: Information Routes Review

Fecha: 2026-05-19
Video: `/Users/pedro/Desktop/Screen Recording 2026-05-19 at 13.15.40.mov`
Duracion: 6:26

## Transcript

> Nota: transcript automatico con correcciones ligeras de puntuacion. Algunos nombres propios pueden requerir verificacion manual.

**00:00-00:08**  
Bueno chat, entonces estaba yo mirando el mapa, cierto? Y dije: que significa este punto? Y doy clic.

**00:08-00:18**  
El punto me lleva a Sudan. Me dice que esta tres veces por encima de lo normal.

**00:18-00:31**  
Sudan shows 177 senales in this 24 hour window, led by crisis event, health and conflict violence. Pues si, me dice que esta pasando algo, cierto? Que el sentimiento es negativo, mas o menos, crisis event.

**00:31-00:45**  
Esto es lo que mas esta contribuyendo, me imagino tanto al volumen como al sentimiento, no se. Pero mas aqui abajo esto no me dice nada, esto no me dice nada.

**00:45-01:05**  
Pues si, las fuentes, pero que dicen? Me gustaria tener como el... o si esta agrupado de esta manera, pues yo se que eso lo estamos realizando con los nuevos temas. Cuando tengamos mayor diversidad de temas va a ser mucho mas facil poder surtir mejor todos los paneles que tenemos centrales, porque si les falta como calidad.

**01:05-01:23**  
Entonces voy a Crisis Event. Click to open Crisis Event. Me parece bien. Se corta un poquito la imagen, pero esta bien. Crisis Event. Ah, ya si mostro, porque ahorita le di y dio cero senales.

**01:23-01:43**  
Bueno, Crisis Event average en Sudan. En este momento, pues en Sudan, el sentimiento parece que siempre ha sido negativo. Esto no se como interpretar un negativo de menos 58. Bueno, 73 me imagino, pues que todo el mundo se esta matando entre si.

**01:43-02:08**  
Y en este momento tambien menos 52, pero es horrible. El Crisis Event esta relacionado con salud, con cancer, con disease, breast cancer, con las montanas y con disease cancer. Se esta muriendo mucha gente de cancer en...? A ver, y aqui la gente esta buscando emergencies, emergencies, emergencies.

**02:08-02:17**  
Related topics, core and same signals, click to explore. No se como usar esto, no se como usar esto.

**02:17-02:27**  
People mentioning. Y quien es esta persona, Malhar Yamur? Vamos a ver que cargue Malhar Yamur.

**02:27-02:42**  
Sabes que? No se si podemos ver ahi: se puede hacer una busqueda a Google, se puede hacer un query de Wikipedia y poner como informacion de la persona. Yo se que no es el mejor source, pero pues como tener algo ahi de que es. Considerarlo.

**02:42-03:03**  
Bueno, Malhar Yamur. Y hablan de manera... framing split. Nadie habla de manera positiva con el, todo el mundo ahora negativo. Y que dicen?

**03:04-03:16**  
Traffic police deploy speed radar gun on national highway to curb over speeding. Esto es lo mismo, esto es lo mismo, esto es lo mismo, esto es lo mismo, todo dice lo mismo. Pues no se que estan diciendo.

**03:16-03:29**  
Volvamos atras. Como vuelvo atras? Se me perdio lo que estaba viendo de Sudan. Bueno, digamos que como para considerar eso.

**03:31-03:53**  
Luego tengo este: Israeli forces fired shots... Se me bajo. Ahora tengo... no, espera, que se me hizo? Ya se me perdio. Me gustaria que si yo me paro en uno, que el feed pudiera seguir pasando detras del que yo seleccione, para yo poderlo leer con tranquilidad, porque la verdad si se me perdio.

**03:55-04:22**  
Bueno, y otra cosa: que empiece a contar el tiempo de agregacion una vez lo renderice, asi todos los que estan en pantalla tienen un tiempo diferente. Yo creo que seria mas bonito que ese. Porque este tiempo que dice, si lo estamos mostrando en la ventana de 24 horas, son cosas que han pasado en 24 horas. Entonces se intuye que esta en ese tiempo y que lo ultimo que entra es lo mas nuevo.

**04:22-04:43**  
Bueno, digamos que me llamo algo la atencion de alla. Dejo de agregar. Este era. Bueno, que dice? Israeli forces fired shots at Gaza flotilla, 48 boats intercepted. Creo que es una noticia bien vieja.

**04:43-05:06**  
Yo creo que es importante considerar la fecha de la noticia. Eso si para clasificarlo internamente como en la tabla de informacion, cierto? Intentar agregar lo mas nuevo a lo nuevo. La fecha de publicacion es importante tenerla. Entonces tenemos dos tiempos: el tiempo en el que se renderice, que es ese que esta aqui, y tenemos la fecha de publicacion, que es la que sabemos en que ventana de tiempo ubicar la noticia.

**05:06-05:31**  
Y de seguir. Pero bueno, entonces el tema... como sigo de aqui? Maritime Incident, que es diferente de Maritime. Bueno, me voy a ir por el tema Maritime Incident, sobre ese tema que me salio ahi. Entonces yo me imagino que debe ser algo que sucedio en las ultimas 24 horas.

**05:33-05:52**  
A ver, que cargue, que cargue. Bueno, esto de aqui mas o menos lo entiendo, cierto? Pero los paises no tienen ese color. En que parte esta? Ah, o es ese color? O ese es el heat layer. Me parece mucha cosa. Yo creo que nada mas el heat layer.

**05:52-06:03**  
Conflict Events, me imagino, son esos punticos, pero que es este otro punto grande? Ni idea. Ah mira, me dice que no hay cosas en las ultimas 24 horas.

**06:03-06:24**  
Pero desde donde vinimos? Ya no se como volver, porque se perdio. Ah, eso se volvio a agregar otras cosas. No se. Bueno, esta eso. Una de las cosas mientras estamos arreglando el Narrative Threads, eso es en este momento que estamos trabajando en el modelo nuevo.

## Findings

1. The product exposes many panels but does not show an explicit evidence route. Users cannot easily tell why a country, topic, person, source, or signal is connected to the current view.
2. Country/topic/person scoped views are visually mixed with global panels. This makes global background look like scoped evidence.
3. Entity drilldowns can look authoritative even when the extracted person appears ambiguous or weakly supported.
4. The signal stream can move while the user is trying to inspect an item, causing loss of context.
5. Stream timestamps mix ingestion/render recency with publication time. The product needs both times.
6. Topic zero-result states can look like loading skeletons or broken panels.
7. The map legend currently shows too many layer concepts at once. The active layer should be visually prioritized.

## Issues Created

- #173 `feat(ux): Evidence Route panel for visible information pathways`
- #174 `fix(scope): keep active country/topic/person scope coherent across side panels`
- #175 `fix(topic-detail): replace zero-result skeletons with actionable empty states`
- #176 `data(entities): entity drilldown hygiene, confidence, and noisy-person guardrails`
- #177 `feat(stream): analyst-grade relevance scoring and noise filters for Signal Stream`
- #178 `feat(stream): stable item inspection with publication time vs render time`
- #179 `ux(map): simplify legend around active layer and explain marker types`

## Existing Issues That Already Cover Part Of This

- #146 Narrative Threads explanation and empty states.
- #160 Voice Mix endpoint and CountryBrief component.
- #167 Atlas Topic Intelligence.
- #168 Public Attention Threads.
- #169 Search latency and country scoping.
- #140 Visual use-case manual.

## Roadmap Integration

This walkthrough is now folded into:

- `docs/roadmap/2026-05-19-topic-and-signal-class-attack.md` as Track D: Evidence Route UX + Analyst Readability.
- `docs/superpowers/plans/2026-05-19-topic-intelligence-and-source-visibility.md` as Task 12: Evidence Route and Readability Pass.
- `docs/methodology/atlas-data-operating-model-2026-05-19.md` as the fourth operating-model layer: ruta de evidencia.

Execution priority:

1. #174, #175, #178 first because they make current data readable immediately.
2. #173 after `signal_class` and initial source/voice mix are available.
3. #176 before entity/person routes are promoted as strong analytical anchors.
4. #177 and #179 after scope and route clarity are in place.
