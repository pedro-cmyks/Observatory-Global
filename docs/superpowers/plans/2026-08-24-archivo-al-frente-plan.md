# Plan de acción — archivo-al-frente (implementa la decisión abierta §6 del spec de campaña)

**2026-08-24. Origen**: spec `2026-08-24-campana-lanzamiento-spec.md` §6 +
la pregunta directa de Pedro: "¿por qué solo desde el 17 de agosto? usemos
toda la data… ¿la base puede vivir físicamente en mi computador?". Regla:
medir → decidir → construir. Nada de este plan toca serving hasta D1.

---

## 0 · La respuesta corta a la pregunta de arquitectura

**Mover la base ENTERA al M1 para SERVIR: no.** El producto sirve 24/7
desde Fly/Vercel; el M1 es una laptop que duerme, vive tras NAT, y su
historial (kernel panic 07-03, swap-death 08-04, tormenta iCloud 08-19)
es la definición de un origen no disponible. Cada request pagaría además
la latencia Fly↔casa.

**PERO la mitad buena de la idea ya es la arquitectura de Atlas y hay que
completarla**: la historia COMPLETA ya vive físicamente en el computador
de Pedro (`/Volumes/Ext/Atlas/Archive`: 2.9GB comprimido, 238 corridas,
desde mayo; 1.7TB libres) y la nube se queda CHIQUITA a propósito (hot 7d;
la auditoría de hoy re-demostró por qué: 4 noches sin poda → 13GB →
INSERTs 3× lentos → ingesta al 30%). El patrón que ya funciona es
**computar local → publicar artefactos → la nube sirve lecturas puras**
(universe_field_artifacts, daily edition, biography stitch). Este plan lo
extiende a la historia profunda.

Reparto final: **nube = el día y la semana (serving). M1+Ext = la memoria
completa (cómputo, investigación, agregados que suben como artefactos).**

## 1 · Lo que YA existe (no re-construir)

- Archivo completo `jsonl.gz` por día/particiones + manifests verificados.
- `historical_evidence_samples` (recibos por país-día, 60K muestras),
  `archive_story_units` (6,473 unidades Stage-B), `/deep-history` (serie
  61 días por historia), replay 30d (`/map/replay`), biography stitch
  (visto HOY en prod: "NARRATIVE BIOGRAPHY · 9 WEEKS" en dt-16556, y el
  botón "⧗ Load full history (back to May 3)" ya renderiza en el detalle).
- Embeddings de archivo: shards OpenAI durables en Ext (6.9M vectores).

El problema NO es que falte sustrato: es que está **sub-servido** — el
lector promedio nunca ve nada anterior a la ventana caliente.

## 2 · M0 — mediciones (1 sesión, antes de cualquier decisión)

1. **Sizing real del archivo-en-Postgres**: cargar 2 semanas de shards a
   un Postgres local en Ext → GB/semana con índices, tiempo de carga,
   y tiempo de las 4 queries que las superficies piden (serie por
   identidad, día-país, top-fuentes por historia-mes, conteo por
   categoría-semana). Proyección: 2.9GB gz ≈ 10-15GB Postgres sin
   vectores — trivial para Ext.
2. **Censo de superficie**: ¿qué % de historias servidas hoy tienen
   deep-history no-vacío? ¿cuántos días promedio? (read-only, el endpoint
   existe).
3. **Latencia del patrón artefacto**: cuánto pesa/tarda pre-computar la
   serie completa por historia activa (~4K historias × 113 días) como
   artefacto nocturno.
4. **El gap del 17-de-agosto**: qué superficies muestran "FROM <hot-min>"
   como si fuera el inicio del universo (header del console, vitals) —
   inventario de los letreros que deben decir "hot desde X · archivo desde
   May 3".

## 3 · D1 — la decisión (Pedro, con los números de M0)

| opción | qué es | veredicto preliminar |
|---|---|---|
| (a) artefactos precomputados | nightly local calcula series/agregados históricos → sube artefactos → nube sirve read-only | **candidata default** — extiende el patrón probado, cero riesgo de serving |
| (b) archive-Postgres local | (a) + un Postgres permanente en Ext con TODO el archivo, para research/M1/agregadores (reemplaza el re-parseo de gz) | probable SÍ además de (a) — es infra de cómputo, no de serving |
| (c) servir historia on-demand desde la nube gorda | subir retención hot / segunda DB cloud con todo | NO por defecto — re-compra el incidente de hoy o duplica costo cloud |
| (d) servir desde el M1 | la nube consulta al laptop | **muerta** (disponibilidad/latencia, §0) |

## 4 · Fases de construcción (post-D1, en orden)

- **F1 — la historia se presenta completa**: "active since Jun 14 ·
  archivo desde May 3" en el detalle; deep-history carga sola (no botón
  enterrado) cuando la historia tiene pasado; el header del console dice
  la verdad completa ("hot 7d · memoria desde May 3").
- **F2 — replay/timelines largos**: scrubbers alimentados del agregado
  histórico (artefacto), no solo 30d.
- **F3 — recibos de archivo**: tarjetas viejas linkean day-evidence del
  archivo (endpoint existe), con su tier "FROM THE ARCHIVE".
- **F4 — (si D1=b) archive-Postgres en Ext**: loader idempotente desde
  shards + los agregadores nocturnos leen de ahí (más rápido que
  re-parsear gz); read-only para research y para el programa M1.

## 5 · Evidencia del día que motiva esto (probe 2026-08-24)

Incendios Colombia (Tolima calamidad pública >20K ha, Nariño 4 municipios):
**52 señales crudas/7d, 36 con membresía — y CERO historia colombiana
propia**: 19 en categoría genérica, 11 en la fusión "Las Hurdes and
Tolima", 18 en historias de ESPAÑA, 3 en "Earthquakes in Mexico", 1 en
"Natalia Villalba". La memoria larga hace estas fusiones MÁS visibles y
más corregibles (la biografía de 9 semanas de dt-16556 ya muestra la
costura ES↔CO). El caso queda como testigo vivo del programa M1/Z1 —
la muestra ciega fresca del gate debería incluir esta clase.

## 6 · Orden y dependencias

M0 corre cuando Pedro quiera (1 sesión, read-only + un Postgres local de
prueba). D1 = Pedro con números en mano. F1-F3 son superficie (no tocan
motor; pueden ir tras el M1-sombra como votó el spec §6, o antes si Pedro
prioriza). F4 solo si D1=b.
