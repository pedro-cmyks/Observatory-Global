# El dial de profundidad — una sola puerta que evoluciona — DISEÑO

**Estado: aprobado en sesión por Pedro (2026-08-18) como visión + escalera;
las decisiones de layout marcadas ABIERTAS se resuelven en el banco de
pruebas (§8), no por opinión. Origen: el concepto Option Modes de OrcaSlicer
(Simple/Advanced/Expert/Developer), traído por Pedro.**

Pantallas de la sesión: `.superpowers/brainstorm/53533-1787083924/content/`.

---

## 1 · La visión

**Una sola puerta.** /brief y /app dejan de ser dos productos: hay UNA
entrada y un **dial de tres posiciones** — **LEER · OBSERVAR · CONSTRUIR** —
que reconfigura la pantalla alrededor de una columna vertebral fija. El
lector no "va al console": profundiza donde está.

La evidencia de que las posiciones son reales: los tres revisores ciegos del
2026-08-18 SON las posiciones. Julián pidió LEER («cero letrero técnico»),
Marcus ES OBSERVAR-profundo (persiguió cada número hasta su recibo), Pedro es
CONSTRUIR/Developer. El juez run-3 llamó «machine debris» exactamente a lo
que la posición honda llama instrumento.

## 2 · La columna vertebral: el mundo (diseño de Pedro)

**UN solo mundo — el de L2, reutilizado, jamás un segundo mundo** — que no se
desmonta al deslizar:

- **LEER**: el mundo «poco pintado» (densidad, sin instrumentos), y debajo el
  Brief tal como es hoy.
- **OBSERVAR**: el MISMO mundo gana sus capas (globo↔universo, heat, flow,
  aviones, barcos, puntos, map key); a los lados se materializa el stream;
  abajo los hilos narrativos; la prosa evoluciona a stream.
- **CONSTRUIR**: el MISMO mundo se vuelve pinneable ◆; aparece TU HISTORIA
  (pins, ruta, constelación, dossier — el workbench materializado).

### Los cinco invariantes (lo que NO cambia al deslizar)

1. **El mundo nunca se desmonta ni se duplica.**
2. **El viaje se mantiene** — volar a un país funciona en toda posición; lo
   que cambia es qué te espera al aterrizar.
3. **La honestidad no tiene posiciones** — chips y advertencias se TRADUCEN
   de registro («⚠ mezcla varios eventos» ↔ `subject_geography_grab_bag`),
   jamás se quitan. Regla dura: ninguna posición sirve una historia marcada
   sin su marca.
4. **El foco sobrevive al deslizar** — mirando a Colombia, subes el dial y
   sigues en Colombia con más instrumentos.
5. **La voz editorial (spec daily-reader §2.1) rige en toda posición** — el
   dial cambia vocabulario, nunca añade opinión.
6. **El tiempo es una variable del dial (Pedro, 2026-08-18)** — el contrato
   temporal ya construido (arco time-as-dimension S1–S4) mapea uno a uno:
   **LEER = el día** (24h fijo, el sello — el periódico de la mañana) ·
   **OBSERVAR = el tiempo como dimensión** — se desbloquea el scrubber del
   mundo que ya existe (map/replay 30d, replay del globo, view-span del
   selector) · **CONSTRUIR = el tiempo congelado** (pins con snapshot,
   dossier inmutable). El dial no inventa tiempo: hereda el contrato
   L1=día / L2=dimensión / L3=congelado y lo vuelve posiciones.

## 3 · Integración con el daily reader recién construido

**LEER = el Brief nuevo, intacto.** La anatomía (Cerca de ti · Qué cambió ·
Qué está raro · El mundo), el lugar declarado, el idioma elegido, el método
plegado, las marcas medidas — todo eso ES la posición LEER. El dial no
deshace nada del arco 2026-08-17/18: lo adopta como su primera posición.

**ABIERTA-1 — RESUELTA por el banco R2 (2026-08-18, unánime, orden
cruzado)**: en LEER el mundo vive ABAJO (colofón consultable — «un mapa
decorativo arriba es un peaje que cobra todos los días»); **al deslizar a
OBSERVAR el mundo ASCIENDE al centro** y gana sus capas. El dial no solo
viste la habitación: promueve el mundo. La respuesta de «¿dónde se concentra
hoy?» puede vivir arriba como UNA FRASE del masthead (la leyenda demostró
cargar el dato mejor que el gráfico — R1 y R2). Reglas anexas del veredicto:
jamás doble codificación sin definir ambas; un claim del mapa no puede
contradecir el ranking; el gráfico se gana el centro con interactividad
real, que es la de OBSERVAR. Artefacto:
`docs/research/ux-council/2026-08-18-banco-r2-mundo-en-leer.md`.

## 4 · El periódico como modelo de navegación (idea de Pedro)

La puerta es un PERIÓDICO: **portada** (la anatomía) · **secciones** (Under
the Radar, Culture Sport & Life…) · y **la página de la historia**:

**«Open story» llega a una PÁGINA del periódico, no a un overlay.** La
historia específica es una página con su propia URL.

Propuestas mías sobre esa idea (a validar en banco):

- **URL por historia** (`/brief/story/dt-XXXX` o equivalente): compartible,
  y mata de paso la clase «botón muerto» de los tres testigos — la página
  abre AL INSTANTE con lo que la portada ya sabe (label + recibos del
  payload) y los instrumentos pesados llegan async con estados de carga
  honestos. La percepción de puerta muerta era el console frío + un 503
  adentro; una página que pinta algo en <100ms la elimina.
- **La profundidad viaja a la página**: la MISMA página de historia se viste
  por posición — LEER: recibos + quién la cuenta; OBSERVAR: + activity
  timeline, voice mix, narrative biography (16 semanas), deep history, how
  it's covered, key subjects, países relacionados; CONSTRUIR: + pin, hermanos
  con pesos, unir historias. **Nada del detalle actual se pierde: cambia de
  traje.** Lo lento (biografía) se carga solo cuando su posición lo pide.

## 5 · El inventario clasificado (por qué no se pierde nada)

| Familia | Piezas | Dónde viven bajo el dial |
|---|---|---|
| **De la página** | stream, hilos, mapa/universo, anomaly alert, source integrity, markets, under the radar | Posiciones del dial: se materializan alrededor del mundo en OBSERVAR |
| **De la historia** | how it's covered, top sources, key subjects, países relacionados, voice mix, activity timeline, narrative biography, deep history | La PÁGINA de historia (§4), vestida por posición |
| **De construir** | pins ◆, ruta, constelación, dossier, corroborar, unir historias | CONSTRUIR, en página e historia |

## 6 · La escalera de tres peldaños (¿rebuild o qué? → ni lo uno ni lo otro)

**P1 — el dial como conmutador (un vagón).** El shell keep-alive YA monta
Brief y App a la vez con foco acarreado por URL. Los botones «OPEN CONSOLE» /
«← INICIO» son hoy un dial vergonzante de dos posiciones. P1 los reemplaza
por el dial real: LEER=Brief · OBSERVAR=console con el foco intacto ·
CONSTRUIR=console+workbench abierto. Una puerta PERCIBIDA desde el día uno,
cero cirugía.

**P2 — OBSERVAR se vuelve mundo-céntrico.** Preset «world-first» del grid del
console (RGL ya persiste presets por bucket): mundo al centro, stream al
lado, hilos abajo. Aquí entra la **medición de capas** (`layer_toggle` ya se
telemetra): qué capas prende cada posición por defecto se decide con datos —
la pregunta del flow de Pedro, respondida midiendo.

**P3 — fusión de identidad + bundle por profundidad.** Cada posición carga su
chunk; LEER jamás paga el código del console. El chip del bundle 1.9MB (en
vuelo, task_f369a2cb) es el prerequisito exacto. La página de historia (§4)
aterriza aquí, tras su ronda de banco.

**Móvil**: las tabs Diario/Lente/En vivo ya son un proto-dial — el dial las
absorbe (no un slider flotante encima de tabs).

## 7 · Persistencia y arranque

La posición del dial persiste como el idioma (localStorage, patrón
`pageLanguage`; sync accounts-v1 cuando hay sesión). Primera visita: LEER.
Deep links llevan posición cuando la nombran (`?depth=observar`); un link sin
posición respeta la del lector.

## 8 · EL BANCO DE PRUEBAS (idea de Pedro, pre-registrada aquí)

**Ninguna decisión de layout mayor se toma por opinión: se compara en
mockups y la juzgan revisores ciegos con TAREAS.**

Protocolo congelado:

- **Mockups estáticos con datos dummy** (estructura real, historias
  inventadas — no hace falta el dato real para probar la forma), 2-3
  variantes por pregunta, servidos localmente.
- **Revisores ciegos SIN contexto del producto**, cada uno con TAREAS
  medibles, no impresiones: «¿cuántos muertos reporta la historia X?» ·
  «¿quién la está contando?» · «¿esta historia es confiable? ¿por qué?» ·
  «vuelve a la portada» · «encuentra qué cambió desde ayer».
- **Métrica**: éxito de tarea (sí/no), pasos hasta el dato, confusiones
  reportadas verbatim. La variante gana por tareas, no por gusto.
- **Regla de honestidad del banco**: los mockups llevan las marcas (chips de
  advertencia) — una variante que gana escondiendo la duda está descalificada.

**Ronda 1 (primera, ya definida): la página de historia.**
V-A «página de periódico» (narrativa primero: titular → quién la cuenta →
recibos → instrumentos abajo) vs V-B «página de instrumentos» (paneles
primero: métricas/timeline arriba, recibos abajo). Tareas: hallar la cifra
clave, nombrar las fuentes, juzgar confiabilidad, volver.

**Ronda 2: dónde vive el mundo en LEER** (ABIERTA-1): mapa arriba «poco
pintado» vs mapa abajo como hoy.

**Ronda 3: el dial mismo**: slider continuo vs 3 paradas nombradas vs las
palabras (LEER/OBSERVAR/CONSTRUIR) sin metáfora de slider.

## 9 · Gates del build (por peldaño; barras congeladas antes de cada uno)

- **P1**: G-FOCO (foco/país sobrevive el dial 10/10 travesías) ·
  G-NAV-LOSS re-run (la batería existente) · G-VELOCIDAD intacta (<1s la
  puerta) · G-HONESTIDAD (toda marca visible en toda posición — auditoría
  mecánica tipo G-NO-BURBUJA).
- **P2**: su preset no pierde NINGÚN panel del console actual (inventario
  mecánico antes/después) + banco ronda de layout.
- **P3**: bundle por posición medido (LEER no carga chunks del console) +
  G-VELOCIDAD de la página de historia (<100ms primer pintado con datos de
  portada).

## 10 · Fuera de alcance (por ahora)

- Un cuarto nivel «Developer» expuesto a usuarios (los campos crudos ya
  existen vía profile=1 y el console; se reconsidera cuando el dial viva).
- Reescribir el motor de layouts del console (RGL se queda).
- Tocar el sello/backend: el dial es enteramente de presentación.

## 11 · Orden

1. Banco ronda 1 (página de historia) — mockups + ciegos, HOY.
2. Spec-review de Pedro → plan del P1.
3. P1 (vagón) → gates → medir uso real del dial (telemetría por posición).
4. Banco rondas 2-3 → P2 → P3.
