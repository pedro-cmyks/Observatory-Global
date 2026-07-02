# Prompts para sesiones paralelas — 2026-07-02

El chat principal (este hilo) trabaja #249 (desalojo GDELT). L11 se fue a su
propio chat. Los siguientes son prompts autocontenidos para cuando abras más
sesiones. Regla anti-colisión: cada prompt lista qué NO tocar.

## L11 — Sistema solar (YA ENTREGADO a Pedro, va en otro chat)
Ver el prompt en el hilo principal / capture doc L11. No tocar:
BriefNewspaper, routers/search.py, thread_ranking.

## #248 — Clases de ruido en persons/threads
```
Trabaja el issue #248 de Observatory-Global (repo
/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal, branch v3-intel-layer).
Tres clases medidas: (1) byline-persons tipo "bysarah falson" (prefijo by+
nombre pegado, GDELT extrae la firma); (2) entertainment-about-crisis
("Ek Hota Maalin" — película SOBRE un desastre clasificada como el desastre);
(3) concatenaciones GDELT "donald trumpafter" (dos tokens pegados).
Método: mide primero cada clase en prod (SQL sobre signals_v2.persons /
nlp_persons), luego guards en backend/app/utils.py::_is_valid_person y/o
subjects.classify_subject, con tests en tests/test_person_hygiene.py.
Precedente de estilo: _PHOTO_CREDIT_TOKENS (commit 2264ecf). Deploy Fly +
verificación prod. NO tocar: frontend (otro chat), ThemeDetail.
```

## Search P3 — semantic-on-submit
```
Implementa search P3 del plan docs/specs/2026-07-01-search-engine-plan.md
(repo ObservatorioGlobal, branch v3-intel-layer): en submit (Enter), si los
segmentos léxicos vienen flacos (<3 hits), consulta el lane semántico
(embed service EMBED_SERVICE_URL, patrón en research_semantic.py /
fetch_semantic_signal_matches) y mezcla anchors semánticos etiquetados en el
dropdown. OJO: el índice HNSW se reconstruyó 2026-07-03 03:15 (verifica
SELECT indexname FROM pg_indexes WHERE tablename='signal_embeddings' antes).
Degradación honesta si el embed service no responde (gap note, nunca 500).
Prod-verify con "crisis hídrica en Teherán". NO tocar: BriefNewspaper,
ThemeDetail.
```

## Search P4 — telemetría de búsqueda (✅ TOMADO por el hilo principal, SHIPPED 2026-07-02)
```
Implementa search P4 (docs/specs/2026-07-01-search-engine-plan.md, repo
ObservatorioGlobal): eventos search_query / search_result_click (segmento,
posición, query-length, cero-resultados) por el pipeline de telemetría
existente (busca brief_open / first_value_moment en BriefNewspaper.tsx para
el patrón + endpoint). El objetivo del wedge: saber si la gente ENCUENTRA.
Dashboard no — solo escribir filas + una query SQL de lectura semanal
documentada en el spec. Verifica end-to-end preview→202→fila en prod.
NO tocar: ThemeDetail, thread_ranking.
```

## #247 C1/C2 + C4 — batch de diseño (necesita el ojo de Pedro)
```
Ejecuta los batches C1/C2 de #247 (repo ObservatorioGlobal, branch
v3-intel-layer): consolidación de panel-headers y familias de badges — specs
exactas en el audit del issue #247. Suma C4 del capture doc
(docs/specs/2026-07-02-pedro-live-review-capture.md): el PA detail
(PublicAttentionPanel) habla otro lenguaje visual — misma lengua de diseño que
el resto (tokens de ThemeContext, no colores propios). DESIGN.md es el canon.
Cada cambio: screenshot antes/después con preview tools para el eyeball de
Pedro. Vanilla CSS. NO tocar: backend, SignalStream.
```
