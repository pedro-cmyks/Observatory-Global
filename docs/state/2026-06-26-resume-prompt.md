# Resume prompt — paste this to start the next session

Continuamos Atlas (branch `v3-intel-layer`). Estado:

**Dónde estamos:** atacando el master spec
`docs/specs/2026-06-26-atlas-master-consolidation.md` en el orden §3. Hecho:
- 3 review-specs cerrados (l2-l3-deep-review, surfaces-editorial, mobile-multilevel).
- **T4.1** embed-service watchdog (#240), **T4.2** embed throughput 10x (#241),
  **T5.1** telemetría time-to-value (mig 056), **T5.2** wedge = *narrative analyst*
  (arriba de CLAUDE.md), **T1.5** gate-recall por idioma (finding: el sesgo está
  upstream en la asignación English-centric + el bucket `xx`, no en el gate).

**Lo último (sin verificar en tu teléfono):** hardening del mapa móvil en blanco
(`c883988`, ya en Vercel). 3 fixes: (1) lazy-mount — el mapa solo monta cuando su
contenedor está dimensionado (no en 0×0 oculto en la tab Stream); (2) recovery de
`webglcontextlost` → remonta (caso iOS Safari mata el contexto WebGL por presión
de memoria — la causa más probable del blanco recurrente); (3) watchdog gateado.
Desktop sin regresión (verificado). **El blanco en el dev-preview es un quirk
solo-de-dev** (todos los tiles de carto cargan 200, WebGL sano, renderiza bien en
Vercel) — no se puede reproducir tu blanco-de-teléfono en local. **PRIMER PASO:
que Pedro confirme en su teléfono si el mapa ya carga.** Si sigue en blanco,
siguiente hipótesis = service-worker PWA sirviendo bundle viejo (probar "borrar
datos del sitio" / reinstalar PWA) o CDN carto bloqueado en su red móvil.

**Siguiente trabajo (master spec §3, item 4):** **T2.2 (C3 — Public Attention
por-thread)** + **T3.1 (A3 — scope strips)**.
- T2.2: bloque "Public Attention for this thread" (trends/wiki/forum scoped al
  thread, con el forum-vs-media sentiment ya servido). Archivos: `ThemeDetail` +
  `useFocusRelation`.
- T3.1: strip persistente `"Scoped to <X>"` con `✕` en NarrativeThreads + header
  del stream, para que los re-scopes silenciosos sean legibles.
Después: item 5 = T1.1 who-says-what + T1.2 Phase-4 evidence quality (Paper 1).

**Comandos:** deploy backend `./scripts/deploy-fly-api.sh`; frontend = push a
`v3-intel-layer` (Vercel auto). Build front: `cd frontend-v2 && tsc -b && npm run
build`. Preview 375px para verificar móvil. Smoke research:
`curl -s -X POST https://atlas-api-pedro.fly.dev/api/v2/research/plan -H 'Content-Type: application/json' -d '{"query":"Iran climate water","hours":168}'`.

**Guardrails:** no presentar GDELT themes crudos como modelo de tópicos; foros =
lane de discusión/atención, nunca evidencia verificada por defecto; verificar
antes de afirmar (panel/funcionalidad) — lección ya en CLAUDE.md.
