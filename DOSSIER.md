---
nombre: Observatory-Global
tipo: proyecto
anillo: 1
familia: personal
estado: pausado
remoto: github.com/pedro-cmyks/Observatory-Global
visibilidad: privado
trabajo_vivo_en: v3-intel-layer
actualizado: 2026-09-16
tags: [inteligencia-narrativa, osint, fastapi, react-typescript, produccion-desplegada, atlas]
---

# Observatory-Global

Atlas: una plataforma que mira como se mueve una noticia por el mundo. Traga
señales abiertas (GDELT, RSS curado, ReliefWeb, NewsData, MediaStack, NewsAPI,
Reddit, Google Trends, Wikipedia pageviews) y las junta en "historias vivas"
con procedencia, recibos y medidas de movimiento. Se ve en tres pantallas: un
landing, un diario (/brief) y una consola de analista (/app) con mapa, hilos,
ficha de pais e investigacion exportable. No es un agregador: buena parte del
codigo esta dedicada a medir si la historia que sirve es la correcta y a
declarar NULL cuando no lo sabe.

## Estado

Pausado, no abandonado. Ultimo commit de trabajo `48cfc111`, 2026-08-20 17:30
(un fix de test: una fecha congelada en un fixture que expiro sola). El arbol
de trabajo esta limpio, sin nada sin commitear.

El trabajo vivo NO esta en `main`. La rama por defecto en el remoto es
`v3-intel-layer` (`origin/HEAD` apunta ahi) y es donde esta el checkout local.
Verificado: **`main` esta 2.113 commits atras de `v3-intel-layer` y 0 commits
adelante** (`git rev-list --left-right --count origin/main...origin/v3-intel-layer`
da `0 2113`); el ultimo commit de `main` es del 2026-04-29. Quien clone y se
quede en `main` por costumbre va a ver un proyecto de abril.

Hay 37 ramas remotas. `eclipse-dramatic-moment` apunta exactamente al mismo
commit que `v3-intel-layer` (es un duplicado). Las otras 34 son cascara: 26
`claude/*` (22 de julio, tres de mayo, una de agosto), una `codex/*`, seis
`feat/*` de noviembre 2025 (cuatro `radar-*`, `gdelt-live-integration` y
`iter2-backendflow/hexmap-api`), y `v2-clean-architecture`.

2.327 commits en la rama viva publicada (2.341 en todas las ramas del remoto),
primero el 2025-11-11. El trabajo se corto con un plan abierto, no con un
cierre: `docs/superpowers/plans/2026-08-20-plan-motor.md` (`c54dc3c9`, M1-M4,
autoevaluacion 52/100) y el pre-registro de las barras del gate M1 ANTES de
elegir el fix (`686f9d28`); encima de esos dos solo quedaron un fix de test y
la mudanza del repo fuera de iCloud. Produccion quedo desplegada y sigue en pie.

## Por donde entrar

- `/var/home/pedro/Observatory-Global/README.md` — la mejor puerta y esta al
  dia: que es, que NO es, las tres superficies, la tabla de fuentes con el rol
  de cada una, la arquitectura por capa y como correrlo. 5 KB, se lee entero.
- `/var/home/pedro/Observatory-Global/docs/ARCHITECTURE.md` — el diagrama del
  flujo de datos, de la ingesta a los endpoints de lectura y de ahi a la UI.
  Leer segundo.
- `/var/home/pedro/Observatory-Global/docs/superpowers/plans/2026-08-20-plan-motor.md`
  — que sigue: el plan abierto del ultimo dia de trabajo, con la evidencia
  medida que lo ordena. Si alguien retoma, empieza aca.
- `/var/home/pedro/Observatory-Global/backend/app/main_v2.py` — el arranque del
  backend (`uvicorn app.main_v2:app`). Corto, y los comentarios explican las
  decisiones vivas: rate limiting antes de CORS, degradacion 503 `db_busy`.

Lo que NO conviene abrir primero: `CLAUDE.md` (288 KB de bitacora historica) y
`STATUS.md` (135 KB, encabezado "Updated: 2026-07-13", cinco semanas atras del
ultimo commit y en contradiccion con CLAUDE.md).

## Como se corre

El README y el `Makefile` no dicen lo mismo: el README instala con `pip` y el
`Makefile` corre todo con `poetry` (y no hay `poetry.lock` ni seccion
`[tool.poetry]` en el pyproject). No verificado en esta maquina: no se levanto
nada para escribir este dossier.

```
# a mano, como dice el README
cd backend && pip install -e ".[dev]" && uvicorn app.main_v2:app --reload --port 8000
cd frontend-v2 && npm install && npm run dev

# o con make (58 targets documentados; `make help` los lista)
make up        # cd infra && docker compose up --build -d  (postgres + redis + api + front)
make test      # backend (251 archivos de test) + frontend (162)
make migrate   # NO sirve: corre `alembic upgrade head` y el repo no tiene
               # alembic; las 108 migraciones .sql de backend/migrations
               # se aplican a mano
make health

# o el panel de consola, que sigue el orden del README
python atlas.py   # docker -> backend -> frontend -> ingesta
```

Hace falta `backend/.env` (hay `backend/.env.example`; el `.env.example` de la
raiz es otro archivo, con otras claves). Lo que NO se puede correr aca:
los crons de produccion, que son plists de launchd (macOS).

## Lo que le falta

- Un solo documento de estado que diga la verdad de hoy, y archivar los otros
  cinco registros (CLAUDE.md, STATUS.md, SESSION_LOG.md, AGENTS.md, GEMINI.md
  se contradicen entre si) (horas).
- Verificar si produccion sigue viva y que esta costando: Fly (api +
  nlp_worker), Supabase, Upstash y tres APIs de noticias con cuota (NewsData,
  MediaStack, NewsAPI), un mes sin mirar (horas).
- Pinear las dependencias del backend: `backend/requirements.freeze.txt` esta
  VACIO (0 bytes) pese al commit que dice que congelo el venv, y lo unico que
  queda son rangos `>=`: `backend/pyproject.toml` (fastapi, pydantic, asyncpg)
  y `backend/requirements-nlp.txt` (`torch>=2.2.0`, `transformers>=4.40.0`)
  (minutos).
- Decir en el README que la capa de operacion es macOS-only, o portarla (horas).
- Sacar los 155 MB de corpus de `docs/research` de git, dejando los informes
  .md y un manifiesto de hashes (horas).
- Podar las 37 ramas remotas y decidir que hacer con `main`, que con ese nombre
  y 2.113 commits de atraso es la trampa mas obvia del repo (horas).
- Borrar o marcar como archivo `walkthrough.md` y `docs/state/KNOWN_ISSUES.md`:
  describen un frontend de noviembre 2025 que ya no existe, y walkthrough.md
  esta en la raiz al lado del README (minutos).
- Un CI minimo, aunque sea lint + tests en push: no existe `.github/`, y 413
  archivos de test solo valen si alguien se acuerda de correrlos (horas).

## Relaciones

- [[calipso]] es el heredero directo del metodo que nacio aca: la misma
  estructura `docs/superpowers/{specs,plans}` con documentos fechados, los
  mismos gates pre-registrados antes de medir, la misma insistencia en no tocar
  sin medir primero. Atlas es donde se invento; Calipso es donde se aplica hoy,
  y es donde esta la atencion de Pedro desde el 08-20. No comparten codigo.
- [[research-court]] es el intento de convertir en negocio lo que aca es
  metodo: la corte adversarial de roles, la procedencia auditable y el ledger
  de fuentes son el label-court y los recibos de Atlas empaquetados como
  servicio. Linaje conceptual, sin codigo compartido.
- [[AvesCO]], [[noaa-proyecto]], [[CAM-CRM-Vincere]],
  [[CAM-CRM-Vincere-collector-build]] y [[cam-crm-vincere-demo]] no tienen
  relacion con este repo: ni codigo, ni referencias cruzadas, ni dominio en
  comun. Se nombran para dejar constancia de que se busco y no hay.

Adentro del propio repo hay dos cosas que casi son proyectos aparte: `markets/`
(capa L4 de precios, con su propio cron y su propio router, que empuja a la base
de Atlas) y `legacy/` (el backend v1 y el frontend v1, muertos pero versionados).

## Cuidado con

- **Produccion depende de un Mac que tiene que estar encendido.** Los 16 crons
  que alimentan el pipeline son plists de launchd (`infra/launchd/`, 15, y
  `backend/infra/launchd/`, 1) que corren en el Mac de Pedro (el M1) y apuntan a
  rutas `/Users/pedro/...`. La API en Fly (`atlas-api-pedro`, dos process
  groups: `app` y `nlp_worker`) y el frontend en Vercel (los rewrites de
  `frontend-v2/vercel.json` mandan `/api/*` a `atlas-api-pedro.fly.dev`) siguen
  sirviendo igual. Si ese Mac no enciende, **produccion sirve datos viejos y
  nada avisa**: no hay CI, no hay alerta y la pagina no se rompe.
- `backend/.env` existe en claro en el disco y es la llave de la base de
  produccion (URLs de base y cache, y claves de las APIs de noticias). Lo bueno:
  nunca se commiteo un `.env` en toda la historia del repo (verificado con
  `git log --all --diff-filter=A`) y `.gitignore` lo cubre. No se transcribe
  ningun valor aca.
- La rama `main`. Ver "Estado": 2.113 commits atras. Si alguien abre el repo en
  GitHub y no mira que `origin/HEAD` es `v3-intel-layer`, lee otro proyecto.
- 155 MB de corpus de investigacion versionados en `docs/research` (.json y
  .jsonl: anotaciones de LLM, universos de sujetos, ledgers de remapeo) sin LFS.
  El `.git` pesa 65 MB. Si este repo alguna vez se hace publico, el corpus se
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
- Licencia PolyForm Noncommercial 1.0.0, no aprobada por la OSI: leer y usar sin
  fines comerciales es libre, cualquier uso comercial necesita licencia aparte.
  Ninguna herramienta estandar la entiende como licencia libre.
- El checkout local pesa ~1,3 GB, casi todo `backend/.venv` y `node_modules`.
  Una copia de seguridad ingenua de la carpeta es cara. Antecedente: el commit
  `ccda8161` documenta que una tormenta de iCloud dejo el repo danado, y ese fue
  el motivo de mudarlo fuera de iCloud.
