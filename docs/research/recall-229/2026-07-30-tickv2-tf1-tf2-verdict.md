# Tick-v2 (lifecycle clock) — TF-1 PASS mecánico, TF-2 KILL por composición

**2026-07-30 · pase manual diurno (máquina libre), flag `ATLAS_LIFECYCLE_TICK_V2=on`,
un pase completo de `project_dynamic_topics` + verificación pre-registrada.
VEREDICTO: la aritmética del reloj es CORRECTA; el gate de composición mató el
flip — revivir un campo enfermo inunda el serving con identidades stale/blob.
Flag revertido a off + estados restaurados al baseline exacto. La lección de
diseño: la V2 debe revivir a CANDIDATE, no a ACTIVE.**

## TF-1 (mecánica del reloj) — PASS limpio

Baseline congelado pre-run: `ALW/logs/lifecycle-pre-20260730.csv` (6,649 topics
no-umbrella). Run summary: `n_snapshots_processed=1`, `lifecycle_tick_v2=true`,
`n_reentrant_groups=5` (los phantom re-entries manejados), written 143 inserted /
1,938 updated / 2,193 members.

| Clase | n |
|---|---|
| re-matched (since_seen→0) | 713 |
| envejeció exactamente +1 | 4 |
| sin cambio | 5,932 |
| topics nuevos | 143 |
| desaparecidos | 0 |
| **VIOLACIONES (Δ≥2 o negativo-no-reset)** | **0** |

Transiciones: retired→active 681 · candidate→active 338 · active→deprecated 4 ·
retired→candidate 3. Activos 1,001 → 2,016 (Δ+1015; el dry-run de hace días
predijo ~+672 — dirección correcta, magnitud mayor por el snapshot pendiente).
Puertas encendidas en vivo: CO sirvió 8 hilos ("School Shooting in Bogotá",
"Earthquakes in Colombia"), JP sirvió 6 ("Takaichi Approval Slump").

## TF-2 (composición de los revividos) — FAIL, y no cerca

Gate pre-registrado: muestra de 40 nuevos-activos, **≥90% historias reales o
KILL**. Muestreo aleatorio sobre los 1,019 no-activos-en-baseline que quedaron
activos; 6 recibos v1-compat evidence (sin cuarentena) por topic; juicio manual
label↔recibos.

| Categoría | n | % |
|---|---|---|
| REAL — label coincide con recibos coherentes | 15 | 37.5% |
| Cluster coherente, label stale/equivocado | 12 | 30.0% |
| Fusión/blob/bucket vago | 8 | 20.0% |
| Basura total (label sin relación alguna con el feed) | 2 | 5.0% |
| Sin recibos evidence | 2 | 5.0% |
| Thin/tangencial | 1 | 2.5% |

**Estricto 37.5% · lectura más caritativa (cluster coherente, ignorando label)
67.5% — ambos < 90%. El veredicto es robusto a la interpretación.**

Testigos: dt-5345 "NYC Flash Floods Threaten World Cup Final" → heladas de Nueva
Zelanda; dt-672 "Germany's Aid to Ukraine" → Reino Unido–Ucrania (Stone Cloak);
dt-1501 label letón ("Ugunsgrēks Ulmaņa gatvē") → lifestyle ucraniano de playas
en España; dt-533 "Detención de Delta 7" → mezcla de Guadalupe y Calvo con
cc=GP (Guadalupe, no Chihuahua — geo-miscode montado en identidad vieja).
Los buenos también existen y duelen: dt-6135 NEET paper-leak, dt-7787
Venezuela-CPI, dt-3384 Jordania intercepta misiles, dt-7998 RAF pellet probe,
más las puertas CO/JP completas.

## KILL ejecutado (sin mover arcos)

1. `ATLAS_LIFECYCLE_TICK_V2=off` en ALW `.env` (la allowlist del runner queda —
   inerte con el flag off).
2. **Revert quirúrgico de estados**: los 1,026 cambios de estado del pase
   restaurados al baseline (SQL por clase de transición; solo `state` — los 143
   topics nuevos y los resets de `since_seen` se quedan: son hechos de matching
   verdaderos bajo cualquier semántica). Verificado: activos exactamente
   **1,001** = baseline. Ledger reversible:
   `ALW/logs/tf2-revert-ledger-20260730.json`.
3. Fetch-mult M=2 quedó DESACOPLADO de este veredicto (su gate A0b es propio y
   ya está ADOPT) — se flipea aparte con atribución limpia.

## La lección de diseño (pre-registro de la V2)

El reloj no estaba roto — **la puerta de salida sí**. Tick-v2 revivió
`retired→active` DIRECTO (681 filas): cero re-vetting entre "volvió a matchear
un snapshot" y "sirve en portada". El campo carga dos enfermedades conocidas
(labels congelados en creación + blobs de dispersión argmax), así que revivir
en masa = servirlas en masa.

**TF-3 (pre-registrado aquí, antes de construir):** tick-v2b = la misma
aritmética de un-tick-por-pase, pero la revival path escribe
`retired→candidate`. La promoción normal (persist≥2, volume_min, junk-gate) +
el court/relabel/overmerge re-vetan ANTES de servir.
Gates: (a) TF-1 idéntico (invariante de deltas); (b) ninguna puerta se
enciende sin pasar promoción; (c) composición TF-2 medida SOLO sobre los
promovidos, mismo bar ≥90% o KILL; (d) el tránsito candidate→active de
revividos debe verse en ≤3 noches para las historias con volumen real (si nada
promueve, la palanca no rinde y se reporta honesto.)

Nota de capacidad: el court acaba de recuperar throughput (backoff de withholds
2026-07-30, `6d6d906f`) — ~1,700 juicios/día alcanzan para re-vetar una ola de
revividos en ~24h.
