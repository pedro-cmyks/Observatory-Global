# Topic Readiness and Search Performance Audit

Fecha: 2026-05-19  
Rama: `v3-intel-layer`  
Alcance: Phase 0 de `docs/superpowers/plans/2026-05-19-topic-intelligence-and-source-visibility.md`, mas diagnostico inicial del buscador Atlas.

## 1. Resumen ejecutivo

Atlas ya tiene volumen suficiente para empezar Topic Intelligence, pero no esta listo para mover ranking de narrativas sin una fase `shadow`.

Hallazgos principales:

1. **GDELT debe pasar por Atlas Topic Intelligence**, igual que todas las demas fuentes. Sus `themes` se conservan como taxonomia de origen, pero la capa de producto debe leer `signal_topic_assignments`.
2. **Las fuentes nuevas estan entrando**, pero casi todas llegan con `themes=[]`. Eso confirma que Reddit, NewsData, MediaStack, RSS y ReliefWeb no alimentan fuerte los hilos narrativos actuales.
3. **El worker NLP no es la causa directa de la lentitud del buscador**. El buscador corre en el proceso API y hace SQL costoso sobre `signals_v2`.
4. **El worker actual de Fly, 2GB, sirve para benchmark y shadow compactos**, pero para Topic Intelligence en produccion conviene subir a 4GB si vamos a usar embeddings + zero-shot compacto.
5. **El buscador tiene queries que pueden tardar >20s o caer por `statement_timeout`**, especialmente consultas como `copper`, `gaza` o `conflicto colombia`.

## 2. Estado operacional observado

Fly:

| Proceso | Maquina | Perfil | Estado |
|---|---|---:|---|
| `app` | `d8d2e46fe07e78` | `shared-cpu-1x:1024MB` | started, health passing |
| `nlp_worker` | `0803426f142468` | `shared-cpu-2x:2048MB` | started |
| `nlp_worker` standby | `876d07c0201658` | `shared-cpu-2x:2048MB` | stopped |

Health snapshot:

```json
{
  "status": "healthy",
  "ingest_lag_minutes": 4.8,
  "rows_ingested_last_15m": 4068,
  "total_signals": 2220673,
  "nlp": {
    "unprocessed_24h": 162395,
    "unprocessed_total": 2061385,
    "oldest_unprocessed_at": "2026-05-03T21:09:39.912120+00:00",
    "lag_minutes": 22282,
    "last_run_at": "2026-05-19T08:32:08.543544+00:00",
    "last_run_duration_seconds": 123.8
  }
}
```

Interpretacion:

- Ingesta esta sana.
- NLP esta corriendo, pero el backlog sigue siendo grande.
- Topic Intelligence no debe correr inline en `app`; debe correr en worker, con modo `shadow`.

## 3. Source/topic readiness

Consulta ejecutada en produccion, ultimas 24h:

```sql
SELECT source_family, attribution_method,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE themes IS NULL OR cardinality(themes)=0) AS empty_themes,
       COUNT(*) FILTER (WHERE headline IS NULL OR length(trim(headline)) < 12) AS weak_headline,
       COUNT(*) FILTER (WHERE nlp_processed_at IS NOT NULL) AS nlp_processed,
       COUNT(*) FILTER (WHERE country_code = 'XX') AS xx_country,
       ROUND(AVG(COALESCE(geo_confidence,0))::numeric, 3) AS avg_geo_confidence
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY 1,2
ORDER BY total DESC;
```

Resultado:

| source_family | attribution_method | total | empty_themes | weak_headline | nlp_processed | XX | avg_geo_confidence |
|---|---|---:|---:|---:|---:|---:|---:|
| gdelt | gdelt_gkg_translated | 103,333 | 8,894 | 7,278 | 75 | 0 | 0.850 |
| gdelt | gdelt_gkg | 62,956 | 5,418 | 209 | 2,377 | 0 | 0.850 |
| independent | rss_feed | 1,152 | 1,152 | 1 | 40 | 0 | 0.600 |
| api | newsdata_api | 434 | 434 | 0 | 0 | 7 | 0.700 |
| api | mediastack_api | 336 | 336 | 0 | 0 | 0 | 0.650 |
| wire | rss_feed | 254 | 254 | 0 | 0 | 0 | 0.600 |
| state | rss_feed | 242 | 242 | 0 | 0 | 0 | 0.600 |
| social | reddit_public | 178 | 178 | 2 | 0 | 18 | 0.500 |

Interpretacion:

- GDELT domina volumen y tiene la mayoria de filas narrativamente elegibles por `themes`.
- Fuentes nuevas son topic-ready por texto: casi todas tienen headlines suficientemente largos.
- Fuentes nuevas no son narrative-ready por taxonomia: casi todas tienen `themes=[]`.
- Reddit tiene utilidad para social-led emergence, pero 10% aprox. cae en `XX`; no debe contar como corroboracion factual.
- NewsData necesita #158: `geo_confidence` plano de 0.7 no refleja calidad real de atribucion.

## 4. Language/source coverage

Ultimas 24h por idioma:

| source_family | attribution_method | source_lang | total | empty_themes | nlp_processed |
|---|---|---|---:|---:|---:|
| gdelt | gdelt_gkg_translated | xx | 103,333 | 8,894 | 75 |
| gdelt | gdelt_gkg | en | 62,956 | 5,418 | 2,377 |
| independent | rss_feed | en | 753 | 753 | 40 |
| independent | rss_feed | es | 399 | 399 | 0 |
| api | mediastack_api | es | 225 | 225 | 0 |
| state | rss_feed | ar | 208 | 208 | 0 |
| social | reddit_public | en | 178 | 178 | 0 |
| wire | rss_feed | en | 172 | 172 | 0 |
| api | mediastack_api | pt | 111 | 111 | 0 |
| api | newsdata_api | es | 107 | 107 | 0 |
| api | newsdata_api | ar | 71 | 71 | 0 |
| api | newsdata_api | fr | 61 | 61 | 0 |
| api | newsdata_api | hi | 51 | 51 | 0 |
| api | newsdata_api | sw | 34 | 34 | 0 |
| api | newsdata_api | vi/id/ur/bn/th/ms/am/fi | 88 | 88 | 0 |

Interpretacion:

- La diversificacion no inglesa ya existe en datos.
- El backlog todavia no ha procesado casi nada de API/social recientes.
- `source_lang='xx'` para GDELT translated complica evaluacion multilingue; Topic Intelligence debe tratarlo como idioma desconocido o usar deteccion ligera si hace falta.

## 5. Muestra disponible para benchmark

Filas con texto suficiente para benchmark de temas, ultimas 24h:

| source_family | attribution_method | sampleable |
|---|---|---:|
| gdelt | gdelt_gkg_translated | 93,829 |
| gdelt | gdelt_gkg | 62,086 |
| independent | rss_feed | 1,141 |
| api | newsdata_api | 428 |
| api | mediastack_api | 329 |
| wire | rss_feed | 254 |
| state | rss_feed | 239 |
| social | reddit_public | 168 |

Conclusion:

- Hay muestra suficiente para benchmark estratificado.
- El benchmark no debe usar `ORDER BY random() LIMIT 300` global, porque quedaria dominado por GDELT.
- Usar muestra estratificada max 50 por `source_family/attribution_method`.

SQL recomendado:

```sql
SELECT *
FROM (
  SELECT id, timestamp, country_code, source_family, attribution_method,
         source_lang, headline, themes,
         ROW_NUMBER() OVER (
           PARTITION BY source_family, attribution_method
           ORDER BY random()
         ) AS rn
  FROM signals_v2
  WHERE timestamp > NOW() - INTERVAL '24 hours'
    AND headline IS NOT NULL
    AND length(trim(headline)) >= 25
) s
WHERE rn <= 50
ORDER BY source_family, attribution_method, rn;
```

## 6. Search performance findings

Mediciones contra produccion:

| Query | Resultado |
|---|---:|
| `colombia` | 200 OK, 0.40s en cache/caliente |
| `copper` | timeout local a 20s |
| `gaza` | timeout local a 20s |
| `conflicto colombia` | timeout local a 20s en una corrida; log posterior muestra 200 OK tardio |

Log relevante:

```text
asyncpg.exceptions.QueryCanceledError: canceling statement due to statement timeout
GET /api/v2/search/unified?q=copper&hours=168 HTTP/1.1" 500 Internal Server Error
File "/app/app/routers/search.py", line 320, in unified_search
  db_result = await search(...)
File "/app/app/routers/search.py", line 41, in search
```

Diagnostico:

- El buscador no esta lento por el `nlp_worker` directamente.
- `/api/v2/search/unified` corre en el proceso `app`.
- El cuello principal esta en SQL:
  - `LOWER(array_to_string(themes, ' ')) LIKE ANY('%...%')`
  - `LOWER(array_to_string(persons, ' ')) LIKE ANY('%...%')`
  - `LOWER(headline) LIKE '%...%'`
  - `LOWER(article_title) LIKE '%...%'`
- Esas expresiones probablemente no usan bien los indexes GIN actuales sobre arrays.
- Unified search tambien ejecuta piezas de DB de forma secuencial.

Bug adicional:

- El frontend envia `country` en `/api/v2/search/unified`, pero el backend no acepta ese parametro.
- Por eso busquedas compuestas pueden perder scoping real.

## 7. Worker/model sizing

Estado actual:

- API: 1GB.
- NLP worker: 2GB.
- Worker separado no sirve HTTP, por lo tanto no mejora directamente search latency.

Recomendacion:

| Estrategia | Perfil Fly recomendado | Uso |
|---|---:|---|
| Lexicon-only | 512MB-1GB | barato, explicable, puede correr rapido |
| Lexicon + embeddings compactos | 2GB | benchmark/shadow si carga modelos secuencialmente |
| Embeddings + zero-shot compacto | 4GB | recomendado para produccion de Topic Intelligence |
| Heavy zero-shot / mDeBERTa grande | 4GB-8GB+ | solo worker experimental, no default |

Decision propuesta:

- Mantener 2GB durante benchmark.
- Subir a 4GB para shadow/produccion si activamos embeddings + zero-shot compacto juntos.
- No usar modelos grandes en el worker principal hasta medir.
- Mantener `NLP_INLINE_ENABLED=false` para proteger API.

## 8. Riesgos para normalizar GDELT

Normalizar GDELT es correcto, pero tiene riesgos:

- Por volumen, GDELT puede dominar `atlas_topics` si no hacemos muestreo/weighting.
- Si usamos `themes` de GDELT como label fuerte, heredamos su superficialidad.
- GDELT translated usa `source_lang='xx'`, lo que baja confianza de rutas multilingues.
- Weak headlines en GDELT translated pueden meter ruido.
- Migrar narrativas a `atlas_topics` demasiado pronto puede cambiar ranking antes de tener UI/Source Mix/correcciones.

Mitigacion:

- `signals_v2.themes` = provenance/source taxonomy.
- `signal_topic_assignments` = normalized product semantics.
- Shadow mode primero.
- Benchmark estratificado por source family.
- Promocion solo con thresholds por fuente/idioma.

## 9. Issues y acciones recomendadas

Ya existe:

- #154 source quality / NLP backlog audit
- #155 `signal_class`
- #160 Voice Mix
- #167 Atlas Topic Intelligence
- #168 Public Attention Threads

Crear nuevo issue:

- `perf(search): optimize unified search latency and country scoping`

Contenido:

- aceptar `country` en `/api/v2/search/unified`,
- agregar abort/stale request handling en `SearchBar.tsx`,
- instrumentar duraciones por segmento,
- agregar timeouts controlados,
- usar `theme_country_hourly_v2` o `themes && ARRAY[...]` para hits de taxonomia,
- agregar indices trigram expression para `LOWER(article_title)`, `LOWER(headline)`, `LOWER(source_name)`.

## 10. Siguiente orden de ejecucion

1. Cerrar #154 con este reporte y el benchmark sample.
2. Implementar #155 `signal_class`.
3. Crear migracion #167 `atlas_topics` + `signal_topic_assignments`.
4. Implementar lexicon pass primero.
5. Benchmark embeddings/zero-shot en 2GB.
6. Decidir upgrade a 4GB antes de shadow con embeddings + zero-shot.
7. Abrir/fijar issue de search performance como trabajo paralelo P1.

