# La puerta y las carpetas — Brief como diario de la cobertura + modelo carpeta + rename — DRAFT

**Status: DRAFT aprobado en dirección por Pedro (opción B con selección de A y
deep-links de C). Pendiente su lectura de ESTE texto antes del plan.
Supersede y absorbe `2026-08-12-brief-voice-bar-design.md` (la barra de voces
vive aquí como tela de la Parte 3, no como chip suelto).**

## El problema (ciego, verbatim)
"No volvería a leer noticias aquí. El Brief es una versión más lagging y noisy
de cualquier portada de wire; su lead era un recall de jalapeños." Y L2 es
demasiado grande como puerta de entrada.

## La tesis
El Brief no compite como periódico del MUNDO (contra los wires pierde por
construcción — llegamos después). Compite como **el diario de la COBERTURA:
las noticias sobre las noticias, escritas para leerse.** El momento estrella
del mismo reviewer fue un hallazgo de cobertura (East Timor: 12σ, 100%
extranjera, 0 hilos propios). Nadie más puede escribir ese diario, porque
nadie más lo mide.

---

## Parte 1 — Rename: Narrative Threads → **Stories / Historias**

Cambio de COPY global, contratos intactos (thread_id, endpoints, tablas no se
tocan). Superficies: panel L2 (header "STORIES"), Brief, FocusIndicator (ya
distingue Story/Theme — se completa), tooltips, docs de usuario, móvil. Con el
selector de idioma existente: "Historias" cuando la página está en español.
Regla: "story/historia" = hilo dinámico servido; "theme/tema" = categoría
(lente R3). La distinción vocabulario-usuario que R4 encontró confusa queda
resuelta por nombre, no por tooltip.

## Parte 2 — Modelo carpeta (la estructura que Pedro describió)

"Me voy metiendo como a subcarpetas: la historia tiene las subhistorias, las
señales, el mapa, el alert; si entro a un país, todo se reacomoda."

**Lo que ya existe y esto formaliza** (no se reconstruye): #234 propagación de
focus (país/persona/historia re-scopean todo), story lens (sub-historias),
Lens móvil ("una anatomía a N scopes: identidad · qué dice · dónde vive ·
conectado · atención"). Lo que FALTA es que la contención sea LEGIBLE:

1. **Breadcrumb de ámbito persistente**: `Mundo ▸ Colombia ▸ Historia X ▸
   señal` — siempre visible (desktop: junto al command bar; móvil: el header
   del Lens). Cada migaja clickeable = subir de carpeta. Entrar a cualquier
   cosa = entrar a su carpeta; los paneles son el CONTENIDO de la carpeta
   actual. Un solo estado de ámbito — el que ya existe en FocusContext — con
   representación visible.
2. **La misma anatomía en cada nivel** (la generalización del Lens móvil a
   desktop): toda carpeta responde las mismas preguntas en el mismo orden —
   qué es, qué dice, dónde vive, qué conecta, quién presta atención. El
   lector aprende UNA gramática y navega todo.
3. **Salida legible**: el breadcrumb ES el "focus-clear" — se acaba el chip
   escondido de 18px (cierra ese residual R4 por diseño).

## Parte 3 — El Brief: diario de la cobertura

### 3a · Selección editorial (la A adentro)
El lead de la EDICIÓN deja de ser max-volumen. Score de edición:
`dominancia_del_día × diversidad_de_fuentes × movimiento`, con dos vetos:
- **Veto jalapeño** (test-frozen con el testigo real): una historia cuya
  cobertura es ≥X% una sola familia sindicada nunca lidera (X medido del
  histograma antes de fijar — pre-registro).
- Junk/service-damp ya existente, más duro en el slot del lead.
Eclipse/anomalía informan: un día con eclipse parcial lidera con el eclipse;
un país en anomalía fuerte con hallazgo de voz entra al fold alto.

### 3b · La estructura de lectura (la B)
1. **EL LEAD** — la historia dominante del día, con standfirst de PROSA que
   teje la medición: qué pasó (recibos), **quién lo cuenta y quién no** (la
   barra de voces como texto: "48 outlets en 9 idiomas; la propia prensa
   siria: 2"), qué está en disputa (tensión del cross-read si existe).
2. **EL VACÍO** — el mejor blindspot del día COMO HISTORIA escrita: el país o
   historia con máxima divergencia atención/voz-propia (East-Timor-class) o
   el top de under-the-radar. Template sobre campos medidos — "X explotó a
   Nσ con M señales; su propia prensa escribió 0" — con recibos y puerta a la
   carpeta. Vacío honesto si el día no lo tiene ("hoy no hay vacío que
   supere la barra" ES el estado).
3. **LO QUE SUBE** — aceleración medida (Kalman ya servido), 2-3 items, cada
   uno con su why-now medido.
4. **EL DESK** — las secciones actuales (World / Under the Radar / Culture),
   intactas.
Presupuesto LLM: CERO llamadas nuevas — prosa = templates sobre campos
medidos (la disciplina why_now/narrative_note); la cadena insight existente
puede enriquecer el lead como ya hace, opcional.

### 3c · Deep-links carpeta (la C como tejido)
Cada item abre SU CARPETA (Parte 2) con el breadcrumb ya puesto: el lead abre
la historia, EL VACÍO abre el país, LO QUE SUBE abre la historia con la vista
de movimiento. El Brief se vuelve el tour guiado de L2 — la consola se
alcanza por curiosidad, no se cae encima del lector.

---

## Orden de construcción
Parte 1 (rename, barato, un día) → Parte 2 (breadcrumb + anatomía, formaliza
lo construido) → Parte 3 (la lectura, sobre 1+2). Cada parte con su plan y su
gate.

## Aceptación pre-registrada (congelar al aprobar)
- **G-JALAPEÑO**: el testigo real (recall USDA sindicado) re-corrido nunca
  lidera; una historia multi-fuente real sí.
- **G-LECTURA (el gate que importa)**: sonda ciega NUEVA sobre /brief —
  debe (a) describir el Brief como algo DISTINTO de una portada de wire sin
  que se le pregunte, y (b) nombrar al menos un item por el que volvería.
- **G-CARPETA**: NAV-LOSS sobre los deep-links (entrar y salir por el
  breadcrumb sin perder dónde estabas, 6/6).
- **G-VACÍO-HONESTO**: en un día sin blindspot sobre la barra, la sección
  dice eso — jamás inventa uno (falso positivo a mano < 1/10).
- **G-SELLO**: el sello nocturno sigue autónomo — la edición nueva se
  construye en el mismo paso, cero dependencias nuevas de red/LLM.
