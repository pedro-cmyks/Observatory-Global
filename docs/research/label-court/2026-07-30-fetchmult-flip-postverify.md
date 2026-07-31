# Fetch-mult M=2 — flip en prod + verificación intra-día post-flip

**2026-07-30 · `ATLAS_THREADS_FETCH_MULT=2` VIVO en Fly (meta confirma
`fetch_mult: 2`, `pool_fetched: 2×limit`). Re-medición inmediata con el harness
A0b (arms intercalados, mismo momento, misma caché). VEREDICTO: SE QUEDA —
C1/C3/C4/C5 pasan; C2-según-escrito disparó en US/DE pero el análisis
fila-por-fila muestra artefacto de denominador, no daño; se pre-registra C2b
para la siguiente medición. Decisión reversible en un env var.**

## Resultados vs las barras congeladas (spec 2026-07-29-a0b-fetch-gate-preregistration.md)

| Condición | Barra | Medido | Veredicto |
|---|---|---|---|
| C1 composición global | ≥ +15pp entailed-share | **+17.8pp** (47.2%→65.0%; failed −25.6pp; fold visible 80% entailed) | **PASS** |
| C2 por-puerta | ninguna cae >5pp | US −13.9pp · DE −9.5pp (share) | **BREACH-como-escrito → ver análisis** |
| C3 newsworthiness | mediana top-10 ≥50% de baseline | 77.8% | PASS |
| C4 cobertura | ninguna puerta pierde >25% filas; global ≥30 | global 40 filas (+11%); US/DE/GR GANARON filas | PASS |
| C5 costo | sin nueva clase de timeout | depth-80 p50 12.6s / p95 14.5s (WAN-incluido desde M1) | PASS con nota ⚠ |

## El análisis C2 — por qué la breach es artefacto y no daño

La share por puerta cayó porque **M=2 rellena páginas que antes quedaban
cortas** (US 18→24 filas, DE 14→18, GR 17→24): el denominador crece, el
numerador NO baja — **ninguna puerta perdió una sola fila entailed** (US 10→10,
DE 6→6, GR 9→**11**, TR 5→**10**, global 17→**26**).

Fila por fila (diff_vs_baseline del harness):
- **US**: entraron "Louisiana AG Indictment Stayed" (entailed, rank 5) y
  "COVID Fraud Suspect Captured" (entailed, rank 9); salieron 4 entailed-fluff
  deportivo/consumo (WNBA All-Star, Medicare grab bars, Ohtani, Aaron Donald) —
  exactamente la clase que el spec §C3 nombró como el hueco de entailed-share
  (el testigo Bieniemy). Los `failed` nuevos entran en ranks 20-21.
  **El top-10 de US mejoró.**
- **DE**: sus 4 `failed` agregados entran todos en rank ≥13 — arriba del fold
  idéntico; el tail crece con ruido stampeado (visible como tal por los chips).

La barra C2 operacionalizó "ninguna puerta empeora" como Δshare sobre página
completa; con conteos de fila variables entre arms, share castiga exactamente
lo que C4 premia (rellenar cobertura). La breach se reporta como está — la
barra disparó — y la decisión de mantener es un juicio documentado y
reversible, no un gate re-escrito en silencio.

## C2b — pre-registrado AHORA para toda medición futura de este lever

Por puerta scored: (a) el CONTEO entailed no cae, y (b) ninguna fila `failed`
ENTRA al fold visible (top-10). Ambas, hoy: **PASS en US/TR/DE/GR y el resto
de las 18 puertas** (peor entrada failed: rank 13).

## Notas

- ⚠ C5: depth-80 p95 14.5s roza el statement-timeout de 15s del fetch dinámico
  — medido DESDE la M1 (WAN incluido); server-side es menor y Redis 120s
  absorbe. Vigilar `ann_timeout`/degradaciones en el ledger tras días de carga;
  si aparecen, M=2 baja a M=1 con el env var.
- unchecked global 7.5% — el court digiere (backoff de withholds `6d6d906f`
  libera ~throughput); re-medir composición en ~2 días debería subir entailed
  aún más.
- Atribución limpia: tick-v2 fue revertido ANTES de este flip (ver
  `docs/research/recall-229/2026-07-30-tickv2-tf1-tf2-verdict.md`); hoy el
  único cambio serving-side es M=2.
- Artefacto crudo: harness A0b post-flip
  (`a0b-postflip-20260730T1649.json`, scratchpad de sesión; 18 puertas + costo).
