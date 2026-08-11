# Roadmap al release público — 2026-08-11

**Supersede `2026-07-09-resume-roadmap.md` (v2.1).** Dos meses de evolución
sin reflejar: este documento fija el estado REAL post-council-R4 y el camino
corto al release. Regla de lectura: cada línea o está VIVA en prod, o tiene
dueño+trigger, o es decisión de Pedro. Nada de "veremos".

## 1 · Dónde estamos (verificado, no narrado)

**Motor / lifecycle** — el arco del reloj completo y VIVO: v2b
(revival→candidate + court-gated promotion) · country-clock · tail-reserve
(163 países / 0 diferidos con presupuesto weekday) · blob-veto (mig 095) ·
5 clases de junk (`active AND is_junk = 0` sostenido) · post-revival receipts
+ revival-cap · recibos durables (mig 097, archived serving). Composición de
promociones frescas: identidades nuevas **83.3%** / stock viejo 65.4% — la
deuda es de stock, con relabel-en-repromoción como siguiente palanca medida
(baseline 65.4%, 153 testigos).

**Identidad** — 9 gates pre-registrados, 9 veredictos honrados. El landing
principle probado 4-de-4; el arco de labels CERRADO con la circularidad
medida. Despertador: **condenación ≤15%** (serie 38.7→28.3→21.7→33.3 — la
reversión de run-3 tiene mecanismo: relabel ahogado por su propio cap
mientras entran 602 nacimientos/7d) → re-run mecánico gates 8-9 → NAV-LOSS
→ `STORY_LENS_AUTO=on`. Cadencia 3 noches, ledger vivo.

**Honestidad (post-R4, hoy)** — los 2 P0 muertos el día del filing: N17
(court avalando mentira geográfica — conjunct + slot guard, testigo excluido
EN VIVO de la puerta CO) y N18 (state-media sellado mainstream — lista en el
clasificador backend, 3ª vez filed, última). N14/N28/N25/N37/N29 también
muertos. **El candidato ya no miente en ninguna superficie prominente.**

**Producto** — móvil phone-native (arco #236 en curso, chip de Pedro) + el
órgano intel restaurado + idioma (selector + Translate-all + citas). Gold:
answered 21-29% banda, identidad-persistencia ES un estado, juez-varianza
medida ±1 nivel. Wedge (dossier): "casi pasa el test de Frank" (NIVELES).

## 2 · La definición de release (lo que falta, TODO enumerado)

### 2a · Confiabilidad — ✅ CERRADO 2026-08-11 (Tren A, 4 agentes, mismo día)
1. ~~**N26** puerta país fría 503~~ → warm-build mig 098: 66 puertas (top-50
   volumen + 16 por anomalía vía country_heat_v2), CO/JP/US fríos 503→1.3-2.2s,
   orden de verdad artefacto-fresco→vivo→viejo-ETIQUETADO, slot-guard
   obligatorio en el artefacto, "Assembled Nh ago" (`99113658`+`5b685854`).
2. ~~**N19** "24h" sobre lifetime~~ → el hallazgo reencuadró el bug: la
   ventana real era 7d en TODAS partes (snapshot_window_h=168). Contrato:
   `total` lifetime nombrado + `currentTotal`/`countWindowHours` medidos,
   fila↔detalle acuerdan por construcción; 3ª superficie (threads/{id})
   cazada de paso (`d822ae17`). Residual → chip timeout-as-zero en themes.
3. ~~**Lanes colgados**~~ → causa raíz: /focus con la ortografía vieja del
   predicado (mig 090 indexó otra) = seq scan. Re-spelled + deadline desde
   la entrada del request (el acquire cuenta); trump 503@38.7s→200@1-8s;
   frontend loading→slow→settled, TODOS los callers /focus acotados
   (`c630e12d`..`eb1b8091`).
4. ~~**N23** timeline fabrica ausencia~~ → `measured_zero` (con cobertura
   que licencia el claim) ≠ `lane_starved` (canal a `unavailable`) ≠
   `invalid_ref` (400); umbral de hambruna 14× bajo el piso medido
   (`1770c961`+`9e7d1277`).
Prod: Fly v502 + Vercel (push v3-intel-layer eb1b8091). 2,833 backend +
1,310 vitest verdes en el gate de integración.

### 2b · Precisión del corroborate (el "file no" del R3, ahora nombrado)
Independencia medible: ownership (tiers en citations — N18 backend ya da la
base) + paraphrase (el caso Haaretz×3) + ventana temporal (recibo de 6
semanas avalando veredicto de hoy). Es UN spec de corroborate-v2.

### 2c · R4 P1/P2 restantes (filed, con dueño natural)
Sub-historias del lens (4 'Thailand School Shooting' = dedup de identidad —
cae con el programa de landing) · relación taxonomy monotype · biografía
narrativa ilegible a 375px · export MD renumeración de citas (N38) ·
SOURCE HEALTH con id crudo · focus-clear 18px.

### 2d · Programas (post-release o paralelos, gateados)
#236 móvil (chip corriendo) · #238 subject-geo (el conjunct fue el 1er
bocado) · #221 maturity contract (diseño) · #237 community (traffic-gated) ·
landing→lens (reloj de condenación) · relabel-de-stock (baseline 65.4%).

### 2e · Decisiones de Pedro (3, todas de registro)
#262 OAuth Google · #180 ReliefWeb appname · #46 ACLED (registrar o retirar
de UI). Ninguna bloquea release técnico; #262 sí bloquea cuentas-para-todos.

## 3 · Los relojes (corren solos)
Condenación cada 3 noches (run-3 HOY 08-11: 33.3%; próx. ~08-14) ·
re-censo cohorte fresca (leones activos) · sello nocturno con N18+conjunct ·
gold día-7 (persistencia-como-estado, 3er par).

## 4 · Criterio honesto de "release al público"
El review del 07-18 fijó: readiness ≥70 + reliability ≥70 + semanas limpias.
Hoy la brecha es §2a (confiabilidad) + §2b (precisión corroborate) — ambas
acotadas. La honestidad — el eje del producto — ya está: **medida, con
council, y sin superficies que mientan.** Cuando §2a cierre: beta pública
con el Brief como puerta (la PWA ya instala), console/workbench detrás.
