# M0 — las mediciones del archivo-al-frente (los números para D1)

**2026-08-24 (noche). Mandato**: plan `2026-08-24-archivo-al-frente-plan.md`
§2, dirección de Pedro "la mayor cantidad de datos posible". Cuatro
mediciones + dos hallazgos que el plan no sabía que necesitaba.

## M0.1 · Archivo-en-Postgres: sizing y carga (medido, no estimado)

Clúster desechable PG 18.3 en `/Volumes/Ext/Atlas/m0-pg-test` (port 55433,
apagado tras medir; la data queda para inspección de D1, 2.0GB).

| medida | 14 días reales (ago 3-16) | extrapolado archivo completo (~113d) |
|---|---|---|
| filas | 1,692,111 (0 ids duplicados entre re-exports) | ~13-14M |
| heap + índices | 976MB + 45MB (ts · cc,ts · family) | **~8-9GB** — cabe ~200× en Ext (1.7TB libres) |
| tiempo de carga | 84s (29 shards gz → COPY) | **~12 min** bootstrap · ~6s/día incremental |

## M0.1b · Queries de superficie: frío vs caliente — LA arquitectura decidida por números

| query | frío (primer toque) | caliente |
|---|---|---|
| conteo de un día | 7.1s | **29ms** |
| serie 14d de un país (cc,ts idx) | 25.2s | **23ms** |
| top-20 fuentes de la ventana | 51.1s | — |
| familia×semana | 33.0s | — |
| needle granular (`incendi` en CO — la clase del probe de Pedro) | 17.5s | **46ms** |

El disco externo frío castiga full-scans (y a 113 días sería ~8× peor, con
working set que NO cabe en los 8GB del M1). **Conclusión mecánica: el
archivo-Postgres local es para CÓMPUTO/research/agregación — no para servir
requests interactivos. La nube sirve agregados precomputados.** Exactamente
la opción (a)+(b) del plan, ahora con números.

## M0.3 · El patrón artefacto es casi gratis

- Agregado día×país×familia (con tono) sobre 14 días: **28s de build,
  8,068 filas, 520KB.** Archivo completo ≈ 65K filas ≈ ~4MB, build ~4 min
  una vez, ~2s/día incremental.
- Query de superficie contra el agregado (serie completa de un país):
  **2ms.** Publicable como tabla chica en la nube o artefacto estático.

## M0.2 · Censo deep-history (40 topics vivos contra prod) — el hallazgo grande

100% de servidos y 100% de aleatorios tienen deep-history no-vacío
(mediana 57-58 días de serie, latencia ~1s) — **pero el 100% es
parcialmente artefacto y la profundidad es una ilusión de ventana**:

1. **`archive_story_units` está CONGELADO en 2026-07-03** — la
   clusterización semanal Stage-B del archivo dejó de correr hace 7.5
   semanas. Ninguna historia de agosto tiene historia de SU era; el techo
   de 61 días es el horizonte muerto, no cobertura.
2. **El matching (label-embedding vs centroides, tau=0.32) no
   discrimina**: mediana ~176 units matcheadas por topic, incluidos
   sinsentidos ("Pregnant Woman Balcony Death" → 206 units). El propio
   código lo declara: al piso permisivo el conteo trackea volumen total
   del archivo, no presencia del topic; la señal real es `peak_sim`.

## M0.4 · Los letreros que mienten por omisión

- Console: pill `FROM 5 AUG` con tooltip **"Signal archive starts {fecha}"**
  (`App.tsx:1962`) — falso: eso es el piso de retención CALIENTE que avanza
  a diario; el archivo real empieza el 3 de mayo. Debe decir la verdad
  doble: "hot 7d · archive since May 3".
- Honestos y bien: los "FROM THE ARCHIVE" de DayEvidencePanel/deep-history,
  el "active since {fecha}" de ThemeDetail, la biografía de 9 semanas.

## Lo que M0 le entrega a D1 (decisión de Pedro)

**Recomendación con números**: (a)+(b) del plan — archivo-Postgres
PERMANENTE en Ext (8-9GB, bootstrap 12 min, incremental 6s/día; loader = el
script de esta medición generalizado) como sustrato de research y de los
agregadores nocturnos + la nube sirve los agregados (KBs, 2ms). Y DOS
reparaciones upstream que suben al frente del plan porque sin ellas F1-F3
sirven historia muerta:

- **R1 — revivir el Stage-B semanal** (units del archivo congeladas
  03-jul): el pipeline existe (`archive_story_units`, mig 069); hay que
  averiguar por qué dejó de correr y re-armarlo con watchdog.
- **R2 — especificidad del match de deep-history**: umbral sobre
  `peak_sim` (no conteo a tau 0.32) antes de hacer prominente el botón —
  prominente + no-discriminante = ruido con uniforme de historia.

Costo total de M0: ~3 min de carga + ~4 min de queries + 40 requests a
prod + $0. Clúster apagado; `/Volumes/Ext/Atlas/m0-pg-test` (2GB) queda
para D1 — borrar con `rm -rf` cuando se decida.
