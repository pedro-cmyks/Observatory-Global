# TF-3b Gate (c) — CENSO completo de los promovidos-vetados: FAIL con dirección clara

**2026-08-03 · Censo (no muestra) de los 244 topics revividos que el court
certificó `entailed` y promovieron durante el fin de semana. Doble juez
independiente por topic + tiebreaker (acuerdo inter-juez **98.4%**), control de
sobre-bloqueo (45 failed), probe de serving (12), crítico de completitud, y el
check de atribución decay-vs-gate que el crítico exigió. 51 agentes, 0 errores.**

## Veredicto

| Métrica | Valor | Barra |
|---|---|---|
| **strict-real (label correcto sobre historia coherente)** | **172/244 = 70.5%** | ≥90% → **FAIL** |
| label_mismatch (cluster coherente, label equivocado) | 29 = 11.9% | |
| blob (fusión / bucket genérico sobre contenido diverso) | 28 = 11.5% | |
| junk (PR-wire spam / no-noticia certificada) | 15 = 6.1% | |
| acuerdo inter-juez (confiabilidad de la medición) | 98.4% | |
| sobre-bloqueo (failed que eran reales — FP del court) | 5/45 = 11.1% | |
| decay post-certificación entre los 72 fails | **0/72** | |

**La atribución es inequívoca: el déficit es la PRECISIÓN DEL CERTIFICADO
(court `entailed` ≈ 70% preciso como pase de serving), no decadencia
post-promoción** (0 de 72 fails tienen recibos mayormente posteriores al
veredicto).

## Lectura honesta — el gate mejora MUCHO y aún no basta

- Sin gate (TF-2, revival directo): **37.5% real** servido.
- Con gate (c): **70.5% real** servido = **+33pp** — el gate FUNCIONA como
  filtro y NO se revierte (revertirlo regresa la composición).
- Pero la barra pre-registrada era 90%: el certificado `entailed` deja pasar
  tres clases medidas, cada una con palanca conocida:
  1. **Blobs certificados (28)**: un label genérico ("NDLEA Drug Seizures")
     ENTAILA honestamente un bucket diverso — la ceguera conocida del court.
     El barredor de fusiones invisible-al-court (Step 3.5c nocturno) debería
     demoler estos; verificar mañana cuántos de los 28 sobreviven la noche →
     si sobreviven, componer la promoción: `entailed AND NOT confirmed-blob`.
  2. **Junk PR-wire certificado (15)**: pr-inside.com alertas de bufetes
     ("SHAREHOLDER ALERT") — el court juzga entailment, no newsworthiness, y
     "Legal Claims and Lawsuits" sobre spam PR entaila. El junk-gate existente
     (few-source/grab-bag) NO disparó — hueco puntual: clase fuente-PR-wire.
  3. **Mismatch certificado (29)**: precisión del juez del court — territorio
     GB6 (calibración post-estabilización de stamps).
- **Sobre-bloqueo 11.1%**: el otro lado del certificado — historias reales
  retenidas (dt-6135 NEET otra vez, DRC referendo, ola de calor IL). El loop
  relabel→re-juicio las recicla; vigilar que de verdad salgan.
- **Serving probe**: 8/12 en página (3 bajo el corte de ranking en páginas
  llenas — legítimo), 1 hard-miss (dt-4917 RU, página con 11 filas y ausente)
  → un caso a rastrear, no un patrón.

## Decisión (siguiendo el pre-registro)

Gate (c) FAIL → **TF-3b se queda ON** (mejora estricta, revertir empeora) pero
**no se declara terminado**: el veredicto completo de la palanca queda gateado
en subir la precisión del certificado. Escalera pre-registrada AHORA:
1. Mañana: contar cuántos de los 28 blobs sobrevivieron el barrido nocturno →
   si >0, promoción compone con confirmed-blob veto (cambio pequeño en
   `next_state`/court, mismo patrón del gate actual).
2. Fix junk PR-wire en el junk-gate (clase de dominio + few-source que no
   disparó) — chip.
3. Re-censo (mismo harness, cacheable) tras 1+2 → barra 90% re-evaluada.
4. Country-clock sigue esperando este veredicto completo (sin cambios).

Artefactos: workflow `wf_83a4f3f1-8f7` (journal con los 244×2 juicios +
tiebreaks), datos censados en scratchpad de sesión, ids de los 72 fails
preservados. Método: los jueces usaron el scoping EXACTO de recibos del court
(engine_version + quarantine — la lección GB1).
