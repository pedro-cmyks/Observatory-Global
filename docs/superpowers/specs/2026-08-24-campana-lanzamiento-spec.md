# SPEC — Campaña de lanzamiento: LinkedIn semanal + puerta de registro + Brief legible

**2026-08-24. Pedido de Pedro**: "una noticia por semana en LinkedIn, que se
vea buena, mostrando los paneles de Atlas… que la gente se registre para
empezarlo a usar… y las preguntas quién/dónde/cuándo deberían salir EN el
texto — el orden del brief no está funcionando". Este spec ES el documento
del que cuelgan esos arreglos (Pedro: "partir del spec y organizar así los
arreglos"). Los frentes de motor NO viven aquí — viven en
`2026-08-20-plan-motor.md` y en el prereg `2026-08-20-assignment-lane-…`;
al final hay un tablero que apunta a todo.

---

## 0b · Directiva de lenguaje (Pedro, 2026-08-24, tarde)

**Todo el inglés reader-facing de Atlas — incluido el caption del kit v2 —
sigue ASD-STE100 adaptado**: frases ≤20 palabras, voz activa, una idea por
frase, sin modismos, tabla de términos una-palabra-un-concepto. Guía:
`docs/design/2026-08-24-atlas-ste-style.md`. El generador de captions de la
pieza A produce STE por construcción.

## 1 · La tesis del arco

Atlas ya mide bien y sirve honesto; lo que no existe es el CIRCUITO PÚBLICO:
una pieza semanal que muestre el producto → un link que aterrice en una
puerta legible → una cuenta gratis que retenga al que llegó. Tres piezas, en
este orden, porque cada una alimenta la siguiente.

## 2 · Pieza A — el ritual semanal LinkedIn (v2 CONSTRUIDA — editorial quote-gated + curación)

- **Selector**: `backend/scripts/pick_story_of_week.py` — ranking read-only
  de historias publicables (active · no-junk · court entailed; score
  transparente vol+geo+lang). **Imprime a TERMINAL** (tabla + deep link por
  fila); no genera archivos — lo publicable se genera EN el app.
- **Kit**: botón `⧉ LinkedIn kit` en el detalle de la historia → card
  1200×627 screenshoteable + caption honesto copy-paste SIN link
  (`lib/storyShare.ts`, puro: campo ausente = línea ausente, conteos solo
  con su ventana, state-media marcado) + "first comment" aparte con el
  deep link (`buildStoryFirstComment`).
- **Ritual (5 min/semana)**: correr el selector → abrir el deep link →
  LinkedIn kit → curar recibos (checkbox, cap 3) → generar lede →
  screenshot card + copy caption → publicar el post SIN link en el cuerpo
  (card + caption + screenshots de paneles que apoyen: mapa, historia, voice
  mix) → copiar el "first comment" del kit y pegarlo como PRIMER COMENTARIO
  del post (ahí vive el link). Por qué: el algoritmo de LinkedIn castiga
  posts con link en el cuerpo (consejo de marketing 08-24, aceptado por
  Pedro).
- **Estado v1**: mergeado (`44805443`) + bugs §4 arreglados (`dd706612`) +
  link-en-primer-comentario (`f235850c`). **Veredicto de Pedro en vivo
  (2026-08-24): "cero tratamiento editorial, solo una foto de datos crudos,
  nada dice"** — y los recibos auto-muestreados salían en cualquier idioma y
  con adjuntos falsos (la enfermedad M1: en Ukraine War Updates 2/3 recibos
  off-story; en Colombia Earthquake 1 de Guinea). → v2.
- **Estado v2 (2026-09-11)**: construido y verificado el 08-24 en la rama de
  sesión pero **NUNCA mergeado a v3** — 3 semanas sin publicar, con prod
  sirviendo el v1 que Pedro ya había rechazado. Rebasado sobre v3 (STE +
  primer comentario) el 09-11; ver §2.2 para el calendario de campaña.

### 2.1 · Kit v2 — mini-editorial quote-gated + curación de recibos (2026-08-24)

Tres movimientos, cada uno con su riel de honestidad:

1. **Lede editorial (backend)** — `POST /api/v2/story/{id}/share-editorial`
   (`app/services/story_editorial.py` + handler en `routers/story.py`,
   contract `story-share-editorial-v1`): 2-3 frases en inglés con la voz de
   Atlas (reglas destiladas de `publication_synthesis`), sintetizadas SOLO de
   los recibos curados que viajan en el body. Una llamada por generación vía
   la cadena `insight_llm` (Anthropic→DeepSeek, cost-ledger
   `story-share-editorial`), bucket `paid`, Redis 7d sobre la curación exacta
   (solo se cachea un lede servido — outage/gate-fail quedan retryables).
   Rieles MECÁNICOS (server, no prompt-hope):
   - **Quote gate** (patrón AI-read): cada frase cita un recibo y trae quote
     VERBATIM de ese headline; substring normalizado o se DROPEA. Todo
     dropeado ⇒ `quote_gate_failed` honesto, lede null — nunca prosa suelta.
   - **Guard de números**: todo dígito de la frase debe existir en el
     headline citado.
   - **STATE MEDIA IS NEVER NEUTRAL**: frase apoyada en recibo state-media
     debe nombrar el outlet en la frase o se dropea; el flag state del
     cliente solo puede AGREGAR — el server lo OR-ea con su clasificador
     (`classify_source_tier`), nunca lo limpia.
2. **Curación de recibos (diálogo)**: checklist de hasta 30 recibos SERVIDOS
   (checkbox, cap 3, chips outlet/lang/STATE/archive). Elegir entre recibos
   reales es honesto — inventar o esconder no. Los no-ingleses se traducen a
   inglés vía el lane `/api/v2/translate` existente (batch + caché server) y
   el card/caption marcan "(translated from es)" — nunca se hace pasar la
   traducción por original. Cambiar la curación RESETEA el lede (un lede
   generado sobre otros recibos sería mentira).
3. **Hallazgo MEDIDO (puro, sin LLM)**: `computeShareFinding` en
   `storyShare.ts` — math sobre campos servidos, con base declarada:
   spread de idiomas del sample (≥3), share state-media del sample (≥1),
   split de tono por país (countryBreakdown, piso 3 señales y gap ≥0.5).
   Nada califica ⇒ sin línea (ausencia sobre gancho fabricado).

**Card/caption v2**: label → lede (si existe; el tagline STE "measurement,
not opinion" solo aparece SIN lede — sería falso sobre un editorial) →
`Measured: <hallazgo>` → vitals con ventana → recibos curados traducidos con
outlet+tier ("Receipts — the lede above is synthesized only from these,
quote-checked:"). SIN link: el link vive en el primer comentario
(`buildStoryFirstComment`).

Tests: `backend/tests/test_story_editorial.py` (18 — gate/guards/contract/
handler) + `storyShare.test.ts` (13 — caption v2 + hallazgos + primer
comentario).

### 2.2 · Kit v2.1 + campaña medida (2026-09-11) — el ritual se vuelve calendario

**Diagnóstico del 09-11**: tres semanas sin publicar; el v2 nunca llegó a
prod; **telemetría prod = 0 eventos del 08-26 al 09-10** (endpoint vivo,
202) — dieciséis días sin una visita medida. El circuito público de §1 no
existe hasta que se publique.

**Investigación LinkedIn 2025-2026** (fuentes en el calendario §7) y lo
que cambió en el kit por ella:

1. **Formato**: 1200×627 es el tamaño de link-preview; el feed móvil (91%)
   premia **1080×1350 portrait** (más dwell) y 1080×1080. El kit ofrece
   los tres (toggle), portrait por default, con tipografía escalada por
   formato y **Download card PNG** a píxeles exactos (html-to-image,
   `canvasWidth/Height`) — muere el screenshot manual.
2. **Hook-first**: ~140 chars visibles antes del "see more" en móvil. El
   caption abre con el LEDE (o el hallazgo medido si no hay lede), no con
   el label; el label cierra ("Story on Atlas: …"). Tests congelan el orden.
3. **CTA humano**: LinkedIn 2026 baja la distribución al copy genérico/IA.
   Campo "Your closing question" en el kit — la escribe Pedro, nunca se
   genera; blanco = nada.
4. **Atribución**: lnkd.in + el navegador in-app de iOS borran el
   referrer → el link del primer comentario lleva UTM
   (`buildCampaignDeepLink`: `entry=linkedin&utm_source=linkedin&
   utm_medium=organic&utm_campaign=sow-YYYY-wNN&utm_content=<historia>`,
   tag ISO-week puro `campaignTagForDate`). El app captura **first touch**
   por cliente (`lib/acquisition.ts`, localStorage `atlas.acq.v1`, misma
   vida que el session id) y TODO evento de telemetría lleva `acq` +
   `acq_first`. Verificado E2E contra la DB de prod (app_open → thread_open
   → first_value_moment con `campaign=sow-2026-w37`).
5. **Lectura semanal**: `backend/scripts/campaign_acquisition_report.py`
   (read-only): por tag, sesiones arrived → story → value → signed_up, con
   la baseline sin-tag al lado (nunca se asume LinkedIn sin UTM) y la
   curva por día.
6. **Link en primer comentario: DISPUTADO en 2026** (una fuente: sigue
   funcionando; otra: −80% + castigo al "bridge post"). Sin datos
   controlados → A/B nuestro en los 6 primeros posts (comentario vs solo
   *Featured*), se decide con la bitácora.

**Calendario, arco de 8 posts, bitácora y anti-patrones**:
`docs/campaign/2026-09-linkedin-calendar.md`. Resumen: **martes historia
(kit) + jueves pieza ligera; quincenal NO** (bajo el piso de todos los
datasets); 08:30-09:30 COT; perfil de Pedro publica, la página repostea
+24 h; poll como encuesta ligera en el post 6; primer pedido de registro en
el post 7. Primer post: **Ceuta Migrant Crisis** (dt-18062), martes
2026-09-15, `sow-2026-w38`.

## 3 · Pieza B — la puerta: registro con correo+clave (CONSTRUIDA — `d214e2ba`; E2E real: el correo llegó y el link verificó)

Verificado contra el Supabase vivo (2026-08-24): `POST /auth/v1/signup`
crea usuario + despacha correo de verificación — el server-side YA está.
Accounts-v1 (julio: magic-link + sync RLS local-first) sigue vivo. Se
construye encima, aditivo:

- Lane correo+clave en AuthContext/AccountSection (magic-link se queda).
- `/register` standalone = el destino del link de campaña.
- `/auth/callback` (cuenta verificada ✓) + `/auth/reset` (clave nueva).
- CTA en Landing: gratis, crea tu cuenta → /register.
- Anónimo intacto (W0-D5); nada paywalleado.
- **Queda para Pedro (dashboard Supabase)**: allowlist de redirect URLs
  (dominio Vercel + /auth/callback + /auth/reset) y decidir SMTP propio
  para volumen de campaña (el built-in ≈2-4 correos/hora — alcanza para
  perfiles internos, corto para campaña).
- Google OAuth: descartado por ahora (se intentó, no salió). No se retoma
  en este arco.

## 4 · Pieza C — la puerta debe abrir: bugs que bloquean (ARREGLADOS — `dd706612`)

1. **Consola muerta post-deploy**: "Unable to preload CSS for /assets/App-…"
   + TRY AGAIN muerto. Clase: React.lazy (split `8fd1f578`) + PWA SW viejo
   → chunk hash desactualizado; el retry re-usa la promesa de import rota.
   Fix: retry de clase-chunk = reload con guard anti-loop + revisar update
   del SW. Es EL bug que le rompió a Pedro el ritual de la pieza A.
2. **Diálogo-franja**: un share dialog renderiza como franja (sospecha:
   container-queries del card sin container-type, o el dialog del Brief).
   Reproducir ambos, arreglar, screenshots 1440/375.
3. **Dock montado**: las tabs ANOMALY/SOURCE INTEGRITY/UNDER THE RADAR/
   MARKETS se superponen al contenido vecino en desktop ancho.

## 5 · Pieza D — el Brief legible: preguntas EN el texto + noticia primero (CONSTRUIDA — `ba1b2592`)

Directiva textual de Pedro. Dos movimientos:

1. **Standfirst tejido**: la grilla de 6 tiles WHO/WHAT/WHEN/WHERE/HOW/WHY
   se convierte en un párrafo de PROSA compuesto solo de campos
   answered/Ready (lib pura `briefStandfirst.ts`, testeable; Partial se
   declara en una línea honesta; "(place)"-ruido se limpia solo en render;
   state-media marcado). Los tiles no mueren: `<details>` "See the six
   measured questions".
2. **Reorden noticia-primero**: masthead → standfirst → HISTORIAS → vitals
   → markets → búsqueda país → resto. La instrumentación baja; la primera
   pantalla es periódico, no tablero.

Invariantes: dial P1.5 intacto (READ = cero bloques por tarjeta; el
standfirst es de edición); nada inventado; degradado = standfirst ausente.

## 6 · Decisión abierta — "usemos toda la data" (pregunta de Pedro, HOY)

Pedro: hay datos desde mayo; el console dice FROM 13 AUG; ¿por qué no usar
más? **La respuesta honesta tiene dos mitades**:

- La ventana caliente de 7 días es DELIBERADA y hoy se re-demostró por qué:
  4 noches sin poda → base 13GB → INSERTs 3× más lentos → ingesta al 30%.
  Subir la retención caliente = comprar ese incidente a diario. No.
- PERO las historias ya viven más que 7 días (identidades persisten;
  "Started 85d ago" en el panel), y el ARCHIVO (mayo→hoy, /Volumes/Ext +
  muestras `historical_evidence_samples` + `archive_story_units` + serie
  `/deep-history` de 61 días) existe y está SUB-SERVIDO en las superficies.
  El camino es archivo-al-frente, no hot-más-gordo: (a) deep-history
  prominente en el detalle de historia; (b) replay/timelines alimentados de
  agregados de archivo más allá de 30d; (c) recibos de archivo (day
  evidence) linkeados desde las tarjetas viejas.

**Decisión de Pedro pendiente**: ¿priorizamos un pase "archivo-al-frente"
después de las piezas A-D, o después del M1-sombra? (Mi voto: después del
M1-sombra — es superficie, y el motor está a mitad de gate.)

## 6b · Programa: subir el output de señales PROCESADAS (Pedro, 2026-08-24 tarde)

Origen: al armar el post #1, Pedro preguntó qué significa "0 verified
stories" en un gap. Respuesta honesta: el gap mezcla dos cosas que hoy no
separamos — silencio real de prensa Y nuestro propio recall (93% de las
señales servibles no se adjuntan a ninguna historia; gate 24.9% kept). Por
eso el bullet salió de la nota: no publicamos un número que aún no sabemos
leer. El programa para subir el output procesado ya existe por partes;
aquí queda unificado con su métrica:

1. **M1 familia ① en sombra** (prereg + calibración 08-24): objetivo
   G-RECALL 7%→≥20% servible-con-historia SIN bajar de 90% precisión. La
   palanca más grande.
2. **Gate recall** (programa existente: two-tier/extended, umbrales por
   topic): el 24.9% kept es la banda actual; las clases duras (election)
   tienen su historial medido.
3. **Ingesta cruda** (chip `task_1f96ad0c` corriendo): backfill de buckets
   GDELT saltados — más señales entran, más se procesan.
4. NLP NO es el cuello (100% sentiment / 99.6% NER medido hoy).

**Métrica semanal del programa** (una línea en el weekly read): señales/día
ingestadas · % gate kept · % servible-con-historia. Cuando (1) aterrice,
el gap vuelve a ser publicable — separado en "silencio real" vs "aún no
procesado".

## 7 · Tablero de frentes (2026-08-24, estado al cierre de sesión)

| frente | estado | doc/commit |
|---|---|---|
| M4 cirugía del lock (suelta tras R1) | **HECHO** — estrena esta noche 22:00; vigilar mañana catchup+goldgrowth+embed y clase timeout-serving | `dfa26e73` |
| Catchup backlog 502K (archivo+poda) | agarró lock 07:53, archivando (69K filas del d17 ya en Ext) | auditoría §3 |
| Ingesta GDELT al 30% | causa = INSERTs lentos por base gorda; re-medir 24-48h post-poda | `docs/state/2026-08-24-health-audit.md` |
| M1 familia ① calibrada (3 sondas) | HECHO — sigue: fix en sombra vs 6 barras | `b649d30c` · prereg addendum |
| Kit LinkedIn (pieza A) | **v2.1 mergeado a v3 el 09-11** (editorial quote-gated + curación + formatos + UTM); primer post mar 09-15 (Ceuta) — calendario `docs/campaign/2026-09-linkedin-calendar.md` | `44805443` · `dd706612` · `f235850c` · v2.1 |
| Registro+clave+CTA (pieza B) | HECHO — pendiente dashboard Supabase (Pedro, §3) | `d214e2ba` |
| Bugs consola/diálogo/dock (pieza C) | HECHO — chunk auto-reload + kit portal + dock wrap | `dd706612` |
| Brief tejido + noticia-primero (pieza D) | HECHO — eyeball de Pedro en prod pendiente | `ba1b2592` |
| threevendor leg anthropic | **HECHO** — κ 0→0.611/0.727; mergeado a la rama principal (Step -1 ya no lo revierte) | `ed84c9d4` |
| Archivo-al-frente (más historia en superficies) | decisión de Pedro (§6) | — |
| Feed rot (~25 feeds/día) | abierto, crónico | auditoría §4.4 |
| M5 lectores humanos | la campaña ES el reclutamiento; sigue siendo decisión/ejecución de Pedro | plan motor M5 |

## 8 · Orden

A-C-D son un solo pulso (la campaña no lanza con la puerta rota) → B cierra
cuando Pedro haga los pasos de dashboard → primera publicación LinkedIn →
M1-sombra continúa en paralelo (motor, no bloquea campaña) → §6 se decide
después.
