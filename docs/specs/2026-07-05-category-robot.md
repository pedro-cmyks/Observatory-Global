# Category robot — spec (2026-07-05, status: AGREED, build finishes Day-3+1)

Decisiones de Pedro (noche 07-04/05), consolidadas para ejecutar mañana sin
re-discutir.

## 1. El modelo (cerrado)

- **Producto = DOS columnas, sin cambios**: columna izquierda = narrative
  threads (filas = historias/eventos); columna derecha = atlas topic (el tag
  de categoría en cada fila). El screenshot anotado de Pedro (07-04 23:03)
  es el contrato visual.
- **Todo clasificador es DINÁMICO**: las categorías no son un número fijo ni
  se actualizan a mano (la edición manual del 29-jun fue intervención, no
  proceso). Los eventos canónicos también nacen solos.
- **El robot** (frase de Pedro): "va por encima de todos los temas siempre y
  se pregunta ¿esto se puede agrupar?" — estructura-primero (agrupa por
  atracción de centroides), nombra el grupo UNA vez después, recursivo, y
  corre sobre TODA la historia (archivo incluido), nunca solo el hot.

## 2. Las tres salidas del robot → dónde caen en las dos columnas

| Salida | Criterio (medido, ya implementado) | Destino |
|---|---|---|
| **Categoría** | grupo de labels DIVERSOS que comparten tema; maxSim vs anchors < bar (p90 inter-anchor) | `atlas_topics` origin='auto' → **tag columna derecha** |
| **Evento canónico** | token de contenido dominante ≥60% de labels ("venezuela"+"earthquake") | umbrella PERSISTENTE: `dynamic_topics` is_umbrella=true + id estable (schema mig 058) → **UNA fila padre en columna izquierda**, sub-historias en el drill-down |
| **Misma-historia** | intra-grupo sim mediana ≥0.80 (labels casi idénticos ×N) | work-list de FUSIÓN de identidades — no es UI; limpia la columna izquierda |

Ejemplo canónico: "Venezuela Earthquake" (25 identidades hoy) → 1 fila padre
"Venezuela Earthquake" · tag "Flood/Landslide Disaster" · click = sus
historias. Ni categoría nueva (nivel equivocado) ni 25 filas hermanas (ruido).

## 3. Estado al cierre de la noche

- `archive_embed_pipeline.py` CORRIENDO (nohup): archivo completo → OpenAI
  fp16 shards en /Volumes/Ext/Atlas/Embeddings. 544K vectores a las 00:50.
- `robot_categories_v1.py` construido + corrido sobre las 1,406 identidades
  (todos los estados): corte medido 0.35 (silhouette), guards nivel-evento y
  misma-historia activos. Primera corrida: 0 categorías nuevas (las 30 seeds
  cubren may31-jul5); 39 eventos; 17 casos de fusión. Reporte:
  `docs/research/taxonomy-revision/robot-v1-2026-07-05.md`.
- Growth loop v0 (nombre-primero) armado en el cron como puente.

## 4. Mañana (orden de ejecución)

1. Verificar pipeline terminado (manifest 772/772).
2. **Stage B** `archive_story_units.py`: shards → clustering semanal →
   unidades {label DeepSeek, centroid, span, n} jsonl.
3. **Robot sobre TODO**: identidades + unidades era-mayo
   (`--units-jsonl`). Ahí deben aparecer las primeras categorías nuevas.
4. **Salida evento → umbrella persistente**: extender el robot para
   escribir los grupos evento como dynamic_topics is_umbrella=true con
   parent_id de sus miembros (hoy solo los reporta).
5. **Salida fusión**: aplicar la work-list de misma-historia (merge de
   identidades duplicadas — absorb() ya existe en project_dynamic_topics).
6. **Eyeball de Pedro al reporte completo** → armar `--write` en el cron
   nocturno (Step junto al growth loop; cap 2 categorías/noche; eventos sin
   cap duro pero con ledger; seeds intocables; kill-switch).

## 5. Guardas permanentes

- Umbrales medidos, nunca adivinados (corte por silhouette; bar de solape
  p90 inter-anchor; re-medir cuando entren unidades del archivo).
- Seeds (candidate-v2) nunca auto-modificadas ni borradas.
- Ledger de todo insert/fusión (`auto-growth-ledger.md` + reportes fechados).
- Retiro por lifecycle: categoría/evento que deja de atraer miembros se
  retira solo — el corpus respira en ambas direcciones.
