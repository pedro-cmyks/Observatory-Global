# Campaña LinkedIn — calendario vivo (arranque 2026-09-15)

**Documento de trabajo de Pedro.** Cada semana: correr el ritual, publicar,
anotar la fila del post en §5. Cuelga del spec de campaña
(`docs/superpowers/specs/2026-08-24-campana-lanzamiento-spec.md` §2.2). La
investigación que lo sustenta está en §7 (fuentes 2025-2026; todo lo que no
tenga fuente es decisión nuestra y se dice).

## 0 · Dónde estamos (2026-09-11, medido)

- Kit v1 en prod desde 08-24; Pedro lo juzgó en vivo: "cero tratamiento
  editorial". El v2 (editorial quote-gated + curación) se construyó ese día
  pero **nunca se mergeó** — 3 semanas con prod sirviendo lo rechazado.
- **Telemetría prod: 0 eventos entre 08-26 y 09-10.** Dieciséis días sin
  una visita medida (el endpoint responde 202 — no es la telemetría, es
  que nadie entró). El circuito público del spec §1 no existe hasta que se
  publique.
- Hoy: v2 rebasado sobre v3 + UTM/atribución + formatos de card + PNG
  exacto. Primer candidato real del selector: **Ceuta Migrant Crisis**
  (dt-18062: 9 países, 7 idiomas, 466 miembros; lede real generado en
  es/en/fi).

## 1 · Decisiones de cadencia y canal

| decisión | qué | por qué (fuente en §7) |
|---|---|---|
| Cadencia | **2 posts/semana: martes (historia de la semana, kit) + jueves (pieza ligera)**. Piso absoluto: 1/semana (martes). **Quincenal NO**: está bajo el piso de todos los datasets — sirve para mantener, no para lanzar. | 2-3/sem con formatos variados = hasta +120% visibilidad vs esporádico; nunca >1/día (−40%/post). Consistencia > volumen. |
| Hora | **Martes/jueves 08:30-09:30 COT** (= 09:30 ET / 15:30 CET). Público = analistas EU+US. | Tue-Thu concuerdan todas las fuentes; la hora exacta NO (Buffer 16:00 local vs Sprout 11-17). Elegimos la ventana que cubre EU tarde + US mañana. |
| Desde dónde | **Perfil personal de Pedro** publica. La página Atlas **repostea ≥24 h después** (nunca inmediato: parte la golden hour) y Pedro comenta en el repost. ~80/20. | Perfiles 5-8× engagement; páginas alcanzan ~1.6% de sus seguidores. |
| Formato | **Card 1080×1350 portrait** (default del kit). Square si el post lleva 2 imágenes. 1200×627 solo como link-preview. | 91% del consumo es móvil; portrait = más pantalla = más dwell. Documents/multi-imagen lideran engagement (5.9-7%); texto solo 0.88× la mediana. |
| Link | **A/B en los 6 primeros posts**: impares = link en PRIMER COMENTARIO (kit); pares = SIN link en post ni comentario, link solo en la sección *Featured* del perfil + "link en mi perfil" en el último renglón. Se decide con la tabla §5 al post 6. | La penalización al link en el cuerpo es real (−19% a −60%, tamaño disputado). El link-en-comentario está **DISPUTADO** en 2026 (una fuente: sigue funcionando; otra: −80% + castigo al "bridge post"). Nadie tiene datos controlados → medimos nosotros. |
| Hashtags | 0-3, específicos (`#OSINT #MediaAnalysis` + país). Nunca genéricos. | Plateau a 2-3, daño a 6+ (n=991). |
| Copy | Hook ≤140 chars (el lede lo pone el kit), 800-1.100 chars total, párrafos ≤4 líneas, nivel de lectura simple, 1-2 emoji máx como marcadores, **CTA = pregunta en palabras de Pedro** (campo del kit). | Reading level >10º grado = −35%; "1 save ≈ 5 likes"; LinkedIn 2026 baja distribución al copy genérico/IA. |
| Golden hour | Responder TODO comentario en los primeros 90 min (ideal <15 min); responder a las respuestas. Nada de pods. | Replies +30%; reply-to-reply hasta 2.4×; pods detectados y castigados (−40/80%). |

## 2 · El ritual (martes, ~15 min)

1. `cd backend && python scripts/pick_story_of_week.py` → elegir la fila #1
   (o la primera con ≥3 idiomas y ≥4 países; saltar deportes/roundups).
2. Abrir el deep link en prod → `⧉ LinkedIn kit`.
3. **Curar 3 recibos**: solo on-story (el pool trae la enfermedad M1 —
   coches autónomos en Ceuta); ≥2 idiomas si los hay; incluir el state-media
   si existe (queda marcado — es el punto). Deschequear lo que no es la
   historia.
4. **Generate editorial lede**. Si `quote_gate_failed` → cambiar un recibo y
   regenerar (el editor no inventa: si no puede citar, no escribe). Si el
   lede es torpe pero correcto, regenerar una vez; no editarlo a mano (la
   licencia del lede es que cada frase está quote-checked).
5. Formato **portrait** → **Download card PNG** (1080×1350 exactos).
6. Escribir la **pregunta de cierre** en el campo (en tus palabras; una sola;
   que invite a discutir, no a hacer clic).
7. **Copy caption** → pegar en LinkedIn con el PNG. Hashtags al final (≤3).
   Publicar 08:30-09:30 COT.
8. Según el arm (§1 Link): copiar **first comment** del kit y pegarlo como
   primer comentario — o no pegar nada y confiar en *Featured*.
9. 90 min de guardia: responder comentarios.
10. +24 h: repost desde la página Atlas + un comentario de Pedro.
11. **Día 7**: anotar la fila en §5 — LinkedIn analytics (impresiones,
    reacciones, comentarios ≥10 palabras, reposts, clics) + Atlas:
    `python scripts/campaign_acquisition_report.py --days 8 --campaign sow-2026-wNN`.

Jueves (pieza ligera, ~10 min): texto + 1 imagen (screenshot de un panel,
o un card square del kit). Sin link. Ver §3 para el tema de cada semana.

## 3 · Arco de 8 posts (4 semanas) — la "orden de publicación"

Regla del arco (§7): 6-8 posts que CARGAN prueba (un número/screenshot
medido de Atlas cada uno) antes del primer pedido directo. Identidad
(1-3) → credibilidad (4-6) → conversión (7-8).

| # | fecha | tipo | tema | prueba que carga | link | tag |
|---|---|---|---|---|---|---|
| 1 | mar 09-15 | Historia (kit) | **Ceuta Migrant Crisis** — 3 outlets, 3 idiomas, una frontera | card portrait + "11 idiomas; 3/200 state media" | A: 1er comentario | `sow-2026-w38` |
| 2 | jue 09-17 | Origen | Por qué construí una máquina que cuenta *quién* habla, no *qué* pasó (la tesis medición ≠ opinión, 2 párrafos, sin vender) | screenshot del mapa de calor con la leyenda "baseline-normalized" | ninguno | — |
| 3 | mar 09-22 | Historia (kit) | selector de la semana | card + hallazgo medido | B: solo Featured | `sow-2026-w39` |
| 4 | jue 09-24 | "Me equivoqué" | El card v1 que rechacé ("una foto de datos crudos") vs el v2 con editor quote-gated — qué cambió y qué NO puede hacer el editor (citar o callar) | 2 imágenes: card v1 / card v2 (square) | ninguno | — |
| 5 | mar 09-29 | Historia (kit) + **encuesta** | historia de la semana; en el hilo, el post del jueves es la poll | card | A: 1er comentario | `sow-2026-w40` |
| 6 | jue 10-01 | **Poll (la encuesta ligera)** | "Cuando lees una noticia extranjera, ¿qué es lo primero que quisieras saber?" — 3 opciones: *quién la cuenta (y si es prensa estatal)* / *cuántos países la cubren* / *qué falta en la cobertura*. 7 días. Decir qué haremos con el resultado (ordena el Brief). | la pregunta ES la prueba | ninguno | `poll-2026-w40` |
| 7 | mar 10-06 | Historia (kit) + **primer pedido** | historia + "cuenta gratis: guarda historias y recibe la edición" | card | B: Featured + `/register?utm_campaign=register-w41` en 1er comentario | `sow-2026-w41` |
| 8 | jue 10-08 | Manifiesto + pedido | Medición, no opinión: qué promete Atlas y qué NO (sin recibos no hay frase) + resultados de la poll + pedido de registro | tabla de la poll + 1 card | 1er comentario `/register` | `register-w41` |

Después de la semana 4: **estado estable = martes historia (kit) + jueves
alterno** (número medido / detrás de cámaras / respuesta a un comentario
bueno de la semana). Una poll cada 6-8 posts, no más (alcance 1.78× la
mediana pero engagement 0.37× — "trampa de alcance").

## 4 · Qué se mide y contra qué

**LinkedIn (analytics del post, día 7)**: impresiones · reacciones ·
comentarios ≥10 palabras · reposts · clics · ER = (reacciones + comentarios
+ reposts + clics) / impresiones. Semanal: visitas al perfil, seguidores.

**Atlas (telemetría, `campaign_acquisition_report.py`)**: por tag —
`arrived` (sesiones con el tag) → `story` (la historia del link se abrió) →
`value` (first_value_moment) → `signed_up`. El link del kit lleva
`utm_source=linkedin&utm_medium=organic&utm_campaign=sow-YYYY-wNN&utm_content=<historia>`
y el app guarda first-touch por cliente (`lib/acquisition.ts`) — lnkd.in y
el navegador in-app de iOS borran el referrer, así que **solo el UTM cuenta**.

**Benchmarks honestos (<2k seguidores)**: ER mediana 2.2%; 5-7
interacciones/post; LinkedIn dejó de exportar saves/sends por post desde
julio 2026. **Regla**: cada post se juzga contra la MEDIANA de nuestros
propios posts anteriores (a partir del 4º), no contra benchmarks ajenos.
Los primeros 3 son la línea base.

**Decisiones programadas**:
- Post 6 → cerrar el A/B del link (§1) con las columnas `clics` y
  `arrived` de §5.
- Post 8 → primera lectura del arco completo: ¿arrived→story ≥50%?
  ¿algún signed_up? → decide si la pieza B (registro) recibe más peso o si
  el problema está en la puerta.
- La encuesta "de verdad" (3 preguntas in-app a quien llega por UTM) queda
  **diferida** hasta ver la poll del post 6 — no se construye superficie
  nueva sin evidencia (anti-goal del wedge).

## 5 · Bitácora (una fila por post — llenar el día 7)

| # | fecha | tag | arm link | impr. | reacc. | coment. ≥10p | reposts | clics | ER | arrived | story | value | signups | nota |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 09-15 | sow-2026-w38 | A | | | | | | | | | | | |
| 2 | 09-17 | — | — | | | | | | | — | — | — | — | |
| 3 | 09-22 | sow-2026-w39 | B | | | | | | | | | | | |
| 4 | 09-24 | — | — | | | | | | | — | — | — | — | |
| 5 | 09-29 | sow-2026-w40 | A | | | | | | | | | | | |
| 6 | 10-01 | poll-2026-w40 | — | | | | | | | — | — | — | — | votos: |
| 7 | 10-06 | sow-2026-w41 | B+reg | | | | | | | | | | | |
| 8 | 10-08 | register-w41 | reg | | | | | | | | | | | |

## 6 · Anti-patrones (no hacer)

- Link en el cuerpo del post. Posts "puente" ("link abajo 👇").
- Pods de engagement / pedir likes a amigos en bloque (patrón recíproco
  detectado → −40/80% fuera de red).
- >3 hashtags · >1 post/día · editar el post con un link promocional
  después de que agarró tracción · publicar y desaparecer.
- Copy genérico de IA. El lede del kit es prosa citada, no marketing; la
  pregunta de cierre la escribe Pedro. Nada de "🚀 Excited to announce".
- Inventar un número. Si el kit no lo midió, no va en el post.
- Presentar prensa estatal como neutral (el card y el caption la marcan;
  no borrar la marca "para que se vea limpio").

## 7 · Fuentes (investigación 2026-09-11)

Casi nada es oficial de LinkedIn — son estudios de terceros (van der Blom
1.8M posts; Metricool 673k; Buffer 4.8M; ContentIn 100k). Direccionales;
la mediana propia manda.

- Cadencia/formatos/algoritmo: [AuthoredUp — LinkedIn algorithm](https://authoredup.com/blog/linkedin-algorithm) · [Metricool 2026 study](https://metricool.com/press-release-linkedin-study-2026/) · [Buffer — best time](https://buffer.com/resources/best-time-to-post-on-linkedin/) · [Sprout — best times](https://sproutsocial.com/insights/best-times-to-post-on-linkedin/) · [Socialinsider benchmarks](https://www.socialinsider.io/social-media-benchmarks/linkedin) · [ContentIn benchmarks](https://contentin.io/blog/linkedin-engagement-benchmarks/)
- Tamaño de imagen: [Sendible — post size](https://www.sendible.com/insights/linkedin-post-size)
- Links (disputado): [Gromming — external links penalty](https://gromming.com/blog/linkedin-external-links-penalty) · [Goodman — algorithm 2026](https://melaniegoodmanlinkedinconsultant.substack.com/p/linkedin-algorithm-2026-reach-topic-authority) · [Jurka (LinkedIn) sobre el feed](https://www.linkedin.com/posts/timjurka_the-linkedin-feed-is-where-professionals-activity-7457822308880134144-iYXb) · [LinkedInPreview — editing](https://linkedinpreview.com/blog/does-editing-a-linkedin-post-reduce-reach)
- Estructura/hashtags: [ConnectSafely — headline guide 2026](https://connectsafely.ai/articles/linkedin-post-headline-writing-guide-2026) · [ContentIn — hashtags](https://contentin.io/blog/do-hashtags-work-on-linkedin/) · [Sprout — hashtags](https://sproutsocial.com/insights/linkedin-hashtags/)
- Golden hour: [Expandi](https://expandi.io/blog/best-time-to-post-on-linkedin/)
- Perfil vs página: [DigitalApplied](https://www.digitalapplied.com/blog/linkedin-personal-profiles-vs-company-pages-8x-engagement)
- Arco de lanzamiento: [Majd Alaily — content startup strategy](https://majdalaily.substack.com/p/content-startup-strategy) · [Indie Hackers — launch log](https://www.indiehackers.com/post/everything-i-posted-on-linkedin-leading-up-to-launch-a-deep-dive-7a81761ac9)
- Polls: [ContentIn — polls](https://contentin.io/blog/linkedin-polls/) · [AuthoredUp — polls](https://authoredup.com/blog/linkedin-polls)
- Medición/UTM: [Socialinsider — ER](https://www.socialinsider.io/blog/linkedin-engagement-rate/) · [Track Link — UTM for LinkedIn](https://gettrack.link/utm-parameters-for-linkedin) · [ZenABM — tracking params](https://zenabm.com/blog/linkedin-url-tracking-parameters)
- Anti-patrones: [ConnectSafely — pods crackdown 2026](https://connectsafely.ai/articles/linkedin-engagement-pods-crackdown-2026) · [Neil Patel — AI slop crackdown](https://neilpatel.com/blog/linkedin-ai-slop-crackdown-content-strategy/) · [SMT — Dan Roth on feed updates](https://www.socialmediatoday.com/news/linkedin-shares-insights-into-latest-feed-algorithm-updates/708710/)
