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

## 2 · Pieza A — el ritual semanal LinkedIn (CONSTRUIDA, en verificación)

- **Selector**: `backend/scripts/pick_story_of_week.py` — ranking read-only
  de historias publicables (active · no-junk · court entailed; score
  transparente vol+geo+lang). **Imprime a TERMINAL** (tabla + deep link por
  fila); no genera archivos — lo publicable se genera EN el app.
- **Kit**: botón `⧉ LinkedIn kit` en el detalle de la historia → card
  1200×627 screenshoteable + caption honesto copy-paste
  (`lib/storyShare.ts`, puro: campo ausente = línea ausente, conteos solo
  con su ventana, state-media marcado).
- **Ritual (5 min/semana)**: correr el selector → abrir el deep link →
  LinkedIn kit → screenshot card + copy caption → pegar en LinkedIn +
  screenshots de paneles que apoyen (mapa, historia, voice mix).
- **Estado**: mergeado (`44805443`); Pedro lo intentó y no le funcionó — la
  consola estaba rota por el bug de chunks post-deploy (§4.1), no el kit;
  el diálogo-franja (§4.2) es del mismo pase de verificación. Hasta que
  ambos cierren, la pieza A no está "entregada".

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
| Kit LinkedIn (pieza A) | construido; bugs §4 arreglados — verificar ritual en prod post-deploy | `44805443` + `dd706612` |
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
