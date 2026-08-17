# El lector diario — el Brief evoluciona a producción editorial — DISEÑO

**Estado: spec para revisión de Pedro. Nada se construye sin su aprobación.**
Nace de la sesión de diseño 2026-08-17 (compañero visual: cuatro pantallas en
`.superpowers/brainstorm/41044-1786744486/content/`). Decisiones tomadas por
Pedro, una a una, con sus precios dichos antes de elegir.

---

## 1 · Para quién

**Para Pedro.** n=1, declarado. No es una hipótesis de mercado ni una persona
sintética: es el usuario real, sentado, que quiere abrir Atlas cada mañana y
enterarse — de Colombia, del mundo, y de lo que le interesa.

Eso no reduce el alcance del producto. La cuña de Atlas sigue siendo el
analista narrativo. Pero **el lector diario es el único usuario que existe
hoy**, y diseñar para él es diseñar contra alguien real en vez de contra una
abstracción.

## 2 · La tesis de forma

El Brief hoy es un **periódico**: ordena por tamaño y sirve lo más grande del
mundo. El reporte que a Pedro le funcionó — *el terremoto que no era
terremoto* — no era un periódico: era un **argumento**. Tenía una tesis,
señalaba lo que no cuadraba, y la evidencia existía para sostener la tesis.

**El Brief no se reemplaza: evoluciona hasta contener esa producción
editorial.** Sigue siendo la puerta de entrada, sigue llevando a L2 con un
clic, y absorbe el lector diario dentro de sí. No hay superficie nueva.

Cuatro huecos concretos, medidos contra el producto de hoy:

| Hueco | Hoy | Consecuencia |
|---|---|---|
| No hay lector | Edición idéntica para todos | El lead de hoy es «German heat deaths top 12,000» para un lector colombiano |
| No hay continuidad | Cada día empieza de cero | Atlas mide firma temporal, movimiento y persistencia — y no los sirve como lectura |
| No hay veredicto | Lo raro se sirve como *chips* | Lo que hizo bacano el reporte era exactamente eso, contado |
| No hay retorno | Lees, clicas, te vas | Nada de eso vuelve a la edición de mañana |

## 3 · La anatomía del día — **un lead, luego las capas**

*(Elegida sobre «capas fijas» y «el día manda».)*

```
┌─ EL LEAD ─────────────────────────────────────────┐
│ HOY LIDERA · lo raro                              │
│ La historia insignia del terremoto colombiano     │
│ no tiene un solo recibo colombiano.               │
│ ── lidera porque 48/48 recibos son extranjeros:   │
│    el desbalance más alto medido en 14 días.      │
└───────────────────────────────────────────────────┘
  CERCA DE TI · COLOMBIA
  QUÉ CAMBIÓ · desde tu última lectura
  QUÉ ESTÁ RARO
  EL MUNDO
     └ The World · Under the Radar · Culture & Sport
```

Razón de la mezcla: un lector diario necesita **las dos cosas** — una silueta
estable para barrerlo en 90 segundos, y un momento que justifique que hoy no
es ayer.

**Reglas de la anatomía:**

- **El segmento vacío desaparece**, sin dejar hueco ni disculpa. Ya es el
  comportamiento de `composeCountrySections` en la edición país; se reusa.
- **El lead declara por qué lidera.** Es la disciplina de reason-codes del
  motor, aplicada a la portada.
- Las tres secciones actuales (The World / Under the Radar / Culture & Sport)
  pasan a ser **subsecciones de «El mundo»**.

## 4 · La regla del lead — rareza relativa + piso absoluto

*(Elegida sobre «precedencia fija».)*

Cuatro candidatos compiten cada mañana: **lo raro · lo cercano · lo que
cambió · lo grande del mundo**. Sus unidades no se comparan entre sí (48/48
recibos extranjeros vs +38 recibos vs 150 señales).

**La comparación honesta es contra sí mismo:** cada candidato se mide como
percentil dentro de su propia serie de 14 días. Gana el más inusual para sí
mismo. Es el mismo truco que ya usa el eclipse (entropía contra su mediana de
7 días) y la rareza de entidades.

**Piso absoluto**: además del percentil, cada candidato debe superar una
magnitud mínima. Mata el modo de falla obvio — que un p99 de algo diminuto se
robe la portada.

**La salida honesta**: si nadie llega a la barra, **el lead dice que nadie
llegó** («Hoy nada pasó la barra. El día abre en capas.») Sin esta cláusula,
cualquier regla de lead fabrica titulares los martes tranquilos.

**Barras a congelar ANTES de la primera corrida** (números por medir, no por
adivinar): percentil de corte (arranque propuesto: p90), ventana de la serie
(14 días), y el piso absoluto por candidato.

Por qué se descartó la precedencia fija: con una fila `raro → cercano →
cambió → mundo`, «lo raro» lidera tres días seguidos no porque hoy sea más
raro que ayer, sino porque está primero en la lista. **La fila decidiría el
lead más que la medición.**

## 5 · «Qué cambió» — la objeción de Pedro, y la regla que sale de ella

**La objeción, textual:** el terremoto de Colombia se pegó dentro de un tema
viejo de terremotos y nadie lo marcó como nuevo.

Esto es fatal para el segmento si el cambio se mide sobre la identidad: un
evento nuevo y catastrófico se leería como *«+38 recibos en una historia que
ya venías viendo»*. **El día que más importa se leería peor que cualquier
otro.**

**La regla, en una línea:**

> **El día nunca le pregunta a la identidad si algo es nuevo. Se lo pregunta a
> los recibos.**

Tres cambios que el segmento puede reportar:

| Cambio | Cómo se mide | Instrumento |
|---|---|---|
| **Nuevo dentro de lo viejo** | Discontinuidad de composición: país, fecha, actores y distancia de centroide de lo que llegó contra lo que ya estaba | Detector de sobre-fusión existente (multimodalidad de país, 2-means sobre embeddings de miembros) |
| **Creció** | Conteo puro, cuando lo que llegó SÍ se parece a lo que había | `changed_10h` / conteo de miembros |
| **Resucitó · se apagó** | Firma temporal | `temporal_signature`, ya medida y ya servida como chip |

**No hay instrumento nuevo.** Es el detector de sobre-fusión leído desde otro
ángulo. Y convierte la debilidad de la identidad en señal: *«esta historia
vieja está cargando algo nuevo adentro»* es un percentil alto de rareza por
construcción — **puede ganar el lead**.

**Límite honesto, declarado antes:** si el evento nuevo llega con pocos
recibos y se parece a los viejos, no se caza. La prueba necesita un **piso
mínimo de recibos** para no dispararse con dos filas. Otro número que se
congela antes.

## 6 · El perfil — lugar es un hecho, interés es un modelo

La distinción es de Pedro y es la que disuelve la tensión de la burbuja:

- **Lugar** — hecho declarado (Colombia). Estable, legítimo. Un periódico de
  Bogotá que abre con Bogotá no es una burbuja: es un periódico local. Única
  deuda: decir qué edición estás leyendo.

  **«Cerca de ti» = PAÍS, y solo país.** Es el grano que Atlas puede sostener:
  la geografía del sustrato es país-sujeto (`signals_v2.country_code`, FIPS
  normalizado), y el mismo detector que ya usamos para conflictos de geografía
  trabaja a ese nivel. **Ciudad queda fuera del alcance** — servir «cerca de
  Bogotá» sería un claim que la medición no respalda, del mismo tipo que el
  chip VE sobre una historia colombiana. Si algún día hay geografía de sujeto
  a nivel ciudad, se reconsidera con su propia barra.

  **Cómo se fija**: declarado por el lector. Se puede *proponer* un valor
  inicial desde el locale del navegador, pero se muestra siempre y se cambia
  con un clic — nunca se infiere en silencio. Un lugar mal inferido y
  escondido produce exactamente el defecto que el producto existe para
  nombrar.
- **Interés** — un modelo. Puede equivocarse. Necesita reglas que un hecho no
  necesita.

### 6.1 · Tres procedencias, tres comportamientos

| Procedencia | Comportamiento |
|---|---|
| **Declarado** — lo dijiste tú | Vale desde el día uno; **mata el arranque en frío**. Nunca se desvanece; solo lo quitas tú. |
| **Inferido** — de tu lectura | Carga su evidencia («de 40 lecturas en 14 días») y **se desvanece** si dejas de leerlo. |
| **Sugerido** — Atlas propone | No ordena nada hasta que digas que sí. Al aceptar → declarado. Al rechazar → no vuelve a proponerse. |

### 6.2 · Las cuatro reglas que impiden la burbuja

1. **CORTAFUEGOS — la personalización SUMA un segmento; nunca RESTA de la
   edición compartida.** Tus intereses ordenan lo que va *dentro* de «lo
   tuyo». «El mundo» queda intacto y completo, debajo. Es un periódico local:
   portada local, sección internacional entera. *Esta regla es estructural, no
   una promesa: hace la burbuja imposible por construcción.*
2. **ESPEJO** — el modelo se sirve como texto legible con su procedencia, y
   cada ítem se quita con un clic. Un modelo que no se puede leer no se puede
   corregir.
3. **DESVANECIMIENTO** — lo inferido que dejas de leer se apaga solo (~3
   semanas, a calibrar). Sin esto, el modelo se osifica alrededor de la semana
   en que estuviste curioso.
4. **DECLARAR LO OMITIDO** — banda «fuera de tu radar hoy: Tailandia · Congo ·
   Omán», con el puntero a dónde sí están. Es la disciplina de
   `could_not_measure` del protocolo, aplicada al lector.

**Arranque en frío**: los primeros días el segmento personal no aparece, con
su frase honesta («todavía no sé qué te interesa — llevo 3 lecturas»). **Nunca
se inventa un perfil para llenar el hueco.**

**Sustrato**: la telemetría necesaria ya existe y ya escribe —
`brief_thread_open`, `brief_section_click`, `country_click`, `thread_open`,
`search_query`, `pin`. Accounts-v1 (Supabase + RLS + sync LWW) ya sincroniza
estado por usuario entre dispositivos. **No hay tabla nueva de perfil en el
alcance de la primera tajada**: el modelo se deriva de lo que ya se observa.

### 6.3 · Recomendaciones con recibo

**Atlas NO puede decir «a gente como tú también le interesa».** Hay un solo
usuario y no hay cohorte: sería inventar una medición que no existe.

Lo que sí puede, y es mejor:

> *«¿Minería y tierras? Porque es hermano medido de 3 historias que abriste
> esta semana — walk 0.71, 0.68, 0.66.»*

Es el caminante de hermanos ya construido (`/api/v2/story/{id}/siblings`), con
su peso de coseno como recibo. **Una recomendación con recibo** — lo que
ningún feed puede dar, porque ninguno mide.

### 6.4 · Culture & Sport

Se queda **genérico** (farándula, lo más hablado) — a menos que el modelo
detecte gusto específico por un tema que caiga ahí, en cuyo caso ese tema sube
al segmento personal por la vía normal. Sin trato especial.

## 7 · El día y sus bordes

**El día empieza en la noche y se lee en la mañana, como un periódico.** El
sello nocturno (02:30) define la edición. No se busca estar siempre
actualizado — se busca ser un periódico.

**Edición corregida.** Una noticia grande durante el día puede corregir la
edición ya sellada. Con una regla que un periódico ya conoce:

> **Nunca una reescritura silenciosa.** El sello carga su hora y la corrección
> carga la suya: *«sellado 02:30 · corregido 14:20»*, con lo que cambió
> nombrado.

Qué califica como «grande» reusa la barra del §4: **solo un candidato que
habría ganado el lead puede corregir la edición.** Una sola barra, dos usos.

**«Desde tu última lectura»** se calcula en el cliente contra la marca en
localStorage, sobre historia que el sello ya carga (§8). Primera visita o
dispositivo nuevo → cae honestamente a «desde la edición de ayer».

## 8 · Arquitectura del delta — vista sobre historia compartida

*(Elegida sobre «desde la edición de ayer» y «estado por usuario en el
servidor».)*

El sello carga, por historia, su estado en varios cortes pasados. El delta se
calcula **en el cliente** contra tu marca de última lectura.

Por qué: convierte el delta en una **vista sobre historia medida compartida**,
no en un cómputo personal en el servidor. El sello sigue siendo uno solo para
todos — sellado y cacheable, que es justo lo que la puerta necesita — y el
claim personal sigue siendo cierto.

**Precio declarado**: el payload engorda con cada corte que carga. **Medir
antes de fijar cuántos cortes.** Si son demasiados, la puerta se vuelve más
lenta y habríamos cambiado un problema por otro.

## 9 · Rendimiento — barra de aceptación, no mejora deseable

`/api/v2/briefing` mide hoy **21.7 s** (medido 2026-08-17, prod, caliente).

**Un lector diario que tarda 21 segundos no es un lector diario: es una
tarea.** Esto entra como barra: si la puerta no abre rápido, lo demás da
igual.

**Método (la disciplina de siempre): medir antes de optimizar.** No se elige
solución antes del perfil. Las familias candidatas, sin comprometerse a
ninguna:

- **Precalcular y servir artefacto** — el patrón que ya salvó `/universe`
  (75-84 s de build → lectura pura ~2.8 s, mig 091). El lector diario es un
  sello: por construcción es precalculable.
- **Separar cómputo de servicio** — el cómputo pesado en la M1 nocturna, el
  servicio como lectura de una fila.
- **Revisar el plan real** — índices y relaciones de tablas, con EXPLAIN sobre
  la consulta de producción, no sobre la que uno cree que corre. (Ya nos
  ahorró tirar un índice de 420 MB que el planeador sí usaba.)

Primer paso, sin decidir nada: **perfilar dónde se van los 21.7 s.**

## 10 · Qué NO está en alcance

- **Arreglar la identidad.** Z1 (predicado de etiquetas) y Z5 (geografía del
  sujeto) corren en su propio reloj. El §5 está diseñado para **funcionar sin
  esperarlos**.
- **Notificaciones push.** Un lector diario necesita un motivo para volver a
  una hora; no está en esta tajada.
- **Perfiles multiusuario.** n=1. Cuando haya más de un lector, la §6 se
  revisa.
- **Feed en vivo.** Decisión explícita de Pedro: periódico, no ticker.

## 11 · Riesgos honestos

**El riesgo mayor: la forma está lista antes que el sustrato.** Hoy Colombia
tiene una sola historia en el top-10 y sus recibos son alemanes y venezolanos
(dt-12927: DE 24 · VE 24 · **CO 0**). El protocolo midió que **77 de 84
señales políticas de una ventana de 24 h no se vuelven historia** — eso es un
hueco de recall de Atlas, no una ausencia del mundo: hay historia por todos
lados. Consecuencia práctica: **«cerca de ti» va a estar ralo muchos días.**

El diseño aguanta eso por construcción (el segmento vacío desaparece), pero
hay que decirlo antes de construir: **el lector diario no va a sentirse lleno
hasta que la identidad y el recall mejoren.** La forma no arregla el motor.

Riesgos menores: percentiles sobre métricas ruidosas suben a p99 con facilidad
(por eso el piso absoluto); el desvanecimiento mal calibrado borra intereses
reales (por eso lo declarado nunca se desvanece); el payload del §8 puede
engordar la puerta (por eso se mide antes de fijar).

## 12 · Gate pre-registrado

Barras congeladas **aquí**, antes de construir. La disciplina que ya honró
diez veredictos, incluidos los que mataron trabajo hecho.

- **G-VELOCIDAD** — la puerta responde **< 3 s** en frío contra prod. Es la
  barra dura: sin esto no se despliega, por bueno que sea el resto.
- **G-NO-FABRICA** — sobre 14 días de historia real, la regla del lead produce
  **al menos un día «hoy nada»**. Si nunca se abstiene, la barra está mal
  puesta y la portada está inventando.
- **G-COMPOSICIÓN** — el caso testigo congelado: el terremoto de Colombia
  absorbido por «Earthquake Reports» **se reporta como «algo nuevo entró en
  una historia vieja»**, no como «+38 recibos». Si el testigo no pasa, el §5
  no funciona y el segmento se queda en conteo honesto.
- **G-NO-BURBUJA** — auditoría mecánica: **ninguna historia presente en la
  edición compartida puede faltar** en la página servida a un usuario con
  perfil. El cortafuegos se verifica, no se promete.
- **G-ESPEJO** — todo interés servido carga procedencia y evidencia; quitar un
  chip cambia la edición siguiente de forma observable.

**Un KILL con evidencia limpia vale más que un pase de cortesía.**

## 13 · Orden propuesto

1. **Perfilar los 21.7 s** (medición, sin decidir solución).
2. **La anatomía y los segmentos** sobre datos de hoy — sin perfil, sin lead:
   solo las capas y el vacío honesto. Es la mitad que no depende de nada nuevo.
3. **§5 el cambio por composición** + su testigo congelado.
4. **§4 la regla del lead**, con sus tres números congelados antes de correr.
5. **§6 el perfil**, empezando por lo declarado (mata el arranque en frío) y
   el cortafuegos; lo inferido y lo sugerido después.
6. **§7 la edición corregida.**

Cada tajada con su verificación, como siempre.
