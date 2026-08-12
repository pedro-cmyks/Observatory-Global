# La puerta y las carpetas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Spec: `docs/superpowers/specs/2026-08-12-puerta-y-carpetas-design.md` (aprobado por Pedro 2026-08-12).

**Goal:** Rename Stories/Historias + modelo carpeta legible (breadcrumb + una anatomía) + Brief como diario de la cobertura, con los 5 gates pre-registrados del spec.

**Secuencia dura:** P1 solo (toca copy en decenas de archivos — nada en paralelo sobre frontend) → P2 (breadcrumb + anatomía) → P3 (la lectura; su medición M0 puede correr en paralelo con P2 porque es backend read-only).

---

## P1 · Rename Stories/Historias (1 agente, arranca YA)

**Regla**: SOLO copy visible al usuario. Contratos (thread_id, endpoints, tablas, tipos TS internos, nombres de archivo/componente) INTACTOS. "Story/Historia" = hilo dinámico servido; "Theme/Tema" = categoría R3.

- [ ] T1.1: inventario grep de todo "Narrative Thread(s)"/"thread" USER-VISIBLE en frontend-v2/src (headers de panel, tooltips, empty states, aria-labels, copy del Brief, móvil, onboarding/tour, exports markdown) — tabla archivo→string→reemplazo. Los que son contrato/código se listan como NO-TOCAR.
- [ ] T1.2: aplicar el rename con el idioma de página: en="Stories", es="Historias" donde la superficie ya es bilingüe (pageLanguage existe); superficies mono-idioma usan "Stories".
- [ ] T1.3: FocusIndicator/typeLabel ya distingue Story/Theme — completar donde falte (mapa, universe, dock, exports).
- [ ] T1.4: vitest con snapshots de los strings clave + build + browser-verify (panel L2, Brief, móvil 375px). Commit pathspec frontend-v2/src.

## P2 · Modelo carpeta (2 agentes secuenciales tras P1)

- [ ] T2.1 **Breadcrumb de ámbito** — `lib/scopePath.ts` puro: deriva `Mundo ▸ [País] ▸ [Historia] ▸ [señal]` del estado de FocusContext + thread/signal abiertos (el estado YA existe — esto es representación, no estado nuevo). Componente `ScopeBreadcrumb` (desktop: junto al command bar; móvil: header del Lens). Cada migaja navega a ese nivel (reusa los handlers existentes: clear focus, open country, open thread). El breadcrumb REEMPLAZA el focus-clear chip de 18px (se retira; el residual R4 muere aquí). TDD puro + browser NAV: entrar señal→historia→país→Mundo por migajas, 6/6 sin pérdida (G-CARPETA parte 1).
- [ ] T2.2 **Anatomía consistente** — auditoría de qué responde cada carpeta hoy (país=CountryBrief, historia=ThemeDetail, persona=EntityPanel) contra la gramática del Lens móvil (qué es · qué dice · dónde vive · qué conecta · quién atiende); ordenar/renombrar section-headers para que las cinco preguntas aparezcan EN ESE ORDEN donde ya existen; huecos se marcan honestos ("no medido para este ámbito"), NO se construyen lanes nuevos. Es un pase de orden y copy, no de features.

## P3 · Diario de la cobertura

- [ ] T3.0 **M0 medición (paralelo con P2, backend read-only)**: (a) histograma de share-de-familia-sindicada en los leads de las últimas ~30 ediciones → fija X del veto jalapeño; (b) distribución de divergencia atención/self-voice por día (¿cuántos días tienen un VACÍO sobre la barra? — fija la barra de EL VACÍO); (c) el testigo jalapeño real extraído como fixture. Artefacto en docs/research/brief-daily/.
- [ ] T3.1 **Selección editorial — ENMENDADO por M0** (backend): el veto va en el
  CAMINO VIVO (rank_threads), no en el sello — las 25 ediciones están
  `degraded` y el Brief sirve hilos vivos; el Pareto del sello ya botaba al
  testigo. Trabajo real: (i) reparar `headline_diversity` (el _norm_headline
  no ve el masthead con en-dash → el jalapeño puntuó 1.000); (ii) fix
  `corroboration._tokens` Latin-only (fabricó familias desde "2026" en
  cirílico) + clusterer greedy orden-sensible (0.538 vs 0.731 mismos
  miembros); (iii) veto = umbral sobre la señal REPARADA (M0: familia
  Jaccard@0.5 ≥0.70 de membresía raw, min n=8 — re-medir tras (i-ii) antes
  de congelar); (iv) DIAGNOSTICAR por qué 25/25 ediciones sellan degraded —
  hallazgo de M0, condición de fondo sin nombre. Fixtures: jalapeño
  dt-11877 (nunca lidera) + dt-1619 misil NK (debe poder liderar).
- [ ] T3.2 **EL VACÍO + LO QUE SUBE — ENMENDADO por M0** (backend, tras
  T3.1): LO QUE SUBE con barra M0 (surprise ≥2.5 ∧ velocity>0 ∧ vol≥20,
  15/15 días de soporte). EL VACÍO: irretro-medible (retención 7d + archivo
  sin voz) → LOGUEAR el candidato diario desde el día 1 (tabla/ledger) y la
  barra (mult ≥3.0 ∧ self-voice ≤0.20 ∧ vol≥20 ∧ known_origin≥50) se
  re-calibra con 2 semanas de log; mientras, sirve con la barra provisional
  + confianza declarada. FIX de honestidad: `local_voice_ratio=0.5` es
  sentinel de known_origin<50 disfrazado de ratio (5/10 del top hoy) —
  servirlo como null+razón, jamás como 0.5. Vacío honesto (G-VACÍO-HONESTO).
- [ ] T3.3 **La lectura** (frontend): BriefNewspaper gana la estructura LEAD(standfirst con voces tejidas — la tela del voice-bar absorbido)/VACÍO/SUBE/DESK; cada item deep-linkea a su carpeta con breadcrumb puesto (P2). Móvil incluido.
- [ ] T3.4 **Gate final**: G-LECTURA — sonda ciega NUEVA sobre /brief (mismo protocolo del 2026-08-12, agente sin contexto): debe (a) describirlo como distinto de una portada de wire sin preguntarle, (b) nombrar un item por el que volvería. + NAV-LOSS deep-links + suites + deploy.

**Regla del arco**: pathspec-only, TDD, cada parte gate-eada antes de la siguiente; los 5 gates del spec se corren y se registran en el artefacto de cierre.
