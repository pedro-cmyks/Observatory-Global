# Panel ciego sobre el daily reader — 2026-08-18

**Tres revisores sin contexto sobre `observatory-global.vercel.app/brief`
(prod, commit `59b9bfac` — la anatomía del día recién desplegada).** Personas:
Camila (34, Bogotá, móvil, 10 min de café, prefiere español) · Marcus (45,
ex-editor de agencia, OSINT, desktop, escéptico profesional) · Julián (26,
vendedor en Medellín, móvil, 3 minutos, cero paciencia). Cada uno en su
pestaña; corrieron CONCURRENTES sobre un pane compartido — los timeouts de
input están parcialmente contaminados por robos de foco entre sesiones (los
dos móviles lo advirtieron ellos mismos), los hallazgos de contenido no.

## Veredictos

| Revisor | ¿Vuelve? | La frase |
|---|---|---|
| Camila | **No** — mañana abre El Tiempo | «Un periódico que se contradice a sí mismo en la portada no me sirve para mis 10 minutos de café» |
| Marcus | Como tip-sheet sí; como fuente de registro no | «Bones good, flesh unreliable» |
| Julián | **3/10** — «lo dejo en visto» | «Parecía el panel de un ingeniero, no noticias» |

## Lo que SOBREVIVIÓ (convergencia de los tres)

1. **La cadena de recibos.** Marcus la auditó de punta a punta: siguió un URL
   (orf.at), el artículo existe, el extracto es fiel. Camila reconoció SUS
   medios (El Tiempo, minuto30, La Opinión). Julián: el chip LOCAL en
   larepublica.ec — «se siente que no es chisme».
2. **El lugar declarado — lo de HOY funcionó.** Camila: selector «guessed
   from your device» → lo cambió a Colombia «sin problema» → NEAR YOU ·
   COLOMBIA de primera con noticias reales. El primer tap de Julián fue el
   selector. La anatomía hizo su trabajo el primer día.
3. **La honestidad estructural, ante un profesional.** Marcus: «nunca he
   visto un producto de monitoreo que publique warnings `grab_bag` sobre sus
   propias historias»; el recibo de RT llevaba el disclosure de RT verbatim
   «en vez de lavarlo». Voice-mix = «algo que mi stack actual no hace».
4. **Cero opinión detectada.** Marcus buscó editorialización expresamente:
   solo señaló «SERIOUS GEOPOLITICS» como juicio estructural y la elección
   de label del lead — que es exactamente el defecto de identidad, no de voz.

## Lo que MATÓ la confianza (los tres, sin coordinarse)

### 1 · Identidad en la portada — el asesino número uno

- **Camila, sobre SU terremoto**: cuatro cifras de muertos en cuatro tarjetas
  — «¿79, 287, 294 o 304?» — y la de 287/294 dentro de una tarjeta titulada
  **«Ceuta Migrant Crisis»**. «Es como si al periódico se le hubieran
  mezclado las páginas.»
- **Marcus**: el lead «Russian Attacks on Kyiv» con recibos de Ucrania
  atacando Rusia — **y el console tiene la etiqueta honesta** («Trade Major
  Drone Strikes»): la etiqueta correcta existe en el edificio, la portada no
  la usó. El top riser = quimera de tres cabezas (label de aviones, recibos
  de un festival de Sri Lanka, título console de una boda india). La historia
  más grande de la página (Wildfires, 17,813 señales) carga cuerpos del
  terremoto — **y el payload la marca `subject_geography_grab_bag`, pero la
  portada la imprime sin la marca**. Seis hilos para un Ébola (uno
  categorizado *Sports*).
- **Julián**: «Mexico Sends Aid to Venezuela» con recibos de plata gringa
  para Colombia — «no cuadra el título con lo que hay adentro».

**Lectura**: es Z1 (la palanca ya nombrada) visto por extraños. Pero hay una
mitigación de superficie BARATA que el panel dejó servida: el backend YA
marca el grab-bag y el court YA veta etiquetas — **las marcas no llegan a las
tarjetas del L1**. Servir la marca no arregla la identidad, pero convierte
una mentira silenciosa en una duda declarada — nuestra regla de siempre.

### 2 · El idioma es un callejón sin salida (Camila)

Quería español. El chip «EN» no respondió al toque en móvil. «TRANSLATE ALL»
tradujo titulares **al inglés** (apunta a `navigator.language`, no al idioma
ELEGIDO en el picker). Quedó un revuelto trilingüe. El picker existe desde el
viernes — pero la lane de traducción no lo obedece.

### 3 · La franja técnica abre la página (Julián + Camila)

«sealed 2 hours ago · full text 7/48 · who_below_full_bar · frozen receipts»
= ~1.5 pantallas de móvil ANTES del primer titular. Julián casi cierra ahí.
Camila: «yo solo quería las noticias». La honestidad de método es
irrenunciable — su POSICIÓN y su idioma no. En móvil el método debe ir
después de las noticias, o plegado.

### 4 · Móvil enfermo (los tres, con el caveat del pane compartido)

Reproducible en código: **el select de país retiene el foco** (PageDown →
cambió a Cook Islands); **overflow horizontal tras scroll** (texto cortado:
«olombia»); un frame duplicado en dos columnas. No reproducible localmente:
los «Open story» muertos — verificado por el controlador en preview que
AMBOS caminos navegan (`/app?theme=dynamic-topic-258&country=CO&entry=brief`);
19 instancias del botón viven en panels de tab inactivos (offsetParent null)
y un click de driver sobre una oculta no hace nada. PERO dos móviles
independientes reportaron taps sordos — la página bloquea input durante la
hidratación. Queda como hallazgo de perf, no de handler.

### 5 · Defectos puntuales con nombre

- **«228 COUNTRIES»**: hay ~195. El dropdown mezcla FIPS e ISO y cuenta la
  unión — Honduras dos veces (HN+HO), dos Indonesias (ID+RI), dos Irlandas,
  dos Yemens. La estadística de portada está inflada por higiene de códigos.
- **Extracto de eltiempo.com = el banner de cookies** del portal, no el
  artículo (clase de extracción trafilatura).
- **«2,325 muertos de Ébola»** — el claim factual más grande de la página —
  apoyado en zerkalo.az + kibrispostasi.com, 0% prensa congolesa (el propio
  voice-mix lo admite), y un recibo dice «terminó» mientras el console dice
  «Accelerating».
- Franken-panel en search→historia (título de la boda + voice-mix del Ébola
  entrelazados) — fuga de estado entre paneles.

## Tren propuesto (para el ojo de Pedro — nada se construye sin su palabra)

| # | Vagón | Costo | Qué compra |
|---|---|---|---|
| 1 | **Marcas de court/grab-bag en las tarjetas L1** — el dato ya viaja en el payload | S | La mentira silenciosa se vuelve duda declarada; el defecto que los TRES nombraron |
| 2 | **Translate-all obedece el idioma ELEGIDO** + chip EN responsivo en móvil | S | El callejón de Camila; el mercado hispano |
| 3 | **La franja de método baja/se pliega en móvil** — titulares primero | S | Los 10 segundos de Julián |
| 4 | **FIPS∪ISO dedup** en dropdown + stat de países | S | «228» deja de ser mentira contable |
| 5 | **Blur del select tras elegir** + cazar el overflow horizontal móvil | S | Los dos bugs móviles reproducibles |
| 6 | Extracto-cookies (filtro de boilerplate en trafilatura) | M | Recibos que no avergüencen |
| Z1 | La identidad — sigue siendo LA palanca; el court refinanciado hoy ya juzga de nuevo | (en curso) | Todo lo demás |

**Método**: el panel corrió sobre pane compartido concurrente — la próxima
vez, secuencial o panes separados; los hallazgos de input llevan esa sal.
