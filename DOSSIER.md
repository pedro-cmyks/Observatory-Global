---
nombre: Observatory-Global
tipo: proyecto
anillo: 1
familia: personal
estado: activo
remoto: github.com/pedro-cmyks/Observatory-Global
visibilidad: privado
trabajo_vivo_en: v3-intel-layer
actualizado: 2026-09-16
tags: [inteligencia-narrativa, osint, fastapi, react-typescript, produccion-desplegada, atlas]
---

# Observatory-Global

Atlas: una plataforma que mira como se mueve una noticia por el mundo. Traga
señales abiertas (GDELT, RSS curado, ReliefWeb, NewsData, MediaStack, NewsAPI,
Reddit, Bluesky, Lemmy, Google Trends, Wikipedia pageviews) y las junta en
"historias vivas" con procedencia, recibos y medidas de movimiento. Se ve en
cuatro superficies: un landing, un diario (/brief), una consola de analista
(/app) con mapa, hilos, ficha de pais e investigacion exportable, y desde
agosto una puerta de registro (/register + verificacion por correo). No es un
agregador: buena parte del codigo esta dedicada a medir si la historia que
sirve es la correcta y a declarar NULL cuando no lo sabe.

## Estado

Activo. Ultimo commit de trabajo `c61728d4`, 2026-09-15: el paquete del primer
post de LinkedIn — dos historias producidas con el kit en produccion, cards PNG
de 1080x1350 y 1080x1080 reales, texto, primer comentario y la evidencia del
link. El arbol de trabajo esta limpio.

Los 39 commits entre el 2026-08-24 y el 2026-09-15 son dos lineas, no una:

- **La rafaga de motor y ops del 08-24/25.** Auditoria de salud (una raiz,
  cuatro sintomas: el runner nocturno retenia el heavy lock ~9h y mataba de
  hambre al catchup de archivo, la base engordo a 13GB, los INSERTs de ingesta
  cayeron y el volumen GDELT se fue al 30%), la cirugia M4 que suelta el lock
  tras R1 (`dfa26e73`), la lane sombra M1 con sus cuatro iteraciones
  (`06049723`), corte-con-cuerpos monotono (`b032ee9a`), archivo Stage-B
  semanal (`203f88a4`), la voz ASD-STE100 (`4d8bff01`) y el leg anthropic del
  threevendor ruteado por claude-CLI (`ed84c9d4`).
- **La campana de lanzamiento, del 09-11 al 09-15** — lo que el dossier viejo
  no mencionaba. El kit de LinkedIn v2 (mini-editorial quote-gated + curacion
  de recibos) estaba construido desde el 08-24 pero **nunca se habia mergeado**:
  tres semanas con prod sirviendo el v1 que Pedro ya habia rechazado. El 09-11
  se rebaso sobre v3 (`d2484de2`: hook-first, formatos 1080x1350, PNG exacto,
  UTM y atribucion, calendario). El 09-14 una revision editorial independiente
  (`e199bbfb`) midio lo que saldria del kit en tres historias reales y lo
  reprobo con numeros: el pool que ofrecia el kit era 20-50% on-story, dos de
  tres etiquetas eran de otra semana, y una traduccion convirtio tiendas de
  campaña en comercios pasando el quote gate. El 09-15 se arreglaron los cuatro
  defectos (`95196369` y siguientes: pool por relevancia a la etiqueta con
  buscador, traduccion con contexto de la historia, edad de la etiqueta visible,
  gate anti-frases-huerfanas) mas dos fixes de traduccion por escritura
  (`45ec009e`, `25982986`: royanews.tv llega etiquetado `lang=en` con titulares
  en arabe, y la identidad "ya esta en ingles" devolvia el arabe tal cual).

**Produccion esta viva y midiendo, verificado hoy** (2026-09-16, dos GET de
lectura): `/api/v2/stats` responde 200 en 1,3s con `degraded:false`, ingesta
`healthy`, 63.971 señales en 24h, 5.422 fuentes distintas, la señal mas nueva
de hace minutos y la mas vieja de hace 7,6 dias (la poda volvio a correr);
`/api/v2/threads` sirve historias dynamic con recibos; el frontend en Vercel
responde 200. El volumen de 64K/24h esta muy por encima del colapso del 08-22
(24K) y todavia por debajo del baseline del 08-17 (131K).

El trabajo vivo NO esta en `main`. La rama por defecto en el remoto es
`v3-intel-layer` (`origin/HEAD` apunta ahi) y es donde esta el checkout local.
Verificado: **`main` esta 2.152 commits atras de `v3-intel-layer` y 0 commits
adelante**; su ultimo commit es del 2026-04-29. Quien clone y se quede en `main`
por costumbre va a ver un proyecto de abril.

Hay 37 ramas remotas y 36 son cascara. `eclipse-dramatic-moment` **ya no es un
duplicado de la rama viva** (lo era en agosto): quedo congelada en `48cfc111`,
2026-08-20, 39 commits atras. Las otras 35: 26 `claude/*` (22 de julio, tres de
mayo, una de agosto), una `codex/*` de mayo, seis `feat/*` de noviembre 2025
(cuatro `radar-*`, `gdelt-live-integration`, `iter2-backendflow/hexmap-api`),
`v2-clean-architecture` de noviembre 2025 y `main`.

2.366 commits en la rama viva publicada (2.380 en todas las ramas del remoto),
el primero el 2025-11-11. Los cuatro commits de este DOSSIER.md viven solo en el
disco: la rama local esta cuatro commits adelante del remoto, sin push.

El frente de motor sigue abierto y **cambio de orden por evidencia**. El plan
del 2026-08-20 (`docs/superpowers/plans/2026-08-20-plan-motor.md`, M1-M4,
autoevaluacion 52/100) mandaba M1 (la assignment lane: 92,2% del corpus servible
no se vuelve historia) y despues M2 (el predicado de etiquetas). La lane sombra
se construyo y se calibro cuatro veces, y el veredicto invirtio el orden: el
destino esta fragmentado — cinco topics maritimos de Hormuz, cuatro de
Panettiere, dos con la etiqueta identica "Neutrogena Backlash Response" — asi
que "la historia correcta" no es un destino bien definido y ningun juez la
elige de forma estable. G-RECALL es alcanzable (20-23% proyectado contra una
barra de 20%); G-PRECISION depende de des-fragmentar primero. La decision de
cual de las tres salidas tomar es de Pedro y esta pendiente.

## Por donde entrar

- `/var/home/pedro/Observatory-Global/README.md` — sigue siendo la mejor puerta
  conceptual: que es, que NO es, las superficies, la tabla de fuentes con el rol
  de cada una, la arquitectura por capa y como correrlo. 5 KB, se lee entero.
  Cuidado: su ultimo commit es del 2026-06-08, asi que no sabe del kit de
  LinkedIn, de la puerta de registro ni de la campana.
- `/var/home/pedro/Observatory-Global/docs/campaign/2026-09-linkedin-calendar.md`
  — el documento de trabajo VIVO: cadencia, el ritual de 15 minutos, el arco de
  8 posts, que se mide contra que, y la bitacora (§5). Si alguien retoma el
  proyecto, empieza aca: es lo ultimo que se movio y la bitacora esta vacia.
- `/var/home/pedro/Observatory-Global/docs/campaign/posts/2026-09-15/README.md`
  — lo ultimo que Atlas produjo: el paquete listo para publicar (Iran y Ceuta,
  texto exacto, cards, primer comentario, y la evidencia sobre la penalizacion
  del link).
- `/var/home/pedro/Observatory-Global/docs/state/2026-08-24-health-audit.md` —
  como se rompe la maquina. Una raiz, cuatro sintomas, con la cascada dibujada.
  Es el mejor mapa de operacion que tiene el repo.
- `/var/home/pedro/Observatory-Global/docs/superpowers/plans/2026-08-20-plan-motor.md`
  + `docs/research/recall-229/2026-08-24-m1-a2-shadow-calibration.md` — el frente
  de motor: el plan y la medicion que le cambio el orden.
- `/var/home/pedro/Observatory-Global/backend/app/main_v2.py` — el arranque del
  backend (`uvicorn app.main_v2:app`). Corto, y los comentarios explican las
  decisiones vivas: rate limiting antes de CORS, degradacion 503 `db_busy`.

Lo que NO conviene abrir primero: `CLAUDE.md` (288 KB de bitacora historica) y
`STATUS.md` (132 KB, encabezado "Updated: 2026-07-13", nueve semanas atras del
ultimo commit y en contradiccion con CLAUDE.md).

## Como se corre

El README y el `Makefile` no dicen lo mismo: el README instala con `pip` y el
`Makefile` corre todo con `poetry` (y no hay `poetry.lock` ni seccion
`[tool.poetry]` en el pyproject). No verificado en esta maquina: no se levanto
nada para escribir este dossier (lo unico que se toco de produccion fueron dos
GET de lectura).

```
# a mano, como dice el README
cd backend && pip install -e ".[dev]" && uvicorn app.main_v2:app --reload --port 8000
cd frontend-v2 && npm install && npm run dev

# o con make (58 targets documentados; `make help` los lista)
make up        # cd infra && docker compose up --build -d  (postgres + redis + api + front)
make test      # backend (254 archivos de test) + frontend (169)
make migrate   # NO sirve: corre `alembic upgrade head` y el repo no tiene
               # alembic; las 108 migraciones .sql de backend/migrations
               # se aplican a mano
make health

# o el panel de consola, que sigue el orden del README
python atlas.py   # docker -> backend -> frontend -> ingesta
```

El ritual semanal de la campana (el unico proceso de usuario que hay hoy) son
dos comandos y el app:

```
cd backend && python scripts/pick_story_of_week.py
# -> elegir una fila, abrir su deep link en prod, boton "LinkedIn kit" en el
#    detalle de la historia: curar 3 recibos, generar el lede quote-gated,
#    formato portrait, Download card PNG, copiar caption y primer comentario.
cd backend && python scripts/campaign_acquisition_report.py --days 8 --campaign sow-2026-w38
```

Hace falta `backend/.env` (hay `backend/.env.example`; el `.env.example` de la
raiz es otro archivo, con otras claves). Lo que NO se puede correr aca: los
crons de produccion, que son 17 plists de launchd (`infra/launchd/`, 16, y
`backend/infra/launchd/`, 1) y solo existen para macOS.

## Lo que le falta

- **Publicar.** El paquete del post #1 esta listo desde el 2026-09-15 y la fila
  1 de la bitacora esta vacia. Todo el circuito publico (impresiones, clics,
  `arrived` -> `story` -> `value` -> `signed_up`, y el A/B del link en primer
  comentario que se decide al post 6) queda sin medir hasta que salga algo. El
  dato duro que lo motiva: telemetria de prod con **0 eventos entre el 08-26 y
  el 09-10**, dieciseis dias sin una sola visita medida (minutos, y despues
  noventa de guardia).
- La decision de Pedro sobre M1: M2 primero (des-fragmentar el espacio de
  destino con el 8º gate ya pre-registrado), familia ② (adjuntar a la
  familia/umbrella en vez del topic exacto, que cambia el contrato de serving),
  o seguir iterando prompts (desaconsejado, rendimientos decrecientes). El arco
  de motor espera esto (dias).
- Las etiquetas viejas y la fragmentacion de identidad que la revision editorial
  dejo medidas: dos de tres historias servian una etiqueta de otra semana, y
  cinco topics distintos de Ceuta coexisten (18062, 1508, 9903, 5004, 8438).
  Es la misma enfermedad que bloquea M1, vista desde el lector (semanas).
- Volumen de ingesta: 64K señales/24h contra un baseline de 131K en agosto. La
  causa de la caida se ataco (poda + suelta del lock) pero la recuperacion esta
  a medias y nadie re-midio (horas de medicion).
- Feed rot: ~25 feeds RSS flagged por dia (10 inalcanzables, 10 stale cronicos
  — chinadaily lleva 3.176 dias). Erosiona la diversidad de voz en silencio
  (horas).
- Un solo documento de estado que diga la verdad de hoy — este — y archivar los
  otros cinco registros (CLAUDE.md, STATUS.md, SESSION_LOG.md, AGENTS.md,
  GEMINI.md se contradicen entre si) (horas).
- Pinear las dependencias del backend: `backend/requirements.freeze.txt` fue
  BORRADO en `e2552240` (estaba vacio pese al commit que decia que congelaba el
  venv), asi que lo unico que queda son rangos `>=`: `backend/pyproject.toml`
  (fastapi, pydantic, asyncpg) y `backend/requirements-nlp.txt`
  (`torch>=2.2.0`, `transformers>=4.40.0`) (minutos).
- M4 estructural, el churn de indices: el bloat volvio en cinco semanas y va a
  volver (130K señales/dia con retencion de 7 dias inflan indices por diseño).
  Las opciones (REINDEX CONCURRENTLY programado, fillfactor, particion por dia)
  se deciden con EXPLAIN y tamaños, no con opinion (horas de medicion).
- Decir en el README que la capa de operacion es macOS-only, o portarla (horas).
- Sacar los 156 MB de corpus de `docs/research` de git, dejando los informes
  .md y un manifiesto de hashes (horas).
- Podar las 37 ramas remotas y decidir que hacer con `main`, que con ese nombre
  y 2.152 commits de atraso es la trampa mas obvia del repo (horas).
- Borrar o marcar como archivo `walkthrough.md` y `docs/state/KNOWN_ISSUES.md`:
  describen un frontend de noviembre 2025 que ya no existe, y walkthrough.md
  esta en la raiz al lado del README (minutos).
- Un CI minimo, aunque sea lint + tests en push: no existe `.github/`, y 423
  archivos de test solo valen si alguien se acuerda de correrlos (horas).

## Relaciones

- [[calipso]] es el heredero directo del metodo que nacio aca: la misma
  estructura `docs/superpowers/{specs,plans}` con documentos fechados, los
  mismos gates pre-registrados antes de medir, la misma insistencia en no tocar
  sin medir primero. Atlas es donde se invento; Calipso es donde se aplica hoy.
  **Los dos estan vivos al mismo tiempo**: el ultimo commit de trabajo de Atlas
  (09-15) es del mismo dia que el ultimo commit de trabajo de Calipso (los dos
  repos recibieron ademas su DOSSIER.md hoy). No comparten codigo.
- [[research-court]] es el intento de convertir en negocio lo que aca es
  metodo: la corte adversarial de roles, la procedencia auditable y el ledger
  de fuentes son el label-court y los recibos de Atlas empaquetados como
  servicio. El quote gate del lede editorial del kit (cada frase tiene que
  citar un recibo con una cita verbatim, o se cae) es esa misma idea puesta a
  producir prosa publicable. Linaje conceptual, sin codigo compartido.
- [[AvesCO]], [[noaa-proyecto]], [[CAM-CRM-Vincere]],
  [[CAM-CRM-Vincere-collector-build]] y [[cam-crm-vincere-demo]] no tienen
  relacion con este repo: ni codigo, ni referencias cruzadas, ni dominio en
  comun. Se nombran para dejar constancia de que se busco y no hay.

Adentro del propio repo hay dos cosas que casi son proyectos aparte: `markets/`
(capa L4 de precios, con su propio cron y su propio router, que empuja a la base
de Atlas) y `legacy/` (el backend v1 y el frontend v1, muertos pero versionados).

## Cuidado con

- **El checkout local puede estar muchos commits atras del remoto y nada avisa.**
  Paso hoy, 2026-09-16: el disco decia que el ultimo trabajo era del 20 de
  agosto y el remoto tenia 39 commits mas, hasta el 15 de septiembre. Un
  dossier anterior leyo `git log -1` en el disco y declaro el proyecto PAUSADO
  cuando estaba activo. **`git log -1` no mide el estado de un proyecto; mide el
  estado de una carpeta.** Antes de juzgar: `git fetch --all` y
  `git rev-list --left-right --count @{u}...HEAD`. No hay CI, ni hook, ni
  notificacion que lo grite.
- **Produccion depende de un Mac que tiene que estar encendido.** Los 17 crons
  que alimentan el pipeline son plists de launchd (`infra/launchd/`, 16, y
  `backend/infra/launchd/`, 1) que corren en el Mac de Pedro (el M1) y apuntan a
  rutas `/Users/pedro/...`. La API en Fly (`atlas-api-pedro`, dos process
  groups: `app` y `nlp_worker`) y el frontend en Vercel (los rewrites de
  `frontend-v2/vercel.json` mandan `/api/*` a `atlas-api-pedro.fly.dev`) siguen
  sirviendo igual. Si ese Mac no enciende, **produccion sirve datos viejos y
  nada avisa**: no hay CI, no hay alerta y la pagina no se rompe. La auditoria
  del 08-24 documenta la version fina de esa trampa: un solo runner que retiene
  el lock nueve horas basta para que la base engorde, la ingesta caiga al 30% y
  todo siga "verde".
- **El saldo de un proveedor LLM se acaba en silencio.** DeepSeek se quedo sin
  saldo el sabado 13-sep a las 07:01 UTC (~5.000 llamadas/dia, 7.600 solo de
  `typing` en tres dias); el nocturno del 13 al 14 corrio sin court y sin
  relabel, y nadie se entero hasta que alguien fue a mirar. Ya paso antes con
  Anthropic (junio, cuatro noches de portada congelada). Cada lane sancionada
  sigue montada sobre un saldo.
- **Lo que sale del kit de LinkedIn no es publicable sin curacion humana.** Con
  los fixes del 09-15 el pool mejoro muchisimo (Ceuta paso de 6/30 a 52/60
  on-story), pero la revision del 09-14 dejo claro que el problema de fondo
  —etiquetas rancias, identidades fragmentadas, pools de umbrella que mezclan
  historias— no lo arregla el kit. Y no confies en `source_lang`: royanews.tv
  llega etiquetado `en` con titulares en arabe; la traduccion ahora decide por
  la escritura del texto, no por la etiqueta.
- `backend/.env` existe en claro en el disco y es la llave de la base de
  produccion (URLs de base y cache, y claves de las APIs de noticias). Lo bueno:
  nunca se commiteo un `.env` en toda la historia del repo (verificado con
  `git log --all --diff-filter=A`) y `.gitignore` lo cubre. No se transcribe
  ningun valor aca.
- La rama `main`. Ver "Estado": 2.152 commits atras. Si alguien abre el repo en
  GitHub y no mira que `origin/HEAD` es `v3-intel-layer`, lee otro proyecto.
- 156 MB de corpus de investigacion versionados en `docs/research` (.json y
  .jsonl: anotaciones de LLM, universos de sujetos, ledgers de remapeo) sin LFS.
  El `.git` pesa 68 MB. Si este repo alguna vez se hace publico, el corpus se
  publica con el.
- CORS abierto por defecto: si `ATLAS_CORS_ORIGINS` no esta seteado,
  `main_v2.py` arranca con `allow_origins=["*"]` y solo imprime un warning. Es
  deliberado (que un deploy no quede mudo) y el propio codigo dice "set it
  before public launch", pero es un pie armado esperando un deploy sin esa
  variable.
- Dependencias sin pin (ver "Lo que le falta"): con torch y transformers en la
  lista, el venv que hoy funciona no se reconstruye igual dentro de un ano.
- Correo personal de Pedro en archivos versionados (entre ellos
  `.env.example` en la raiz, donde ni siquiera hacia falta que fuera real). No se
  transcribe.
- Licencia MIT desde 2026-10-05 (antes PolyForm Noncommercial 1.0.0, que no era
  open source segun la OSI). El repositorio es publico.
- El checkout local pesa ~1,3 GB, casi todo `backend/.venv` y `node_modules`.
  Una copia de seguridad ingenua de la carpeta es cara. Antecedente: el commit
  `ccda8161` documenta que una tormenta de iCloud dejo el repo danado, y ese fue
  el motivo de mudarlo fuera de iCloud.
