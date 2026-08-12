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
- [ ] T3.1 **Selección editorial** (backend): score de edición `dominancia × diversidad × movimiento` + veto jalapeño (X de M0) + junk-damp duro en el lead — en select_daily_edition / el paso de sello. G-JALAPEÑO test-frozen. El sello sigue autónomo (G-SELLO: cero deps nuevas).
- [ ] T3.2 **EL VACÍO + LO QUE SUBE** (backend): dos secciones nuevas del package selladas por template sobre campos medidos (divergencia del día + top aceleración Kalman); vacío honesto bajo la barra (G-VACÍO-HONESTO). Cero LLM nuevo.
- [ ] T3.3 **La lectura** (frontend): BriefNewspaper gana la estructura LEAD(standfirst con voces tejidas — la tela del voice-bar absorbido)/VACÍO/SUBE/DESK; cada item deep-linkea a su carpeta con breadcrumb puesto (P2). Móvil incluido.
- [ ] T3.4 **Gate final**: G-LECTURA — sonda ciega NUEVA sobre /brief (mismo protocolo del 2026-08-12, agente sin contexto): debe (a) describirlo como distinto de una portada de wire sin preguntarle, (b) nombrar un item por el que volvería. + NAV-LOSS deep-links + suites + deploy.

**Regla del arco**: pathspec-only, TDD, cada parte gate-eada antes de la siguiente; los 5 gates del spec se corren y se registran en el artefacto de cierre.
