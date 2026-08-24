# M1 familia ① — calibración del confirmador (3 sondas, 2026-08-24)

**Mandato**: M1-GATE addendum 2026-08-24 — familia elegida ① (coseno +
confirmación barata, veredicto de Pedro). La familia exigía medir ANTES el
costo por señal y la viabilidad del confirmador. **Esto NO es G-PRECISIÓN**
(esa barra corre sobre muestra fresca y ciega, n≥50, de adjuntos NUEVOS del
fix en sombra); es la calibración que decide la FORMA del fix.

**Sustrato**: muestra A0 congelada (n=40, seed 229, candidatos coseno≥0.88 de
u2, juicios a mano del 08-20: 7 sí · 7 dudoso · 26 no) + fixture
`fixtures/2026-08-24-m1-shadow-fixture.json.gz`. Scripts:
`m1_confirmation_calibration.py` · `m1_topk_judge_probe.py` ·
`m1_comparative_probe.py`. Juez: DeepSeek temp 0, JSON estricto,
precision-first (unsure/fail = no adjuntar).

---

## Sonda 1 — confirmador binario sobre el ARGMAX único

| regla | acc | sí | dud | no | P_strict | P_lenient | R_sí |
|---|---|---|---|---|---|---|---|
| cos solo (baseline A0) | 40 | 7 | 7 | 26 | 0.175 | 0.35 | 1.0 |
| cos ≥0.90 (gate u2) | 29 | 6 | 6 | 17 | 0.207 | 0.41 | 0.86 |
| P-NUEVO headline↔label | 1 | 0 | 1 | 0 | 0 | 1.0 | 0 |
| cobertura tokens ≥0.5 | 4 | 1 | 3 | 0 | 0.25 | 1.0 | 0.14 |
| entidades compartidas ≥1 | 3 | 0 | 2 | 1 | 0 | 0.67 | 0 |
| **juez binario** | **3** | **2** | **1** | **0** | 0.67 | **1.0** | 0.29 |

- **El juez no aceptó NINGÚN vecino falso (0/26)** — la señal léxica casi no
  dispara sola (labels cortos, cross-language). El costo: 40 juicios en 8.7s,
  ~194 tokens/juicio ≈ **$0.0001/señal** — el costo no es la barrera.
- Pero el binario-sobre-argmax hereda la dispersión: rechaza correctamente al
  vecino falso y el adjunto SE PIERDE (recall 3/40).

## Sonda 2 — binario sobre top-5 de ACTIVOS: dos fallas instructivas

200 pares juzgados (30s): 5 yes → **a mano, 3 de los 5 son falsos**
(protesta albanesa→"Crime and Tragedy", Sifnos→"Wildfires", deuda-US→"Gas
Prices").

1. **Comparaciones múltiples**: el juez binario tiene ~1.6% de falso-yes por
   par; K=5 pares independientes por señal multiplica la exposición. K juicios
   binarios NO es la forma correcta.
2. **El pool de solo-activos EXCLUYE la historia correcta**: dt-9844
   (protesta) y dt-15350 (deuda US) EXISTEN — en estado `candidate`. La
   historia correcta de una señal fresca suele estar naciendo como candidate
   (u2 la creó en la misma corrida, A0 §4). Sin ella en el pool, el juez solo
   ve vecinos.

## Sonda 3 — comparativo sobre active∪candidate (la forma que va a sombra)

Pool 9,878 topics (4,245 active + candidates con centroide), top-5 ≥0.80,
**UNA llamada por señal** (elige 1..K o null). 40 llamadas, 7.5s.

**12/40 adjuntos (30%)**. Juicio a mano de los 12 (un lector, mismo criterio
del A0):

| clase | n | casos |
|---|---|---|
| correcto específico | 6 | Sudan Displacement · **Albanian Anti-Government Protests (rescatado del pool candidate)** · **Sunita Ahuja Divorce Case (un "no" del argmax adjuntado a su historia EXACTA)** · Hernández Trial · Mushroom Murder Appeal · Flock Camera Backlash |
| bucket genérico (cuenta sí por la convención A0) | 2 | Price Target Changes · Q2 Earnings Calls |
| dudoso (gemela de teatro) | 1 | Lake Powell→Lake Mead |
| **falso** | **3** | Шлосберг→"Journalist Shipacheva Sentenced" (gemela-de-PERSONA) · tenants-AC→"Germany's Social and Policy Issues" (bucket vago regional) · Cauvery firing→"Cauvery Water Dispute" (misma-entidad-otro-evento) |

**Precisión ~67-75%** (8/12 estricto; 9/12 contando el dudoso) vs 17.5% del
argmax. **Recall sobre modo-ii**: los rescates de Sunita y Albania son
exactamente la clase que el Z4 nombró (la historia correcta existe, el argmax
cae al lado).

## Lectura

1. **La familia ① es viable y su forma es la comparativa**: top-K sobre
   active∪candidate + juez que elige-o-rechaza. 1 llamada/señal, centavos por
   decenas de miles.
2. **La brecha a 90% tiene nombre** — los 3 falsos son 3 clases con palanca:
   - *gemela-de-persona* (Shlosberg/Shipacheva): veto barato — persona en el
     label del candidato ≠ persona de la señal (nlp_persons ya cubre 99.6%);
     cross-script necesita transliteración o el propio juez con la persona
     EXPLÍCITA en el prompt.
   - *bucket vago* ("Germany's Social and Policy Issues", "Crime and
     Tragedy"): excluir del pool los labels clase-blob (el programa
     junk/overmerge ya los detecta) o marcar bucket-attach como tier aparte,
     nunca "historia".
   - *misma-entidad-otro-evento* (Cauvery): prompt más duro sobre "same
     event" + member-headlines del candidato (ya van, subir de 2 a 3).
3. **G-RECALL es plausible**: 30% de adjuntos confirmados sobre candidatos
   ≥0.88; con 93% sin historia y 88% con candidato, el orden de magnitud es
   7% → ~25-30% de cobertura — encima de la barra de 20%, SI la precisión
   aguanta. La sombra lo mide de verdad.

## Caveats

- Un solo lector (yo), n chico, misma muestra que nombró el problema —
  calibración, no gold. El gold es del gate (muestra fresca ciega n≥50).
- **Drift de 4 días**: las sondas corren contra los topics de HOY; los
  juicios a mano del A0 eran contra los del 08-20 (dt-9844 pasó a candidate,
  labels cambiaron). En sombra el fix corre mismo-día y este ruido desaparece.
- Los testigos (86) no entraron a las sondas: sin fila en signal_embeddings
  (re-embed e5 del headline en el replay de sombra — determinístico).

## Siguiente (A2 — el fix en sombra, per prereg)

Lane nocturna en sombra: señales servibles sin historia → top-5
active∪candidate ≥0.80 → juez comparativo + vetos (persona-conflicto,
bucket-vago fuera del pool) → ledger sombra (flag propio, cero writes a
serving). Contra las 6 barras congeladas: G-PRECISIÓN muestra ciega n≥50 ·
G-RECALL fracción servible-con-historia · G-RETENCIÓN adjunto persiste ·
G-TESTIGOS replay del fixture · G-NO-DAÑO cohesión/court/blob-rate ·
reversibilidad por ledger.

*Costo total de las 3 sondas: 280 llamadas DeepSeek, <$0.01, <50s de pared.*
